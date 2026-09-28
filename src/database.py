"""
database.py — lightweight in-process store for EvidenceItem and Case objects.

Uses a plain Python dict keyed by ID.  No external database is required.
The store is initialised once per Python process; Streamlit re-runs keep the
same objects alive via st.session_state (see app.py).
"""
from __future__ import annotations

from typing import Optional

from models import Case, EvidenceItem


class EvidenceStore:
    """Thread-unsafe, in-memory store — sufficient for a single-user demo."""

    def __init__(self) -> None:
        self._items: dict[str, EvidenceItem] = {}
        self._cases: dict[str, Case] = {}

    # ── Evidence items ────────────────────────────────────────────────────────

    def add_item(self, item: EvidenceItem) -> EvidenceItem:
        self._items[item.id] = item
        # Also attach to its case if one exists
        if item.case_id and item.case_id in self._cases:
            case = self._cases[item.case_id]
            if item not in case.evidence_items:
                case.evidence_items.append(item)
        return item

    def get_item(self, item_id: str) -> Optional[EvidenceItem]:
        return self._items.get(item_id)

    def update_item(self, item: EvidenceItem) -> EvidenceItem:
        self._items[item.id] = item
        return item

    def delete_item(self, item_id: str) -> bool:
        item = self._items.pop(item_id, None)
        if item and item.case_id in self._cases:
            case = self._cases[item.case_id]
            case.evidence_items = [i for i in case.evidence_items if i.id != item_id]
        return item is not None

    def all_items(self) -> list[EvidenceItem]:
        return list(self._items.values())

    def items_for_case(self, case_id: str) -> list[EvidenceItem]:
        return [i for i in self._items.values() if i.case_id == case_id]

    # ── Cases ─────────────────────────────────────────────────────────────────

    def add_case(self, case: Case) -> Case:
        self._cases[case.id] = case
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        return self._cases.get(case_id)

    def all_cases(self) -> list[Case]:
        return list(self._cases.values())

    def delete_case(self, case_id: str) -> bool:
        return self._cases.pop(case_id, None) is not None

    # ── Bulk operations ───────────────────────────────────────────────────────

    def load_bulk(self, items: list[EvidenceItem], cases: list[Case]) -> None:
        """Replace current state with the provided items and cases."""
        self._cases = {c.id: c for c in cases}
        self._items = {}
        for item in items:
            self.add_item(item)

    def clear(self) -> None:
        self._items.clear()
        self._cases.clear()

    # ── Simple queries ────────────────────────────────────────────────────────

    def summary(self) -> dict:
        from constants import Priority, EvidenceStatus
        items = self.all_items()
        return {
            "total_items": len(items),
            "total_cases": len(self._cases),
            "by_priority": {
                p.value: sum(1 for i in items if i.priority == p)
                for p in Priority
            },
            "by_status": {
                s.value: sum(1 for i in items if i.status == s)
                for s in EvidenceStatus
            },
        }
