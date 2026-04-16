from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional

mcp = FastMCP("Helldivers 2 Community API")

BASE_URL = "https://api.helldivers2.dev"
DEFAULT_HEADERS = {
    "X-Super-Client": "fastmcp-helldivers2-server",
    "Accept": "application/json",
}


def get_language_headers(language: str) -> dict:
    headers = DEFAULT_HEADERS.copy()
    headers["Accept-Language"] = language
    return headers


@mcp.tool()
async def get_war_status(language: Optional[str] = "en-US") -> dict:
    """Retrieve the current state of the galactic war in Helldivers 2, including overall war progress, active campaigns, and the current war season. Use this when the user wants a high-level overview of the ongoing war effort."""
    headers = get_language_headers(language or "en-US")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/war",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_planets(language: Optional[str] = "en-US") -> list:
    """Retrieve a list of all planets in the Helldivers 2 galaxy, including their liberation status, current owner faction, player counts, and ongoing campaigns. Use this when the user wants to browse or compare planets across the war map."""
    headers = get_language_headers(language or "en-US")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/planets",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_planet(planet_index: int, language: Optional[str] = "en-US") -> dict:
    """Retrieve detailed information about a specific planet in Helldivers 2, including its biome, hazards, liberation percentage, active campaigns, statistics, and controlling faction. Use this when the user asks about a particular named planet."""
    headers = get_language_headers(language or "en-US")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/planets/{planet_index}",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_campaigns(language: Optional[str] = "en-US") -> list:
    """Retrieve all active campaigns (ongoing military operations) currently happening across the Helldivers 2 galaxy. Use this to find out which planets are currently being fought over, their liberation or defense progress, and how many Helldivers are participating."""
    headers = get_language_headers(language or "en-US")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/campaigns",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_assignments(language: Optional[str] = "en-US") -> list:
    """Retrieve the current Major Orders (assignments) issued by Super Earth High Command in Helldivers 2. These are the primary objectives the community should focus on, including task descriptions, rewards, and expiration times. Use this when the user asks about current major orders or what they should be doing."""
    headers = get_language_headers(language or "en-US")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/assignments",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_dispatches(language: Optional[str] = "en-US") -> list:
    """Retrieve the latest dispatches (in-game news messages and announcements) from Super Earth High Command in Helldivers 2. These are narrative updates and lore messages sent to players. Use this when the user wants to read recent in-game news or story updates."""
    headers = get_language_headers(language or "en-US")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/dispatches",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_steam_news(page: Optional[int] = 1) -> dict:
    """Retrieve the latest Steam news and patch notes for Helldivers 2. Use this when the user wants to know about recent game updates, patch notes, or official announcements posted on Steam."""
    params = {}
    if page is not None and page > 1:
        params["page"] = page
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/steam",
            headers=DEFAULT_HEADERS,
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_war_history(
    planet_index: Optional[int] = None,
    language: Optional[str] = "en-US",
) -> dict:
    """Retrieve historical snapshots and statistics of the Helldivers 2 war over time, including past planet states and liberation progress. Use this when the user wants to analyze trends, compare past vs current war states, or look up historical campaign outcomes."""
    headers = get_language_headers(language or "en-US")
    async with httpx.AsyncClient() as client:
        if planet_index is not None:
            url = f"{BASE_URL}/api/v1/planets/{planet_index}/history"
        else:
            url = f"{BASE_URL}/api/v1/war/history"
        response = await client.get(
            url,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()




_SERVER_SLUG = "api"

def _track(tool_name: str, ua: str = ""):
    try:
        import urllib.request, json as _json
        data = _json.dumps({"slug": _SERVER_SLUG, "event": "tool_call", "tool": tool_name, "user_agent": ua}).encode()
        req = urllib.request.Request("https://www.volspan.dev/api/analytics/event", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass

async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

mcp_app = mcp.http_app(transport="streamable-http")

class _FixAcceptHeader:
    """Ensure Accept header includes both types FastMCP requires."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            accept = headers.get(b"accept", b"").decode()
            if "text/event-stream" not in accept:
                new_headers = [(k, v) for k, v in scope["headers"] if k != b"accept"]
                new_headers.append((b"accept", b"application/json, text/event-stream"))
                scope = dict(scope, headers=new_headers)
        await self.app(scope, receive, send)

app = _FixAcceptHeader(Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", mcp_app),
    ],
    lifespan=mcp_app.lifespan,
))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
