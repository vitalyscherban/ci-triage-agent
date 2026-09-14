from toyshop.orders import (
    Cart,
    add_line,
    apply_bulk_discount,
    bulk_discount_rate,
    format_cents_as_currency,
)


def test_add_line_accumulates_subtotal():
    cart = Cart()
    add_line(cart, "SKU-1", 500, 3)
    assert cart.subtotal_cents == 1500
    assert cart.item_count == 3


def test_format_cents_as_currency():
    assert format_cents_as_currency(1234) == "$12.34"
    assert format_cents_as_currency(-50) == "-$0.50"


def test_bulk_discount_rate_below_smallest_tier_is_zero():
    assert bulk_discount_rate(1) == 0.0


def test_apply_bulk_discount():
    cart = Cart()
    add_line(cart, "SKU-1", 2400, 5)
    result = apply_bulk_discount(cart.subtotal_cents, cart.item_count)
    assert result < cart.subtotal_cents
