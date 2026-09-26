from anne.language_learning import (
    LanguageLearningEngine,
    LanguageLearningMission,
    LanguageStatus,
    LearningSource,
)


def test_teacher_can_seed_language_without_external_authorization():
    engine = LanguageLearningEngine()
    profile = engine.seed(
        "Türkçe",
        "tr",
        source=LearningSource.HUMAN_TEACHER,
        units=("alfabe", "temel dilbilgisi", "temel kelime hazinesi"),
    )
    assert profile.status is LanguageStatus.ENABLED
    assert profile.authorized is True


def test_research_learning_requires_explicit_authorization():
    engine = LanguageLearningEngine()
    mission = LanguageLearningMission(
        language="English",
        code="en",
        objective="Learn basic English grammar",
        source=LearningSource.RESEARCH,
    )
    try:
        engine.start_mission(mission)
    except PermissionError:
        pass
    else:
        raise AssertionError("research learning must require authorization")


def test_authorized_language_can_start_research_mission():
    engine = LanguageLearningEngine()
    authorization = engine.authorize(
        "English",
        "en",
        granted_by="human",
    )
    mission = LanguageLearningMission(
        language="English",
        code="en",
        objective="Learn basic English grammar",
        source=LearningSource.RESEARCH,
        authorization_id=authorization.authorization_id,
    )
    assert engine.start_mission(mission).mission_id.startswith("lang_")
