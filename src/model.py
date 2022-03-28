from dataclasses import dataclass, field
from typing import List


@dataclass
class Message:
    author: str
    content: str
    link: str
    update_at: int
    images: List[str] = field(default_factory=list)

    def __str__(self):
        return "\n".join([
            f"Message(author={self.author}, link={self.link}, update_at={self.update_at},",
            f"content={self.content},"
            f"images={self.images}"
        ])
