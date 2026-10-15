from __future__ import annotations

from dataclasses import replace

import pytest

from anne.core.cognitive_state import (
    CognitiveState,
    Consciousness,
    EthicScore,
    HissetAssessment,
    HissetStatus,
    Hypothesis,
)
from anne.core.pipeline import AnnePipeline
from anne.memory.fractal_memory import FractalMemory


class RelationMemory:
    def __init__(self, relations: dict[tuple[str, str], float] | None = None) -> None:
        self.relations = relations or {}

    def get_empathy_strength(self, id_a: str, id_b: str) -> float:
        return self.relations.get((id_a, id_b), 0.5)

    def update_empathy(self, *args: object, **kwargs: object) -> None:
        return None


class FailingRelationMemory(RelationMemory):
    def get_empathy_strength(self, id_a: str, id_b: str) -> float:
        raise RuntimeError("relation lookup failed")

    def has_empathy_relation(self, id_a: str, id_b: str) -> bool:
        raise RuntimeError("relation presence lookup failed")


def make_state(*parties: Consciousness) -> CognitiveState:
    return CognitiveState(
        raw_input="bounded test",
        affected_consciousnesses=list(parties),
        logic_valid=True,
        context_map={
            "evidence_gate": "passed",
            "action_reversible": True,
            "action_risk": 0.1,
        },
        ethic_score=EthicScore(
            goodness=0.8,
            equality=1.0,
            harm=0.1,
            total=0.75,
            verdict="ONAYLA",
            reasoning="bounded test",
        ),
    )


def test_hisset_assessment_is_immutable_and_explicit() -> None:
    assessment = HissetAssessment(
        status=HissetStatus.INSUFFICIENT,
        uncertainty=1.0,
        reasons=("unknown relationship",),
        provenance=("memory:empathy_map",),
        party_impacts=(("a", 0.375),),
    )

    with pytest.raises(AttributeError):
        assessment.uncertainty = 0.0  # type: ignore[misc]


def test_single_party_is_explicitly_insufficient() -> None:
    pipeline = AnnePipeline(memory=RelationMemory())
    state = pipeline.hisset(make_state(Consciousness(id="a")))

    assert state.empathy_map["a"]["estimated_impact"] == 0.375
    assert state.hisset_assessment is not None
    assert state.hisset_assessment.status is HissetStatus.INSUFFICIENT
    assert state.hisset_assessment.uncertainty == 1.0
    assert "no relation counterpart" in state.hisset_assessment.reasons[0]
    assert state.hisset_assessment.provenance == ("core:ethic_core",)


def test_two_party_assessment_preserves_empathy_map_and_marks_unknown_presence() -> None:
    pipeline = AnnePipeline(memory=RelationMemory({("a", "b"): 0.8, ("b", "a"): 0.8}))
    state = pipeline.hisset(
        make_state(Consciousness(id="a"), Consciousness(id="b"))
    )

    assert state.empathy_map == {
        "a": {
            "perspective_weight": 1.0,
            "avg_relation_strength": 0.8,
            "estimated_impact": 0.6,
        },
        "b": {
            "perspective_weight": 1.0,
            "avg_relation_strength": 0.8,
            "estimated_impact": 0.6,
        },
    }
    assert state.hisset_assessment is not None
    assert state.hisset_assessment.status is HissetStatus.INSUFFICIENT
    assert state.hisset_assessment.uncertainty == 1.0
    assert "unknown" in state.hisset_assessment.reasons[0].lower()
    assert state.hisset_assessment.provenance == ("core:ethic_core",)
    assert dict(state.context_map["hisset_assessment"]["party_impacts"]) == {
        "a": 0.6,
        "b": 0.6,
    }


def test_explicit_relation_presence_can_produce_available_assessment() -> None:
    class KnownRelationMemory(RelationMemory):
        def has_empathy_relation(self, id_a: str, id_b: str) -> bool:
            return (id_a, id_b) in self.relations

    pipeline = AnnePipeline(
        memory=KnownRelationMemory({("a", "b"): 0.8, ("b", "a"): 0.8})
    )
    state = pipeline.hisset(
        make_state(Consciousness(id="a"), Consciousness(id="b"))
    )

    assert state.hisset_assessment is not None
    assert state.hisset_assessment.status is HissetStatus.AVAILABLE
    assert state.hisset_assessment.uncertainty == 0.5
    assert state.hisset_assessment.provenance == (
        "memory:empathy_map:presence_query",
        "memory:empathy_map:strength",
        "core:ethic_core",
    )


def test_real_fractal_memory_distinguishes_present_and_absent_relations(tmp_path) -> None:
    memory = FractalMemory(str(tmp_path / "anne.db"))
    memory.update_empathy("a", "b", conflict=False, resolved=True)
    pipeline = AnnePipeline(memory=memory)

    present = pipeline.hisset(make_state(Consciousness(id="a"), Consciousness(id="b")))
    assert present.hisset_assessment is not None
    assert present.hisset_assessment.status is HissetStatus.AVAILABLE
    assert memory.has_empathy_relation("a", "b") is True
    assert memory.has_empathy_relation("a", "c") is False

    absent = pipeline.hisset(make_state(Consciousness(id="a"), Consciousness(id="c")))
    assert absent.hisset_assessment is not None
    assert absent.hisset_assessment.status is HissetStatus.INSUFFICIENT
    assert "no stored relation" in absent.hisset_assessment.reasons[0].lower()


def test_relation_lookup_failure_is_unknown_and_does_not_change_yap() -> None:
    pipeline = AnnePipeline(memory=FailingRelationMemory())
    state = make_state(Consciousness(id="a"), Consciousness(id="b"))
    before = (state.ethic_score, state.logic_valid, state.action)
    pipeline.hisset(state)

    assert state.hisset_assessment is not None
    assert state.hisset_assessment.status is HissetStatus.INSUFFICIENT
    assert "unknown" in state.hisset_assessment.reasons[0]
    assert state.hisset_assessment.provenance == ("core:ethic_core",)
    assert (state.ethic_score, state.logic_valid, state.action) == before


@pytest.mark.parametrize("party_id", [None, 1, "", "   "])
def test_invalid_party_id_is_explicitly_insufficient(party_id: object) -> None:
    pipeline = AnnePipeline(memory=RelationMemory())
    state = pipeline.hisset(make_state(Consciousness(id=party_id)))  # type: ignore[arg-type]

    assert state.hisset_assessment is not None
    assert state.hisset_assessment.status is HissetStatus.INSUFFICIENT
    assert state.hisset_assessment.uncertainty == 1.0
    assert state.hisset_assessment.provenance == ()


def test_duplicate_party_id_is_explicitly_insufficient() -> None:
    pipeline = AnnePipeline(memory=RelationMemory())
    state = pipeline.hisset(
        make_state(Consciousness(id="same"), Consciousness(id="same"))
    )

    assert state.hisset_assessment is not None
    assert state.hisset_assessment.status is HissetStatus.INSUFFICIENT
    assert "duplicate" in state.hisset_assessment.reasons[0].lower()


def test_context_trace_is_canonical_assessment_trace() -> None:
    pipeline = AnnePipeline(memory=RelationMemory())
    state = pipeline.hisset(make_state(Consciousness(id="a")))

    assert state.hisset_assessment is not None
    assert state.context_map["hisset_assessment"] == state.hisset_assessment.as_trace()


def test_hisset_does_not_change_existing_yap_result_or_decision_state() -> None:
    pipeline = AnnePipeline(memory=RelationMemory())
    hypothesis = Hypothesis("h", "test", "bounded claim", 0.9)
    state_without_hisset = make_state(Consciousness(id="a"))
    state_with_hisset = replace(
        make_state(Consciousness(id="a")),
        context_map=dict(state_without_hisset.context_map),
    )

    original_score = state_with_hisset.ethic_score
    original_logic = state_with_hisset.logic_valid
    pipeline.hisset(state_with_hisset)

    assert state_with_hisset.ethic_score is original_score
    assert state_with_hisset.logic_valid is original_logic
    assert state_with_hisset.action == ""

    without_result = pipeline.yap(state_without_hisset, hypothesis)
    with_result = pipeline.yap(state_with_hisset, hypothesis)

    assert with_result.action == without_result.action
    assert with_result.output["verdict"] == without_result.output["verdict"]
    assert with_result.output["action"] == without_result.output["action"]
    assert with_result.output["core"] == without_result.output["core"]
    assert with_result.output["agency_decision"] == without_result.output["agency_decision"]



@pytest.mark.parametrize(
    "invalid_strength",
    [float("nan"), float("inf"), -0.1, 1.1, "invalid", None, True, 10**1000],
)
def test_invalid_relation_strength_fails_closed_without_crashing(
    invalid_strength: object,
) -> None:
    class InvalidStrengthMemory(RelationMemory):
        def get_empathy_strength(self, id_a: str, id_b: str) -> float:
            return invalid_strength  # type: ignore[return-value]

        def has_empathy_relation(self, id_a: str, id_b: str) -> bool:
            return True

    pipeline = AnnePipeline(memory=InvalidStrengthMemory())
    state = make_state(Consciousness(id="a"), Consciousness(id="b"))
    original_score = state.ethic_score
    original_logic = state.logic_valid
    original_action = state.action

    pipeline.hisset(state)

    assert state.hisset_assessment is not None
    assert state.hisset_assessment.status is HissetStatus.INSUFFICIENT
    assert state.hisset_assessment.uncertainty == 1.0
    assert "unknown" in state.hisset_assessment.reasons[0].lower()
    assert all(
        value["avg_relation_strength"] == 0.5
        and value["estimated_impact"] == 0.375
        for value in state.empathy_map.values()
    )
    assert state.ethic_score is original_score
    assert state.logic_valid is original_logic
    assert state.action == original_action


@pytest.mark.parametrize(
    "invalid_total",
    [float("nan"), float("inf"), -0.1, 1.1, "invalid", None, True, 10**1000],
)
def test_invalid_ethical_total_fails_closed_without_crashing(
    invalid_total: object,
) -> None:
    class KnownRelationMemory(RelationMemory):
        def get_empathy_strength(self, id_a: str, id_b: str) -> float:
            return 0.8

        def has_empathy_relation(self, id_a: str, id_b: str) -> bool:
            return True

    pipeline = AnnePipeline(memory=KnownRelationMemory())
    state = make_state(Consciousness(id="a"), Consciousness(id="b"))
    assert state.ethic_score is not None
    state.ethic_score.total = invalid_total  # type: ignore[assignment]
    original_score = state.ethic_score
    original_logic = state.logic_valid
    original_action = state.action

    pipeline.hisset(state)

    assert state.hisset_assessment is not None
    assert state.hisset_assessment.status is HissetStatus.INSUFFICIENT
    assert state.hisset_assessment.uncertainty == 1.0
    assert "ethical score" in state.hisset_assessment.reasons[0].lower()
    assert state.hisset_assessment.provenance == (
        "memory:empathy_map:presence_query",
        "memory:empathy_map:strength",
    )
    assert all(
        value["avg_relation_strength"] == 0.8
        and value["estimated_impact"] == 0.4
        for value in state.empathy_map.values()
    )
    assert state.ethic_score is original_score
    assert state.logic_valid is original_logic
    assert state.action == original_action
