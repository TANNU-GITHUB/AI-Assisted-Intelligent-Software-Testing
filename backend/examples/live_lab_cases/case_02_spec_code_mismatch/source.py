"""
Order pricing (Case 02 — implementation does NOT match requirements.txt).
Constants intentionally differ from the spec in requirements.txt for mismatch testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Code uses 10% member discount; spec asks 15%
MEMBER_LINE_DISCOUNT = 0.10
# Code uses 7.5% tax on post-discount subtotal; spec asks 8% and post-discount only (same base but rate differs)
TAX_RATE = 0.075
# Code: free shipping over 500 subtotal; spec: over 300
FREE_SHIPPING_SUBTOTAL = 500.0
FLAT_SHIPPING = 15.0  # spec: 12 when not free
MEMBER_EXTRA_THRESHOLD = 500.0  # spec: 400 final total, 25 off
MEMBER_EXTRA_OFF = 20.0  # spec: 25
MAX_LINES = 100  # spec: 50
BULK_QTY_THRESHOLD = 50  # spec: 10 for 5% SKU discount — not implemented
SAVE_COUPON = 10.0


@dataclass
class LineItem:
    sku: str
    unit_price: float
    quantity: int
    country: str = "US"


@dataclass
class Order:
    lines: list[LineItem] = field(default_factory=list)
    is_member: bool = False
    coupon_code: str | None = None


def validate_line_item(item: LineItem) -> None:
    if not item.sku or not str(item.sku).strip():
        raise ValueError("SKU required")
    if item.unit_price < 0:
        raise ValueError("negative price")
    if item.quantity <= 0:
        raise ValueError("bad quantity")


def line_discounted_unit(price: float, is_member: bool) -> float:
    if is_member:
        return price * (1.0 - MEMBER_LINE_DISCOUNT)
    return price


def line_total(item: LineItem, is_member: bool) -> float:
    validate_line_item(item)
    unit = line_discounted_unit(item.unit_price, is_member)
    return unit * item.quantity


def subtotal(lines: list[LineItem], is_member: bool) -> float:
    if not lines:
        return 0.0
    if len(lines) > MAX_LINES:
        raise ValueError("too many lines")
    return sum(line_total(line, is_member) for line in lines)


def apply_tax(pre_discount_subtotal: float, post_discount_subtotal: float) -> float:
    # BUG vs spec: taxes pre-discount subtotal passed as first arg in checkout path
    base = pre_discount_subtotal  # spec says post-discount only
    return base * TAX_RATE if base > 0 else 0.0


def shipping(subtotal_after_discount: float, coupon: str | None) -> float:
    if coupon and coupon.upper().startswith("VIP"):
        return FLAT_SHIPPING  # spec: VIP removes shipping — not implemented
    if subtotal_after_discount > FREE_SHIPPING_SUBTOTAL:
        return 0.0
    return FLAT_SHIPPING


def international_fee(lines: list[LineItem]) -> float:
    # spec: 30 for non-US — not implemented
    return 0.0


def bulk_sku_discount(lines: list[LineItem], is_member: bool) -> float:
    # spec: 5% off line when qty >= 10 — stub returns 0
    return 0.0


def member_final_bonus(final_total: float, is_member: bool) -> float:
    if is_member and final_total > MEMBER_EXTRA_THRESHOLD:
        return MEMBER_EXTRA_OFF
    return 0.0


def checkout_total(
    lines: list[LineItem],
    is_member: bool,
    coupon_code: str | None = None,
) -> float:
    if not lines:
        return 0.0
    pre = sum(line.unit_price * line.quantity for line in lines)
    post = subtotal(lines, is_member)
    post -= bulk_sku_discount(lines, is_member)
    tax = apply_tax(pre, post)
    ship = shipping(post, coupon_code)
    total = post + tax + ship + international_fee(lines)
    total -= member_final_bonus(total, is_member)
    return round(total, 2)


def validate_country(code: str | None) -> None:
    if code is None:
        return
    if len(code) != 2 or not code.isupper():
        raise ValueError("invalid country")


def gift_message_ok(message: str) -> bool:
    return len(message) <= 200


def round_display(amount: float) -> float:
    return round(amount, 2)


def confirm(order: Order) -> Order:
    if not order.lines:
        raise ValueError("empty")
    checkout_total(order.lines, order.is_member, order.coupon_code)
    return order


def refund_ratio(returned: int, purchased: int) -> float:
    if returned > purchased:
        raise ValueError("too much returned")
    if purchased == 0:
        return 0.0
    return returned / purchased


def points_restore(refund_amount: float, points_per_dollar: float = 100.0) -> int:
    return int(refund_amount * points_per_dollar)


def sku_is_alnum(sku: str) -> bool:
    return sku.isalnum() and len(sku) <= 32


def count_distinct_skus(lines: list[LineItem]) -> int:
    return len({line.sku for line in lines})


def heaviest_line(lines: list[LineItem]) -> LineItem | None:
    if not lines:
        return None
    return max(lines, key=lambda line: line.unit_price * line.quantity)


def split_order(lines: list[LineItem], max_per: int = 25) -> list[list[LineItem]]:
    chunks: list[list[LineItem]] = []
    for index in range(0, len(lines), max_per):
        chunks.append(lines[index : index + max_per])
    return chunks


def estimate_checkout(lines: list[LineItem], member: bool) -> dict[str, float]:
    post = subtotal(lines, member)
    return {
        "subtotal": post,
        "tax": apply_tax(post, post),
        "shipping": shipping(post, None),
        "total": checkout_total(lines, member),
    }


def apply_save_coupon(total: float, code: str | None) -> float:
    if code and code.upper().startswith("SAVE"):
        return max(0.0, total - SAVE_COUPON)
    return total


def cart_weight_units(lines: list[LineItem]) -> int:
    return sum(line.quantity for line in lines)


def average_line_value(lines: list[LineItem], is_member: bool) -> float:
    if not lines:
        return 0.0
    return subtotal(lines, is_member) / len(lines)


def has_expensive_item(lines: list[LineItem], threshold: float = 1000.0) -> bool:
    return any(line.unit_price >= threshold for line in lines)


def normalize_sku(sku: str) -> str:
    return sku.strip().upper()


def duplicate_skus(lines: list[LineItem]) -> list[str]:
    seen: set[str] = set()
    dups: list[str] = []
    for line in lines:
        key = normalize_sku(line.sku)
        if key in seen:
            dups.append(key)
        seen.add(key)
    return dups


def merge_duplicate_skus(lines: list[LineItem]) -> list[LineItem]:
    merged: dict[str, LineItem] = {}
    for line in lines:
        key = normalize_sku(line.sku)
        if key not in merged:
            merged[key] = LineItem(key, line.unit_price, line.quantity, line.country)
        else:
            existing = merged[key]
            merged[key] = LineItem(
                key,
                (existing.unit_price + line.unit_price) / 2,
                existing.quantity + line.quantity,
                line.country,
            )
    return list(merged.values())
