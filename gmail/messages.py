"""Write operations on Gmail messages: mark read/unread, trash, delete, move, send.

`MessageService` wraps an authenticated googleapiclient Gmail resource so it can
be unit-tested with a mock. `build_raw_message` constructs the base64url-encoded
MIME payload the Gmail send endpoint expects.
"""

import base64
import mimetypes
import os
from email.message import EmailMessage
from typing import List, Optional


def build_raw_message(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    sender: Optional[str] = None,
    html: bool = False,
    attachments: Optional[List[str]] = None,
) -> str:
    """Build a base64url-encoded RFC 2822 message for messages.send."""
    msg = EmailMessage()
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    if sender:
        msg["From"] = sender
    msg["Subject"] = subject

    if html:
        msg.set_content("This message requires an HTML-capable client.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    for path in attachments or []:
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(path, "rb") as fh:
            data = fh.read()
        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=os.path.basename(path),
        )

    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


class MessageService:
    """Write operations on messages, backed by an authenticated Gmail service."""

    def __init__(self, service):
        self.service = service

    def _modify(self, message_id: str, add=None, remove=None):
        body = {}
        if add:
            body["addLabelIds"] = list(add)
        if remove:
            body["removeLabelIds"] = list(remove)
        return (
            self.service.users()
            .messages()
            .modify(userId="me", id=message_id, body=body)
            .execute()
        )

    def mark_read(self, message_id: str):
        """Remove the UNREAD label."""
        return self._modify(message_id, remove=["UNREAD"])

    def mark_unread(self, message_id: str):
        """Add the UNREAD label."""
        return self._modify(message_id, add=["UNREAD"])

    def move(self, message_id: str, add_label_ids=None, remove_label_ids=None):
        """Add and/or remove labels on a message (the basis of `gmail mv`)."""
        return self._modify(message_id, add=add_label_ids, remove=remove_label_ids)

    def trash(self, message_id: str):
        """Move a message to Trash (reversible)."""
        return (
            self.service.users().messages().trash(userId="me", id=message_id).execute()
        )

    def delete(self, message_id: str):
        """Permanently delete a message (irreversible)."""
        return (
            self.service.users().messages().delete(userId="me", id=message_id).execute()
        )

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        sender: Optional[str] = None,
        html: bool = False,
        attachments: Optional[List[str]] = None,
    ):
        """Send a message; returns the API response (with the new message id)."""
        raw = build_raw_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            sender=sender,
            html=html,
            attachments=attachments,
        )
        return (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
