"""Shared normalization utilities used across repository implementations."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_text(value: Any) -> str:
    """Normalizes text by removing accents, trimming, and upper-casing."""
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.upper()


def normalize_document(value: Any) -> str:
    """Normalizes CPF/CNPJ by keeping only digits."""
    if value is None:
        return ""
    return "".join(char for char in str(value) if char.isdigit())


def normalize_customer_name(value: Any) -> str:
    """Normalizes customer names for deterministic matching."""
    raw = normalize_text(value)
    raw = re.sub(r"\s+", " ", raw)
    return raw


def normalize_invoice_status(value: Any) -> str:
    """Normalizes fiscal status values for robust filtering."""
    return normalize_text(value)
