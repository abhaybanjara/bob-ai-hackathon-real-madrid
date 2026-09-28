"""
tests/test_scoring.py — unit tests for the urgency scoring engine.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from datetime import datetime, timedelta
import pytest

from scoring import score_item, score_batch, _age_score, _score_to_priority
from constants import EvidenceCategory, EvidenceStatus, Priority
from models import EvidenceItem


def _make_item(**kwargs) -> EvidenceItem:
    defaults = dict(
        description="Test item",
        category=EvidenceCategory.BIOLOGICAL,
        status=EvidenceStatus.RECEIVED,
        received_at=datetime.now() - timedelta(days=5),
        case_id="CASE-TEST",
    )
    defaults.update(kwargs)
    return EvidenceItem(**defaults)


class TestAgeScore:

    def test_brand_new_item_scores_zero(self):
        score = _age_score(datetime.now())
        assert score == pytest.approx(0.0, abs=0.02)

    def test_30_day_old_item_scores_one(self):
        score = _age_score(datetime.now() - timedelta(days=30))
        assert score == pytest.approx(1.0, abs=0.01)

    def test_15_day_item_scores_half(self):
        score = _age_score(datetime.now() - timedelta(days=15))
        assert score == pytest.approx(0.5, abs=0.05)

    def test_older_than_30_days_capped_at_one(self):
        score = _age_score(datetime.now() - timedelta(days=90))
        assert score == 1.0


class TestScoreToPrority:

    def test_critical_threshold(self):
        assert _score_to_priority(80) == Priority.CRITICAL
        assert _score_to_priority(100) == Priority.CRITICAL

    def test_high_threshold(self):
        assert _score_to_priority(60) == Priority.HIGH
        assert _score_to_priority(79) == Priority.HIGH

    def test_medium_threshold(self):
        assert _score_to_priority(40) == Priority.MEDIUM
        assert _score_to_priority(59) == Priority.MEDIUM

    def test_low_threshold(self):
        assert _score_to_priority(0) == Priority.LOW
        assert _score_to_priority(39) == Priority.LOW


class TestScoreItem:

    def test_score_in_range(self):
        item = _make_item()
        score_item(item)
        assert 0.0 <= item.urgency_score <= 100.0

    def test_priority_assigned(self):
        item = _make_item()
        score_item(item)
        assert item.priority in list(Priority)

    def test_score_breakdown_populated(self):
        item = _make_item()
        score_item(item)
        assert "category" in item.score_breakdown
        assert "age" in item.score_breakdown
        assert "total" in item.score_breakdown

    def test_biological_scores_higher_than_document(self):
        """Biological evidence should outscore document evidence (degrades faster)."""
        now = datetime.now() - timedelta(days=5)
        bio = _make_item(category=EvidenceCategory.BIOLOGICAL, received_at=now)
        doc = _make_item(category=EvidenceCategory.DOCUMENT, received_at=now)
        score_item(bio)
        score_item(doc)
        assert bio.urgency_score > doc.urgency_score

    def test_received_scores_higher_than_completed(self):
        """Items waiting for analysis should score higher than completed ones."""
        received = _make_item(status=EvidenceStatus.RECEIVED)
        completed = _make_item(status=EvidenceStatus.COMPLETED)
        score_item(received)
        score_item(completed)
        assert received.urgency_score > completed.urgency_score

    def test_urgent_keyword_boosts_score(self):
        base = _make_item(description="Evidence item")
        urgent = _make_item(description="Urgent evidence item — time-sensitive")
        score_item(base)
        score_item(urgent)
        assert urgent.urgency_score > base.urgency_score

    def test_no_case_link_reduces_score(self):
        with_case = _make_item(case_id="CASE-001")
        without_case = _make_item(case_id="")
        score_item(with_case, has_active_case=True)
        score_item(without_case, has_active_case=False)
        assert with_case.urgency_score > without_case.urgency_score

    def test_score_batch_sorted_desc(self):
        items = [
            _make_item(description="Low priority item", category=EvidenceCategory.DOCUMENT, status=EvidenceStatus.COMPLETED),
            _make_item(description="Urgent biological material", category=EvidenceCategory.BIOLOGICAL, status=EvidenceStatus.RECEIVED),
            _make_item(description="Digital device", category=EvidenceCategory.DIGITAL, status=EvidenceStatus.ON_HOLD),
        ]
        result = score_batch(items)
        scores = [i.urgency_score for i in result]
        assert scores == sorted(scores, reverse=True)

    def test_cctv_item_scores_high(self):
        """Video evidence is time-sensitive and should receive a high base score."""
        item = _make_item(
            description="Critical CCTV recording — footage expires soon",
            category=EvidenceCategory.VIDEO,
            status=EvidenceStatus.RECEIVED,
            received_at=datetime.now() - timedelta(days=4),
        )
        score_item(item)
        assert item.urgency_score >= 60
