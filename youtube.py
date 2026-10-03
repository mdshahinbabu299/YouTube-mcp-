"""YouTube Data API v3 এর ছোট async ক্লায়েন্ট।"""
import os
import httpx

BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeError(Exception):
    pass


class YouTubeClient:
    def __init__(self, api_key: str):
        # কী URL-এ নয়, header-এ যায়, তাই লগ বা এররে ফাঁস হয় না
        self._http = httpx.AsyncClient(
            base_url=BASE,
            headers={"X-Goog-Api-Key": api_key},
            timeout=20,
        )

    async def get(self, endpoint: str, **params) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        try:
            r = await self._http.get(f"/{endpoint}", params=params)
        except httpx.HTTPError:
            raise YouTubeError("YouTube API-তে পৌঁছানো যায়নি, একটু পরে আবার চেষ্টা করুন।")
        if r.status_code != 200:
            try:
                err = r.json()["error"]
                reason = err.get("errors", [{}])[0].get("reason", "")
                msg = err.get("message", "")
            except Exception:
                reason, msg = "", ""
            if reason == "quotaExceeded":
                raise YouTubeError("আজকের YouTube API কোটা শেষ। কাল আবার চেষ্টা করুন।")
            raise YouTubeError(f"YouTube API error {r.status_code} {reason}: {msg}")
        return r.json()


def from_env() -> YouTubeClient:
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        raise SystemExit("YOUTUBE_API_KEY সেট করা নেই।")
    return YouTubeClient(key)
