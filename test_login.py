"""One-off login + slot-scan test. No email sent. Saves HTML + screenshot to debug/."""
from dataclasses import replace
from pathlib import Path

from playwright.sync_api import sync_playwright

from checker import _login, _scan_for_slots, DEBUG_DIR
from config import load


def main() -> None:
    cfg = load()
    cfg = replace(cfg, debug_dump=True)
    DEBUG_DIR.mkdir(exist_ok=True)
    print(f"Logging in as {cfg.supersaas_email} (headless={cfg.headless})...")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=cfg.headless)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        try:
            _login(page, cfg)
            available, summary = _scan_for_slots(page)
            Path(DEBUG_DIR / "available_view.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(DEBUG_DIR / "available_view.png"), full_page=True)
            print("Available:", available)
            print("Summary:  ", summary)
        finally:
            ctx.close()
            browser.close()


if __name__ == "__main__":
    main()
