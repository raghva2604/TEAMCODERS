import os
import re
from pathlib import Path
import requests


BOT_TOKEN_PATTERN = re.compile(r"^\d+:[A-Za-z0-9_-]{35,}$")


def get_telegram_settings(env_path: str | None = None):
    if env_path is None:
        env_path = Path(__file__).resolve().parent.parent / ".env"

    env_file = Path(env_path)
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}:
                os.environ[key] = value

    return os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")


def validate_telegram_credentials(token: str, chat_id: str) -> tuple[bool, str]:
    if not token or not chat_id:
        return False, "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID"

    if not BOT_TOKEN_PATTERN.match(token):
        return False, "Telegram bot token looks invalid"

    if not str(chat_id).strip().lstrip("-").isdigit():
        return False, "Telegram chat ID must be numeric"

    return True, ""


def send_telegram_alert(message: str) -> tuple[bool, str]:
    token, chat_id = get_telegram_settings()
    valid, error = validate_telegram_credentials(token, chat_id)
    if not valid:
        print(f"[TELEGRAM] {error}")
        return False, error

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        if response.status_code != 200:
            error = f"send_telegram_alert failed: {response.status_code} {response.text}"
            print(f"[TELEGRAM] {error}")
            return False, error
        return True, ""
    except Exception as e:
        error = f"send_telegram_alert exception: {e}"
        print(f"[TELEGRAM] {error}")
        return False, error


def send_telegram_image(image_path: str) -> tuple[bool, str]:
    token, chat_id = get_telegram_settings()
    valid, error = validate_telegram_credentials(token, chat_id)
    if not valid:
        print(f"[TELEGRAM] {error}")
        return False, error

    if not os.path.exists(image_path):
        error = f"send_telegram_image file not found: {image_path}"
        print(f"[TELEGRAM] {error}")
        return False, error

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(image_path, "rb") as img:
            response = requests.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": "🚨 Unauthorized person detected!",
                },
                files={"photo": img},
                timeout=10,
            )
        if response.status_code != 200:
            error = f"send_telegram_image failed: {response.status_code} {response.text}"
            print(f"[TELEGRAM] {error}")
            return False, error
        return True, ""
    except Exception as e:
        error = f"send_telegram_image exception: {e}"
        print(f"[TELEGRAM] {error}")
        return False, error
