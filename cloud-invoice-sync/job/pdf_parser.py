"""
PDF text extraction and regex-based parsing of billing period / invoice
total, using pdfplumber.
"""
import io
import re
import logging
from datetime import date
from typing import List, Optional, Tuple

import pdfplumber

logger = logging.getLogger(__name__)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def extract_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF's pages, concatenated with newlines."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def parse_billing_period(text: str, period_patterns: List[str]) -> Tuple[int, int]:
    """
    Try each pattern in order against the PDF text and return the first
    (year, month) match found. Returns (0, 0) if nothing matches -- callers
    should fall back to fallback_period() in that case.
    """
    text_l = text.lower()

    for pattern in period_patterns:
        match = re.search(pattern, text_l, re.IGNORECASE)
        if not match:
            continue

        groups = match.groups()
        month_name = next((g.lower() for g in groups if g and g.lower() in MONTHS), None)
        year_str = next((g for g in groups if g and g.isdigit() and len(g) == 4), None)

        if month_name and year_str:
            return int(year_str), MONTHS[month_name]

    return 0, 0


def parse_amount(text: str, amount_patterns: List[str]) -> Optional[str]:
    """Return the first matched invoice total, or None if no pattern matched."""
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def fallback_period() -> Tuple[int, int]:
    """
    Used when the billing period can't be parsed from the PDF text.
    Defaults to the previous calendar month so the invoice still gets
    uploaded (with a best-guess filename) instead of being dropped.
    """
    today = date.today()
    month = today.month - 1
    year = today.year
    if month == 0:
        month = 12
        year -= 1
    return year, month
