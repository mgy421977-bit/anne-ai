from anne.core.source_independence import (
    SourceIndependence,
    SourceIndependenceStatus,
)


def test_same_publisher_family_is_not_multiple_independent_sources():
    assessment = SourceIndependence.assess(
        (
            "https://example.com/a",
            "https://example.com/b",
        )
    )

    assert assessment.status == SourceIndependenceStatus.SINGLE_PUBLISHER_FAMILY
    assert assessment.distinct_publisher_family_count == 1


def test_multiple_publisher_families_are_explicitly_counted():
    assessment = SourceIndependence.assess(
        (
            "https://example.com/a",
            "https://news.example.com/a",
            "https://news.example.org/story",
        )
    )

    assert assessment.status == SourceIndependenceStatus.MULTIPLE_PUBLISHER_FAMILIES
    assert assessment.publisher_families == ("example.com", "example.org")
    assert assessment.distinct_publisher_family_count == 2


def test_common_multilabel_public_suffix_is_handled_conservatively():
    assert (
        SourceIndependence.publisher_family("https://news.example.co.uk/story")
        == "example.co.uk"
    )
    assert (
        SourceIndependence.publisher_family("https://sub.wikipedia.org/page")
        == "wikipedia.org"
    )


def test_unknown_relationship_does_not_become_independent():
    assessment = SourceIndependence.assess(
        (
            "not-a-url",
            "https://example.com/story",
        )
    )

    assert assessment.status == SourceIndependenceStatus.UNKNOWN
    assert assessment.unknown_sources == 1


def test_serialization_is_explicit():
    assessment = SourceIndependence.assess(
        (
            "https://one.example.com/a",
            "https://two.example.org/b",
        )
    )

    assert assessment.as_dict() == {
        "status": "multiple_publisher_families",
        "publisher_families": ["example.com", "example.org"],
        "unknown_sources": 0,
        "distinct_publisher_family_count": 2,
    }
