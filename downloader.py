"""Downloader module.
Handles downloading, saving, and verifying generated videos to output_videos/.
Supports Playwright download events, direct URL streams, and blob URL exports.
"""

import re
import base64
import logging
from pathlib import Path
from typing import Optional
import requests
from config import OUTPUT_DIR

logger = logging.getLogger("flow_automation.downloader")


class VideoDownloader:
    """Manages downloading, naming, and verification of video files."""

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_filename(self, index: Optional[int] = None, prompt_text: Optional[str] = None) -> str:
        """Generate a sequential or slugified filename, e.g. video_001.mp4."""
        if index is not None:
            return f"video_{index:03d}.mp4"

        # Determine next index from existing files in output_dir
        existing = list(self.output_dir.glob("video_*.mp4"))
        indices = []
        for p in existing:
            match = re.search(r"video_(\d+)", p.stem)
            if match:
                try:
                    indices.append(int(match.group(1)))
                except ValueError:
                    pass
        next_idx = (max(indices) + 1) if indices else 1

        if prompt_text:
            # Short sanitized slug appended
            clean_slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", prompt_text[:30]).strip("_")
            if clean_slug:
                return f"video_{next_idx:03d}_{clean_slug}.mp4"

        return f"video_{next_idx:03d}.mp4"

    def verify_file(self, file_path: Path, min_bytes: int = 1024) -> bool:
        """Verify that the file exists and is greater than min_bytes."""
        if not file_path.exists():
            logger.error(f"Verification failed: File does not exist at {file_path}")
            return False
        size = file_path.stat().st_size
        if size < min_bytes:
            logger.error(f"Verification failed: File size too small ({size} bytes) at {file_path}")
            return False
        logger.info(f"Verified video file {file_path.name} ({size} bytes)")
        return True

    def save_playwright_download(self, download, target_filename: Optional[str] = None) -> Path:
        """Save a Playwright Download object to the output directory and verify it."""
        filename = target_filename or self.generate_filename()
        if not filename.endswith((".mp4", ".webm", ".mov")):
            filename += ".mp4"

        target_path = self.output_dir / filename
        logger.info(f"Saving Playwright download to {target_path}...")

        # Playwright save_as
        download.save_as(str(target_path))

        if not self.verify_file(target_path):
            if target_path.exists():
                target_path.unlink()
            raise IOError(f"Downloaded file at {target_path} failed integrity check.")

        return target_path

    def download_url(
        self,
        url: str,
        target_filename: Optional[str] = None,
        headers: Optional[dict] = None,
        timeout: int = 60,
    ) -> Path:
        """Stream download from an HTTP/HTTPS URL and verify."""
        filename = target_filename or self.generate_filename()
        if not filename.endswith((".mp4", ".webm")):
            filename += ".mp4"

        target_path = self.output_dir / filename
        logger.info(f"Downloading from URL {url} to {target_path}...")

        with requests.get(url, stream=True, headers=headers, timeout=timeout) as response:
            response.raise_for_status()
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        if not self.verify_file(target_path):
            if target_path.exists():
                target_path.unlink()
            raise IOError(f"Downloaded file from {url} failed verification.")

        return target_path

    def download_blob_via_page(self, page, blob_url: str, target_filename: Optional[str] = None) -> Path:
        """Extract a blob: URL using in-page fetch and FileReader conversion."""
        filename = target_filename or self.generate_filename()
        if not filename.endswith((".mp4", ".webm")):
            filename += ".mp4"

        target_path = self.output_dir / filename
        logger.info(f"Extracting in-page blob {blob_url} to {target_path}...")

        js_script = """
        async (blobUrl) => {
            const resp = await fetch(blobUrl);
            const blob = await resp.blob();
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        }
        """
        data_url = page.evaluate(js_script, blob_url)
        if not data_url or not data_url.startswith("data:"):
            raise ValueError(f"Failed to read data URL from blob: {blob_url}")

        header, base64_data = data_url.split(",", 1)
        video_bytes = base64.b64decode(base64_data)

        with open(target_path, "wb") as f:
            f.write(video_bytes)

        if not self.verify_file(target_path):
            if target_path.exists():
                target_path.unlink()
            raise IOError(f"Blob video at {target_path} failed verification.")

        return target_path

