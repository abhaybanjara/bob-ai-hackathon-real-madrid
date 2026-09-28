"""
constants.py — shared enumerations and configuration values.

No weapon-related categories are defined here.
"""
from __future__ import annotations

from enum import Enum


# ── Evidence categories ───────────────────────────────────────────────────────

class EvidenceCategory(str, Enum):
    """Broad forensic category assigned to each evidence item."""
    BIOLOGICAL = "Biological"          # hair, blood, saliva, tissue …
    DIGITAL = "Digital"                # phones, computers, storage media …
    DOCUMENT = "Document"              # paper, handwriting, printed material …
    TRACE = "Trace"                    # fibres, paint transfer, glass …
    IMPRESSION = "Impression"          # footwear, tyre marks …
    VIDEO = "Video"                    # CCTV footage, dashcam recordings …


# ── Evidence status ───────────────────────────────────────────────────────────

class EvidenceStatus(str, Enum):
    RECEIVED = "Received"
    IN_ANALYSIS = "In Analysis"
    PENDING_REVIEW = "Pending Review"
    COMPLETED = "Completed"
    ON_HOLD = "On Hold"


# ── Priority tiers ────────────────────────────────────────────────────────────

class Priority(str, Enum):
    CRITICAL = "Critical"   # score >= 80
    HIGH = "High"           # score 60–79
    MEDIUM = "Medium"       # score 40–59
    LOW = "Low"             # score < 40


# ── Lab departments ───────────────────────────────────────────────────────────

class LabDepartment(str, Enum):
    DNA = "DNA & Serology"
    DIGITAL_FORENSICS = "Digital Forensics"
    DOCUMENT_EXAMINATION = "Document Examination"
    TRACE_EVIDENCE = "Trace Evidence"
    IMPRESSION_EVIDENCE = "Impression Evidence"
    AUDIO_VIDEO = "Audio/Video Analysis"


# Mapping: category → lab department
CATEGORY_TO_DEPARTMENT: dict[EvidenceCategory, LabDepartment] = {
    EvidenceCategory.BIOLOGICAL: LabDepartment.DNA,
    EvidenceCategory.DIGITAL: LabDepartment.DIGITAL_FORENSICS,
    EvidenceCategory.DOCUMENT: LabDepartment.DOCUMENT_EXAMINATION,
    EvidenceCategory.TRACE: LabDepartment.TRACE_EVIDENCE,
    EvidenceCategory.IMPRESSION: LabDepartment.IMPRESSION_EVIDENCE,
    EvidenceCategory.VIDEO: LabDepartment.AUDIO_VIDEO,
}

# Estimated processing time (working days) per category
PROCESSING_DAYS: dict[EvidenceCategory, int] = {
    EvidenceCategory.BIOLOGICAL: 5,
    EvidenceCategory.DIGITAL: 3,
    EvidenceCategory.DOCUMENT: 4,
    EvidenceCategory.TRACE: 3,
    EvidenceCategory.IMPRESSION: 2,
    EvidenceCategory.VIDEO: 2,
}

# Score thresholds for priority assignment
PRIORITY_THRESHOLDS = {
    Priority.CRITICAL: 80,
    Priority.HIGH: 60,
    Priority.MEDIUM: 40,
    Priority.LOW: 0,
}
