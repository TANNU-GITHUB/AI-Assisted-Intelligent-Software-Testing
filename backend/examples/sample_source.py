"""Demo module used to verify Phase 1 analysis."""


def calculate_discount(price: float, is_member: bool) -> float:
    if price < 0:
        raise ValueError("price must be non-negative")
    if is_member:
        return price * 0.9
    return price


def checkout_total(prices: list[float], is_member: bool) -> float:
    total = 0.0
    for price in prices:
        total += calculate_discount(price, is_member)
    if total > 500 and is_member:
        total -= 20
    return total
