"""Small checkout example for testing source, document, and flowchart uploads."""


def checkout_total(
    subtotal: float,
    is_member: bool,
    coupon_code: str | None = None,
) -> float:
    if subtotal < 0:
        raise ValueError("subtotal must be non-negative")

    discount_rate = 0.10 if is_member else 0.0
    if coupon_code == "SAVE10":
        discount_rate += 0.10

    discounted_subtotal = subtotal * (1 - discount_rate)
    shipping = 0.0 if discounted_subtotal >= 100 else 10.0
    return round(discounted_subtotal + shipping, 2)
