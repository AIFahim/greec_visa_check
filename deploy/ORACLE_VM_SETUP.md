# Deploy to an Oracle Cloud Always Free VM

Polls every 60 seconds from a real Linux VM that GitHub's cron delays don't affect. Free forever.

## 1. Create the VM (~10 min in browser)

1. Sign up at https://www.oracle.com/cloud/free/ (credit card required for identity verification only — no charge on the Always Free tier).
2. In the console → **Compute → Instances → Create instance**.
3. Settings:
   - **Image**: Canonical Ubuntu 22.04
   - **Shape**: `VM.Standard.A1.Flex` (ARM Ampere, Always Free) with 1 OCPU and 6 GB memory. If A1 capacity is unavailable in your region, use `VM.Standard.E2.1.Micro` (AMD, also Always Free).
   - **Networking**: Assign a public IPv4.
   - **SSH keys**: Upload your public key OR let Oracle generate a key pair and **download the private key** — save it somewhere safe as `~/oracle-vm.key` (WSL) or `C:\Users\User\.ssh\oracle-vm.key` (Windows).
4. Click **Create** → wait ~2 min for the VM to reach "Running".
5. Copy the **Public IP address** from the instance details page.

## 2. Open port 22 (SSH) — usually already open

Default security lists already allow SSH. No action needed unless you later change them.

## 3. SSH in from your PC

From PowerShell on Windows:
```powershell
icacls C:\Users\User\.ssh\oracle-vm.key /inheritance:r /grant:r User:R
ssh -i C:\Users\User\.ssh\oracle-vm.key ubuntu@<VM_PUBLIC_IP>
```
(First command fixes key permissions so SSH will accept it.)

## 4. Install the checker (one command on the VM)

Once SSH'd in, run:

```bash
curl -fsSL https://raw.githubusercontent.com/AIFahim/greec_visa_check/main/deploy/install.sh | bash
```

This script will:
- Install Python 3 + git + Playwright system deps
- Clone https://github.com/AIFahim/greec_visa_check into `/home/ubuntu/greec_visa_check`
- Create a placeholder `.env`
- Install a systemd service + timer that runs `run_once.py` every 60 seconds

The script pauses before enabling the timer so you can fill in `.env` first.

## 5. Fill in .env on the VM

```bash
cd ~/greec_visa_check
nano .env
```

Paste / edit these values:

```
SUPERSAAS_URL=https://www.supersaas.com/schedule/login/GreekEmbassyInDublin/Visas
SUPERSAAS_EMAIL=md.fahim@ucdconnect.ie
SUPERSAAS_PASSWORD=<your SuperSaaS password>

GMAIL_ADDRESS=asif.iqbal.fahim.bd@gmail.com
GMAIL_APP_PASSWORD=<your 16-char Gmail app password>
NOTIFY_TO=asif.iqbal.fahim.bd@gmail.com

TELEGRAM_BOT_TOKEN=<see step 6>
TELEGRAM_CHAT_ID=<see step 6>

AUTO_BOOK=true
AUTO_BOOK_CUTOFF_DATE=2026-06-01

HEADLESS=true
DEBUG_DUMP=false
```

Save (Ctrl+O, Enter, Ctrl+X).

## 6. Set up Telegram (2 minutes on phone)

1. Open Telegram → search for **@BotFather** → send `/newbot`.
2. Pick a name and a username ending in `bot` (e.g. `greek_visa_asif_bot`).
3. BotFather replies with a token like `7123456789:AAF...`. Put that in `TELEGRAM_BOT_TOKEN`.
4. Search for your new bot in Telegram → open the chat → send any message (e.g. "hi").
5. On your PC, visit (replace `<TOKEN>`):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Find `"chat":{"id":XXXXXX,...}` in the JSON. That number is your `TELEGRAM_CHAT_ID`.

## 7. Enable the timer

Back on the VM:

```bash
sudo systemctl enable --now greek-visa-check.timer
systemctl list-timers | grep greek-visa
```

You should see it listed with a "next trigger" time ~60 seconds out.

## 8. Verify

Tail logs:
```bash
journalctl -u greek-visa-check.service -f
```

You should see one check every 60 seconds with `Check done: available=False | ...`. The first time a slot is detected, Telegram pings you instantly, and if `AUTO_BOOK=true` the bot attempts to book the first slot before the cutoff.

## Turning it off

```bash
sudo systemctl disable --now greek-visa-check.timer
```

## Re-deploy after code changes

On the VM:
```bash
cd ~/greec_visa_check && git pull && ~/.venv/bin/pip install -r requirements.txt
```

The timer picks up the new code automatically on the next run.
