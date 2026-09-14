from toyshop.inventory import (
    available_quantity,
    is_low_stock,
    receive_stock,
    reserve,
    restock_needed,
)


def test_receive_stock_accumulates():
    stock: dict[str, int] = {}
    receive_stock(stock, "SKU-1", 10)
    receive_stock(stock, "SKU-1", 5)
    assert stock["SKU-1"] == 15


def test_reserve_accumulates():
    reserved: dict[str, int] = {}
    reserve(reserved, "SKU-1", 3)
    reserve(reserved, "SKU-1", 2)
    assert reserved["SKU-1"] == 5


def test_is_low_stock():
    stock = {"SKU-1": 3}
    assert is_low_stock(stock, "SKU-1", threshold=5) is True
    assert is_low_stock(stock, "SKU-2", threshold=5) is True  # missing == 0


def test_restock_needed():
    stock = {"SKU-1": 2, "SKU-2": 40}
    assert restock_needed(stock, threshold=5) == ["SKU-1"]


def test_available_quantity_with_reservation():
    stock = {"SKU-1": 20}
    reserved = {"SKU-1": 4}
    assert available_quantity(stock, reserved, "SKU-1") == 16


def test_available_quantity_missing_reservation():
    stock = {"SKU-404": 12}
    reserved: dict = {}
    result = available_quantity(stock, reserved, "SKU-404")
    assert result == 12
