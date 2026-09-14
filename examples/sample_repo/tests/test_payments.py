from toyshop.payments import (
    apply_processing_fee,
    convert_from_minor_units,
    convert_to_minor_units,
    is_supported_currency,
    validate_amount,
)


def test_convert_to_minor_units_usd():
    assert convert_to_minor_units(19.99, "USD") == 1999


def test_convert_from_minor_units_round_trip():
    assert convert_from_minor_units(9200, "EUR") == 100.0


def test_is_supported_currency():
    assert is_supported_currency("GBP") is True
    assert is_supported_currency("AUD") is False


def test_apply_processing_fee():
    assert apply_processing_fee(10_000, fee_bps=250) == 10_250


def test_validate_amount():
    assert validate_amount(500) is True
    assert validate_amount(-1) is False
    assert validate_amount(0) is False


def test_convert_to_minor_units_unknown_currency():
    amount = 42.50
    result = convert_to_minor_units(amount, "AUD")
    assert result > 0
