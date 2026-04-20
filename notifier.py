import mimetypes
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from config import Config

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_email(cfg: Config, subject: str, body: str, attachment: str | None = None) -> None:
    msg = EmailMessage()
    msg["From"] = cfg.gmail_address
    msg["To"] = cfg.notify_to
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment:
        path = Path(attachment)
        if path.exists():
            ctype, _ = mimetypes.guess_type(path.name)
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
            msg.add_attachment(
                path.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as smtp:
        smtp.login(cfg.gmail_address, cfg.gmail_app_password)
        smtp.send_message(msg)
