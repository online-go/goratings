__all__ = ["EloEntry", "elo_update", "elo_configure"]


K:float = 32.0

class EloEntry:
    rating: float

    def __init__(self, rating:float) -> None:
        self.rating = rating

    def expected(self, opponent: 'EloEntry') -> float:
        return 1 / (1 + 10 ** ((opponent.rating - self.rating) / 400))

    def __str__(self) -> str:
        return "%6.2f" % self.rating

def elo_update(
        player: EloEntry, opponent: EloEntry, outcome: float
) -> EloEntry:
    expected = player.expected(opponent)
    return EloEntry(player.rating + K * (outcome - expected))

def elo_configure(k:float = 32.0) -> None:
    global K
    K = k
