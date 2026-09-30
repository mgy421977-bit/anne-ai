from anne.core.intent import IntentClassifier, IntentKind
from anne.language.policy import TurkishLanguageCheckPolicy


def test_high_ambiguity_routes_to_language_check():
    intent = IntentClassifier().classify("Bunu yap")
    decision = TurkishLanguageCheckPolicy().decide(intent)

    assert intent.intent is IntentKind.ACTION_REQUEST
    assert decision.should_lookup is True


def test_low_ambiguity_does_not_route_to_language_check():
    intent = IntentClassifier().classify("Bu nedir?")
    decision = TurkishLanguageCheckPolicy().decide(intent)

    assert intent.ambiguity < 0.6
    assert decision.should_lookup is False


def test_greeting_never_routes_to_language_check():
    intent = IntentClassifier().classify("Merhaba")
    decision = TurkishLanguageCheckPolicy().decide(intent)

    assert decision.should_lookup is False


def test_policy_threshold_is_bounded():
    for value in (-0.1, 1.1):
        try:
            TurkishLanguageCheckPolicy(ambiguity_threshold=value)
        except ValueError:
            pass
        else:
            raise AssertionError("threshold outside [0, 1] must be rejected")
