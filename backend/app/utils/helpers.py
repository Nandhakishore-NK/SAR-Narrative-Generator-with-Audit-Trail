"""
Utility Helpers — Common functions used across the application.
"""

import re
from typing import Optional


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent prompt injection.
    Strips control characters and common injection patterns.
    """
    if not text:
        return text

    # Remove null bytes and control characters (except newlines/tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Neutralize common prompt injection patterns
    injection_patterns = [
        r'(?i)ignore\s+(previous|above|all)\s+instructions',
        r'(?i)disregard\s+(previous|above|all)',
        r'(?i)you\s+are\s+now',
        r'(?i)new\s+instructions?:',
        r'(?i)system\s*prompt:',
        r'(?i)override\s+mode',
    ]
    for pattern in injection_patterns:
        text = re.sub(pattern, '[FILTERED]', text)

    return text.strip()


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to a maximum length with ellipsis."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_uuid_string(value: str) -> bool:
    """Check if a string is a valid UUID format."""
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))
