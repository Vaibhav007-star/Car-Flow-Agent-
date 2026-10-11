"""Autopilot Pipeline for Google Flow Video Automation System.
Runs a zero-touch autonomous loop:
  1. Scans viral automotive trends (YouTube Shorts / Google Trends)
  2. Formulates locked 10-shot prompts from Car Promot.pdf
  3. Automates Google Flow to render 9:16 vertical Short videos
  4. Downloads and verifies MP4s to output_videos/
  5. Repeats continuously on a configured schedule or runs once.
"""

import sys
import time
import signal
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import LOGS_DIR, OUTPUT_DIR
from prompt_manager import PromptManager
from browser_manager import BrowserManager
from downloader import VideoDownloader
from flow_automation import GoogleFlowAutomation
from trend_hunter import TrendHunter
from history_manager import HistoryManager

# Configure autopilot logging
logger = logging.getLogger("flow_automation.autopilot")
logger.setLevel(logging.INFO)

autopilot_log = LOGS_DIR / "autopilot.log"
file_handler = logging.FileHandler(autopilot_log, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
if not logger.handlers:
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)


class AutopilotRunner:
    """Orchestrates end-to-end hands-free content generation cycles."""

    def __init__(self, headless: bool = False, auto_upload: bool = False, privacy_status: str = "public", schedule_interval: Optional[float] = None, daily_slots: bool = False):
        self.headless = headless
        self.auto_upload = auto_upload
        self.privacy_status = privacy_status
        self.schedule_interval = schedule_interval
        self.daily_slots = daily_slots
        self.stop_requested = False
        self.pm = PromptManager()
        self.hm = HistoryManager()
        self.th = TrendHunter(history_manager=self.hm)
        self.dl = VideoDownloader()

    def run_single_cycle(self, viral_count: int = 2) -> dict:
        """Executes one full autonomous cycle: Hunt -> Prompt -> Generate -> Download."""
        cycle_start = datetime.now()
        logger.info("===================================================================")
        logger.info(f"🚀 STARTING AUTOPILOT CYCLE: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("===================================================================")

        # 0. Anti-Repetition Pre-check
        self.hm.sync_from_prompts_state(self.pm)
        cleaned = self.hm.clean_queue_duplicates(self.pm)
        if cleaned > 0:
            logger.info(f"Anti-repetition: Purged {cleaned} duplicate prompts from generation queue.")

        # 1. Trend Hunting
        logger.info(f"[Step 1/3] Hunting top {viral_count} viral cars (excluding past builds)...")
        trends = self.th.get_trending_cars(max_results=viral_count)
        if not trends:
            logger.warning("No viral trends discovered in this cycle. Retrying on next tick.")
            return {"status": "no_trends", "downloaded": []}

        # 2. Auto-Queue Prompts
        logger.info(f"[Step 2/3] Synthesizing Car Promot.pdf prompts for {len(trends)} cars...")
        added_count = self.th.queue_trending_cars(trends, self.pm)
        logger.info(f"Queued {added_count} new non-duplicate prompts into generation queue.")

        # 3. Automated Flow Generation
        logger.info(f"[Step 3/3] Launching Google Flow automation (headless={self.headless})...")
        bm = BrowserManager(headless=self.headless)
        automation = GoogleFlowAutomation(browser_manager=bm, prompt_manager=self.pm, downloader=self.dl)

        try:
            summary = automation.run_queue(max_items=viral_count)
            logger.info(f"Cycle generation finished. Queue summary: {summary}")
        except Exception as e:
            logger.error(f"Error during automation cycle: {e}")
        finally:
            bm.close()

        # 4. Auto-Upload to YouTube Shorts (if enabled)
        if self.auto_upload:
            logger.info("[Step 4/4] Auto-uploading/scheduling completed videos to YouTube Shorts...")
            try:
                from yt_uploader import YouTubeUploader
                uploader = YouTubeUploader()
                uploaded = uploader.auto_upload_completed_videos(
                    privacy_status=self.privacy_status,
                    use_daily_slots=self.daily_slots,
                    schedule_interval_hours=self.schedule_interval,
                    pm=self.pm,
                )
                logger.info(f"Uploaded/Scheduled {len(uploaded)} videos to YouTube Shorts.")
            except Exception as e:
                logger.warning(f"YouTube auto-upload notice: {e}")

        # Update persistent history ledger
        self.hm.sync_from_prompts_state(self.pm)

        cycle_end = datetime.now()
        duration_min = (cycle_end - cycle_start).total_seconds() / 60
        logger.info(f"🏁 Cycle finished in {duration_min:.1f} minutes.")
        logger.info("===================================================================\n")
        return self.pm.get_summary()

    def run_loop(self, viral_count: int = 2, interval_hours: float = 12.0) -> None:
        """Runs the autonomous pipeline on a recurring schedule."""
        interval_seconds = interval_hours * 3600
        cycle_num = 1

        logger.info(f"🤖 Autopilot active: Producing {viral_count} viral videos every {interval_hours} hours.")
        logger.info("Press Ctrl+C at any time to shut down gracefully.\n")

        while not self.stop_requested:
            logger.info(f"--- Cycle #{cycle_num} ---")
            self.run_single_cycle(viral_count=viral_count)
            cycle_num += 1

            if self.stop_requested:
                break

            next_run = datetime.fromtimestamp(time.time() + interval_seconds)
            logger.info(f"💤 Sleeping for {interval_hours} hours. Next cycle at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

            # Sleep in short increments to allow responsive Ctrl+C shutdown
            sleep_start = time.time()
            while time.time() - sleep_start < interval_seconds:
                if self.stop_requested:
                    break
                time.sleep(2)

        logger.info("Autopilot loop terminated cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Google Flow Autopilot Runner")
    parser.add_argument("--count", type=int, default=2, help="Number of viral cars to produce per cycle (default 2)")
    parser.add_argument("--interval-hours", type=float, default=12.0, help="Interval between cycles in hours (default 12.0)")
    parser.add_argument("--once", action="store_true", help="Execute a single cycle immediately and exit")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode without opening GUI window")
    parser.add_argument("--upload", action="store_true", help="Automatically upload completed videos to YouTube Shorts")
    parser.add_argument("--privacy", type=str, default="public", choices=["public", "unlisted", "private"], help="Privacy status for YouTube uploads (default: public)")
    parser.add_argument("--daily-slots", action="store_true", help="Automatically schedule videos to next 2 daily peak slots (1:30 PM & 8:00 PM IST)")
    parser.add_argument("--schedule-interval", type=float, default=None, help="Stagger scheduled video release by N hours apart (e.g. 2 or 4)")

    args = parser.parse_args()
    runner = AutopilotRunner(
        headless=args.headless,
        auto_upload=args.upload,
        privacy_status=args.privacy,
        schedule_interval=args.schedule_interval,
        daily_slots=args.daily_slots,
    )

    # Handle Ctrl+C gracefully
    def handle_signal(sig, frame):
        print("\n[!] Shutdown signal received. Stopping autopilot...")
        runner.stop_requested = True

    signal.signal(signal.SIGINT, handle_signal)

    if args.once:
        runner.run_single_cycle(viral_count=args.count)
    else:
        runner.run_loop(viral_count=args.count, interval_hours=args.interval_hours)


if __name__ == "__main__":
    main()

