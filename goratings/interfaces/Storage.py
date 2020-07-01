import abc

from goratings.math.glicko2 import Glicko2Entry

__all__ = ["Storage"]


class Storage(abc.ABC):
    @abc.abstractmethod
    def getGlicko2Entry(self, player_id: int) -> Glicko2Entry:
        raise NotImplementedError

    @abc.abstractmethod
    def setGlicko2Entry(self, player_id: int, entry: Glicko2Entry) -> None:
        raise NotImplementedError
