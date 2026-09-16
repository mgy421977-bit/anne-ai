from anne.core.character_integrity import (
    CharacterBaseline,
    CharacterIntegrityGate,
    FactualStatus,
)


def test_verified_learning_preserves_character():
    gate = CharacterIntegrityGate(CharacterBaseline(goodness=0.7, equality=0.7))
    result = gate.assess(
        probability=0.9,
        goodness=0.8,
        equality=0.9,
        evidence_verified=True,
        evidence_available=True,
    )
    assert result.factual_status is FactualStatus.VERIFIED
    assert result.learning_allowed is True
    assert result.quarantined is False


def test_best_available_is_not_promoted_to_fact():
    gate = CharacterIntegrityGate(CharacterBaseline(goodness=0.7, equality=0.7))
    result = gate.assess(
        probability=0.8,
        goodness=0.8,
        equality=0.8,
        evidence_available=True,
    )
    assert result.factual_status is FactualStatus.BEST_AVAILABLE
    assert result.learning_allowed is True


def test_character_regression_is_quarantined():
    gate = CharacterIntegrityGate(CharacterBaseline(goodness=0.8, equality=0.8))
    result = gate.assess(
        probability=0.9,
        goodness=0.79,
        equality=0.9,
        evidence_verified=True,
        evidence_available=True,
    )
    assert result.quarantined is True
    assert result.learning_allowed is False


def test_contradictory_evidence_cannot_be_verified():
    gate = CharacterIntegrityGate(CharacterBaseline(goodness=0.7, equality=0.7))
    result = gate.assess(
        probability=0.9,
        goodness=0.8,
        equality=0.8,
        evidence_verified=True,
        evidence_available=True,
        contradiction=True,
    )
    assert result.factual_status is FactualStatus.INSUFFICIENT
