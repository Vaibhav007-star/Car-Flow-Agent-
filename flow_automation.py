"""Google Flow Automation Core.
Coordinates Playwright browser interaction, prompt submission, generation monitoring,
error detection, and automatic video downloading.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config import FLOW_URL, GENERATION_TIMEOUT_SEC, POLL_INTERVAL_SEC, LOGS_DIR
from browser_manager import BrowserManager
from prompt_manager import PromptManager
from downloader import VideoDownloader

# Setup file and stream logger
logger = logging.getLogger("flow_automation")
logger.setLevel(logging.INFO)

log_file = LOGS_DIR / "automation.log"
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
if not logger.handlers:
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)


class GoogleFlowAutomation:
    """Automates video generation lifecycle on Google Flow."""

    def __init__(
        self,
        browser_manager: Optional[BrowserManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        downloader: Optional[VideoDownloader] = None,
    ):
        self.browser_manager = browser_manager or BrowserManager()
        self.prompt_manager = prompt_manager or PromptManager()
        self.downloader = downloader or VideoDownloader()
        self.is_running = False
        self._stop_requested = False

    def request_stop(self) -> None:
        """Signal the automation loop to stop after the current step."""
        logger.info("Stop requested by user.")
        self._stop_requested = True

    def ensure_authenticated_session(self, page: Page, wait_timeout: int = 300) -> bool:
        """Checks if user is logged into Google Flow. If not, prompts for manual login and waits."""
        current_url = page.url.lower()

        # Check if we landed on about page or Google sign-in
        if "flow.google.com/about" in current_url:
            logger.info("On Google Flow landing page. Clicking 'Create with Google Flow'...")
            try:
                create_btn = page.locator("button:has-text('Create with Google Flow'), a:has-text('Create with Google Flow')").first
                if create_btn.is_visible():
                    create_btn.click()
                    page.wait_for_timeout(3000)
                    current_url = page.url.lower()
            except Exception as e:
                logger.warning(f"Could not click 'Create with Google Flow': {e}")

        if "accounts.google.com" in current_url or "flow.google.com/about" in current_url:
            logger.warning("===================================================================")
            logger.warning("ACTION REQUIRED: Please sign in to your Google Account in the browser window.")
            logger.warning(f"Waiting up to {wait_timeout} seconds for sign-in to complete...")
            logger.warning("===================================================================")

            start_time = time.time()
            while time.time() - start_time < wait_timeout:
                if self._stop_requested:
                    return False
                time.sleep(2)
                cur = page.url.lower()
                # If redirected to flow.google.com (and not /about or accounts)
                if "flow.google.com" in cur and "/about" not in cur and "accounts.google" not in cur:
                    logger.info("Successfully authenticated! Reached Google Flow studio.")
                    page.wait_for_timeout(3000)
                    return True

            logger.error("Authentication timed out. Please sign in and try again.")
            return False

        # Ensure project studio is active
        self.ensure_project_open(page)
        return True

    def ensure_project_open(self, page: Page, timeout_sec: int = 20) -> bool:
        """Ensures the browser has entered an active Google Flow project canvas."""
        current_url = page.url.lower()
        if "/project/" in current_url:
            return True

        logger.info("Opening Google Flow project studio...")
        # Check for 'New project' button on dashboard
        new_proj_selectors = [
            "button:has-text('New project')",
            "a:has-text('New project')",
            "[aria-label*='New project' i]",
            "button:has-text('add')",
            "div:has-text('New project')",
        ]

        start_t = time.time()
        while time.time() - start_t < timeout_sec:
            if "/project/" in page.url.lower():
                page.wait_for_timeout(3000)
                return True

            for sel in new_proj_selectors:
                loc = page.locator(sel)
                try:
                    if loc.count() > 0 and loc.first.is_visible():
                        logger.info(f"Clicking 'New project' button ({sel})...")
                        loc.first.click()
                        page.wait_for_timeout(4000)
                        if "/project/" in page.url.lower():
                            logger.info(f"Entered project studio: {page.url}")
                            page.wait_for_timeout(2000)
                            return True
                except Exception:
                    continue

            # Also check if existing projects exist to click
            project_cards = page.locator("a[href*='/project/']")
            if project_cards.count() > 0:
                logger.info("Clicking existing project card...")
                project_cards.first.click()
                page.wait_for_timeout(4000)
                if "/project/" in page.url.lower():
                    return True

            time.sleep(2)

        return "/project/" in page.url.lower()

    def find_prompt_input(self, page: Page, timeout_sec: int = 15):
        """Locates the prompt input box using resilient fallback selectors with a retry loop."""
        input_selectors = [
            "div.ProseMirror[contenteditable='true']",
            ".prosemirror-editor [contenteditable='true']",
            ".prompt-input [contenteditable='true']",
            "flow-rich-text-editor [contenteditable='true']",
            "div[contenteditable='true']",
            "[contenteditable='true']",
            "textarea[placeholder*='Describe' i]",
            "textarea[placeholder*='prompt' i]",
            "textarea[placeholder*='create' i]",
            "textarea",
            "input[placeholder*='Describe' i]",
            "[role='textbox']",
        ]

        start_t = time.time()
        while time.time() - start_t < timeout_sec:
            for selector in input_selectors:
                loc = page.locator(selector)
                try:
                    count = loc.count()
                    for i in range(count):
                        candidate = loc.nth(i)
                        if candidate.is_visible():
                            logger.info(f"Found prompt input with selector: '{selector}'")
                            return candidate
                except Exception:
                    continue
            time.sleep(1)

        return None

    def find_generate_button(self, page: Page):
        """Locates the generate/submit button."""
        button_selectors = [
            "button[aria-label*='Start generation' i]",
            "flow-generate-icon-button button",
            "button[type='submit']:has-text('arrow_forward')",
            "button[type='submit']",
            "button:has-text('Generate')",
            "button:has-text('Create')",
            "button[aria-label*='Generate' i]",
            "button[aria-label*='Create' i]",
            "button[aria-label*='Submit' i]",
            "button[aria-label*='Send' i]",
        ]

        for selector in button_selectors:
            loc = page.locator(selector)
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    logger.info(f"Found generate button with selector: '{selector}'")
                    return loc.first
            except Exception:
                continue

        return None

    def detect_generation_in_progress(self, page: Page) -> bool:
        """Check if generation is actively ongoing."""
        indicators = [
            "text=Generating",
            "text=Creating video",
            "text=In progress",
            "text=Rendering",
            "[role='progressbar']",
            ".progress-bar",
            "svg.spinner",
        ]
        for ind in indicators:
            try:
                if page.locator(ind).count() > 0 and page.locator(ind).first.is_visible():
                    return True
            except Exception:
                continue
        return False

    def check_for_errors(self, page: Page) -> Optional[str]:
        """Detect visible error banners, policy blocks, or rate limit messages."""
        error_indicators = [
            ("Policy violation", "Prompt flagged by content policy"),
            ("Terms of Service", "Content blocked by terms"),
            ("Daily limit reached", "Daily generation limit reached"),
            ("Limit reached", "Account limit reached"),
            ("Generation failed", "Generation failed on server"),
            ("Something went wrong", "Temporary server error"),
        ]
        page_text = ""
        try:
            page_text = page.locator("body").inner_text()
        except Exception:
            pass

        for trigger, msg in error_indicators:
            if trigger.lower() in page_text.lower():
                return msg
    def configure_generation_settings(
        self,
        page: Page,
        mode: str = "Video",
        sub_type: str = "Ingredients",
        aspect_ratio: str = "9:16",
        duration: str = "8s",
        quantity: str = "x1",
    ) -> bool:
        """Configures generation parameters (Video, 9:16 vertical ratio, 8s, x1) in the Flow popover."""
        settings_btn = page.locator("button[aria-label*='Settings trigger' i]").first
        if not settings_btn.is_visible():
            logger.debug("Settings trigger button not found.")
            return False

        logger.info(f"Configuring generation settings: {mode}, {sub_type}, {aspect_ratio}, {duration}, {quantity}...")
        try:
            settings_btn.click()
            page.wait_for_timeout(1000)

            # 1. Mode: Video
            if mode:
                v_btn = page.locator(f".cdk-overlay-container button:has-text('{mode}')").first
                if v_btn.is_visible():
                    v_btn.click()
                    page.wait_for_timeout(500)

            # 2. Sub-type: Ingredients
            if sub_type:
                ing_btn = page.locator(f".cdk-overlay-container button:has-text('{sub_type}')").first
                if ing_btn.is_visible():
                    ing_btn.click()
                    page.wait_for_timeout(300)

            # 3. Aspect Ratio: 9:16
            if aspect_ratio:
                ar_btn = page.locator(f".cdk-overlay-container button:has-text('{aspect_ratio}')").first
                if ar_btn.is_visible():
                    ar_btn.click()
                    page.wait_for_timeout(300)

            # 4. Duration: 8s
            if duration:
                dur_btn = page.locator(f".cdk-overlay-container button:has-text('{duration}')").first
                if dur_btn.is_visible():
                    dur_btn.click()
                    page.wait_for_timeout(300)

            # 5. Quantity: x1
            if quantity:
                q_btn = page.locator(f".cdk-overlay-container button:has-text('{quantity}')").first
                if q_btn.is_visible():
                    q_btn.click()
                    page.wait_for_timeout(300)

            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            logger.info("Settings configured successfully.")
            return True
        except Exception as e:
            logger.warning(f"Error configuring settings popover: {e}")
            page.keyboard.press("Escape")
            return False

    def try_open_canvas_card(self, page: Page) -> bool:
        """Finds and clicks the latest generated media card on the Google Flow canvas to reveal the video player."""
        if page.locator("video").count() > 0 and page.locator("video").first.is_visible():
            return True

        # 1. Direct HTML5 Canvas Coordinate Click (Flow cards are WebGL rendered)
        try:
            canvas = page.locator("canvas").first
            if canvas.is_visible():
                coords_to_try = [(110, 300), (150, 320), (200, 300), (250, 350), (180, 280), (120, 260)]
                for x, y in coords_to_try:
                    page.mouse.click(x, y)
                    page.wait_for_timeout(1200)
                    if page.locator("video").count() > 0:
                        logger.info(f"Canvas card successfully opened at coordinates ({x}, {y})!")
                        return True
        except Exception as e:
            logger.debug(f"Canvas coordinate click notice: {e}")

        # 2. DOM-based fallbacks
        card_selectors = [
            "flow-media-card",
            "flow-card",
            "[data-node-id]",
            "div[role='article']",
            "div[class*='media-card' i]",
            "button[aria-label*='Play' i]",
        ]

        for sel in card_selectors:
            loc = page.locator(sel)
            try:
                cnt = loc.count()
                if cnt > 0:
                    target = loc.nth(cnt - 1)
                    if target.is_visible():
                        logger.info(f"Clicking latest canvas card with selector '{sel}'...")
                        target.click(force=True)
                        page.wait_for_timeout(1500)
                        if page.locator("video").count() > 0:
                            logger.info("Canvas card clicked successfully, video player revealed!")
                            return True
            except Exception as e:
                logger.debug(f"Selector '{sel}' click notice: {e}")

        return False

    def extract_and_download_video(self, page: Page, prompt_item: Dict[str, Any], direct_url: Optional[str] = None) -> Optional[Path]:
        """Detect and download completed video either via direct URL, download button, or video element src."""
        prompt_text = prompt_item.get("prompt", "")
        target_name = self.downloader.generate_filename(prompt_text=prompt_text)

        # 0. Direct captured URL from network response listener
        if direct_url and direct_url.startswith("http"):
            try:
                logger.info(f"Downloading directly from captured stream URL: {direct_url[:60]}...")
                return self.downloader.download_url(direct_url, target_filename=target_name)
            except Exception as e:
                logger.warning(f"Direct stream URL download notice ({e}), falling back to UI extraction...")

        # If video element is not yet in DOM, click the canvas card
        if page.locator("video").count() == 0:
            self.try_open_canvas_card(page)

        # 1. Check for <video> element inside player
        video_locator = page.locator("video")
        if video_locator.count() > 0:
            for i in range(video_locator.count()):
                v = video_locator.nth(i)
                src = v.get_attribute("src")
                if src:
                    logger.info(f"Found video element src: {src[:60]}...")
                    if src.startswith("blob:"):
                        try:
                            saved_path = self.downloader.download_blob_via_page(page, src, target_filename=target_name)
                            page.keyboard.press("Escape")
                            return saved_path
                        except Exception as e:
                            logger.error(f"Failed to extract blob video: {e}")
                    elif src.startswith("http"):
                        try:
                            saved_path = self.downloader.download_url(src, target_filename=target_name)
                            page.keyboard.press("Escape")
                            return saved_path
                        except Exception as e:
                            logger.error(f"Failed to download video URL: {e}")

        # 2. Check for Playwright download trigger on download button
        download_buttons = [
            "button[aria-label*='Download' i]",
            "button:has-text('Download')",
            "a[aria-label*='Download' i]",
            "a:has-text('Download')",
            "a[download]",
        ]

        for sel in download_buttons:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                logger.info(f"Triggering download button ({sel})...")
                try:
                    with page.expect_download(timeout=15000) as download_info:
                        loc.first.click()
                    download = download_info.value
                    saved_path = self.downloader.save_playwright_download(download, target_filename=target_name)
                    return saved_path
                except Exception as e:
                    logger.debug(f"Direct download trigger notice: {e}. Trying alternative extraction...")

        return None

    def process_single_prompt(self, page: Page, prompt_item: Dict[str, Any]) -> bool:
        """Executes generation for a single prompt."""
        prompt_id = prompt_item["id"]
        prompt_text = prompt_item["prompt"]

        logger.info(f"--- Starting Prompt [{prompt_id}]: '{prompt_text}' ---")
        self.prompt_manager.update_status(prompt_id, "Processing")

        # 1. Locate prompt input (ensure project is open)
        self.ensure_project_open(page)

        # Apply settings: Video, Ingredients, 9:16 vertical, 8s, x1
        self.configure_generation_settings(page, mode="Video", sub_type="Ingredients", aspect_ratio="9:16", duration="8s", quantity="x1")

        input_box = self.find_prompt_input(page, timeout_sec=15)
        if not input_box:
            err = "Could not locate prompt input box. Interface may have changed or project is not open."
            logger.error(err)
            self.prompt_manager.update_status(prompt_id, "Failed", error=err)
            return False

        # 2. Enter prompt into ProseMirror / input element
        try:
            input_box.click()
            page.wait_for_timeout(300)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.wait_for_timeout(200)
            input_box.press_sequentially(prompt_text, delay=10)
            page.wait_for_timeout(1000)
        except Exception as e:
            err = f"Failed to type prompt into input box: {e}"
            logger.error(err)
            self.prompt_manager.update_status(prompt_id, "Failed", error=err)
            return False

        # 3. Locate & trigger generate button
        gen_btn = self.find_generate_button(page)
        if gen_btn:
            try:
                gen_btn.click()
                logger.info("Clicked generate button (Start generation).")
            except Exception as e:
                logger.warning(f"Failed clicking generate button: {e}. Trying Enter key...")
                page.keyboard.press("Enter")
        else:
            logger.info("No generate button found; pressing Enter...")
            page.keyboard.press("Enter")

        # 4. Wait for generation to start and finish
        logger.info(f"Waiting for video generation (up to {GENERATION_TIMEOUT_SEC}s)...")
        start_time = time.time()
        page.wait_for_timeout(5000)  # Initial grace period

        # Sniff network responses for video streams (.mp4 or flow-content.google/video)
        captured_stream_url: Optional[str] = None
        def on_response(response):
            nonlocal captured_stream_url
            try:
                u = response.url
                if ".mp4" in u or "flow-content.google/video" in u:
                    captured_stream_url = u
                    logger.info(f"Captured live video stream from network: {u[:60]}...")
            except Exception:
                pass

        page.on("response", on_response)

        generation_completed = False
        try:
            while time.time() - start_time < GENERATION_TIMEOUT_SEC:
                if self._stop_requested:
                    logger.warning("Generation aborted due to stop request.")
                    self.prompt_manager.update_status(prompt_id, "Pending")
                    return False

                # Check for error banners
                error_detected = self.check_for_errors(page)
                if error_detected:
                    logger.error(f"Generation error detected: {error_detected}")
                    self.prompt_manager.update_status(prompt_id, "Failed", error=error_detected)
                    return False

                # Check if stream URL was captured directly
                if captured_stream_url:
                    logger.info("Direct video stream detected from Flow CDN!")
                    generation_completed = True
                    break

                # Check if video player or download button is already open
                videos = page.locator("video")
                downloads = page.locator("button[aria-label*='Download' i], a[aria-label*='Download' i], button:has-text('Download')")

                if (videos.count() > 0 and videos.first.is_visible()) or (downloads.count() > 0 and downloads.first.is_visible()):
                    logger.info("Video generation completed successfully!")
                    generation_completed = True
                    break

                # After 25 seconds of generation, try opening the canvas card
                elapsed = time.time() - start_time
                if elapsed > 25:
                    if self.try_open_canvas_card(page):
                        logger.info("Video generation completed and modal opened!")
                        generation_completed = True
                        break

                time.sleep(POLL_INTERVAL_SEC)
        finally:
            try:
                page.remove_listener("response", on_response)
            except Exception:
                pass

        if not generation_completed:
            err = f"Generation timed out after {GENERATION_TIMEOUT_SEC} seconds."
            logger.error(err)
            self.prompt_manager.update_status(prompt_id, "Failed", error=err)
            return False

        # 5. Download and verify the video
        page.wait_for_timeout(3000)
        saved_file = self.extract_and_download_video(page, prompt_item, direct_url=captured_stream_url)
        if saved_file and saved_file.exists():
            rel_path = str(saved_file.name)
            logger.info(f"Successfully saved and verified video: {rel_path}")
            self.prompt_manager.update_status(prompt_id, "Completed", output_file=rel_path)
            return True
        else:
            err = "Video generated but download could not be captured automatically."
            logger.error(err)
            self.prompt_manager.update_status(prompt_id, "Failed", error=err)
            return False

    def run_queue(
        self,
        max_items: Optional[int] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, int]:
        """Main batch processing loop."""
        self.is_running = True
        self._stop_requested = False
        logger.info("Starting Google Flow automation queue...")

        _, page = self.browser_manager.start()
        self.browser_manager.navigate_to_flow()

        auth_ok = self.ensure_authenticated_session(page)
        if not auth_ok:
            logger.error("Could not authenticate session. Halting automation.")
            self.is_running = False
            return self.prompt_manager.get_summary()

        processed_count = 0
        while not self._stop_requested:
            if max_items is not None and processed_count >= max_items:
                logger.info(f"Reached requested max_items ({max_items}). Stopping.")
                break

            item = self.prompt_manager.get_next_pending()
            if not item:
                logger.info("No pending prompts remaining in queue.")
                break

            if progress_callback:
                progress_callback(item)

            success = self.process_single_prompt(page, item)
            processed_count += 1

            if progress_callback:
                progress_callback(item)

            # Polling delay between prompts
            time.sleep(2)

        self.is_running = False
        summary = self.prompt_manager.get_summary()
        logger.info(f"Automation queue completed. Summary: {summary}")
        return summary

