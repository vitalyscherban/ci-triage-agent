"""Payment gateway currency conversion for the toy shop service."""

from __future__ import annotations

# Minor-unit conversion rate per major-currency unit, relative to USD cents.
_RATE_TABLE = {
    "USD": 100,
    "EUR": 92,
    "GBP": 79,
}

SUPPORTED_CURRENCIES = tuple(_RATE_TABLE)


def is_supported_currency(currency: str) -> bool:
    """Return whether a currency code has a configured conversion rate."""
    return currency in _RATE_TABLE


def convert_to_minor_units(amount: float, currency: str) -> int:
    """Convert a major-unit amount (e.g. dollars) to minor units (cents).

    Raises KeyError for a currency without a configured rate - callers should
    check ``is_supported_currency`` first, or catch the error and surface a
    clear "unsupported currency" message instead of letting it propagate.
    """
    # BUG: indexes the rate table directly instead of validating the currency
    # first (or using .get() with a clear fallback), so an unsupported
    # currency like "AUD" raises a raw KeyError instead of a helpful error.
    rate = _RATE_TABLE[currency]
    return round(amount * rate)


def convert_from_minor_units(amount_minor: int, currency: str) -> float:
    """Convert minor units (cents) back to a major-unit float amount."""
    rate = _RATE_TABLE.get(currency, 100)
    return round(amount_minor / rate, 2)


def apply_processing_fee(amount_minor: int, fee_bps: int = 250) -> int:
    """Apply a payment-processing fee, expressed in basis points (bps)."""
    fee = (amount_minor * fee_bps) // 10_000
    return amount_minor + fee


def validate_amount(amount_minor: int) -> bool:
    """A charge must be a positive integer number of minor units."""
    return isinstance(amount_minor, int) and amount_minor > 0


def apply_refund(amount_minor: int, refund_minor: int) -> int:
    """Compute the remaining charge amount after a partial or full refund."""
    if refund_minor > amount_minor:
        raise ValueError("refund cannot exceed the original charge amount")
    return amount_minor - refund_minor


def is_valid_card_number(card_number: str) -> bool:
    """Luhn checksum validation for a card number string of digits."""
    digits = [int(c) for c in card_number if c.isdigit()]
    if len(digits) < 8:
        return False
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def mask_card_number(card_number: str) -> str:
    """Mask all but the last four digits of a card number for display/logs."""
    digits = "".join(c for c in card_number if c.isdigit())
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


def generate_transaction_id(sequence: int, currency: str) -> str:
    """Build a deterministic, human-readable transaction identifier."""
    return f"txn-{currency.lower()}-{sequence:010d}"


def split_amount_evenly(amount_minor: int, parts: int) -> list[int]:
    """Split a minor-unit amount into ``parts`` shares, distributing any
    remainder across the first few shares so the shares sum exactly."""
    if parts <= 0:
        raise ValueError("parts must be positive")
    base, remainder = divmod(amount_minor, parts)
    return [base + 1 if i < remainder else base for i in range(parts)]


def total_with_fee(amount_minor: int, fee_bps: int = 250) -> int:
    """Convenience wrapper: apply the processing fee and return the total."""
    return apply_processing_fee(amount_minor, fee_bps)


def retry_delays_seconds(max_attempts: int = 5, base_delay: float = 0.5) -> list[float]:
    """Exponential-backoff delay schedule for retrying a failed payment call."""
    return [round(base_delay * (2**attempt), 2) for attempt in range(max_attempts)]


def is_currency_supported_case_insensitive(currency: str) -> bool:
    """Case-insensitive variant of :func:`is_supported_currency`."""
    return currency.upper() in _RATE_TABLE


def format_minor_units(amount_minor: int, currency: str) -> str:
    """Format a minor-unit amount for display in its major-unit currency."""
    major = convert_from_minor_units(amount_minor, currency)
    return f"{major:.2f} {currency.upper()}"


def combine_charges(charges_minor: list[int]) -> int:
    """Sum a list of minor-unit charges into a single settlement amount."""
    return sum(charges_minor)


def largest_charge(charges_minor: list[int]) -> int:
    """Return the largest single charge in a list, or 0 if the list is empty."""
    return max(charges_minor, default=0)


def gateway_status_message(success: bool, reason: str = "") -> str:
    """Render a short human-readable gateway response message."""
    if success:
        return "payment accepted"
    return f"payment declined: {reason}" if reason else "payment declined"
