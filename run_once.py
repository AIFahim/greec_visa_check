"""Single-shot version for GitHub Actions cron. Runs one check, emails on transition, exits."""
import json
import logging
import sys
import traceback
from pathlib import Path

from checker import check_once
from config import load
from notifier import send_email

STATE_FILE = Path(__file__).parent / "seen_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
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

    if result.available and not state.get("notified_available"):
        body = (
            f"A slot appears to be available on the SuperSaaS schedule.\n\n"
            f"{result.summary}\n\n"
            f"Book immediately: {result.page_url}\n"
        )
        send_email(cfg, "Greek visa appointment slot available!", body, attachment=result.screenshot_path)
        state["notified_available"] = True
        _save_state(state)
        log.info("Notification email sent to %s", cfg.notify_to)
    elif not result.available and state.get("notified_available"):
        state["notified_available"] = False
        _save_state(state)
        log.info("Availability cleared; re-armed.")
    else:
        # Ensure file exists so cache save doesn't skip it on first run.
        _save_state(state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
