"""
classifier.py — forensic evidence category classifier.

Primary path: rule-based keyword matching (fully offline, no credentials needed).
Optional enhancement: IBM watsonx.ai Granite model for free-text descriptions.
"""
from __future__ import annotations

import re
from typing import Optional

from constants import EvidenceCategory
from models import EvidenceItem


# ── Keyword rules (category → list of regex patterns) ────────────────────────

_RULES: list[tuple[EvidenceCategory, list[str]]] = [
    (
        EvidenceCategory.BIOLOGICAL,
        [
            r"\bhair\b", r"\bstrand\b", r"\bblood\b", r"\bsaliva\b",
            r"\bswab\b", r"\btissue\b", r"\bdna\b", r"\bskin\b",
            r"\bbiological\b", r"\bfluids?\b", r"\bsemen\b",
        ],
    ),
    (
        EvidenceCategory.DIGITAL,
        [
            r"\bphone\b", r"\bmobile\b", r"\bsmartphone\b", r"\blaptop\b",
            r"\bcomputer\b", r"\busb\b", r"\bhard\s*drive\b", r"\bsd\s*card\b",
            r"\btablet\b", r"\bstorage\b", r"\bdevice\b",
        ],
    ),
    (
        EvidenceCategory.VIDEO,
        [
            r"\bcctv\b", r"\bvideo\b", r"\bfootage\b", r"\brecording\b",
            r"\bdashcam\b", r"\bcamera\b", r"\bclip\b",
        ],
    ),
    (
        EvidenceCategory.DOCUMENT,
        [
            r"\bnote\b", r"\bletter\b", r"\bdocument\b", r"\bhandwritten\b",
            r"\bwritten\b", r"\bpaper\b", r"\bprint\b", r"\breceipt\b",
            r"\bcheque\b", r"\bcontract\b",
        ],
    ),
    (
        EvidenceCategory.IMPRESSION,
        [
            r"\bfootprint\b", r"\bfootwear\b", r"\bshoe\s*(print|mark|impression)\b",
            r"\btyre\b", r"\btire\b", r"\bimpression\b", r"\bcast\b",
            r"\bstamp\b",
        ],
    ),
    (
        EvidenceCategory.TRACE,
        [
            r"\bfibre\b", r"\bfiber\b", r"\bfabric\b", r"\bpaint\b",
            r"\btransfer\b", r"\bglass\b", r"\bfingerprint\b", r"\blatent\b",
            r"\bparticle\b", r"\bdust\b", r"\bsoil\b", r"\btrace\b",
        ],
    ),
]


def _classify_rule_based(description: str) -> tuple[Optional[EvidenceCategory], float]:
    """
    Return (category, confidence) using keyword matching.

    Confidence is proportional to the fraction of a category's patterns that
    matched, scaled so that even a single strong match returns >= 0.6.
    """
    text = description.lower()
    best_category: Optional[EvidenceCategory] = None
    best_score = 0.0

    for category, patterns in _RULES:
        hits = sum(1 for p in patterns if re.search(p, text))
        if hits == 0:
            continue
        # Normalise: 1 hit → 0.6; all hits → 1.0
        score = 0.6 + 0.4 * (hits / len(patterns))
        if score > best_score:
            best_score = score
            best_category = category

    return best_category, round(best_score, 2)


class EvidenceClassifier:
    """
    Classify a single EvidenceItem in-place.

    Parameters
    ----------
    watsonx_client : optional WatsonxClient instance.
        When provided and USE_WATSONX=true the model supplements rule-based
        classification for ambiguous descriptions.
    """

    def __init__(self, watsonx_client=None):
        self._wx = watsonx_client

    def classify(self, item: EvidenceItem) -> EvidenceItem:
        """Assign category, confidence and source to *item* and return it."""
        category, confidence = _classify_rule_based(item.description)

        # Attempt watsonx enhancement only when confidence is low and client is available
        if self._wx is not None and confidence < 0.75:
            try:
                wx_category, wx_confidence = self._wx.classify(item.description)
                if wx_category is not None and wx_confidence > confidence:
                    item.category = wx_category
                    item.category_confidence = wx_confidence
                    item.category_source = "watsonx"
                    return item
            except Exception:
                pass  # Fall back to rule-based result silently

        item.category = category
        item.category_confidence = confidence
        item.category_source = "rule_based"
        return item

    def classify_batch(self, items: list[EvidenceItem]) -> list[EvidenceItem]:
        return [self.classify(item) for item in items]
