"""YouTube crawler that uses the official API and timedtext endpoint."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree

import httpx
from googleapiclient.discovery import build

from src.models import ContentDocument
from src.utils.text_clean import clean_text

LOGGER = logging.getLogger(__name__)


class YouTubeCrawler:
    def __init__(self, api_key: str, settings) -> None:
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY is not set")
        self.settings = settings
        self.client = build("youtube", "v3", developerKey=api_key)
        self._http = httpx.Client(headers={"User-Agent": settings.http.get("user_agent", "Mozilla/5.0")})

    def close(self) -> None:
        self._http.close()

    def list_videos_from_channel(self, channel_id: str) -> List[Dict]:
        videos: List[Dict] = []
        page_token: Optional[str] = None
        while True:
            request = self.client.search().list(
                part="id,snippet",
                channelId=channel_id,
                maxResults=50,
                order="date",
                type="video",
                pageToken=page_token,
            )
            response = request.execute()
            for item in response.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue
                snippet = item.get("snippet", {})
                videos.append(
                    {
                        "videoId": video_id,
                        "title": snippet.get("title"),
                        "publishedAt": snippet.get("publishedAt"),
                        "channelTitle": snippet.get("channelTitle"),
                    }
                )
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return videos

    def fetch_transcript(self, video_id: str, lang: str = "ja") -> Optional[str]:
        url = f"https://www.youtube.com/api/timedtext?lang={lang}&v={video_id}"
        response = self._http.get(url)
        if response.status_code != 200 or not response.text:
            LOGGER.debug("Transcript not available for %s", video_id)
            return None
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError:
            return None
        texts = [clean_text(node.text or "") for node in root.findall("text") if node.text]
        return "\n".join(filter(None, texts)) or None

    def crawl_channel(self, channel_config: Dict, output_path: Path) -> int:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        channel_id = channel_config["channel_id"]
        videos = self.list_videos_from_channel(channel_id)
        collected = 0

        with output_path.open("a", encoding="utf-8") as fh:
            for idx, video in enumerate(videos, start=1):
                transcript = self.fetch_transcript(video["videoId"]) or ""
                document = ContentDocument(
                    id=f"youtube_{today}_{channel_config.get('name', channel_id)}_{idx:04d}",
                    source="youtube",
                    url=f"https://www.youtube.com/watch?v={video['videoId']}",
                    title=video.get("title") or "Untitled",
                    author=video.get("channelTitle") or channel_config.get("name"),
                    published_at=video.get("publishedAt"),
                    fetched_at=ContentDocument.now_iso(),
                    tags=channel_config.get("tags", []),
                    content=transcript,
                )
                fh.write(document.to_json() + "\n")
                collected += 1
        LOGGER.info("%s: collected %s videos", channel_config.get("name", channel_id), collected)
        return collected
