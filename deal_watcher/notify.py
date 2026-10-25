from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable

import requests


def render_digest(matches: Iterable[dict[str, object]]) -> str:
    lines = ["November Tech Deal Watcher found matching deals:", ""]
    for match in matches:
        status = "lowest price seen so far" if match["lowest"] else "not the lowest price seen"
        lines.extend([
            f"{match['item']}: ${match['price']:.2f} (target: ${match['target']:.2f})",
            f"Retailer: {match['retailer']} — {status}",
            str(match["link"]), "",
        ])
    return "\n".join(lines)


def send_digest(matches: list[dict[str, object]]) -> None:
    """Send one digest when configured; fail loudly so Actions reports notification errors."""
    if not matches:
        return
    channel = os.getenv("NOTIFICATION_CHANNEL", "").lower()
    body = render_digest(matches)
    if channel == "teams":
        webhook = os.environ["TEAMS_WEBHOOK_URL"]
        response = requests.post(webhook, json={"text": body}, timeout=20)
        response.raise_for_status()
    elif channel == "smtp":
        message = EmailMessage()
        message["Subject"] = f"{len(matches)} tech deal match(es)"
        message["From"] = os.environ["SMTP_FROM"]
        message["To"] = os.environ["SMTP_TO"]
        message.set_content(body)
        with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "465"))) as client:
            client.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            client.send_message(message)
    elif channel:
        raise ValueError("NOTIFICATION_CHANNEL must be 'teams' or 'smtp'")
    else:
        print(body)
