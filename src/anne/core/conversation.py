"""Native ANNE conversation loop with optional bounded web research.

The conversation surface does not require an LLM. Web research can be enabled
for questions and research-oriented intents, while retrieved material remains
provenance-bearing evidence rather than automatically verified truth.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.cognitive_state import CognitiveState, Consciousness, Hypothesis
from anne.core.pipeline import AnnePipeline
from anne.learning.evidence import EvidenceItem
from anne.learning.web_research import WebResearcher
from anne.memory.fractal_memory import FractalMemory


@dataclass(frozen=True)
class ConversationTurn:
    """One native ANNE conversation turn."""

    user_input: str
    response: str
    state: CognitiveState


class NativeConversation:
    """Conversation surface for the ANNE core with optional web research.

    The native path can receive, frame, process, research, and respond to a
    turn without depending on another model. Model providers can be attached
    later as generators when richer language synthesis is desired.
    """

    def __init__(
        self,
        memory: FractalMemory | None = None,
        pipeline: AnnePipeline | None = None,
        web_researcher: WebResearcher | None = None,
        use_web_research: bool = True,
    ) -> None:
        self.memory = memory or FractalMemory(":memory:")
        self.pipeline = pipeline or AnnePipeline(self.memory)
        self.turns: list[ConversationTurn] = []
        self.user = Consciousness(id="user", weight=1.0, exists=True)
        self.web_researcher = web_researcher or WebResearcher()
        self.use_web_research = use_web_research

    def respond(self, user_input: str) -> ConversationTurn:
        text = user_input.strip()
        if not text:
            raise ValueError("user_input must not be empty")

        hypothesis = Hypothesis(
            id=f"turn-{len(self.turns) + 1}",
            topic="conversation",
            claim=text,
            probability=0.9,
            source="native",
        )
        fail_fast, state = self.pipeline.run_with_fail_fast(
            text,
            [self.user],
            hypothesis,
        )

        if not fail_fast.passed or state is None:
            response = "Bu isteği güvenli biçimde işleyemedim."
            if state is None:
                state = self.pipeline.duy(text, [self.user])
        else:
            state = self.pipeline.hisset(state)
            state = self.pipeline.yap(state, hypothesis)
            evidence: tuple[EvidenceItem, ...] = ()
            if self.use_web_research and state.intent in {
                "question",
                "evidence_request",
                "comparison",
                "planning",
                "uncertainty",
                "risk",
            }:
                try:
                    evidence = tuple(self.web_researcher.research(text))
                except Exception:
                    # External retrieval is optional. ANNE must remain usable
                    # when the network/search layer is unavailable.
                    evidence = ()
            response = self._compose_response(state, evidence)

        turn = ConversationTurn(text, response, state)
        self.turns.append(turn)
        return turn

    @staticmethod
    def _compose_response(state: CognitiveState, evidence: tuple[object, ...] = ()) -> str:
        intent = state.intent
        core = state.context_map.get("core_decision")
        action = state.action

        if action in {"HALT", "ABSTAIN"}:
            return (
                "Bunu şu anda güvenli biçimde sonuçlandıramıyorum. "
                f"ANNE çekirdeği: {state.context_map.get('core_reason', 'ek doğrulama gerekiyor.')}"
            )

        if intent == "greeting":
            return (
                "Merhaba. Ben ANNE. Şu anda dış bir model veya servis "
                "kullanmadan kendi bilişsel döngüm üzerinden seninle konuşuyorum. "
                "Seni dinliyorum."
            )

        if evidence:
            claims: list[EvidenceItem] = list(evidence)
            synthesized = WebResearcher.answer(state.raw_input, claims)
            lines = [
                "Web araştırması yaptım. Aşağıdaki yanıt yalnızca bulunan "
                "kaynaklı bulgulara dayanır; otomatik olarak doğrulanmış gerçek "
                "olarak sunulmuyor."
            ]
            if synthesized:
                lines.append("")
                lines.append(synthesized)
            lines.append("")
            lines.append("Kaynak bulguları:")
            for item in claims[:8]:
                passage = item.passage.strip() or item.claim.strip()
                lines.append(f"- {item.source}: {passage}")
            return "\n".join(lines)

        if intent == "evidence_request":
            return (
                "Kanıt istediğini anladım. Web araştırması sonucunda yeterli kaynak bulunmadı; "
                "bu nedenle bir bilgiyi doğrulanmış gerçek olarak sunmayacağım."
            )

        if intent == "action_request":
            return (
                "Bunu bir eylem isteği olarak çerçeveledim. Eylem yetkisini "
                "düşünmekten ayrı tutuyorum; bu oturumda dışarıda işlem yapmıyorum."
            )

        if intent == "question":
            return (
                "Sorunu aldım. Şimdilik bunu bir soru olarak çerçeveledim; "
                "cevabı uydurmak yerine hangi kanıtın gerektiğini ayırırım."
            )

        return (
            "Seni dinliyorum. Söylediğini ANNE'nin bilişsel döngüsünde "
            f"çerçeveledim. Çekirdek sonucu: {core or 'PROCEED'}."
        )


__all__ = ["ConversationTurn", "NativeConversation"]
