import mimetypes
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

from config import Config

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def send_email(cfg: Config, subject: str, body: str, attachment: str | None = None) -> None:
    if not (cfg.gmail_address and cfg.gmail_app_password and cfg.notify_to):
        return
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


def _tg_api(token: str, method: str, data: dict | None = None, files: dict | None = None) -> None:
    url = f"https://api.telegram.org/bot{token}/{method}"
    if files:
        import mimetypes as _mt
        boundary = "----greekvisa" + str(id(data))
        body = bytearray()
        for name, value in (data or {}).items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")
        for name, filepath in files.items():
            p = Path(filepath)
            ctype, _ = _mt.guess_type(p.name)
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                f'Content-Disposition: form-data; name="{name}"; filename="{p.name}"\r\n'.encode()
            )
            body.extend(f"Content-Type: {ctype or 'application/octet-stream'}\r\n\r\n".encode())
            body.extend(p.read_bytes())
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(
            url,
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
    else:
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(data or {}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def send_telegram(cfg: Config, message: str, photo: str | None = None) -> None:
    if not (cfg.telegram_bot_token and cfg.telegram_chat_id):
        return
    if photo and Path(photo).exists():
        _tg_api(
            cfg.telegram_bot_token,
            "sendPhoto",
            data={"chat_id": cfg.telegram_chat_id, "caption": message[:1024]},
            files={"photo": photo},
        )
    else:
        _tg_api(
            cfg.telegram_bot_token,
            "sendMessage",
            data={"chat_id": cfg.telegram_chat_id, "text": message[:4000]},
        )


def notify(cfg: Config, subject: str, body: str, attachment: str | None = None) -> list[str]:
    """Send both Telegram (fast) and Email (backup). Returns list of channels used."""
    used: list[str] = []
    try:
        send_telegram(cfg, f"{subject}\n\n{body}", photo=attachment)
        if cfg.telegram_bot_token and cfg.telegram_chat_id:
            used.append("telegram")
    except Exception as e:
        used.append(f"telegram-failed:{e}")
    try:
        send_email(cfg, subject, body, attachment=attachment)
        if cfg.gmail_address and cfg.gmail_app_password and cfg.notify_to:
            used.append("email")
    except Exception as e:
        used.append(f"email-failed:{e}")
    return used
