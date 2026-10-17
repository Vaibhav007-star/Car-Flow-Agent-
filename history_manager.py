"""Generation History and Anti-Repetition Intelligence Module.
Tracks all created videos, niches, and (Car, Material/Color) combinations to prevent duplicate generation,
save Google Flow computing limits, conserve YouTube API quota, and ensure content variety across niches.
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

# The 10 locked colors defined in Car Promot.pdf (Diecast Niche)
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

# The 10 locked woods defined in wooden_car_carving.md (Wooden Carving Niche)
LOCKED_WOODS = [
    "Light Maple",
    "Pale Birch",
    "Natural Oak",
    "Honey Ash",
    "Raw Pine",
    "Blonde Bamboo",
    "Warm Cherry",
    "Rich Walnut",
    "Golden Teak",
    "Dark Ebony",
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
    def parse_car_niche_and_material(cls, prompt_text: str = "", filename: str = "") -> Tuple[str, str, str]:
        """Parses canonical Car Model, Niche ('diecast' | 'wooden'), and Material/Color."""
        matched_material = "Custom"
        matched_niche = "diecast"
        car_name = ""

        p_lower = (prompt_text or "").lower()
        f_lower = (filename or "").lower()

        # 1. Detect Niche
        if "restoration" in p_lower or "moss" in p_lower or "rusty" in p_lower or "scalpel" in p_lower or "restoration" in f_lower:
            matched_niche = "restoration"
        elif "shipping container" in p_lower or "bolt cutters" in p_lower or "container" in p_lower or "container" in f_lower:
            matched_niche = "container"
        elif "kinetic" in p_lower or "gadget" in p_lower or "transformation" in p_lower or "kinetic" in f_lower or "gadget" in f_lower:
            matched_niche = "kinetic"
        elif "overland" in p_lower or "microvan" in p_lower or "off-road" in p_lower or "overland" in f_lower or "restomod" in p_lower:
            matched_niche = "overland"
        elif "foam" in p_lower or "styrofoam" in p_lower or "foam" in f_lower:
            matched_niche = "foam"
        elif "peel" in p_lower or "transit film" in p_lower or "push-to-start" in p_lower or "peel" in f_lower:
            matched_niche = "peel"
        elif "model-kit" in p_lower or "model kit" in p_lower or "unboxing" in p_lower or "model_kit" in f_lower:
            matched_niche = "model_kit"
        elif "wood" in p_lower or "carv" in p_lower or "workshop" in p_lower or "workbench" in p_lower or "wooden" in f_lower:
            matched_niche = "wooden"
        else:
            matched_niche = "diecast"

        # 2. Extract Material based on Niche
        if matched_niche in ("model_kit", "peel"):
            for c in LOCKED_COLORS + ["Rosso Corsa Red", "Solarbeam Yellow", "Kemora Gray", "Liquid Blue", "British Racing Green", "Papaya Orange", "Nardo Gray"]:
                if c.lower() in p_lower:
                    matched_material = c
                    break
            if prompt_text:
                m = re.search(r"completed\s+(?:.*?)\s+(.*?)\s+orbits smoothly on an illuminated dark turntable", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"miniature\s+(.*?)\s+hood and carbon roof", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"completed miniature\s+(.*?)\s+on a rotating", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"miniature\s+(.*?)\s+(?:aluminum frame|chassis|carbon monocoque|carbon tub)", prompt_text, re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip()
                    for c in LOCKED_COLORS + ["Rosso Corsa Red", "Solarbeam Yellow", "Kemora Gray", "Liquid Blue", "British Racing Green", "Papaya Orange", "Nardo Gray"]:
                        if candidate.lower().startswith(c.lower()):
                            candidate = candidate[len(c):].strip()
                            break
                    car_name = candidate
        elif matched_niche == "wooden":
            for w in LOCKED_WOODS:
                if w.lower() in p_lower:
                    matched_material = w
                    break
            # Extract car name from wooden prompt patterns
            if prompt_text:
                if matched_material != "Custom":
                    m = re.search(rf"miniature\s+{re.escape(matched_material)}\s+(.*?)\s+closed-roof coupe", prompt_text, re.IGNORECASE)
                    if not m:
                        m = re.search(rf"finished\s+{re.escape(matched_material)}\s+(.*?)\s+on the workbench", prompt_text, re.IGNORECASE)
                else:
                    m = None

                if not m:
                    m = re.search(r"miniature\s+(.*?)\s+closed-roof coupe", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"A miniature (.*?) handcrafted", prompt_text, re.IGNORECASE)

                if m:
                    candidate = m.group(1).strip()
                    for w in LOCKED_WOODS:
                        if candidate.lower().startswith(w.lower()):
                            candidate = candidate[len(w):].strip()
        elif matched_niche == "restoration":
            matched_material = "Mirror Jet Black"
            for c in LOCKED_COLORS + ["Mirror Jet Black", "Jet Black", "Gloss Black"]:
                if c.lower() in p_lower:
                    matched_material = c
                    break
            if prompt_text:
                m = re.search(r"rusty,\s+moss-covered\s+(?:1:18\s+scale\s+)?(.*?),\s+extreme\s+macro", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"restoration.*?scale\s+(.*?),\s+extreme\s+macro", prompt_text, re.IGNORECASE)
                if m:
                    car_name = m.group(1).strip()
            if not car_name and "bmw" in (p_lower + f_lower):
                car_name = "BMW M4 Coupe"
        elif matched_niche == "container":
            matched_material = "Mirror Black"
            for c in LOCKED_COLORS + ["Mirror Black"]:
                if c.lower() in p_lower:
                    matched_material = c
                    break
            if prompt_text:
                m = re.search(r"holding a 1:18 scale\s+(?:mirror-black|[\w-]+)\s+(.*?);", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"holding a 1:18 scale\s+(?:.*?)\s+(.*?);", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"completed\s+(?:.*?)\s+(.*?)\s+resting in front", prompt_text, re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip()
                    for pref in ["mirror-black", "black", "silver", "red", "white"]:
                        if candidate.lower().startswith(pref):
                            candidate = candidate[len(pref):].strip()
                    car_name = candidate
            if not car_name:
                car_name = "Mercedes-AMG G63"
        elif matched_niche == "kinetic":
            matched_material = "Crimson Red"
            for c in LOCKED_COLORS:
                if c.lower() in p_lower:
                    matched_material = c
                    break
            if prompt_text:
                m = re.search(r"miniature\s+(.*?)\s+snap flush into place", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"completed 1:18 scale\s+(?:.*?)\s+(.*?)\s+rests solid", prompt_text, re.IGNORECASE)
                if m:
                    car_name = m.group(1).strip()
            if not car_name:
                car_name = "Boxy 4x4 SUV"
        elif matched_niche == "overland":
            matched_material = "Rugged Off-Road"
            if prompt_text:
                m = re.search(r"bumper and winch plate onto a\s+(?:white\s+)?(.*?);", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"tracking hero reveal of the lifted\s+(?:white\s+)?(.*?)\s+reflected", prompt_text, re.IGNORECASE)
                if m:
                    car_name = m.group(1).strip()
            if not car_name and ("microvan" in p_lower or "microvan" in f_lower):
                car_name = "Suzuki Microvan"
        elif matched_niche == "foam":
            matched_material = "White Foam"
            if prompt_text:
                m = re.search(r"completed white Styrofoam\s+(.*?)\s+into a dramatic", prompt_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"foam block into a\s+(?:sleek\s+)?(?:sculpted\s+)?(.*?)(?:body|with)", prompt_text, re.IGNORECASE)
                if m:
                    car_name = m.group(1).strip()
            if not car_name:
                car_name = "Realistic Sedan"
        else:
            # Diecast Niche
            for c in LOCKED_COLORS:
                if c.lower() in p_lower:
                    matched_material = c
                    break
            if prompt_text:
                m = re.search(r"A miniature (.*?) in a spotless", prompt_text, re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip()
                    for c in LOCKED_COLORS:
                        if candidate.lower().startswith(c.lower()):
                            candidate = candidate[len(c):].strip()
                            break
                    car_name = candidate

        # 3. Fallback extraction from filename
        if not car_name and filename:
            clean_stem = Path(filename).stem
            parts = clean_stem.replace("video_", "").replace("wooden_", "").split("_")
            car_parts = [p for p in parts if not p.isdigit()]
            car_name = " ".join(car_parts).title()

        car_name = car_name.strip() or "Supercar"
        return car_name, matched_niche, matched_material

    @classmethod
    def parse_car_and_color(cls, prompt_text: str = "", filename: str = "") -> Tuple[str, str]:
        """Backwards compatibility wrapper returning (car_name, material)."""
        car_name, _, material = cls.parse_car_niche_and_material(prompt_text, filename)
        return car_name, material

    def has_generated(self, car_name: str, material: str, niche: Optional[str] = None) -> bool:
        """Checks if this specific Car + Material (in the given niche) has already been created."""
        target_car = car_name.strip().lower()
        target_mat = material.strip().lower()
        target_niche = (niche or "").strip().lower()

        for e in self.entries:
            e_car = e.get("car", "").strip().lower()
            e_mat = (e.get("material") or e.get("color") or "").strip().lower()
            e_niche = e.get("niche", "diecast").strip().lower()

            car_matches = (e_car == target_car or target_car in e_car or e_car in target_car)
            mat_matches = (e_mat == target_mat)
            niche_matches = (not target_niche or e_niche == target_niche)

            if car_matches and mat_matches and niche_matches:
                return True
        return False

    def get_palette_for_niche(self, niche: str = "diecast") -> List[str]:
        """Returns the locked materials palette for the chosen niche."""
        if niche.lower() == "wooden":
            return LOCKED_WOODS
        return LOCKED_COLORS

    def get_used_materials(self, car_name: str, niche: str = "diecast") -> List[str]:
        """Returns the list of materials/colors already used for this car model in the given niche."""
        target_car = car_name.strip().lower()
        target_niche = niche.strip().lower()
        used = []

        for e in self.entries:
            e_car = e.get("car", "").strip().lower()
            e_niche = e.get("niche", "diecast").strip().lower()
            if (e_car == target_car or target_car in e_car or e_car in target_car) and e_niche == target_niche:
                mat = e.get("material") or e.get("color")
                if mat and mat not in used:
                    used.append(mat)
        return used

    def get_available_materials(self, car_name: str, niche: str = "diecast") -> List[str]:
        """Returns locked materials that have NOT yet been used for this car in the given niche."""
        used = set(m.lower() for m in self.get_used_materials(car_name, niche=niche))
        palette = self.get_palette_for_niche(niche)
        return [m for m in palette if m.lower() not in used]

    def get_smart_fresh_material(self, car_name: str, niche: str = "diecast", preferred_material: Optional[str] = None) -> Optional[str]:
        """Returns a non-duplicate material/color for this car.
        
        If preferred_material is available, returns it.
        Otherwise picks the first unused material from the locked palette.
        Returns None if all 10 locked options have already been made for this car in this niche.
        """
        available = self.get_available_materials(car_name, niche=niche)
        if not available:
            return None

        if preferred_material and preferred_material in available:
            return preferred_material

        return available[0]

    # Legacy Aliases
    def get_used_colors(self, car_name: str) -> List[str]:
        return self.get_used_materials(car_name, niche="diecast")

    def get_available_colors(self, car_name: str) -> List[str]:
        return self.get_available_materials(car_name, niche="diecast")

    def get_smart_fresh_color(self, car_name: str, preferred_color: Optional[str] = None) -> Optional[str]:
        return self.get_smart_fresh_material(car_name, niche="diecast", preferred_material=preferred_color)

    def record_success(
        self,
        car_name: str,
        material: str,
        output_file: str,
        niche: str = "diecast",
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
            "niche": niche.strip().lower(),
            "material": material.strip(),
            "color": material.strip(),  # kept for backwards compatibility
            "output_file": output_file,
            "yt_uploaded": yt_uploaded,
            "yt_url": yt_url,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self.entries.append(entry)
        self.save()
        logger.info(f"Recorded in history ledger: [{niche}] {material} {car_name} -> {output_file}")
        return entry

    def sync_from_prompts_state(self, pm: Optional[PromptManager] = None) -> int:
        """Backfills history ledger with any Completed items found in prompts_state.json."""
        manager = pm or PromptManager()
        added_count = 0

        for item in manager.items:
            if item.get("status") == "Completed" and item.get("output_file"):
                car_name, niche, material = self.parse_car_niche_and_material(item.get("prompt", ""), item.get("output_file", ""))
                out_file = item["output_file"]
                yt_up = item.get("yt_uploaded", False)
                yt_u = item.get("yt_url")

                # Check if already present
                already_in_ledger = any(e.get("output_file") == out_file for e in self.entries)
                if not already_in_ledger:
                    self.record_success(car_name, material, out_file, niche=niche, yt_uploaded=yt_up, yt_url=yt_u)
                    added_count += 1
                else:
                    # Update upload status if changed
                    for e in self.entries:
                        if e.get("output_file") == out_file:
                            if "niche" not in e:
                                e["niche"] = niche
                            if "material" not in e:
                                e["material"] = material
                            if yt_up and not e.get("yt_uploaded"):
                                e["yt_uploaded"] = True
                                e["yt_url"] = yt_u
                                self.save()

        return added_count

    def clean_queue_duplicates(self, pm: Optional[PromptManager] = None) -> int:
        """Removes pending prompts from the queue that duplicate an already completed car/material/niche or earlier pending prompt."""
        manager = pm or PromptManager()
        seen_triplets: Set[Tuple[str, str, str]] = set()

        # Seed with already completed entries from history
        for e in self.entries:
            e_niche = e.get("niche", "diecast").lower()
            e_car = e.get("car", "").lower()
            e_mat = (e.get("material") or e.get("color") or "").lower()
            seen_triplets.add((e_niche, e_car, e_mat))

        filtered_items = []
        removed_count = 0

        for item in manager.items:
            if item.get("status") == "Completed":
                filtered_items.append(item)
                continue

            car, niche, material = self.parse_car_niche_and_material(item.get("prompt", ""))
            triplet = (niche.lower(), car.lower(), material.lower())

            if triplet in seen_triplets:
                logger.info(f"Removing duplicate pending prompt [{item['id']}]: [{niche}] {material} {car}")
                removed_count += 1
            else:
                seen_triplets.add(triplet)
                filtered_items.append(item)

        if removed_count > 0:
            manager.items = filtered_items
            manager.save()
            logger.info(f"Cleaned {removed_count} duplicate prompts from generation queue.")

        return removed_count
