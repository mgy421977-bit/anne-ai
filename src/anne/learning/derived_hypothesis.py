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
    """Create a bounded set of testable follow-up hypotheses."""

    def generate(self, inferences: tuple[JointInference, ...], *, max_hypotheses: int = 2) -> tuple[DerivedHypothesis, ...]:
        if max_hypotheses < 1:
            raise ValueError("max_hypotheses must be >= 1")
        result: list[DerivedHypothesis] = []
        for inference in inferences:
            if inference.status != JointInferenceStatus.DERIVED or not inference.claim.strip():
                continue
            result.append(
                DerivedHypothesis(
                    id=f"DH{len(result) + 1}",
                    claim=inference.claim,
                    source_inference_claim=inference.claim,
                    status="PROPOSED",
                    research_question=f"Independently test the joint inference: {inference.claim}",
                )
            )
            if len(result) >= max_hypotheses:
                break
        return tuple(result)


__all__ = ["DerivedHypothesis", "DerivedHypothesisGenerator"]
