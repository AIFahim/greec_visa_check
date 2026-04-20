# Greek Visa Slot Checker

Automation that watches the Greek Embassy in Dublin's SuperSaaS visa appointment calendar and emails the user the moment a bookable slot appears.

## Status

**Deployed and live.** Runs every 5 minutes on GitHub Actions at https://github.com/AIFahim/greec_visa_check.

## Architecture

- `checker.py` — Playwright-based scraper. Logs into SuperSaaS, calls `switch_view('free')` to open SuperSaaS's built-in "Available" view, then inspects `#viewholder`.
- `notifier.py` — Gmail SMTP sender (smtp.gmail.com:465 SSL) with optional screenshot attachment.
- `config.py` — loads creds from env (falls back to `.env` locally via python-dotenv).
- `run_once.py` — single-shot entrypoint called by the GitHub Actions cron. Persists notification state in `seen_state.json` so we email once per "available" transition.
- `main.py` — local loop version (`while True: check; sleep 300`), unused in production.
- `.github/workflows/check.yml` — cron `*/5 * * * *` + `workflow_dispatch` + push trigger. Caches Playwright Chromium and `seen_state.json` via `actions/cache`.
- `test_login.py`, `test_email.py` — local smoke-test scripts.

## How slot detection works

SuperSaaS calendar has a month/week/day/agenda/**Available** view. We switch to the Available view, which shows only bookable slots for the next ~100 days. The signal is the literal text inside `#viewholder`:

- `"No available space found"` (bold) → nothing bookable
- Anything else → slot(s) likely available; we count `.achip` / anchor elements for the summary

Do NOT rely on the `#noroom` div — it's a separate "(No available space found)" message that's hidden (`display:none`) in the Available view.

## Page structure notes (from debug dump on 2026-04-20)

- Login form: plain email + password fields on `/schedule/login/GreekEmbassyInDublin/Visas`. No CSRF. Success redirects to `/schedule/GreekEmbassyInDublin/Visas` and shows a green "Successfully logged in" banner.
- Post-login: view tabs are `<li onclick="switch_view('...')">`. Programmatic switch via `page.evaluate("switch_view('free')")` works.
- Slot rules (from embassy's posted legend): white = available, blue = booked, green day = no slots allocated. All visible blue `.achip` elements correspond to entries in the JS `app[]` array (existing reservations).

## Deployment

- Runs on GitHub Actions Ubuntu runner, Python 3.12, Playwright 1.48 Chromium.
- Secrets live in repo Secrets (settings → Secrets and variables → Actions):
  - `SUPERSAAS_EMAIL`, `SUPERSAAS_PASSWORD`
  - `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `NOTIFY_TO`
- State (`seen_state.json`) persisted across runs via `actions/cache` using a rolling `seen-state-<run_id>` key pattern with `restore-keys: seen-state-`.
- On check failure, `debug/` is uploaded as a run artifact (retained 7 days).

### Gotchas

- **`.env` has Windows CRLF line endings.** `bash source .env` captures `\r` into values and breaks passwords. Use `python-dotenv`'s `dotenv_values` when reading from scripts.
- **Gmail App Passwords** are 16 characters (optionally shown with spaces). `config.py` strips spaces. UCD/Outlook accounts don't work with smtp.gmail.com — if the user ever switches sender to UCD, change `notifier.py` to `smtp.office365.com:587` STARTTLS.
- **GitHub cron lag.** `*/5 * * * *` can slip 5-15 min during GitHub peak load. Acceptable here.
- **60-day inactivity pause.** GitHub auto-disables scheduled workflows after 60 days with no repo activity. A push re-enables.

## Running locally

```bash
cp .env.example .env    # then fill in creds
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe test_login.py   # verify SuperSaaS login + scan
.venv/Scripts/python.exe test_email.py   # verify Gmail SMTP
.venv/Scripts/python.exe main.py         # start 5-min loop locally
```

## Common debugging

- Check latest Actions runs: `gh run list -R AIFahim/greec_visa_check --limit 5`
- View failing-step log: `gh run view <run_id> -R AIFahim/greec_visa_check --log-failed`
- Force a full HTML+screenshot dump: set `DEBUG_DUMP=true` in `.env` and run `test_login.py`. Artifacts land in `debug/`.
- Trigger workflow manually: `gh workflow run check.yml -R AIFahim/greec_visa_check --ref main`

## What to be careful about

- Don't commit `.env`, `debug/`, `seen_state.json`, or `checker.log` — all gitignored.
- If you change the Playwright version, bump the cache key in `check.yml` (`pw-${{ runner.os }}-chromium-1.48.0`) so browsers are re-downloaded.
- The detector relies on the exact string `"No available space found"` appearing inside `#viewholder`. If SuperSaaS changes that wording, the check will silently start reporting false-positives. Re-run `test_login.py` with `DEBUG_DUMP=true` to refresh selectors.
