import json
import mimetypes
from io import BytesIO
from typing import Optional, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.config import settings


class DriveService:
    def __init__(self):
        self.folder_id = settings.google_drive_folder_id
        self._client = None

    def _load_credentials(self):
        if not settings.google_service_account_json:
            return None
        try:
            info = json.loads(settings.google_service_account_json)
        except json.JSONDecodeError:
            return None
        scopes = ["https://www.googleapis.com/auth/drive"]
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)

    def _get_client(self):
        if self._client is not None:
            return self._client
        creds = self._load_credentials()
        if not creds:
            return None
        self._client = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._client

    def is_enabled(self) -> bool:
        return bool(settings.google_service_account_json and self.folder_id)

    def upload_bytes(self, filename: str, content: bytes, mime_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self.is_enabled():
            return None

        client = self._get_client()
        if not client:
            return None

        if not mime_type:
            mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        file_metadata = {
            "name": filename,
            "parents": [self.folder_id],
        }
        media = MediaIoBaseUpload(BytesIO(content), mimetype=mime_type, resumable=False)
        created = client.files().create(body=file_metadata, media_body=media, fields="id, webViewLink, webContentLink").execute()
        file_id = created.get("id")

        if file_id:
            client.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
                fields="id",
            ).execute()

        direct_url = None
        if file_id:
            direct_url = f"https://drive.google.com/uc?export=view&id={file_id}"

        return {
            "id": file_id,
            "webViewLink": created.get("webViewLink"),
            "webContentLink": created.get("webContentLink"),
            "directUrl": direct_url,
        }
