from anne.core.verification import FactualStatus, VerificationResult
from anne.research.evidence_package import ResearchEvidencePackage
from anne.research.general import GeneralResearchEngine, ResearchMission
from anne.research.web_search import WebSearchResult


class FakeSearchProvider:
    def search(self, request):
        return [WebSearchResult("Source", "https://example.com/source", "candidate", source_domain="example.com")]


def test_research_report_becomes_unverified_evidence_package():
    report = GeneralResearchEngine(FakeSearchProvider()).research(
        ResearchMission(objective="research a claim")
    )
    package = ResearchEvidencePackage.from_report(report)

    assert package.evidence_status == "unverified"
    assert package.factual_status == FactualStatus.UNVERIFIED
    assert package.sources == ("https://example.com/source",)


def test_verification_promotes_only_with_provenance():
    report = GeneralResearchEngine(FakeSearchProvider()).research(
        ResearchMission(objective="research a claim")
    )
    package = ResearchEvidencePackage.from_report(report)
    verified = package.with_verification(
        VerificationResult(
            FactualStatus.VERIFIED,
            ("https://example.com/source",),
            "Independent verifier confirmed the claim.",
        )
    )

    assert verified.evidence_status == "available"
    assert verified.factual_status == FactualStatus.VERIFIED


def test_verified_without_source_is_rejected():
    report = GeneralResearchEngine(FakeSearchProvider()).research(
        ResearchMission(objective="research a claim")
    )
    package = ResearchEvidencePackage.from_report(report)

    try:
        package.with_verification(
            VerificationResult(FactualStatus.VERIFIED, (), "missing provenance")
        )
    except ValueError:
        pass
    else:
        raise AssertionError("verified evidence without provenance must fail")
