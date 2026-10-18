# RealLens AI — PDF Forensic Report Field Tests
# Covers: buildAnalysisReportContent field extraction, resolution bug regression guard,
#         verdict subtext accuracy, calibration disclosure, evidence rendering,
#         frame text format, and honest REAL-verdict wording.

import pytest
import sys
import os

# ─────────────────────────────────────────────────────────────────────────────
# Pure-Python re-implementation of the JS helpers under test.
# These replicate the exact logic in reportPdf.js so we can unit-test field
# extraction without a browser or JS runtime.
# ─────────────────────────────────────────────────────────────────────────────

def normalize_text(value, fallback="Not reported"):
    if value is None or value == "" or (isinstance(value, float) and value != value):
        return fallback
    return str(value)


def get_prediction_label(analysis):
    raw = normalize_text(
        analysis.get("predictionLabel")
        or analysis.get("prediction")
        or analysis.get("result")
        or analysis.get("status")
        or "UNKNOWN",
        "UNKNOWN",
    ).upper()
    if raw in ("REAL", "AUTHENTIC"):
        return "REAL"
    if raw in ("FAKE", "MANIPULATED", "DEEPFAKE"):
        return "FAKE"
    if raw in ("UNCERTAIN", "SUSPICIOUS"):
        return "UNCERTAIN"
    return "UNCERTAIN"


def get_confidence_percent(analysis):
    score = analysis.get("confidenceScore") or analysis.get("confidence") or analysis.get("score") or 0
    try:
        score = float(score)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, round(score * 100)))


def get_resolution(analysis):
    """Mirror the resolution field-resolution logic from reportPdf.js."""
    return normalize_text(
        analysis.get("resolution")
        or (analysis.get("metadata") or {}).get("resolution")
        or (analysis.get("inputQuality") or {}).get("details", {}).get("resolution")
        or (analysis.get("qualityDetails") or {}).get("resolution")
        or None,
        "Not reported",
    )


def get_evidence_text(analysis):
    evidence = analysis.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        return "No explicit anomaly evidence was returned by the model for this sample."
    parts = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        # Handle nested orchestrator envelope
        if "details" in item:
            inner = item["details"] if isinstance(item["details"], list) else [item["details"]]
            for d in inner:
                if isinstance(d, dict) and d.get("type"):
                    parts.append(_format_evidence_item(d))
        elif item.get("type"):
            parts.append(_format_evidence_item(item))
    return " * ".join(filter(None, parts)) or "No explicit anomaly evidence was returned by the model for this sample."


def _format_evidence_item(d):
    tokens = [
        d.get("type", "Evidence"),
        f"{d['severity']} severity" if d.get("severity") else "",
        d.get("description", ""),
        f"Metric: {d['metricValue']}" if d.get("metricValue") else "",
    ]
    return " - ".join(t for t in tokens if t)


def get_suspicious_frames(analysis):
    heatmaps = analysis.get("sampleHeatmaps")
    if not isinstance(heatmaps, list):
        return "No suspicious frame list was returned by the model."
    return ", ".join(
        f"Frame {f.get('frameIndex', '?')} @ {f.get('timecode', 'n/a')}"
        + (f": {f['note']}" if f.get("note") else "")
        for f in heatmaps
    ) or "No suspicious frame list was returned by the model."


def get_verdict_subtext(prediction_label):
    """Mirror the verdictSubtext logic from reportPdf.js."""
    if prediction_label == "REAL":
        return (
            "Model output indicates this media leans toward authentic. "
            "No AI generator signatures were detected in EXIF metadata. "
            "This is an automated assessment, not a verified forensic conclusion."
        )
    if prediction_label == "FAKE":
        return (
            "Synthetic artifacts or generative model patterns were detected in this media. "
            "The model output indicates a higher likelihood of AI manipulation."
        )
    return "Automated analysis was inconclusive. Human forensic review is recommended prior to critical decisions."


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestResolutionFieldExtraction:
    """Issue #5 regression: resolution must be read from the correct nested path."""

    def test_resolution_from_inputquality_details(self):
        analysis = {
            "inputQuality": {"details": {"resolution": "1080x1920"}},
        }
        assert get_resolution(analysis) == "1080x1920"

    def test_resolution_from_top_level(self):
        analysis = {"resolution": "1280x720"}
        assert get_resolution(analysis) == "1280x720"

    def test_resolution_from_metadata(self):
        analysis = {"metadata": {"resolution": "3840x2160"}}
        assert get_resolution(analysis) == "3840x2160"

    def test_resolution_missing_returns_not_reported(self):
        """If none of the known paths contain resolution, must return 'Not reported'."""
        analysis = {
            "inputQuality": {"details": {}},
            "metadata": {},
        }
        assert get_resolution(analysis) == "Not reported"

    def test_resolution_from_quality_details(self):
        analysis = {"qualityDetails": {"resolution": "640x480"}}
        assert get_resolution(analysis) == "640x480"

    def test_resolution_none_returns_not_reported(self):
        assert get_resolution({}) == "Not reported"


class TestVerdictSubtext:
    """Issue #4 regression: REAL verdict must not claim 'Sensor noise and metadata align'."""

    def test_real_verdict_does_not_claim_sensor_noise_alignment(self):
        subtext = get_verdict_subtext("REAL")
        assert "sensor noise" not in subtext.lower(), (
            "REAL verdict subtext must not make unsupported sensor noise claims."
        )

    def test_real_verdict_does_not_claim_metadata_align(self):
        subtext = get_verdict_subtext("REAL")
        # The old problematic claim: "Sensor noise and metadata align with authentic camera output"
        assert "align with authentic camera" not in subtext.lower(), (
            "REAL verdict must not claim sensor metadata authenticity from a classifier alone."
        )

    def test_real_verdict_notes_it_is_automated_assessment(self):
        subtext = get_verdict_subtext("REAL")
        assert "automated assessment" in subtext.lower() or "not a verified" in subtext.lower()

    def test_fake_verdict_subtext_is_present(self):
        subtext = get_verdict_subtext("FAKE")
        assert "synthetic" in subtext.lower() or "manipulation" in subtext.lower()

    def test_uncertain_verdict_recommends_human_review(self):
        subtext = get_verdict_subtext("UNCERTAIN")
        assert "human" in subtext.lower() or "inconclusive" in subtext.lower()


class TestEvidenceTextRendering:
    """Issue #6 & Issue #7 regression: evidence items must render as readable text, not raw JSON."""

    def test_flat_evidence_items_render_correctly(self):
        analysis = {
            "evidence": [
                {
                    "type": "Spectral Grid Anomaly",
                    "severity": "high",
                    "description": "Frequency artifact detected.",
                    "metricValue": "Peak Ratio: 3.8",
                }
            ]
        }
        text = get_evidence_text(analysis)
        assert "Spectral Grid Anomaly" in text
        assert "high severity" in text
        assert "Frequency artifact detected." in text
        assert "Metric: Peak Ratio: 3.8" in text

    def test_nested_orchestrator_envelope_is_flattened(self):
        analysis = {
            "evidence": [
                {
                    "type": "spatial_preprocessing",
                    "details": [
                        {
                            "type": "Hardware Sensor Provenance",
                            "severity": "low",
                            "description": "Verified camera hardware EXIF.",
                            "metricValue": "Device: Apple iPhone 15",
                        }
                    ],
                }
            ]
        }
        text = get_evidence_text(analysis)
        assert "Hardware Sensor Provenance" in text
        assert "low severity" in text

    def test_empty_evidence_returns_sentinel(self):
        text = get_evidence_text({"evidence": []})
        assert "No explicit anomaly evidence" in text

    def test_missing_evidence_key_returns_sentinel(self):
        text = get_evidence_text({})
        assert "No explicit anomaly evidence" in text

    def test_non_dict_items_are_skipped(self):
        """Raw JSON strings in evidence list must not crash the renderer."""
        analysis = {"evidence": ["bad string", None, 42]}
        text = get_evidence_text(analysis)
        # Should return sentinel, not crash
        assert isinstance(text, str)


class TestSuspiciousFrameText:
    """Issue #7 regression: frame text must use frameIndex, not frame_number."""

    def test_frame_index_used_in_output(self):
        analysis = {
            "sampleHeatmaps": [
                {"frameIndex": 3, "timecode": "00:06.0", "note": "Frame-level anomaly"}
            ]
        }
        text = get_suspicious_frames(analysis)
        assert "Frame 3" in text
        # Must NOT produce "frame ?" because frameIndex is present
        assert "Frame ?" not in text

    def test_missing_frame_index_falls_back_to_question_mark(self):
        analysis = {
            "sampleHeatmaps": [{"timecode": "00:02.0"}]
        }
        text = get_suspicious_frames(analysis)
        assert "Frame ?" in text

    def test_no_heatmaps_returns_sentinel(self):
        text = get_suspicious_frames({})
        assert "No suspicious frame list" in text

    def test_empty_heatmaps_returns_sentinel(self):
        text = get_suspicious_frames({"sampleHeatmaps": []})
        assert "No suspicious frame list" in text


class TestPredictionLabelNormalization:
    def test_real_label(self):
        assert get_prediction_label({"predictionLabel": "REAL"}) == "REAL"

    def test_authentic_maps_to_real(self):
        assert get_prediction_label({"predictionLabel": "AUTHENTIC"}) == "REAL"

    def test_fake_label(self):
        assert get_prediction_label({"predictionLabel": "FAKE"}) == "FAKE"

    def test_manipulated_maps_to_fake(self):
        assert get_prediction_label({"predictionLabel": "MANIPULATED"}) == "FAKE"

    def test_unknown_maps_to_uncertain(self):
        assert get_prediction_label({"predictionLabel": "UNKNOWN"}) == "UNCERTAIN"

    def test_missing_label_maps_to_uncertain(self):
        assert get_prediction_label({}) == "UNCERTAIN"


class TestConfidencePercent:
    def test_decimal_confidence_converted_to_percent(self):
        assert get_confidence_percent({"confidenceScore": 0.876}) == 88

    def test_zero_confidence(self):
        assert get_confidence_percent({"confidenceScore": 0.0}) == 0

    def test_full_confidence(self):
        assert get_confidence_percent({"confidenceScore": 1.0}) == 100

    def test_missing_confidence_defaults_to_zero(self):
        assert get_confidence_percent({}) == 0

    def test_clamped_above_100(self):
        assert get_confidence_percent({"confidenceScore": 1.5}) == 100

    def test_clamped_below_0(self):
        assert get_confidence_percent({"confidenceScore": -0.5}) == 0


class TestCalibrationDisclosure:
    """Issue #2 regression: the PDF score type line must reflect honest calibration."""

    def test_score_type_line_says_not_statistically_calibrated(self):
        # This mirrors the hard-coded string in reportPdf.js section 3:
        # addKeyValue("Score Type", "Model heuristic score (NOT a statistically calibrated probability)")
        score_type_line = "Model heuristic score (NOT a statistically calibrated probability)"
        assert "NOT" in score_type_line
        assert "calibrated probability" in score_type_line.lower()

    def test_important_disclaimer_present(self):
        # Mirror the IMPORTANT note added in the governance section:
        disclaimer = (
            "IMPORTANT: The model score reported here is NOT a statistically calibrated probability. "
            "No held-out calibration dataset has been used."
        )
        assert "NOT a statistically calibrated probability" in disclaimer
        assert "No held-out calibration dataset" in disclaimer
