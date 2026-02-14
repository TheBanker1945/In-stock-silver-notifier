# LEGACY: Kept as fallback. Primary deal evaluation is now handled by SilverStack dashboard.
import requests
import config


class TelegramNotifier:
    """Sends messages to a Telegram chat via the Bot API."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID

    def send(self, message: str) -> bool:
        """Send a text message to the configured Telegram chat.

        Returns True on success, False on failure.
        """
        url = self.API_URL.format(token=self.token)
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if not data.get("ok"):
                print(f"[Telegram] API returned not ok: {data}")
                return False

            print(f"[Telegram] Message sent successfully.")
            return True

        except requests.RequestException as e:
            print(f"[Telegram] Failed to send message: {e}")
            return False
