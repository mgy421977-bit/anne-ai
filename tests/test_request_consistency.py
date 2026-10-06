from anne.core.request_consistency import RequestConsistencyGate


def test_consistent_request_continues():
    result = RequestConsistencyGate.evaluate("Raporu oluştur ve göster")
    assert result.status == "CONSISTENT"
    assert result.action == "CONTINUE"


def test_same_action_required_and_forbidden_is_inconsistent():
    result = RequestConsistencyGate.evaluate("Dosyayı oluştur ama dosyayı oluşturma")
    assert result.status == "INCONSISTENT"
    assert result.action == "REFRAME"
    assert result.contradictions


def test_consistency_does_not_claim_factual_truth():
    result = RequestConsistencyGate.evaluate("Ay'ın yüzeyinde su vardır")
    assert result.status == "CONSISTENT"
    assert result.action == "CONTINUE"


def test_empty_request_is_undetermined():
    result = RequestConsistencyGate.evaluate("   ")
    assert result.status == "UNDETERMINED"
    assert result.action == "REVIEW"
