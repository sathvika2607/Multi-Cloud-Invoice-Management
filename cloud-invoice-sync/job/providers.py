"""
Provider definitions: which sender domains / subject keywords identify an
invoice email from each cloud provider, and the regex patterns used to pull
the billing period and total amount out of the PDF text.

To add a new provider, add a Provider(...) entry to PROVIDERS below.
See the README ("Adding a New Cloud Provider") for a step-by-step guide.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Provider:
    name: str
    sender_domains: List[str]
    subject_keywords: List[str]
    period_patterns: List[str]
    amount_patterns: List[str] = field(default_factory=list)


PROVIDERS: List[Provider] = [
    Provider(
        name="GCP",
        sender_domains=["google.com", "cloud.google.com"],
        subject_keywords=["invoice", "billing"],
        period_patterns=[
            r"billing period[:\s]+(\w+ \d{1,2}),?\s+(\d{4})\s*[-\u2013\u2014]\s*(\w+ \d{1,2}),?\s+(\d{4})",
            r"(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\s+(\d{4})",
        ],
        amount_patterns=[
            r"(?:total due|amount due|total)[:\s]+\$?([\d,]+\.\d{2})",
        ],
    ),
    Provider(
        name="AWS",
        sender_domains=["amazonaws.com", "aws.amazon.com"],
        subject_keywords=["invoice", "billing statement", "your aws"],
        period_patterns=[
            r"billing period[:\s]+(\w+ \d{1,2}),?\s+(\d{4})",
            r"(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\s+(\d{4})",
        ],
        amount_patterns=[
            r"(?:total amount due|amount due)[:\s]+\$?([\d,]+\.\d{2})",
        ],
    ),
    Provider(
        name="Azure",
        sender_domains=["microsoft.com", "azure.com"],
        subject_keywords=["invoice", "billing"],
        period_patterns=[
            r"billing period[:\s]+(\w+ \d{1,2}),?\s+(\d{4})",
            r"(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\s+(\d{4})",
        ],
        amount_patterns=[
            r"(?:total due|amount due)[:\s]+\$?([\d,]+\.\d{2})",
        ],
    ),
    Provider(
        name="OCI",
        sender_domains=["oracle.com", "oraclecloud.com"],
        subject_keywords=["invoice", "billing"],
        period_patterns=[
            r"billing period[:\s]+(\w+ \d{1,2}),?\s+(\d{4})",
            r"(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\s+(\d{4})",
        ],
        amount_patterns=[
            r"(?:total due|amount due)[:\s]+\$?([\d,]+\.\d{2})",
        ],
    ),
]


def match_provider(sender: str, subject: str) -> Optional[Provider]:
    """Return the first Provider whose sender domain AND subject keyword both
    match, or None if nothing matches."""
    sender_l = (sender or "").lower()
    subject_l = (subject or "").lower()

    for provider in PROVIDERS:
        domain_match = any(d.lower() in sender_l for d in provider.sender_domains)
        keyword_match = any(k.lower() in subject_l for k in provider.subject_keywords)
        if domain_match and keyword_match:
            return provider

    return None
