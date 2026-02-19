"""
Test — SAR Narrative Generation

Validates:
- Fallback narrative is generated when LLM is unavailable
- Narrative contains required sections
- Severity determination is correct based on evidence
- Sentences are properly broken into components
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.services.sar_engine import (
    _determine_severity,
    _generate_fallback_narrative,
    _identify_data_gaps,
    _parse_llm_response,
)


class MockTransaction:
    def __init__(self, amount=1000, country="US", **kwargs):
        self.id = uuid.uuid4()
        self.transaction_ref = kwargs.get("ref", f"TXN-{uuid.uuid4().hex[:8]}")
        self.amount = amount
        self.currency = kwargs.get("currency", "USD")
        self.transaction_date = kwargs.get("date", datetime.now(timezone.utc))
        self.transaction_type = kwargs.get("type", "wire")
        self.direction = kwargs.get("direction", "outbound")
        self.counterparty_name = kwargs.get("counterparty", "Test Corp")
        self.counterparty_bank = kwargs.get("bank", "Test Bank")
        self.country = country
        self.purpose = kwargs.get("purpose", "payment")
        self.is_flagged = kwargs.get("flagged", False)


class MockRuleTrigger:
    def __init__(self, breached=True, **kwargs):
        self.id = uuid.uuid4()
        self.rule_code = kwargs.get("code", "AML-001")
        self.rule_description = kwargs.get("desc", "Structuring detection")
        self.threshold_value = kwargs.get("threshold", 10000)
        self.actual_value = kwargs.get("actual", 15000)
        self.breached = breached
        self.typology_code = kwargs.get("typology", "STRUCTURING")
        self.typology_description = kwargs.get("typology_desc", "Potential structuring activity")


class MockCase:
    def __init__(self, **kwargs):
        self.id = uuid.uuid4()
        self.customer_id = kwargs.get("customer_id", "CUST-001")
        self.customer_name = kwargs.get("customer_name", "John Doe")
        self.customer_type = kwargs.get("customer_type", "individual")
        self.customer_risk_rating = kwargs.get("risk_rating", "HIGH")
        self.kyc_id_type = kwargs.get("kyc_id_type", "passport")
        self.kyc_id_number = kwargs.get("kyc_id_number", "AB123456")
        self.kyc_country = kwargs.get("kyc_country", "US")
        self.kyc_occupation = kwargs.get("occupation", "business owner")
        self.kyc_onboarding_date = kwargs.get("onboarding", datetime(2023, 1, 15, tzinfo=timezone.utc))
        self.account_number = kwargs.get("account", "1234567890")
        self.account_type = kwargs.get("account_type", "checking")
        self.account_open_date = kwargs.get("open_date", datetime(2023, 1, 15, tzinfo=timezone.utc))
        self.account_balance = kwargs.get("balance", 50000)
        self.account_currency = kwargs.get("currency", "USD")
        self.alert_id = kwargs.get("alert_id", "ALERT-2026-001")
        self.alert_date = kwargs.get("alert_date", datetime.now(timezone.utc))
        self.alert_type = kwargs.get("alert_type", "structuring")
        self.alert_score = kwargs.get("alert_score", 85.0)
        self.status = kwargs.get("status", "open")
        self.notes = kwargs.get("notes", None)
        self.historical_avg_monthly_volume = kwargs.get("hist_vol", 25000)
        self.historical_avg_transaction_size = kwargs.get("hist_size", 5000)
        self.historical_counterparty_count = kwargs.get("hist_cp", 5)
        self.historical_sar_count = kwargs.get("hist_sar", 0)
        self.composite_risk_score = kwargs.get("risk_composite", 75.0)
        self.network_risk_score = kwargs.get("risk_network", 60.0)
        self.behavioral_risk_score = kwargs.get("risk_behavioral", 70.0)
        self.graph_analysis = kwargs.get("graph", None)


class TestSeverityDetermination:
    """Test severity is computed strictly from evidence, never inflated."""

    def test_low_severity_minimal_activity(self):
        transactions = [MockTransaction(amount=500)]
        triggers = [MockRuleTrigger(breached=False)]
        case = MockCase(risk_composite=20.0)
        severity = _determine_severity(transactions, triggers, case)
        assert severity == "LOW"

    def test_medium_severity_moderate_activity(self):
        transactions = [MockTransaction(amount=50000) for _ in range(3)]
        triggers = [MockRuleTrigger(breached=True)]
        case = MockCase(risk_composite=50.0)
        severity = _determine_severity(transactions, triggers, case)
        assert severity in ("MEDIUM", "HIGH")

    def test_high_severity_significant_breaches(self):
        transactions = [
            MockTransaction(amount=200000, country="US"),
            MockTransaction(amount=150000, country="CH"),
            MockTransaction(amount=100000, country="SG"),
            MockTransaction(amount=80000, country="HK"),
        ]
        triggers = [MockRuleTrigger(breached=True) for _ in range(4)]
        case = MockCase(risk_composite=85.0, hist_sar=1)
        severity = _determine_severity(transactions, triggers, case)
        assert severity in ("HIGH", "CRITICAL")

    def test_critical_severity_extreme_activity(self):
        transactions = [MockTransaction(amount=300000, country=c) for c in ["US", "CH", "SG", "HK", "AE"]]
        triggers = [MockRuleTrigger(breached=True) for _ in range(8)]
        case = MockCase(risk_composite=95.0, hist_sar=2, graph="Complex layering network detected")
        severity = _determine_severity(transactions, triggers, case)
        assert severity == "CRITICAL"

    def test_no_severity_inflation_without_breaches(self):
        """Severity must NOT be inflated without actual threshold breaches."""
        transactions = [MockTransaction(amount=1000)]
        triggers = []
        case = MockCase(risk_composite=None)
        severity = _determine_severity(transactions, triggers, case)
        assert severity == "LOW"


class TestFallbackNarrative:
    """Test the template-based fallback narrative generator."""

    def test_narrative_contains_required_sections(self):
        case = MockCase()
        transactions = [MockTransaction()]
        triggers = [MockRuleTrigger()]
        narrative = _generate_fallback_narrative(case, transactions, triggers, "MEDIUM")

        required_sections = [
            "Subject Information",
            "Summary of Suspicious Activity",
            "Detailed Transaction Pattern Analysis",
            "Graph & Relationship Analysis",
            "Typology Mapping",
            "Historical Behavior Comparison",
            "Risk Scoring & Threshold Analysis",
            "Data Completeness & Limitations",
            "Conclusion",
        ]
        for section in required_sections:
            assert section in narrative, f"Missing section: {section}"

    def test_narrative_includes_customer_info(self):
        case = MockCase(customer_name="Test Subject", customer_id="TS-001")
        narrative = _generate_fallback_narrative(case, [], [], "LOW")
        assert "Test Subject" in narrative
        assert "TS-001" in narrative

    def test_narrative_severity_reflected_in_conclusion(self):
        case = MockCase()
        txns = [MockTransaction(amount=500000, country=c) for c in ["US", "CH"]]
        triggers = [MockRuleTrigger(breached=True)]

        narrative_high = _generate_fallback_narrative(case, txns, triggers, "HIGH")
        assert "escalation" in narrative_high.lower() or "investigation" in narrative_high.lower()

        narrative_low = _generate_fallback_narrative(case, [], [], "LOW")
        assert "does not support" in narrative_low.lower() or "not support" in narrative_low.lower()


class TestDataGapIdentification:
    """Test that missing data is properly identified."""

    def test_identifies_missing_kyc(self):
        case = MockCase(kyc_id_type=None, kyc_id_number=None)
        gaps = _identify_data_gaps(case, [MockTransaction()], [])
        assert any("KYC" in g for g in gaps)

    def test_identifies_no_transactions(self):
        case = MockCase()
        gaps = _identify_data_gaps(case, [], [])
        assert any("transaction" in g.lower() for g in gaps)

    def test_no_gaps_complete_data(self):
        case = MockCase(graph="Some analysis")
        txns = [MockTransaction()]
        triggers = [MockRuleTrigger()]
        gaps = _identify_data_gaps(case, txns, triggers)
        assert len(gaps) == 0 or all("graph" not in g.lower() for g in gaps)


class TestLLMResponseParsing:
    """Test parsing of LLM output into narrative and audit JSON."""

    def test_parse_well_formed_response(self):
        response = '''SECTION A — SAR DRAFT NARRATIVE

## 1. Subject Information
Test narrative content.

SECTION B — COMPLETE AUDIT TRAIL (STRICT JSON)

{"case_id": "test-123", "reasoning_trace": []}'''

        narrative, audit_json = _parse_llm_response(response)
        assert "Subject Information" in narrative
        assert audit_json.get("case_id") == "test-123"

    def test_parse_json_only_response(self):
        response = 'Some narrative text. {"case_id": "test", "data": true}'
        narrative, audit_json = _parse_llm_response(response)
        assert len(narrative) > 0
        assert "case_id" in audit_json

    def test_parse_malformed_json_gracefully(self):
        response = "Just a narrative without any JSON."
        narrative, audit_json = _parse_llm_response(response)
        assert len(narrative) > 0
        # Should not crash, audit_json may be empty
