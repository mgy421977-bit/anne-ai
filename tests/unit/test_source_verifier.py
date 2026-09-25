from datetime import date, timedelta

import pytest

from anne.core.source_verifier import SourceAwareVerifier, SourceRecord
from anne.core.verification import FactualStatus


def test_verified_when_scope_date_and_authority_pass():
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                source="https://example.com/registry",
                claim="panel price is 100",
                scope="TR",
                published_date=date.today(),
                authority_level="official",
            ),
        ),
        required_scope="TR",
        max_age_days=30,
        allowed_authorities=("official",),
    )
    result = verifier.verify("panel price is 100")
    assert result.status == FactualStatus.VERIFIED


def test_stale_source_stays_unverified():
    verifier = SourceAwareVerifier(
        (
            SourceRecord(
                source="https://example.com/old",
                claim="panel price is 100",
                scope="TR",
                published_date=date.today() - timedelta(days=31),
                authority_level="official",
            ),
        ),
        required_scope="TR",
        max_age_days=30,
        allowed_authorities=("official",),
    )
    result = verifier.verify("panel price is 100")
    assert result.status == FactualStatus.UNVERIFIED


def test_conflicting_accepted_sources_are_not_verified():
    records = (
        SourceRecord("https://example.com/a", "price is 100", "TR", date.today(), True, "official"),
        SourceRecord("https://example.com/b", "price is 100", "TR", date.today(), False, "official"),
    )
    result = SourceAwareVerifier(records, required_scope="TR").verify("price is 100")
    assert result.status == FactualStatus.CONFLICTING


def test_no_match_abstains():
    verifier = SourceAwareVerifier(
        (SourceRecord("https://example.com/a", "different claim"),)
    )
    assert verifier.verify("unknown claim").status == FactualStatus.UNVERIFIED


def test_invalid_source_rejected():
    with pytest.raises(ValueError):
        SourceRecord("not-a-url", "claim")
