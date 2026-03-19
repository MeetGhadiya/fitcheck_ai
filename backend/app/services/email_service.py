"""FitCheck AI — Email Service (Resend)"""
import httpx, logging
from app.core.config import settings

logger = logging.getLogger("fitcheck.email")

async def send_welcome_email(to_email: str, name: str):
    if not settings.RESEND_API_KEY:
        logger.info(f"[Mock email] Welcome to {name} <{to_email}>")
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json={
                    "from":    settings.FROM_EMAIL,
                    "to":      [to_email],
                    "subject": "Welcome to FitCheck AI 👗",
                    "html":    f"""
                    <h2>Hey {name}! Welcome to FitCheck AI 🎉</h2>
                    <p>You get <strong>3 free try-ons per day</strong> — no credit card needed.</p>
                    <p><a href="https://fitcheck.ai/studio">Start your first try-on →</a></p>
                    <hr/>
                    <p style="color:#888;font-size:12px">FitCheck AI · Revolutionising online fashion shopping</p>
                    """,
                },
            )
    except Exception as e:
        logger.error(f"Email send failed: {e}")
