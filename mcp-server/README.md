# wiki-LLM MCP Server（唯讀）

把 `wiki/` 的知識頁開放給其他 Claude Code / claude.ai session 查詢。
寫入（ingest / lint）不經過這裡，一律在這個 repo 內用 Claude Code 依 `CLAUDE.md` 流程做，走 git。

## 工具

| 工具 | 用途 |
|---|---|
| `wiki_index()` | 回傳 `index.md`，查詢第一步 |
| `wiki_read(page)` | 讀一頁；`page` 是相對 wiki/ 的路徑，可省 `.md`，可直接貼 `[[wikilink]]` |
| `wiki_list(prefix="")` | 列所有頁的 path / title / updated / confidence |
| `wiki_search(query, limit=10)` | 全文搜尋（不分大小寫、多個字以空白分隔需同時命中），回傳命中頁與片段 |
| `wiki_log(limit=5)` | `log.md` 最新幾筆，看 wiki 多新 |

## 容器怎麼讀到本機的 wiki

`docker-compose.yml` 用 bind mount 把 repo 的 `./wiki` 以唯讀掛進容器 `/wiki`：

```yaml
volumes:
  - ./wiki:/wiki:ro
```

所以本機 `git pull` 或 ingest 寫完，容器**立刻**讀得到，不需要 rebuild / restart。
容器裡只有 `/wiki`，看不到 `raw/`、`.env` 或其他檔案。

## 部署（這台主機）

```bash
cp .env.example .env         # 填一把隨機 API_KEY
docker compose up -d --build
curl http://127.0.0.1:8002/health   # 若有解開 compose 裡的 ports 才能用
```

對外不開 host port，而是加入 english-tutor 的 docker network（`english-tutor_default`），
由它的 caddy 以 `/wiki-mcp*` 反向代理到 `wiki-mcp:8001/mcp`（見 `english-tutor/deploy/Caddyfile`）。
改了 Caddyfile 之後要 reload：

```bash
cd ../english-tutor && docker compose -f docker-compose.prod.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## 給其他使用者的 client 設定

Claude Code：專案的 `.mcp.json`，或放進 plugin 的 `.mcp.json`（例如 lesh-common-plugin）讓所有專案共用。

```json
{
  "mcpServers": {
    "wiki-llm": {
      "type": "http",
      "url": "https://english-tutor.palettex.ca/wiki-mcp",
      "headers": { "X-API-Key": "${WIKI_LLM_API_KEY}" }
    }
  }
}
```

使用者在自己的 shell 設 `export WIKI_LLM_API_KEY=...`（跟 server 的 `.env` 同一把）。
claude.ai 的 custom connector：URL 同上，header 帶 `X-API-Key`。

## 本機 stdio 模式（除錯用）

```bash
cd mcp-server && uv run python server.py     # WIKI_ROOT 預設 ../wiki
```

## 安全

- http 模式沒有 `API_KEY` 會拒絕啟動；除 `/health` 外每個請求都要帶 key。
- `wiki_read` 會擋 `..` 跳出 wiki 目錄；只讀 `.md`。
- 單頁超過 60k 字會截斷並標 `truncated: true`。
