"""
tests/test_classifier.py — unit tests for the rule-based classifier.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from classifier import EvidenceClassifier, _classify_rule_based
from constants import EvidenceCategory
from models import EvidenceItem


class TestRuleBasedClassifier:

    def test_hair_strand_is_biological(self):
        cat, conf = _classify_rule_based("Hair strand recovered from scene")
        assert cat == EvidenceCategory.BIOLOGICAL
        assert conf >= 0.6

    def test_fabric_biological_material(self):
        cat, conf = _classify_rule_based("Fabric with possible biological material found at entry point")
        # fabric → TRACE, but 'biological' keyword should also match BIOLOGICAL
        # whichever wins — must be one of the two, not None
        assert cat in (EvidenceCategory.BIOLOGICAL, EvidenceCategory.TRACE)
        assert conf >= 0.6

    def test_mobile_phone_is_digital(self):
        cat, conf = _classify_rule_based("Mobile phone found inside the property")
        assert cat == EvidenceCategory.DIGITAL
        assert conf >= 0.6

    def test_cctv_recording_is_video(self):
        cat, conf = _classify_rule_based("CCTV recording from nearby shop")
        assert cat == EvidenceCategory.VIDEO
        assert conf >= 0.6

    def test_fingerprint_on_glass_is_trace(self):
        cat, conf = _classify_rule_based("Fingerprint on glass — latent print from door handle")
        assert cat == EvidenceCategory.TRACE
        assert conf >= 0.6

    def test_footwear_impression_is_impression(self):
        cat, conf = _classify_rule_based("Footwear impression in soft soil")
        assert cat == EvidenceCategory.IMPRESSION
        assert conf >= 0.6

    def test_handwritten_note_is_document(self):
        cat, conf = _classify_rule_based("Handwritten note recovered from shredder bin")
        assert cat == EvidenceCategory.DOCUMENT
        assert conf >= 0.6

    def test_paint_transfer_is_trace(self):
        cat, conf = _classify_rule_based("Vehicle paint transfer on barrier")
        assert cat == EvidenceCategory.TRACE
        assert conf >= 0.6

    def test_empty_description_returns_none(self):
        cat, conf = _classify_rule_based("")
        assert cat is None
        assert conf == 0.0

    def test_unknown_description_returns_none(self):
        cat, conf = _classify_rule_based("xyz unknown item qwerty")
        assert cat is None
        assert conf == 0.0

    def test_no_firearm_category_exists(self):
        """Ensure the FIREARM category has been removed from the codebase."""
        category_values = [c.value for c in EvidenceCategory]
        assert "Firearm" not in category_values
        assert "FIREARM" not in [c.name for c in EvidenceCategory]


class TestEvidenceClassifier:

    def setup_method(self):
        self.clf = EvidenceClassifier()

    def test_classify_mutates_item(self):
        item = EvidenceItem(description="Mobile phone found at scene")
        self.clf.classify(item)
        assert item.category is not None
        assert item.category_confidence > 0
        assert item.category_source == "rule_based"

    def test_classify_batch(self):
        items = [
            EvidenceItem(description="Hair strand collected"),
            EvidenceItem(description="CCTV recording from camera"),
            EvidenceItem(description="Handwritten note on paper"),
        ]
        result = self.clf.classify_batch(items)
        assert len(result) == 3
        assert all(i.category is not None for i in result)

    def test_classifier_without_watsonx_works(self):
        """Classifier must function with no watsonx client (offline mode)."""
        clf = EvidenceClassifier(watsonx_client=None)
        item = EvidenceItem(description="Fingerprint on glass")
        clf.classify(item)
        assert item.category == EvidenceCategory.TRACE
        assert item.category_source == "rule_based"
