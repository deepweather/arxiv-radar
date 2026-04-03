# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email **security@arxiv-radar.local** (replace with your real contact) with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | Yes       |

## Security Considerations for Self-Hosters

- Always change `SECRET_KEY` and `POSTGRES_PASSWORD` from the defaults before deploying
- Set `COOKIE_SECURE=true` when running behind HTTPS
- Redis has no authentication by default — use `requirepass` or network isolation on untrusted networks
- Rate limiting depends on `X-Forwarded-For` — ensure your reverse proxy is the only source of this header
- Webhook URLs are stored in the database — treat them as secrets
