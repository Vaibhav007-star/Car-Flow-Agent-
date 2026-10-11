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
# Daily Peak Slots in UTC:
# Slot 1: 1:30 PM IST = 08:00 UTC
# Slot 2: 8:00 PM IST = 14:30 UTC
DAILY_SLOTS_UTC = [(8, 0), (14, 30)]


def get_next_daily_slots(count: int = 1, min_lead_minutes: int = 45) -> List[str]:
    """Computes upcoming target ISO 8601 timestamps matching the 2 daily peak slots (1:30 PM & 8:00 PM IST).
    
    Guarantees at least min_lead_minutes buffer from now to ensure YouTube has processing headroom.
    """
    now_utc = datetime.now(timezone.utc)
    slots: List[str] = []
    day_offset = 0

    while len(slots) < count:
        target_day = (now_utc + timedelta(days=day_offset)).date()
        for hour, minute in DAILY_SLOTS_UTC:
            candidate = datetime(target_day.year, target_day.month, target_day.day, hour, minute, tzinfo=timezone.utc)
            if candidate > now_utc + timedelta(minutes=min_lead_minutes):
                slots.append(candidate.strftime("%Y-%m-%dT%H:%M:%SZ"))
                if len(slots) == count:
                    break
        day_offset += 1

    return slots


class YouTubeSEO:
    """Generates high-CTR viral titles, rich SEO descriptions, and high-ranking tags for YouTube Shorts."""

    LOCKED_COLORS = [
        "Racing Red", "Electric Blue", "Midnight Purple", "Sunset Orange",
        "Emerald Green", "Frozen Silver", "Solar Yellow", "Gloss White",
        "Matte Carbon", "Candy Apple Red",
    ]

    VIRAL_HOOKS = [
        "Satisfying {car} Assembly ASMR 🎧 #Shorts",
        "Rate this {car} build 1-10? 🔥 #Shorts",
        "Wait for the exhaust sound... {car} 🔊 #Shorts",
        "Building the Ultimate {color} {car} in 8s ⚡ #Shorts",
        "The Most Satisfying {car} Build Ever 🤤 #Shorts",
    ]

    @classmethod
    def extract_car_and_color(cls, prompt: str = "", filename: str = "") -> tuple[str, str]:
        """Extracts clean car name and color from prompt text or filename."""
        matched_color = "Custom"
        car_name = ""

        if prompt:
            import re
            m = re.search(r"A miniature (.*?) in a spotless", prompt, re.IGNORECASE)
            if m:
                target_str = m.group(1).strip()
                for c in cls.LOCKED_COLORS:
                    if target_str.lower().startswith(c.lower()):
                        matched_color = c
                        car_name = target_str[len(c):].strip()
                        break
                if not car_name:
                    car_name = target_str

        if not car_name and filename:
            clean_stem = Path(filename).stem
            parts = clean_stem.replace("video_", "").split("_")
            car_parts = [p for p in parts if not p.isdigit()]
            car_name = " ".join(car_parts).title()

        car_name = car_name or "Supercar"
        return car_name, matched_color

    @classmethod
    def generate_title(cls, car_name: str, color: str = "", variant_idx: Optional[int] = None) -> str:
        """Generates a viral hook title under 85 characters with #Shorts."""
        if variant_idx is None:
            variant_idx = abs(hash(car_name)) % len(cls.VIRAL_HOOKS)
        else:
            variant_idx = variant_idx % len(cls.VIRAL_HOOKS)

        template = cls.VIRAL_HOOKS[variant_idx]
        title = template.format(car=car_name, color=color or "Custom")
        if "#shorts" not in title.lower():
            title = f"{title} #Shorts"
        return title[:95]

    @classmethod
    def generate_description(cls, car_name: str, color: str = "", prompt: str = "") -> str:
        """Generates high-retention SEO description with timestamps, CTA, and keyword hashtags."""
        car_tag = car_name.replace(" ", "").replace("-", "")
        desc = (
            f"Satisfying ASMR customization and assembly of the miniature {color} {car_name}.\n"
            f"🎧 Wear headphones for the best binaural mechanical clicks, ratchet sounds, and exhaust rumble!\n\n"
            f"💬 Which dream supercar should we customize next? Drop your pick in the comments below! 👇\n\n"
            f"#Shorts #ASMR #CarCustomization #{car_tag} #Diecast #Satisfying #Supercars #Viral"
        )
        return desc

    @classmethod
    def generate_tags(cls, car_name: str, color: str = "") -> List[str]:
        """Generates ranked tag cluster targeting high search volume and Shorts feed velocity."""
        clean_car = car_name.strip()
        brand = clean_car.split()[0] if clean_car else ""
        car_tag = clean_car.replace(" ", "")

        candidates = [
            "Shorts",
            "YouTube Shorts",
            "viral shorts",
            "satisfying",
            "oddly satisfying",
            "ASMR",
            "car ASMR",
            "car customization",
            "miniature car",
            "miniature car assembly",
            "diecast car",
            "diecast restoration",
            "diecast customization",
            "custom car build",
            "exhaust sound",
            "engine startup",
            "supercars",
            "hypercar",
            clean_car,
            f"{clean_car} ASMR",
            f"{clean_car} sound",
            brand,
            car_tag,
        ]
        if color:
            candidates.append(f"{color} {clean_car}")

        seen = set()
        final_tags = []
        for t in candidates:
            tc = t.strip()
            if tc and tc.lower() not in seen:
                seen.add(tc.lower())
                final_tags.append(tc)
        return final_tags


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
        use_daily_slots: bool = False,
        schedule_interval_hours: Optional[float] = None,
        pm: Optional[PromptManager] = None,
    ) -> List[Dict[str, Any]]:
        """Scans prompt state for completed videos that haven't been uploaded yet, and uploads or schedules them.
        
        Uses YouTubeSEO for high-ranking titles, descriptions, and tag clusters.
        """
        manager = pm or PromptManager()
        uploaded_results = []
        unuploaded_count = 0

        # Count pending videos to allocate daily slots if requested
        pending_items = [
            it for it in manager.items
            if it.get("status") == "Completed" and it.get("output_file") and not it.get("yt_uploaded", False)
        ]
        
        daily_slot_timestamps: List[str] = []
        if use_daily_slots and pending_items:
            daily_slot_timestamps = get_next_daily_slots(count=len(pending_items))

        for item in manager.items:
            output_file = item.get("output_file")
            already_uploaded = item.get("yt_uploaded", False)

            if item.get("status") == "Completed" and output_file and not already_uploaded:
                full_path = OUTPUT_DIR / output_file
                if full_path.exists():
                    prompt_text = item.get("prompt", "")

                    # Extract car and color, then generate dynamic SEO metadata
                    car_name, color = YouTubeSEO.extract_car_and_color(prompt_text, full_path.name)
                    title = YouTubeSEO.generate_title(car_name, color, variant_idx=unuploaded_count)
                    desc = YouTubeSEO.generate_description(car_name, color, prompt_text)
                    tags = YouTubeSEO.generate_tags(car_name, color)

                    # Determine schedule target
                    sched_hours = None
                    target_publish_at = None

                    if use_daily_slots and unuploaded_count < len(daily_slot_timestamps):
                        target_publish_at = daily_slot_timestamps[unuploaded_count]
                    elif schedule_interval_hours and schedule_interval_hours > 0:
                        sched_hours = (unuploaded_count + 1) * schedule_interval_hours

                    try:
                        res = self.upload_short(
                            full_path,
                            title=title,
                            description=desc,
                            tags=tags,
                            privacy_status=privacy_status,
                            publish_at=target_publish_at,
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
    parser.add_argument("--title", type=str, help="Video title (auto-generated if omitted)")
    parser.add_argument("--privacy", type=str, default="public", choices=["public", "unlisted", "private"], help="Privacy status (default public)")
    parser.add_argument("--schedule-in-hours", type=float, help="Schedule release N hours from now (e.g. 2 or 5.5)")
    parser.add_argument("--schedule-at", type=str, help="Schedule release at specific UTC timestamp (YYYY-MM-DDTHH:MM:SSZ)")
    parser.add_argument("--daily-slots", action="store_true", help="Schedule to next 2 daily peak slots (1:30 PM & 8:00 PM IST)")
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
        car_name, color = YouTubeSEO.extract_car_and_color("", p.name)
        title = args.title or YouTubeSEO.generate_title(car_name, color)
        desc = YouTubeSEO.generate_description(car_name, color)
        tags = YouTubeSEO.generate_tags(car_name, color)

        publish_target = args.schedule_at
        if args.daily_slots:
            publish_target = get_next_daily_slots(count=1)[0]

        res = uploader.upload_short(
            p,
            title=title,
            description=desc,
            tags=tags,
            privacy_status=args.privacy,
            publish_at=publish_target,
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
            use_daily_slots=args.daily_slots,
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
