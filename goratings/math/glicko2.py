from math import exp, log, pi, sqrt
from typing import List, Tuple

__all__ = ["Glicko2Entry", "glicko2_update", "glicko2_configure"]


EPSILON = 0.000001
# TAO = 1.2
TAO = 0.5
LOSS = 0.0
DRAW = 0.5
WIN = 1.0
MAX_RD = 500.0
MIN_RD = 30.0
MIN_VOLATILITY = 0.01
MAX_VOLATILITY = 0.15
MIN_RATING = 100.0
MAX_RATING = 6000.0
PROVISIONAL_RATING_CUTOFF = 160.0
GLICKO2_SCALE = 173.7178
AGING_PERIOD_SECONDS = None


class Glicko2Entry:
    rating: float
    deviation: float
    volatility: float
    mu: float
    phi: float
    timestamp: int

    def __init__(self, rating: float = 1500, deviation: float = 350, volatility: float = 0.06, timestamp: int | None = None) -> None:
        self.rating = rating
        self.deviation = deviation
        self.volatility = volatility
        self.mu = (self.rating - 1500) / GLICKO2_SCALE
        self.phi = self.deviation / GLICKO2_SCALE
        self.timestamp = timestamp

    def __str__(self) -> str:
        return "%7.2f +- %6.2f (%.6f [%.4f]) @ %10d" % (
            self.rating,
            self.deviation,
            self.volatility,
            self.volatility * GLICKO2_SCALE,
            0 if self.timestamp is None else self.timestamp,
        )

    def copy(self, adjustment: (float, float) = (0.0, 0.0)) -> "Glicko2Entry":
        ret = Glicko2Entry(self.rating + adjustment[0], (self.deviation ** 2 + adjustment[1] ** 2) ** 0.5, self.volatility, self.timestamp,)
        return ret

    def expand_deviation_because_no_games_played(self, n_periods: int = 1) -> "Glicko2Entry":
        return self.expand_deviation(age=n_periods, override_aging_period=1)

    def after_aging_to_timestamp(self, timestamp: int | None, minus_one_period: bool = False) -> "Glicko2Entry":
        global AGING_PERIOD_SECONDS

        # Create copy with the new timestamp and expand the deviation if the
        # timestamp is moving forward.
        if timestamp and AGING_PERIOD_SECONDS and minus_one_period:
            timestamp = max(self.timestamp if self.timestamp else 0, timestamp - AGING_PERIOD_SECONDS)
        copy = self.copy()
        copy.timestamp = timestamp

        if copy.timestamp and self.timestamp and copy.timestamp > self.timestamp:
            copy.expand_deviation(age=copy.timestamp - self.timestamp)
        return copy

    def expand_deviation(self, age: int, override_aging_period: int | None = None) -> "Glicko2Entry":
        # Implementation as defined by [glicko2], but converted to closed form,
        # allowing deviation to expand continuously over fractional periods.
        #
        # [glicko2]: http://www.glicko.net/glicko/glicko2.pdf (note after step 8)
        global MAX_RD
        global MIN_RD

        phi_prime = _age_phi(self.phi, self.volatility, age, override_aging_period)
        self.deviation = min(MAX_RD, max(MIN_RD, GLICKO2_SCALE * phi_prime))
        self.phi = self.deviation / GLICKO2_SCALE

        return self

    def expected_win_probability(self, white: "Glicko2Entry", handicap_adjustment: (float, float), ignore_g: bool = False) -> float:
        # Implementation extracted from glicko2_update below.
        if not ignore_g:
            def g() -> float:
                return 1
        else:
            def g() -> float:
                return 1 / sqrt(1 + (3 * white.phi ** 2) / (pi ** 2))

        E = 1 / (1 + exp(-g() * (self.rating + handicap_adjustment[0] - white.rating) / GLICKO2_SCALE))
        return E


def _age_phi(phi: float, volatility: float, age: int | None, override_aging_period: int | None = None) -> float:
    # Implementation as defined by [glicko2], but converted to closed form,
    # allowing deviation to expand continuously over fractional periods.
    #
    # [glicko2]: http://www.glicko.net/glicko/glicko2.pdf (note after step 8)
    global AGING_PERIOD_SECONDS

    aging_factor = 1
    if age is not None:
        assert age >= 0
        aging_period = AGING_PERIOD_SECONDS if override_aging_period is None else override_aging_period
        if aging_period:
            assert aging_period >= 0
            aging_factor = float(age) / aging_period

    return sqrt(phi ** 2 + aging_factor * volatility ** 2)


def glicko2_update(player: Glicko2Entry, matches: List[Tuple[Glicko2Entry, int]],
                   timestamp: int | None = None) -> Glicko2Entry:
    # Implementation as defined by: http://www.glicko.net/glicko/glicko2.pdf
    if len(matches) == 0:
        return player.after_aging_to_timestamp(timestamp)

    # Expand the deviation due to inactivity, in case the last game was more
    # than a period ago.
    player = player.after_aging_to_timestamp(timestamp, minus_one_period=True);

    # step 1/2 implicitly done during Glicko2Entry construction

    # step 3 / 4, compute 'v' and delta
    v_sum = 0.0
    delta_sum = 0.0
    for m in matches:
        p = m[0].after_aging_to_timestamp(timestamp, minus_one_period=True)
        outcome = m[1]
        g_phi_j = 1 / sqrt(1 + (3 * p.phi ** 2) / (pi ** 2))
        E = 1 / (1 + exp(-g_phi_j * (player.mu - p.mu)))
        v_sum += g_phi_j ** 2 * E * (1 - E)
        delta_sum += g_phi_j * (outcome - E)

    v = 1.0 / v_sum if v_sum else 9999
    delta = v * delta_sum

    # step 5
    a = log(player.volatility ** 2)

    def f(x: float) -> float:
        ex = exp(x)
        return (ex * (delta ** 2 - player.phi ** 2 - v - ex) / (2 * ((player.phi ** 2 + v + ex) ** 2))) - (
            (x - a) / (TAO ** 2)
        )

    A = a
    if delta ** 2 > player.phi ** 2 + v:
        B = log(delta ** 2 - player.phi ** 2 - v)
    else:
        k = 1
        safety = 100
        while f(a - k * TAO) < 0 and safety > 0:  # pragma: no cover
            safety -= 1
            k += 1
        B = a - k * TAO

    fA = f(A)
    fB = f(B)
    safety = 100

    while abs(B - A) > EPSILON and safety > 0:
        C = A + (A - B) * fA / (fB - fA)
        fC = f(C)
        if fC * fB <= 0:
            A = B
            fA = fB
        else:
            fA = fA / 2
        B = C
        fB = fC

        safety -= 1

    new_volatility = exp(A / 2)

    # step 6
    phi_star = sqrt(player.phi ** 2 + new_volatility ** 2)

    # step 7
    phi_prime = 1 / sqrt(1 / phi_star ** 2 + 1 / v)
    mu_prime = player.mu + (phi_prime ** 2) * delta_sum

    # step 8
    ret = Glicko2Entry(
        rating=min(MAX_RATING, max(MIN_RATING, GLICKO2_SCALE * mu_prime + 1500)),
        deviation=min(MAX_RD, max(MIN_RD, GLICKO2_SCALE * phi_prime)),
        volatility=min(0.15, max(0.01, new_volatility)),
        timestamp=timestamp,
    )
    return ret


def glicko2_configure(tao: float, min_rd: float, max_rd: float, aging_period_days: float) -> None:
    global TAO
    global MIN_RD
    global MAX_RD
    global AGING_PERIOD_SECONDS

    TAO = tao
    MIN_RD = min_rd
    MAX_RD = max_rd
    AGING_PERIOD_SECONDS = int(aging_period_days * 24 * 60 * 60) if aging_period_days else None
