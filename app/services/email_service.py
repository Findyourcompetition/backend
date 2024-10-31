from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from ..config import settings
import logging

logger = logging.getLogger(__name__)

mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,  # Changed from MAIL_TLS
    MAIL_SSL_TLS=False,  # Changed from MAIL_SSL
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=True  # Added validation for SSL certificates
)

fastmail = FastMail(mail_config)

async def send_reset_email(email: str, reset_token: str):
    """Send password reset email using FastMail."""
    reset_link = f"https://yourapp.com/reset-password?token={reset_token}"
    
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"""
        <h2>Password Reset Request</h2>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p>This link will expire in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <p>If you didn't request this reset, please ignore this email.</p>
        """,
        subtype="html"
    )

    try:
        await fastmail.send_message(message)
        logger.info(f"Reset email sent to {email}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise
