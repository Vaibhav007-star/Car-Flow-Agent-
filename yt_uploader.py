"""YouTube Automation Uploader Module.
Handles OAuth2 authentication and direct video upload to YouTube Shorts
using the official YouTube Data API v3.
"""

import os
import sys
import json
import socket
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

# Force IPv4 resolution to prevent Windows IPv6 timeout hangs on Google APIs
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import BASE_DIR, LOGS_DIR, OUTPUT_DIR
from prompt_manager import PromptManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flow_automation.yt_uploader")

# YouTube Upload & Management OAuth Scope
SCOPES = ["https://www.googleapis.com/auth/youtube"]
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
    """Generates high-CTR viral titles, rich SEO descriptions, and high-ranking tags for YouTube Shorts across niches."""

    DIECAST_HOOKS = [
        "Satisfying {car} Assembly ASMR 🎧 #Shorts",
        "Rate this {car} build 1-10? 🔥 #Shorts",
        "Wait for the exhaust sound... {car} 🔊 #Shorts",
        "Building the Ultimate {material} {car} in 8s ⚡ #Shorts",
        "The Most Satisfying {car} Build Ever 🤤 #Shorts",
    ]

    WOODEN_HOOKS = [
        "Handcrafting a {material} {car} ASMR 🪵🎧 #Shorts",
        "Rate this wooden {car} carving 1-10? 🔥 #Shorts",
        "Carving the Ultimate {car} from {material} 🪚 #Shorts",
        "Listen to the wood carving sound... {car} 🔊 #Shorts",
        "The Most Satisfying Wooden {car} Build 🤤 #Shorts",
    ]

    MODEL_KIT_HOOKS = [
        "Unboxing & Building a {car} in 8s 📦⚡ #Shorts",
        "The Most Satisfying {car} Model Kit Build 🤤 #Shorts",
        "Unboxing the Ultimate {material} {car} Model Kit 📦🎧 #Shorts",
        "Wait for the headlights to turn on... {car} 💡 #Shorts",
        "Rate this miniature {car} build 1-10? 🔥 #Shorts",
    ]

    PEEL_HOOKS = [
        "{car}: Satisfying ASMR Factory Film Peel & Startup! 🎧🔥 #Shorts",
        "{car}: Unpeeling the {material} Monster in 8s ⚡ #Shorts",
        "{car}: Most Satisfying Protective Peel & Push-to-Start 🤤 #Shorts",
        "Wait for the angel-eyes to light up... {car} 💡 #Shorts",
        "Rate this {car} ASMR factory delivery peel 1-10? 🔥 #Shorts",
    ]

    FOAM_HOOKS = [
        "Carving a Realistic Sedan from Styrofoam! 🪚🤤 #Shorts",
        "Satisfying Styrofoam Car Crafting ASMR 🎧🔥 #Shorts",
        "The Most Satisfying Styrofoam Car Build Ever! 🎧✨ #Shorts",
        "Listen to the foam carving sound... 🔊🤍 #Shorts",
        "Rate this Styrofoam car carving 1-10? 🔥 #Shorts",
    ]

    OVERLAND_HOOKS = [
        "Transforming a Microvan into a Rugged 4x4 Off-Roader! 🛞🔥 #Shorts",
        "The Ultimate 4x4 Overland Microvan Build in 8s! ⚡ #Shorts",
        "Rate this Lifted 4x4 Microvan Makeover 1-10? 🔥 #Shorts",
        "Wait for the LED light bar reveal... 4x4 Overlander 💡 #Shorts",
        "Building a Tiny 4x4 Off-Road Monster! 🛞🤤 #Shorts",
    ]

    KINETIC_HOOKS = [
        "Pushing the Button on a Desk Toy... Transforms into a 4x4! 🤯 #Shorts",
        "The Most Satisfying Kinetic Gadget Car Transformation 🤤 #Shorts",
        "Wait for the LED headlights to turn on... {car} 💡 #Shorts",
        "Mechanical Desk Toy to {car} in 8s! ⚡ #Shorts",
        "Rate this kinetic {car} transformation 1-10? 🔥 #Shorts",
    ]

    @classmethod
    def extract_metadata(cls, prompt: str = "", filename: str = "") -> tuple[str, str, str]:
        """Extracts (car_name, niche, material) from prompt text or filename."""
        from history_manager import HistoryManager
        return HistoryManager.parse_car_niche_and_material(prompt, filename)

    @classmethod
    def extract_car_and_color(cls, prompt: str = "", filename: str = "") -> tuple[str, str]:
        """Backwards-compatibility extraction returning (car_name, material)."""
        car_name, _, material = cls.extract_metadata(prompt, filename)
        return car_name, material

    @classmethod
    def generate_title(cls, car_name: str, material: str = "", niche: str = "diecast", variant_idx: Optional[int] = None) -> str:
        """Generates a viral hook title under 95 characters with #Shorts."""
        niche_lower = niche.lower()
        if niche_lower == "wooden":
            hooks = cls.WOODEN_HOOKS
        elif niche_lower in ("model_kit", "modelkit", "unboxing"):
            hooks = cls.MODEL_KIT_HOOKS
        elif niche_lower in ("peel", "delivery", "peel_and_delivery"):
            hooks = cls.PEEL_HOOKS
        elif niche_lower in ("foam", "styrofoam", "craft"):
            hooks = cls.FOAM_HOOKS
        elif niche_lower in ("overland", "overlander", "restomod", "microvan"):
            hooks = cls.OVERLAND_HOOKS
        elif niche_lower in ("kinetic", "gadget", "transformation"):
            hooks = cls.KINETIC_HOOKS
        else:
            hooks = cls.DIECAST_HOOKS

        if variant_idx is None:
            variant_idx = abs(hash(car_name)) % len(hooks)
        else:
            variant_idx = variant_idx % len(hooks)

        template = hooks[variant_idx]
        title = template.format(car=car_name, material=material or "Custom", color=material or "Custom")
        if "#shorts" not in title.lower():
            title = f"{title} #Shorts"
        return title[:95]

    @classmethod
    def generate_description(cls, car_name: str, material: str = "", prompt: str = "", niche: str = "diecast") -> str:
        """Generates high-retention SEO description tailored to the niche."""
        car_tag = car_name.replace(" ", "").replace("-", "")
        niche_lower = niche.lower()
        if niche_lower == "wooden":
            desc = (
                f"Satisfying macro ASMR woodworking and hand carving of the miniature {material} {car_name}.\n"
                f"🎧 Wear headphones for the best binaural wood carving scrapes, sanding friction, and tactile wooden taps!\n\n"
                f"💬 Which dream car should we carve from wood next? Drop your pick in the comments below! 👇\n\n"
                f"#Shorts #ASMR #Woodworking #CarCarving #Handmade #{car_tag} #WoodArt #Satisfying #Viral"
            )
        elif niche_lower in ("model_kit", "modelkit", "unboxing"):
            desc = (
                f"Satisfying unboxing & precision assembly of the miniature {material} {car_name} model kit. 📦🏎️\n"
                f"🎧 Wear headphones for the best binaural cardboard unboxing, micro-ratchet bolt clicks, and engine startup hum!\n\n"
                f"💬 Which iconic supercar model kit should we build next? Drop your pick in the comments below! 👇\n\n"
                f"#Shorts #ASMR #ModelKit #Unboxing #CarBuild #{car_tag} #MiniatureCar #Satisfying #Supercars #Viral"
            )
        elif niche_lower in ("peel", "delivery", "peel_and_delivery"):
            desc = (
                f"Satisfying ASMR protective transit film peel, precision detail, and push-to-start ignition of the miniature {material} {car_name}. 🏎️✨\n"
                f"🎧 Wear headphones for the best binaural vinyl peel hiss, door latch click, and quad angel-eye LED headlight startup hum!\n\n"
                f"💬 Which dream supercar should we unpeel and deliver next? Drop your pick in the comments below! 👇\n\n"
                f"#Shorts #ASMR #CarUnboxing #BMW #M4Competition #{car_tag} #Satisfying #Supercars #Viral"
            )
        elif niche_lower in ("foam", "styrofoam", "craft"):
            desc = (
                f"Satisfying macro ASMR hand carving of a realistic white Styrofoam {car_name}. 🪚🤍\n"
                f"🎧 Wear headphones for the best binaural razor blade foam slicing, sandpaper friction, and soft brush strokes!\n\n"
                f"💬 Which vehicle should we carve from Styrofoam next? Drop your pick in the comments below! 👇\n\n"
                f"#Shorts #ASMR #Styrofoam #Carving #DIYCraft #CarBuild #Satisfying #Handmade #Viral #{car_tag}"
            )
        elif niche_lower in ("overland", "overlander", "restomod", "microvan"):
            desc = (
                f"Satisfying custom garage transformation of a white {car_name} into a rugged lifted 4x4 off-roader! 🛞🔥\n"
                f"🎧 Wear headphones for the best binaural impact-driver whirrs, socket clicks, and tire thuds!\n\n"
                f"💬 Which vehicle should we turn into a 4x4 overland monster next? Drop your pick below! 👇\n\n"
                f"#Shorts #Overlanding #4x4 #Microvan #CustomCar #OffRoad #CarBuild #Satisfying #Viral"
            )
        elif niche_lower in ("kinetic", "gadget", "transformation"):
            desc = (
                f"Satisfying sci-fi kinetic desk toy transformation into a miniature {material} {car_name}! 🤖✨\n"
                f"🎧 Wear headphones for the best binaural button clicks, spring snaps, and servo hums!\n\n"
                f"💬 Which vehicle should our kinetic desk gadget transform into next? Drop your pick below! 👇\n\n"
                f"#Shorts #ASMR #KineticToy #DeskToy #Gadget #Transformers #{car_tag} #Satisfying #Viral"
            )
        else:
            desc = (
                f"Satisfying ASMR customization and assembly of the miniature {material} {car_name}.\n"
                f"🎧 Wear headphones for the best binaural mechanical clicks, ratchet sounds, and exhaust rumble!\n\n"
                f"💬 Which dream supercar should we customize next? Drop your pick in the comments below! 👇\n\n"
                f"#Shorts #ASMR #CarCustomization #{car_tag} #Diecast #Satisfying #Supercars #Viral"
            )
        return desc

    @classmethod
    def generate_tags(cls, car_name: str, material: str = "", niche: str = "diecast") -> List[str]:
        """Generates ranked tag cluster targeting high search volume and Shorts feed velocity."""
        clean_car = car_name.strip()
        brand = clean_car.split()[0] if clean_car else ""
        car_tag = clean_car.replace(" ", "")

        if niche.lower() == "wooden":
            candidates = [
                "Shorts",
                "YouTube Shorts",
                "viral shorts",
                "satisfying",
                "oddly satisfying",
                "ASMR",
                "woodworking",
                "wood carving",
                "wood carving ASMR",
                "woodworking ASMR",
                "car carving",
                "wooden car",
                "handmade wooden car",
                "wood art",
                "chisel ASMR",
                "sanding ASMR",
                "tactile ASMR",
                clean_car,
                f"{clean_car} build",
                f"{clean_car} wooden",
                f"{material} wood",
                f"{brand} car",
                car_tag,
                "binaural ASMR",
                "relaxing woodworking",
            ]
        elif niche.lower() in ("model_kit", "modelkit", "unboxing"):
            candidates = [
                "Shorts",
                "YouTube Shorts",
                "viral shorts",
                "satisfying",
                "oddly satisfying",
                "ASMR",
                "model kit",
                "unboxing",
                "model car",
                "car model kit",
                "miniature car",
                "scale model",
                "precision build",
                "time lapse build",
                clean_car,
                f"{clean_car} model",
                f"{clean_car} build",
                f"{brand} model kit",
                car_tag,
                "diegetic ASMR",
                "binaural sound",
            ]
        elif niche.lower() in ("peel", "delivery", "peel_and_delivery"):
            candidates = [
                "Shorts",
                "YouTube Shorts",
                "viral shorts",
                "satisfying",
                "oddly satisfying",
                "ASMR",
                "peel ASMR",
                "unboxing",
                "car unboxing",
                "delivery peel",
                "miniature car",
                "scale model",
                "push to start",
                "startup sound",
                clean_car,
                f"{clean_car} build",
                f"{clean_car} ASMR",
                f"{brand} M4",
                car_tag,
                "binaural ASMR",
                "satisfying video",
            ]
        elif niche.lower() in ("foam", "styrofoam", "craft"):
            candidates = [
                "Shorts",
                "YouTube Shorts",
                "viral shorts",
                "satisfying",
                "oddly satisfying",
                "ASMR",
                "foam carving",
                "styrofoam carving",
                "foam craft",
                "car carving",
                "DIY craft",
                "handmade car",
                "scalpel carving",
                "sandpaper ASMR",
                "satisfying carving",
                "binaural ASMR",
                "relaxing ASMR",
                "miniature car",
                "sculpture",
                car_tag,
            ]
        elif niche.lower() in ("overland", "overlander", "restomod", "microvan"):
            candidates = [
                "Shorts",
                "YouTube Shorts",
                "viral shorts",
                "satisfying",
                "oddly satisfying",
                "ASMR",
                "overlanding",
                "4x4 build",
                "custom car",
                "car restomod",
                "microvan",
                "suzuki microvan",
                "off road",
                "lifted 4x4",
                "car makeover",
                "impact driver ASMR",
                "time lapse build",
                clean_car,
                f"{clean_car} 4x4",
                f"{clean_car} build",
                car_tag,
                "binaural ASMR",
            ]
        elif niche.lower() in ("kinetic", "gadget", "transformation"):
            candidates = [
                "Shorts",
                "YouTube Shorts",
                "viral shorts",
                "satisfying",
                "oddly satisfying",
                "ASMR",
                "kinetic toy",
                "desk toy",
                "gadget",
                "transformation",
                "mechanical toy",
                "spring loaded",
                "miniature car",
                "scale model",
                "diegetic ASMR",
                clean_car,
                f"{clean_car} transformation",
                f"{clean_car} build",
                car_tag,
                "binaural ASMR",
            ]
        else:
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
                "binaural ASMR",
            ]
        # Clean tags: strip any hash symbols or special characters
        sanitized = []
        for t in candidates:
            cleaned = t.replace("#", "").strip()
            if cleaned and cleaned not in sanitized:
                sanitized.append(cleaned)
        return sanitized[:25]
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
                with open(self.token_file, "r", encoding="utf-8") as f:
                    token_data = json.load(f)
                token_scopes = token_data.get("scopes", [])
                if not all(s in token_scopes for s in SCOPES):
                    logger.info("Existing token.json lacks full YouTube management scope. Re-authorizing...")
                    self.credentials = None
                else:
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
        raw_tags = (tags or []) + default_tags
        clean_tags = []
        for t in raw_tags:
            c = str(t).replace("#", "").strip()
            if c and c not in clean_tags and len(c) < 100:
                clean_tags.append(c)
        all_tags = clean_tags[:25]

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

        # Automatically extract and set the best high-engagement thumbnail
        try:
            self.set_custom_thumbnail(video_id, video_path)
        except Exception as e:
            logger.debug(f"Thumbnail set notice: {e}")

        return {
            "video_id": video_id,
            "url": shorts_url,
            "title": clean_title,
            "privacy_status": status_body["privacyStatus"],
            "publish_at": publish_at,
        }

    def set_custom_thumbnail(self, video_id: str, video_path: Path) -> Optional[Path]:
        """Extracts the highest engagement frame from the video and sets it as the custom thumbnail."""
        try:
            from thumbnail_generator import ThumbnailGenerator
            gen = ThumbnailGenerator()
            best_thumb_path, info = gen.get_best_thumbnail(video_path)

            media = MediaFileUpload(str(best_thumb_path), mimetype="image/jpeg", resumable=True)
            self.youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
            logger.info(f"Successfully set custom thumbnail on YouTube for {video_id} from {best_thumb_path.name} (timestamp: {info['timestamp']}s)")
            return best_thumb_path
        except Exception as e:
            logger.warning(f"Notice setting custom thumbnail for {video_id}: {e}")
            return None

    def update_video_metadata(
        self,
        video_id: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        category_id: str = "2",
        privacy_status: Optional[str] = None,
        publish_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Updates metadata and scheduling for an existing YouTube video."""
        if not self.youtube:
            self.authenticate()

        clean_title = title.strip()
        if "#shorts" not in clean_title.lower():
            clean_title = f"{clean_title[:85]} #Shorts"
        clean_title = clean_title[:100]

        default_tags = ["Shorts", "car customization", "ASMR car", "miniature car", "supercars", "diegetic ASMR"]
        all_tags = list(set((tags or []) + default_tags))

        part_list = ["snippet"]
        body: Dict[str, Any] = {
            "id": video_id,
            "snippet": {
                "title": clean_title,
                "description": description,
                "tags": all_tags,
                "categoryId": category_id,
            },
        }

        if privacy_status or publish_at:
            part_list.append("status")
            status_body: Dict[str, Any] = {
                "selfDeclaredMadeForKids": False,
            }
            if publish_at:
                status_body["privacyStatus"] = "private"
                status_body["publishAt"] = publish_at
            elif privacy_status:
                status_body["privacyStatus"] = privacy_status
            body["status"] = status_body

        part_str = ",".join(part_list)
        logger.info(f"Updating video {video_id} with part={part_str}...")
        resp = self.youtube.videos().update(part=part_str, body=body).execute()
        logger.info(f"Successfully updated metadata on YouTube for {video_id}!")
        return resp

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

                    # Extract car, niche, and material, then generate dynamic SEO metadata
                    car_name, niche, material = YouTubeSEO.extract_metadata(prompt_text, full_path.name)
                    title = YouTubeSEO.generate_title(car_name, material=material, niche=niche, variant_idx=unuploaded_count)
                    desc = YouTubeSEO.generate_description(car_name, material=material, prompt=prompt_text, niche=niche)
                    tags = YouTubeSEO.generate_tags(car_name, material=material, niche=niche)

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
    import sys
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

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
    parser.add_argument("--update-video", type=str, help="Update an existing YouTube video metadata/schedule by ID or URL")
    parser.add_argument("--car", type=str, help="Car name for metadata generation")
    parser.add_argument("--niche", type=str, default="diecast", choices=["diecast", "wooden"], help="Niche for metadata generation")
    parser.add_argument("--material", type=str, help="Material or color (e.g. Rich Walnut, Racing Red)")

    args = parser.parse_args()
    uploader = YouTubeUploader()

    if args.auth:
        print("\nStarting one-time YouTube authorization...")
        uploader.authenticate()
        print("[SUCCESS] YouTube authorization completed and token.json saved!\n")
        return

    if args.upload:
        p = Path(args.upload)
        car_name, niche, material = YouTubeSEO.extract_metadata("", p.name)
        title = args.title or YouTubeSEO.generate_title(car_name, material=material, niche=niche)
        desc = YouTubeSEO.generate_description(car_name, material=material, niche=niche)
        tags = YouTubeSEO.generate_tags(car_name, material=material, niche=niche)

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

    if args.update_video:
        vid = args.update_video.split("/")[-1].replace("watch?v=", "")
        car = args.car or "Supercar"
        niche = args.niche
        mat = args.material or ""
        title = args.title or YouTubeSEO.generate_title(car, material=mat, niche=niche)
        desc = YouTubeSEO.generate_description(car, material=mat, niche=niche)
        tags = YouTubeSEO.generate_tags(car, material=mat, niche=niche)

        publish_target = args.schedule_at
        if args.daily_slots:
            publish_target = get_next_daily_slots(count=1)[0]

        uploader.update_video_metadata(
            video_id=vid,
            title=title,
            description=desc,
            tags=tags,
            privacy_status="private" if publish_target else args.privacy,
            publish_at=publish_target,
        )
        sched_info = f" (Scheduled: {publish_target})" if publish_target else ""
        print(f"[SUCCESS] Updated video {vid} -> https://youtube.com/shorts/{vid}{sched_info}")
        return

    # Default action
    uploader.authenticate()
    print("[SUCCESS] Connected to YouTube API.")


if __name__ == "__main__":
    main()
