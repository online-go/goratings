import abc

from .GameAnalytics import GameAnalytics
from .GameRecord import GameRecord

__all__ = ["RatingSystem"]


class RatingSystem(abc.ABC):
    @abc.abstractmethod
    def process_game(self, game: GameRecord) -> GameAnalytics:
        raise NotImplementedError
