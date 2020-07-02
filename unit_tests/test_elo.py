from goratings.math.elo import EloEntry, elo_configure, elo_update


def test_elo_defaults():
    a = EloEntry(1200)
    b = EloEntry(1000)
    new_a = elo_update(a, b, 1)
    new_b = elo_update(b, a, 0)

    assert round(new_a.rating, 1) == 1207.7
    assert round(new_b.rating, 1) == 992.3


def test_elo_k30():
    elo_configure(k=30)

    a = EloEntry(1200)
    b = EloEntry(1000)
    new_a = elo_update(a, b, 1)
    new_b = elo_update(b, a, 0)

    assert round(new_a.rating, 1) == 1207.2
    assert round(new_b.rating, 1) == 992.8
