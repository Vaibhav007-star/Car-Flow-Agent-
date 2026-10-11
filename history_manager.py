"""Generation History and Anti-Repetition Intelligence Module.
Tracks all created videos and (Car, Color) combinations to prevent duplicate generation,
save Google Flow computing limits, conserve YouTube API quota, and ensure content variety.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timezone

from config import BASE_DIR
from prompt_manager import PromptManager

logger = logging.getLogger("flow_automation.history")
logger.setLevel(logging.INFO)

HISTORY_FILE = BASE_DIR / "generation_history.json"

LOCKED_COLORS = [
    "Pearl White",
    "Jet Black",
    "Racing Red",
    "Electric Blue",
    "Matte Grey",
    "Metallic Silver",
    "Deep Emerald Green",
    "Sunset Orange",
    "Titanium Gold",
    "Midnight Purple",
]


class HistoryManager:
    """Maintains a persistent ledger of all generated and uploaded vehicles to eliminate duplicates."""

    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = Path(history_file)
        self.entries: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> List[Dict[str, Any]]:
        """Loads generation history ledger from JSON file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception as e:
                logger.warning(f"Could not parse {self.history_file}: {e}")
                self.entries = []
        else:
            self.entries = []
        return self.entries

    def save(self) -> None:
        """Persists generation history ledger to JSON file."""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)

    @classmethod
    def parse_car_and_color(cls, prompt_text: str = "", filename: str = "") -> Tuple[str, str]:
        """Parses canonical Car Model and Color from a prompt string or video filename."""
        matched_color = "Custom"
        car_name = ""

        if prompt_text:
            m = re.search(r"A miniature (.*?) in a spotless", prompt_text, re.IGNORECASE)
            if m:
                target_str = m.group(1).strip()
                for c in LOCKED_COLORS:
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

        car_name = car_name.strip() or "Supercar"
        return car_name, matched_color

    def has_generated(self, car_name: str, color: str) -> bool:
        """Checks if this specific Car + Color combination has already been created."""
        target_car = car_name.strip().lower()
        target_color = color.strip().lower()

        for e in self.entries:
            e_car = e.get("car", "").strip().lower()
            e_color = e.get("color", "").strip().lower()
            if (e_car == target_car or target_car in e_car or e_car in target_car) and e_color == target_color:
                return True
        return False

    def get_used_colors(self, car_name: str) -> List[str]:
        """Returns the list of colors already used for this car model."""
        target_car = car_name.strip().lower()
        used = []
        for e in self.entries:
            e_car = e.get("car", "").strip().lower()
            if e_car == target_car or target_car in e_car or e_car in target_car:
                color = e.get("color")
                if color and color not in used:
                    used.append(color)
        return used

    def get_available_colors(self, car_name: str) -> List[str]:
        """Returns locked colors that have NOT yet been used for this car."""
        used = set(c.lower() for c in self.get_used_colors(car_name))
        return [c for c in LOCKED_COLORS if c.lower() not in used]

    def get_smart_fresh_color(self, car_name: str, preferred_color: Optional[str] = None) -> Optional[str]:
        """Returns a non-duplicate color for this car.
        
        If preferred_color is available, returns it.
        Otherwise picks the first unused color from LOCKED_COLORS.
        Returns None if all 10 locked colors have already been made for this car.
        """
        available = self.get_available_colors(car_name)
        if not available:
            return None

        if preferred_color and preferred_color in available:
            return preferred_color

        return available[0]

    def record_success(
        self,
        car_name: str,
        color: str,
        output_file: str,
        yt_uploaded: bool = False,
        yt_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Records a successfully completed video into the permanent ledger."""
        for e in self.entries:
            if e.get("output_file") == output_file:
                # Update existing
                e["yt_uploaded"] = yt_uploaded or e.get("yt_uploaded", False)
                if yt_url:
                    e["yt_url"] = yt_url
                self.save()
                return e

        entry = {
            "car": car_name.strip(),
            "color": color.strip(),
            "output_file": output_file,
            "yt_uploaded": yt_uploaded,
            "yt_url": yt_url,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self.entries.append(entry)
        self.save()
        logger.info(f"Recorded in history ledger: {color} {car_name} -> {output_file}")
        return entry

    def sync_from_prompts_state(self, pm: Optional[PromptManager] = None) -> int:
        """Backfills history ledger with any Completed items found in prompts_state.json."""
        manager = pm or PromptManager()
        added_count = 0

        for item in manager.items:
            if item.get("status") == "Completed" and item.get("output_file"):
                car_name, color = self.parse_car_and_color(item.get("prompt", ""), item.get("output_file", ""))
                out_file = item["output_file"]
                yt_up = item.get("yt_uploaded", False)
                yt_u = item.get("yt_url")

                # Check if already present
                already_in_ledger = any(e.get("output_file") == out_file for e in self.entries)
                if not already_in_ledger:
                    self.record_success(car_name, color, out_file, yt_uploaded=yt_up, yt_url=yt_u)
                    added_count += 1
                else:
                    # Update upload status if changed
                    for e in self.entries:
                        if e.get("output_file") == out_file:
                            if yt_up and not e.get("yt_uploaded"):
                                e["yt_uploaded"] = True
                                e["yt_url"] = yt_u
                                self.save()

        return added_count

    def clean_queue_duplicates(self, pm: Optional[PromptManager] = None) -> int:
        """Removes any pending prompts from the queue that duplicate an already completed car/color or another pending prompt."""
        manager = pm or PromptManager()
        seen_pairs: Set[Tuple[str, str]] = set()

        # Seed with already completed entries from history
        for e in self.entries:
            seen_pairs.add((e["car"].lower(), e["color"].lower()))

        filtered_items = []
        removed_count = 0

        for item in manager.items:
            if item.get("status") == "Completed":
                filtered_items.append(item)
                continue

            car, color = self.parse_car_and_color(item.get("prompt", ""))
            pair = (car.lower(), color.lower())

            if pair in seen_pairs:
                logger.info(f"Removing duplicate pending prompt [{item['id']}]: {color} {car}")
                removed_count += 1
            else:
                seen_pairs.add(pair)
                filtered_items.append(item)

        if removed_count > 0:
            manager.items = filtered_items
            manager.save()
            logger.info(f"Cleaned {removed_count} duplicate prompts from generation queue.")

        return removed_count
