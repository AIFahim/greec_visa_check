import json
import logging
import sys
import time
import traceback
from pathlib import Path

from checker import check_once
from config import load
from notifier import send_email

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


def run_loop() -> None:
    cfg = load()
    log.info("Starting Greek visa checker. Interval=%ss Headless=%s", cfg.check_interval_seconds, cfg.headless)
    state = _load_state()
    error_streak = 0

    while True:
        started = time.time()
        try:
            result = check_once(cfg)
            log.info("Check done: available=%s | %s", result.available, result.summary)
            error_streak = 0

            if result.available and not state.get("notified_available"):
                subject = "Greek visa appointment slot available!"
                body = (
                    f"A slot appears to be available on the SuperSaaS schedule.\n\n"
                    f"{result.summary}\n\n"
                    f"Book immediately: {result.page_url}\n"
                )
                send_email(cfg, subject, body, attachment=result.screenshot_path)
                state["notified_available"] = True
                _save_state(state)
                log.info("Notification email sent to %s", cfg.notify_to)
            elif not result.available and state.get("notified_available"):
                state["notified_available"] = False
                _save_state(state)
                log.info("Availability cleared; re-armed for future notifications.")

        except Exception as e:
            error_streak += 1
            log.error("Check failed (streak=%d): %s", error_streak, e)
            log.debug(traceback.format_exc())
            if error_streak == 5:
                try:
                    send_email(
                        cfg,
                        "Greek visa checker: persistent errors",
                        f"The checker has failed 5 checks in a row.\nLast error: {e}\n\n{traceback.format_exc()}",
                    )
                except Exception as notify_err:
                    log.error("Failed to send error notification: %s", notify_err)

        elapsed = time.time() - started
        sleep_for = max(10, cfg.check_interval_seconds - int(elapsed))
        log.info("Sleeping %ss before next check.", sleep_for)
        time.sleep(sleep_for)


if __name__ == "__main__":
    try:
        run_loop()
    except KeyboardInterrupt:
        log.info("Stopped by user.")
