from decimal import Decimal

import pytest

from app.services.transactions.toll_payment import (
    balance_after_toll,
    has_sufficient_balance,
    recognition_is_charge_eligible,
)


def test_balance_after_toll_deducts_the_exact_simulated_amount() -> None:
    assert balance_after_toll(Decimal("20.00"), Decimal("2.00")) == Decimal("18.00")


def test_insufficient_balance_never_creates_an_overdraft() -> None:
    assert not has_sufficient_balance(Decimal("1.99"), Decimal("2.00"))
    with pytest.raises(ValueError, match="insufficient"):
        balance_after_toll(Decimal("1.99"), Decimal("2.00"))


@pytest.mark.parametrize(
    ("accepted", "plate", "expected"),
    [
        (True, "VAA1234", True),
        (False, "VAA1234", False),
        (True, "", False),
        (True, None, False),
    ],
)
def test_only_confidence_eligible_recognitions_can_be_charged(
    accepted: bool, plate: str | None, expected: bool
) -> None:
    assert recognition_is_charge_eligible(accepted, plate) is expected
