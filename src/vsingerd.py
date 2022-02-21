import os
import csv
import sys
import time
import json
import requests
import traceback
from typing import List
from dataclasses import dataclass
from requests_html import HTMLSession
from bs4 import BeautifulSoup


class Indexer:
    csv_path = "data/index.csv"
    csv_header = ["user", "content", "link", "update_at"]

    @staticmethod
    def ensure_database_created():
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(Indexer.csv_path):
            with open("data/index.csv", mode="w+", encoding="utf8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=Indexer.csv_header)
                writer.writeheader()

    def __init__(self):
        Indexer.ensure_database_created()
        with open("data/index.csv", mode="r", encoding="utf8") as f:
            reader = csv.DictReader(f, fieldnames=Indexer.csv_header)
            self.database = [row for row in reader]

    def exist(self, link: str) -> bool:
        for row in self.database:
            if row["link"].strip() == link.strip():
                return True
        return False

    @staticmethod
    def write(message):
        Indexer.ensure_database_created()
        with open("data/index.csv", mode="a", encoding="utf8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=Indexer.csv_header, )
            writer.writerow({
                "user": message["user"],
                "content": json.dumps(message["content"], ensure_ascii=False),
                "link": message["link"],
                "update_at": time.time(),
            })


# noinspection PyBroadException
@dataclass
class Creeper:
    weibo_ids: List[int]
    telegram_token: str
    telegram_chat: int

    def __post_init__(self):
        self.telegram_endpoint = f"https://api.telegram.org/bot{self.telegram_token}"
        self.telegram_endpoint_log = f"https://api.telegram.org/bot****"
        self.session = HTMLSession()
        self.indexer = Indexer()

    def send_telegram_message(self, text: str, weibo_link: str):
        data = {
            "chat_id": self.telegram_chat,
            "text": text,
            "reply_markup": {
                "inline_keyboard": [[{"text":"🔗点击查看原微博", "url": weibo_link}]]
            },
        }
        print(f"POST {self.telegram_endpoint_log}/sendMessage", end="", flush=True)
        res = requests.post(f"{self.telegram_endpoint}/sendMessage", json=data)
        if res.status_code != 200:
                print("\n>", res.json())
        time.sleep(2)
        print(f" ({res.status_code})")

    def send_telegram_photos(self, photo_urls: List[str]):
        for url in photo_urls:
            data = {"chat_id": self.telegram_chat, "photo": url}
            print(f"POST {self.telegram_endpoint_log}/sendPhoto", end="", flush=True)
            res = requests.post(f"{self.telegram_endpoint}/sendPhoto", json=data)
            if res.status_code != 200:
                print("\n>", res.json())
            time.sleep(2)
            print(f" ({res.status_code})")

    def send_message(self, message: dict):
        text = f'{message["user"]}：'
        if len(message["images"]) > 0:
            text += f'[{len(message["images"])}图]'
        text += "\n" + message["content"]
        self.send_telegram_message(text, message["link"])
        if len(message["images"]) < 3:
            for image in message["images"]:
                self.send_telegram_photos([image])
                return
        images_slice = int(len(message["images"]) / 2)
        self.send_telegram_photos(message["images"][:images_slice])
        self.send_telegram_photos(message["images"][images_slice:])

    def save_message(self, message: dict):
        Indexer.write(message)
        os.makedirs("data/images", exist_ok=True)
        for image in message["images"]:
            basename = os.path.basename(image)
            with open(f"data/images/{basename}", "wb+") as f:
                print(f"GET {image}")
                f.write(self.session.get(image).content)

    def parse_activity_cards(self, weibo_id: int, activity_cards: List[dict]):
        messages = []
        for activity_card in activity_cards:
            tweet: dict = activity_card.get("mblog")
            if tweet is None:
                continue
            if tweet.get("isLongText"):
                try:
                    url = f"https://m.weibo.cn/statuses/show?id={tweet.get('bid')}"
                    print(f"GET {url}")
                    full_tweet = self.session.get(url).json()
                except:
                    continue
                tweet = full_tweet.get("data")
            message = self.tweet_to_message(weibo_id, tweet)
            if message is not None:
                messages.append(message)
        return messages

    def tweet_to_message(self, weibo_id: int, tweet: dict):
        tweet_link = f'https://weibo.com/{weibo_id}/{tweet.get("bid", "")}'
        if self.indexer.exist(tweet_link):
            return

        message = {
            "content": BeautifulSoup(tweet.get("text").replace("<br />", "\n"), "html.parser").get_text(),
            "images": list(filter(lambda url: url.strip() != "",
                                  [p.get("large", {}).get("url") for p in tweet.get("pics", [])])),
            "link": tweet_link,
            "user": tweet.get("user", {}).get("screen_name", "?")
        }

        if tweet.get('weibo_position') == 3:
            # 如果状态为3表示转发微博，附加上转发链，状态1为原创微博
            retweet = tweet.get("retweeted_status", {})
            retweet_username = retweet.get("user", {}).get("screen_name", "未知用户")
            retweet_content = retweet.get("raw_text", "原微博被夹了")
            message["title"] += f'@{retweet_username}: {retweet_content}'
        try:
            self.save_message(message)
        except:
            pass
        return message

    def run(self, weibo_id: int):
        print(time.strftime('%Y-%m-%d %H:%M:%S 执行完毕', time.localtime()))
        url = f"https://m.weibo.cn/api/container/getIndex?containerid=107603{weibo_id}"
        print(f"GET {url}")
        try:
            activity_cards = self.session.get(url).json().get("data", {}).get("cards", [])[::-1]
        except:
            print(f"Error UID {weibo_id}")
            return

        messages = self.parse_activity_cards(weibo_id, activity_cards)
        for message in messages:
            self.send_message(message)

    def run_all(self):
        for weibo_id in self.weibo_ids:
            try:
                self.run(weibo_id)
            except:
                print("发生了错误。")
                traceback.print_exc()
            print(f"已完成微博ID {weibo_id} 休息 15 秒")
            time.sleep(15)
        print(f"全部完成")


def die(message: str):
    print(message)
    sys.exit(-1)


if __name__ == '__main__':
    weibo_ids = [int(i.strip()) for i in os.getenv("CONFIG_WEIBO_IDS", "").strip().split(":")]
    if len(weibo_ids) <= 0:
        die("ERR: No ENV:CONFIG_WEIBO_IDS set")
    telegram_token = os.getenv("CONFIG_TG_TOKEN").strip() or die("ERR: Missing ENV:CONFIG_TG_TOKEN")
    telegram_chat = int(os.getenv("CONFIG_TG_CHAT").strip()) or die("ERR: Missing ENV:CONFIG_TG_CHAT")
    creeper = Creeper(weibo_ids, telegram_token, telegram_chat)
    creeper.run_all()

