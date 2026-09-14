from toyshop.utils import chunked, clamp, dedupe_preserve_order, last_n_values


def test_chunked():
    assert chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_dedupe_preserve_order():
    assert dedupe_preserve_order([1, 2, 1, 3, 2]) == [1, 2, 3]


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10


def test_last_n_values_within_bounds():
    assert last_n_values([1, 2, 3, 4], 2) == [4, 3]


def test_last_n_values_overrun():
    values = [1, 2, 3]
    result = last_n_values(values, 5)
    assert len(result) == 5
