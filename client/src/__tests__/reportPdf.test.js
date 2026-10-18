import { describe, expect, it } from "vitest";
import { buildAnalysisReportContent } from "../utils/reportPdf";

describe("buildAnalysisReportContent", () => {
  it("includes evidence, accessible summaries, and honest accuracy context", () => {
    const report = buildAnalysisReportContent({
      id: "analysis-123",
      fileName: "sample-video.mp4",
      mediaType: "video",
      predictionLabel: "FAKE",
      confidenceScore: 0.98,
      model: "AIDE",
      modelVersion: "v2",
      evidence: [
        {
          type: "Temporal anomaly",
          severity: "high",
          description: "Inconsistent motion was reported.",
          metricValue: "0.91 anomaly score",
          details: [
            {
              frame_number: 12,
              timestamp: 4.5,
              prediction: "FAKE",
              confidence: 0.91,
            },
          ],
        },
      ],
      sampleHeatmaps: [
        { frameIndex: 12, timecode: "00:04.5", note: "Motion inconsistency" },
      ],
    });

    expect(report.seoTitle).toContain("AI Deepfake Detection Report");
    expect(report.seoKeywords).toContain("media authenticity analysis");
    expect(report.technicalSummary).toContain("98% model confidence");
    expect(report.plainLanguageSummary).toContain("not proof of a deepfake");
    expect(report.accuracyDisclosure).toContain(
      "not an accuracy percentage",
    );
    expect(report.gradCamEvidence).toContain("12 @ 4.5s FAKE (91%)");
    expect(report.gradCamEvidence).toContain("0.91 anomaly score");
    expect(report.suspiciousFrames).toContain("Motion inconsistency");
  });

  it("reports supplied accuracy metrics as unverified dataset-level results", () => {
    const report = buildAnalysisReportContent({
      evaluationMetrics: { test_accuracy: 0.98 },
    });

    expect(report.accuracyDisclosure).toContain("model supplied an accuracy metric");
    expect(report.accuracyDisclosure).toContain(
      "not a guarantee for this individual file",
    );
  });
});
