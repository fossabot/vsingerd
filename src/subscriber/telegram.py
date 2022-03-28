import time
import requests
import traceback
import datetime
from typing import List, Dict

from . import ISubscriber
from . import Message


def format_message(message: Message) -> str:
    time_beijing = datetime.datetime.utcfromtimestamp(message.update_at) + datetime.timedelta(hours=8)
    time_text = time_beijing.strftime("北京时间 %Y-%m-%d %H:%M:%S")
    text = f"{message.author}: "
    if len(message.images) > 0:
        text += f'[{len(message.images)}图]'
    text += f"\n{time_text}\n{message.content}"
    return text


class TelegramSubscriber(ISubscriber):
    def __init__(self, config):
        self.token = config["token"]
        self.chat = config["chat"]
        self.endpoint_api = f"https://api.telegram.org/bot{self.token}"
        self.endpoint_log = f"https://api.telegram.org/bot****"

    def send_text_message(self, text: str, link: str):
        data = {
            "chat_id": self.chat, "text": text,
            "reply_markup": {
                "inline_keyboard": [[{"text": "🔗点击查看原微博", "url": link}]]
            }
        }
        self.request_telegram_api("sendMessage", data)

    def send_photo_message(self, urls: List[str]):
        for url in urls:
            data = {"chat_id": self.chat, "photo": url}
            print(f"Sending photo URL: {url}")
            self.request_telegram_api("sendPhoto", data)

    def request_telegram_api(self, api_name: str, data: Dict):
        retries = 3
        while retries > 0:
            retries = retries - 1
            print(f"POST {self.endpoint_log}/{api_name}", end="", flush=True)
            res = requests.post(f"{self.endpoint_api}/{api_name}", json=data)
            print(f" ({res.status_code})")
            time.sleep(1)
            if res.status_code == 200:
                return
            print("req >", data)
            print("res <", res.json())
            if res.status_code == 404:
                return
            if res.status_code == 420:
                time.sleep(10)
            if res.status_code == 429:
                retry_after = int(res.json().get("parameters", {}).get("retry_after", 10))
                print(f"HTTP 429, will sleep {retry_after}")
                time.sleep(retry_after)

    def send_message(self, message: Message):
        self.send_text_message(format_message(message), message.link)
        if len(message.images) < 3:
            for image in message.images:
                self.send_photo_message([image])
                return
        images_slice = int(len(message.images) / 2)
        self.send_photo_message(message.images[:images_slice])
        self.send_photo_message(message.images[images_slice:])

    # noinspection PyBroadException
    def send_messages(self, messages: List[Message]):
        print(f"Start sending {len(messages)} messages to Telegram...")
        for message in messages:
            try:
                self.send_message(message)
            except:
                print(f"Error sending message to telegram chat ${self.chat}")
                print(f"Message: {message}")
                traceback.print_exc()
                continue
        print("Done sending messages to Telegram")
