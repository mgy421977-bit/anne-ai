"""Native, provider-free ANNE conversation loop.

This module deliberately does not call an LLM, network service, or external tool.
It turns a user message into a bounded cognitive turn and produces a small,
inspectable response from ANNE's own deterministic state.
"""

from __future__ import annotations

from dataclasses import dataclass

from anne.core.cognitive_state import Consciousness, CognitiveState, Hypothesis
from anne.core.pipeline import AnnePipeline
from anne.memory.fractal_memory import FractalMemory


@dataclass(frozen=True)
class ConversationTurn:
    """One native ANNE conversation turn."""

    user_input: str
    response: str
    state: CognitiveState


class NativeConversation:
    """Provider-free conversation surface for the ANNE core.

    The goal is not natural-language generation. The goal is to prove that
    ANNE can receive, frame, process, and respond to a turn without depending
    on another model. Model providers can be attached later as generators.
    """

    def __init__(
        self,
        memory: FractalMemory | None = None,
        pipeline: AnnePipeline | None = None,
    ) -> None:
        self.memory = memory or FractalMemory(":memory:")
        self.pipeline = pipeline or AnnePipeline(self.memory)
        self.turns: list[ConversationTurn] = []
        self.user = Consciousness(id="user", weight=1.0, exists=True)

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
            response = self._compose_response(state)

        turn = ConversationTurn(text, response, state)
        self.turns.append(turn)
        return turn

    @staticmethod
    def _compose_response(state: CognitiveState) -> str:
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

        if intent == "evidence_request":
            return (
                "Kanıt istediğini anladım. Dış kaynak doğrulaması olmadan "
                "bir bilgiyi doğrulanmış gerçek olarak sunmayacağım."
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
