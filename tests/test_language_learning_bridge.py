from anne.language.bitigci import BitigciProvider
from anne.language.learning import to_evidence_items


def test_language_lookup_maps_to_non_authoritative_evidence_item():
    result = BitigciProvider(
        lambda _: {
            "meaning": "Bir sözcüğün bağlama göre açıklaması.",
            "examples": ("Örnek kullanım.",),
            "context": {"register": "standard"},
            "source_ref": "https://bitigci.shakalin.net/madde/ornek",
        }
    ).lookup("örnek")

    items = to_evidence_items(result)

    assert len(items) == 1
    item = items[0]
    assert item.source == "bitigci"
    assert item.kind == "language"
    assert item.provenance.endswith("/ornek")
    assert item.support == "unclear"
    assert "Örnek kullanım." in item.passage
    assert "register=standard" in item.passage


def test_empty_language_lookup_produces_no_evidence_items():
    result = BitigciProvider().lookup("bağlam")

    assert to_evidence_items(result) == ()
