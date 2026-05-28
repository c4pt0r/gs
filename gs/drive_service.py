"""Google Drive operations: list, upload, download, delete, mkdir.

`DriveService` wraps an authenticated Drive v3 resource. Deletes move to Trash
by default (reversible), matching `gs gmail rm`.
"""

import os
from typing import List, Dict, Any, Optional

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveService:
    """List/upload/download/delete files and create folders."""

    def __init__(self, service):
        self.service = service

    def list_files(
        self, query: Optional[str] = None, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        params = {
            "pageSize": max_results,
            "fields": "files(id,name,mimeType,size,modifiedTime)",
        }
        if query:
            params["q"] = query
        return self.service.files().list(**params).execute().get("files", [])

    def mkdir(self, name: str, parent: Optional[str] = None) -> Dict[str, Any]:
        body = {"name": name, "mimeType": FOLDER_MIME}
        if parent:
            body["parents"] = [parent]
        return self.service.files().create(body=body, fields="id,name").execute()

    def upload(self, path: str, parent: Optional[str] = None) -> Dict[str, Any]:
        body = {"name": os.path.basename(path)}
        if parent:
            body["parents"] = [parent]
        media = MediaFileUpload(path, resumable=False)
        return (
            self.service.files()
            .create(body=body, media_body=media, fields="id,name")
            .execute()
        )

    def download(self, file_id: str, out_path: str) -> str:
        request = self.service.files().get_media(fileId=file_id)
        with open(out_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return out_path

    def delete(self, file_id: str, permanent: bool = False):
        if permanent:
            return self.service.files().delete(fileId=file_id).execute()
        return (
            self.service.files()
            .update(fileId=file_id, body={"trashed": True})
            .execute()
        )
