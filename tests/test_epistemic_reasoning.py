from anne.core.epistemic_reasoning import EpistemicAnalyzer
from anne.core.pipeline import AnnePipeline
from anne.core.cognitive_orchestrator import CognitiveOrchestrator
from anne.memory.fractal_memory import FractalMemory
from anne.mythos.engine import ExplorationMode, HypothesisCandidate


def candidate(identifier: str, claim: str) -> HypothesisCandidate:
    return HypothesisCandidate(
        id=identifier,
        goal="test",
        claim=claim,
        mode=ExplorationMode.HYPOTHESIS,
        probability=0.5,
        discovery_value=0.5,
        novelty=0.5,
        testability=0.5,
        harm_risk=0.0,
        reversibility=1.0,
        expected_benefit=0.5,
        test_cost=0.2,
        evidence_status="UNVERIFIED",
    )


def test_epistemic_analysis_preserves_internal_and_evidence_boundaries():
    result = EpistemicAnalyzer.analyze(
        "Işık hızı aşılamaz mı?",
        [
            candidate("h1", "A spacetime geometry mechanism may alter causal propagation."),
            candidate("h2", "A spacetime geometry mechanism may alter causal propagation through a different path."),
        ],
    )

    assert len(result.assessments) == 2
    assert all(item.internally_consistent for item in result.assessments)
    assert len(result.relations) == 1
    assert result.clusters
    assert result.common_solution_space
    assert result.novel_hypothesis_status == "SYNTHESIS_UNVERIFIED"
    assert "novel_hypothesis_synthesis" in result.verification_boundary


def test_epistemic_analysis_does_not_claim_truth_from_candidate_status():
    result = EpistemicAnalyzer.analyze(
        "claim",
        [candidate("h1", "A mechanism is possible.")],
    )

    assert result.assessments[0].evidence_status == "UNVERIFIED"
    assert result.novel_hypothesis is None
    assert result.novel_hypothesis_status == "NOT_DERIVED"


def test_pipeline_persists_epistemic_map(tmp_path):
    pipeline = AnnePipeline(FractalMemory(tmp_path / "anne.db"))

    state = pipeline.duy("Bir çözüm bul", [])
    candidates = [
        candidate("h1", "A shared mechanism may change propagation."),
        candidate("h2", "A shared mechanism may change propagation."),
    ]
    state = pipeline.request_consistency(state)
    state = pipeline.bak(state)
    state = pipeline.epistemic_analysis(state, candidates)

    assert state.context_map["epistemic_candidate_count"] == 2
    assert state.context_map["epistemic_consistent_count"] == 2
    assert state.context_map["epistemic_relation_count"] == 1
    assert state.context_map["novel_hypothesis_status"] == "SYNTHESIS_UNVERIFIED"
    assert state.epistemic_map["verification_boundary"]
