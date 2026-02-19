"""
Hash Service — SHA256 hashing for narrative sentences and immutable log chain.

Compliance function:
- Every narrative sentence is hashed for tamper detection
- Immutable log entries form a hash chain (each entry references previous hash)
- Override validation compares original vs modified hashes
"""

import hashlib
import json
from typing import Optional


def hash_sentence(text: str) -> str:
    """
    Generate SHA256 hash of a narrative sentence.
    Used for tamper detection and override validation.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_log_entry(
    entity_type: str,
    entity_id: str,
    action: str,
    timestamp: str,
    previous_hash: Optional[str] = None,
) -> str:
    """
    Generate SHA256 hash for an immutable log entry.
    Creates hash chain by incorporating the previous entry's hash.
    
    Chain formula: SHA256(previous_hash + entity_type + entity_id + action + timestamp)
    """
    payload = f"{previous_hash or 'GENESIS'}{entity_type}{entity_id}{action}{timestamp}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_hash_chain(entries: list) -> bool:
    """
    Verify integrity of the immutable log hash chain.
    Returns True if chain is valid, False if tampering detected.
    """
    for i, entry in enumerate(entries):
        expected_hash = hash_log_entry(
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            action=entry.action,
            timestamp=entry.timestamp.isoformat(),
            previous_hash=entry.previous_hash,
        )
        if expected_hash != entry.hash_signature:
            return False
        # Verify chain linkage (skip first entry which has no previous)
        if i > 0 and entry.previous_hash != entries[i - 1].hash_signature:
            return False
    return True


def hash_audit_json(audit_data: dict) -> str:
    """
    Generate deterministic hash of the full audit JSON.
    Ensures audit trail integrity.
    """
    canonical = json.dumps(audit_data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
