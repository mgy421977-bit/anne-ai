from types import SimpleNamespace

from anne.core.cognitive_orchestrator import OrchestrationResult
from anne.core.decision_loop import DecisionLoop
from anne.core.fail_fast import FailFastResult
from anne.language.bitigci import BitigciProvider
from anne.language.service import TurkishLanguageEvidenceService
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
                    "reason": "test",
                },
                action="PROCEED",
                context_map={
                    "verification_status": "VERIFIED",
                    "verification_sources": ("source-a", "source-b"),
                    "requires_evidence": False,
                    "intent": "answer",
                },
                ethic_score=None,
            ),
            selection=None,
            stage_trace=("FAIL_FAST", "DUY", "SELECT", "ANLA", "YAP"),
            reason="test",
            retry_count=0,
            lineage=("runtime-language-test",),
            stop_reason="validated",
        )

    def run(self, *args, **kwargs):
        return self.result


class _ProceedCritic:
    def decide(self, *args, **kwargs) -> LoopDecision:
        return LoopDecision("PROCEED", "test", True)


def _loop() -> DecisionLoop:
    def resolver(query: str):
        return {
            "meaning": "belirsiz eylem ifadesi",
            "source_ref": "bitigci:test/bunu-yap",
            "examples": ("Bunu yapabilir misin?",),
        }

    loop = DecisionLoop.__new__(DecisionLoop)
    loop.memory = None
    loop.orchestrator = _FakeOrchestrator()
    loop.research_loop = ResearchCognitiveLoop(
        critic_loop=_ProceedCritic(),
        language_service=TurkishLanguageEvidenceService(
            provider=BitigciProvider(resolver=resolver)
        ),
    )
    loop._experience_history = ()
    loop._experience_history_limit = 64
    return loop


def test_runtime_trace_contains_non_authoritative_language_observation():
    result = _loop().run("Bunu yap")

    assert result.trace is not None
    assert result.trace.language["should_lookup"] is True
    assert result.trace.language["provider"] == "bitigci"
    assert result.trace.language["available"] is True
    assert result.trace.language["evidence"][0]["support"] == "unclear"
    assert result.trace.language["evidence"][0]["provenance"] == "bitigci:test/bunu-yap"
