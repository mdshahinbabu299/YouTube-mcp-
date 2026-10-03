"""YouTube MCP Server (streamable HTTP + token auth)."""
import hmac
import json
import os
from typing import Optional
from urllib.parse import parse_qs

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from youtube import from_env

PORT = int(os.environ.get("PORT", "8000"))
AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "").strip()

yt = from_env()

mcp = FastMCP(
    "youtube",
    host="0.0.0.0",
    port=PORT,
    stateless_http=True,
    json_response=True,
)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# ---------- helpers ----------

def _n(max_results: int, hi: int = 50) -> int:
    return max(1, min(int(max_results), hi))


def _video(item: dict) -> dict:
    sn = item.get("snippet", {})
    st = item.get("statistics", {})
    cd = item.get("contentDetails", {})
    vid = item["id"]
    if isinstance(vid, dict):
        vid = vid.get("videoId")
    return {
        "id": vid,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "title": sn.get("title"),
        "channel": sn.get("channelTitle"),
        "channel_id": sn.get("channelId"),
        "published_at": sn.get("publishedAt"),
        "description": (sn.get("description") or "")[:300],
        "duration": cd.get("duration"),
        "views": st.get("viewCount"),
        "likes": st.get("likeCount"),
        "comments": st.get("commentCount"),
    }


async def _video_details(ids: list[str]) -> list[dict]:
    if not ids:
        return []
    data = await yt.get(
        "videos",
        part="snippet,contentDetails,statistics",
        id=",".join(ids[:50]),
    )
    return [_video(i) for i in data.get("items", [])]


def _channel(item: dict) -> dict:
    sn = item.get("snippet", {})
    st = item.get("statistics", {})
    return {
        "id": item["id"],
        "url": f"https://www.youtube.com/channel/{item['id']}",
        "title": sn.get("title"),
        "handle": sn.get("customUrl"),
        "description": (sn.get("description") or "")[:500],
        "country": sn.get("country"),
        "created_at": sn.get("publishedAt"),
        "subscribers": st.get("subscriberCount"),
        "views": st.get("viewCount"),
        "videos": st.get("videoCount"),
        "uploads_playlist": item.get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads"),
    }


# ---------- tools ----------

@mcp.tool()
async def search_videos(
    query: str,
    max_results: int = 10,
    order: str = "relevance",
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
    region_code: Optional[str] = None,
    video_duration: Optional[str] = None,
    channel_id: Optional[str] = None,
) -> str:
    """Search YouTube videos. (খরচ: 100 quota unit)

    order: relevance | date | viewCount | rating | title
    published_after/before: RFC3339, e.g. 2026-09-01T00:00:00Z
    region_code: 2-letter country code, e.g. BD, US
    video_duration: short (<4m) | medium (4-20m) | long (>20m)
    """
    data = await yt.get(
        "search",
        part="id",
        type="video",
        q=query,
        maxResults=_n(max_results),
        order=order,
        publishedAfter=published_after,
        publishedBefore=published_before,
        regionCode=region_code,
        videoDuration=video_duration,
        channelId=channel_id,
    )
    ids = [i["id"]["videoId"] for i in data.get("items", [])]
    return json.dumps(await _video_details(ids), ensure_ascii=False)


@mcp.tool()
async def search_channels(query: str, max_results: int = 10) -> str:
    """Search YouTube channels. (খরচ: 100 quota unit)"""
    data = await yt.get(
        "search", part="id", type="channel", q=query, maxResults=_n(max_results)
    )
    ids = [i["id"]["channelId"] for i in data.get("items", [])]
    if not ids:
        return "[]"
    ch = await yt.get(
        "channels", part="snippet,statistics,contentDetails", id=",".join(ids)
    )
    return json.dumps([_channel(i) for i in ch.get("items", [])], ensure_ascii=False)


@mcp.tool()
async def search_playlists(query: str, max_results: int = 10) -> str:
    """Search YouTube playlists. (খরচ: 100 quota unit)"""
    data = await yt.get(
        "search", part="snippet", type="playlist", q=query, maxResults=_n(max_results)
    )
    out = [
        {
            "id": i["id"]["playlistId"],
            "url": f"https://www.youtube.com/playlist?list={i['id']['playlistId']}",
            "title": i["snippet"].get("title"),
            "channel": i["snippet"].get("channelTitle"),
            "description": (i["snippet"].get("description") or "")[:200],
        }
        for i in data.get("items", [])
    ]
    return json.dumps(out, ensure_ascii=False)


@mcp.tool()
async def get_video_details(video_ids: list[str]) -> str:
    """Details + statistics for up to 50 video IDs. (খরচ: 1 unit)"""
    return json.dumps(await _video_details(video_ids), ensure_ascii=False)


@mcp.tool()
async def get_channel_details(channel_ids: list[str]) -> str:
    """Details + statistics for up to 50 channel IDs. (খরচ: 1 unit)"""
    data = await yt.get(
        "channels",
        part="snippet,statistics,contentDetails",
        id=",".join(channel_ids[:50]),
    )
    return json.dumps([_channel(i) for i in data.get("items", [])], ensure_ascii=False)


@mcp.tool()
async def get_channel_by_handle(handle: str) -> str:
    """Look up a channel by @handle, e.g. @MrBeast. (খরচ: 1 unit)"""
    if not handle.startswith("@"):
        handle = "@" + handle
    data = await yt.get(
        "channels",
        part="snippet,statistics,contentDetails",
        forHandle=handle,
    )
    items = data.get("items", [])
    if not items:
        return "এই handle-এ কোনো চ্যানেল পাওয়া যায়নি।"
    return json.dumps(_channel(items[0]), ensure_ascii=False)


@mcp.tool()
async def get_trending_videos(
    region_code: str = "BD",
    category_id: Optional[str] = None,
    max_results: int = 20,
) -> str:
    """Most popular videos in a region. (খরচ: 1 unit)
    category_id: get_video_categories থেকে পাবেন।
    """
    data = await yt.get(
        "videos",
        part="snippet,contentDetails,statistics",
        chart="mostPopular",
        regionCode=region_code,
        videoCategoryId=category_id,
        maxResults=_n(max_results),
    )
    return json.dumps([_video(i) for i in data.get("items", [])], ensure_ascii=False)


@mcp.tool()
async def get_video_categories(region_code: str = "BD") -> str:
    """List video categories for a region. (খরচ: 1 unit)"""
    data = await yt.get("videoCategories", part="snippet", regionCode=region_code)
    out = [
        {"id": i["id"], "title": i["snippet"]["title"]} for i in data.get("items", [])
    ]
    return json.dumps(out, ensure_ascii=False)


@mcp.tool()
async def get_channel_videos(channel_id: str, max_results: int = 20) -> str:
    """Latest uploads of a channel. (খরচ: ~2 unit, search-এর চেয়ে অনেক সস্তা)"""
    ch = await yt.get("channels", part="contentDetails", id=channel_id)
    items = ch.get("items", [])
    if not items:
        return "চ্যানেল পাওয়া যায়নি।"
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return await get_playlist_videos(uploads, max_results)


@mcp.tool()
async def get_playlist_videos(playlist_id: str, max_results: int = 20) -> str:
    """Videos in a playlist. (খরচ: ~2 unit)"""
    data = await yt.get(
        "playlistItems",
        part="contentDetails",
        playlistId=playlist_id,
        maxResults=_n(max_results),
    )
    ids = [i["contentDetails"]["videoId"] for i in data.get("items", [])]
    return json.dumps(await _video_details(ids), ensure_ascii=False)


@mcp.tool()
async def get_video_comments(
    video_id: str, max_results: int = 20, order: str = "relevance"
) -> str:
    """Top-level comments of a video. order: relevance | time (খরচ: 1 unit)"""
    data = await yt.get(
        "commentThreads",
        part="snippet",
        videoId=video_id,
        maxResults=_n(max_results, 100),
        order=order,
        textFormat="plainText",
    )
    out = []
    for i in data.get("items", []):
        c = i["snippet"]["topLevelComment"]["snippet"]
        out.append(
            {
                "author": c.get("authorDisplayName"),
                "text": c.get("textDisplay"),
                "likes": c.get("likeCount"),
                "published_at": c.get("publishedAt"),
                "replies": i["snippet"].get("totalReplyCount"),
            }
        )
    return json.dumps(out, ensure_ascii=False)


# ---------- auth ----------

class TokenAuth:
    """Authorization: Bearer <token> অথবা ?key=<token> চাই। /health খোলা।"""

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/health":
            return await self.app(scope, receive, send)

        headers = dict(scope["headers"])
        auth = headers.get(b"authorization", b"").decode()
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
        else:
            qs = parse_qs(scope.get("query_string", b"").decode())
            supplied = qs.get("key", [""])[0]

        if hmac.compare_digest(supplied.encode(), self.token.encode()):
            return await self.app(scope, receive, send)

        resp = JSONResponse({"error": "unauthorized"}, status_code=401)
        await resp(scope, receive, send)


def main():
    if not AUTH_TOKEN or len(AUTH_TOKEN) < 16:
        raise SystemExit(
            "MCP_AUTH_TOKEN সেট করুন (কমপক্ষে 16 অক্ষর), না হলে সার্ভার চালু হবে না।"
        )
    app = TokenAuth(mcp.streamable_http_app(), AUTH_TOKEN)
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
