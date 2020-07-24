from goratings.math.gor import GorEntry, gor_configure, gor_update, gor_configure


def test_table_1():
    gor_configure(epsilon = 0)
    a = GorEntry(1800)
    assert round(a.expected_win_probability(GorEntry(1820)), 3) == 0.457
    assert round(a.expected_win_probability(GorEntry(1840)), 3) == 0.414
    assert round(a.expected_win_probability(GorEntry(1860)), 3) == 0.372
    assert round(a.expected_win_probability(GorEntry(1880)), 3) == 0.333

def test_example_3():
    gor_configure(epsilon = 0)

    ra = GorEntry(2400)
    rb = GorEntry(2400)

    na = gor_update(ra, rb, 1)
    nb = gor_update(rb, ra, 0)
    assert(round(na.rating, 1) == 2407.5)
    assert(round(nb.rating, 1) == 2392.5)


def test_example_4():
    gor_configure(epsilon = 0)

    ra = GorEntry(320)
    rb = GorEntry(400)

    na = gor_update(ra, rb, 1)
    assert(round(na.rating, 0) == 383)

    nb = gor_update(rb, ra, 0)
    assert(round(nb.rating, 0) == 340)


def test_example_5():
    gor_configure(epsilon = 0)

    ra = GorEntry(1850, 450)
    rb = GorEntry(2400)

    nb = gor_update(rb, ra, 0)
    assert(round(nb.rating, 0) == 2389)

    na = gor_update(ra, rb, 1)
    assert(round(na.rating, 0) == 1875)

