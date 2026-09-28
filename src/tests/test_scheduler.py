"""
tests/test_scheduler.py — unit tests for the lab scheduling engine.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from datetime import datetime, timedelta
import pytest

from scheduler import LabScheduler, _add_working_days, _next_working_day
from scoring import score_item
from constants import EvidenceCategory, EvidenceStatus, Priority, LabDepartment
from models import EvidenceItem


def _monday() -> datetime:
    """Return the most recent or upcoming Monday at 9:00."""
    today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    # Go to next Monday
    days_ahead = (7 - today.weekday()) % 7 or 7
    return today + timedelta(days=days_ahead)


def _make_item(category=EvidenceCategory.BIOLOGICAL, priority=Priority.HIGH, **kwargs) -> EvidenceItem:
    item = EvidenceItem(
        description="Test evidence item",
        category=category,
        status=EvidenceStatus.RECEIVED,
        priority=priority,
        urgency_score=65.0,
        case_id="CASE-TEST",
        received_at=datetime.now() - timedelta(days=3),
    )
    for k, v in kwargs.items():
        setattr(item, k, v)
    return item


class TestWorkingDayUtils:

    def test_add_zero_working_days(self):
        monday = _monday()
        result = _add_working_days(monday, 0)
        assert result == monday

    def test_add_5_working_days_skips_weekend(self):
        # Starting on a Monday, +5 working days = next Monday
        monday = _monday()
        result = _add_working_days(monday, 5)
        assert result.weekday() == 0  # Monday

    def test_next_working_day_on_saturday(self):
        saturday = _monday() + timedelta(days=5)
        assert saturday.weekday() == 5  # confirm it's a Saturday
        result = _next_working_day(saturday)
        assert result.weekday() == 0  # should be Monday

    def test_next_working_day_on_weekday_unchanged(self):
        monday = _monday()
        result = _next_working_day(monday)
        assert result == monday


class TestLabScheduler:

    def test_critical_item_scheduled_soonest(self):
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        item = _make_item(priority=Priority.CRITICAL, urgency_score=90)
        scheduler.schedule(item)
        assert item.scheduled_date is not None
        # Critical items get offset=0 — same day or very close
        assert (item.scheduled_date - ref).days <= 1

    def test_low_priority_scheduled_later_than_high(self):
        ref = _monday()
        high = _make_item(priority=Priority.HIGH, urgency_score=70)
        low = _make_item(priority=Priority.LOW, urgency_score=20)
        scheduler = LabScheduler(reference_date=ref)
        scheduler.schedule(high)
        scheduler.schedule(low)
        assert low.scheduled_date >= high.scheduled_date

    def test_department_assigned_from_category(self):
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        item = _make_item(category=EvidenceCategory.DIGITAL)
        scheduler.schedule(item)
        assert item.assigned_department == LabDepartment.DIGITAL_FORENSICS

    def test_biological_goes_to_dna(self):
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        item = _make_item(category=EvidenceCategory.BIOLOGICAL)
        scheduler.schedule(item)
        assert item.assigned_department == LabDepartment.DNA

    def test_video_goes_to_audio_video(self):
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        item = _make_item(category=EvidenceCategory.VIDEO)
        scheduler.schedule(item)
        assert item.assigned_department == LabDepartment.AUDIO_VIDEO

    def test_document_goes_to_document_examination(self):
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        item = _make_item(category=EvidenceCategory.DOCUMENT)
        scheduler.schedule(item)
        assert item.assigned_department == LabDepartment.DOCUMENT_EXAMINATION

    def test_estimated_completion_after_scheduled(self):
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        item = _make_item(category=EvidenceCategory.BIOLOGICAL)
        scheduler.schedule(item)
        assert item.estimated_completion > item.scheduled_date

    def test_scheduled_date_is_working_day(self):
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        item = _make_item()
        scheduler.schedule(item)
        assert item.scheduled_date.weekday() < 5  # Mon–Fri

    def test_no_category_item_skipped(self):
        """Items without a category should be returned without scheduling fields."""
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        item = EvidenceItem(description="Unknown item", priority=Priority.HIGH, urgency_score=70)
        scheduler.schedule(item)
        assert item.scheduled_date is None
        assert item.assigned_department is None

    def test_capacity_respected_across_batch(self):
        """Excess items for a department on a single day must overflow to next day."""
        from constants import LabDepartment
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        # DNA capacity is 4 — submit 5 critical items
        items = [
            _make_item(category=EvidenceCategory.BIOLOGICAL, priority=Priority.CRITICAL, urgency_score=90)
            for _ in range(5)
        ]
        scheduler.schedule_batch(items)
        dates = [i.scheduled_date for i in items if i.scheduled_date]
        assert len(dates) == 5
        # At least one item must have spilled to a different day
        unique_dates = set(d.date() for d in dates)
        assert len(unique_dates) >= 2

    def test_schedule_batch_returns_all_items(self):
        ref = _monday()
        scheduler = LabScheduler(reference_date=ref)
        items = [_make_item(category=c) for c in EvidenceCategory]
        result = scheduler.schedule_batch(items)
        assert len(result) == len(items)
