"""Send recommendation digest emails via SMTP."""

import html
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def send_digest_email(to_email: str, username: str, papers: list[dict]) -> bool:
    """Send a recommendation digest email. Returns True on success."""
    if not settings.smtp_host:
        logger.warning("SMTP not configured, skipping email to %s", to_email)
        return False

    safe_username = html.escape(username)
    paper_rows = ""
    for p in papers[:20]:
        authors = html.escape(", ".join(a["name"] for a in p.get("authors", [])[:3]))
        title = html.escape(p.get("title", ""))
        summary = html.escape(p.get("summary", "")[:200])
        score = p.get("similarity", 0)
        pid = html.escape(p.get("id", ""))
        paper_rows += f"""
        <tr>
          <td style="padding:8px;vertical-align:top;font-weight:bold;color:#b91c1c;">{score:.2f}</td>
          <td style="padding:8px;">
            <a href="https://arxiv.org/abs/{pid}" style="color:#1d4ed8;font-weight:500;">{title}</a>
            <div style="color:#6b7280;font-size:13px;margin-top:2px;">{authors}</div>
            <div style="color:#9ca3af;font-size:12px;margin-top:4px;">{summary}...</div>
          </td>
        </tr>
        """

    body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:system-ui,-apple-system,sans-serif;color:#1f2937;max-width:600px;margin:0 auto;">
      <div style="background:#b91c1c;color:white;padding:16px 24px;border-radius:8px 8px 0 0;">
        <h1 style="margin:0;font-size:20px;">arxiv radar</h1>
        <p style="margin:4px 0 0;font-size:14px;opacity:0.9;">Your daily paper recommendations</p>
      </div>
      <div style="padding:24px;background:#ffffff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;">
        <p>Hi {safe_username},</p>
        <p>Here are your top paper recommendations based on your tags:</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          {paper_rows}
        </table>
        <p style="color:#9ca3af;font-size:13px;margin-top:24px;">
          To stop these emails, update your preferences in your account settings.
        </p>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "arxiv radar \u2014 Your daily recommendations"
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("Digest email sent to %s", to_email)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False
