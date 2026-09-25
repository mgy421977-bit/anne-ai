"""Executable protocol connecting MITOS exploration to ANNE evaluation.

MITOS can now run bounded public-web research and hand provenance-preserving
EvidencePackage records to ANNE. Research is read-only; validation remains an
ANNE responsibility.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from anne.core.global_workspace import GlobalWorkspace, WorkspaceItem
from anne.mythos.engine import HypothesisCandidate, MitosEngine
from anne.mythos.experience import ExperienceRecord
from anne.mythos.web_research import MitosResearchResult, MitosWebResearcher


@dataclass(frozen=True)
class DiscoveryBatch:
    goal: str
    candidates: list[HypothesisCandidate]
    shortlisted: list[HypothesisCandidate]


class MitosAnneLoop:
    """Bounded MITOS loop: explore/research -> broadcast -> ANNE gate."""

    def __init__(
        self,
        engine: MitosEngine | None = None,
        workspace: GlobalWorkspace | None = None,
        researcher: MitosWebResearcher | None = None,
    ) -> None:
        self.engine = engine or MitosEngine()
        self.workspace = workspace or GlobalWorkspace()
        self.researcher = researcher or MitosWebResearcher()

    def propose(
        self,
        goal: str,
        batch_size: int = 10,
        evaluator: Callable[[HypothesisCandidate], bool] | None = None,
    ) -> DiscoveryBatch:
        candidates = self.engine.generate(goal, batch_size=batch_size)
        for candidate in candidates:
            self.workspace.publish(
                WorkspaceItem(
                    source="MITOS",
                    content=candidate,
                    salience=candidate.discovery_value,
                    confidence=candidate.probability,
                    novelty=candidate.novelty,
                    risk=candidate.harm_risk,
                )
            )
        gate = evaluator or (lambda c: c.harm_risk <= 0.0 and c.testability >= 0.25)
        shortlisted = [c for c in self.workspace.winners(batch_size) if gate(c.content)]
        return DiscoveryBatch(goal, candidates, [c.content for c in shortlisted])

    def research(
        self,
        objective: str,
        *,
        scope: str = "",
        queries: list[str] | None = None,
    ) -> MitosResearchResult:
        """Send a bounded public-web research package to ANNE's workspace."""
        result = self.researcher.research(
            objective,
            scope=scope,
            queries=queries,
        )
        for package in result.packages:
            self.workspace.publish(
                WorkspaceItem(
                    source="MITOS",
                    content=package,
                    salience=0.8,
                    confidence=0.20,
                    novelty=0.5,
                    risk=0.0,
                )
            )
        return result

    @staticmethod
    def begin_experience(candidate: HypothesisCandidate) -> ExperienceRecord:
        return ExperienceRecord(
            hypothesis_id=candidate.id,
            goal=candidate.goal,
            claim=candidate.claim,
            predicted_outcome="pending test",
            confidence=candidate.probability,
            context={
                "mode": candidate.mode.value,
                "novelty": candidate.novelty,
                "testability": candidate.testability,
                "expected_benefit": candidate.expected_benefit,
                "harm_risk": candidate.harm_risk,
                "test_cost": candidate.test_cost,
            },
        )
