from goratings.math.glicko2 import Glicko2Entry, glicko2_configure, glicko2_update


def test_glicko2():
    glicko2_configure(
        tao=0.5, min_rd=10, max_rd=500,
    )

    player = Glicko2Entry(1500, 200, 0.06)
    a = Glicko2Entry(1400, 30, 0.06)
    b = Glicko2Entry(1550, 100, 0.06)
    c = Glicko2Entry(1700, 300, 0.06)
    player = glicko2_update(player, [(a, 1), (b, 0), (c, 0)])

    assert round(player.rating, 1) == 1464.1
    assert round(player.deviation, 1) == 151.5


def test_str():
    player = Glicko2Entry(1500, 200, 0.06)
    assert isinstance(str(player), str)


def test_expansion():
    player = Glicko2Entry(1500, 200, 0.06)
    player.expand_deviation_because_no_games_played(1)
    assert round(player.deviation, 1) == 200.3


def test_copy():
    player = Glicko2Entry(1500, 200, 0.06)
    copy = player.copy()
    assert copy.rating == player.rating
    assert copy.deviation == player.deviation
    assert copy.volatility == player.volatility
    assert copy.mu == player.mu
    assert copy.phi == player.phi


def test_expected_win_probability():
    player = Glicko2Entry(1500, 200, 0.06)
    assert player.expected_win_probability(player, 0) == 0.5


def test_nop():
    player = Glicko2Entry(1500, 200, 0.06)
    p = glicko2_update(player, [])
    assert p.rating == player.rating


def test_exercise():
    player = Glicko2Entry(1500, 200, 0.06)
    glicko2_update(
        player,
        [
            (Glicko2Entry(100, 100), 0),
            (Glicko2Entry(30000, 10000), 1),
            (Glicko2Entry(1500, 100), 1),
            (Glicko2Entry(1500, 100), 0),
        ],
    )
