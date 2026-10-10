"""Prompt Manager module.
Handles reading, queueing, state persistence, and status tracking for video prompts.
Supports prompts.txt and prompts_state.json.
"""

import json
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from config import PROMPTS_FILE, STATE_FILE


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class PromptManager:
    """Manages video generation prompts and their lifecycle states."""

    def __init__(self, prompts_file: Path = PROMPTS_FILE, state_file: Path = STATE_FILE):
        self.prompts_file = Path(prompts_file)
        self.state_file = Path(state_file)
        self.items: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> List[Dict[str, Any]]:
        """Load prompts state from JSON, syncing new entries from prompts.txt if available."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception:
                self.items = []
        else:
            self.items = []

        # Sync from text file if it exists
        self.sync_from_text_file()
        return self.items

    def save(self) -> None:
        """Persist items to state_file JSON."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=2, ensure_ascii=False)

    def sync_from_text_file(self) -> int:
        """Reads prompts.txt and appends any prompt text not already present."""
        if not self.prompts_file.exists():
            return 0

        added_count = 0
        existing_texts = {item["prompt"].strip().lower() for item in self.items}

        with open(self.prompts_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

        for line in lines:
            if line.lower() not in existing_texts:
                item = {
                    "id": str(uuid.uuid4())[:8],
                    "prompt": line,
                    "status": "Pending",  # Pending, Processing, Completed, Failed
                    "output_file": None,
                    "error": None,
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                }
                self.items.append(item)
                existing_texts.add(line.lower())
                added_count += 1

        if added_count > 0 or not self.state_file.exists():
            self.save()

        return added_count

    def add_prompt(self, text: str) -> Dict[str, Any]:
        """Add a single prompt to the queue."""
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Prompt text cannot be empty.")

        item = {
            "id": str(uuid.uuid4())[:8],
            "prompt": clean_text,
            "status": "Pending",
            "output_file": None,
            "error": None,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        self.items.append(item)
        self.save()
        return item

    def edit_prompt(self, prompt_id: str, new_text: str) -> bool:
        """Edit the prompt text of an existing item."""
        clean_text = new_text.strip()
        if not clean_text:
            raise ValueError("Prompt text cannot be empty.")
        for item in self.items:
            if item["id"] == prompt_id:
                item["prompt"] = clean_text
                item["updated_at"] = _now_iso()
                self.save()
                return True
        return False

    def remove_prompt(self, prompt_id: str) -> bool:
        """Remove a prompt by ID."""
        initial_len = len(self.items)
        self.items = [item for item in self.items if item["id"] != prompt_id]
        if len(self.items) != initial_len:
            self.save()
            return True
        return False

    def get_next_pending(self) -> Optional[Dict[str, Any]]:
        """Return the next Pending prompt in queue order."""
        for item in self.items:
            if item["status"] == "Pending":
                return item
        return None

    def update_status(
        self,
        prompt_id: str,
        status: str,
        output_file: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update prompt status ('Pending', 'Processing', 'Completed', 'Failed')."""
        valid_statuses = {"Pending", "Processing", "Completed", "Failed"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        for item in self.items:
            if item["id"] == prompt_id:
                item["status"] = status
                item["updated_at"] = _now_iso()
                if output_file is not None:
                    item["output_file"] = output_file
                if error is not None:
                    item["error"] = error
                elif status == "Completed":
                    item["error"] = None
                self.save()
                return True
        return False

    def retry_failed(self) -> int:
        """Reset all Failed or interrupted Processing prompts to Pending."""
        count = 0
        for item in self.items:
            if item["status"] in ("Failed", "Processing"):
                item["status"] = "Pending"
                item["error"] = None
                item["updated_at"] = _now_iso()
                count += 1
        if count > 0:
            self.save()
        return count

    def reset_all(self) -> None:
        """Reset all prompts back to Pending."""
        for item in self.items:
            item["status"] = "Pending"
            item["output_file"] = None
            item["error"] = None
            item["updated_at"] = _now_iso()
        self.save()

    def get_summary(self) -> Dict[str, int]:
        """Return counts of prompts by status."""
        summary = {"Total": len(self.items), "Pending": 0, "Processing": 0, "Completed": 0, "Failed": 0}
        for item in self.items:
            st = item.get("status", "Pending")
            if st in summary:
                summary[st] += 1
        return summary

