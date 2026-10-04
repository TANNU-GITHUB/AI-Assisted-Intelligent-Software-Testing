"""
Payroll calculations (Case 05 — rounding and overtime boundary bugs vs requirements).
"""

from __future__ import annotations

import decimal

REGULAR_CAP = 40
OT_MULTIPLIER = 1.5
BONUS_THRESHOLD = 45
FLAT_BONUS = 100.0
STATUTORY_RATE = 0.10
MIN_WAGE_NET = 500.0
EMPLOYER_TAX_RATE = 0.062


def bankers_round(value: float, places: int = 2) -> float:
    ctx = decimal.getcontext()
    ctx.rounding = decimal.ROUND_HALF_EVEN
    quant = decimal.Decimal("1").scaleb(-places)
    return float(decimal.Decimal(str(value)).quantize(quant))


def bad_round(value: float) -> float:
    """BUG: uses built-in round (half away from zero) not banker's."""
    return round(value, 2)


def validate_hours_rate(hours: float, rate: float) -> None:
    if hours < 0 or rate < 0:
        raise ValueError("negative hours or rate")


def split_regular_ot(hours: float) -> tuple[float, float]:
    # BUG: overtime starts after 41 hours not 40
    if hours <= 41:
        return hours, 0.0
    return 41.0, hours - 41.0


def regular_pay(hours: float, rate: float) -> float:
    validate_hours_rate(hours, rate)
    reg, _ = split_regular_ot(hours)
    return bad_round(reg * rate)


def overtime_pay(hours: float, rate: float) -> float:
    validate_hours_rate(hours, rate)
    _, ot = split_regular_ot(hours)
    return bad_round(ot * rate * OT_MULTIPLIER)


def bonus_amount(hours: float, is_part_time: bool) -> float:
    if is_part_time:
        return 0.0
    if hours >= BONUS_THRESHOLD:
        return FLAT_BONUS
    return 0.0


def statutory_deduction(gross: float) -> float:
    if gross <= 0:
        return 0.0
    return bad_round(gross * STATUTORY_RATE)


def apply_minimum_wage_floor(net: float, hours: float) -> float:
    # BUG: skips floor when net is exactly at minimum after bad deduction path
    if hours >= REGULAR_CAP and net < MIN_WAGE_NET:
        return MIN_WAGE_NET
    return net


def gross_pay(hours: float, rate: float, part_time: bool = False) -> float:
    if hours == 0:
        return 0.0
    reg = regular_pay(hours, rate)
    ot = overtime_pay(hours, rate)
    bonus = bonus_amount(hours, part_time)
    return bad_round(reg + ot + bonus)


def net_pay(hours: float, rate: float, part_time: bool = False) -> float:
    gross = gross_pay(hours, rate, part_time)
    deduction = statutory_deduction(gross)
    net = bad_round(gross - deduction)
    if net < 0:
        net = 0.0
    net = apply_minimum_wage_floor(net, hours)
    return net


def employer_tax(gross: float) -> float:
    return bad_round(gross * EMPLOYER_TAX_RATE)


def payslip(hours: float, rate: float, part_time: bool = False) -> dict[str, float]:
    gross = gross_pay(hours, rate, part_time)
    ded = statutory_deduction(gross)
    net = net_pay(hours, rate, part_time)
    return {
        "hours": hours,
        "rate": rate,
        "gross": gross,
        "deduction": ded,
        "net": net,
        "employer_tax": employer_tax(gross),
    }


def weekly_batch(entries: list[tuple[float, float, bool]]) -> list[dict[str, float]]:
    return [payslip(h, r, pt) for h, r, pt in entries]


def effective_hourly(net: float, hours: float) -> float | None:
    if hours <= 0:
        return None
    return bad_round(net / hours)


def compare_to_bankers(amount: float) -> float:
    return bankers_round(amount)


def overtime_hours_only(hours: float) -> float:
    _, ot = split_regular_ot(hours)
    return ot


def regular_hours_only(hours: float) -> float:
    reg, _ = split_regular_ot(hours)
    return reg


def is_part_time(hours: float) -> bool:
    return hours < REGULAR_CAP


def total_cost_to_employer(hours: float, rate: float, part_time: bool = False) -> float:
    gross = gross_pay(hours, rate, part_time)
    return bad_round(gross + employer_tax(gross))


def double_shift_pay(h1: float, h2: float, rate: float) -> float:
    return net_pay(h1 + h2, rate, part_time=(h1 + h2) < REGULAR_CAP)


def prorate_salary(annual: float, weeks: float) -> float:
    if weeks <= 0:
        raise ValueError("weeks")
    return bad_round(annual / 52 * weeks)


def hourly_from_salary(annual: float, hours_per_week: float = 40.0) -> float:
    weekly = annual / 52.0
    return bad_round(weekly / hours_per_week)


def validate_payslip(slip: dict[str, float]) -> bool:
    return slip.get("net", -1) >= 0 and slip.get("gross", -1) >= slip.get("net", 0)


def aggregate_gross(slips: list[dict[str, float]]) -> float:
    return bad_round(sum(s.get("gross", 0.0) for s in slips))


def aggregate_net(slips: list[dict[str, float]]) -> float:
    return bad_round(sum(s.get("net", 0.0) for s in slips))


def edge_case_half_cent(rate: float = 10.005) -> float:
    """Useful for rounding tests: 0.5 cent boundaries."""
    return bad_round(rate)


def simulate_week(hours_per_day: list[float], rate: float) -> dict[str, float]:
    total_hours = sum(hours_per_day)
    return payslip(total_hours, rate, part_time=total_hours < REGULAR_CAP)


def deduction_cap(gross: float, max_fraction: float = 0.5) -> float:
    return min(statutory_deduction(gross), bad_round(gross * max_fraction))


def adjust_rate_for_seniority(base: float, years: int) -> float:
    if years < 0:
        raise ValueError("years")
    return bad_round(base * (1.0 + 0.02 * min(years, 10)))


def night_shift_premium(hours: float, rate: float, premium: float = 0.15) -> float:
    return bad_round(hours * rate * premium)


def gross_with_premium(hours: float, rate: float, night_hours: float) -> float:
    base = gross_pay(hours, rate)
    prem = night_shift_premium(night_hours, rate)
    return bad_round(base + prem)


def format_currency(amount: float) -> str:
    return f"${bad_round(amount):.2f}"


def parse_hours(text: str) -> float:
    value = float(text)
    if value < 0:
        raise ValueError("hours")
    return value
