"""Viral Car Trend Hunter module.
Discovers trending automotive models across YouTube Shorts, Google Trends,
and viral social media niches, then formats them directly into locked prompt specifications:
1. Diecast Miniature Assembly (Car Promot.pdf)
2. Artisan Wooden Car Carving (wooden_car_carving.md)
"""

import os
import re
import random
import logging
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import requests

from config import PROMPTS_FILE
from prompt_manager import PromptManager
from history_manager import HistoryManager, LOCKED_COLORS, LOCKED_WOODS

logger = logging.getLogger("flow_automation.trend_hunter")

# High-velocity viral cars proven across YouTube Shorts, Reels, and TikTok
CURATED_VIRAL_CARS = [
    {"car": "Porsche 911 GT3 RS", "default_color": "Racing Red", "default_wood": "Rich Walnut", "niche": "Track Supercar", "score": 98},
    {"car": "Nissan Skyline GT-R R34", "default_color": "Midnight Purple", "default_wood": "Dark Ebony", "niche": "JDM Legend", "score": 97},
    {"car": "Lamborghini Revuelto", "default_color": "Sunset Orange", "default_wood": "Warm Cherry", "niche": "V12 Hybrid Hypercar", "score": 96},
    {"car": "Toyota Supra MK4 Turbo", "default_color": "Deep Emerald Green", "default_wood": "Golden Teak", "niche": "JDM Icon", "score": 95},
    {"car": "Ferrari SF90 XX Stradale", "default_color": "Racing Red", "default_wood": "Warm Cherry", "niche": "Italian Hypercar", "score": 94},
    {"car": "Koenigsegg Jesko Attack", "default_color": "Pearl White", "default_wood": "Light Maple", "niche": "Megacar Record Breaker", "score": 95},
    {"car": "BMW M4 Competition G82", "default_color": "Electric Blue", "default_wood": "Natural Oak", "niche": "German Performance", "score": 92},
    {"car": "Audi RS6 Avant C8", "default_color": "Matte Grey", "default_wood": "Pale Birch", "niche": "Widebody Super Wagon", "score": 91},
    {"car": "McLaren 765LT Spider", "default_color": "Sunset Orange", "default_wood": "Honey Ash", "niche": "Longtail Track Car", "score": 90},
    {"car": "Dodge Challenger SRT Demon 170", "default_color": "Jet Black", "default_wood": "Dark Ebony", "niche": "American Muscle", "score": 93},
    {"car": "Bugatti Chiron Pur Sport", "default_color": "Metallic Silver", "default_wood": "Blonde Bamboo", "niche": "W16 Hypercar", "score": 94},
    {"car": "Pagani Huayra BC", "default_color": "Titanium Gold", "default_wood": "Golden Teak", "niche": "Artisan Hypercar", "score": 91},
]


def format_short_video_prompt(car_name: str, color: str) -> str:
    """Formats a vehicle into the exact 10-shot locked short-form video prompt structure from Car Promot.pdf (Diecast Niche).

    Compresses all 10 shots into a single 8-second rapid macro time-lapse cut with diegetic ASMR audio.
    """
    clean_car = car_name.strip()
    clean_color = color.strip()
    if clean_color not in LOCKED_COLORS:
        clean_color = random.choice(LOCKED_COLORS)

    prompt = (
        f"A miniature {clean_color} {clean_car} in a spotless white cyclorama automotive studio with soft overhead lighting. "
        f"Rapid 8-second macro time-lapse cut: hands snap chrome emblem into black mesh front grille; "
        f"firmly press carbon-fibre hood vents flush with audible clicks; "
        f"clip on carbon side skirts and chrome door handles; "
        f"polish matte-black multi-spoke wheels with glowing blue lug nut LED accents; "
        f"fit glossy color-matched brake calipers with swift bolt-tightening; "
        f"lock titanium blue-tipped quad exhausts into carbon rear diffuser; "
        f"seat GT-style racing wing on trunk; "
        f"trigger LED headlights and taillights startup sequence with soft chimes; "
        f"quick interior touch-up on leather steering wheel; "
        f"ending on a smooth cinematic wide tracking reveal of the fully customized {clean_color} {clean_car} "
        f"accelerating across the white studio with dramatic reflections. "
        f"Hyper-detailed 8K macro cinematography, shallow depth of field, rapid time-lapse commercial pacing, "
        f"diegetic ASMR mechanical clicks and engine hum only, no music."
    )
    return prompt


def format_wooden_car_prompt(car_name: str, wood_type: str) -> str:
    """Formats an artisan wooden car carving prompt strictly according to the 8-second specification in wooden_car_carving.md."""
    clean_car = car_name.strip()
    clean_wood = wood_type.strip()
    if clean_wood not in LOCKED_WOODS:
        clean_wood = random.choice(LOCKED_WOODS)

    prompt = (
        f"A miniature {clean_wood} {clean_car} closed-roof coupe model handcrafted from solid {clean_wood} "
        f"on a flat wooden workbench in a warm, cozy artisan workshop under soft workshop lighting. "
        f"Rapid 8-second macro ASMR woodworking time-lapse: "
        f"[0.0-0.7s] chisel cuts kidney-style front grille slats with curling wood shavings blown off; "
        f"[0.7-1.4s] knife sculpts dual hood vents, sanding block glides over center line until wood grain glows; "
        f"[1.4-2.1s] slim side skirts carved, tiny door handles pressed flush with soft wooden tap; "
        f"[2.1-2.9s] rotary tool carves multi-spoke wheel, cloth polishes spokes, wheel pressed onto axle with smooth turn; "
        f"[2.9-3.5s] tweezers seat small red brake caliper behind wheel with quick tightening; "
        f"[3.5-4.3s] quad exhaust outlets carved into rear diffuser, brush cleans shavings; "
        f"[4.3-5.0s] dark carbon-fiber-weave spoiler lowered and pressed down onto trunk; "
        f"[5.0-5.7s] tweezers set LED headlight cluster glowing white and rear taillight strip glowing red; "
        f"[5.7-6.3s] quick macro through open driver door as seat is carved and tiny steering wheel wrapped in leather; "
        f"[6.3-8.0s] smooth slow cinematic wide tracking reveal of the finished {clean_wood} {clean_car} on the workbench "
        f"with warm light across detailed wood grain, dark spoiler, glowing white headlights and red taillights, holding final frame steady. "
        f"Hyper-realistic cinematic macro photography, detailed wood grain, natural imperfections, artisan hands only, "
        f"shallow depth of field, warm cinematic bokeh, vertical 9:16 composition, 4K quality. "
        f"Diegetic ASMR carving scrapes, sanding friction, wooden taps, and LED hum only. "
        f"No face, no person visible, no open-top roof, no clamp or vise, no text, no logos, no watermark, no music."
    )
    return prompt


class TrendHunter:
    """Discovers viral automotive trends and converts them into multi-niche production prompts."""

    def __init__(self, youtube_api_key: Optional[str] = None, history_manager: Optional[HistoryManager] = None):
        self.youtube_api_key = youtube_api_key or os.getenv("YOUTUBE_API_KEY")
        self.history = history_manager or HistoryManager()

    def fetch_youtube_viral_cars(self, query: str = "car build asmr shorts", max_results: int = 5) -> List[Dict[str, Any]]:
        """Queries YouTube Data API v3 for high-performing automotive shorts."""
        if not self.youtube_api_key:
            logger.info("No YOUTUBE_API_KEY provided; skipping live YouTube API query.")
            return []

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoDuration": "short",
            "order": "viewCount",
            "maxResults": max_results,
            "key": self.youtube_api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                title = snippet.get("title", "")
                desc = snippet.get("description", "")
                combined = f"{title} {desc}"

                found_car = None
                for c in CURATED_VIRAL_CARS:
                    pattern = rf"\b{re.escape(c['car'])}\b"
                    if re.search(pattern, combined, re.IGNORECASE):
                        found_car = c["car"]
                        break

                if found_car:
                    results.append({
                        "car": found_car,
                        "source": "YouTube Shorts Trending",
                        "details": f"Viral video: '{title[:45]}...'",
                        "score": 95,
                    })

            return results
        except Exception as e:
            logger.warning(f"YouTube Trends API query failed: {e}")
            return []

    def fetch_google_trends_cars(self) -> List[Dict[str, Any]]:
        """Parses Google Trends Daily Search Trends RSS feed for automotive keywords."""
        feed_url = "https://trends.google.com/trending/rss?geo=US"
        try:
            resp = requests.get(feed_url, timeout=10)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            trends = []
            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                text = f"{title} {desc}"

                for c in CURATED_VIRAL_CARS:
                    if re.search(rf"\b{re.escape(c['car'])}\b", text, re.IGNORECASE):
                        trends.append({
                            "car": c["car"],
                            "source": "Google Trends Search Spike",
                            "details": f"Spike in searches: '{title}'",
                            "score": 92,
                        })
            return trends
        except Exception as e:
            logger.warning(f"Google Trends RSS query failed: {e}")
            return []

    def get_trending_cars(self, max_results: int = 4, niche: str = "all") -> List[Dict[str, Any]]:
        """Returns deduplicated, viral automotive candidates formatted with anti-repetition memory.
        
        niche: 'diecast' | 'wooden' | 'all' (alternates between both)
        """
        trends: List[Dict[str, Any]] = []
        raw_candidates: List[Dict[str, Any]] = []

        # 1. YouTube API search
        yt_trends = self.fetch_youtube_viral_cars(max_results=max_results)
        raw_candidates.extend(yt_trends)

        # 2. Google Trends search
        g_trends = self.fetch_google_trends_cars()
        raw_candidates.extend(g_trends)

        # 3. Curated viral catalog
        for item in CURATED_VIRAL_CARS:
            raw_candidates.append({
                "car": item["car"],
                "color": item["default_color"],
                "default_wood": item.get("default_wood", "Rich Walnut"),
                "source": f"Viral Automotive Niche ({item['niche']})",
                "details": f"Top viral rank on Reels/Shorts with {item['score']}% engagement",
                "score": item["score"],
            })

        seen_cars = set()
        chosen_niche_mode = niche.lower()

        for idx, cand in enumerate(raw_candidates):
            if len(trends) >= max_results:
                break

            car = cand["car"].strip()
            car_key = car.lower()
            if car_key in seen_cars:
                continue

            # Determine specific niche for this candidate
            if chosen_niche_mode == "wooden":
                cand_niche = "wooden"
            elif chosen_niche_mode == "diecast":
                cand_niche = "diecast"
            else:
                # "all" / "mixed": alternate
                cand_niche = "wooden" if len(trends) % 2 == 1 else "diecast"

            # Anti-repetition check: pick fresh, unused material for this niche
            if cand_niche == "wooden":
                requested_mat = cand.get("default_wood", LOCKED_WOODS[0])
                fresh_mat = self.history.get_smart_fresh_material(car, niche="wooden", preferred_material=requested_mat)
                if not fresh_mat:
                    logger.info(f"Skipping {car} (wooden): all 10 locked woods already carved.")
                    continue
                prompt = format_wooden_car_prompt(car, fresh_mat)
            else:
                requested_mat = cand.get("color", LOCKED_COLORS[0])
                fresh_mat = self.history.get_smart_fresh_material(car, niche="diecast", preferred_material=requested_mat)
                if not fresh_mat:
                    logger.info(f"Skipping {car} (diecast): all 10 locked colors already built.")
                    continue
                prompt = format_short_video_prompt(car, fresh_mat)

            details = cand.get("details", "")
            if fresh_mat != requested_mat:
                details = f"{details} · [Material rotated: {requested_mat} ➔ {fresh_mat} to prevent repeat]"

            cand["car"] = car
            cand["niche"] = cand_niche
            cand["material"] = fresh_mat
            cand["color"] = fresh_mat  # backwards compatibility
            cand["details"] = details
            cand["prompt"] = prompt
            trends.append(cand)
            seen_cars.add(car_key)

        return trends[:max_results]

    def queue_trending_cars(self, selected_cars: List[Dict[str, Any]], pm: Optional[PromptManager] = None) -> int:
        """Converts selected trending cars into prompts and queues them up.
        
        Verifies both history ledger and active queue to prevent duplicate execution across niches.
        """
        manager = pm or PromptManager()
        self.history.sync_from_prompts_state(manager)
        queued_count = 0

        # Build set of existing (niche, car, material) triplets currently in queue
        existing_triplets = set()
        for p in manager.items:
            c, n, m = self.history.parse_car_niche_and_material(p.get("prompt", ""))
            existing_triplets.add((n.lower(), c.lower(), m.lower()))

        for item in selected_cars:
            car_name = item.get("car")
            material = item.get("material") or item.get("color")
            niche = item.get("niche", "diecast").lower()
            if not car_name or not material:
                continue

            triplet = (niche, car_name.strip().lower(), material.strip().lower())

            # 1. Skip if already completed in history ledger
            if self.history.has_generated(car_name, material, niche=niche):
                logger.info(f"Anti-repetition: Skipping [{niche}] {material} {car_name} (already in completed history).")
                continue

            # 2. Skip if already pending/processing in queue
            if triplet in existing_triplets:
                logger.info(f"Anti-repetition: Skipping [{niche}] {material} {car_name} (already queued).")
                continue

            prompt_text = item.get("prompt")
            if not prompt_text:
                if niche == "wooden":
                    prompt_text = format_wooden_car_prompt(car_name, material)
                else:
                    prompt_text = format_short_video_prompt(car_name, material)

            manager.add_prompt(prompt_text)
            existing_triplets.add(triplet)
            queued_count += 1

        return queued_count
