# Contributing to arxiv radar

Thanks for your interest in contributing. This document covers the basics.

## Development Setup

1. Clone the repo and start the Docker stack (see [README.md](README.md))
2. The `docker-compose.override.yml` enables hot reload for both backend and frontend
3. Backend changes in `backend/app/` are picked up by uvicorn automatically
4. Frontend changes in `frontend/src/` are picked up by Vite HMR

## Pull Requests

- Fork the repo and create a feature branch from `main`
- Keep PRs focused — one feature or fix per PR
- Include a clear description of what changed and why
- Add or update tests if applicable
- Make sure the app builds and runs before submitting

## Code Style

### Python (backend)

- Python 3.11+, type hints on public functions
- Use `ruff` for linting if available
- Follow existing patterns for new API endpoints (router, service, models)
- No comments that just restate what the code does

### TypeScript (frontend)

- Strict mode, avoid `any` — use proper types
- React functional components with hooks
- Tailwind CSS for styling, no inline style objects except where necessary
- `aria-label` on icon-only buttons

## Commit Messages

Write clear, imperative commit messages:

```
fix: prevent HTML injection in email digest
feat: add citation graph to paper detail page
refactor: extract shared paper serializer
```

## Reporting Bugs

Open a GitHub issue with:

- Steps to reproduce
- Expected vs actual behavior
- Browser/OS if it's a frontend issue
- Docker logs if it's a backend issue

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
