from __future__ import annotations

from anne.learning.evidence import EvidenceItem
from anne.learning.web_providers import ProviderLimits, ScraplingProvider


class FakePage:
    status = 200

    def get_all_text(self, *, ignore_tags):
        assert ignore_tags == ("script", "style")
        return "  Main evidence text.  "


def test_scrapling_provider_applies_bounded_fetch_policy() -> None:
    calls: list[dict[str, object]] = []

    def fetch_page(url: str, **kwargs: object) -> FakePage:
        calls.append({"url": url, **kwargs})
        return FakePage()

    provider = ScraplingProvider(
        limits=ProviderLimits(timeout_seconds=3, max_claim_chars=40, max_passage_chars=20),
        fetch_page=fetch_page,
    )

    items = provider.research("https://example.test/source")

    assert len(items) == 1
    assert isinstance(items[0], EvidenceItem)
    assert items[0].claim == "Main evidence text."
    assert items[0].passage == "Main evidence text."
    assert items[0].provenance == "https://example.test/source"
    assert calls == [
        {
            "url": "https://example.test/source",
            "timeout": 3,
            "retries": 0,
            "follow_redirects": "safe",
        }
    ]


def test_scrapling_provider_rejects_error_status() -> None:
    class ErrorPage:
        status = 503

    provider = ScraplingProvider(fetch_page=lambda *_args, **_kwargs: ErrorPage())

    assert provider.research("https://example.test/unavailable") == ()


def test_scrapling_provider_rejects_non_url_queries() -> None:
    provider = ScraplingProvider(fetch_page=lambda *_args, **_kwargs: FakePage())

    assert provider.research("not-a-url") == ()
