"""Human conversation loop owned by ANNE's cognitive runtime.

The language model is deliberately a linguistic instrument: it turns ANNE's
already-decided message plan into natural language. It never chooses whether
to research, consult an external assistant, learn, or revise knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from anne.core.cognitive_runtime import CognitiveWorkspace, HierarchicalPlanner, Metacognition


class LanguageInterface(Protocol):
    """Natural-language surface used by ANNE after cognition has decided content."""

    def express(self, content: str, *, language: str = "tr") -> str:
        """Express ANNE's decided content without adding decisions."""


class ResearchInterface(Protocol):
    """External research controlled by ANNE's cognitive flow."""

    def research(self, question: str) -> dict[str, Any]:
        """Return evidence; never decide what ANNE should believe."""


class ConsultationInterface(Protocol):
    """External consultation controlled by ANNE."""

    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        """Return an external explanation for ANNE to evaluate."""


@dataclass
class ExperienceRecord:
    """A record of a person's problem-solving pattern, separate from facts."""

    actor: str
    question: str
    approach: list[str] = field(default_factory=list)
    evaluation_criteria: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    outcome: str = ""


@dataclass
class ManagerSummary:
    """Human-facing result after ANNE completes its cognitive cycle."""

    answer: str
    benefit: str
    learned: str
    current_evidence: int = 0
    changed_since_previous: bool = False
    experience: ExperienceRecord | None = None


@dataclass
class CognitiveConversation:
    """ANNE-owned conversation orchestration.

    The important invariant is that language, research and consultation are
    dependencies. The state transitions and decisions belong to ANNE.
    """

    language: LanguageInterface
    research: ResearchInterface | None = None
    consultation: ConsultationInterface | None = None
    planner: HierarchicalPlanner = field(default_factory=HierarchicalPlanner)
    metacognition: Metacognition = field(default_factory=Metacognition)

    def handle(self, actor: str, question: str, *, known_context: str = "") -> ManagerSummary:
        workspace = CognitiveWorkspace(task=question)
        workspace.add_goal(question).status = "active"
        workspace.transition("DUY")
        workspace.observations.append(f"Input actor={actor}")

        # ANNE decides epistemic state from its own workspace/memory layer.
        # This first implementation uses explicit knowledge availability rather
        # than asking a model to decide whether a tool should be called.
        workspace.transition("BAK")
        has_known_context = bool(known_context.strip())
        needs_research = not has_known_context
        if needs_research and self.research is not None:
            workspace.transition("GÖR")
            evidence = self.research.research(question)
            workspace.record_tool_result("MITOS", evidence, ok=True)
        elif needs_research:
            workspace.observations.append("No research interface configured")

        workspace.transition("ANLA")
        evidence_items = sum(
            1 for item in workspace.tool_results if item.get("ok")
        )

        # Consultation is a deliberate ANNE decision, never an LLM tool call.
        if needs_research and self.consultation is not None and evidence_items == 0:
            consultation = self.consultation.ask(question, {"known_context": known_context})
            workspace.record_tool_result("CHATGPT", consultation, ok=True)

        workspace.transition("HİSSET")
        review = self.metacognition.review(workspace)
        answer_material = self._build_answer_material(
            question, known_context, workspace.tool_results, review.confidence
        )
        workspace.transition("YAP")
        answer = self.language.express(answer_material, language="tr")

        experience = ExperienceRecord(
            actor=actor,
            question=question,
            approach=[
                "mevcut bilgi kontrolü",
                "gerekirse dış araştırma",
                "gerekirse harici danışma",
                "kanıtı değerlendirme",
                "sonucu sunma",
            ],
            outcome="ANNE tarafından tamamlanan bilişsel konuşma döngüsü",
        )
        workspace.transition("ÖĞREN")
        return ManagerSummary(
            answer=answer,
            benefit="Soruyu güncel/önceki bilgiyle değerlendirip doğrulanabilir bir sonuç üretmek.",
            learned="Bu etkileşimde kullanılan problem çözme yolu tecrübe kaydı olarak ayrıştırıldı.",
            current_evidence=evidence_items,
            changed_since_previous=False,
            experience=experience,
        )

    @staticmethod
    def _build_answer_material(
        question: str,
        known_context: str,
        results: list[dict[str, Any]],
        confidence: float,
    ) -> str:
        return (
            "ANNE KARARI — bunu doğal Türkçeye dönüştür; yeni karar veya bilgi ekleme.\n"
            f"Soru: {question}\n"
            f"Önceki bilgi mevcut: {'evet' if known_context.strip() else 'hayır'}\n"
            f"Dış kanıt kayıtları: {len(results)}\n"
            f"Bilişsel değerlendirme güveni: {confidence:.2f}\n"
            "Sonucu kullanıcıya açıkla; belirsizliği ve kanıt eksikliğini açıkça belirt."
        )


__all__ = [
    "CognitiveConversation",
    "ConsultationInterface",
    "ExperienceRecord",
    "LanguageInterface",
    "ManagerSummary",
    "ResearchInterface",
]
