import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PWTimeout, sync_playwright

from config import Config

DEBUG_DIR = Path(__file__).parent / "debug"


@dataclass
class CheckResult:
    available: bool
    summary: str
    screenshot_path: str | None
    page_url: str


def _login(page: Page, cfg: Config) -> None:
    page.goto(cfg.supersaas_url, wait_until="domcontentloaded", timeout=30_000)

    email_field = page.locator(
        'input[type="email"], input[name*="email" i], input[id*="email" i], input[name="name"]'
    ).first
    email_field.wait_for(state="visible", timeout=15_000)
    email_field.fill(cfg.supersaas_email)

    password_field = page.locator('input[type="password"]').first
    password_field.fill(cfg.supersaas_password)

    submit = page.locator(
        'button[type="submit"], input[type="submit"], button:has-text("Log in"), button:has-text("Login")'
    ).first
    submit.click()

    page.wait_for_load_state("domcontentloaded", timeout=30_000)

    if page.locator('input[type="password"]').count() > 0:
        err = page.locator("body").inner_text()[:400]
        raise RuntimeError(f"Login appears to have failed. Page still shows password field. Excerpt: {err!r}")


def _scan_for_slots(page: Page) -> tuple[bool, str]:
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PWTimeout:
        pass

    # Switch to SuperSaaS's built-in "Available" (free) view — lists only bookable slots.
    try:
        page.evaluate("switch_view('free')")
    except Exception:
        pass
    page.wait_for_timeout(3000)

    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except PWTimeout:
        pass

    viewholder_text = page.locator("#viewholder").inner_text().strip()

    if "No available space found" in viewholder_text:
        return False, "Available view shows 'No available space found'."

    slot_count = page.locator("#viewholder a, #viewholder .achip").count()
    if slot_count > 0:
        return True, f"Available view shows {slot_count} bookable slot(s)!"

    # Fallback: any HH:MM time inside the availability view means something is listed.
    import re
    if re.search(r"\b([01]?\d|2[0-3]):[0-5]\d\b", viewholder_text):
        return True, "Available view contains time entries — slot(s) appear bookable."

    return False, "Available view empty but no explicit 'no availability' message — treating as unavailable."


def check_once(cfg: Config) -> CheckResult:
    DEBUG_DIR.mkdir(exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=cfg.headless)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        try:
            _login(page, cfg)
            available, summary = _scan_for_slots(page)
            page_url = page.url

            screenshot_path: str | None = None
            if available or cfg.debug_dump:
                screenshot_path = str(DEBUG_DIR / f"schedule_{ts}.png")
                page.screenshot(path=screenshot_path, full_page=True)
            if cfg.debug_dump:
                (DEBUG_DIR / f"schedule_{ts}.html").write_text(
                    page.content(), encoding="utf-8"
                )

            return CheckResult(
                available=available,
                summary=summary,
                screenshot_path=screenshot_path,
                page_url=page_url,
            )
        finally:
            context.close()
            browser.close()
