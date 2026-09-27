from anne.learning.evidence import EvidenceItem, SupportStatus
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


def _evidence(claim: str, support: str) -> EvidenceItem:
    return EvidenceItem(
        claim=claim,
        source="source",
        provenance="https://example.test/source",
        confidence=0.9,
        passage=claim,
        support=support,
    )


def test_fresh_evidence_reassesses_hypotheses() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.reassess_with_fresh_evidence(
        "Question",
        (
            _evidence("Question", SupportStatus.SUPPORTS.value),
            _evidence(
                "An alternative explanation exists for: Question",
                SupportStatus.SUPPORTS.value,
            ),
        ),
    )

    statuses = {item.hypothesis_id: item.status for item in state.critic.assessments}
    assert statuses["H1"].value == "SUPPORTED"
    assert statuses["H2"].value == "SUPPORTED"
    assert statuses["H3"].value == "UNRESOLVED"


def test_fresh_contradicting_evidence_can_weaken_primary_hypothesis() -> None:
    loop = ResearchCognitiveLoop()
    state = loop.reassess_with_fresh_evidence(
        "Question",
        (
            _evidence("Question", SupportStatus.CONTRADICTS.value),
        ),
    )

    statuses = {item.hypothesis_id: item.status for item in state.critic.assessments}
    assert statuses["H1"].value == "REJECTED"
    assert statuses["H2"].value == "UNRESOLVED"
