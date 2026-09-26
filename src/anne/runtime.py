"""ANNE's client-neutral runtime entry point.

This is the boundary Tinker, VITA Intelligence, or another client can call.
The runtime decides whether a user message needs research, creates the
ResearchMission, runs bounded retrieval, and feeds candidate evidence into
ANNE's guarded reasoning path.

Language-learning requests are routed through the governed language-learning
engine. No new language is researched or enabled without explicit
authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anne.core.decision_loop import DecisionLoop, DecisionResult
from anne.language_learning import (
    LanguageLearningEngine,
    LanguageLearningMission,
    LearningSource,
)
from anne.research.general import GeneralResearchEngine
from anne.research.web_search import WebSearchProvider


@dataclass(frozen=True)
class AnneRequest:
    text: str
    research: bool | None = None
    scope: str = "general"
    max_searches: int = 5
    max_results_per_search: int = 10


@dataclass(frozen=True)
class AnneResponse:
    mode: str
    result: DecisionResult | None
    research_used: bool
    mission_id: str | None
    language_learning: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "result": self.result.as_dict() if self.result else None,
            "research_used": self.research_used,
            "mission_id": self.mission_id,
            "language_learning": self.language_learning,
        }


class AnneRuntime:
    """The public question → research → evidence → reasoning entry point."""

    def __init__(
        self,
        search_provider: WebSearchProvider,
        *,
        decision_loop: DecisionLoop | None = None,
        language_engine: LanguageLearningEngine | None = None,
    ) -> None:
        self.decision_loop = decision_loop or DecisionLoop()
        self.research_engine = GeneralResearchEngine(search_provider)
        self.language_engine = language_engine or LanguageLearningEngine()

    @staticmethod
    def _is_language_request(text: str) -> bool:
        lowered = text.casefold()
        return any(
            marker in lowered
            for marker in (
                "türkçe öğren",
                "ingilizce öğren",
                "english öğren",
                "learn turkish",
                "learn english",
                "dil öğren",
                "language learning",
            )
        )

    @staticmethod
    def _language_from_request(text: str) -> tuple[str, str]:
        lowered = text.casefold()
        if "türkçe" in lowered or "turkish" in lowered:
            return "Türkçe", "tr"
        if "ingilizce" in lowered or "english" in lowered:
            return "English", "en"
        raise ValueError("language could not be determined from request")

    @staticmethod
    def _needs_research(request: AnneRequest) -> bool:
        if request.research is not None:
            return request.research
        lowered = request.text.casefold()
        return any(
            marker in lowered
            for marker in (
                "araştır",
                "research",
                "kaynak",
                "güncel",
                "latest",
                "today",
                "mevzuat",
                "fiyat",
                "kimdir",
                "nedir",
                "hangi",
                "how",
                "why",
            )
        )

    def teach_language(
        self,
        language: str,
        code: str,
        *,
        units: tuple[str, ...],
        teacher: str = "human",
    ) -> dict[str, Any]:
        profile = self.language_engine.seed(
            language,
            code,
            source=LearningSource.HUMAN_TEACHER,
            units=units,
        )
        return {
            "status": profile.status.value,
            "language": profile.language,
            "code": profile.code,
            "learned_units": profile.learned_units,
            "source": LearningSource.HUMAN_TEACHER.value,
            "teacher": teacher,
        }

    def authorize_language_learning(
        self,
        language: str,
        code: str,
        *,
        granted_by: str,
    ):
        return self.language_engine.authorize(
            language,
            code,
            granted_by=granted_by,
        )

    def handle(self, request: AnneRequest) -> AnneResponse:
        text = request.text.strip()
        if not text:
            raise ValueError("request text is required")

        if self._is_language_request(text):
            language, code = self._language_from_request(text)
            profile = self.language_engine.profile(code)
            if not profile or not profile.authorized:
                return AnneResponse(
                    mode="LANGUAGE_LEARNING",
                    result=None,
                    research_used=False,
                    mission_id=None,
                    language_learning={
                        "status": "AUTHORIZATION_REQUIRED",
                        "language": language,
                        "code": code,
                        "message": (
                            "This language is not authorized for autonomous "
                            "research-based learning."
                        ),
                    },
                )
            mission = LanguageLearningMission(
                language=language,
                code=code,
                objective=text,
                source=LearningSource.RESEARCH,
                authorization_id=(
                    self.language_engine.authorization(code).authorization_id
                    if self.language_engine.authorization(code)
                    else None
                ),
            )
            started = self.language_engine.start_mission(mission)
            report = self.research_engine.research(
                self.decision_loop.make_research_mission(
                    started.objective,
                    scope=f"language:{code}",
                    questions=(
                        f"{language} grammar rules",
                        f"{language} vocabulary and usage",
                    ),
                    max_searches=request.max_searches,
                    max_results_per_search=request.max_results_per_search,
                )
            )
            return AnneResponse(
                mode="LANGUAGE_LEARNING",
                result=None,
                research_used=True,
                mission_id=report.mission_id,
                language_learning={
                    "status": "RESEARCH_STARTED",
                    "language": language,
                    "code": code,
                    "mission_id": started.mission_id,
                    "evidence_status": report.evidence_status,
                    "verification_status": report.verification_status,
                    "sources": len(report.sources),
                },
            )

        if self._needs_research(request):
            result = self.decision_loop.run_with_research(
                text,
                self.research_engine,
                scope=request.scope,
                max_searches=request.max_searches,
                max_results_per_search=request.max_results_per_search,
            )
            mission_id = None
            if result.state:
                mission_id = result.state.context_map.get("research_mission_id")
            return AnneResponse(
                mode="RESEARCH",
                result=result,
                research_used=True,
                mission_id=mission_id,
            )

        result = self.decision_loop.run(text)
        return AnneResponse(
            mode="DIRECT",
            result=result,
            research_used=False,
            mission_id=None,
        )


__all__ = ["AnneRequest", "AnneResponse", "AnneRuntime"]
