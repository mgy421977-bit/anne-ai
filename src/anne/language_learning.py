"""Language acquisition boundaries for ANNE.

Language learning is treated as a governed capability: ANNE may learn a
language from an explicitly authorized curriculum, teacher input, or
research-backed material, but a new language is never enabled implicitly.

The module stores learning state and evidence metadata; it does not pretend
that exposure to text is the same as verified linguistic knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class LanguageStatus(str, Enum):
    ENABLED = "ENABLED"
    LEARNING = "LEARNING"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


class LearningSource(str, Enum):
    HUMAN_TEACHER = "HUMAN_TEACHER"
    RESEARCH = "RESEARCH"
    CURRICULUM = "CURRICULUM"


@dataclass(frozen=True)
class LanguageProfile:
    language: str
    code: str
    status: LanguageStatus
    native_or_target: str = "target"
    grammar_version: str = "1.0"
    vocabulary_version: str = "1.0"
    authorized: bool = False
    learned_units: tuple[str, ...] = ()


@dataclass(frozen=True)
class LanguageLearningMission:
    language: str
    code: str
    objective: str
    source: LearningSource
    authorization_id: str | None = None
    mission_id: str = field(default_factory=lambda: f"lang_{uuid4().hex[:12]}")

    def validate(self) -> None:
        if not self.language.strip() or not self.code.strip():
            raise ValueError("language and code are required")
        if not self.objective.strip():
            raise ValueError("objective is required")
        if self.source is not LearningSource.HUMAN_TEACHER and not self.authorization_id:
            raise PermissionError("language learning requires explicit authorization")


@dataclass(frozen=True)
class LanguageObservation:
    language: str
    code: str
    category: str
    content: str
    source: LearningSource
    source_url: str = ""
    verified: bool = False
    confidence: str = "UNVERIFIED"


@dataclass(frozen=True)
class LearningAuthorization:
    authorization_id: str
    language: str
    code: str
    granted_by: str
    scope: str = "language_learning"
    active: bool = True


class LanguageLearningEngine:
    """Governed language-learning state; no implicit language activation."""

    def __init__(self, profiles: tuple[LanguageProfile, ...] = ()) -> None:
        self._profiles = {profile.code: profile for profile in profiles}

    def authorize(
        self,
        language: str,
        code: str,
        *,
        granted_by: str,
        authorization_id: str | None = None,
    ) -> LearningAuthorization:
        if not language.strip() or not code.strip() or not granted_by.strip():
            raise ValueError("language, code and granted_by are required")
        authorization = LearningAuthorization(
            authorization_id=authorization_id or f"auth_{uuid4().hex[:12]}",
            language=language,
            code=code,
            granted_by=granted_by,
        )
        self._profiles[code] = LanguageProfile(
            language=language,
            code=code,
            status=LanguageStatus.LEARNING,
            authorized=True,
        )
        return authorization

    def seed(
        self,
        language: str,
        code: str,
        *,
        source: LearningSource,
        units: tuple[str, ...],
        authorization: LearningAuthorization | None = None,
    ) -> LanguageProfile:
        if source is not LearningSource.HUMAN_TEACHER and authorization is None:
            raise PermissionError("seed requires authorization for non-teacher sources")
        if source is not LearningSource.HUMAN_TEACHER and authorization and not authorization.active:
            raise PermissionError("authorization is inactive")
        if not language.strip() or not code.strip():
            raise ValueError("language and code are required")
        profile = LanguageProfile(
            language=language,
            code=code,
            status=LanguageStatus.ENABLED,
            authorized=True,
            learned_units=tuple(dict.fromkeys(unit.strip() for unit in units if unit.strip())),
        )
        self._profiles[code] = profile
        return profile

    def start_mission(self, mission: LanguageLearningMission) -> LanguageLearningMission:
        mission.validate()
        profile = self._profiles.get(mission.code)
        if not profile or not profile.authorized:
            raise PermissionError("language is not authorized for learning")
        return mission

    def profile(self, code: str) -> LanguageProfile | None:
        return self._profiles.get(code)


__all__ = [
    "LanguageStatus",
    "LearningSource",
    "LanguageProfile",
    "LanguageLearningMission",
    "LanguageObservation",
    "LearningAuthorization",
    "LanguageLearningEngine",
]
