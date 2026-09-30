from types import SimpleNamespace

from anne.core.cognitive_orchestrator import OrchestrationResult
from anne.core.decision_loop import DecisionLoop
from anne.core.fail_fast import FailFastResult
from anne.language.bitigci import BitigciProvider
from anne.language.corroboration import TurkishLanguageCorroborationService
from anne.language.tdk import TdkProvider
from anne.learning.critic_loop import LoopDecision
from anne.learning.research_cognitive_loop import ResearchCognitiveLoop


class _FakeOrchestrator:
    def __init__(self) -> None:
        self.result = OrchestrationResult(
            status="EXECUTED",
            fail_fast=FailFastResult(True, "ok"),
            state=SimpleNamespace(
                output={
                    "verdict": "ONAYLA",
                    "action": "PROCEED",
                    "reason": "test decision",
                },
                action="PROCEED",
                context_map={
                    "verification_status": "VERIFIED",
                    "verification_sources": ("source-a", "source-b"),
                    "requires_evidence": True,
                    "intent": "answer",
                },
                ethic_score=None,
            ),
            selection=None,
            stage_trace=("FAIL_FAST", "DUY", "SELECT", "ANLA", "YAP"),
            reason="test decision",
            retry_count=0,
            lineage=("or_language_runtime",),
            stop_reason="validated",
        )

    def run(self, *args, **kwargs) -> OrchestrationResult:
        return self.result


class _ProceedCritic:
    def decide(self, *args, **kwargs) -> LoopDecision:
        return LoopDecision(
            action="PROCEED",
            reason="test bounded loop permits continuation",
            research_allowed=True,
        )


def _language_loop(*, divergent: bool) -> DecisionLoop:
    meaning_a = "bağlama göre kullanılan anlam"
    meaning_b = "aynı sözcüğün farklı bağlamdaki anlamı" if divergent else meaning_a

    corroboration = TurkishLanguageCorroborationService(
        providers=(
            BitigciProvider(
                resolver=lambda query: {
                    "meaning": meaning_a,
                    "source_ref": "bitigci:runtime-test",
                }
            ),
            TdkProvider(
                resolver=lambda query: {
                    "meaning": meaning_b,
                    "source_ref": "tdk:runtime-test",
                }
            ),
        )
    )

    loop = DecisionLoop.__new__(DecisionLoop)
    loop.memory = None
    loop.orchestrator = _FakeOrchestrator()
    loop.research_loop = ResearchCognitiveLoop(
        critic_loop=_ProceedCritic(),
        memory=None,
        language_corroboration_service=corroboration,
    )
    loop._experience_history = ()
    loop._experience_history_limit = 64
    return loop


def test_runtime_language_corroboration_reaches_metacognition() -> None:
    loop = _language_loop(divergent=False)

    result = loop.run("Bunu yap")

    assert result.status == "EXECUTED"
    assert result.action == "PROCEED"
    assert result.research_state is not None
    assert result.research_state.language_corroboration is not None
    assert result.research_state.language_corroboration.verification is not None
    assert (
        result.research_state.language_corroboration.verification.status.value
        == "corroborated"
    )
    assert result.research_state.adaptive_learning is not None
    assessment = result.research_state.adaptive_learning.metacognition
    assert "language_corroboration_observation" in assessment.decision_dependencies
    assert assessment.requires_review is False
    assert result.trace is not None
    assert result.trace.language_corroboration["status"] == "corroborated"
    assert result.trace.language_corroboration["authoritative"] is False
    assert result.trace.verification["verification_status"] == "VERIFIED"


def test_runtime_language_divergence_routes_to_bounded_review() -> None:
    loop = _language_loop(divergent=True)

    result = loop.run("Bunu yap")

    assert result.status == "BOUNDED"
    assert result.verdict == "REVIEW"
    assert result.action == "REVIEW"
    assert result.research_state is not None
    assert result.research_state.decision.action == "REVIEW"
    assert result.research_state.decision.research_allowed is False
    assert result.research_state.adaptive_learning is not None
    assessment = result.research_state.adaptive_learning.metacognition
    assert assessment.evaluation_status == "PROCESS_REVIEW_REQUIRED"
    assert assessment.research_required is False
    assert "language_source_divergence" in assessment.recalibration_triggers
    assert result.trace is not None
    assert result.trace.language_corroboration["status"] == "divergent"
    assert result.trace.language_corroboration["authoritative"] is False
    assert result.trace.verification["verification_status"] == "VERIFIED"
    assert result.output["original_output"]["action"] == "PROCEED"
