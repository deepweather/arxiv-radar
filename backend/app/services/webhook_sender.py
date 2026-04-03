"""Send notifications to Slack/Discord webhooks."""

import logging
import httpx

logger = logging.getLogger(__name__)


async def send_slack_notification(webhook_url: str, papers: list[dict]) -> bool:
    if not papers:
        return True

    blocks = []
    for p in papers[:10]:
        authors = ", ".join(a["name"] for a in p.get("authors", [])[:3])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<https://arxiv.org/abs/{p['id']}|{p['title']}>*\n{authors}\n_{p.get('summary', '')[:200]}..._",
            },
        })

    payload = {
        "text": f"arxiv radar: {len(papers)} new paper recommendations",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "arxiv radar — New Recommendations"}},
            *blocks,
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Failed to send Slack webhook")
        return False


async def send_discord_notification(webhook_url: str, papers: list[dict]) -> bool:
    if not papers:
        return True

    description_parts = []
    for p in papers[:10]:
        authors = ", ".join(a["name"] for a in p.get("authors", [])[:3])
        description_parts.append(
            f"**[{p['title']}](https://arxiv.org/abs/{p['id']})**\n{authors}"
        )

    payload = {
        "embeds": [
            {
                "title": "arxiv radar — New Recommendations",
                "description": "\n\n".join(description_parts),
                "color": 0xB91C1C,
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Failed to send Discord webhook")
        return False
