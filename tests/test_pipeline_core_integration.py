from anne.core.cognitive_state import CognitiveState, Consciousness, EthicScore, Hypothesis
from anne.core.pipeline import AnnePipeline


class FakeMemory:
    def update_empathy(self, *args, **kwargs):
        return None


def _state(goodness: float, equality: float) -> CognitiveState:
    state = CognitiveState(
        raw_input="test",
        affected_consciousnesses=[Consciousness(id="a"), Consciousness(id="b")],
        logic_valid=True,
        action="",
        context_map={
            "evidence_gate": "passed",
            "action_reversible": True,
            "action_risk": 0.1,
        },
        ethic_score=EthicScore(
            goodness=goodness,
            equality=equality,
            harm=0.0,
            total=max(goodness, 0.1),
            verdict="ONAYLA",
            reasoning="test",
        ),
    )
    return state


def test_pipeline_halts_when_core_blocks():
    pipeline = AnnePipeline(memory=FakeMemory())
    state = _state(goodness=0.0, equality=1.0)
    state.context_map.update(
        {
            "core_decision": "BLOCK",
            "core_goodness": 0.0,
            "core_equality": 1.0,
            "core_reason": "bad path",
        }
    )

    result = pipeline.yap(state, Hypothesis("h", "test", "test", 0.9))

    assert result.output["verdict"] == "REDDET"
    assert result.output["action"] == "HALT"


def test_pipeline_can_choose_separate_solutions():
    pipeline = AnnePipeline(memory=FakeMemory())
    state = _state(goodness=0.9, equality=1.0)

    result = pipeline.yap(
        state,
        Hypothesis("h", "test", "test", 0.9),
        group_a=[Consciousness(id="a")],
        group_b=[Consciousness(id="b")],
        common_solution=False,
    )

    assert result.output["action"] == "SEPARATE_SOLUTIONS"
    assert result.output["verdict"] == "AYRI_ÇÖZÜM"
    assert result.output["core"]["decision"] == "SEPARATE"
