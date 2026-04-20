"""Send a test email via the real notifier to verify Gmail SMTP works."""
from config import load
from notifier import send_email


def main() -> None:
    cfg = load()
    print(f"Sending test email from {cfg.gmail_address} to {cfg.notify_to}...")
    send_email(
        cfg,
        subject="Greek visa checker: SMTP test",
        body="If you received this, the Gmail SMTP config in your .env works. No action needed.",
    )
    print("Email sent successfully.")


if __name__ == "__main__":
    main()
