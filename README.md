# arxiv radar

Modern arXiv paper discovery with semantic search, personalized recommendations, and an MCP server for AI agent access. A from-scratch rewrite inspired by [arxiv-sanity-lite](https://github.com/karpathy/arxiv-sanity-lite), designed for self-hosting on a single server via Docker.

## Features

- **Semantic search** — hybrid search combining sentence-transformer embeddings (pgvector) with PostgreSQL full-text search, merged via Reciprocal Rank Fusion
- **Personalized recommendations** — tag papers you like, get recommendations based on embedding similarity
- **Reading lists and collections** — save papers, organize into shareable collections
- **Citation graph** — view citing/cited-by relationships via Semantic Scholar API
- **Trending papers** — see what the community is tagging
- **Notifications** — Slack/Discord webhooks and email digests for new matching papers
- **MCP server** — expose paper search and retrieval as tools for AI agents (Claude, Cursor, etc.)
- **Dark mode** — system preference detection with manual toggle
- **Mobile-friendly** — responsive layout with bottom nav on mobile

## Architecture

| Component | Technology |
|---|---|
| Backend | FastAPI (async Python) |
| Frontend | Vite + React 18 + TypeScript + Tailwind CSS |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, runs on CPU) |
| MCP server | FastMCP (SSE transport on port 8811) |
| Reverse proxy | Nginx |
| Orchestration | Docker Compose (7 containers) |

## Quick Start

```bash
git clone https://github.com/yourname/arxiv-radar.git
cd arxiv-radar

# Create environment file — review and change secrets before any exposed deploy
cp .env.example .env

# Start all services (includes MCP server)
docker compose up -d
```

The app is now running at **http://localhost:8080** and the MCP server at **http://localhost:8080/mcp/sse**.

The worker container automatically ingests new papers and computes embeddings every 30 minutes. Register an account at `/register` to start tagging papers and getting recommendations.

## MCP Server for AI Agents

The MCP (Model Context Protocol) server lets AI agents search and retrieve arXiv papers programmatically. It exposes 4 tools:

| Tool | Description |
|---|---|
| `search_papers` | Semantic search over paper abstracts. Supports category filters, date ranges, and sort order. |
| `get_paper` | Get metadata and abstract for a single paper by arXiv ID. |
| `list_recent_papers` | Browse recently published papers with optional category/date filters. |
| `get_similar_papers` | Find papers similar to a given paper via embedding similarity. |

Every result includes **PDF**, **HTML** (ar5iv), and **abstract page** URLs so agents can fetch full paper content on demand.

### Public Instance

The hosted instance is available at **https://arxivradar.com/mcp/sse** — no setup required beyond adding it to your client.

### Connecting to Cursor

Add to `.cursor/mcp.json` in your project root (or `~/.cursor/mcp.json` for global access):

```json
{
  "mcpServers": {
    "arxiv-radar": {
      "type": "sse",
      "url": "https://arxivradar.com/mcp/sse"
    }
  }
}
```

Restart Cursor after saving.

### Connecting to Claude Desktop

Add to your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "arxiv-radar": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://arxivradar.com/mcp/sse"]
    }
  }
}
```

Restart Claude Desktop after saving. Look for the hammer icon to confirm tools are loaded.

### Connecting to Claude Code

```bash
claude mcp add --transport sse arxiv-radar https://arxivradar.com/mcp/sse
```

Add `--scope user` for global access across all projects, or `--scope project` to commit it as `.mcp.json` for your team.

### Self-hosted Instance

If running your own instance, replace `https://arxivradar.com` with your host (e.g. `http://localhost:8080`). The MCP endpoint is served through nginx at `/mcp/sse` — no extra ports needed.

## Development

A `docker-compose.override.yml` is included that enables hot reload for both backend and frontend — no image rebuilds needed for code changes.

### With Docker (recommended)

```bash
# Starts all services with hot reload enabled
docker compose up -d

# Backend (uvicorn --reload) is at localhost:8000
# Frontend (Vite HMR) is at localhost:5174
# MCP server is at localhost:8811/sse
# Full app through nginx is at localhost:8080
```

Edit files in `backend/app/` or `frontend/src/` and changes are reflected immediately.

To run **without** hot reload (production-like), rename or remove `docker-compose.override.yml` before starting.

### Without Docker

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev

# MCP server (in a separate terminal)
cd backend
python -m app.mcp_server_main
```

The Vite dev server proxies `/api` requests to the backend at `localhost:8000`.

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...@postgres:5432/arxiv_radar` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `SECRET_KEY` | JWT signing key — **change this** | `changeme...` |
| `COOKIE_SECURE` | Set `true` behind TLS in production | `false` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173,http://localhost:8080` |
| `ARXIV_CATEGORIES` | Comma-separated arXiv categories to index | `cs.CV,cs.LG,cs.CL,cs.AI,cs.NE,cs.RO` |
| `ARXIV_INGEST_INTERVAL_MINUTES` | How often to poll arXiv | `30` |
| `ARXIV_INGEST_BATCH_SIZE` | Max papers per ingest run | `2000` |
| `EMBEDDING_MODEL` | sentence-transformers model name | `all-MiniLM-L6-v2` |
| `MODEL_CACHE_DIR` | Path to cache downloaded models | `/app/model_cache` |
| `MCP_TRANSPORT` | MCP transport protocol (`sse` or `stdio`) | `sse` |
| `MCP_HOST` | MCP server bind address | `0.0.0.0` |
| `MCP_PORT` | MCP server port | `8811` |
| `FULLTEXT_ENABLED` | Enable background full-text extraction pipeline | `false` |
| `SMTP_HOST` | SMTP server for email digests (optional) | — |
| `SEMANTIC_SCHOLAR_API_KEY` | API key for citation data (optional) | — |

## Production Deployment

For production, at minimum:

1. **Remove `docker-compose.override.yml`** so containers use production builds
2. **Generate a strong `SECRET_KEY`**: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
3. **Set `COOKIE_SECURE=true`** (requires HTTPS)
4. **Set strong `POSTGRES_PASSWORD`**
5. **Configure TLS** via a reverse proxy (Caddy, Traefik, or nginx with certbot) in front of the app
6. **Consider Redis authentication** if the server is on an untrusted network
7. **MCP is proxied** through nginx at `/mcp/` — no extra ports to expose

## API

The backend auto-generates OpenAPI docs at `/api/docs` when running.

Key endpoints:

- `GET /api/papers` — list/search papers (supports `q`, `days`, `categories`, pagination)
- `GET /api/papers/{id}` — paper detail
- `GET /api/papers/{id}/similar` — similar papers by embedding
- `GET /api/recommendations/for-you` — personalized feed
- `GET /api/recommendations/tag/{id}` — recommendations for a tag
- `POST /api/auth/register` — create account
- `POST /api/auth/login` — sign in
- `CRUD /api/tags` — manage tags
- `CRUD /api/collections` — manage collections
- `GET /api/social/trending` — trending papers
- `GET /api/social/citations/{id}` — citation graph data

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
