from dataclasses import replace

from anne.core.verification import FactualStatus
from anne.learning.derived_hypothesis import DerivedHypothesis
from anne.learning.derived_research_executor import DerivedResearchResult
from anne.learning.derived_research_planner import DerivedResearchPlanner
from anne.learning.evidence import EvidenceItem
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop, ResearchCognitiveState


class _StubExecutor:
    def __init__(self, evidence: tuple[EvidenceItem, ...]) -> None:
        self.evidence = evidence

    def execute(self, _plan) -> DerivedResearchResult:
        return DerivedResearchResult(
            plan_question="derived research",
            evidence=self.evidence,
            queries_used=1,
            sources_used=len(self.evidence),
            stopped_reason="plan_exhausted",
        )


def _state_with_derived_hypothesis() -> tuple[ResearchCognitiveLoop, ResearchCognitiveState, str]:
    loop = ResearchCognitiveLoop()
    state = loop.initialize("Question")
    claim = "A derived claim"
    hypothesis = DerivedHypothesis(
        id="DH1",
        claim=claim,
        source_inference_claim=claim,
        status="PROPOSED",
        research_question="Independently test A derived claim",
    )
    plan = DerivedResearchPlanner().create_plan((hypothesis,))
    assert plan is not None
    return loop, replace(
        state,
        derived_hypotheses=(hypothesis,),
        derived_research_plan=plan,
    ), claim


def _evidence(\n    claim: str, provenance: str, support: str, passage: str | None = None\n) -> EvidenceItem:\n    return EvidenceItem(
        source=provenance,
        claim=claim,
        kind="web",
        provenance=provenance,
        confidence=0.9,
        passage=passage or claim,
        support=support,
    )


def test_research_execution_verifies_fresh_independent_evidence() -> None:
    loop, state, claim = _state_with_derived_hypothesis()
    evidence = (
        _evidence(claim, "https://primary.example/source", "supports"),
        _evidence(claim, "https://independent.example/source", "supports"),
    )

    refreshed = loop.reassess_after_derived_research(
        state,
        executor=_StubExecutor(evidence),
    )

    assert refreshed.derived_research_result is not None
    assert refreshed.derived_research_result.sources_used == 2
    assert refreshed.derived_verifications
    verification = refreshed.derived_verifications[0]
    assert verification.status == FactualStatus.VERIFIED
    assert set(verification.sources) == {
        "https://primary.example/source",
        "https://independent.example/source",
    }


def test_research_execution_preserves_conflict_as_unverified_decision_state() -> None:
    loop, state, claim = _state_with_derived_hypothesis()
    evidence = (
        _evidence(claim, "https://primary.example/source", "supports"),
        _evidence(\n            claim,\n            "https://independent.example/source",\n            "contradicts",\n            passage=f"{claim} is not true",\n        ),
    )

    refreshed = loop.reassess_after_derived_research(
        state,
        executor=_StubExecutor(evidence),
    )

    assert refreshed.derived_verifications[0].status == FactualStatus.CONFLICTING
    assert refreshed.decision.action == "RESEARCH"
    assert refreshed.decision.research_allowed is True
