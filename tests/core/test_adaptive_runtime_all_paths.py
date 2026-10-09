from pathlib import Path

from anne.core.decision_loop import DecisionLoop
from anne.core.resource_profile import ResourceProfile


def test_prepare_runtime_profile_updates_orchestrator(tmp_path: Path) -> None:
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))
    profile = loop._prepare_runtime_profile("bounded resource planning")

    assert isinstance(profile, ResourceProfile)
    assert loop.resource_profile == profile
    assert loop.orchestrator.resource_profile == profile
    assert loop.orchestrator.candidate_batch_size == profile.max_mitos_candidates


def test_run_cognitive_prepares_adaptive_profile(tmp_path: Path, monkeypatch) -> None:
    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))
    calls: list[str] = []

    monkeypatch.setattr(
        loop,
        "_prepare_runtime_profile",
        lambda raw_input: calls.append(raw_input) or ResourceProfile.minimal(),
    )
    monkeypatch.setattr(loop.orchestrator, "run", lambda *args, **kwargs: "result")

    result = loop.run_cognitive("cognitive route")

    assert result == "result"
    assert calls == ["cognitive route"]


def test_run_fractal_prepares_adaptive_profile(tmp_path: Path, monkeypatch) -> None:
    import anne.core.decision_loop as decision_loop_module

    loop = DecisionLoop(memory_db_path=str(tmp_path / "anne.db"))
    calls: list[str] = []

    monkeypatch.setattr(
        loop,
        "_prepare_runtime_profile",
        lambda raw_input: calls.append(raw_input) or ResourceProfile.scaled(2),
    )

    class FakeFractalThinkingLoop:
        def __init__(self, *args, **kwargs):
            assert kwargs["resource_profile"] == ResourceProfile.scaled(2)

        def run(self, *args, **kwargs):
            return "fractal-result"

    monkeypatch.setattr(decision_loop_module, "FractalThinkingLoop", FakeFractalThinkingLoop)

    result = loop.run_fractal("fractal route")

    assert result == "fractal-result"
    assert calls == ["fractal route"]
