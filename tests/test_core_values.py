from anne.core.values import ANNECore, CoreDecision


def test_goodness_and_equality_both_allow_proceed() -> None:
    result = ANNECore().resolve(goodness=1.0, equality=1.0)
    assert result.decision is CoreDecision.PROCEED


def test_goodness_blocks_when_the_path_is_bad() -> None:
    result = ANNECore().resolve(goodness=0.0, equality=1.0)
    assert result.decision is CoreDecision.BLOCK


def test_equality_violation_blocks_when_no_goodness_conflict_is_declared() -> None:
    result = ANNECore().resolve(goodness=1.0, equality=0.0)
    assert result.decision is CoreDecision.BLOCK


def test_goodness_wins_when_principles_explicitly_conflict() -> None:
    result = ANNECore().resolve(
        goodness=0.9,
        equality=0.1,
        principles_conflict=True,
    )
    assert result.decision is CoreDecision.PROCEED
    assert "goodness has priority" in result.reason


def test_no_common_solution_produces_separate_solutions() -> None:
    result = ANNECore().resolve(
        goodness=0.9,
        equality=1.0,
        parties_conflict=True,
        common_solution=False,
    )
    assert result.decision is CoreDecision.SEPARATE
    assert "independent solutions" in result.reason


def test_scores_are_bounded() -> None:
    for name in ("goodness", "equality"):
        try:
            ANNECore().resolve(
                goodness=1.2 if name == "goodness" else 1.0,
                equality=1.2 if name == "equality" else 1.0,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"{name} accepted an out-of-range score")
