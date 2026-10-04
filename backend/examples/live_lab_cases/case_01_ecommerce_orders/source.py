"""
Order pricing and checkout domain logic (Case 01 — baseline implementation).
Designed for branch coverage: discounts, tax, shipping, coupons, loyalty, refunds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


TAX_RATE = 0.075
MEMBER_LINE_DISCOUNT = 0.10
MEMBER_HIGH_TOTAL_THRESHOLD = 500.0
MEMBER_HIGH_TOTAL_BONUS = 20.0
FREE_SHIPPING_SUBTOTAL = 250.0
FLAT_SHIPPING = 15.0
GIFT_WRAP_PER_LINE = 5.0
SAVE_COUPON_DISCOUNT = 10.0
MAX_LINES = 100
POINTS_PER_CURRENCY = 100.0


@dataclass
class LineItem:
    sku: str
    unit_price: float
    quantity: int
    gift_wrap: bool = False


@dataclass
class Order:
    lines: list[LineItem] = field(default_factory=list)
    is_member: bool = False
    coupon_code: str | None = None
    loyalty_points_to_redeem: int = 0
    status: str = "draft"

    def line_count(self) -> int:
        return len(self.lines)


def validate_line_item(item: LineItem) -> None:
    if not item.sku or not str(item.sku).strip():
        raise ValueError("SKU must be non-empty")
    if item.unit_price < 0:
        raise ValueError("unit price must be non-negative")
    if item.quantity <= 0:
        raise ValueError("quantity must be positive")


def validate_order_size(lines: Iterable[LineItem]) -> None:
    items = list(lines)
    if len(items) > MAX_LINES:
        raise ValueError("too many line items")


def line_subtotal(item: LineItem, is_member: bool) -> float:
    validate_line_item(item)
    base = item.unit_price * item.quantity
    if is_member:
        base *= 1.0 - MEMBER_LINE_DISCOUNT
    if item.gift_wrap:
        base += GIFT_WRAP_PER_LINE * item.quantity
    return base


def subtotal_before_tax(lines: list[LineItem], is_member: bool) -> float:
    validate_order_size(lines)
    if not lines:
        return 0.0
    total = 0.0
    for line in lines:
        total += line_subtotal(line, is_member)
    return total


def apply_coupon(subtotal: float, coupon_code: str | None) -> float:
    if not coupon_code:
        return subtotal
    code = coupon_code.strip().upper()
    if code.startswith("SAVE"):
        return max(0.0, subtotal - SAVE_COUPON_DISCOUNT)
    return subtotal


def shipping_cost(subtotal_after_discounts: float) -> float:
    if subtotal_after_discounts > FREE_SHIPPING_SUBTOTAL:
        return 0.0
    return FLAT_SHIPPING


def tax_amount(taxable_subtotal: float) -> float:
    if taxable_subtotal <= 0:
        return 0.0
    return taxable_subtotal * TAX_RATE


def loyalty_discount(subtotal: float, points: int, balance: int) -> tuple[float, int]:
    if points <= 0:
        return 0.0, balance
    if points > balance:
        raise ValueError("insufficient loyalty points")
    max_redeem_value = subtotal * 0.5
    value = points / POINTS_PER_CURRENCY
    if value > max_redeem_value:
        value = max_redeem_value
        points_used = int(value * POINTS_PER_CURRENCY)
    else:
        points_used = points
    new_balance = balance - points_used
    if new_balance < 0:
        raise ValueError("loyalty balance would go negative")
    return value, new_balance


def member_post_tax_bonus(total_before_bonus: float, is_member: bool) -> float:
    if is_member and total_before_bonus > MEMBER_HIGH_TOTAL_THRESHOLD:
        return MEMBER_HIGH_TOTAL_BONUS
    return 0.0


def checkout_total(
    lines: list[LineItem],
    is_member: bool,
    coupon_code: str | None = None,
    loyalty_points: int = 0,
    loyalty_balance: int = 0,
) -> float:
    """Compute final checkout total for an order."""
    if not lines:
        return 0.0
    sub = subtotal_before_tax(lines, is_member)
    sub = apply_coupon(sub, coupon_code)
    ship = shipping_cost(sub)
    tax = tax_amount(sub)
    running = sub + ship + tax
    discount_value, _ = loyalty_discount(sub, loyalty_points, loyalty_balance)
    running -= discount_value
    running -= member_post_tax_bonus(running, is_member)
    return round(running, 2)


def confirm_order(order: Order) -> Order:
    if not order.lines:
        raise ValueError("cannot confirm empty order")
    total = checkout_total(
        order.lines,
        order.is_member,
        order.coupon_code,
        order.loyalty_points_to_redeem,
        loyalty_balance=10_000,
    )
    if total < 0:
        raise ValueError("negative total")
    order.status = "confirmed"
    return order


def cancel_order(order: Order) -> Order:
    order.status = "cancelled"
    return order


def refund_line_quantity(original_qty: int, return_qty: int) -> float:
    if return_qty < 0:
        raise ValueError("return quantity negative")
    if return_qty > original_qty:
        raise ValueError("return exceeds purchased quantity")
    if original_qty == 0:
        return 0.0
    return return_qty / original_qty


def proportional_refund(line_total: float, original_qty: int, return_qty: int) -> float:
    ratio = refund_line_quantity(original_qty, return_qty)
    return round(line_total * ratio, 2)


def aggregate_sku_quantities(lines: list[LineItem]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for line in lines:
        totals[line.sku] = totals.get(line.sku, 0) + line.quantity
    return totals


def estimate_tax_report(lines: list[LineItem], is_member: bool) -> dict[str, float]:
    sub = subtotal_before_tax(lines, is_member)
    return {
        "taxable_subtotal": round(sub, 2),
        "tax": round(tax_amount(sub), 2),
        "shipping": shipping_cost(sub),
    }


def price_after_member_discount(unit_price: float, is_member: bool) -> float:
    if unit_price < 0:
        raise ValueError("price must be non-negative")
    if is_member:
        return unit_price * (1.0 - MEMBER_LINE_DISCOUNT)
    return unit_price


def bulk_order_flag(lines: list[LineItem], threshold_qty: int = 50) -> bool:
    agg = aggregate_sku_quantities(lines)
    return any(q >= threshold_qty for q in agg.values())


def draft_total_preview(order: Order) -> float:
    return checkout_total(
        order.lines,
        order.is_member,
        order.coupon_code,
        order.loyalty_points_to_redeem,
        loyalty_balance=10_000,
    )


def merge_lines(a: LineItem, b: LineItem) -> LineItem:
    if a.sku != b.sku:
        raise ValueError("cannot merge different SKUs")
    return LineItem(
        sku=a.sku,
        unit_price=(a.unit_price + b.unit_price) / 2.0,
        quantity=a.quantity + b.quantity,
        gift_wrap=a.gift_wrap or b.gift_wrap,
    )


def sanitize_coupon(code: str | None) -> str | None:
    if code is None:
        return None
    trimmed = code.strip()
    return trimmed if trimmed else None


def compute_gift_wrap_fees(lines: list[LineItem]) -> float:
    fee = 0.0
    for line in lines:
        if line.gift_wrap:
            fee += GIFT_WRAP_PER_LINE * line.quantity
    return fee


def is_empty_cart(lines: list[LineItem]) -> bool:
    return len(lines) == 0


def max_line_item_price(lines: list[LineItem]) -> float:
    if not lines:
        return 0.0
    return max(line.unit_price for line in lines)


def min_line_item_price(lines: list[LineItem]) -> float:
    if not lines:
        return 0.0
    return min(line.unit_price for line in lines)


def average_unit_price(lines: list[LineItem]) -> float:
    if not lines:
        return 0.0
    return sum(line.unit_price for line in lines) / len(lines)


def count_wrapped_lines(lines: list[LineItem]) -> int:
    return sum(1 for line in lines if line.gift_wrap)


def validate_and_checkout(
    lines: list[LineItem],
    is_member: bool,
    coupon: str | None = None,
) -> dict[str, float | str]:
    for line in lines:
        validate_line_item(line)
    validate_order_size(lines)
    total = checkout_total(lines, is_member, sanitize_coupon(coupon))
    return {"status": "ok", "total": total}
