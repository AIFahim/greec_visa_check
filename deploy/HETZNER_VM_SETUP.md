# Deploy to a Hetzner Cloud VM (€4.51/month)

Real 24/7 Linux server with standard cron. Polls every 60 seconds. Most reliable option.

## 1. Sign up (~5 min)

1. Go to https://accounts.hetzner.com/signUp and create an account.
2. Verify email, then add a payment method (credit or debit card, SEPA direct debit, or PayPal). Hetzner's card validation is much less strict than Oracle's.
3. Once payment is verified, open the Cloud Console: https://console.hetzner.cloud/
4. Create a new **Project** (any name, e.g. `visa-bot`).

## 2. Upload an SSH key (first time only)

On Windows PowerShell:
```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\hetzner -N '""'
Get-Content $env:USERPROFILE\.ssh\hetzner.pub
```
Copy the printed `ssh-ed25519 ...` line.

In Hetzner console → **Security → SSH keys → Add SSH key** → paste → give it a name → Add.

## 3. Create the server (~2 min)

In your project → **Servers → Add Server**:

- **Location**: Nuremberg (Germany) — lowest latency to Ireland/UK. Any EU location is fine.
- **Image**: Ubuntu 22.04
- **Type**: **CX22** (shared vCPU, €4.51/month, 2 vCPU, 4 GB RAM, 40 GB disk). Plenty for this workload.
- **Networking**: leave IPv4 + IPv6 enabled.
- **SSH Keys**: tick the key you uploaded.
- **Name**: `greek-visa-bot` (or anything).
- Click **Create & Buy now**.

After ~30 sec the server appears with a public IPv4. Copy that IP.

## 4. SSH in

On Windows PowerShell:
```powershell
ssh -i $env:USERPROFILE\.ssh\hetzner root@<SERVER_IP>
```

You're now root on Ubuntu. (The installer script expects a non-root `ubuntu` user, so create one.)

```bash
adduser --disabled-password --gecos "" ubuntu
usermod -aG sudo ubuntu
mkdir -p /home/ubuntu/.ssh
cp /root/.ssh/authorized_keys /home/ubuntu/.ssh/
chown -R ubuntu:ubuntu /home/ubuntu/.ssh
echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu
exit
```

Now reconnect as `ubuntu`:
```powershell
ssh -i $env:USERPROFILE\.ssh\hetzner ubuntu@<SERVER_IP>
```

## 5. Run the installer

```bash
curl -fsSL https://raw.githubusercontent.com/AIFahim/greec_visa_check/main/deploy/install.sh | bash
```

## 6. Fill in `.env`, enable Telegram, start the timer

These steps are identical to the Oracle guide. See **sections 5, 6, 7, and 8** of [`ORACLE_VM_SETUP.md`](./ORACLE_VM_SETUP.md) — everything after "Install the checker" applies exactly the same on Hetzner.

Short version:
```bash
nano ~/greec_visa_check/.env      # fill in creds + AUTO_BOOK=true + CUTOFF=2026-06-01
sudo systemctl enable --now greek-visa-check.timer
journalctl -u greek-visa-check.service -f
```

## Costs

- Server CX22: €4.51/month (pro-rated hourly, so €0.006/hour — if you only need this for a few days, stop the server after booking and pay ~€0.15/day).
- Traffic: 20 TB included, you'll use <1 GB/month.
- No surprise charges.

## Stopping / deleting after you book

Once you've got your appointment, you can:
- **Stop billing immediately**: Hetzner console → right-click the server → **Delete**. Pro-rated to the hour.
- **Keep running**: cost is €0.006/hour (~€1.50/week).
