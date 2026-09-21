"""
Thin wrapper around the Gmail API: search the inbox, read message headers,
and download PDF attachments.

Auth: uses a refresh-token-based OAuth credential (see
scripts/get_oauth_token.py for how that credential is generated).
"""
import base64
import json
import logging
from typing import Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    def __init__(self, oauth_json: str):
        """oauth_json is the JSON string produced by get_oauth_token.py,
        containing client_id / client_secret / refresh_token."""
        creds_data = json.loads(oauth_json)
        self.credentials = Credentials(
            token=None,
            refresh_token=creds_data["refresh_token"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            token_uri="https://oauth2.googleapis.com/token",
            scopes=GMAIL_SCOPES,
        )
        self.service = build("gmail", "v1", credentials=self.credentials)

    def search_invoice_emails(self, query: str, max_results: int = 50) -> List[Dict]:
        """Search the inbox with a Gmail search query. Returns a list of
        {id, threadId} message stubs -- call get_message() for full content."""
        results: List[Dict] = []
        page_token = None

        while True:
            response = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, pageToken=page_token, maxResults=max_results)
                .execute()
            )
            results.extend(response.get("messages", []))
            page_token = response.get("nextPageToken")
            if not page_token or len(results) >= max_results:
                break

        return results

    def get_message(self, message_id: str) -> Dict:
        return (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

    def get_header(self, message: Dict, name: str) -> Optional[str]:
        headers = message.get("payload", {}).get("headers", [])
        for h in headers:
            if h.get("name", "").lower() == name.lower():
                return h.get("value")
        return None

    def get_pdf_attachments(self, message: Dict) -> List[Dict]:
        """Walk the message's MIME parts (including nested ones) and return
        [{filename, attachment_id}, ...] for every .pdf attachment found."""
        attachments: List[Dict] = []
        parts = message.get("payload", {}).get("parts", []) or []

        def walk(parts_list):
            for part in parts_list:
                filename = part.get("filename", "")
                if filename.lower().endswith(".pdf"):
                    attachment_id = part.get("body", {}).get("attachmentId")
                    if attachment_id:
                        attachments.append({"filename": filename, "attachment_id": attachment_id})
                if part.get("parts"):
                    walk(part["parts"])

        walk(parts)
        return attachments

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        attachment = (
            self.service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        data = attachment.get("data", "")
        return base64.urlsafe_b64decode(data.encode("utf-8"))
