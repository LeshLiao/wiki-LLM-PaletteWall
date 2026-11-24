"""wiki-LLM MCP Server（唯讀）。

把 wiki/ 目錄的 markdown 知識頁開放給其他 Claude Code / claude.ai session 查詢。
寫入（ingest / lint）不經過這裡，一律在 wiki repo 內用 Claude Code 依 CLAUDE.md 流程做，走 git。

環境變數：
  WIKI_ROOT      wiki 目錄；docker 內預設 /wiki（由 compose bind mount 進來），本機預設 ../wiki
  API_KEY        http 模式必填；client 以 X-API-Key 或 Authorization: Bearer 帶同一把 key
  MCP_TRANSPORT  stdio（預設）或 http（Streamable HTTP，跑在容器裡）
  MCP_HOST / MCP_PORT  http 模式的監聽位址，預設 0.0.0.0:8001
"""

from __future__ import annotations

import hmac
import os
import re
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

_DEFAULT_ROOT = "/wiki" if Path("/wiki").is_dir() else str(Path(__file__).resolve().parent.parent / "wiki")
WIKI_ROOT = Path(os.environ.get("WIKI_ROOT", _DEFAULT_ROOT)).resolve()
API_KEY = os.environ.get("API_KEY", "")
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))

MAX_PAGE_CHARS = 60_000

mcp = MCPServer(
    name="wiki-llm",
    instructions=(
        "Read-only access to an LLM-maintained knowledge wiki (markdown pages). "
        "Query workflow: 1) call wiki_index first to see every page with a one-line summary; "
        "2) call wiki_read on the relevant page path (e.g. 'projects/PaletteWallAndroid/api'); "
        "3) only if the index does not point to an answer, call wiki_search for full-text hits. "
        "Pages link to each other with [[path]] wikilinks; pass the path inside the brackets to wiki_read. "
        "Call wiki_log to see how recently the wiki was updated. "
        "Each page has frontmatter with 'confidence' (high/medium/low) and sentences marked 待確認 are unverified."
    ),
)


# ---------- helpers ----------

def _resolve(page: str) -> Path:
    """把 wiki 相對路徑（可省 .md、可帶 [[ ]]）安全地對應到檔案，擋住跳出 WIKI_ROOT。"""
    page = page.strip().strip("[]").strip()
    if not page:
        raise ToolError("page path is empty")
    if not page.endswith(".md"):
        page += ".md"
    candidate = (WIKI_ROOT / page).resolve()
    if WIKI_ROOT not in candidate.parents and candidate != WIKI_ROOT:
        raise ToolError(f"invalid page path: {page}")
    if not candidate.is_file():
        raise ToolError(f"page not found: {page} (call wiki_index to list pages)")
    return candidate


def _rel(path: Path) -> str:
    return path.relative_to(WIKI_ROOT).with_suffix("").as_posix()


def _all_pages() -> list[Path]:
    return sorted(p for p in WIKI_ROOT.rglob("*.md") if p.is_file())


_FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def _frontmatter(text: str) -> dict[str, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


# ---------- tools ----------

@mcp.tool()
def wiki_index() -> str:
    """Return wiki/index.md: the table of contents with every page path and a one-line summary. Call this first."""
    return (WIKI_ROOT / "index.md").read_text(encoding="utf-8")


@mcp.tool()
def wiki_read(page: str) -> dict:
    """Read one wiki page by its path relative to wiki/, without .md (e.g. 'projects/PaletteWallAndroid/api').
    Accepts the text inside a [[wikilink]]. Returns frontmatter (source, updated, confidence) and the markdown body."""
    path = _resolve(page)
    text = path.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    truncated = len(text) > MAX_PAGE_CHARS
    return {
        "page": _rel(path),
        "frontmatter": fm,
        "truncated": truncated,
        "content": text[:MAX_PAGE_CHARS],
    }


@mcp.tool()
def wiki_list(prefix: str = "") -> list[dict]:
    """List wiki pages (path, title, updated, confidence), optionally filtered by a path prefix such as 'projects/'."""
    rows = []
    for p in _all_pages():
        rel = _rel(p)
        if prefix and not rel.startswith(prefix.strip("/")):
            continue
        fm = _frontmatter(p.read_text(encoding="utf-8"))
        rows.append({
            "page": rel,
            "title": fm.get("title", ""),
            "updated": fm.get("updated", ""),
            "confidence": fm.get("confidence", ""),
        })
    return rows


@mcp.tool()
def wiki_search(query: str, limit: int = 10, context_lines: int = 1) -> list[dict]:
    """Case-insensitive full-text search across all wiki pages. Returns the best-matching pages with
    short snippets around each hit. Use after wiki_index when the index does not point to an answer."""
    q = query.strip()
    if not q:
        raise ToolError("query is empty")
    limit = max(1, min(limit, 50))
    terms = [t for t in re.split(r"\s+", q.lower()) if t]
    results = []
    for p in _all_pages():
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        lowered = [ln.lower() for ln in lines]
        hit_idx = [i for i, ln in enumerate(lowered) if all(t in ln for t in terms)]
        if not hit_idx:
            continue
        snippets = []
        for i in hit_idx[:5]:
            lo, hi = max(0, i - context_lines), min(len(lines), i + context_lines + 1)
            snippets.append({"line": i + 1, "text": "\n".join(lines[lo:hi])})
        fm = _frontmatter(text)
        results.append({
            "page": _rel(p),
            "title": fm.get("title", ""),
            "hits": len(hit_idx),
            "snippets": snippets,
        })
    results.sort(key=lambda r: r["hits"], reverse=True)
    return results[:limit]


@mcp.tool()
def wiki_log(limit: int = 5) -> str:
    """Return the most recent entries of wiki/log.md (newest first), to see when and how the wiki was last updated."""
    text = (WIKI_ROOT / "log.md").read_text(encoding="utf-8")
    parts = re.split(r"(?m)^(?=## )", text)
    header, entries = parts[0], parts[1:]
    return header + "".join(entries[: max(1, limit)])


# ---------- http mode ----------

@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> Response:
    """給 docker compose healthcheck 用，不需要認證。"""
    return JSONResponse({"status": "ok", "transport": "http", "pages": len(_all_pages())})


def _presented_key(scope: Scope) -> str | None:
    headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
    if "x-api-key" in headers:
        return headers["x-api-key"].strip()
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


class ApiKeyMiddleware:
    """純 ASGI middleware：除了 /health 之外，每個請求都要帶正確的 API key，否則 401。"""

    def __init__(self, app: ASGIApp, api_key: str, exempt_paths: tuple[str, ...] = ("/health",)) -> None:
        self.app = app
        self.api_key = api_key
        self.exempt_paths = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self.exempt_paths:
            await self.app(scope, receive, send)
            return
        presented = _presented_key(scope)
        if presented is None or not hmac.compare_digest(presented, self.api_key):
            response = PlainTextResponse("Unauthorized: missing or invalid API key", status_code=401)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def build_http_app():
    if not API_KEY:
        raise SystemExit("API_KEY is required in http mode (refusing to start an unauthenticated MCP server)")
    if not (WIKI_ROOT / "index.md").is_file():
        raise SystemExit(f"WIKI_ROOT={WIKI_ROOT} has no index.md (is the wiki directory mounted?)")
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp", stateless_http=True, json_response=True, host=MCP_HOST
    )
    app.add_middleware(ApiKeyMiddleware, api_key=API_KEY)
    return app


if __name__ == "__main__":
    if MCP_TRANSPORT == "http":
        import uvicorn

        uvicorn.run(build_http_app(), host=MCP_HOST, port=MCP_PORT, log_level="info")
    else:
        mcp.run(transport="stdio")
