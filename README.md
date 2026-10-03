# YouTube MCP (নিজের বানানো)

YouTube Data API v3 এর জন্য MCP সার্ভার। পাসওয়ার্ড (token) ছাড়া কেউ ব্যবহার করতে পারবে না।

## Sevalla-তে ডিপ্লয়

1. এই ফোল্ডার GitHub-এ নতুন রিপো বানিয়ে আপলোড করুন
2. Sevalla → Add application → রিপো সিলেক্ট → Build: **Dockerfile**
3. Environment variables (Runtime):
   - `YOUTUBE_API_KEY` = আপনার কী
   - `MCP_AUTH_TOKEN` = লম্বা random পাসওয়ার্ড
4. Networking: পোর্ট `8000`
5. Deploy

## টোকেন বানানো

    python3 -c "import secrets; print(secrets.token_urlsafe(32))"

## পরীক্ষা

    https://আপনার-ডোমেইন/health              -> {"status":"ok"}
    https://আপনার-ডোমেইন/mcp?key=আপনার_টোকেন  -> MCP endpoint

ক্লায়েন্ট header সাপোর্ট করলে `Authorization: Bearer <token>` দিন, না করলে URL-এ `?key=` দিন।

## টুলস

search_videos, search_channels, search_playlists, get_video_details,
get_channel_details, get_channel_by_handle, get_trending_videos,
get_video_categories, get_channel_videos, get_playlist_videos, get_video_comments

search = 100 unit, বাকি প্রায় সবই 1-2 unit। দৈনিক কোটা 10,000।

## লোকাল চালানো

    pip install -r requirements.txt
    export YOUTUBE_API_KEY=... MCP_AUTH_TOKEN=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))")
    python server.py
