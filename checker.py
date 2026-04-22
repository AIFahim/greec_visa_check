import datetime as dt
import re
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
    booked: bool = False
    booking_summary: str = ""
    booked_when_text: str = ""


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

    if re.search(r"\b([01]?\d|2[0-3]):[0-5]\d\b", viewholder_text):
        return True, "Available view contains time entries — slot(s) appear bookable."

    return False, "Available view empty but no explicit 'no availability' message — treating as unavailable."


def _try_autobook(page: Page, cfg: Config) -> tuple[bool, str, str]:
    """Attempt to book the first available slot. Returns (success, summary, when_text)."""
    slot = page.locator(
        "#viewholder a, #viewholder [onclick*='bs(']"
    ).first

    if slot.count() == 0:
        return False, "Auto-book: no clickable slot element found in Available view.", ""

    when_text = ""
    try:
        slot.scroll_into_view_if_needed(timeout=5_000)
        when_text = slot.inner_text().strip()[:200]
        slot.click(timeout=10_000)
    except Exception as e:
        return False, f"Auto-book: failed to click slot — {e}", when_text

    dialog = page.locator("#reservation")
    try:
        dialog.wait_for(state="visible", timeout=10_000)
    except PWTimeout:
        return False, "Auto-book: reservation dialog did not open after clicking slot.", when_text

    start_val = ""
    finish_val = ""
    try:
        start_val = page.locator("#reservation_start_time").input_value(timeout=2_000) or ""
        finish_val = page.locator("#reservation_finish_time").input_value(timeout=2_000) or ""
    except Exception:
        pass
    dialog_when = f"{start_val} → {finish_val}".strip(" →")
    if dialog_when:
        when_text = dialog_when

    # Optional cutoff: if user set AUTO_BOOK_CUTOFF_DATE and slot is on/after it, bail.
    if cfg.auto_book_cutoff_date:
        slot_date = _parse_slot_date(start_val or when_text)
        if slot_date and slot_date >= cfg.auto_book_cutoff_date:
            try:
                page.locator("#reservation a.bttn-ghost, #reservation a.l-c").first.click(timeout=2_000)
            except Exception:
                pass
            return (
                False,
                f"Auto-book skipped: slot {slot_date.isoformat()} is on/after cutoff {cfg.auto_book_cutoff_date.isoformat()}.",
                when_text,
            )

    submit_btn = page.locator(
        '#reservation button[type="submit"], #reservation button:has-text("Create reservation")'
    ).first
    try:
        submit_btn.click(timeout=10_000)
    except Exception as e:
        return False, f"Auto-book: failed to submit reservation — {e}", when_text

    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PWTimeout:
        pass

    body = page.locator("body").inner_text()
    error_visible = False
    try:
        err_el = page.locator("#reservation_error")
        if err_el.count() > 0 and err_el.is_visible():
            err_text = err_el.inner_text().strip()
            if err_text:
                return False, f"Auto-book: SuperSaaS returned error — {err_text}", when_text
                error_visible = True
    except Exception:
        pass

    lowered = body.lower()
    success_markers = [
        "reservation created",
        "your reservation",
        "booking confirmed",
        "successfully",
        "confirmation",
    ]
    if any(m in lowered for m in success_markers) and not error_visible:
        return True, "Auto-book: reservation submitted and success indicator found.", when_text

    # Dialog closed and no visible error → treat as success (SuperSaaS often just closes the dialog).
    try:
        if not dialog.is_visible():
            return True, "Auto-book: reservation dialog closed without error — likely booked.", when_text
    except Exception:
        pass

    return False, "Auto-book: submitted but could not confirm success.", when_text


def _parse_slot_date(text: str) -> dt.date | None:
    if not text:
        return None
    patterns = [
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})",
    ]
    for p in patterns:
        m = re.search(p, text)
        if not m:
            continue
        try:
            if len(m.group(1)) == 4:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return dt.date(y, mo, d)
        except ValueError:
            continue
    return None


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

            booked = False
            booking_summary = ""
            booked_when = ""
            if available and cfg.auto_book:
                booked, booking_summary, booked_when = _try_autobook(page, cfg)

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
                booked=booked,
                booking_summary=booking_summary,
                booked_when_text=booked_when,
            )
        finally:
            context.close()
            browser.close()
