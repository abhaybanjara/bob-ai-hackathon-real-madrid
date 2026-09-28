"""
demo_data.py — seed data for the forensic evidence management demo.

All evidence items are fictional and use the specified evidence types:
  Hair strand, Fabric with possible biological material, Mobile phone,
  CCTV recording, Fingerprint on glass, Footwear impression,
  Handwritten note, Vehicle paint transfer.

No weapon-related items are included.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from models import Case, EvidenceItem
from constants import EvidenceStatus


def _days_ago(n: int) -> datetime:
    return datetime.now() - timedelta(days=n)


# ── Demo cases ────────────────────────────────────────────────────────────────

DEMO_CASES: list[Case] = [
    Case(
        id="CASE-A1B2C3",
        title="Residential Burglary – Oak Street",
        description="Break-in at a residential property; suspect entered through rear window.",
        created_at=_days_ago(10),
    ),
    Case(
        id="CASE-D4E5F6",
        title="Hit-and-Run Incident – Central Avenue",
        description="Vehicle struck a pedestrian and fled the scene.",
        created_at=_days_ago(5),
    ),
    Case(
        id="CASE-G7H8I9",
        title="Office Fraud Investigation – Meridian Corp",
        description="Suspected document forgery and financial fraud at a corporate office.",
        created_at=_days_ago(20),
    ),
]


# ── Demo evidence items ───────────────────────────────────────────────────────

DEMO_ITEMS: list[EvidenceItem] = [
    # ── Case A: Residential Burglary ──────────────────────────────────────────
    EvidenceItem(
        id="EV-0001",
        case_id="CASE-A1B2C3",
        description=(
            "Hair strand recovered from the point of entry. "
            "Possible biological material present. Urgent — degrades quickly."
        ),
        status=EvidenceStatus.RECEIVED,
        received_at=_days_ago(9),
    ),
    EvidenceItem(
        id="EV-0002",
        case_id="CASE-A1B2C3",
        description=(
            "Fabric swatch with possible biological material, found snagged "
            "on broken window frame."
        ),
        status=EvidenceStatus.RECEIVED,
        received_at=_days_ago(9),
    ),
    EvidenceItem(
        id="EV-0003",
        case_id="CASE-A1B2C3",
        description=(
            "Fingerprint on glass — latent print lifted from interior door handle."
        ),
        status=EvidenceStatus.IN_ANALYSIS,
        received_at=_days_ago(8),
    ),
    EvidenceItem(
        id="EV-0004",
        case_id="CASE-A1B2C3",
        description=(
            "Footwear impression in soft soil near rear garden gate. "
            "Cast taken at scene."
        ),
        status=EvidenceStatus.RECEIVED,
        received_at=_days_ago(8),
    ),
    EvidenceItem(
        id="EV-0005",
        case_id="CASE-A1B2C3",
        description=(
            "Mobile phone found inside the property; may belong to suspect. "
            "Device is locked — digital forensics required."
        ),
        status=EvidenceStatus.PENDING_REVIEW,
        received_at=_days_ago(7),
    ),
    # ── Case B: Hit-and-Run ───────────────────────────────────────────────────
    EvidenceItem(
        id="EV-0006",
        case_id="CASE-D4E5F6",
        description=(
            "CCTV recording from a nearby shop covering the incident location. "
            "Critical — footage retention period expires in 48 hours."
        ),
        status=EvidenceStatus.RECEIVED,
        received_at=_days_ago(4),
    ),
    EvidenceItem(
        id="EV-0007",
        case_id="CASE-D4E5F6",
        description=(
            "Vehicle paint transfer on barrier at scene. "
            "Trace evidence collected — paint flakes in evidence bag."
        ),
        status=EvidenceStatus.RECEIVED,
        received_at=_days_ago(4),
    ),
    EvidenceItem(
        id="EV-0008",
        case_id="CASE-D4E5F6",
        description=(
            "Hair strand retrieved from the vehicle bonnet. "
            "DNA analysis required urgently."
        ),
        status=EvidenceStatus.RECEIVED,
        received_at=_days_ago(3),
    ),
    # ── Case C: Office Fraud ──────────────────────────────────────────────────
    EvidenceItem(
        id="EV-0009",
        case_id="CASE-G7H8I9",
        description=(
            "Handwritten note recovered from shredder bin; "
            "partially reconstructed. Document examination needed."
        ),
        status=EvidenceStatus.ON_HOLD,
        received_at=_days_ago(18),
    ),
    EvidenceItem(
        id="EV-0010",
        case_id="CASE-G7H8I9",
        description=(
            "Mobile phone belonging to primary suspect; "
            "may contain deleted communications. Digital forensics required."
        ),
        status=EvidenceStatus.RECEIVED,
        received_at=_days_ago(15),
    ),
]


def get_demo_cases() -> list[Case]:
    return list(DEMO_CASES)


def get_demo_items() -> list[EvidenceItem]:
    return list(DEMO_ITEMS)
