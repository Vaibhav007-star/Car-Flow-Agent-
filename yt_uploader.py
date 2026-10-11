"""YouTube Automation Uploader Module.
Handles OAuth2 authentication and direct video upload to YouTube Shorts
using the official YouTube Data API v3.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import BASE_DIR, LOGS_DIR, OUTPUT_DIR
from prompt_manager import PromptManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flow_automation.yt_uploader")

# YouTube Upload OAuth Scope
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "token.json"


class YouTubeUploader:
    """Manages YouTube authentication and automated Shorts uploads."""

    def __init__(self, client_secrets_file: Path = CLIENT_SECRETS_FILE, token_file: Path = TOKEN_FILE):
        self.client_secrets_file = Path(client_secrets_file)
        self.token_file = Path(token_file)
        self.credentials: Optional[Credentials] = None
        self.youtube = None

    def authenticate(self) -> Any:
        """Authenticates with YouTube API.

        Reuses token.json if valid; launches one-time browser login flow if needed.
        """
        if self.token_file.exists():
            try:
                self.credentials = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                logger.warning(f"Could not load existing token: {e}")
                self.credentials = None

        # If no valid credentials, perform OAuth flow
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                logger.info("Refreshing expired YouTube access token...")
                try:
                    self.credentials.refresh(Request())
                except Exception:
                    self.credentials = None

            if not self.credentials:
                if not self.client_secrets_file.exists():
                    raise FileNotFoundError(
                        f"Missing client_secrets.json at {self.client_secrets_file}. "
                        "Please download OAuth Client ID credentials from Google Cloud Console."
                    )

                logger.info("Opening browser for one-time YouTube OAuth authorization...")
                flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secrets_file), SCOPES)
                self.credentials = flow.run_local_server(port=0)

            # Save the credentials for subsequent runs
            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(self.credentials.to_json())
            logger.info(f"Saved permanent credentials to {self.token_file}")

        self.youtube = build("youtube", "v3", credentials=self.credentials)
        return self.youtube

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        privacy_status: str = "public",
        publish_at: Optional[str] = None,
        schedule_in_hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Uploads a video to YouTube with Shorts optimization.

        Args:
            video_path: Path to .mp4 video file.
            title: Video title (should contain #Shorts).
            description: Video description.
            tags: List of search keywords.
            privacy_status: 'public', 'unlisted', or 'private'.
            publish_at: ISO 8601 UTC string (e.g. '2026-10-11T18:00:00Z').
            schedule_in_hours: Number of hours from now to automatically schedule release.
        """
        if not self.youtube:
            self.authenticate()

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at {video_path}")

        # Compute publish_at from relative hours if requested
        if schedule_in_hours and schedule_in_hours > 0:
            scheduled_dt = datetime.now(timezone.utc) + timedelta(hours=schedule_in_hours)
            publish_at = scheduled_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Ensure #Shorts is present in title for algorithm pickup
        clean_title = title.strip()
        if "#shorts" not in clean_title.lower():
            clean_title = f"{clean_title[:85]} #Shorts"
        clean_title = clean_title[:100]

        default_tags = ["Shorts", "car customization", "ASMR car", "miniature car", "supercars", "diegetic ASMR"]
        all_tags = list(set((tags or []) + default_tags))

        status_body: Dict[str, Any] = {
            "selfDeclaredMadeForKids": False,
        }

        if publish_at:
            # YouTube API strictly requires privacyStatus='private' when scheduling via publishAt
            status_body["privacyStatus"] = "private"
            status_body["publishAt"] = publish_at
            upload_mode = f"Scheduled for {publish_at}"
        else:
            status_body["privacyStatus"] = privacy_status
            upload_mode = f"Privacy: {privacy_status}"

        body = {
            "snippet": {
                "title": clean_title,
                "description": description,
                "tags": all_tags,
                "categoryId": "2",  # 2 = Autos & Vehicles
            },
            "status": status_body,
        }

        media = MediaFileUpload(str(video_path), chunksize=2 * 1024 * 1024, resumable=True, mimetype="video/mp4")
        logger.info(f"Initiating upload for '{video_path.name}' to YouTube ({upload_mode})...")

        request = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                logger.info(f"Upload progress: {percent}%")

        video_id = response.get("id")
        shorts_url = f"https://youtube.com/shorts/{video_id}"
        logger.info(f"Successfully uploaded! Video ID: {video_id} -> {shorts_url} ({upload_mode})")

        return {
            "video_id": video_id,
            "url": shorts_url,
            "title": clean_title,
            "privacy_status": status_body["privacyStatus"],
            "publish_at": publish_at,
        }

    def auto_upload_completed_videos(
        self,
        privacy_status: str = "public",
        schedule_interval_hours: Optional[float] = None,
        pm: Optional[PromptManager] = None,
    ) -> List[Dict[str, Any]]:
        """Scans prompt state for completed videos that haven't been uploaded yet, and uploads or schedules them."""
        manager = pm or PromptManager()
        uploaded_results = []
        unuploaded_count = 0

        for item in manager.items:
            output_file = item.get("output_file")
            already_uploaded = item.get("yt_uploaded", False)

            if item.get("status") == "Completed" and output_file and not already_uploaded:
                full_path = OUTPUT_DIR / output_file
                if full_path.exists():
                    prompt_text = item.get("prompt", "")

                    # Extract car name from prompt for clean title
                    title = f"Customizing {output_file.replace('video_', '').replace('.mp4', '').replace('_', ' ').title()} ASMR #Shorts"
                    desc = (
                        f"{prompt_text}\n\n"
                        "🎧 Wear headphones for the best ASMR experience.\n"
                        "#Shorts #ASMR #CarCustomization #ViralCars #Supercars"
                    )

                    # Compute staggered schedule if requested
                    sched_hours = None
                    if schedule_interval_hours and schedule_interval_hours > 0:
                        sched_hours = (unuploaded_count + 1) * schedule_interval_hours

                    try:
                        res = self.upload_short(
                            full_path,
                            title=title,
                            description=desc,
                            privacy_status=privacy_status,
                            schedule_in_hours=sched_hours,
                        )
                        item["yt_uploaded"] = True
                        item["yt_video_id"] = res["video_id"]
                        item["yt_url"] = res["url"]
                        if res.get("publish_at"):
                            item["yt_publish_at"] = res["publish_at"]
                        manager.save()
                        uploaded_results.append(res)
                        unuploaded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to auto-upload {full_path.name}: {e}")

        return uploaded_results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Shorts Auto-Uploader & Scheduler")
    parser.add_argument("--auth", action="store_true", help="Run one-time YouTube OAuth authorization")
    parser.add_argument("--upload", type=str, help="Upload a specific video file path")
    parser.add_argument("--title", type=str, default="Viral Miniature Car Assembly ASMR", help="Video title")
    parser.add_argument("--privacy", type=str, default="public", choices=["public", "unlisted", "private"], help="Privacy status (default public)")
    parser.add_argument("--schedule-in-hours", type=float, help="Schedule release N hours from now (e.g. 2 or 5.5)")
    parser.add_argument("--schedule-at", type=str, help="Schedule release at specific UTC timestamp (YYYY-MM-DDTHH:MM:SSZ)")
    parser.add_argument("--schedule-interval", type=float, help="Stagger scheduled batch uploads by N hours apart")
    parser.add_argument("--all", action="store_true", help="Upload all un-uploaded completed videos from queue")

    args = parser.parse_args()
    uploader = YouTubeUploader()

    if args.auth:
        print("\nStarting one-time YouTube authorization...")
        uploader.authenticate()
        print("[SUCCESS] YouTube authorization completed and token.json saved!\n")
        return

    if args.upload:
        p = Path(args.upload)
        res = uploader.upload_short(
            p,
            title=args.title,
            description="Generated via Google Flow",
            privacy_status=args.privacy,
            publish_at=args.schedule_at,
            schedule_in_hours=args.schedule_in_hours,
        )
        if res.get("publish_at"):
            print(f"[SUCCESS] Uploaded and SCHEDULED for {res['publish_at']}: {res['url']}")
        else:
            print(f"[SUCCESS] Uploaded to YouTube Shorts ({res['privacy_status']}): {res['url']}")
        return

    if args.all:
        print("\nChecking for completed videos to upload...")
        results = uploader.auto_upload_completed_videos(
            privacy_status=args.privacy,
            schedule_interval_hours=args.schedule_interval,
        )
        print(f"[SUCCESS] Processed {len(results)} videos.")
        for r in results:
            sched = f" (Scheduled: {r['publish_at']})" if r.get('publish_at') else ""
            print(f"- {r['title']} -> {r['url']}{sched}")
        return

    # Default action
    uploader.authenticate()
    print("[SUCCESS] Connected to YouTube API.")


if __name__ == "__main__":
    main()
