import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _req(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}. Copy .env.example to .env and fill it in.")
    return val


@dataclass(frozen=True)
class Config:
    supersaas_url: str
    supersaas_email: str
    supersaas_password: str
    gmail_address: str
    gmail_app_password: str
    notify_to: str
    check_interval_seconds: int
    headless: bool
    debug_dump: bool


def load() -> Config:
    return Config(
        supersaas_url=_req("SUPERSAAS_URL"),
        supersaas_email=_req("SUPERSAAS_EMAIL"),
        supersaas_password=_req("SUPERSAAS_PASSWORD"),
        gmail_address=_req("GMAIL_ADDRESS"),
        gmail_app_password=_req("GMAIL_APP_PASSWORD").replace(" ", ""),
        notify_to=_req("NOTIFY_TO"),
        check_interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "300")),
        headless=os.getenv("HEADLESS", "true").lower() == "true",
        debug_dump=os.getenv("DEBUG_DUMP", "false").lower() == "true",
    )
