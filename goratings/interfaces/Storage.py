import abc
from typing import Any

__all__ = ["Storage"]


class Storage(abc.ABC):
    @abc.abstractmethod
    def get(self, player_id: int) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, player_id: int, entry: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_timeout_flag(self, player_id: int) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def set_timeout_flag(self, player_id: int, tf: bool) -> None:
        raise NotImplementedError
