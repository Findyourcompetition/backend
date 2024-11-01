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

async def send_reset_email(email: str, otp: str):
    """Send password reset email with OTP using FastMail."""
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"""
        <h2>FYC - Password Reset Request</h2>
        <p>Your password reset code is:</p>
        <h3 style="background-color: #f5f5f5; padding: 10px; font-family: monospace; text-align: center;">{otp}</h3>
        <p>Enter this code in the password reset form to create a new password.</p>
        <p>This code will expire in {settings.RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <p>If you didn't request this reset, please ignore this email.</p>
        """,
        subtype="html"
    )

    try:
        await fastmail.send_message(message)
        logger.info(f"Reset email with OTP sent to {email}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise
