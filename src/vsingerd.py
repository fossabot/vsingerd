import os
import time
import traceback
from typing import List, Tuple
from datetime import datetime
from requests_html import HTMLSession
from bs4 import BeautifulSoup

from model import Message
from subscriber.csv import CsvSubscriber
from subscriber.telegram import TelegramSubscriber


class Creeper:
    def __init__(self, weibo_id: int, last_update: int):
        self.weibo_id = weibo_id
        self.last_update = last_update
        self.session = HTMLSession()

    def run(self) -> Tuple[List[Message], int]:
        print(time.strftime(f"%Y-%m-%d %H:%M:%S Start fetching Weibo UID {self.weibo_id}", time.localtime()))
        activity_cards = self.get_activity_cards()
        update_at = int(time.time())
        tweets = self.get_tweets(activity_cards)
        messages = self.get_messages(tweets)
        messages = list(filter(lambda m: m.update_at >= self.last_update, messages))
        return messages, update_at

    def get_activity_cards(self) -> List[dict]:
        url = f"https://m.weibo.cn/api/container/getIndex?containerid=107603{self.weibo_id}"
        print(f"GET {url}")
        activity_cards: List[dict] = self.session.get(url).json().get("data", {}).get("cards", [])[::-1]
        if activity_cards is None:
            raise Exception(f"Unable to get activity cards of UID {self.weibo_id}")
        return activity_cards

    def get_tweets(self, activity_cards: List[dict]) -> List[dict]:
        tweets = list()
        for activity_card in activity_cards:
            tweet_preview: dict = activity_card.get("mblog")
            if tweet_preview is None:
                print(f"A null tweet encountered when parsing activity cards of UID {self.weibo_id}")
                continue
            tweet = self.get_tweet(tweet_preview)
            if tweet.get("bid") is None:
                print(f"A a tweet of UID {self.weibo_id} has no id")
                continue
            tweets.append(tweet)
        return tweets

    # noinspection PyBroadException
    def get_tweet(self, tweet: dict) -> dict:
        if tweet.get("isLongText"):
            # 获取长微博完整内容
            print(f"Parsing long weibo of UID {self.weibo_id}")
            try:
                url = f"https://m.weibo.cn/statuses/show?id={tweet.get('bid')}"
                print(f"GET {url}")
                tweet = self.session.get(url).json().get("data")
            except:
                print(f"Unable to load lang weibo {tweet.get('bid')} of UID {self.weibo_id}")
                return {}
        return tweet

    # noinspection PyBroadException
    def get_messages(self, tweets: List[dict]) -> List[Message]:
        messages = list()
        for tweet in tweets:
            try:
                message = Message(
                    author=tweet.get("user", {}).get("screen_name", f"[无法获取用户名] (uid:${self.weibo_id})"),
                    content=self.parse_tweet_text(tweet),
                    link=f"https://weibo.com/{self.weibo_id}/{tweet.get('bid')}",
                    update_at=int(datetime.strptime(tweet.get("created_at"), "%a %b %d %H:%M:%S %z %Y").timestamp()),
                    images=list(filter(
                        lambda url: url.strip() != "",
                        [p.get("large", {}).get("url") for p in tweet.get("pics", [])])
                    )
                )

                if tweet.get('weibo_position') == 3:
                    # 如果状态为3表示转发微博，附加上转发链，状态1 为原创微博
                    retweet = tweet.get("retweeted_status", {})
                    retweet_username = retweet.get("user", {}).get("screen_name", "未知用户")
                    retweet_content = retweet.get("raw_text", "[原微博被夹了]")
                    message.content += f'@{retweet_username}: {retweet_content}'
                if message.content.strip() == "":
                    message.content = "[内容为空]"
                messages.append(message)
            except:
                print(f"Error parsing tweet {tweet.get('bid')} of UID {self.weibo_id} to message")
                continue
        return messages

    @staticmethod
    def parse_tweet_text(tweet: dict) -> str:
        text = tweet.get("text", "")
        if text.strip() == "":
            text = tweet.get("raw_text")
        return BeautifulSoup(text.replace("<br />", "\n"), "html.parser").get_text()


def basedir() -> str:
    return os.path.abspath(os.path.dirname(__file__))


def get_last_update_filename(file_id: int) -> str:
    dirname = os.path.join(basedir(), "last_update")
    os.makedirs(dirname, exist_ok=True)
    file = os.path.join(dirname, f"{file_id}.last_update")
    return file


def read_last_update(file_id: int) -> int:
    file = get_last_update_filename(file_id)
    if not os.path.exists(file):
        return 0
    with open(file, encoding="utf-8") as f:
        return int(f.read())


def write_last_update(file_id: int, timestamp: int):
    file = get_last_update_filename(file_id)
    with open(file, "w+", encoding="utf-8") as f:
        f.write(str(timestamp))


def main():
    config = {
        "weibo": {
            "ids": [int(i.strip()) for i in os.getenv("CONFIG_WEIBO_IDS", "").strip().split(":")]
        },
        "telegram": {
            "enable": (os.getenv("CONFIG_TG_DISABLE") is None),
            "token": os.getenv("CONFIG_TG_TOKEN").strip(),
            "chat": int(os.getenv("CONFIG_TG_CHAT").strip())
        },
        "csv": {
            "enable": (os.getenv("CONFIG_CSV_DISABLE") is None),
            "path": os.getenv("CONFIG_CSV_PATH", os.path.join(basedir(), "data")).strip()
        },
        "mysql": {
            "enable": (os.getenv("CONFIG_MYSQL") is not None),
            "file_storage": os.getenv("CONFIG_MYSQL_FILE_STORAGE")
        }
    }
    for weibo_id in config["weibo"]["ids"]:
        # noinspection PyBroadException
        try:
            last_update = read_last_update(weibo_id)
            creeper = Creeper(weibo_id, last_update)
            messages, new_timestamp = creeper.run()
            write_last_update(weibo_id, new_timestamp)
            print(f"Got {len(messages)} for UID {weibo_id}")
            if config["csv"]["enable"]:
                CsvSubscriber(config["csv"]).send_messages(messages)
            if config["telegram"]["enable"]:
                TelegramSubscriber(config["telegram"]).send_messages(messages)
        except:
            print(f"Error running creeper of weibo id ${weibo_id}")
            traceback.print_exc()
            continue


if __name__ == "__main__":
    main()
