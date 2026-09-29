from dataclasses import replace

from anne.core.verification import FactualStatus
from anne.learning.derived_hypothesis import DerivedHypothesis
from anne.learning.derived_research_executor import DerivedResearchExecutor
from anne.learning.derived_research_planner import DerivedResearchPlanner
from anne.learning.evidence import EvidenceItem
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


class FakeResearcher:
    def research(self, query: str) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                source="source-a",
                claim=query,
                kind="web",
                provenance="https://alpha.example/a",
                confidence=0.8,
                passage=query,
            ),
            EvidenceItem(
                source="source-b",
                claim=query,
                kind="web",
                provenance="https://beta.example/b",
                confidence=0.8,
                passage=f"Independent source confirms: {query}",
            ),
        ]


def test_derived_research_is_verified_before_reassessment() -> None:
    question = "A and B jointly support X"
    loop = ResearchCognitiveLoop()
    initial = loop.initialize(question)

    derived = DerivedHypothesis(
        id="DH1",
        claim=question,
        source_inference_claim=question,
        status="PROPOSED",
        research_question=question,
    )
    plan = DerivedResearchPlanner(max_hypotheses=1, max_queries=1).create_plan((derived,))
    assert plan is not None
    state = replace(initial, derived_hypotheses=(derived,), derived_research_plan=plan)

    refreshed = loop.reassess_after_derived_research(
        state,
        executor=DerivedResearchExecutor(researcher=FakeResearcher()),
    )

    assert len(refreshed.derived_verifications) == 1
    verification = refreshed.derived_verifications[0]
    assert verification.status == FactualStatus.VERIFIED
    assert len(verification.sources) == 2

    # Verification supplies a support signal to the normal critic/synthesis
    # path, but the Evidence Ledger remains epistemically explicit.
    assert refreshed.synthesis.status.value == "SUPPORTED"
    entries = refreshed.evidence_ledger.as_dict()["entries"]
    assert len(entries) == 2
    assert all(entry["status"] == "unverified" for entry in entries)
