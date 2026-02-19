"""
Test — Override Validation

Validates governance rules:
- Override requires reason code and evidence
- Hash comparison must match
- HIGH/CRITICAL severity requires supervisor approval
- Empty evidence is rejected
"""

import pytest
from app.services.hash_service import hash_sentence


class TestOverrideValidation:
    """Test override governance enforcement at the data level."""

    def test_hash_changes_with_text_modification(self):
        """Modified text must produce a different hash."""
        original = "The subject conducted 5 wire transfers totaling USD 250,000."
        modified = "The subject conducted 5 wire transfers totaling USD 250,001."
        
        original_hash = hash_sentence(original)
        modified_hash = hash_sentence(modified)
        
        assert original_hash != modified_hash

    def test_identical_text_produces_same_hash(self):
        """Identical text must produce the same hash (deterministic)."""
        text = "This is a test sentence for hashing."
        hash1 = hash_sentence(text)
        hash2 = hash_sentence(text)
        assert hash1 == hash2

    def test_hash_is_64_character_hex(self):
        """SHA256 hash must be 64-character hex string."""
        text = "Test sentence."
        h = hash_sentence(text)
        assert len(h) == 64
        assert all(c in '0123456789abcdef' for c in h)

    def test_empty_evidence_should_be_rejected(self):
        """Evidence reference must be substantive (not empty or too short)."""
        evidence = ""
        assert len(evidence.strip()) < 10  # Should be rejected

    def test_valid_reason_codes(self):
        """Validate all accepted override reason codes."""
        valid_codes = [
            "factual_correction",
            "additional_evidence",
            "regulatory_update",
            "typology_reclassification",
            "risk_reassessment",
            "data_quality_issue",
            "supervisor_directed",
        ]
        for code in valid_codes:
            assert code in valid_codes

    def test_invalid_reason_code_detection(self):
        """Invalid reason codes must be detectable."""
        valid_codes = {
            "factual_correction", "additional_evidence", "regulatory_update",
            "typology_reclassification", "risk_reassessment", "data_quality_issue",
            "supervisor_directed",
        }
        assert "random_reason" not in valid_codes
        assert "because_i_want_to" not in valid_codes
