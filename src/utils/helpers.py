"""Shared utility functions for GeneTropica."""

import re
from datetime import datetime, timezone
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it doesn't exist.

    Args:
        path: Directory path to create.

    Returns:
        The same path, for chaining.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def timestamp() -> str:
    """Return current UTC timestamp as ISO 8601 string.

    Returns:
        Timestamp string like '2025-01-15T08:30:00Z'.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_filename(name: str) -> str:
    """Convert a string into a filesystem-safe filename.

    Replaces spaces with underscores, removes special characters,
    and lowercases the result.

    Args:
        name: Original string to sanitize.

    Returns:
        Sanitized filename string.
    """
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s-]+", "_", name)
    return name
