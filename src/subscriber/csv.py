import os
import csv
import json
import traceback
from typing import List
from requests_html import HTMLSession

from . import ISubscriber
from . import Message


IMAGE_PATH = "images"
CSV_FILENAME = "index.csv"
CSV_HEADER = ["user", "content", "link", "update_at"]


def ensure_database_created(dirname: str):
    os.makedirs(dirname, exist_ok=True)
    os.makedirs(os.path.join(dirname, IMAGE_PATH), exist_ok=True)
    csv_file = os.path.join(os.path.join(dirname, CSV_FILENAME))
    if not os.path.exists(csv_file):
        with open(csv_file, mode="w+", encoding="utf8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()


class CsvSubscriber(ISubscriber):
    def __init__(self, config):
        self.base = config["path"]
        self.file = os.path.join(self.base, CSV_FILENAME)
        self.image_path = os.path.join(self.base, IMAGE_PATH)
        self.session = HTMLSession()
        ensure_database_created(self.base)

    def send_message(self, message: Message):
        ensure_database_created(self.base)
        with open(self.file, mode="a", encoding="utf8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writerow({
                "user": message.author,
                "content": json.dumps(message.content, ensure_ascii=False),
                "link": message.link,
                "update_at": message.update_at
            })
        for image in message.images:
            image_basename = os.path.basename(image)
            image_filename = os.path.join(self.image_path, image_basename)
            with open(image_filename, "wb+") as f:
                print(f"GET {image}")
                image_binary = self.session.get(image).content
                image_size_mb = len(image_binary) / 1024 / 1024
                f.write(image_binary)
                print(f"Saved image to {image_filename} ({image_size_mb:.2f}MiB)")

    # noinspection PyBroadException
    def send_messages(self, messages: List[Message]):
        print(f"Start writing {len(messages)} messages to csv...")
        for message in messages:
            try:
                self.send_message(message)
            except:
                print("Error sending message to csv")
                print(f"csv: {self.file}")
                print(f"images: {self.image_path}")
                print(f"Message: {message}")
                traceback.print_exc()
                continue
        print("Done writing csv")
