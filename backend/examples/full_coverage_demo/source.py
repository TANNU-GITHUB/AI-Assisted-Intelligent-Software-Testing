"""
Retail operations module — full-coverage demo for AI Testing Live Lab.

Six business areas: pricing, inventory, shipping, payment, loyalty, returns.
Each rule function is independent, branch-heavy, and testable in isolation.
"""

from __future__ import annotations

MAX_LINE_QTY = 10_000
MIN_PRICE = 0.0
MEMBER_DISCOUNT = 0.10
BULK_DISCOUNT_THRESHOLD = 50
BULK_DISCOUNT_RATE = 0.05


def _reject_negative(amount: float, field: str = "amount") -> None:
    if amount < 0:
        raise ValueError(f"{field} must be non-negative")


def _round_money(value: float) -> float:
    return round(float(value), 2)



# --- PRICING ---

def pricing_rule_001(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #1."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def pricing_rule_002(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #2."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def pricing_rule_003(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #3."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def pricing_rule_004(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #4."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def pricing_rule_005(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #5."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def pricing_rule_006(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #6."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def pricing_rule_007(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #7."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def pricing_rule_008(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #8."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def pricing_rule_009(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #9."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def pricing_rule_010(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #10."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def pricing_rule_011(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #11."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def pricing_rule_012(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #12."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def pricing_rule_013(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #13."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def pricing_rule_014(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #14."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def pricing_rule_015(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #15."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def pricing_rule_016(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #16."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def pricing_rule_017(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #17."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def pricing_rule_018(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #18."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def pricing_rule_019(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #19."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def pricing_rule_020(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #20."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def pricing_rule_021(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #21."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def pricing_rule_022(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #22."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def pricing_rule_023(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #23."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def pricing_rule_024(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #24."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def pricing_rule_025(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #25."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def pricing_rule_026(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #26."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def pricing_rule_027(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #27."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def pricing_rule_028(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #28."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def pricing_rule_029(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #29."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def pricing_rule_030(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #30."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def pricing_rule_031(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #31."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def pricing_rule_032(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #32."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def pricing_rule_033(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #33."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def pricing_rule_034(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply pricing business rule #34."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def compute_pricing_bundle(quantity: float, is_member: bool) -> float:
    """Sum first ten pricing rules (integration path)."""
    _reject_negative(quantity, 'quantity')
    parts = [
        pricing_rule_001(quantity, is_member),
        pricing_rule_002(quantity, is_member),
        pricing_rule_003(quantity, is_member),
        pricing_rule_004(quantity, is_member),
        pricing_rule_005(quantity, is_member),
        pricing_rule_006(quantity, is_member),
        pricing_rule_007(quantity, is_member),
        pricing_rule_008(quantity, is_member),
        pricing_rule_009(quantity, is_member),
        pricing_rule_010(quantity, is_member),
    ]
    return _round_money(sum(parts))


# --- INVENTORY ---

def inventory_rule_001(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #1."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def inventory_rule_002(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #2."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def inventory_rule_003(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #3."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def inventory_rule_004(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #4."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def inventory_rule_005(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #5."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def inventory_rule_006(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #6."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def inventory_rule_007(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #7."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def inventory_rule_008(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #8."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def inventory_rule_009(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #9."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def inventory_rule_010(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #10."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def inventory_rule_011(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #11."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def inventory_rule_012(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #12."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def inventory_rule_013(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #13."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def inventory_rule_014(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #14."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def inventory_rule_015(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #15."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def inventory_rule_016(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #16."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def inventory_rule_017(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #17."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def inventory_rule_018(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #18."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def inventory_rule_019(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #19."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def inventory_rule_020(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #20."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def inventory_rule_021(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #21."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def inventory_rule_022(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #22."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def inventory_rule_023(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #23."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def inventory_rule_024(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #24."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def inventory_rule_025(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #25."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def inventory_rule_026(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #26."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def inventory_rule_027(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #27."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def inventory_rule_028(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #28."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def inventory_rule_029(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #29."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def inventory_rule_030(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #30."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def inventory_rule_031(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #31."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def inventory_rule_032(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #32."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def inventory_rule_033(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #33."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def inventory_rule_034(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply inventory business rule #34."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def compute_inventory_bundle(quantity: float, is_member: bool) -> float:
    """Sum first ten inventory rules (integration path)."""
    _reject_negative(quantity, 'quantity')
    parts = [
        inventory_rule_001(quantity, is_member),
        inventory_rule_002(quantity, is_member),
        inventory_rule_003(quantity, is_member),
        inventory_rule_004(quantity, is_member),
        inventory_rule_005(quantity, is_member),
        inventory_rule_006(quantity, is_member),
        inventory_rule_007(quantity, is_member),
        inventory_rule_008(quantity, is_member),
        inventory_rule_009(quantity, is_member),
        inventory_rule_010(quantity, is_member),
    ]
    return _round_money(sum(parts))


# --- SHIPPING ---

def shipping_rule_001(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #1."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def shipping_rule_002(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #2."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def shipping_rule_003(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #3."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def shipping_rule_004(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #4."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def shipping_rule_005(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #5."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def shipping_rule_006(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #6."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def shipping_rule_007(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #7."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def shipping_rule_008(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #8."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def shipping_rule_009(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #9."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def shipping_rule_010(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #10."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def shipping_rule_011(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #11."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def shipping_rule_012(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #12."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def shipping_rule_013(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #13."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def shipping_rule_014(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #14."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def shipping_rule_015(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #15."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def shipping_rule_016(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #16."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def shipping_rule_017(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #17."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def shipping_rule_018(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #18."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def shipping_rule_019(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #19."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def shipping_rule_020(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #20."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def shipping_rule_021(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #21."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def shipping_rule_022(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #22."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def shipping_rule_023(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #23."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def shipping_rule_024(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #24."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def shipping_rule_025(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #25."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def shipping_rule_026(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #26."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def shipping_rule_027(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #27."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def shipping_rule_028(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #28."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def shipping_rule_029(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #29."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def shipping_rule_030(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #30."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def shipping_rule_031(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #31."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def shipping_rule_032(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #32."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def shipping_rule_033(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #33."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def shipping_rule_034(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply shipping business rule #34."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def compute_shipping_bundle(quantity: float, is_member: bool) -> float:
    """Sum first ten shipping rules (integration path)."""
    _reject_negative(quantity, 'quantity')
    parts = [
        shipping_rule_001(quantity, is_member),
        shipping_rule_002(quantity, is_member),
        shipping_rule_003(quantity, is_member),
        shipping_rule_004(quantity, is_member),
        shipping_rule_005(quantity, is_member),
        shipping_rule_006(quantity, is_member),
        shipping_rule_007(quantity, is_member),
        shipping_rule_008(quantity, is_member),
        shipping_rule_009(quantity, is_member),
        shipping_rule_010(quantity, is_member),
    ]
    return _round_money(sum(parts))


# --- PAYMENT ---

def payment_rule_001(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #1."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def payment_rule_002(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #2."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def payment_rule_003(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #3."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def payment_rule_004(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #4."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def payment_rule_005(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #5."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def payment_rule_006(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #6."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def payment_rule_007(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #7."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def payment_rule_008(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #8."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def payment_rule_009(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #9."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def payment_rule_010(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #10."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def payment_rule_011(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #11."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def payment_rule_012(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #12."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def payment_rule_013(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #13."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def payment_rule_014(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #14."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def payment_rule_015(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #15."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def payment_rule_016(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #16."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def payment_rule_017(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #17."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def payment_rule_018(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #18."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def payment_rule_019(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #19."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def payment_rule_020(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #20."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def payment_rule_021(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #21."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def payment_rule_022(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #22."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def payment_rule_023(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #23."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def payment_rule_024(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #24."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def payment_rule_025(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #25."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def payment_rule_026(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #26."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def payment_rule_027(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #27."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def payment_rule_028(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #28."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def payment_rule_029(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #29."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def payment_rule_030(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #30."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def payment_rule_031(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #31."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def payment_rule_032(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #32."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def payment_rule_033(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #33."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def payment_rule_034(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply payment business rule #34."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def compute_payment_bundle(quantity: float, is_member: bool) -> float:
    """Sum first ten payment rules (integration path)."""
    _reject_negative(quantity, 'quantity')
    parts = [
        payment_rule_001(quantity, is_member),
        payment_rule_002(quantity, is_member),
        payment_rule_003(quantity, is_member),
        payment_rule_004(quantity, is_member),
        payment_rule_005(quantity, is_member),
        payment_rule_006(quantity, is_member),
        payment_rule_007(quantity, is_member),
        payment_rule_008(quantity, is_member),
        payment_rule_009(quantity, is_member),
        payment_rule_010(quantity, is_member),
    ]
    return _round_money(sum(parts))


# --- LOYALTY ---

def loyalty_rule_001(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #1."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def loyalty_rule_002(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #2."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def loyalty_rule_003(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #3."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def loyalty_rule_004(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #4."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def loyalty_rule_005(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #5."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def loyalty_rule_006(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #6."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def loyalty_rule_007(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #7."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def loyalty_rule_008(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #8."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def loyalty_rule_009(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #9."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def loyalty_rule_010(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #10."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def loyalty_rule_011(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #11."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def loyalty_rule_012(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #12."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def loyalty_rule_013(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #13."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def loyalty_rule_014(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #14."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def loyalty_rule_015(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #15."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def loyalty_rule_016(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #16."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def loyalty_rule_017(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #17."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def loyalty_rule_018(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #18."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def loyalty_rule_019(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #19."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def loyalty_rule_020(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #20."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def loyalty_rule_021(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #21."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def loyalty_rule_022(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #22."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def loyalty_rule_023(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #23."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def loyalty_rule_024(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #24."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def loyalty_rule_025(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #25."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def loyalty_rule_026(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #26."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def loyalty_rule_027(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #27."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def loyalty_rule_028(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #28."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def loyalty_rule_029(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #29."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def loyalty_rule_030(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #30."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def loyalty_rule_031(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #31."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def loyalty_rule_032(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #32."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def loyalty_rule_033(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #33."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def loyalty_rule_034(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply loyalty business rule #34."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def compute_loyalty_bundle(quantity: float, is_member: bool) -> float:
    """Sum first ten loyalty rules (integration path)."""
    _reject_negative(quantity, 'quantity')
    parts = [
        loyalty_rule_001(quantity, is_member),
        loyalty_rule_002(quantity, is_member),
        loyalty_rule_003(quantity, is_member),
        loyalty_rule_004(quantity, is_member),
        loyalty_rule_005(quantity, is_member),
        loyalty_rule_006(quantity, is_member),
        loyalty_rule_007(quantity, is_member),
        loyalty_rule_008(quantity, is_member),
        loyalty_rule_009(quantity, is_member),
        loyalty_rule_010(quantity, is_member),
    ]
    return _round_money(sum(parts))


# --- RETURNS ---

def returns_rule_001(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #1."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def returns_rule_002(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #2."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def returns_rule_003(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #3."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def returns_rule_004(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #4."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def returns_rule_005(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #5."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def returns_rule_006(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #6."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def returns_rule_007(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #7."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def returns_rule_008(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #8."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def returns_rule_009(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #9."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def returns_rule_010(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #10."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def returns_rule_011(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #11."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def returns_rule_012(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #12."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def returns_rule_013(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #13."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def returns_rule_014(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #14."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def returns_rule_015(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #15."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def returns_rule_016(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #16."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def returns_rule_017(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #17."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def returns_rule_018(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #18."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def returns_rule_019(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #19."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def returns_rule_020(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #20."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def returns_rule_021(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #21."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def returns_rule_022(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #22."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def returns_rule_023(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #23."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def returns_rule_024(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #24."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def returns_rule_025(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #25."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def returns_rule_026(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #26."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def returns_rule_027(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #27."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def returns_rule_028(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #28."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def returns_rule_029(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #29."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def returns_rule_030(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #30."""
    _reject_negative(quantity, 'quantity')
    if quantity == 0:
        return 0.0
    base = quantity * 10.0
    if is_member:
        base *= 1.0 - MEMBER_DISCOUNT
    return _round_money(base)

def returns_rule_031(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #31."""
    _reject_negative(quantity, 'quantity')
    if quantity > BULK_DISCOUNT_THRESHOLD:
        discounted = quantity * (1.0 - BULK_DISCOUNT_RATE)
    else:
        discounted = quantity
    if premium and is_member:
        discounted *= 0.92
    return _round_money(discounted)

def returns_rule_032(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #32."""
    _reject_negative(quantity, 'quantity')
    total = 0.0
    for step in range(int(min(quantity, 5))):
        total += (step + 1) * 2.0
    if is_member:
        total -= 1.5
    if total < 0:
        total = 0.0
    return _round_money(total)

def returns_rule_033(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #33."""
    _reject_negative(quantity, 'quantity')
    if quantity < 1:
        raise ValueError('quantity must be at least 1 for this rule')
    fee = 2.5
    if premium:
        fee += 1.0
    if is_member:
        fee *= 0.5
    return _round_money(quantity * 3.0 + fee)

def returns_rule_034(quantity: float, is_member: bool, premium: bool = False) -> float:
    """Apply returns business rule #34."""
    _reject_negative(quantity, 'quantity')
    tier = 'standard'
    if quantity >= 100:
        tier = 'gold'
    elif quantity >= 25:
        tier = 'silver'
    multiplier = {'standard': 1.0, 'silver': 0.97, 'gold': 0.94}[tier]
    if is_member:
        multiplier -= 0.02
    return _round_money(quantity * multiplier)

def compute_returns_bundle(quantity: float, is_member: bool) -> float:
    """Sum first ten returns rules (integration path)."""
    _reject_negative(quantity, 'quantity')
    parts = [
        returns_rule_001(quantity, is_member),
        returns_rule_002(quantity, is_member),
        returns_rule_003(quantity, is_member),
        returns_rule_004(quantity, is_member),
        returns_rule_005(quantity, is_member),
        returns_rule_006(quantity, is_member),
        returns_rule_007(quantity, is_member),
        returns_rule_008(quantity, is_member),
        returns_rule_009(quantity, is_member),
        returns_rule_010(quantity, is_member),
    ]
    return _round_money(sum(parts))



# --- CROSS-CUTTING VALIDATORS (extra branches for coverage) ---

def validate_cart_line(quantity: float, unit_price: float, sku: str) -> None:
    _reject_negative(quantity, "quantity")
    _reject_negative(unit_price, "unit_price")
    if not sku or not sku.strip():
        raise ValueError("sku required")
    if quantity > MAX_LINE_QTY:
        raise ValueError("quantity exceeds maximum")


def validate_member_flag(is_member: bool) -> bool:
    if is_member is not True and is_member is not False:
        raise TypeError("is_member must be bool")
    return is_member


def combine_domain_bundles(quantity: float, is_member: bool) -> float:
    """Calls every domain bundle — strong integration / coverage path."""
    _reject_negative(quantity, "quantity")
    total = 0.0
    total += compute_pricing_bundle(quantity, is_member)
    total += compute_inventory_bundle(quantity, is_member)
    total += compute_shipping_bundle(quantity, is_member)
    total += compute_payment_bundle(quantity, is_member)
    total += compute_loyalty_bundle(quantity, is_member)
    total += compute_returns_bundle(quantity, is_member)
    return _round_money(total)


def estimate_order_total(quantity: float, is_member: bool, premium: bool) -> float:
    if quantity == 0:
        return 0.0
    base = pricing_rule_001(quantity, is_member, premium)
    base += inventory_rule_002(quantity, is_member, premium)
    base += shipping_rule_003(quantity, is_member, premium)
    if is_member and base > 500:
        base -= 20.0
    return _round_money(max(base, 0.0))
