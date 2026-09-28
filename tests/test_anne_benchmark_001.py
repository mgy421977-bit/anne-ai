from anne.learning.evidence import EvidenceItem
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop
from anne.learning.web_reevaluation import BoundedWebReEvaluator


class ScenarioResearcher:
    def __init__(self, fresh_items):
        self.fresh_items = tuple(fresh_items)
        self.calls = []

    def research(self, query):
        self.calls.append(query)
        return self.fresh_items


def test_benchmark_001_evidence_change_rebuilds_decision_trace():
    question = "Original claim"
    initial = EvidenceItem(
        source="source-a",
        claim=question,
        kind="web",
        provenance="https://a.example/source",
        confidence=0.9,
        passage=question,
        support="supports",
    )
    fresh = EvidenceItem(
        source="source-b",
        claim=question,
        kind="web",
        provenance="https://b.example/source",
        confidence=0.9,
        passage=question,
        support="contradicts",
    )

    state = ResearchCognitiveLoop().initialize(
        question,
        evidence=(initial,),
        queries_used=1,
        sources_used=1,
    )
    evidence_id = next(
        node["id"]
        for node in state.evidence_ledger.provenance()["nodes"]
        if node["kind"] == "evidence"
    )

    assert state.synthesis.status.value == "SUPPORTED"
    assert state.decision.action == "PROCEED"

    result = BoundedWebReEvaluator(
        ScenarioResearcher((fresh,))
    ).reevaluate(
        question=question,
        ledger=state.evidence_ledger,
        evidence_id=evidence_id,
    )

    assert result.plan.action == "RESEARCH"
    assert result.plan.invalidated_node == evidence_id
    assert state.evidence_ledger.status(evidence_id).value == "invalidated"
    assert result.refreshed_state is not None
    assert result.refreshed_state.synthesis.status.value == "REJECTED_WITH_ALTERNATIVES"
    assert result.refreshed_state.decision.action == "RESEARCH"
