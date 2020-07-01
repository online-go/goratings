import abc
from .GameRecord import GameRecord
from .GameAnalytics import GameAnalytics

__all__ = ["RatingSystem"]


class RatingSystem(abc.ABC):
    @abc.abstractmethod
    def process_game(self, game: GameRecord) -> GameAnalytics:
        raise NotImplementedError
