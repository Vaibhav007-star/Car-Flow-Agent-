"""Thumbnail Extraction and Engagement Scoring Module.
Extracts candidate frames across key video scenes, analyzes visual metrics
(sharpness, contrast, color vibrancy, face/motion-blur avoidance),
and selects the best high-CTR thumbnail for YouTube Shorts.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger("flow_automation.thumbnail")

# Default sampling timestamps for 8-second shorts
KEY_TIMESTAMPS = [0.5, 1.2, 2.3, 3.6, 5.2, 6.0, 6.8, 7.2, 7.6]


class ThumbnailGenerator:
    """Analyzes video frames and exports the highest-engaging thumbnail."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else Path("output_videos/thumbnails")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_candidates(
        self,
        video_path: Path,
        timestamps: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Extracts candidate frames from video and calculates engagement scores."""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 8.0

        ts_list = timestamps or KEY_TIMESTAMPS
        candidates = []

        for ts in ts_list:
            if ts > duration:
                continue

            frame_idx = min(int(ts * fps), total_frames - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            # 1. Sharpness via Laplacian variance (higher = sharper, avoids motion blur)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            # 2. Contrast & Luminance
            contrast = float(gray.std())
            brightness = float(gray.mean())

            # 3. Color Vibrancy (HSV Saturation std + mean)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            sat = hsv[:, :, 1]
            color_richness = float(sat.mean())

            # 4. Engagement Score Calculation:
            # - Prioritize high sharpness (clarity)
            # - Boost late reveal frames (6.5s to 7.8s) which show the complete build
            # - Reward rich contrast and saturation
            reveal_bonus = 1.35 if ts >= 6.5 else 1.0
            score = (sharpness * 0.5 + contrast * 4.0 + color_richness * 2.5) * reveal_bonus

            out_filename = f"{video_path.stem}_thumb_{ts:.1f}s.jpg"
            out_path = self.output_dir / out_filename
            cv2.imwrite(str(out_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 96])

            candidates.append({
                "timestamp": ts,
                "frame_idx": frame_idx,
                "path": out_path,
                "sharpness": round(sharpness, 2),
                "contrast": round(contrast, 2),
                "brightness": round(brightness, 2),
                "color_richness": round(color_richness, 2),
                "is_reveal": ts >= 6.5,
                "score": round(score, 2),
            })

        cap.release()
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    def get_best_thumbnail(self, video_path: Path) -> Tuple[Path, Dict[str, Any]]:
        """Picks and returns the #1 highest-scoring engagement thumbnail."""
        candidates = self.extract_candidates(video_path)
        if not candidates:
            raise RuntimeError(f"Could not extract any valid frames from {video_path}")

        best = candidates[0]
        # Copy to canonical best name
        best_canonical = self.output_dir / f"{video_path.stem}_best.jpg"
        import shutil
        shutil.copyfile(best["path"], best_canonical)
        best["best_path"] = best_canonical
        logger.info(f"Selected best thumbnail for {video_path.name}: {best_canonical.name} (Score: {best['score']})")
        return best_canonical, best


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "output_videos/video_003_wooden_rich_walnut_porsche_gt3_rs.mp4"
    gen = ThumbnailGenerator()
    best_file, info = gen.get_best_thumbnail(Path(target))
    print(f"\n[BEST THUMBNAIL]: {best_file}")
    print(f"Timestamp: {info['timestamp']}s (Frame #{info['frame_idx']})")
    print(f"Engagement Score: {info['score']} (Sharpness: {info['sharpness']}, Contrast: {info['contrast']}, Color: {info['color_richness']})\n")

