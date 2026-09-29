"""Bounded generation of testable hypotheses from joint inferences.

This layer transforms an explicit derived claim into a research target. It does
not add external facts, assign truth, or authorize action.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.learning.joint_inference import JointInference, JointInferenceStatus


@dataclass(frozen=True)
class DerivedHypothesis:
    id: str
    claim: str
    source_inference_claim: str
    status: str
    research_question: str

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "claim": self.claim,
            "source_inference_claim": self.source_inference_claim,
            "status": self.status,
            "research_question": self.research_question,
        }


class DerivedHypothesisGenerator:
    """Create at most bounded, inspectable follow-up hypotheses."""

    def generate(
        self,
        inferences: tuple[JointInference, ...],
        *,
        max_hypotheses: int = 2,
    ) -> tuple[DerivedHypothesis, ...]:
        if max_hypotheses < 1:
            raise ValueError("max_hypotheses must be >= 1")

        result: list[DerivedHypothesis] = []
        for inference in inferences:
            if inference.status != JointInferenceStatus.DERIVED:
                continue
            if not inference.claim.strip():
                continue

            index = len(result) + 1
            result.append(
                DerivedHypothesis(
                    id=f"DH{index}",
                    claim=inference.claim,
                    source_inference_claim=inference.claim,
                    status="PROPOSED",
                    research_question=(
                        "Independently test the joint inference: "
                        f"{inference.claim}"
                    ),
                )
            )
            if len(result) >= max_hypotheses:
                break

        return tuple(result)


__all__ = ["DerivedHypothesis", "DerivedHypothesisGenerator"]
