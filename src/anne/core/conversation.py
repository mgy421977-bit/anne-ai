"""Human conversation loop owned by ANNE's cognitive runtime.

ANNE is the cognitive actor. External models and services are instruments used
by ANNE; the human-facing answer is attributed to ANNE's evaluation of the
evidence, never to the model that happened to express it.

All epistemic decisions (research, comparison, revision, experience extraction)
are deterministic Python runtime logic. The LanguageInterface only expresses
content that ANNE has already decided.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from anne.core.cognitive_runtime import CognitiveWorkspace, HierarchicalPlanner, Metacognition


class LanguageInterface(Protocol):
    def express(self, content: str, *, language: str = "tr") -> str:
        """Express ANNE's decided content without adding decisions or facts."""


class ResearchInterface(Protocol):
    def research(self, question: str) -> dict[str, Any]:
        """Return evidence for ANNE to evaluate."""


class ConsultationInterface(Protocol):
    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        """Return an external explanation for ANNE to evaluate."""


_TIME_SENSITIVE = re.compile(
    r"\b(bugün|today|şu an|now|güncel|current|son|latest|202[4-9]|2030)\b",
    re.IGNORECASE,
)
_NEGATION = re.compile(
    r"\b(değil|yok|hayır|no|not|never|asla|yanlış|false|incorrect)\b",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+")


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1}


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta | tb), 1)


@dataclass
class EpistemicAssessment:
    """Inspectable research decision produced by ANNE runtime, not by an LLM."""

    research_required: bool
    reason: str
    confidence: float
    knowledge_state: str  # none | present | stale | uncertain


@dataclass
class ComparisonResult:
    """Deterministic comparison of previous factual answer vs new evidence."""

    status: str  # UNCHANGED | UPDATED | CONFLICT | INSUFFICIENT
    changed_since_previous: bool
    reason: str
    previous_response: str = ""
    new_evidence_summary: str = ""


@dataclass
class CognitiveAudit:
    """Inspectable decision trail for tests and debug (not required in user UI)."""

    question: str
    previous_knowledge_found: bool = False
    previous_confidence: float | None = None
    research_required: bool = False
    research_reason: str = ""
    evidence_count: int = 0
    comparison_status: str = "INSUFFICIENT"
    confidence: float = 0.0
    revision_decision: str = ""
    experience_observed: list[str] = field(default_factory=list)
    knowledge_state: str = "none"


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
    audit: CognitiveAudit | None = None
    comparison_status: str = "INSUFFICIENT"


class EpistemicPolicy:
    """Deterministic policy that decides whether ANNE needs fresh research.

    LLM has zero authority here. All inputs are inspectable runtime state.
    """

    CONFIDENCE_SKIP_THRESHOLD = 0.75
    MAX_AGE_HOURS_FOR_SKIP = 168.0  # 7 days

    def assess(
        self,
        question: str,
        previous: dict[str, Any] | None,
        research_available: bool,
        recent_experiences: list[dict[str, Any]] | None = None,
    ) -> EpistemicAssessment:
        if not research_available:
            return EpistemicAssessment(
                research_required=False,
                reason="No research capability configured",
                confidence=0.4,
                knowledge_state="none" if previous is None else "present",
            )

        if previous is None:
            return EpistemicAssessment(
                research_required=True,
                reason="No previous factual answer found for this exact question",
                confidence=0.3,
                knowledge_state="none",
            )

        prev_conf = float(previous.get("confidence", 0.5))
        age_hours = self._age_hours(str(previous.get("timestamp", "")))
        time_sensitive = bool(_TIME_SENSITIVE.search(question))
        uncertainty = self._has_unresolved_uncertainty(str(previous.get("response", "")))
        experience_prefers_research = self._experience_prefers_research(
            recent_experiences or []
        )

        if time_sensitive:
            return EpistemicAssessment(
                research_required=True,
                reason="Question appears time-sensitive; refresh evidence",
                confidence=0.5,
                knowledge_state="stale" if age_hours and age_hours > 24 else "present",
            )

        if uncertainty:
            return EpistemicAssessment(
                research_required=True,
                reason="Previous answer contained unresolved uncertainty",
                confidence=max(0.2, prev_conf - 0.2),
                knowledge_state="uncertain",
            )

        if (
            prev_conf >= self.CONFIDENCE_SKIP_THRESHOLD
            and age_hours is not None
            and age_hours <= self.MAX_AGE_HOURS_FOR_SKIP
            and not experience_prefers_research
        ):
            return EpistemicAssessment(
                research_required=False,
                reason=(
                    f"Previous answer confidence={prev_conf:.2f} and age={age_hours:.1f}h "
                    "sufficient; research not required"
                ),
                confidence=prev_conf,
                knowledge_state="present",
            )

        return EpistemicAssessment(
            research_required=True,
            reason="Previous knowledge present but refresh preferred for epistemic safety",
            confidence=min(0.6, prev_conf + 0.1),
            knowledge_state="present" if age_hours is not None and age_hours < 72 else "stale",
        )

    @staticmethod
    def _age_hours(timestamp: str) -> float | None:
        if not timestamp:
            return None
        try:
            ts = timestamp.replace("Z", "+00:00")
            then = datetime.fromisoformat(ts)
            if then.tzinfo is None:
                then = then.replace(tzinfo=UTC)
            return max(0.0, (datetime.now(UTC) - then).total_seconds() / 3600.0)
        except ValueError:
            return None

    @staticmethod
    def _has_unresolved_uncertainty(text: str) -> bool:
        markers = (
            "yeterli kanıt yok",
            "belirsiz",
            "emin değil",
            "insufficient",
            "uncertain",
            "bilmiyorum",
            "kesin değil",
        )
        lower = text.lower()
        return any(m in lower for m in markers)

    @staticmethod
    def _experience_prefers_research(experiences: list[dict[str, Any]]) -> bool:
        if not experiences:
            return False
        research_count = 0
        for exp in experiences[:5]:
            approach = exp.get("approach") or []
            if any("research" in str(a).lower() or "araştır" in str(a).lower() for a in approach):
                research_count += 1
        return research_count >= 2


class ComparisonEngine:
    """Runtime-owned comparison of previous factual answer vs new evidence."""

    OVERLAP_UNCHANGED = 0.55
    OVERLAP_CONFLICT_SIGNAL = 0.15

    def compare(
        self,
        previous: dict[str, Any] | None,
        evidence_texts: list[str],
    ) -> ComparisonResult:
        if previous is None:
            if not evidence_texts:
                return ComparisonResult(
                    status="INSUFFICIENT",
                    changed_since_previous=False,
                    reason="No previous answer and no usable evidence",
                )
            return ComparisonResult(
                status="UPDATED",
                changed_since_previous=True,
                reason="No previous answer; new evidence establishes baseline",
                new_evidence_summary="; ".join(t[:200] for t in evidence_texts[:3]),
            )

        prev_text = str(previous.get("response", "")).strip()
        if not evidence_texts:
            return ComparisonResult(
                status="INSUFFICIENT",
                changed_since_previous=False,
                reason="Previous answer exists but no new evidence to compare",
                previous_response=prev_text[:500],
            )

        combined = " ".join(evidence_texts)
        ov = _overlap(prev_text, combined)
        new_neg = len(_NEGATION.findall(combined))
        prev_neg = len(_NEGATION.findall(prev_text))
        conflict_signal = new_neg > prev_neg + 1 and ov < 0.35

        if conflict_signal or (ov < self.OVERLAP_CONFLICT_SIGNAL and new_neg > 0):
            return ComparisonResult(
                status="CONFLICT",
                changed_since_previous=True,
                reason="New evidence appears to contradict previous evaluation",
                previous_response=prev_text[:500],
                new_evidence_summary=combined[:400],
            )

        if ov >= self.OVERLAP_UNCHANGED:
            return ComparisonResult(
                status="UNCHANGED",
                changed_since_previous=False,
                reason=f"New evidence consistent with previous answer (overlap={ov:.2f})",
                previous_response=prev_text[:500],
                new_evidence_summary=combined[:400],
            )

        return ComparisonResult(
            status="UPDATED",
            changed_since_previous=True,
            reason=f"New evidence adds material not covered by previous answer (overlap={ov:.2f})",
            previous_response=prev_text[:500],
            new_evidence_summary=combined[:400],
        )


def _extract_evidence_texts(results: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for item in results:
        if not item.get("ok"):
            continue
        payload = item.get("data", item.get("result", ""))
        if isinstance(payload, dict):
            for key in ("answer", "summary", "text", "content", "data"):
                if key in payload and payload[key]:
                    texts.append(str(payload[key])[:4000])
                    break
            else:
                texts.append(str(payload)[:4000])
        else:
            text = str(payload).strip()
            if text:
                texts.append(text[:4000])
    return texts


def _build_experience_approach(
    research_used: bool,
    previous_used: bool,
    comparison: ComparisonResult,
    consultation_used: bool,
    uncertainty: bool,
) -> list[str]:
    approach: list[str] = ["previous_knowledge_check"]
    if previous_used:
        approach.append("previous_answer_used")
    if research_used:
        approach.append("research_used")
    if consultation_used:
        approach.append("consultation_used")
    approach.append(f"comparison_{comparison.status.lower()}")
    if comparison.changed_since_previous:
        approach.append("previous_answer_changed")
    if uncertainty:
        approach.append("uncertainty_detected")
    approach.append("anne_evaluation_formed")
    approach.append("experience_recorded")
    return approach


def _build_learning(
    previous: dict[str, Any] | None,
    comparison: ComparisonResult,
    research_used: bool,
    evidence_count: int,
) -> str:
    parts = [
        f"previous_knowledge_used={'yes' if previous else 'no'}",
        f"new_evidence_found={evidence_count}",
        f"knowledge_changed={comparison.changed_since_previous}",
        f"comparison_status={comparison.status}",
        f"research_used={research_used}",
        f"reason={comparison.reason}",
    ]
    return "; ".join(parts)


def _filter_model_attribution(text: str) -> str:
    patterns = [
        (r"(?i)\b(gemini|chatgpt|gpt-?[0-9]|claude|openrouter|llm)\s+(dedi|söyledi|diyor)\b", "Araştırma sonuçları gösteriyor"),
        (r"(?i)\b(according to|per)\s+(gemini|chatgpt|claude)\b", "mevcut değerlendirmeye göre"),
    ]
    out = text
    for pat, repl in patterns:
        out = re.sub(pat, repl, out)
    return out


@dataclass
class CognitiveConversation:
    """ANNE's end-to-end conversational cognitive cycle."""

    language: LanguageInterface
    research: ResearchInterface | None = None
    consultation: ConsultationInterface | None = None
    planner: HierarchicalPlanner = field(default_factory=HierarchicalPlanner)
    metacognition: Metacognition = field(default_factory=Metacognition)
    epistemic_policy: EpistemicPolicy = field(default_factory=EpistemicPolicy)
    comparison_engine: ComparisonEngine = field(default_factory=ComparisonEngine)

    def handle(
        self,
        actor: str,
        question: str,
        *,
        known_context: str = "",
        previous_answer: dict[str, Any] | None = None,
        recent_experiences: list[dict[str, Any]] | None = None,
    ) -> ManagerSummary:
        workspace = CognitiveWorkspace(task=question)
        workspace.add_goal(question).status = "active"
        workspace.transition("DUY")
        workspace.observations.append(f"Input actor={actor}")

        audit = CognitiveAudit(question=question)

        workspace.transition("BAK")
        previous = previous_answer
        if previous is None and known_context.strip() and known_context != "No local memories have been recorded yet.":
            previous = {
                "response": known_context[:2000],
                "confidence": 0.4,
                "timestamp": "",
                "question": question,
                "learning": "",
            }
        if previous is not None:
            audit.previous_knowledge_found = True
            audit.previous_confidence = float(previous.get("confidence", 0.5))
            workspace.observations.append("Previous factual answer located")

        assessment = self.epistemic_policy.assess(
            question=question,
            previous=previous,
            research_available=(self.research is not None or self.consultation is not None),
            recent_experiences=recent_experiences,
        )
        audit.research_required = assessment.research_required
        audit.research_reason = assessment.reason
        audit.knowledge_state = assessment.knowledge_state
        workspace.observations.append(f"Epistemic: {assessment.reason}")

        research_used = False
        if assessment.research_required and self.research is not None:
            workspace.transition("GÖR")
            evidence = self.research.research(question)
            ok = bool(evidence.get("ok", True)) if isinstance(evidence, dict) else True
            workspace.record_tool_result("MITOS", evidence, ok=ok)
            research_used = True
        elif not assessment.research_required:
            workspace.observations.append("Research skipped by EpistemicPolicy")
        else:
            workspace.observations.append("No dedicated research interface configured")

        workspace.transition("ANLA")
        evidence_items = sum(1 for item in workspace.tool_results if item.get("ok"))
        audit.evidence_count = evidence_items

        consultation_used = False
        if self.consultation is not None and evidence_items == 0 and assessment.research_required:
            consultation = self.consultation.ask(
                question,
                {
                    "known_context": known_context,
                    "previous_answer": previous,
                    "epistemic_reason": assessment.reason,
                },
            )
            ok = bool(consultation.get("ok", True)) if isinstance(consultation, dict) else True
            workspace.record_tool_result("CHATGPT", consultation, ok=ok)
            consultation_used = True
            evidence_items = sum(1 for item in workspace.tool_results if item.get("ok"))
            audit.evidence_count = evidence_items

        evidence_texts = _extract_evidence_texts(workspace.tool_results)
        comparison = self.comparison_engine.compare(previous, evidence_texts)
        audit.comparison_status = comparison.status
        audit.revision_decision = comparison.status

        workspace.transition("HİSSET")
        review = self.metacognition.review(workspace)
        conf = min(1.0, max(0.0, (review.confidence + assessment.confidence) / 2.0))
        if comparison.status == "CONFLICT":
            conf = min(conf, 0.45)
        elif comparison.status == "INSUFFICIENT":
            conf = min(conf, 0.55)
        audit.confidence = conf
        uncertainty = conf < 0.5 or comparison.status in ("CONFLICT", "INSUFFICIENT")

        answer_material = self._build_answer_material(
            question=question,
            previous=previous,
            results=workspace.tool_results,
            comparison=comparison,
            confidence=conf,
            research_used=research_used,
        )

        workspace.transition("YAP")
        raw_answer = self.language.express(answer_material, language="tr")
        answer = _filter_model_attribution(raw_answer)

        approach = _build_experience_approach(
            research_used=research_used,
            previous_used=previous is not None,
            comparison=comparison,
            consultation_used=consultation_used,
            uncertainty=uncertainty,
        )
        audit.experience_observed = list(approach)

        experience = ExperienceRecord(
            actor=actor,
            question=question,
            approach=approach,
            evaluation_criteria=[],
            objections=[],
            outcome=f"comparison={comparison.status}; confidence={conf:.2f}",
        )

        learned = _build_learning(previous, comparison, research_used, evidence_items)

        workspace.transition("ÖĞREN")
        return ManagerSummary(
            answer=answer,
            benefit=(
                "Soruyu önceki bilgi ve güncel kanıtla değerlendirip "
                "doğrulanabilir bir sonuç üretmek."
            ),
            learned=learned,
            current_evidence=evidence_items,
            changed_since_previous=comparison.changed_since_previous,
            experience=experience,
            audit=audit,
            comparison_status=comparison.status,
        )

    @staticmethod
    def _build_answer_material(
        question: str,
        previous: dict[str, Any] | None,
        results: list[dict[str, Any]],
        comparison: ComparisonResult,
        confidence: float,
        research_used: bool,
    ) -> str:
        evidence_lines: list[str] = []
        for index, result in enumerate(results, start=1):
            if not result.get("ok"):
                evidence_lines.append(
                    f"Kanıt {index}: kullanılamadı; belirsizlik olarak belirt."
                )
                continue
            payload = result.get("data", result.get("result", ""))
            text = str(payload).strip()
            if text:
                evidence_lines.append(f"Araştırma sonucu {index}: {text[:4000]}")
            else:
                evidence_lines.append(
                    f"Araştırma sonucu {index}: veri döndü, ayrıntı yok."
                )

        evidence_block = (
            "\n".join(evidence_lines) if evidence_lines else "Araştırma sonucu bulunamadı."
        )

        if comparison.status == "UNCHANGED":
            frame = (
                "Önceki değerlendirmem yeni kanıtlarla uyumlu. "
                "Mevcut bilgilerle karşılaştırıldığında anlamlı bir değişiklik yok. "
                "Önceki sonucu koruyarak ifade et."
            )
        elif comparison.status == "UPDATED":
            frame = (
                "Yeni araştırma sonuçları önceki bilgime ek anlamlı içerik getiriyor. "
                "Önceki bilgiyi güncelleyerek birleştir ve ANNE'nin güncel değerlendirmesi "
                "olarak sun."
            )
        elif comparison.status == "CONFLICT":
            frame = (
                "Yeni araştırma sonuçları önceki değerlendirmemle farklılık gösteriyor. "
                "Bunu gizleme. Kullanıcıya açıkça belirt: önceki bilgimi yeniden "
                "değerlendiriyorum ve yeni kanıtları dikkate alıyorum. "
                "Model adı kullanma."
            )
        else:
            frame = (
                "Karşılaştırma için yeterli kanıt yok veya önceki bilgi bulunamadı. "
                "Belirsizliği açıkça belirt. 'Bu konuda kesin sonuca varmak için "
                "yeterli kanıt yok' çerçevesini kullan."
            )

        prev_snippet = ""
        if previous is not None:
            prev_snippet = str(previous.get("response", ""))[:800]

        return (
            "Sen ANNE'nin dil arayüzüsün. Aşağıdaki içerik ANNE'nin bilişsel değerlendirmesinin "
            "ifade edilecek taslağıdır. Yalnızca doğal Türkçe ile ifade et. Yeni bilgi, karar, "
            "araç çağrısı, kaynak veya öğrenme ekleme. Harici bir modelin adını konuşmacı olarak "
            "kullanma ve 'Gemini dedi', 'ChatGPT dedi' gibi bir atıf üretme. Sonucu ANNE'nin "
            "değerlendirmesi olarak anlat.\n\n"
            "KONUŞMACI: ANNE\n"
            f"SORU: {question}\n"
            f"ÖNCEKİ BİLGİ MEVCUT: {'evet' if previous is not None else 'hayır'}\n"
            f"ÖNCEKİ CEVAP ÖZETİ: {prev_snippet or 'yok'}\n"
            f"KARŞILAŞTIRMA DURUMU: {comparison.status}\n"
            f"KARŞILAŞTIRMA NEDENİ: {comparison.reason}\n"
            f"ARAŞTIRMA YAPILDI: {'evet' if research_used else 'hayır'}\n"
            f"BİLİŞSEL DEĞERLENDİRME GÜVENİ: {confidence:.2f}\n"
            f"KANIT KAYITLARI: {len(results)}\n"
            f"KULLANICIYA YANSITILACAK ÇERÇEVE: {frame}\n\n"
            f"ARAŞTIRMA MALZEMESİ:\n{evidence_block}"
        )


__all__ = [
    "CognitiveAudit",
    "CognitiveConversation",
    "ComparisonEngine",
    "ComparisonResult",
    "ConsultationInterface",
    "EpistemicAssessment",
    "EpistemicPolicy",
    "ExperienceRecord",
    "LanguageInterface",
    "ManagerSummary",
    "ResearchInterface",
]
