"""Browser Manager module.
Manages persistent Playwright browser sessions for Google Flow.
Preserves user profile, authentication cookies, and handles anti-bot mitigations.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, Playwright, BrowserContext, Page
from config import USER_DATA_DIR, HEADLESS, PAGE_TIMEOUT_SEC, FLOW_URL

logger = logging.getLogger("flow_automation.browser")


class BrowserManager:
    """Controls Playwright persistent context to retain Google authentication."""

    def __init__(
        self,
        user_data_dir: Path = USER_DATA_DIR,
        headless: bool = HEADLESS,
        timeout_sec: int = PAGE_TIMEOUT_SEC,
    ):
        self.user_data_dir = Path(user_data_dir)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.timeout_sec = timeout_sec
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self) -> Tuple[BrowserContext, Page]:
        """Launch persistent browser context and return (context, page)."""
        if self.context and self.page and not self.page.is_closed():
            return self.context, self.page

        logger.info(f"Launching persistent browser context from {self.user_data_dir} (headless={self.headless})...")
        self.playwright = sync_playwright().start()

        # Browser flags to prevent automation detection during Google login
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-infobars",
            "--start-maximized",
        ]

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            channel=None,  # Playwright bundled chromium
            args=args,
            no_viewport=True,
            accept_downloads=True,
        )

        # Remove navigator.webdriver flag in JS
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Get or create page
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        self.page.set_default_timeout(self.timeout_sec * 1000)
        return self.context, self.page

    def navigate_to_flow(self, url: str = FLOW_URL) -> Page:
        """Navigate to Google Flow with timeout and networkidle wait."""
        _, page = self.start()
        logger.info(f"Navigating to {url}...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_sec * 1000)
        except Exception as e:
            logger.warning(f"Initial navigation notice: {e}. Trying to continue...")
        return page

    def is_logged_in(self, page: Optional[Page] = None) -> bool:
        """Check if user is logged into Google / Google Labs."""
        p = page or self.page
        if not p:
            return False

        # Common indicators of being signed in to Google / Google Labs:
        # 1. Profile avatar / account button (e.g., aria-label containing "Google Account", "Sign out")
        # 2. Absence of primary "Sign in" buttons
        try:
            sign_in_buttons = p.locator("a:has-text('Sign in'), button:has-text('Sign in'), a:has-text('Log in'), button:has-text('Log in')")
            if sign_in_buttons.count() > 0 and sign_in_buttons.first.is_visible():
                return False

            profile_elements = p.locator("[aria-label*='Google Account' i], [aria-label*='Account' i], img[src*='googleusercontent.com']")
            if profile_elements.count() > 0 and profile_elements.first.is_visible():
                return True
        except Exception as e:
            logger.debug(f"is_logged_in check error: {e}")

        return False

    def close(self) -> None:
        """Safely close context and Playwright instance."""
        try:
            if self.context:
                self.context.close()
        except Exception as e:
            logger.debug(f"Context close error: {e}")
        finally:
            self.context = None
            self.page = None

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.debug(f"Playwright stop error: {e}")
        finally:
            self.playwright = None
        logger.info("Browser session closed cleanly.")

