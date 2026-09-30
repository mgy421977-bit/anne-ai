"""Language evidence adapters for ANNE."""

from .bitigci import BitigciProvider
from .evidence import LanguageEvidence, LanguageEvidenceProvider, LanguageLookupResult
from .learning import to_evidence_items
from .policy import LanguageCheckDecision, TurkishLanguageCheckPolicy
from .service import LanguageCheckResult, TurkishLanguageEvidenceService
from .tdk import TdkProvider
from .verification import (
    LanguageEvidenceVerifier,
    LanguageVerificationResult,
    LanguageVerificationStatus,
)

__all__ = [
    "BitigciProvider",
    "LanguageCheckDecision",
    "LanguageCheckResult",
    "LanguageEvidence",
    "LanguageEvidenceProvider",
    "LanguageEvidenceVerifier",
    "LanguageLookupResult",
    "LanguageVerificationResult",
    "LanguageVerificationStatus",
    "TdkProvider",
    "TurkishLanguageCheckPolicy",
    "TurkishLanguageEvidenceService",
    "to_evidence_items",
]
