"""Viral Car Trend Hunter module.
Discovers trending automotive models across YouTube Shorts, Google Trends,
and viral social media niches, then formats them directly into locked prompt specifications:
1. Diecast Miniature Assembly (Car Promot.pdf)
2. Artisan Wooden Car Carving (wooden_car_carving.md)
"""

import os
import sys
import re
import random
import logging
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import requests

from config import PROMPTS_FILE, BASE_DIR
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


def format_model_kit_car_prompt(car_name: str, color: str) -> str:
    """Formats a POV model-kit car unboxing & assembly prompt strictly according to redesigned 8-second model_kit_car_assembly.md."""
    clean_car = car_name.strip()
    clean_color = color.strip()
    if clean_color not in LOCKED_COLORS:
        clean_color = random.choice(LOCKED_COLORS)

    prompt = (
        f"First-person POV macro 8-second rapid time-lapse on a dark green grid cutting mat: "
        f"[0.0-2.0s] precision hobby nippers snip {clean_color} miniature parts off plastic sprue runners next to an open branded box; "
        f"[2.0-4.0s] hands place rolling chassis down, press in silver engine block, and click matte-black wheels onto axles with micro-ratchet spin; "
        f"[4.0-6.0s] hands lower {clean_color} aerodynamic body shell flush onto chassis with a crisp snap, tweezers locking carbon-fiber rear GT wing into place; "
        f"[6.0-8.0s] swift microfiber cloth polish across hood, placing the completed miniature {clean_color} {clean_car} onto an illuminated dark rotating turntable "
        f"as aggressive LED headlights flare to life with a dramatic lighting sweep. "
        f"Exactly two natural human hands with five fingers each throughout, hyper-detailed 8K macro product cinematography, "
        f"shallow depth of field, rapid satisfying assembly pacing, diegetic ASMR sprue snips, mechanical clicks, and engine idle only, no music. "
        f"No extra fingers, no deformed hands, no floating parts, no cartoon look, no text overlays, no watermark."
    )
    return prompt


def format_peel_delivery_prompt(car_name: str, color: str) -> str:
    """Formats an ASMR protective peel & push-to-start delivery prompt according to peel_and_delivery_car_assembly.md."""
    clean_car = car_name.strip()
    clean_color = color.strip()
    if clean_color not in LOCKED_COLORS:
        clean_color = random.choice(LOCKED_COLORS)

    prompt = (
        f"First-person POV macro 8-second rapid time-lapse: hands use fine tweezers to smoothly peel clear protective transit film "
        f"off the pristine {clean_color} miniature {clean_car} hood and carbon roof. "
        f"Hands click on carbon-fiber side mirrors and rear diffuser, pull tiny foam blocks from the front grilles, "
        f"and gently click open the miniature driver's door. A fingertip presses the tiny center-console push-to-start button "
        f"as the digital gauge cluster glows bright, LED headlights flare to life with a dramatic light sweep, "
        f"and the completed {clean_color} {clean_car} orbits smoothly on an illuminated dark turntable. "
        f"Exactly two natural human hands with five fingers each throughout, hyper-detailed 8K macro product cinematography, "
        f"shallow depth of field, rapid satisfying pacing, diegetic ASMR vinyl peels, mechanical clicks, and engine idle only, no music. "
        f"No extra fingers, no deformed hands, no floating parts, no cartoon look, no text overlays, no watermark."
    )
    return prompt


def format_foam_car_prompt(car_name: str = "sedan") -> str:
    """Formats an 8-second photorealistic Styrofoam car crafting prompt according to foam_car_sculpting.md."""
    clean_car = car_name.strip()
    is_generic = clean_car.lower() in ("sedan", "car", "model")
    car_descriptor = "sedan body" if is_generic else f"{clean_car} sedan body with signature grille cuts"
    hood_descriptor = "smooths the hood" if is_generic else "smooths the dual hood vents"
    hero_car = f"white Styrofoam {clean_car}"

    prompt = (
        f"Vertical 9:16 photorealistic ASMR DIY craft time-lapse, exactly 8 seconds on a light oak workbench under soft natural window light: "
        f"[0.0-2.0s] a pair of natural medium-brown hands uses a steel ruler and utility knife to slice a clean rectangular white Styrofoam block, foam offcuts falling away; "
        f"[2.0-4.0s] knife swiftly carves the foam block into a sleek sculpted {car_descriptor} with defined wheel arches, scattering tiny foam beads across the table; "
        f"[4.0-6.0s] close-up: sandpaper {hood_descriptor}, a fine scalpel scribes door seams and window lines, and matching round foam wheels are pressed into place; "
        f"[6.0-8.0s] a wide soft paintbrush sweeps white foam dust off the car, hands rotating the completed {hero_car} into a dramatic three-quarter hero pose on the workbench. "
        f"Exactly two natural human hands with five fingers each throughout, consistent workbench and car model, crisp matte EPS foam bead texture, warm neutral workshop tones, shallow depth of field, "
        f"diegetic ASMR knife slicing, sandpaper friction, and soft bristle brush strokes only, no music, no voice. "
        f"No face, no text, no watermark, no logos, no extra fingers, no deformed hands, no cartoon look, no glossy plastic, no painted color, no melting foam, no flicker, no shape-shifting."
    )
    return prompt


def format_overlander_prompt(car_name: str = "Suzuki Microvan") -> str:
    """Formats an 8-second 4x4 overlander restomod makeover prompt according to offroad_overlander_makeover.md."""
    clean_car = car_name.strip()
    prompt = (
        f"Vertical 9:16 photorealistic custom-garage makeover time-lapse, exactly 8 seconds in a bright seamless white cyclorama studio with glossy white floor and soft overhead lighting: "
        f"[0.0-2.0s] low-angle shot as two mechanics' black-gloved hands use pneumatic impact drivers to bolt a rugged black steel bull-bar bumper and winch plate onto a white {clean_car}; "
        f"[2.0-4.0s] close-up: hands tighten a heavy-duty roof rack and curved black LED light bar with a socket wrench, slotting in round LED halo headlights; "
        f"[4.0-6.0s] hands press on flared black fender arches and torque down beadlock wheels wrapped in knobby all-terrain tires, red lifted suspension coilovers visible behind; "
        f"[6.0-8.0s] open door reveals white diamond-quilted leather seats and glowing digital cluster before clicking shut, pulling back into a wide cinematic tracking hero reveal of the lifted white {clean_car} reflected in the glossy floor as all LED lights beam alive. "
        f"Exactly four natural human hands with black mechanic gloves throughout, consistent vehicle and tools, clean commercial aesthetic, shallow depth of field, "
        f"diegetic ASMR impact-driver whirrs, socket ratchet clicks, tire thuds, and LED startup chime only, no music, no voice. "
        f"No faces, no visible bodies, no text, no logos, no watermark, no extra fingers, no cartoon look, no vehicle color change, no flickering."
    )
    return prompt


def format_kinetic_gadget_prompt(car_name: str = "boxy 4x4 SUV", color: str = "Crimson Red") -> str:
    """Formats an 8-second kinetic gadget car transformation prompt according to kinetic_gadget_transformation.md."""
    clean_car = car_name.strip() or "boxy 4x4 SUV"
    clean_color = color.strip() or "Crimson Red"
    prompt = (
        f"Vertical 9:16 photorealistic kinetic gadget transformation, exactly 8 seconds on a polished grey-white granite table in an Indian living room with soft window lighting: "
        f"[0.0-2.0s] low-angle shot as a man's hand presses the steel top button on a compact dark-grey octagonal gadget, triggering an instant spring-loaded burst of {clean_color.lower()} mechanical arms and chrome pistons; "
        f"[2.0-4.0s] scissor-links push up a silver ladder chassis, locking gold coilover shock springs and knobby all-terrain tires onto axles with sharp mechanical clicks; "
        f"[4.0-6.0s] glossy {clean_color.lower()} body panels, black roof, and front grille of the miniature {clean_car} snap flush into place with magnetic clicks, driver door swinging open and snapping shut; "
        f"[6.0-8.0s] the completed 1:18 scale {clean_color.lower()} {clean_car} rests solid on the granite table as dual round LED headlights and amber fog lamps switch on with crisp reflections, holding final hero shot. "
        f"Exactly one natural human hand visible in initial beat, consistent vehicle model and granite surface throughout, shallow depth of field, rapid satisfying mechanical pacing, "
        f"diegetic ASMR button click, spring snaps, servo whirrs, and LED chime only, no music, no voice. "
        f"No face, no text, no captions, no logos, no watermark, no extra fingers, no cartoon look, no morphing parts, no camera shake."
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
    def fetch_channel_performance(self) -> Dict[str, Any]:
        """Analyzes real channel metrics (views, likes, engagement) via YouTube Data API v3."""
        import socket
        _orig = socket.getaddrinfo
        socket.getaddrinfo = lambda h, p, f=0, t=0, pr=0, fl=0: _orig(h, p, socket.AF_INET, t, pr, fl)

        token_file = BASE_DIR / "token.json"
        if not token_file.exists():
            logger.info("No token.json found; audience analysis falling back to default weights.")
            return {}

        try:
            import json
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            with open(token_file, "r", encoding="utf-8") as f:
                token_data = json.load(f)
            creds = Credentials.from_authorized_user_info(token_data)
            yt = build("youtube", "v3", credentials=creds)

            ch = yt.channels().list(mine=True, part="contentDetails,statistics").execute()
            if not ch.get("items"):
                return {}

            upl_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            items = yt.playlistItems().list(playlistId=upl_id, part="contentDetails", maxResults=25).execute().get("items", [])
            if not items:
                return {}

            vids = [it["contentDetails"]["videoId"] for it in items]
            v_info = yt.videos().list(id=",".join(vids), part="snippet,statistics").execute().get("items", [])

            brand_scores = {}
            niche_scores = {"diecast": 0, "wooden": 0, "model_kit": 0}
            video_insights = []

            for v in v_info:
                title = v["snippet"]["title"]
                stats = v.get("statistics", {})
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                engagement_score = views + (likes * 25)

                brand = None
                for b in ["BMW", "Porsche", "Nissan", "Ferrari", "Lamborghini", "Toyota", "Audi", "McLaren", "Bugatti", "Koenigsegg"]:
                    if b.lower() in title.lower():
                        brand = b
                        break

                if brand:
                    brand_scores[brand] = brand_scores.get(brand, 0) + engagement_score

                t_lower = title.lower()
                if "wood" in t_lower or "carv" in t_lower:
                    niche_scores["wooden"] += engagement_score
                elif "unboxing" in t_lower or "model kit" in t_lower:
                    niche_scores["model_kit"] += engagement_score
                else:
                    niche_scores["diecast"] += engagement_score

                video_insights.append({
                    "title": title,
                    "views": views,
                    "likes": likes,
                    "score": engagement_score,
                })

            logger.info(f"Audience Analysis: Analyzed {len(video_insights)} channel videos. Top brands: {list(brand_scores.keys())[:3]}")
            return {
                "brand_scores": brand_scores,
                "niche_scores": niche_scores,
                "videos": sorted(video_insights, key=lambda x: x["score"], reverse=True),
            }
        except Exception as e:
            logger.warning(f"Audience channel analysis notice: {e}")
            return {}

    def get_audience_driven_trends(self, max_results: int = 1) -> List[Dict[str, Any]]:
        """Selects high-performing vehicles & niches guided directly by real YouTube audience data."""
        perf = self.fetch_channel_performance()
        brand_scores = perf.get("brand_scores", {})

        # Determine smart niche rotation: pick the least recently used niche
        recent_niches = [e.get("niche") for e in self.history.entries[-3:] if e.get("niche")]
        all_niches = ["model_kit", "wooden", "diecast"]
        candidate_niches = [n for n in all_niches if n not in recent_niches]
        chosen_niche = candidate_niches[0] if candidate_niches else all_niches[(len(self.history.entries)) % len(all_niches)]

        # Candidate vehicles with baseline viral ratings
        prioritized = [
            {"car": "BMW M4 Competition G82", "brand": "BMW", "default_color": "Electric Blue", "default_wood": "Natural Oak", "score": 99},
            {"car": "Nissan Skyline GT-R R34", "brand": "Nissan", "default_color": "Midnight Purple", "default_wood": "Dark Ebony", "score": 98},
            {"car": "Porsche 911 GT3 RS", "brand": "Porsche", "default_color": "Racing Red", "default_wood": "Rich Walnut", "score": 97},
            {"car": "Lamborghini Revuelto", "brand": "Lamborghini", "default_color": "Sunset Orange", "default_wood": "Warm Cherry", "score": 96},
            {"car": "Toyota Supra MK4 Turbo", "brand": "Toyota", "default_color": "Deep Emerald Green", "default_wood": "Golden Teak", "score": 95},
            {"car": "Ferrari SF90 XX Stradale", "brand": "Ferrari", "default_color": "Rosso Corsa Red", "default_wood": "Warm Cherry", "score": 95},
            {"car": "Koenigsegg Jesko Attack", "brand": "Koenigsegg", "default_color": "Pearl White", "default_wood": "Light Maple", "score": 94},
            {"car": "Audi R8 V10 Performance", "brand": "Audi", "default_color": "Matte Grey", "default_wood": "Pale Birch", "score": 93},
            {"car": "McLaren 765LT Spider", "brand": "McLaren", "default_color": "Sunset Orange", "default_wood": "Honey Ash", "score": 92},
            {"car": "Dodge Challenger SRT Demon 170", "brand": "Dodge", "default_color": "Jet Black", "default_wood": "Dark Ebony", "score": 91},
        ]

        # Elevate cars that align with high-performing channel audience brands
        for c in prioritized:
            b = c.get("brand")
            if b in brand_scores:
                c["score"] += min(brand_scores[b] // 200, 30)

        prioritized.sort(key=lambda x: x["score"], reverse=True)

        results = []
        for cand in prioritized:
            if len(results) >= max_results:
                break

            car = cand["car"]

            # Anti-repetition check: pick fresh, unused material for this specific niche
            if chosen_niche == "wooden":
                req_mat = cand.get("default_wood", LOCKED_WOODS[0])
                fresh_mat = self.history.get_smart_fresh_material(car, niche="wooden", preferred_material=req_mat)
                if not fresh_mat:
                    continue
                prompt = format_wooden_car_prompt(car, fresh_mat)
            elif chosen_niche == "model_kit":
                req_mat = cand.get("default_color", LOCKED_COLORS[0])
                fresh_mat = self.history.get_smart_fresh_material(car, niche="model_kit", preferred_material=req_mat)
                if not fresh_mat:
                    continue
                prompt = format_model_kit_car_prompt(car, fresh_mat)
            else:
                req_mat = cand.get("default_color", LOCKED_COLORS[0])
                fresh_mat = self.history.get_smart_fresh_material(car, niche="diecast", preferred_material=req_mat)
                if not fresh_mat:
                    continue
                prompt = format_short_video_prompt(car, fresh_mat)

            score_val = brand_scores.get(cand.get("brand"), "High")
            reason = f"Audience Favorite: {cand.get('brand')} (Channel Score: {score_val}) · Balanced into [{chosen_niche.upper()}] niche"

            results.append({
                "car": car,
                "niche": chosen_niche,
                "material": fresh_mat,
                "color": fresh_mat,
                "prompt": prompt,
                "score": cand["score"],
                "source": "Audience Intelligence",
                "details": reason,
            })

            # Cycle niche if gathering multiple items
            if len(results) < max_results:
                niche_idx = (all_niches.index(chosen_niche) + 1) % len(all_niches)
                chosen_niche = all_niches[niche_idx]

        return results

    def get_trending_cars(self, max_results: int = 4, niche: str = "all", audience_driven: bool = False) -> List[Dict[str, Any]]:
        """Returns deduplicated, viral automotive candidates formatted with anti-repetition memory.
        
        niche: 'diecast' | 'wooden' | 'model_kit' | 'all' | 'audience'
        audience_driven: If True, uses actual YouTube channel metrics to guide selection.
        """
        if audience_driven or niche.lower() in ("audience", "smart"):
            return self.get_audience_driven_trends(max_results=max_results)

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
            elif chosen_niche_mode in ("model_kit", "modelkit", "unboxing"):
                cand_niche = "model_kit"
            elif chosen_niche_mode == "diecast":
                cand_niche = "diecast"
            else:
                # "all" / "mixed": cycle through niches
                niche_cycle = ["diecast", "wooden", "model_kit"]
                cand_niche = niche_cycle[len(trends) % len(niche_cycle)]

            # Anti-repetition check: pick fresh, unused material for this niche
            if cand_niche == "wooden":
                requested_mat = cand.get("default_wood", LOCKED_WOODS[0])
                fresh_mat = self.history.get_smart_fresh_material(car, niche="wooden", preferred_material=requested_mat)
                if not fresh_mat:
                    logger.info(f"Skipping {car} (wooden): all 10 locked woods already carved.")
                    continue
                prompt = format_wooden_car_prompt(car, fresh_mat)
            elif cand_niche == "model_kit":
                requested_mat = cand.get("color", LOCKED_COLORS[0])
                fresh_mat = self.history.get_smart_fresh_material(car, niche="model_kit", preferred_material=requested_mat)
                if not fresh_mat:
                    logger.info(f"Skipping {car} (model_kit): all 10 locked colors already built.")
                    continue
                prompt = format_model_kit_car_prompt(car, fresh_mat)
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
                elif niche in ("model_kit", "modelkit", "unboxing"):
                    prompt_text = format_model_kit_car_prompt(car_name, material)
                elif niche in ("peel", "delivery", "peel_and_delivery"):
                    prompt_text = format_peel_delivery_prompt(car_name, material)
                elif niche in ("foam", "styrofoam", "craft"):
                    prompt_text = format_foam_car_prompt(car_name)
                elif niche in ("overland", "overlander", "restomod", "microvan"):
                    prompt_text = format_overlander_prompt(car_name)
                elif niche in ("kinetic", "gadget", "transformation"):
                    prompt_text = format_kinetic_gadget_prompt(car_name, material)
                else:
                    prompt_text = format_short_video_prompt(car_name, material)

            manager.add_prompt(prompt_text)
            existing_triplets.add(triplet)
            queued_count += 1

        return queued_count


if __name__ == "__main__":
    import argparse

    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Automotive Trend Hunter & Prompt Synthesizer")
    parser.add_argument("--audience", action="store_true", help="Guide selection via real YouTube channel performance metrics")
    parser.add_argument("--count", type=int, default=3, help="Number of cars to hunt (default 3)")
    parser.add_argument("--niche", type=str, default="all", choices=["all", "diecast", "wooden", "model_kit", "audience"], help="Target niche")
    parser.add_argument("--queue", action="store_true", help="Directly queue discovered cars into generation queue")

    args = parser.parse_args()

    th = TrendHunter()
    print(f"\nScanning automotive trends (count={args.count}, niche={args.niche}, audience_driven={args.audience})...")
    results = th.get_trending_cars(max_results=args.count, niche=args.niche, audience_driven=args.audience)

    print("\n" + "=" * 60)
    print(f"  DISCOVERED TRENDING CARS ({'AUDIENCE-DRIVEN' if args.audience else 'MARKET-DRIVEN'})")
    print("=" * 60)
    for i, item in enumerate(results, 1):
        n_tag = f"[{item.get('niche', 'diecast').upper()}]"
        mat = item.get("material") or item.get("color")
        print(f"{i}. {n_tag} {item['car']} ({mat})")
        print(f"   Score: {item.get('score')} | Source: {item.get('source')}")
        print(f"   Details: {item.get('details')}")
        print(f"   Prompt Preview: {item.get('prompt')[:90]}...\n")

    if args.queue and results:
        pm = PromptManager()
        added = th.queue_trending_cars(results, pm)
        print(f"-> Queued {added} new prompts into prompts_state.json.")

