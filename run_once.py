"""Single-shot runner. Invoked by cron (GH Actions or VM). One check + optional auto-book + notify."""
import json
import logging
import sys
import traceback
from pathlib import Path

from checker import check_once
from config import load
from notifier import notify

STATE_FILE = Path(__file__).parent / "seen_state.json"
LOG_FILE = Path(__file__).parent / "checker.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("greek-visa")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main() -> int:
    cfg = load()
    state = _load_state()

    try:
        result = check_once(cfg)
    except Exception as e:
        log.error("Check failed: %s", e)
        log.error(traceback.format_exc())
        return 1

    log.info("Check done: available=%s | %s", result.available, result.summary)
    if result.booked or result.booking_summary:
        log.info("Auto-book: booked=%s | %s | when=%s", result.booked, result.booking_summary, result.booked_when_text)

    if result.booked:
        subject = "Greek visa: BOOKED a slot"
        body = (
            "Auto-book succeeded. A reservation has been created on your behalf.\n\n"
            f"When: {result.booked_when_text or '(unknown — check the site)'}\n"
            f"Status: {result.booking_summary}\n\n"
            f"Verify / cancel at: {result.page_url}\n"
        )
        channels = notify(cfg, subject, body, attachment=result.screenshot_path)
        log.info("Booking notification sent via: %s", channels)
        state["notified_available"] = True
        state["notified_booked"] = True
        _save_state(state)
    elif result.available and not state.get("notified_available"):
        subject = "Greek visa slot available!"
        body = (
            "A slot appears to be available on the SuperSaaS schedule.\n\n"
            f"{result.summary}\n"
        )
        if cfg.auto_book and result.booking_summary:
            body += f"\nAuto-book outcome: {result.booking_summary}\n"
        body += f"\nBook immediately: {result.page_url}\n"
        channels = notify(cfg, subject, body, attachment=result.screenshot_path)
        log.info("Availability notification sent via: %s", channels)
        state["notified_available"] = True
        _save_state(state)
    elif not result.available and state.get("notified_available"):
        state["notified_available"] = False
        state["notified_booked"] = False
        _save_state(state)
        log.info("Availability cleared; re-armed.")
    else:
        _save_state(state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
