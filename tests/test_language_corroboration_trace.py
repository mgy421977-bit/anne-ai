from types import SimpleNamespace

from anne.core.cognitive_orchestrator import OrchestrationResult
from anne.core.decision_loop import DecisionLoop
from anne.core.fail_fast import FailFastResult
from anne.language.bitigci import BitigciProvider
from anne.language.corroboration import TurkishLanguageCorroborationService
from anne.language.research_cognitive_loop import ResearchCognitiveLoop
from anne.language.tdk import TdkProvider
from anne.learning.critic_loop import LoopDecision


class _FakeOrchestrator:
    def __init__(self) -> None:
        self.result = OrchestrationResult(
            status="EXECUTED",
            fail_fast=FailFastResult(True, "ok"),
            state=SimpleNamespace(
                output={"verdict": "ONAYLA", "action": "PROCEED", "reason": "test"},
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
            lineage=("runtime-language-corroboration-test",),
            stop_reason="validated",
        )

    def run(self, *args, **kwargs):
        return self.result


class _ProceedCritic:
    def decide(self, *args, **kwargs) -> LoopDecision:
        return LoopDecision("PROCEED", "test", True)


def _loop() -> DecisionLoop:
    loop = DecisionLoop.__new__(DecisionLoop)
    loop.memory = None
    loop.orchestrator = _FakeOrchestrator()
    loop.research_loop = ResearchCognitiveLoop(
        critic_loop=_ProceedCritic(),
        language_corroboration_service=TurkishLanguageCorroborationService(
            providers=(
                BitigciProvider(
                    lambda _: {
                        "meaning": "belirsiz eylem ifadesi",
                        "source_ref": "https://bitigci.shakalin.net/madde/bunu-yap",
                    }
                ),
                TdkProvider(
                    lambda _: {
                        "meaning": "belirsiz eylem ifadesi",
                        "source_ref": "https://sozluk.gov.tr/madde/bunu-yap",
                    }
                ),
            )
        ),
    )
    loop._experience_history = ()
    loop._experience_history_limit = 64
    return loop


def test_runtime_trace_keeps_language_corroboration_scoped_and_non_authoritative():
    result = _loop().run("Bunu yap")

    assert result.trace is not None
    payload = result.trace.language_corroboration
    assert payload["should_lookup"] is True
    assert payload["providers"] == ["bitigci", "tdk"]
    assert payload["status"] == "corroborated"
    assert payload["authoritative"] is False
    assert result.trace.verification["verification_status"] == "VERIFIED"
