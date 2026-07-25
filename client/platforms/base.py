"""Base platform adapter."""

from abc import ABC, abstractmethod

from client.core.models import AppConfig, StreamInfo


class PlatformAdapter(ABC):
    name: str = "unknown"

    @abstractmethod
    def match(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_room(self, url: str, config: AppConfig) -> dict:
        raise NotImplementedError

    @abstractmethod
    def resolve_stream(self, room_data: dict, quality: str, config: AppConfig) -> StreamInfo:
        raise NotImplementedError
