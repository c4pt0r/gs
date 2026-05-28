"""
Checkpoint management for gmail
"""

import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from .config import Config


class Checkpoint:
    """Manage checkpoint state for resuming email monitoring"""

    def __init__(self, config: Config):
        self.config = config
        self.checkpoint_file = config.checkpoint.checkpoint_file
        self.checkpoint_interval = config.checkpoint.checkpoint_interval
        self.last_save_time = 0
        self._data = {
            "last_history_id": None,
            "last_timestamp": None,
            "processed_message_ids": set(),
            "total_processed": 0,
            "started_at": None,
            "last_updated": None,
        }

        # Ensure checkpoint directory exists
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)

        # Load existing checkpoint if resuming
        if config.checkpoint.resume:
            self.load()
        elif config.checkpoint.reset_checkpoint:
            self.reset()

    def load(self) -> bool:
        """Load checkpoint from file"""
        if not os.path.exists(self.checkpoint_file):
            if not self.config.quiet:
                print(f"No checkpoint file found at {self.checkpoint_file}")
            return False

        try:
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)

            self._data["last_history_id"] = data.get("last_history_id")
            self._data["last_timestamp"] = data.get("last_timestamp")

            # Convert list back to set for processed message IDs
            processed_ids = data.get("processed_message_ids", [])
            self._data["processed_message_ids"] = set(processed_ids)

            self._data["total_processed"] = data.get("total_processed", 0)
            self._data["started_at"] = data.get("started_at")
            self._data["last_updated"] = data.get("last_updated")

            if not self.config.quiet:
                timestamp_str = self._data["last_timestamp"] or "unknown"
                print(f"Resumed from checkpoint: {timestamp_str}")
                print(f"Total processed messages: {self._data['total_processed']}")

            return True

        except Exception as e:
            if not self.config.quiet:
                print(f"Failed to load checkpoint: {e}")
            return False

    def save(self, force: bool = False) -> bool:
        """Save checkpoint to file"""
        current_time = time.time()

        # Check if we should save based on interval
        if (
            not force
            and (current_time - self.last_save_time) < self.checkpoint_interval
        ):
            return False

        try:
            # Convert set to list for JSON serialization
            data_to_save = self._data.copy()
            data_to_save["processed_message_ids"] = list(
                self._data["processed_message_ids"]
            )
            data_to_save["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Write to temporary file first, then rename for atomic operation
            temp_file = f"{self.checkpoint_file}.tmp"
            with open(temp_file, "w") as f:
                json.dump(data_to_save, f, indent=2)

            os.rename(temp_file, self.checkpoint_file)
            self.last_save_time = current_time

            if self.config.verbose:
                print(f"Checkpoint saved: {data_to_save['last_updated']}")

            return True

        except Exception as e:
            if not self.config.quiet:
                print(f"Failed to save checkpoint: {e}")
            return False

    def reset(self):
        """Reset checkpoint state"""
        self._data = {
            "last_history_id": None,
            "last_timestamp": datetime.now(timezone.utc).isoformat(),
            "processed_message_ids": set(),
            "total_processed": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": None,
        }

        # Remove existing checkpoint file
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)

        if not self.config.quiet:
            print("Checkpoint reset")

    def update_history_id(self, history_id: str):
        """Update the last processed history ID"""
        self._data["last_history_id"] = history_id

    def update_timestamp(self, timestamp: str):
        """Update the last processed timestamp"""
        self._data["last_timestamp"] = timestamp

    def add_processed_message(self, message_id: str):
        """Add a message ID to the processed set"""
        self._data["processed_message_ids"].add(message_id)
        self._data["total_processed"] += 1

    def is_message_processed(self, message_id: str) -> bool:
        """Check if a message has already been processed"""
        return message_id in self._data["processed_message_ids"]

    def get_last_history_id(self) -> Optional[str]:
        """Get the last processed history ID"""
        return self._data["last_history_id"]

    def get_last_timestamp(self) -> Optional[str]:
        """Get the last processed timestamp"""
        return self._data["last_timestamp"]

    def get_total_processed(self) -> int:
        """Get total number of processed messages"""
        return self._data["total_processed"]

    def get_started_at(self) -> Optional[str]:
        """Get the timestamp when monitoring started"""
        return self._data["started_at"]

    def cleanup_old_message_ids(self, max_ids: int = 10000):
        """Clean up old message IDs to prevent memory bloat"""
        if len(self._data["processed_message_ids"]) > max_ids:
            # Keep only the most recent message IDs
            # Note: This is a simple approach; in practice, you might want
            # to use a more sophisticated LRU cache or time-based cleanup
            processed_list = list(self._data["processed_message_ids"])
            self._data["processed_message_ids"] = set(processed_list[-max_ids:])

            if self.config.verbose:
                print(f"Cleaned up old message IDs, kept {max_ids} most recent")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save checkpoint"""
        self.save(force=True)
