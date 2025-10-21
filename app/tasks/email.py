from __future__ import annotations

import httpx
from datetime import datetime
from app.core.config import settings
from app.tasks.metrics_tasks import record_system_metrics


async def send_health_email() -> dict:
    """
    Send a plain-text health summary email via SendGrid.
    Requires SENDGRID_API_KEY and HEALTH_EMAIL_TO in .env.
    Uses SENDGRID_FROM_EMAIL if set (required for verified single sender).
    """
    api_key = settings.sendgrid_api_key
    to_email = settings.health_email_to
    from_email = getattr(settings, "sendgrid_from_email", None) or "noreply@smartenergy.local"

    if not api_key or not to_email:
        return {"status": "skip", "reason": "SendGrid not configured"}

    # Collect latest metrics on the fly
    metrics = await record_system_metrics()

    subject = f"SmartEnergy API Health Report — {datetime.utcnow():%Y-%m-%d %H:%M UTC}"
    body = (
        f"Environment: {settings.env}\n"
        f"Version: stage-2.4\n\n"
        f"DB latency: {metrics['db_latency_ms']} ms\n"
        f"Redis latency: {metrics['redis_latency_ms']} ms\n\n"
        f"Row counts:\n"
        + "\n".join([f"  {k}: {v}" for k, v in metrics.get('row_counts', {}).items()])
    )

    message = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    print("[send_health_email] Using from:", from_email)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {api_key}"},
                json=message,
            )
        if resp.status_code in (200, 202):
            return {"status": "ok", "sent_to": to_email, "from": from_email}
        return {"status": "error", "code": resp.status_code, "body": resp.text}
    except Exception as e:
        return {"status": "error", "error": str(e)}
