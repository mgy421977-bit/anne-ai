"""Epistemic hypothesis-space analysis for ANNE.

This module does not establish truth. It organizes candidate explanations,
checks bounded internal consistency, finds relationships, and identifies a
possible shared solution space. Novel-hypothesis synthesis is conservative:
it only emits a proposal when candidates share substantive terms and the
proposal remains explicitly unverified.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import re
from typing import Sequence

from anne.mythos.engine import HypothesisCandidate


@dataclass(frozen=True)
class HypothesisAssessment:
    candidate_id: str
    internally_consistent: bool
    evidence_status: str
    assumptions: tuple[str, ...]
    boundary_conditions: tuple[str, ...]


@dataclass(frozen=True)
class HypothesisRelation:
    left: str
    right: str
    shared_terms: tuple[str, ...]
    relation: str


@dataclass(frozen=True)
class EpistemicAnalysis:
    claim: str
    assessments: tuple[HypothesisAssessment, ...]
    relations: tuple[HypothesisRelation, ...]
    clusters: tuple[tuple[str, ...], ...]
    common_solution_space: tuple[str, ...]
    novel_hypothesis: str | None
    novel_hypothesis_status: str
    verification_boundary: tuple[str, ...]


class EpistemicAnalyzer:
    """Analyze a bounded set of hypotheses without making truth claims."""

    _STOPWORDS = {
        "bir", "ve", "veya", "ile", "için", "olan", "olabilir", "olur",
        "the", "a", "an", "and", "or", "for", "with", "may", "can",
        "under", "goal", "pathway", "satisfy", "testable", "bounded",
        "assumptions", "alternative", "cross", "domain", "analogy",
        "reveal", "overlooked", "constraint", "opportunity", "materially",
        "change", "solution", "space",
    }

    _ASSUMPTION_MARKERS = (
        "varsay", "kabul", "şart", "koşul", "assum", "provided", "assuming",
        "if ", "eğer ",
    )

    _BOUNDARY_MARKERS = (
        "sınır", "koşul", "şart", "under ", "only ", "unless ", "ancak ",
    )

    @classmethod
    def analyze(
        cls,
        claim: str,
        candidates: Sequence[HypothesisCandidate],
    ) -> EpistemicAnalysis:
        assessments = tuple(cls._assess(c) for c in candidates)
        relations: list[HypothesisRelation] = []
        adjacency: dict[str, set[str]] = {c.id: set() for c in candidates}
        for i, left in enumerate(candidates):
            left_terms = cls._terms(left.claim)
            for right in candidates[i + 1 :]:
                shared = tuple(sorted(left_terms & cls._terms(right.claim)))
                if len(shared) >= 2:
                    relation = "shared_solution_area"
                    relations.append(
                        HypothesisRelation(left.id, right.id, shared, relation)
                    )
                    adjacency[left.id].add(right.id)
                    adjacency[right.id].add(left.id)

        clusters: list[tuple[str, ...]] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate.id in seen:
                continue
            stack = [candidate.id]
            component: list[str] = []
            while stack:
                node = stack.pop()
                if node in seen:
                    continue
                seen.add(node)
                component.append(node)
                stack.extend(sorted(adjacency[node] - seen))
            if len(component) > 1:
                clusters.append(tuple(sorted(component)))

        term_counts = Counter()
        for candidate in candidates:
            term_counts.update(cls._terms(candidate.claim))
        common_terms = tuple(
            term for term, count in term_counts.most_common()
            if count >= 2
        )[:8]

        novel: str | None = None
        novel_status = "NOT_DERIVED"
        if len(common_terms) >= 2 and len(candidates) >= 2:
            novel = (
                "A shared mechanism suggested by multiple candidate hypotheses "
                "may be testable around: " + ", ".join(common_terms) + "."
            )
            novel_status = "SYNTHESIS_UNVERIFIED"

        verification_boundary = (
            "internal_consistency",
            "relationship_similarity",
            "common_solution_space",
            "novel_hypothesis_synthesis",
        )
        return EpistemicAnalysis(
            claim=claim,
            assessments=assessments,
            relations=tuple(relations),
            clusters=tuple(clusters),
            common_solution_space=common_terms,
            novel_hypothesis=novel,
            novel_hypothesis_status=novel_status,
            verification_boundary=verification_boundary,
        )

    @classmethod
    def _assess(cls, candidate: HypothesisCandidate) -> HypothesisAssessment:
        text = candidate.claim.strip()
        lower = text.lower()
        contradictions = (
            ("not " in lower and "must " in lower)
            or ("değil" in lower and "zorunlu" in lower)
        )
        assumptions = tuple(
            marker.strip()
            for marker in cls._ASSUMPTION_MARKERS
            if marker in lower
        )
        boundaries = tuple(
            marker.strip()
            for marker in cls._BOUNDARY_MARKERS
            if marker in lower
        )
        return HypothesisAssessment(
            candidate_id=candidate.id,
            internally_consistent=not contradictions,
            evidence_status=candidate.evidence_status,
            assumptions=assumptions,
            boundary_conditions=boundaries,
        )

    @classmethod
    def _terms(cls, text: str) -> set[str]:
        tokens = {
            token
            for token in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{4,}", text.lower())
            if token not in cls._STOPWORDS
        }
        return tokens


def analysis_as_dict(analysis: EpistemicAnalysis) -> dict[str, object]:
    """Return an inspection-friendly representation for CognitiveState."""
    return asdict(analysis)


__all__ = [
    "EpistemicAnalysis",
    "EpistemicAnalyzer",
    "HypothesisAssessment",
    "HypothesisRelation",
    "analysis_as_dict",
]
