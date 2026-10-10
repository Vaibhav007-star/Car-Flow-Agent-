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
    parser.add_argument("--headless", action="store_true", help="Force headless browser mode")

    args = parser.parse_args()
    pm = PromptManager()

    if args.add:
        item = pm.add_prompt(args.add)
        print(f"Added prompt [{item['id']}]: '{item['prompt']}'")
        return

    if args.retry:
        count = pm.retry_failed()
        print(f"Reset {count} failed/processing prompts back to Pending.")

    if args.status or (not args.login and not args.run):
        print_status(pm)
        if not args.login and not args.run:
            print("Tip: Use --login to sign into Google, or --run to start generation.")
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
        except KeyboardInterrupt:
            print("\nStopped by user.")
            automation.request_stop()
        finally:
            bm.close()


if __name__ == "__main__":
    main()

