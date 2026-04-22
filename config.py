import datetime as dt
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _req(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}. Copy .env.example to .env and fill it in.")
    return val


def _opt(key: str) -> str:
    return (os.getenv(key) or "").strip()


def _parse_date(s: str) -> dt.date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


@dataclass(frozen=True)
class Config:
    supersaas_url: str
    supersaas_email: str
    supersaas_password: str
    gmail_address: str
    gmail_app_password: str
    notify_to: str
    telegram_bot_token: str
    telegram_chat_id: str
    check_interval_seconds: int
    headless: bool
    debug_dump: bool
    auto_book: bool
    auto_book_cutoff_date: dt.date | None
    booking_purpose: str
    booking_host: str


def load() -> Config:
    return Config(
        supersaas_url=_req("SUPERSAAS_URL"),
        supersaas_email=_req("SUPERSAAS_EMAIL"),
        supersaas_password=_req("SUPERSAAS_PASSWORD"),
        gmail_address=_opt("GMAIL_ADDRESS"),
        gmail_app_password=_opt("GMAIL_APP_PASSWORD").replace(" ", ""),
        notify_to=_opt("NOTIFY_TO"),
        telegram_bot_token=_opt("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_opt("TELEGRAM_CHAT_ID"),
        check_interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "300")),
        headless=os.getenv("HEADLESS", "true").lower() == "true",
        debug_dump=os.getenv("DEBUG_DUMP", "false").lower() == "true",
        auto_book=os.getenv("AUTO_BOOK", "false").lower() == "true",
        auto_book_cutoff_date=_parse_date(_opt("AUTO_BOOK_CUTOFF_DATE")),
        booking_purpose=_opt("BOOKING_PURPOSE") or "Research visit to CERTH, Thessaloniki, Greece",
        booking_host=_opt("BOOKING_HOST") or "CERTH (Centre for Research & Technology Hellas), Thessaloniki",
    )
