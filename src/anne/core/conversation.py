"""Human conversation loop owned by ANNE's cognitive runtime.

Language models are linguistic instruments. ANNE owns the decision to research,
consult, compare, learn and revise; external services only return material for
ANNE to evaluate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from anne.core.cognitive_runtime import CognitiveWorkspace, HierarchicalPlanner, Metacognition


class LanguageInterface(Protocol):
    def express(self, content: str, *, language: str = "tr") -> str:
        """Express ANNE's decided content without adding decisions."""


class ResearchInterface(Protocol):
    def research(self, question: str) -> dict[str, Any]:
        """Return evidence for ANNE to evaluate."""


class ConsultationInterface(Protocol):
    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        """Return an external explanation for ANNE to evaluate."""


@dataclass
class ExperienceRecord:
    """Observed problem-solving pattern, kept separate from factual memory."""
    actor: str
    question: str
    approach: list[str] = field(default_factory=list)
    evaluation_criteria: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    outcome: str = ""


@dataclass
class ManagerSummary:
    answer: str
    benefit: str
    learned: str
    current_evidence: int = 0
    changed_since_previous: bool = False
    experience: ExperienceRecord | None = None


@dataclass
class CognitiveConversation:
    """ANNE's end-to-end conversational cognitive cycle."""

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

        # Epistemic action is ANNE's decision. If a research interface exists,
        # current evidence is checked again even when an older answer exists.
        workspace.transition("BAK")
        needs_research = self.research is not None
        if needs_research:
            workspace.transition("GÖR")
            evidence = self.research.research(question)
            ok = bool(evidence.get("ok", True)) if isinstance(evidence, dict) else True
            workspace.record_tool_result("MITOS", evidence, ok=ok)
        else:
            workspace.observations.append("No research interface configured")

        workspace.transition("ANLA")
        evidence_items = sum(1 for item in workspace.tool_results if item.get("ok"))

        # ANNE decides whether external consultation is useful; the language
        # model never emits a tool call and cannot invoke this branch itself.
        if self.consultation is not None and evidence_items == 0:
            consultation = self.consultation.ask(question, {"known_context": known_context})
            ok = bool(consultation.get("ok", True)) if isinstance(consultation, dict) else True
            workspace.record_tool_result("CHATGPT", consultation, ok=ok)

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
                "güncel araştırma",
                "gerekiyorsa harici danışma",
                "kanıtı değerlendirme",
                "önceki bilgiyle karşılaştırma",
                "sonucu sunma ve tecrübe kaydı",
            ],
            outcome="ANNE tarafından tamamlanan bilişsel konuşma döngüsü",
        )
        workspace.transition("ÖĞREN")
        return ManagerSummary(
            answer=answer,
            benefit="Soruyu güncel ve önceki bilgiyle değerlendirip doğrulanabilir bir sonuç üretmek.",
            learned="Bu etkileşimdeki problem çözme yolu ayrı bir tecrübe kaydı olarak saklandı.",
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
            "ANNE'NİN KARAR VERDİĞİ İÇERİK. Bunu yalnızca doğal Türkçeye dönüştür; "
            "yeni bilgi, karar, araç çağrısı veya öğrenme ekleme.\n"
            f"Soru: {question}\n"
            f"Önceki bilgi mevcut: {'evet' if known_context.strip() else 'hayır'}\n"
            f"Güncel kanıt kaydı: {len(results)}\n"
            f"Bilişsel değerlendirme güveni: {confidence:.2f}\n"
            "Belirsizlik ve kanıt eksikliği varsa aynen belirt."
        )


__all__ = [
    "CognitiveConversation",
    "ConsultationInterface",
    "ExperienceRecord",
    "LanguageInterface",
    "ManagerSummary",
    "ResearchInterface",
]
