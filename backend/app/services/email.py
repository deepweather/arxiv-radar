"""Email sending via SMTP (Namecheap PrivateMail compatible)."""

import html
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Low-level SMTP send. Returns True on success."""
    if not settings.smtp_host:
        logger.warning("SMTP not configured, skipping email to %s", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        if settings.smtp_use_ssl:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ctx) as server:
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls(context=ssl.create_default_context())
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def _wrap_html(content: str) -> str:
    """Wraps content in the shared branded email shell."""
    return f"""<!DOCTYPE html>
<html>
<body style="font-family:system-ui,-apple-system,sans-serif;color:#1f2937;max-width:600px;margin:0 auto;padding:0;">
  <div style="background:#b91c1c;color:white;padding:16px 24px;border-radius:8px 8px 0 0;">
    <h1 style="margin:0;font-size:20px;">arxiv radar</h1>
  </div>
  <div style="padding:24px;background:#ffffff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;">
    {content}
    <p style="color:#9ca3af;font-size:12px;margin-top:32px;border-top:1px solid #e5e7eb;padding-top:16px;">
      This email was sent by arxiv radar. If you didn't request this, you can safely ignore it.
    </p>
  </div>
</body>
</html>"""


def send_verification_email(to_email: str, token: str) -> bool:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    content = f"""
    <p>Hi,</p>
    <p>Thanks for signing up! Please verify your email address by clicking below:</p>
    <div style="text-align:center;margin:24px 0;">
      <a href="{link}"
         style="display:inline-block;padding:12px 32px;background:#b91c1c;color:white;
                text-decoration:none;border-radius:6px;font-weight:600;font-size:15px;">
        Verify email address
      </a>
    </div>
    <p style="color:#6b7280;font-size:13px;">Or copy this link: <a href="{link}" style="color:#1d4ed8;">{link}</a></p>
    """
    return _send_email(to_email, "Verify your email — arxiv radar", _wrap_html(content))


def send_password_reset_email(to_email: str, token: str) -> bool:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    content = f"""
    <p>Hi,</p>
    <p>We received a request to reset your password. Click below to choose a new one:</p>
    <div style="text-align:center;margin:24px 0;">
      <a href="{link}"
         style="display:inline-block;padding:12px 32px;background:#b91c1c;color:white;
                text-decoration:none;border-radius:6px;font-weight:600;font-size:15px;">
        Reset password
      </a>
    </div>
    <p style="color:#6b7280;font-size:13px;">Or copy this link: <a href="{link}" style="color:#1d4ed8;">{link}</a></p>
    <p style="color:#6b7280;font-size:13px;">This link expires in 1 hour. If you didn't request a reset, ignore this email.</p>
    """
    return _send_email(to_email, "Reset your password — arxiv radar", _wrap_html(content))


def send_digest_email(to_email: str, papers: list[dict]) -> bool:
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
        </tr>"""

    content = f"""
    <p>Hi,</p>
    <p>Here are your top paper recommendations based on your tags:</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
      {paper_rows}
    </table>
    <p style="color:#9ca3af;font-size:13px;margin-top:24px;">
      To stop these emails, update your preferences in your account settings.
    </p>
    """
    return _send_email(to_email, "arxiv radar — Your daily recommendations", _wrap_html(content))


def send_test_email(to_email: str) -> bool:
    """Sends a simple test email to verify SMTP connectivity."""
    content = """
    <p>Hi there,</p>
    <p>This is a test email from <strong>arxiv radar</strong>.</p>
    <p>If you're reading this, SMTP delivery via Namecheap PrivateMail is working correctly.</p>
    """
    return _send_email(to_email, "Test email — arxiv radar", _wrap_html(content))
