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


class RelationMemory:
    def __init__(self, relations: dict[tuple[str, str], float] | None = None) -> None:
        self.relations = relations or {}

    def get_empathy_strength(self, id_a: str, id_b: str) -> float:
        return self.relations.get((id_a, id_b), 0.5)

    def update_empathy(self, *args: object, **kwargs: object) -> None:
        return None


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
    assert state.hisset_assessment.provenance == (
        "memory:empathy_map",
        "anla:ethic_score",
    )


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
    assert "presence is unknown" in state.hisset_assessment.reasons[0]
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
