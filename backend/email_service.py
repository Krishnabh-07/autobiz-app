import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

def send_email(to_email: str, subject: str, body: str, is_html: bool = False):
    """
    Sends an email using the configured SMTP server.
    If no SMTP credentials are provided, falls back to logging (mock mode).
    """
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        logger.warning(f"SMTP not fully configured. Cannot send real email to {to_email}.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "html" if is_html else "plain"))
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        logger.info(f"OTP email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"OTP email failed to send to {to_email}. Exact error: {str(e)}")
        return False
