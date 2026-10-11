"""CLI entry point for Google Flow Video Automation System.
Allows running batch generation, testing authentication, and inspecting queue status.
"""

import sys
import argparse
import logging
from prompt_manager import PromptManager
from browser_manager import BrowserManager
from downloader import VideoDownloader
from flow_automation import GoogleFlowAutomation

logger = logging.getLogger("flow_automation.cli")


def print_status(manager: PromptManager) -> None:
    summary = manager.get_summary()
    print("\n" + "=" * 50)
    print("      GOOGLE FLOW AUTOMATION - QUEUE STATUS      ")
    print("=" * 50)
    print(f"Total:      {summary['Total']}")
    print(f"Pending:    {summary['Pending']}")
    print(f"Processing: {summary['Processing']}")
    print(f"Completed:  {summary['Completed']}")
    print(f"Failed:     {summary['Failed']}")
    print("-" * 50)
    for i, item in enumerate(manager.items, 1):
        status_symbol = {
            "Completed": "[DONE]",
            "Processing": "[BUSY]",
            "Pending": "[WAIT]",
            "Failed": "[FAIL]",
        }.get(item["status"], "[?]")
        out = f" -> {item['output_file']}" if item.get("output_file") else ""
        err = f" (Error: {item['error']})" if item.get("error") else ""
        print(f"{i:2d}. {status_symbol} [{item['id']}] {item['prompt'][:60]}...{out}{err}")
    print("=" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Google Flow Video Automation CLI")
    parser.add_argument("--login", action="store_true", help="Launch browser to manually log into Google Account")
    parser.add_argument("--run", action="store_true", help="Run the automated video generation queue")
    parser.add_argument("--status", action="store_true", help="Display current queue status")
    parser.add_argument("--retry", action="store_true", help="Reset all Failed/Processing prompts to Pending")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of prompts to process")
    parser.add_argument("--add", type=str, help="Add a new prompt to the queue")
    parser.add_argument("--hunt", type=int, nargs="?", const=3, help="Hunt for top N viral cars and auto-queue them (default 3)")
    parser.add_argument("--upload-yt", action="store_true", help="Upload completed un-uploaded videos to YouTube Shorts")
    parser.add_argument("--privacy", type=str, default="public", choices=["public", "unlisted", "private"], help="YouTube upload privacy status")
    parser.add_argument("--daily-slots", action="store_true", help="Automatically schedule uploads to the 2 daily peak slots (1:30 PM & 8:00 PM IST)")
    parser.add_argument("--schedule-interval", type=float, default=None, help="Stagger scheduled batch uploads by N hours apart")
    parser.add_argument("--clean", action="store_true", help="Purge any duplicate pending prompts from queue")
    parser.add_argument("--history", action="store_true", help="Display permanent generation history ledger")
    parser.add_argument("--headless", action="store_true", help="Force headless browser mode")

    args = parser.parse_args()
    pm = PromptManager()

    if args.hunt:
        from trend_hunter import TrendHunter
        th = TrendHunter()
        print(f"\nScanning viral automotive trends (top {args.hunt})...")
        trends = th.get_trending_cars(max_results=args.hunt)
        added = th.queue_trending_cars(trends, pm)
        print(f"Successfully queued {added} new viral car prompts:")
        for t in trends:
            print(f"- {t['car']} ({t['color']}) [Score: {t['score']}] Source: {t['source']}")
        print_status(pm)
        return

    if args.add:
        item = pm.add_prompt(args.add)
        print(f"Added prompt [{item['id']}]: '{item['prompt']}'")
        return

    if args.history:
        from history_manager import HistoryManager
        hm = HistoryManager()
        hm.sync_from_prompts_state(pm)
        print("\n" + "=" * 50)
        print("      GENERATION HISTORY LEDGER (UNIQUE BUILDS)    ")
        print("=" * 50)
        if not hm.entries:
            print("No completed builds recorded yet.")
        else:
            for i, e in enumerate(hm.entries, 1):
                yt_status = f" -> YT: {e['yt_url']}" if e.get("yt_url") else ""
                print(f"{i:2d}. {e['color']} {e['car']} ({e['output_file']}){yt_status}")
        print("=" * 50 + "\n")
        return

    if args.clean:
        from history_manager import HistoryManager
        hm = HistoryManager()
        hm.sync_from_prompts_state(pm)
        count = hm.clean_queue_duplicates(pm)
        print(f"Purged {count} duplicate pending prompts from queue.")
        print_status(pm)
        return

    if args.retry:
        count = pm.retry_failed()
        print(f"Reset {count} failed/processing prompts back to Pending.")

    if args.upload_yt and not args.run:
        from yt_uploader import YouTubeUploader
        uploader = YouTubeUploader()
        print("\nChecking for completed videos to upload to YouTube Shorts...")
        results = uploader.auto_upload_completed_videos(
            privacy_status=args.privacy,
            use_daily_slots=args.daily_slots,
            schedule_interval_hours=args.schedule_interval,
            pm=pm,
        )
        if results:
            print(f"[SUCCESS] Processed {len(results)} videos for YouTube Shorts:")
            for r in results:
                sched = f" (Scheduled: {r['publish_at']})" if r.get('publish_at') else ""
                print(f"- {r['title']} -> {r['url']}{sched}")
        else:
            print("No pending completed videos found for upload.")
        return

    if args.status or (not args.login and not args.run):
        print_status(pm)
        if not args.login and not args.run:
            print("Tip: Use --login to sign into Google, --run to start generation, or --upload-yt to upload videos.")
            return

    bm = BrowserManager(headless=args.headless)
    downloader = VideoDownloader()

    if args.login:
        print("\nOpening browser for Google Flow login...")
        print("Please log into your Google Account in the browser window.")
        print("Once done, close the browser or press Ctrl+C to return.\n")
        _, page = bm.start()
        bm.navigate_to_flow()
        try:
            while not page.is_closed():
                page.wait_for_timeout(2000)
        except KeyboardInterrupt:
            print("\nReturning from login session.")
        finally:
            bm.close()
        return

    if args.run:
        print("\nStarting Google Flow batch generation...")
        automation = GoogleFlowAutomation(browser_manager=bm, prompt_manager=pm, downloader=downloader)
        try:
            summary = automation.run_queue(max_items=args.limit)
            print("\nExecution finished.")
            print_status(pm)
            if args.upload_yt:
                print("\nAutomatically uploading/scheduling generated videos to YouTube Shorts...")
                from yt_uploader import YouTubeUploader
                uploader = YouTubeUploader()
                results = uploader.auto_upload_completed_videos(
                    privacy_status=args.privacy,
                    use_daily_slots=args.daily_slots,
                    schedule_interval_hours=args.schedule_interval,
                    pm=pm,
                )
                print(f"[SUCCESS] Processed {len(results)} videos for YouTube Shorts.")
        except KeyboardInterrupt:
            print("\nStopped by user.")
            automation.request_stop()
        finally:
            bm.close()


if __name__ == "__main__":
    main()

