from abc import ABC, abstractmethod
from typing import List, Any, Dict

from model import Message


class ISubscriber(ABC):
    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        pass

    @abstractmethod
    def send_message(self, message: Message):
        pass

    @abstractmethod
    def send_messages(self, messages: List[Message]):
        pass
