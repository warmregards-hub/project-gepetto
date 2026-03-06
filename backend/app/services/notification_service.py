from typing import Optional

import httpx

from app.config import settings


class NotificationService:
    def __init__(self):
        self.base_url = settings.ntfy_base_url.rstrip("/")
        self.topic = settings.ntfy_topic

    async def notify(self, title: str, message: str, link: Optional[str] = None) -> None:
        if not self.topic:
            return
        url = f"{self.base_url}/{self.topic}"
        body = message
        if link:
            body = f"{message}\n{link}"
        headers = {
            "Title": title,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, content=body.encode("utf-8"), headers=headers)
        except Exception:
            return
