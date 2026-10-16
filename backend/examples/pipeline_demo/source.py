"""Compact checkout module for Live Lab — branches, calls, and errors for coverage."""


def calculate_discount(price: float, is_member: bool) -> float:
    if price < 0:
        raise ValueError("price must be non-negative")
    if is_member:
        return round(price * 0.9, 2)
    return round(price, 2)


def shipping_fee(subtotal: float) -> float:
    if subtotal <= 0:
        return 0.0
    if subtotal < 100.0:
        return 15.0
    return 0.0


def validate_quantity(quantity: int) -> None:
    if quantity < 0:
        raise ValueError("quantity cannot be negative")
    if quantity == 0:
        raise ValueError("quantity must be positive")


def line_total(unit_price: float, quantity: int, is_member: bool) -> float:
    validate_quantity(quantity)
    unit = calculate_discount(unit_price, is_member)
    return round(unit * quantity, 2)


def checkout_total(prices: list[float], is_member: bool) -> float:
    if not prices:
        return 0.0
    total = 0.0
    for price in prices:
        total += calculate_discount(price, is_member)
    total += shipping_fee(total)
    if is_member and total > 500.0:
        total -= 20.0
    return round(total, 2)


def member_bonus_eligible(total: float, is_member: bool) -> bool:
    return is_member and total > 500.0


def describe_cart(prices: list[float], is_member: bool) -> str:
    if not prices:
        return "empty"
    total = checkout_total(prices, is_member)
    label = "member" if is_member else "guest"
    return f"{label}:{total}"
