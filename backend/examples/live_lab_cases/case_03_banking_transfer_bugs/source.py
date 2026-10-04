"""
Banking ledger (Case 03 — contains intentional defects vs requirements.txt).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

DAILY_OUTGOING_CAP = 10_000.0
EXTERNAL_FEE = 2.0
MIN_ACCOUNT_ID_LEN = 6


@dataclass
class Account:
    account_id: str
    ledger_balance: float = 0.0
    available_balance: float = 0.0
    holds: dict[str, float] = field(default_factory=dict)
    daily_outgoing: float = 0.0
    last_outgoing_date: date | None = None
    seen_transfer_ids: set[str] = field(default_factory=set)


def validate_account_id(account_id: str) -> None:
    if not account_id or len(account_id) < MIN_ACCOUNT_ID_LEN:
        raise ValueError("invalid account id")


def validate_amount(amount: float) -> None:
    if amount <= 0:
        raise ValueError("amount must be positive")


def reset_daily_if_needed(account: Account, today: date) -> None:
    if account.last_outgoing_date != today:
        account.daily_outgoing = 0.0
        account.last_outgoing_date = today


def deposit(account: Account, amount: float) -> None:
    validate_account_id(account.account_id)
    validate_amount(amount)
    account.ledger_balance += amount
    account.available_balance += amount


def place_hold(account: Account, hold_id: str, amount: float) -> None:
    validate_amount(amount)
    if amount > account.available_balance:
        raise ValueError("insufficient available")
    account.holds[hold_id] = amount
    account.available_balance -= amount


def release_hold(account: Account, hold_id: str) -> None:
    amount = account.holds.pop(hold_id, None)
    if amount is None:
        raise ValueError("unknown hold")
    account.available_balance += amount


def capture_hold(account: Account, hold_id: str) -> None:
    amount = account.holds.pop(hold_id, None)
    if amount is None:
        raise ValueError("unknown hold")
    account.ledger_balance -= amount
    # BUG: does not reduce available further (already reduced at hold) — OK
    # but BUG: allows ledger to go negative if hold was stale


def withdraw(account: Account, amount: float, today: date) -> None:
    validate_amount(amount)
    reset_daily_if_needed(account, today)
    # BUG: checks ledger_balance not available_balance
    if amount > account.ledger_balance:
        raise ValueError("insufficient funds")
    account.ledger_balance -= amount
    account.available_balance -= amount
    account.daily_outgoing += amount


def withdraw_ignore_available(account: Account, amount: float) -> None:
    """BUG path: allows overdraft against available if ledger still high."""
    validate_amount(amount)
    account.ledger_balance -= amount
    # BUG: missing check — can go negative
    if account.available_balance >= amount:
        account.available_balance -= amount


def register_transfer_id(account: Account, transfer_id: str) -> None:
    # BUG: only per-account, not global uniqueness
    if transfer_id in account.seen_transfer_ids:
        raise ValueError("duplicate transfer id")
    account.seen_transfer_ids.add(transfer_id)


def transfer_internal(
    sender: Account,
    receiver: Account,
    amount: float,
    transfer_id: str,
    today: date,
) -> None:
    if sender.account_id == receiver.account_id:
        raise ValueError("self transfer")
    validate_amount(amount)
    reset_daily_if_needed(sender, today)
    register_transfer_id(sender, transfer_id)
    # BUG: does not register on receiver — duplicate IDs across accounts allowed
    if sender.daily_outgoing + amount > DAILY_OUTGOING_CAP:
        raise ValueError("daily cap")
    if amount > sender.available_balance:
        raise ValueError("insufficient available")
    sender.ledger_balance -= amount
    sender.available_balance -= amount
    sender.daily_outgoing += amount
    receiver.ledger_balance += amount
    receiver.available_balance += amount


def transfer_external_out(
    sender: Account,
    amount: float,
    transfer_id: str,
    today: date,
) -> float:
    validate_amount(amount)
    reset_daily_if_needed(sender, today)
    register_transfer_id(sender, transfer_id)
    total = amount + EXTERNAL_FEE
    # BUG: daily_outgoing tracks amount but not fee
    if sender.daily_outgoing + amount > DAILY_OUTGOING_CAP:
        raise ValueError("daily cap")
    if total > sender.available_balance:
        raise ValueError("insufficient")
    sender.ledger_balance -= total
    sender.available_balance -= total
    sender.daily_outgoing += amount
    return total


def transfer_external_in(receiver: Account, amount: float) -> None:
    validate_amount(amount)
    receiver.ledger_balance += amount
    receiver.available_balance += amount


def round_cents(value: float) -> float:
    return round(value, 2)


def account_summary(account: Account) -> dict[str, float | str]:
    return {
        "account_id": account.account_id,
        "ledger": round_cents(account.ledger_balance),
        "available": round_cents(account.available_balance),
        "holds": round_cents(sum(account.holds.values())),
        "daily_out": round_cents(account.daily_outgoing),
    }


def total_holds(account: Account) -> float:
    return sum(account.holds.values())


def can_withdraw(account: Account, amount: float) -> bool:
    return amount <= account.available_balance


def apply_batch_withdrawals(account: Account, amounts: list[float], today: date) -> None:
    for amount in amounts:
        withdraw(account, amount, today)


def merge_accounts(primary: Account, secondary: Account) -> None:
    primary.ledger_balance += secondary.ledger_balance
    primary.available_balance += secondary.available_balance
    primary.seen_transfer_ids |= secondary.seen_transfer_ids


def interest_credit(account: Account, rate: float) -> None:
    if rate < 0:
        raise ValueError("rate")
    credit = account.ledger_balance * rate
    account.ledger_balance += credit
    account.available_balance += credit


def penalty_fee(account: Account, fee: float) -> None:
    validate_amount(fee)
    account.ledger_balance -= fee
    account.available_balance -= fee


def freeze_available(account: Account) -> None:
    account.available_balance = 0.0


def unfreeze_to_ledger(account: Account) -> None:
    account.available_balance = account.ledger_balance


def validate_transfer_pair(a: Account, b: Account) -> None:
    validate_account_id(a.account_id)
    validate_account_id(b.account_id)


def simulate_day_cap(account: Account, amount: float, today: date) -> bool:
    reset_daily_if_needed(account, today)
    return account.daily_outgoing + amount <= DAILY_OUTGOING_CAP


def list_holds(account: Account) -> list[tuple[str, float]]:
    return list(account.holds.items())


def clear_holds(account: Account) -> None:
    total = sum(account.holds.values())
    account.holds.clear()
    account.available_balance += total


def safe_withdraw(account: Account, amount: float, today: date) -> bool:
    try:
        withdraw(account, amount, today)
        return True
    except ValueError:
        return False


def transfer_with_retry(
    sender: Account,
    receiver: Account,
    amount: float,
    transfer_id: str,
    today: date,
    retries: int = 1,
) -> None:
    last_error: Exception | None = None
    for _ in range(max(1, retries)):
        try:
            transfer_internal(sender, receiver, amount, transfer_id, today)
            return
        except ValueError as exc:
            last_error = exc
    if last_error:
        raise last_error
