"""Label management: list, create, delete, rename, and name↔id resolution.

`LabelService` wraps an authenticated googleapiclient Gmail resource. Gmail's
built-in (system) labels use their uppercase name as their id (e.g. INBOX,
TRASH); user labels have generated ids like ``Label_42`` and a separate name.
"""

from typing import List, Dict, Any

SYSTEM_LABELS = {
    "INBOX",
    "SENT",
    "DRAFT",
    "SPAM",
    "TRASH",
    "UNREAD",
    "STARRED",
    "IMPORTANT",
}


class LabelService:
    """CRUD and resolution for Gmail labels."""

    def __init__(self, service):
        self.service = service

    def list(self) -> List[Dict[str, Any]]:
        """Return all labels (each a dict with at least id and name)."""
        result = self.service.users().labels().list(userId="me").execute()
        return result.get("labels", [])

    def create(self, name: str) -> Dict[str, Any]:
        """Create a user label."""
        body = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        return self.service.users().labels().create(userId="me", body=body).execute()

    def delete(self, label_id: str):
        """Delete a label by its id."""
        return self.service.users().labels().delete(userId="me", id=label_id).execute()

    def rename(self, label_id: str, new_name: str) -> Dict[str, Any]:
        """Rename a label by its id."""
        body = {"id": label_id, "name": new_name}
        return (
            self.service.users()
            .labels()
            .update(userId="me", id=label_id, body=body)
            .execute()
        )

    def resolve_id(self, name: str) -> str:
        """Resolve a label name to its id.

        System labels resolve case-insensitively to their uppercase id. User
        labels are looked up by exact name first, then case-insensitively.
        Raises ValueError if no matching label exists.
        """
        if name.upper() in SYSTEM_LABELS:
            return name.upper()

        labels = self.list()
        for label in labels:
            if label.get("name") == name:
                return label["id"]
        lowered = name.lower()
        for label in labels:
            if label.get("name", "").lower() == lowered:
                return label["id"]

        raise ValueError(f"Label not found: {name}")
