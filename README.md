# YouTube MCP Server

A lightweight [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that gives AI assistants access to the YouTube Data API v3. Search videos, inspect channels, browse trending content, and read comments, all through a token-protected HTTP endpoint.

## Features

- **11 tools** covering search, details, trending, playlists, and comments
- **Streamable HTTP transport**, ready for remote deployment
- **Token authentication** is mandatory; the server refuses to start without it
- **Quota-aware design**: channel uploads use the playlist endpoint (about 2 units) instead of search (100 units)
- **Secure by default**: the API key is sent in a request header, never in URLs or logs
- **Docker-ready** with a non-root container user

## Tools

| Tool | Description | Quota cost |
|------|-------------|-----------|
| `search_videos` | Search videos with filters (date range, region, duration, order) | 100 |
| `search_channels` | Search channels by query | 100 |
| `search_playlists` | Search playlists by query | 100 |
| `get_video_details` | Metadata and statistics for up to 50 videos | 1 |
| `get_channel_details` | Metadata and statistics for up to 50 channels | 1 |
| `get_channel_by_handle` | Look up a channel by `@handle` | 1 |
| `get_trending_videos` | Most popular videos by region and category | 1 |
| `get_video_categories` | List video categories for a region | 1 |
| `get_channel_videos` | Latest uploads from a channel | ~2 |
| `get_playlist_videos` | Videos in a playlist | ~2 |
| `get_video_comments` | Top-level comments on a video | 1 |

The default YouTube API quota is 10,000 units per day.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `YOUTUBE_API_KEY` | Yes | YouTube Data API v3 key |
| `MCP_AUTH_TOKEN` | Yes | Secret token clients must present (minimum 16 characters) |
| `PORT` | No | Port to listen on (default `8000`) |

Generate a strong token:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Getting a YouTube API key

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable **YouTube Data API v3** under *APIs & Services → Library*.
3. Create an API key under *APIs & Services → Credentials*.
4. Restrict the key to the YouTube Data API v3 only.

## Quick Start

### Run locally

```bash
git clone https://github.com/<your-username>/youtube-mcp.git
cd youtube-mcp
pip install -r requirements.txt

export YOUTUBE_API_KEY="your_api_key"
export MCP_AUTH_TOKEN="your_secret_token"
python server.py
```

### Run with Docker

```bash
docker build -t youtube-mcp .
docker run -p 8000:8000 \
  -e YOUTUBE_API_KEY="your_api_key" \
  -e MCP_AUTH_TOKEN="your_secret_token" \
  youtube-mcp
```

## Deployment

The server runs on any container platform (Sevalla, Render, Railway, Fly.io, Google Cloud Run, or a VPS).

1. Connect this repository and select **Dockerfile** as the build type.
2. Set `YOUTUBE_API_KEY` and `MCP_AUTH_TOKEN` as **runtime** environment variables.
3. Expose port `8000`.
4. Use `/health` as the health check path.

A small instance (512 MB RAM, 0.25 to 1 vCPU) is sufficient.

## Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | None | Health check, returns `{"status":"ok"}` |
| `POST /mcp` | Required | MCP streamable HTTP endpoint |

## Authentication

Every request to `/mcp` must include the token in one of two ways:

- **Header (recommended):** `Authorization: Bearer <MCP_AUTH_TOKEN>`
- **Query parameter:** `https://your-domain/mcp?key=<MCP_AUTH_TOKEN>`

Use the query parameter only with clients that cannot send custom headers. URLs may appear in proxy or access logs, so treat the full URL as a secret and rotate the token if it leaks.

## Connecting a client

For clients that support custom headers:

```json
{
  "mcpServers": {
    "youtube": {
      "type": "streamable-http",
      "url": "https://your-domain/mcp",
      "headers": {
        "Authorization": "Bearer <MCP_AUTH_TOKEN>"
      }
    }
  }
}
```

For URL-only clients, use `https://your-domain/mcp?key=<MCP_AUTH_TOKEN>`.

## Quick test

```bash
curl https://your-domain/health

curl -X POST "https://your-domain/mcp" \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Project structure

```
├── server.py          # MCP server, tools, and auth middleware
├── youtube.py         # Async YouTube Data API client
├── requirements.txt
├── Dockerfile
└── .env.example
```

## Security notes

- Never commit your `.env` file or API key to version control.
- Restrict your API key to the YouTube Data API v3 in the Google Cloud Console.
- Rotate `MCP_AUTH_TOKEN` immediately if you suspect it has leaked.
