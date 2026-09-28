"""
scheduler.py — lab scheduling logic for forensic evidence items.

Rules
-----
* Each item is routed to the department determined by its category.
* Critical/High-priority items are scheduled for the next available slot
  starting from today (or tomorrow if today's capacity is already full).
* Medium items are scheduled within 3 working days.
* Low items are scheduled within 7 working days.
* Estimated completion = scheduled_date + PROCESSING_DAYS for the category.
* Weekends (Saturday/Sunday) are skipped when calculating working days.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from constants import (
    CATEGORY_TO_DEPARTMENT,
    PROCESSING_DAYS,
    EvidenceCategory,
    LabDepartment,
    Priority,
)
from models import EvidenceItem


# Max items scheduled per department per day (simplified capacity model)
_DAILY_CAPACITY: dict[LabDepartment, int] = {
    LabDepartment.DNA: 4,
    LabDepartment.DIGITAL_FORENSICS: 6,
    LabDepartment.DOCUMENT_EXAMINATION: 5,
    LabDepartment.TRACE_EVIDENCE: 5,
    LabDepartment.IMPRESSION_EVIDENCE: 4,
    LabDepartment.AUDIO_VIDEO: 4,
}

# Working-day offset by priority tier
_PRIORITY_OFFSET: dict[Priority, int] = {
    Priority.CRITICAL: 0,   # schedule as soon as possible
    Priority.HIGH: 1,
    Priority.MEDIUM: 3,
    Priority.LOW: 7,
}


def _add_working_days(start: datetime, days: int) -> datetime:
    """Return *start* + *days* working days (skipping Sat/Sun)."""
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:   # Mon–Fri
            added += 1
    return current


def _next_working_day(from_date: datetime) -> datetime:
    """Return *from_date* if it is a working day, else the next working day."""
    result = from_date
    while result.weekday() >= 5:
        result += timedelta(days=1)
    return result


class LabScheduler:
    """
    Assigns scheduled_date, estimated_completion, and assigned_department
    to each EvidenceItem.

    Parameters
    ----------
    reference_date : datetime, optional
        Used as "today" — defaults to datetime.now() at construction time.
    """

    def __init__(self, reference_date: Optional[datetime] = None):
        self._today = _next_working_day(reference_date or datetime.now())
        # Track per-department, per-day booking counts
        self._bookings: dict[LabDepartment, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def schedule(self, item: EvidenceItem) -> EvidenceItem:
        """Assign scheduling fields to *item* and return it."""
        if item.category is None:
            # Cannot schedule without a category; leave unscheduled
            return item

        department = CATEGORY_TO_DEPARTMENT.get(item.category)
        if department is None:
            return item

        priority = item.priority or Priority.LOW
        offset = _PRIORITY_OFFSET[priority]

        # Find earliest available slot on or after (today + offset working days)
        earliest = _add_working_days(self._today, offset) if offset > 0 else self._today
        earliest = _next_working_day(earliest)
        scheduled = self._find_slot(department, earliest)

        processing = PROCESSING_DAYS.get(item.category, 3)
        completion = _add_working_days(scheduled, processing)

        item.assigned_department = department
        item.scheduled_date = scheduled
        item.estimated_completion = completion

        # Reserve the slot
        day_key = scheduled.strftime("%Y-%m-%d")
        self._bookings[department][day_key] += 1

        return item

    def _find_slot(self, department: LabDepartment, earliest: datetime) -> datetime:
        """Return the first available working-day slot for *department*."""
        capacity = _DAILY_CAPACITY.get(department, 4)
        current = earliest
        for _ in range(60):     # safety limit: search up to 60 working days ahead
            day_key = current.strftime("%Y-%m-%d")
            if self._bookings[department][day_key] < capacity:
                return current
            current = _add_working_days(current, 1)
        return current          # fallback (should never be reached in practice)

    def schedule_batch(self, items: list[EvidenceItem]) -> list[EvidenceItem]:
        """
        Schedule a list of items.

        Items are sorted by urgency score (descending) so that the highest-
        priority items claim the earliest slots first.
        """
        sorted_items = sorted(items, key=lambda i: i.urgency_score, reverse=True)
        return [self.schedule(item) for item in sorted_items]
