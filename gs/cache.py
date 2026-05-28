"""
SQLite cache implementation for gmail
"""

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path


class MessageCache:
    """SQLite-based cache for Gmail messages"""

    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self.ensure_cache_dir()
        self.init_database()

    def ensure_cache_dir(self):
        """Ensure cache directory exists"""
        cache_dir = Path(self.cache_path).parent
        cache_dir.mkdir(parents=True, exist_ok=True)

    def init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT,
                    history_id TEXT,
                    internal_date INTEGER,
                    subject TEXT,
                    from_email TEXT,
                    to_email TEXT,
                    body TEXT,
                    snippet TEXT,
                    labels TEXT,
                    attachments TEXT,
                    raw_data TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes separately
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_thread_id ON messages(thread_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_internal_date ON messages(internal_date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_from_email ON messages(from_email)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_subject ON messages(subject)")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get cached message by ID"""
        with sqlite3.connect(self.cache_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_message(row)
            return None

    def cache_message(self, message: Dict[str, Any]):
        """Cache a message"""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO messages 
                (id, thread_id, history_id, internal_date, subject, from_email, 
                 to_email, body, snippet, labels, attachments, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    message["id"],
                    message.get("threadId"),
                    message.get("historyId"),
                    message.get("internalDate"),
                    message.get("subject", ""),
                    self._extract_email(message.get("from", {})),
                    self._extract_emails(message.get("to", [])),
                    message.get("body", ""),
                    message.get("snippet", ""),
                    json.dumps(message.get("labels", [])),
                    json.dumps(message.get("attachments", [])),
                    json.dumps(message),
                ),
            )

    def cache_messages(self, messages: List[Dict[str, Any]]):
        """Cache multiple messages"""
        for message in messages:
            self.cache_message(message)

    def search_messages(
        self, query: Dict[str, Any], limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search cached messages"""
        sql = "SELECT * FROM messages WHERE 1=1"
        params = []

        if query.get("from_email"):
            sql += " AND from_email LIKE ?"
            params.append(f"%{query['from_email']}%")

        if query.get("to_email"):
            sql += " AND to_email LIKE ?"
            params.append(f"%{query['to_email']}%")

        if query.get("subject"):
            sql += " AND subject LIKE ?"
            params.append(f"%{query['subject']}%")

        if query.get("since"):
            sql += " AND internal_date >= ?"
            params.append(query["since"])

        if query.get("until"):
            sql += " AND internal_date <= ?"
            params.append(query["until"])

        sql += " ORDER BY internal_date DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.cache_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            return [self._row_to_message(row) for row in rows]

    def get_cached_count(self) -> int:
        """Get number of cached messages"""
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            return cursor.fetchone()[0]

    def clear_cache(self):
        """Clear all cached messages"""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM cache_metadata")

    def cleanup_old_messages(self, days: int = 30):
        """Remove messages older than specified days"""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                """
                DELETE FROM messages 
                WHERE cached_at < datetime('now', '-{} days')
            """.format(
                    days
                )
            )

    def set_metadata(self, key: str, value: str):
        """Set cache metadata"""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_metadata (key, value)
                VALUES (?, ?)
            """,
                (key, value),
            )

    def get_metadata(self, key: str) -> Optional[str]:
        """Get cache metadata"""
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM cache_metadata WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def _row_to_message(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to message dict"""
        try:
            raw_data = json.loads(row["raw_data"])
            return raw_data
        except (json.JSONDecodeError, TypeError):
            # Fallback to constructing from individual fields
            return {
                "id": row["id"],
                "threadId": row["thread_id"],
                "historyId": row["history_id"],
                "internalDate": row["internal_date"],
                "subject": row["subject"],
                "from": {"email": row["from_email"], "name": ""},
                "to": [
                    {"email": email, "name": ""}
                    for email in row["to_email"].split(",")
                    if email
                ],
                "body": row["body"],
                "snippet": row["snippet"],
                "labels": json.loads(row["labels"]) if row["labels"] else [],
                "attachments": (
                    json.loads(row["attachments"]) if row["attachments"] else []
                ),
            }

    def _extract_email(self, email_obj: Dict[str, str]) -> str:
        """Extract email address from email object"""
        if isinstance(email_obj, dict):
            return email_obj.get("email", "")
        return str(email_obj)

    def _extract_emails(self, email_list: List[Dict[str, str]]) -> str:
        """Extract email addresses from list of email objects"""
        if not email_list:
            return ""

        emails = []
        for email_obj in email_list:
            if isinstance(email_obj, dict):
                emails.append(email_obj.get("email", ""))
            else:
                emails.append(str(email_obj))

        return ",".join(emails)
