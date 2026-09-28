"""
models.py — core data structures for the forensic evidence system.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from constants import EvidenceCategory, EvidenceStatus, Priority, LabDepartment


@dataclass
class EvidenceItem:
    """Represents a single piece of forensic evidence."""

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    case_id: str = ""
    description: str = ""

    # Classification (populated by classifier)
    category: Optional[EvidenceCategory] = None
    category_confidence: float = 0.0          # 0.0–1.0
    category_source: str = "rule_based"       # "rule_based" | "watsonx"

    # Scoring (populated by scoring engine)
    urgency_score: float = 0.0                # 0–100
    priority: Optional[Priority] = None

    # Scheduling (populated by scheduler)
    assigned_department: Optional[LabDepartment] = None
    scheduled_date: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    # Lifecycle
    status: EvidenceStatus = EvidenceStatus.RECEIVED
    received_at: datetime = field(default_factory=datetime.now)
    notes: str = ""

    # Scoring breakdown (for transparency)
    score_breakdown: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "description": self.description,
            "category": self.category.value if self.category else None,
            "category_confidence": round(self.category_confidence, 2),
            "category_source": self.category_source,
            "urgency_score": round(self.urgency_score, 1),
            "priority": self.priority.value if self.priority else None,
            "assigned_department": self.assigned_department.value if self.assigned_department else None,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "status": self.status.value,
            "received_at": self.received_at.isoformat(),
            "notes": self.notes,
            "score_breakdown": self.score_breakdown,
        }


@dataclass
class Case:
    """Groups evidence items belonging to the same investigation."""

    id: str = field(default_factory=lambda: "CASE-" + str(uuid.uuid4())[:6].upper())
    title: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    evidence_items: list[EvidenceItem] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return len(self.evidence_items)

    @property
    def highest_priority(self) -> Optional[Priority]:
        priorities = [
            item.priority for item in self.evidence_items if item.priority
        ]
        if not priorities:
            return None
        order = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]
        for p in order:
            if p in priorities:
                return p
        return None
