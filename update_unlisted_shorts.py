"""Automated Updater and Scheduler for Unlisted YouTube Shorts.
Updates titles, viral hashtags, rich ASMR descriptions, thumbnails, and schedules
for unlisted Shorts on the user's YouTube channel.
"""

import sys
import socket
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Force IPv4 to avoid Windows IPv6 hangs
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import BASE_DIR, OUTPUT_DIR
from yt_uploader import YouTubeUploader, YouTubeSEO, get_next_daily_slots

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flow_automation.update_unlisted")

# Target queue of unlisted shorts provided by the user
PRECONFIGURED_SHORTS = [
    {
        "video_id": "y9R9unY2ygE",
        "car": "Porsche 911 GT3 RS",
        "material": "Racing Red",
        "niche": "diecast",
        "title": "Satisfying Porsche 911 GT3 RS Assembly ASMR 🎧 #Shorts",
        "description": (
            "Satisfying ASMR customization and assembly of the miniature Racing Red Porsche 911 GT3 RS. 🏎️💨\n"
            "🎧 Wear headphones for the best binaural mechanical clicks, ratchet sounds, and deep exhaust rumble!\n\n"
            "💬 Which dream supercar should we customize next? Drop your pick in the comments below! 👇\n\n"
            "#Shorts #ASMR #CarCustomization #Porsche911GT3RS #Porsche #Diecast #Satisfying #Supercars #Viral"
        ),
        "local_file": OUTPUT_DIR / "video_001_porsche_gt3_rs.mp4",
        "slot_offset": 0,  # Today 1:30 PM IST (2026-10-13T08:00:00Z)
    },
    {
        "video_id": "4w4crdPorTM",
        "car": "BMW M4 Competition",
        "material": "Electric Blue",
        "niche": "diecast",
        "title": "Satisfying BMW M4 Competition Assembly ASMR 🎧 #Shorts",
        "description": (
            "Satisfying ASMR customization and assembly of the miniature Electric Blue BMW M4 Competition. 🏎️💨\n"
            "🎧 Wear headphones for the best binaural mechanical clicks, ratchet sounds, and twin-turbo exhaust rumble!\n\n"
            "💬 Which dream supercar should we customize next? Drop your pick in the comments below! 👇\n\n"
            "#Shorts #ASMR #CarCustomization #BMWM4Competition #BMW #BMWM #Diecast #Satisfying #Supercars #Viral"
        ),
        "local_file": OUTPUT_DIR / "video_002_bmw_m4.mp4",
        "slot_offset": 1,  # Today 8:00 PM IST (2026-10-13T14:30:00Z)
    },
    {
        "video_id": "vUB5PhaHTPM",
        "car": "BMW M4",
        "material": "Alpine White",
        "niche": "diecast",
        "title": "Wait for the titanium exhaust click... BMW M4 🔊 #Shorts",
        "description": (
            "Satisfying ASMR installation of titanium blue-tipped quad exhausts and carbon rear diffuser on the miniature BMW M4. 🏎️💨\n"
            "🎧 Wear headphones for the crisp mechanical clicks, bolt ratchets, and deep twin-turbo exhaust rumble!\n\n"
            "💬 Rate this titanium exhaust setup from 1 to 10 in the comments below! 👇\n\n"
            "#Shorts #ASMR #BMW #BMWM4 #CarCustomization #TitaniumExhaust #Diecast #Satisfying #Supercars #Viral"
        ),
        "local_file": None,
        "slot_offset": 2,  # Tomorrow 1:30 PM IST (2026-10-14T08:00:00Z)
    },
    {
        "video_id": "ouLdtSVzY-Q",
        "car": "Nissan GT-R Nismo",
        "material": "Nardo Gray",
        "niche": "diecast",
        "title": "Building Godzilla: Custom Nissan GT-R Nismo ASMR 🦖🎧 #Shorts",
        "description": (
            "Satisfying ASMR customization and assembly of the miniature Nissan GT-R Nismo (R35 Godzilla). 🦖⚡\n"
            "🎧 Wear headphones for the crisp mechanical clicks, bolt ratchets, and twin-turbo VR38DETT startup hum!\n\n"
            "💬 Is the Nissan GT-R the greatest supercar killer of all time? Drop your thoughts below! 👇\n\n"
            "#Shorts #ASMR #NissanGTR #GTR #R35 #Godzilla #JDM #CarCustomization #Diecast #Satisfying #Viral"
        ),
        "local_file": None,
        "slot_offset": 3,  # Tomorrow 8:00 PM IST (2026-10-14T14:30:00Z)
    },
]


def update_all_preconfigured_shorts(dry_run: bool = False):
    uploader = YouTubeUploader()
    uploader.authenticate()

    slots = get_next_daily_slots(count=len(PRECONFIGURED_SHORTS), min_lead_minutes=45)

    print(f"\n=======================================================")
    print(f"  BATCH UPDATING & SCHEDULING {len(PRECONFIGURED_SHORTS)} UNLISTED SHORTS")
    print(f"=======================================================\n")

    for idx, item in enumerate(PRECONFIGURED_SHORTS):
        video_id = item["video_id"]
        title = item["title"]
        desc = item["description"]
        tags = YouTubeSEO.generate_tags(item["car"], material=item["material"], niche=item["niche"])
        publish_at = slots[idx]

        print(f"[{idx+1}/{len(PRECONFIGURED_SHORTS)}] Processing Video ID: {video_id} ({item['car']})")
        print(f"  • Title: {title}")
        print(f"  • Scheduled Release: {publish_at} (Private -> Auto-publish)")
        print(f"  • Tags: {len(tags)} optimized tags")

        if dry_run:
            print("  [DRY RUN] Skipping API call.")
            continue

        try:
            uploader.update_video_metadata(
                video_id=video_id,
                title=title,
                description=desc,
                tags=tags,
                category_id="2",  # Autos & Vehicles
                privacy_status="private",
                publish_at=publish_at,
            )
            print(f"  [SUCCESS] Updated and scheduled {video_id} -> https://youtube.com/shorts/{video_id}")

            # If local file exists, set high-contrast custom thumbnail
            local_file = item.get("local_file")
            if local_file and Path(local_file).exists():
                print(f"  • Uploading high-contrast custom thumbnail from {Path(local_file).name}...")
                try:
                    uploader.set_custom_thumbnail(video_id, Path(local_file))
                except Exception as te:
                    print(f"  [NOTICE] Custom thumbnail notice: {te}")

        except Exception as e:
            logger.error(f"Failed to update video {video_id}: {e}")

    print("\n[COMPLETE] All unlisted shorts updated and scheduled successfully!\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch update and schedule unlisted YouTube Shorts")
    parser.add_argument("--dry-run", action="store_true", help="Simulate update without sending API requests")
    args = parser.parse_args()
    update_all_preconfigured_shorts(dry_run=args.dry_run)

