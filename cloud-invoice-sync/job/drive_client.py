"""
Thin wrapper around the Drive API: find-or-create the provider/year folder
hierarchy, check for an existing file before uploading (idempotency), and
upload PDFs.

Auth: reuses the same refresh-token-based OAuth credential as GmailClient,
just scoped to drive.file (only files this app creates).
"""
import io
import json
import logging
from typing import Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class DriveClient:
    def __init__(self, oauth_json: str, root_folder_id: str):
        creds_data = json.loads(oauth_json)
        self.credentials = Credentials(
            token=None,
            refresh_token=creds_data["refresh_token"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            token_uri="https://oauth2.googleapis.com/token",
            scopes=DRIVE_SCOPES,
        )
        self.service = build("drive", "v3", credentials=self.credentials)
        self.root_folder_id = root_folder_id
        self._folder_cache: Dict[str, str] = {}

    def _find_folder(self, name: str, parent_id: str) -> Optional[str]:
        escaped_name = name.replace("'", "\\'")
        query = (
            f"name = '{escaped_name}' and mimeType = 'application/vnd.google-apps.folder' "
            f"and '{parent_id}' in parents and trashed = false"
        )
        response = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get("files", [])
        return files[0]["id"] if files else None

    def _create_folder(self, name: str, parent_id: str) -> str:
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = self.service.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    def get_or_create_folder(self, name: str, parent_id: str) -> str:
        cache_key = f"{parent_id}/{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        folder_id = self._find_folder(name, parent_id)
        if not folder_id:
            folder_id = self._create_folder(name, parent_id)
            logger.info(f"Created Drive folder: {name}")

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def get_provider_year_folder(self, provider_name: str, year: int) -> str:
        provider_folder = self.get_or_create_folder(provider_name, self.root_folder_id)
        return self.get_or_create_folder(str(year), provider_folder)

    def file_exists(self, filename: str, parent_id: str) -> bool:
        escaped_name = filename.replace("'", "\\'")
        query = f"name = '{escaped_name}' and '{parent_id}' in parents and trashed = false"
        response = self.service.files().list(q=query, fields="files(id, name)").execute()
        return len(response.get("files", [])) > 0

    def upload_pdf(self, filename: str, pdf_bytes: bytes, parent_id: str) -> str:
        metadata = {"name": filename, "parents": [parent_id]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=True)
        uploaded = self.service.files().create(body=metadata, media_body=media, fields="id").execute()
        return uploaded["id"]
