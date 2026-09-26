"""AnneMythosBridge – full system integration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from anne.core.cognitive_state import Consciousness
from anne.core.decision_loop import DecisionLoop
from anne.core.pipeline import AnnePipeline
from anne.dream.cycle import DreamCycle
from anne.memory.fractal_memory import FractalMemory
from anne.mythos.engine import MythosEngine


class AnneMythosBridge:
    """Orchestrates Mythos curiosity + ANNE six-stage pipeline + Dream cycle."""

    def __init__(self, db_path: str = "anne.db") -> None:
        self.memory = FractalMemory(db_path)
        self.mythos = MythosEngine()
        self.pipeline = AnnePipeline(self.memory)
        self.loop = DecisionLoop(memory=self.memory, pipeline=self.pipeline)
        self.dream = DreamCycle(self.memory)
        self.cycle_count = 0

    def process(
        self,
        topic: str,
        consciousnesses: Sequence[Consciousness],
        group_a: Sequence[Consciousness] | None = None,
        group_b: Sequence[Consciousness] | None = None,
        max_iterations: int = 4,
    ) -> dict[str, Any]:
        """Full processing cycle: Mythos → six stages → memory → (optional) dream."""
        self.cycle_count += 1

        hypotheses = self.mythos.curiosity_loop(
            topic,
            max_iterations,
            prior=0.4 + self.cycle_count * 0.02,
        )

        results: list[dict[str, Any]] = []
        for h in hypotheses:
            result = self.loop.run(
                topic,
                parties=consciousnesses,
                hypothesis=h,
                group_a=group_a,
                group_b=group_b,
            )
            state = result.state
            if state is None:
                results.append(
                    {
                        "hypothesis": asdict(h),
                        "ethic": None,
                        "output": result.output,
                    }
                )
                continue

            score = state.ethic_score
            results.append(
                {
                    "hypothesis": asdict(h),
                    "ethic": asdict(score) if score else None,
                    "output": result.output,
                }
            )

            if score is None or result.status != "EXECUTED":
                continue

            self.memory.save_dream_pattern(
                f"{state.input_type}:{score.verdict}",
                score.total,
                score.verdict,
            )
            if score.verdict == "REDDET":
                self.memory.save_failure_trace(
                    cycle_id=str(self.cycle_count),
                    stage="ANLA",
                    raw_input=topic,
                    reason=score.reasoning,
                    meta_tag=f"verdict={score.verdict}",
                    hypothesis_id=h.id,
                    ethic_total=score.total,
                )

        dream_report: dict[str, Any] | None = None
        if self.cycle_count % 3 == 0:
            dream_report = self.dream.run()

        return {
            "cycle": self.cycle_count,
            "topic": topic,
            "results": results,
            "dream_report": dream_report,
        }
