"""Inventory stock-level accounting for the toy shop service."""

from __future__ import annotations


def receive_stock(stock_by_sku: dict[str, int], sku: str, quantity: int) -> dict[str, int]:
    """Record newly received stock for a SKU, returning the updated map."""
    stock_by_sku[sku] = stock_by_sku.get(sku, 0) + quantity
    return stock_by_sku


def reserve(reserved_by_sku: dict[str, int], sku: str, quantity: int) -> dict[str, int]:
    """Reserve units of a SKU (e.g. for an in-flight order)."""
    reserved_by_sku[sku] = reserved_by_sku.get(sku, 0) + quantity
    return reserved_by_sku


def available_quantity(stock_by_sku: dict, reserved_by_sku: dict, sku: str) -> int:
    """Compute sellable quantity on hand for a SKU (stock minus reservations).

    A SKU with stock but no active reservations legitimately has no entry in
    ``reserved_by_sku`` - that is not stock data missing, it just means zero
    reserved.
    """
    on_hand = stock_by_sku[sku]
    # BUG: indexes reserved_by_sku directly, so a SKU with stock but zero
    # reservations (a very common case) raises KeyError instead of treating
    # "not reserved" as 0.
    reserved = reserved_by_sku[sku]
    return on_hand - reserved


def is_low_stock(stock_by_sku: dict[str, int], sku: str, threshold: int = 5) -> bool:
    """Return whether a SKU's on-hand stock is at or below a low-stock threshold."""
    return stock_by_sku.get(sku, 0) <= threshold


def restock_needed(stock_by_sku: dict[str, int], threshold: int = 5) -> list[str]:
    """List every SKU whose on-hand stock is at or below the threshold."""
    return [sku for sku, qty in stock_by_sku.items() if qty <= threshold]


def release_reservation(reserved_by_sku: dict[str, int], sku: str, quantity: int) -> dict[str, int]:
    """Release previously reserved units of a SKU back to available stock."""
    current = reserved_by_sku.get(sku, 0)
    reserved_by_sku[sku] = max(0, current - quantity)
    return reserved_by_sku


def transfer_stock(
    stock_by_sku: dict[str, int],
    from_warehouse: dict[str, int],
    to_warehouse: dict[str, int],
    sku: str,
    quantity: int,
) -> None:
    """Move stock for a SKU from one warehouse ledger to another.

    Both warehouse ledgers are updated in place; the shared ``stock_by_sku``
    total is unaffected since the goods stay within the business, just move
    location.
    """
    if from_warehouse.get(sku, 0) < quantity:
        raise ValueError(f"insufficient stock of {sku} at source warehouse")
    from_warehouse[sku] = from_warehouse.get(sku, 0) - quantity
    to_warehouse[sku] = to_warehouse.get(sku, 0) + quantity
    _ = stock_by_sku  # retained for signature symmetry with receive_stock


def total_units_on_hand(stock_by_sku: dict[str, int]) -> int:
    """Sum on-hand units across every SKU."""
    return sum(stock_by_sku.values())


def stock_valuation_cents(stock_by_sku: dict[str, int], unit_cost_cents: dict[str, int]) -> int:
    """Value current on-hand stock at unit cost, in cents.

    SKUs missing from ``unit_cost_cents`` are valued at zero rather than
    raising, since a missing cost entry usually means "not yet costed"
    rather than "this SKU doesn't exist".
    """
    total = 0
    for sku, quantity in stock_by_sku.items():
        total += quantity * unit_cost_cents.get(sku, 0)
    return total


def skus_out_of_stock(stock_by_sku: dict[str, int]) -> list[str]:
    """List SKUs that are present in the ledger but have zero units on hand."""
    return sorted(sku for sku, qty in stock_by_sku.items() if qty == 0)


def reorder_suggestion(stock_by_sku: dict[str, int], sku: str, target_level: int = 20) -> int:
    """Suggest how many units of a SKU to reorder to reach a target level."""
    on_hand = stock_by_sku.get(sku, 0)
    return max(0, target_level - on_hand)


def bulk_reserve(reserved_by_sku: dict[str, int], reservations: dict[str, int]) -> dict[str, int]:
    """Apply several reservations at once, e.g. all lines of one order."""
    for sku, quantity in reservations.items():
        reserve(reserved_by_sku, sku, quantity)
    return reserved_by_sku


def merge_stock_ledgers(*ledgers: dict[str, int]) -> dict[str, int]:
    """Combine several per-warehouse stock ledgers into one company-wide total."""
    merged: dict[str, int] = {}
    for ledger in ledgers:
        for sku, quantity in ledger.items():
            merged[sku] = merged.get(sku, 0) + quantity
    return merged


def normalize_sku(raw_sku: str) -> str:
    """Normalize a SKU string to the canonical upper-case, trimmed form."""
    return raw_sku.strip().upper()


def stock_summary_lines(stock_by_sku: dict[str, int]) -> list[str]:
    """Format a human-readable one-line-per-SKU stock summary, sorted by SKU."""
    return [f"{sku}: {qty} units on hand" for sku, qty in sorted(stock_by_sku.items())]


def apply_stock_adjustment(stock_by_sku: dict[str, int], sku: str, delta: int) -> dict[str, int]:
    """Apply a signed adjustment (e.g. from a stocktake correction)."""
    current = stock_by_sku.get(sku, 0)
    new_level = current + delta
    if new_level < 0:
        raise ValueError(f"adjustment would drive {sku} stock negative")
    stock_by_sku[sku] = new_level
    return stock_by_sku


def highest_stock_sku(stock_by_sku: dict[str, int]) -> str | None:
    """Return the SKU with the most units on hand, or None if empty."""
    if not stock_by_sku:
        return None
    return max(stock_by_sku, key=stock_by_sku.get)


def stock_turnover_ratio(units_sold: int, average_stock: float) -> float:
    """Compute a simple inventory turnover ratio for a reporting period."""
    if average_stock <= 0:
        return 0.0
    return round(units_sold / average_stock, 2)


def days_of_supply(on_hand: int, average_daily_demand: float) -> float:
    """Estimate how many days current stock will last at current demand."""
    if average_daily_demand <= 0:
        return float("inf")
    return round(on_hand / average_daily_demand, 1)


def audit_log_entry(sku: str, action: str, quantity: int) -> str:
    """Format a single inventory audit-log line for a stock movement."""
    return f"[inventory] {action} sku={sku} qty={quantity}"
