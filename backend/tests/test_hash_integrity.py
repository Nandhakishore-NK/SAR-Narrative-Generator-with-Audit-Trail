"""
Test — Hash Integrity

Validates:
- SHA256 sentence hashing
- Hash chain generation for immutable logs
- Hash chain verification
- Tamper detection
"""

import pytest
from datetime import datetime, timezone

from app.services.hash_service import (
    hash_sentence,
    hash_log_entry,
    verify_hash_chain,
    hash_audit_json,
)


class MockLogEntry:
    def __init__(self, entity_type, entity_id, action, timestamp, previous_hash, hash_signature):
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.action = action
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.hash_signature = hash_signature


class TestSentenceHashing:
    """Test SHA256 hashing of narrative sentences."""

    def test_deterministic_hashing(self):
        """Same input must always produce same hash."""
        text = "The subject transferred funds to 3 jurisdictions."
        assert hash_sentence(text) == hash_sentence(text)

    def test_different_text_different_hash(self):
        """Different text must produce different hashes."""
        h1 = hash_sentence("Original sentence.")
        h2 = hash_sentence("Modified sentence.")
        assert h1 != h2

    def test_whitespace_sensitivity(self):
        """Hashing must be whitespace-sensitive (exact match required)."""
        h1 = hash_sentence("Test sentence.")
        h2 = hash_sentence("Test  sentence.")
        assert h1 != h2

    def test_hash_format(self):
        """Hash must be 64-char lowercase hex (SHA256)."""
        h = hash_sentence("anything")
        assert len(h) == 64
        assert h == h.lower()
        assert all(c in '0123456789abcdef' for c in h)


class TestHashChain:
    """Test immutable log hash chain generation and verification."""

    def test_genesis_entry_has_no_previous(self):
        """First entry in chain uses 'GENESIS' as previous hash."""
        h = hash_log_entry("case", "case-1", "created", "2026-01-01T00:00:00", None)
        assert len(h) == 64

    def test_chain_linkage(self):
        """Each entry's hash incorporates the previous hash."""
        ts1 = "2026-01-01T00:00:00"
        ts2 = "2026-01-01T00:01:00"

        h1 = hash_log_entry("case", "case-1", "created", ts1, None)
        h2_with_chain = hash_log_entry("case", "case-1", "updated", ts2, h1)
        h2_without_chain = hash_log_entry("case", "case-1", "updated", ts2, None)

        # Chained hash must differ from unchained
        assert h2_with_chain != h2_without_chain

    def test_chain_verification_valid(self):
        """Valid chain must pass verification."""
        ts1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)

        h1 = hash_log_entry("case", "c1", "created", ts1.isoformat(), None)
        h2 = hash_log_entry("case", "c1", "updated", ts2.isoformat(), h1)

        entries = [
            MockLogEntry("case", "c1", "created", ts1, None, h1),
            MockLogEntry("case", "c1", "updated", ts2, h1, h2),
        ]
        assert verify_hash_chain(entries) is True

    def test_chain_verification_tampered(self):
        """Tampered chain must fail verification."""
        ts1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc)

        h1 = hash_log_entry("case", "c1", "created", ts1.isoformat(), None)
        h2 = hash_log_entry("case", "c1", "updated", ts2.isoformat(), h1)

        # Tamper with second entry's hash
        entries = [
            MockLogEntry("case", "c1", "created", ts1, None, h1),
            MockLogEntry("case", "c1", "updated", ts2, h1, "tampered_hash_value_here_1234567890abcdef1234567890abcdef"),
        ]
        assert verify_hash_chain(entries) is False

    def test_empty_chain_is_valid(self):
        """Empty chain must pass verification."""
        assert verify_hash_chain([]) is True


class TestAuditJsonHashing:
    """Test deterministic hashing of audit JSON objects."""

    def test_deterministic_json_hash(self):
        """Same JSON content must produce same hash regardless of key order."""
        json1 = {"b": 2, "a": 1}
        json2 = {"a": 1, "b": 2}
        assert hash_audit_json(json1) == hash_audit_json(json2)

    def test_different_content_different_hash(self):
        """Different JSON content must produce different hashes."""
        h1 = hash_audit_json({"case_id": "1"})
        h2 = hash_audit_json({"case_id": "2"})
        assert h1 != h2
