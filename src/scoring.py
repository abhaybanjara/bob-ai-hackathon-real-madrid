"""
scoring.py — urgency scoring engine for forensic evidence items.

Score (0–100) is the weighted sum of five independent factors:
  1. Category base score           (accounts for typical analysis complexity)
  2. Age factor                    (older items score higher — degradation risk)
  3. Case link bonus               (evidence tied to an active case scores higher)
  4. Status factor                 (items awaiting analysis score higher)
  5. Keyword boost                 (description contains urgency signals)

The final score is clamped to [0, 100] and mapped to a Priority tier.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from constants import (
    EvidenceCategory,
    EvidenceStatus,
    Priority,
    PRIORITY_THRESHOLDS,
)
from models import EvidenceItem


# ── Weight configuration ──────────────────────────────────────────────────────

# Maximum contribution from each factor (must sum to 100)
_W_CATEGORY = 25
_W_AGE = 25
_W_CASE = 15
_W_STATUS = 20
_W_KEYWORDS = 15

# Category base scores (0–1 relative to _W_CATEGORY ceiling)
_CATEGORY_BASE: dict[EvidenceCategory, float] = {
    EvidenceCategory.BIOLOGICAL: 1.0,    # time-sensitive; degrades quickly
    EvidenceCategory.VIDEO: 0.9,         # storage may be limited / overwritten
    EvidenceCategory.DIGITAL: 0.85,      # volatile data
    EvidenceCategory.TRACE: 0.75,
    EvidenceCategory.IMPRESSION: 0.60,
    EvidenceCategory.DOCUMENT: 0.55,
}

# Status multipliers (0–1)
_STATUS_SCORE: dict[EvidenceStatus, float] = {
    EvidenceStatus.RECEIVED: 1.0,       # not yet started — highest urgency
    EvidenceStatus.ON_HOLD: 0.8,
    EvidenceStatus.PENDING_REVIEW: 0.5,
    EvidenceStatus.IN_ANALYSIS: 0.3,
    EvidenceStatus.COMPLETED: 0.0,
}

# Urgency keywords in description → additive bonus (capped at _W_KEYWORDS)
_URGENCY_PATTERNS: list[tuple[str, float]] = [
    (r"\burgent\b", 10),
    (r"\bcritical\b", 10),
    (r"\bpriority\b", 8),
    (r"\btime[\s-]?sensitive\b", 8),
    (r"\bfragile\b", 6),
    (r"\bperishable\b", 6),
    (r"\bcontaminated\b", 5),
    (r"\bdegrading\b", 5),
]


def _age_score(received_at: datetime, now: Optional[datetime] = None) -> float:
    """Return a 0–1 score based on how old the item is (cap at 30 days)."""
    now = now or datetime.now()
    age_days = max(0, (now - received_at).total_seconds() / 86400)
    return min(age_days / 30.0, 1.0)


def _keyword_bonus(description: str) -> float:
    """Return 0–1 keyword boost from urgency signals in the description."""
    text = description.lower()
    total = sum(bonus for pattern, bonus in _URGENCY_PATTERNS if re.search(pattern, text))
    return min(total / _W_KEYWORDS, 1.0)


def score_item(
    item: EvidenceItem,
    has_active_case: bool = True,
    now: Optional[datetime] = None,
) -> EvidenceItem:
    """
    Compute and assign urgency_score, priority, and score_breakdown to *item*.

    Returns the same item (mutated in-place) for chaining.
    """
    # 1. Category
    cat_base = _CATEGORY_BASE.get(item.category, 0.5) if item.category else 0.5
    s_category = cat_base * _W_CATEGORY

    # 2. Age
    s_age = _age_score(item.received_at, now) * _W_AGE

    # 3. Case link
    s_case = _W_CASE if has_active_case else 0.0

    # 4. Status
    status_mult = _STATUS_SCORE.get(item.status, 0.5)
    s_status = status_mult * _W_STATUS

    # 5. Keywords
    s_keywords = _keyword_bonus(item.description) * _W_KEYWORDS

    total = min(s_category + s_age + s_case + s_status + s_keywords, 100.0)

    item.urgency_score = round(total, 1)
    item.priority = _score_to_priority(total)
    item.score_breakdown = {
        "category": round(s_category, 1),
        "age": round(s_age, 1),
        "case_link": round(s_case, 1),
        "status": round(s_status, 1),
        "keywords": round(s_keywords, 1),
        "total": round(total, 1),
    }
    return item


def _score_to_priority(score: float) -> Priority:
    if score >= PRIORITY_THRESHOLDS[Priority.CRITICAL]:
        return Priority.CRITICAL
    if score >= PRIORITY_THRESHOLDS[Priority.HIGH]:
        return Priority.HIGH
    if score >= PRIORITY_THRESHOLDS[Priority.MEDIUM]:
        return Priority.MEDIUM
    return Priority.LOW


def score_batch(
    items: list[EvidenceItem],
    now: Optional[datetime] = None,
) -> list[EvidenceItem]:
    """Score a list of items. Returns sorted list (highest score first)."""
    scored = [score_item(item, has_active_case=bool(item.case_id), now=now) for item in items]
    return sorted(scored, key=lambda i: i.urgency_score, reverse=True)
