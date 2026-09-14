"""Order pricing and discount logic for the toy shop service."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OrderLine:
    sku: str
    unit_price_cents: int
    quantity: int

    @property
    def subtotal_cents(self) -> int:
        return self.unit_price_cents * self.quantity


@dataclass
class Cart:
    lines: list[OrderLine] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def subtotal_cents(self) -> int:
        return sum(line.subtotal_cents for line in self.lines)


# Discount rate (as a fraction of subtotal) by total item count in the cart.
_BULK_DISCOUNT_TABLE = {
    5: 0.02,
    10: 0.05,
    25: 0.10,
    50: 0.15,
}


def add_line(cart: Cart, sku: str, unit_price_cents: int, quantity: int) -> Cart:
    """Add a line item to a cart, returning the same cart for chaining."""
    cart.lines.append(OrderLine(sku=sku, unit_price_cents=unit_price_cents, quantity=quantity))
    return cart


def bulk_discount_rate(item_count: int) -> float:
    """Look up the applicable bulk-discount rate for a given item count.

    Falls back to 0 (no discount) for counts below the smallest tier.
    """
    tier = 0
    for threshold in sorted(_BULK_DISCOUNT_TABLE):
        if item_count >= threshold:
            tier = threshold
    return _BULK_DISCOUNT_TABLE.get(tier, 0.0)


def apply_bulk_discount(subtotal_cents: int, item_count: int) -> int:
    """Apply a per-item discount share proportional to bulk order size.

    Returns the discounted subtotal in cents.
    """
    discount_rate = bulk_discount_rate(item_count)
    # BUG: dividing the subtotal evenly across (item_count - item_count) items
    # is always a division by zero - this should divide by item_count.
    per_item_share = subtotal_cents / (item_count - item_count)
    discount_cents = per_item_share * discount_rate * item_count
    return int(subtotal_cents - discount_cents)


def total_after_discount(cart: Cart) -> int:
    """Compute the cart's final total in cents, discount applied."""
    if not cart.lines:
        return 0
    return apply_bulk_discount(cart.subtotal_cents, cart.item_count)


def format_cents_as_currency(amount_cents: int) -> str:
    """Format an integer cent amount as a human-readable dollar string."""
    sign = "-" if amount_cents < 0 else ""
    whole, cents = divmod(abs(amount_cents), 100)
    return f"{sign}${whole}.{cents:02d}"


# Sales-tax rate by two-letter region code; unlisted regions are untaxed.
_TAX_RATE_TABLE = {
    "CA": 0.0725,
    "NY": 0.04,
    "TX": 0.0625,
    "WA": 0.065,
}


def sales_tax_cents(subtotal_cents: int, region: str) -> int:
    """Compute sales tax owed on a subtotal for a given region."""
    rate = _TAX_RATE_TABLE.get(region.upper(), 0.0)
    return round(subtotal_cents * rate)


def shipping_cost_cents(total_weight_grams: int, expedited: bool = False) -> int:
    """Estimate shipping cost in cents from total order weight."""
    base = 500 + (total_weight_grams // 100) * 25
    return base * 2 if expedited else base


def order_summary_lines(cart: Cart) -> list[str]:
    """Format a human-readable one-line-per-item order summary."""
    return [
        f"{line.sku} x{line.quantity} @ {format_cents_as_currency(line.unit_price_cents)}"
        for line in cart.lines
    ]


def validate_cart(cart: Cart) -> list[str]:
    """Return a list of validation problems with a cart (empty if valid)."""
    problems = []
    if not cart.lines:
        problems.append("cart has no line items")
    for line in cart.lines:
        if line.quantity <= 0:
            problems.append(f"{line.sku}: quantity must be positive")
        if line.unit_price_cents < 0:
            problems.append(f"{line.sku}: unit price cannot be negative")
    return problems


def apply_coupon_code(subtotal_cents: int, code: str) -> int:
    """Apply a flat percentage discount for a known coupon code."""
    coupons = {"WELCOME10": 0.10, "SAVE20": 0.20}
    rate = coupons.get(code.upper(), 0.0)
    return round(subtotal_cents * (1 - rate))


def merge_carts(*carts: Cart) -> Cart:
    """Combine several carts' line items into a single new cart."""
    merged = Cart()
    for cart in carts:
        merged.lines.extend(cart.lines)
    return merged


def order_weight_grams(cart: Cart, unit_weight_grams: dict[str, int]) -> int:
    """Estimate total order weight, defaulting unknown SKUs to 200g each."""
    total = 0
    for line in cart.lines:
        total += unit_weight_grams.get(line.sku, 200) * line.quantity
    return total


def largest_line_item(cart: Cart) -> OrderLine | None:
    """Return the line item with the highest subtotal, or None if empty."""
    if not cart.lines:
        return None
    return max(cart.lines, key=lambda line: line.subtotal_cents)


def order_item_count_by_sku(cart: Cart) -> dict[str, int]:
    """Aggregate quantity ordered per SKU across all line items in a cart."""
    counts: dict[str, int] = {}
    for line in cart.lines:
        counts[line.sku] = counts.get(line.sku, 0) + line.quantity
    return counts


def estimate_delivery_days(expedited: bool, region: str) -> int:
    """Estimate delivery time in business days for a region and speed tier."""
    base_days = {"CA": 2, "NY": 3, "TX": 3, "WA": 2}.get(region.upper(), 5)
    return max(1, base_days // 2) if expedited else base_days


def order_receipt_text(cart: Cart, region: str) -> str:
    """Render a plain-text receipt for a completed order."""
    lines = order_summary_lines(cart)
    tax = sales_tax_cents(cart.subtotal_cents, region)
    total = cart.subtotal_cents + tax
    lines.append(f"tax: {format_cents_as_currency(tax)}")
    lines.append(f"total: {format_cents_as_currency(total)}")
    return "\n".join(lines)
