from .GameRecord import GameRecord

__all__ = ["GameAnalytics"]


class GameAnalytics:
    '''
    This is intended as a base class for more detailed analytics, depending on
    what kinds of interesting information a rating system can provide.
    '''
    skipped: bool
    game: GameRecord

    def __init__(
        self,
        skipped: bool,
        game: GameRecord,
    ) -> None:
        self.skipped = skipped
        self.game = game
