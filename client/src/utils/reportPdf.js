import { jsPDF } from "jspdf";

const normalizeText = (value, fallback = "Not reported") => {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
};

const getPredictionLabel = (analysis = {}) => {
  const raw = normalizeText(
    analysis.predictionLabel ||
      analysis.prediction ||
      analysis.result ||
      analysis.status ||
      "UNKNOWN",
    "UNKNOWN",
  ).toUpperCase();

  if (raw === "REAL" || raw === "AUTHENTIC") return "REAL";
  if (raw === "FAKE" || raw === "MANIPULATED" || raw === "DEEPFAKE")
    return "FAKE";
  if (raw === "UNCERTAIN" || raw === "SUSPICIOUS") return "UNCERTAIN";
  return "UNCERTAIN";
};

const getConfidencePercent = (analysis = {}) => {
  const score = Number(
    analysis.confidenceScore ?? analysis.confidence ?? analysis.score ?? 0,
  );
  if (!Number.isFinite(score)) return 0;
  return Math.max(0, Math.min(100, Math.round(score * 100)));
};

const getFileHash = (analysis = {}) =>
  normalizeText(
    analysis.fileHash ||
      analysis.metadata?.hashSHA256 ||
      analysis.metadata?.hash ||
      analysis.hash ||
      "Not computed for this analysis",
    "Not computed for this analysis",
  );

const getEvaluationMetrics = (analysis = {}) => {
  const metrics =
    analysis.evaluationMetrics ||
    analysis.modelMetrics ||
    analysis.metadata?.evaluationMetrics ||
    analysis.metadata?.metrics ||
    {};

  const entries = Object.entries(metrics).filter(
    ([, value]) => value !== null && value !== undefined && value !== "",
  );
  if (entries.length === 0) {
    return "No measured evaluation metrics were returned in this analysis record.";
  }

  return entries
    .map(
      ([key, value]) =>
        `${key.replace(/_/g, " ")}: ${Number(value).toFixed?.(value < 1 && value > 0 ? 3 : 2) ?? value}`,
    )
    .join(" | ");
};

const getEvidenceText = (analysis = {}) => {
  const evidenceList = Array.isArray(analysis.evidence)
    ? analysis.evidence
    : [];
  if (evidenceList.length === 0) {
    return "No explicit anomaly evidence was returned by the model for this sample.";
  }

  return evidenceList
    .map((item) => {
      if (!item || typeof item !== "object") return "";

      const mainParts = [
        item.type || "Evidence",
        item.severity ? `${item.severity} severity` : "",
        item.description || "",
        item.metricValue ? `Metric: ${item.metricValue}` : "",
      ].filter(Boolean);

      let detailString = "";
      if (item.details !== undefined) {
        const inner = Array.isArray(item.details) ? item.details : [item.details];
        const detailParts = inner
          .map((d) => {
            if (!d || typeof d !== "object") return "";
            if (d.frame_number !== undefined) {
              const conf = d.confidence !== undefined ? Math.round(Number(d.confidence) * 100) : 0;
              return `${d.frame_number} @ ${d.timestamp ?? "0"}s ${d.prediction || "FLAGGED"} (${conf}%)`;
            }
            if (d.type || d.description) {
              return [
                d.type,
                d.severity ? `${d.severity} severity` : "",
                d.description,
                d.metricValue ? `Metric: ${d.metricValue}` : "",
              ].filter(Boolean).join(" - ");
            }
            return "";
          })
          .filter(Boolean);

        if (detailParts.length > 0) {
          detailString = detailParts.join("; ");
        }
      }

      if (mainParts.length > 0 && detailString) {
        return `${mainParts.join(" - ")} [${detailString}]`;
      }
      return mainParts.join(" - ") || detailString;
    })
    .filter(Boolean)
    .join(" * ");
};

const getSummaryText = (analysis = {}) => {
  const qualityStatus = String(
    (typeof analysis.quality === "object"
      ? analysis.quality.status
      : analysis.quality) ||
      analysis.qualityStatus ||
      "UNKNOWN",
  ).toUpperCase();
  const qualityWarning =
    analysis.qualityWarning ||
    (typeof analysis.quality === "object" ? analysis.quality.warning : "") ||
    analysis.inputQuality?.warning ||
    analysis.qualityDetails?.warning ||
    (qualityStatus === "POOR"
      ? "Low-quality media may reduce detection reliability."
      : "");

  const fallback =
    analysis.message ||
    (analysis.result === "authentic"
      ? "The uploaded media remains within the expected authenticity band for the current model pipeline."
      : analysis.result === "manipulated"
        ? "The model found a concerning anomaly pattern, which suggests the content may be manipulated."
        : "The model produced an uncertain result. Human review is recommended before making a decision.");

  const detail = qualityWarning ? `${qualityWarning} ${fallback}` : fallback;
  return normalizeText(
    detail,
    "The model produced an uncertain result. Human review is recommended before making a decision.",
  );
};

const getAnalysisDate = (analysis = {}) => {
  const dateValue =
    analysis.processedAt ||
    analysis.uploadedAt ||
    analysis.generatedAt ||
    new Date().toISOString();
  const date = new Date(dateValue);
  return Number.isNaN(date.getTime())
    ? "Date not available"
    : date.toLocaleString();
};

const wrapText = (doc, text, maxWidth) => doc.splitTextToSize(text, maxWidth);

export const buildAnalysisReportContent = (analysis = {}) => {
  const predictionLabel = getPredictionLabel(analysis);
  const confidencePercent = getConfidencePercent(analysis);
  const fileName = normalizeText(
    analysis.fileName ||
      analysis.originalName ||
      analysis.filename ||
      "Unknown media file",
    "Unknown media file",
  );
  const suspiciousFrames = Array.isArray(analysis.sampleHeatmaps)
    ? analysis.sampleHeatmaps
        .map(
          (frame) =>
            `Frame ${frame.frameIndex ?? "?"} @ ${frame.timecode ?? "n/a"}${frame.note ? `: ${frame.note}` : ""}`,
        )
        .join(", ")
    : "No suspicious frame list was returned by the model.";

  const timestamps = Array.isArray(analysis.sampleHeatmaps)
    ? analysis.sampleHeatmaps
        .map((frame) => frame.timecode || "n/a")
        .filter(Boolean)
        .join(", ")
    : "No timestamped evidence was returned.";

  const modelName = normalizeText(
    analysis.modelName || analysis.model || "AIDE",
    "AIDE",
  );
  const modelVersion = normalizeText(
    analysis.modelVersion || analysis.model_version || "Not specified",
    "Not specified",
  );
  const trainingDataset = normalizeText(
    analysis.trainingDataset ||
      analysis.dataset ||
      analysis.metadata?.trainingDataset ||
      "Not reported for this analysis run",
    "Not reported for this analysis run",
  );
  const modalities = analysis.modalities || analysis.modalityScores || {};
  const modalityScores = Object.entries(modalities)
    .filter(([, item]) => item && typeof item === "object")
    .map(([name, item]) => {
      const score =
        item.score === null || item.score === undefined
          ? "not available"
          : Number(item.score).toFixed(4);
      const role = item.included_in_fusion
        ? `included (normalized weight ${Number(item.normalized_fusion_weight ?? item.fusion_weight ?? 0).toFixed(3)}, contribution ${Number(item.weighted_contribution || 0).toFixed(4)})`
        : "not included in fusion";
      return `${name}: ${score} (${item.score_type || "score"}, ${item.status || "status unknown"}, ${role})`;
    });
  const pipelineModules = Object.entries(analysis.processing?.modules || {}).map(
    ([name, item]) => `${name}: ${item.status || "unknown"}`,
  );
  const pipelineTimestamps = [
    analysis.timestamps?.started_at
      ? `Started ${analysis.timestamps.started_at}`
      : "",
    analysis.timestamps?.completed_at
      ? `Completed ${analysis.timestamps.completed_at}`
      : "",
  ]
    .filter(Boolean)
    .join(" | ");
  const modelVersions = Object.entries(
    analysis.model_versions || analysis.modelVersions || {},
  ).map(([name, version]) => `${name}: ${version}`);
  const evaluationMetrics = getEvaluationMetrics(analysis);
  const hasReportedAccuracy =
    /(^|[|,;])\s*(?:test\s+|val(?:idation)?\s+)?accuracy\s*:/i.test(
      evaluationMetrics,
    );
  const accuracyDisclosure = hasReportedAccuracy
    ? "The model supplied an accuracy metric, but its benchmark dataset and evaluation conditions were not independently verified in this report. A dataset-level accuracy value is not a guarantee for this individual file."
    : "No independently measured model-accuracy figure was supplied for this analysis. The per-file confidence score is not an accuracy percentage and does not establish that the result is correct.";
  const rawFakeProb =
    analysis.fake_probability ??
    analysis.fakeProbability ??
    analysis.processing?.fusion?.fake_probability ??
    null;
  const decisionThreshold = Number(
    analysis.decision_threshold ?? analysis.threshold ?? 0.5,
  );
  const decisionMarginPercent =
    rawFakeProb !== null && rawFakeProb !== undefined
      ? `${(Math.abs(Number(rawFakeProb) - decisionThreshold) * 100).toFixed(2)}%`
      : "Not computed";

  const technicalSummary = `${modelName} ${modelVersion} classified this ${normalizeText(analysis.mediaType || "media")} as ${predictionLabel} at ${confidencePercent}% model confidence (Decision margin: ${decisionMarginPercent} from ${Math.round(decisionThreshold * 100)}% threshold). This score describes the uncalibrated model output for this file; it is not a verified accuracy rate.`;
  const plainLanguageSummary =
    predictionLabel === "REAL"
      ? `The AI model classified this ${normalizeText(analysis.mediaType || "media")} as REAL (${confidencePercent}% model confidence). This is an automated assessment, not a verified forensic conclusion or proof of physical camera authenticity; check the evidence and original source before relying on it.`
      : predictionLabel === "FAKE"
        ? `The AI found signals associated with possible manipulation in this ${normalizeText(analysis.mediaType || "media")} (${confidencePercent}% model confidence). This is not proof of a deepfake; review the evidence and ask a person to verify it.`
        : `The AI could not confidently decide whether this ${normalizeText(analysis.mediaType || "media")} is authentic or manipulated (${confidencePercent}% model confidence). Treat it as inconclusive and request human review.`;
  const seoTitle = `AI Deepfake Detection Report for ${fileName} | RealLens AI`;

  return {
    predictionLabel,
    confidencePercent,
    decisionMargin: decisionMarginPercent,
    authenticityVerified: "Not established by model prediction alone",
    groundTruth: normalizeText(analysis.ground_truth || analysis.evaluation?.ground_truth || null, "None supplied"),
    evaluationOutcome: normalizeText(analysis.evaluation_outcome || analysis.evaluation?.outcome || null, "N/A"),
    technicalSummary,
    plainLanguageSummary,
    accuracyDisclosure,
    seoTitle,
    seoKeywords:
      "AI deepfake detection, media authenticity analysis, forensic media report, image video audio manipulation evidence, RealLens AI",
    dateTime: getAnalysisDate(analysis),
    fileName,
    mediaType: normalizeText(analysis.mediaType || "unknown", "unknown"),
    fileHash: getFileHash(analysis),
    duration: normalizeText(
      analysis.duration || analysis.metadata?.duration || "Not reported",
      "Not reported",
    ),
    resolution: normalizeText(
      analysis.resolution ||
        analysis.metadata?.resolution ||
        analysis.inputQuality?.details?.resolution ||
        analysis.qualityDetails?.resolution ||
        "Not reported",
      "Not reported",
    ),
    fps: normalizeText(
      analysis.fps || analysis.metadata?.fps || "Not reported",
      "Not reported",
    ),
    audioAvailable: normalizeText(
      analysis.audioAvailable ??
        (typeof analysis.audio_available === "boolean"
          ? analysis.audio_available
            ? "Yes"
            : "No"
          : undefined) ??
        analysis.metadata?.audioAvailable ??
        analysis.metadata?.audio_available ??
        (analysis.mediaType === "audio" ? "Yes" : "No"),
      "Not reported",
    ),
    facesDetected: normalizeText(
      analysis.facesDetected ?? analysis.faces_detected ?? "Not reported",
      "Not reported",
    ),
    spatialAnalysis: normalizeText(
      analysis.spatialAnalysis ||
        analysis.metadata?.spatialAnalysis ||
        (Array.isArray(analysis.evidence) && analysis.evidence[0]?.type
          ? analysis.evidence[0].type
          : "No measured spatial anomaly was reported."),
      "No measured spatial anomaly was reported.",
    ),
    temporalAnalysis: normalizeText(
      analysis.temporalAnalysis ||
        analysis.metadata?.temporalAnalysis ||
        (Array.isArray(analysis.evidence)
          ? analysis.evidence.find((item) =>
              /time|frame|motion|temporal/i.test(
                item.type || item.description || "",
              ),
            )?.description || "No measured temporal anomaly was reported."
          : "No measured temporal anomaly was reported."),
      "No measured temporal anomaly was reported.",
    ),
    frequencyAnalysis: normalizeText(
      analysis.frequencyAnalysis ||
        analysis.metadata?.frequencyAnalysis ||
        (Array.isArray(analysis.evidence)
          ? analysis.evidence.find((item) =>
              /frequency|spectral|audio/i.test(
                item.type || item.description || "",
              ),
            )?.description || "No measured frequency anomaly was reported."
          : "No measured frequency anomaly was reported."),
      "No measured frequency anomaly was reported.",
    ),
    audioAnalysis: normalizeText(
      analysis.audioAnalysis ||
        analysis.metadata?.audioAnalysis ||
        (analysis.mediaType === "audio"
          ? "Audio stream analyzed by the model."
          : "No separate audio analysis result was reported for this sample."),
      "No separate audio analysis result was reported for this sample.",
    ),
    suspiciousFrames,
    timestamps,
    gradCamEvidence: getEvidenceText(analysis),
    frequencyVisualization: normalizeText(
      analysis.frequencyVisualization ||
        analysis.metadata?.frequencyVisualization ||
        "No frequency visualization generated for this analysis run.",
      "No frequency visualization generated for this analysis run.",
    ),
    resolutionQuality: normalizeText(
      analysis.inputQuality?.details?.resolution ||
        analysis.inputQuality?.resolution ||
        analysis.qualityDetails?.resolution ||
        analysis.resolution ||
        "Not reported",
      "Not reported",
    ),
    compressionIndicators: normalizeText(
      analysis.inputQuality?.details?.compressionIndicators ||
        analysis.inputQuality?.compressionIndicators ||
        analysis.qualityDetails?.compressionIndicators ||
        analysis.metadata?.compressionIndicators ||
        "Not reported",
      "Not reported",
    ),
    blurNoiseIndicators: normalizeText(
      analysis.inputQuality?.details?.blurEstimate &&
        analysis.inputQuality?.details?.noiseEstimate
        ? `Blur: ${analysis.inputQuality.details.blurEstimate}; Noise: ${analysis.inputQuality.details.noiseEstimate}`
        : analysis.inputQuality?.blurNoiseIndicators ||
            analysis.qualityDetails?.blurNoiseIndicators ||
            analysis.metadata?.blurNoiseIndicators ||
            "Not reported",
      "Not reported",
    ),
    qualityStatus: normalizeText(
      (typeof analysis.quality === "object"
        ? analysis.quality.status
        : analysis.quality) ||
        analysis.qualityStatus ||
        "UNKNOWN",
      "UNKNOWN",
    ),
    qualityWarning: normalizeText(
      analysis.qualityWarning ||
        (typeof analysis.quality === "object" ? analysis.quality.warning : "") ||
        analysis.inputQuality?.warning ||
        analysis.qualityDetails?.warning ||
        "",
      "",
    ),
    summary: getSummaryText(analysis),
    limitations:
      "The prediction is generated by a machine-learning model and should not be treated as absolute proof of authenticity or manipulation. Absent metadata, frequency spectrum distributions, and noise measurements cannot independently prove physical camera capture.",
    modelName,
    modelVersion,
    trainingDataset,
    modalityScores,
    pipelineModules,
    pipelineTimestamps: pipelineTimestamps || "Not reported",
    modelVersions,
    fusionMethod: normalizeText(
      analysis.processing?.fusion?.method || "Not reported",
    ),
    fusedFakeProbability:
      rawFakeProb === null || rawFakeProb === undefined
        ? "Not available"
        : `${(Number(rawFakeProb) * 100).toFixed(2)}%`,
    confidenceCalibration: normalizeText(
      analysis.processing?.fusion?.confidence_calibration?.description ||
        analysis.confidence_calibration?.message ||
        "Score is uncalibrated. Confidence reflects distance from the decision boundary; no held-out calibration model is configured.",
    ),
    unavailableModalities: Array.isArray(
      analysis.processing?.unavailable_modalities,
    )
      ? analysis.processing.unavailable_modalities.join(", ") || "None"
      : "Not reported",
    evaluationMetrics,
    inferenceTime: normalizeText(
      analysis.processingTimeMs ||
        analysis.inferenceTimeMs ||
        analysis.metadata?.inferenceTime ||
        "Not reported",
      "Not reported",
    ),
    analysisId: normalizeText(
      analysis.id || analysis.analysisId || analysis.mediaId || "Not reported",
      "Not reported",
    ),
  };
};

export const cleanPdfText = (str) => {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/[\u2013\u2014]/g, " - ")
    .replace(/[\u2022\u25CF]/g, "* ")
    .replace(/[\u00B7]/g, " | ")
    .replace(/[^\x20-\x7E\t\n\r]/g, " ");
};

export const getReportFileName = (analysis = {}) => {
  const rawFileName =
    analysis.fileName ||
    analysis.originalName ||
    analysis.filename ||
    "ImageName";
  const baseName = String(rawFileName)
    .replace(/^.*[\\/]/, "")
    .replace(/\.[^/.]+$/, "")
    .trim();
  const cleanImageName = baseName.replace(/[^a-zA-Z0-9_.-]/g, "_") || "ImageName";
  return `${cleanImageName}_forensic_report.pdf`;
};

export const generateAnalysisReportPdf = (analysis = {}, options = {}) => {
  const autoDownload = options.autoDownload ?? true;
  const report = buildAnalysisReportContent(analysis);
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  doc.setProperties({
    title: report.seoTitle,
    subject: "AI-powered deepfake detection and media authenticity analysis",
    author: "RealLens AI",
    keywords: report.seoKeywords,
    creator: "RealLens AI Digital Forensics Lab",
  });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 40;
  const contentWidth = pageWidth - margin * 2;
  const bottomMargin = 45;
  let y = margin;

  const ensureSpace = (spaceNeeded = 20) => {
    if (y + spaceNeeded > pageHeight - bottomMargin) {
      doc.addPage();
      y = margin + 35; // Reserve top space for page 2+ running header
    }
  };

  const addSectionHeader = (title, accentColor = [14, 165, 233]) => {
    ensureSpace(34);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(15, 23, 42);
    doc.setFontSize(10);
    doc.text(title.toUpperCase(), margin, y);
    doc.setDrawColor(...accentColor);
    doc.setLineWidth(1.2);
    doc.line(margin, y + 4, pageWidth - margin, y + 4);
    y += 18;
  };

  const addWrappedText = (text, color = [51, 65, 85], size = 8.5, style = "normal") => {
    const sanitized = cleanPdfText(text);
    const wrapped = wrapText(doc, sanitized, contentWidth);
    const lineHeight = size + 4;
    doc.setFont("helvetica", style);
    doc.setTextColor(...color);
    doc.setFontSize(size);
    wrapped.forEach((line) => {
      ensureSpace(lineHeight);
      doc.text(line, margin, y);
      y += lineHeight;
    });
    y += 2;
  };

  const addKeyValue = (label, value, labelWidth = 145) => {
    const textVal = cleanPdfText(value || "N/A");
    const wrapped = wrapText(doc, textVal, contentWidth - labelWidth);
    const lineHeight = 11.5;
    const blockHeight = Math.max(1, wrapped.length) * lineHeight;

    ensureSpace(blockHeight + 3);

    doc.setFont("helvetica", "bold");
    doc.setTextColor(71, 85, 105);
    doc.setFontSize(8.5);
    doc.text(`${cleanPdfText(label)}:`, margin, y);

    doc.setFont("helvetica", "normal");
    doc.setTextColor(15, 23, 42);

    wrapped.forEach((line, idx) => {
      if (idx > 0) {
        y += lineHeight;
        ensureSpace(lineHeight);
      }
      doc.text(line, margin + labelWidth, y);
    });
    y += lineHeight + 3;
  };

  // 1. TOP BRAND HEADER
  doc.setFillColor(7, 14, 27);
  doc.rect(0, 0, pageWidth, 85, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.text("REALLENS AI", margin, 36);

  doc.setFontSize(9);
  doc.setTextColor(56, 189, 248);
  doc.text("FORENSIC MEDIA AUTHENTICITY & DEEPFAKE VERIFICATION REPORT", margin, 52);

  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184);
  doc.text(`Generated: ${report.dateTime}  |  Report ID: ${report.analysisId.slice(0, 24)}`, margin, 68);

  y = 100;

  // 2. EXECUTIVE SUMMARY & VERDICT BADGE (FOR NON-TECH STAKEHOLDERS)
  const isReal = report.predictionLabel === "REAL";
  const isFake = report.predictionLabel === "FAKE";
  const verdictBg = isReal ? [240, 253, 244] : isFake ? [254, 242, 242] : [254, 252, 232];
  const verdictBorder = isReal ? [34, 197, 94] : isFake ? [239, 68, 68] : [234, 179, 8];
  const verdictTextColor = isReal ? [22, 101, 52] : isFake ? [153, 27, 27] : [133, 77, 14];

  doc.setFillColor(...verdictBg);
  doc.setDrawColor(...verdictBorder);
  doc.setLineWidth(1.5);
  doc.roundedRect(margin, y, contentWidth, 76, 6, 6, "FD");

  doc.setFont("helvetica", "bold");
  doc.setTextColor(...verdictTextColor);
  doc.setFontSize(13);
  const verdictTitle = isReal
    ? "VERDICT: REAL-CLASSIFIED (AUTOMATED MODEL OUTPUT)"
    : isFake
      ? "VERDICT: AI-GENERATED / MANIPULATED"
      : "VERDICT: INCONCLUSIVE / UNCERTAIN";
  doc.text(verdictTitle, margin + 14, y + 22);

  // Confidence meter pill & progress bar
  doc.setFontSize(10.5);
  doc.text(`Confidence Score: ${report.confidencePercent}% (Margin: ${report.decisionMargin})`, margin + 14, y + 38);

  // Draw visual confidence bar
  const barX = margin + 170;
  const barY = y + 29;
  const barWidth = contentWidth - 190;
  const barHeight = 11;
  doc.setFillColor(226, 232, 240);
  doc.roundedRect(barX, barY, barWidth, barHeight, 3, 3, "F");
  doc.setFillColor(...(isReal ? [34, 197, 94] : isFake ? [239, 68, 68] : [234, 179, 8]));
  const fillWidth = Math.max(8, (barWidth * report.confidencePercent) / 100);
  doc.roundedRect(barX, barY, fillWidth, barHeight, 3, 3, "F");

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(71, 85, 105);
  const verdictSubtext = isReal
    ? `Model output indicates this media leans toward authentic (Decision margin: ${report.decisionMargin}). This is an automated assessment, not a verified forensic conclusion or proof of physical camera hardware capture.`
    : isFake
      ? "Synthetic artifacts or generative model patterns were detected in this media. The model output indicates a higher likelihood of AI manipulation."
      : "Automated analysis was inconclusive. Secondary human forensic review is recommended prior to critical decisions.";
  doc.text(verdictSubtext, margin + 14, y + 56);

  y += 94;

  // 3. EXECUTIVE TAKEAWAY (PLAIN-LANGUAGE EXPLANATION FOR NON-TECH USERS)
  addSectionHeader("1. Executive Summary & Takeaway (For Everyone)", [14, 165, 233]);
  addWrappedText(report.plainLanguageSummary, [15, 23, 42], 9, "bold");
  addWrappedText(report.summary, [51, 65, 85], 8.5, "normal");

  // 4. MEDIA TELEMETRY & DIGITAL PROVENANCE
  addSectionHeader("2. Digital Asset Provenance & File Telemetry", [99, 102, 241]);
  addKeyValue("File Name", report.fileName);
  addKeyValue("Media Modality", report.mediaType.toUpperCase());
  addKeyValue("Cryptographic Hash (SHA-256)", report.fileHash);
  addKeyValue("Resolution / Dimensions", report.resolution);
  addKeyValue("Frame Rate / Duration", `${report.fps} | Duration: ${report.duration}`);
  addKeyValue("Faces Detected", report.facesDetected);

  // 5. TECHNICAL FORENSIC MODALITY BREAKDOWN
  addSectionHeader("3. Forensic Modality Analysis (Technical Deep Dive)", [16, 185, 129]);
  if (report.modalityScores.length > 0) {
    report.modalityScores.forEach((line) => addKeyValue("Modality Metric", line));
  } else {
    addKeyValue("Spatial Neural Net", report.spatialAnalysis);
    addKeyValue("Frequency Domain (DCT)", report.frequencyAnalysis);
    addKeyValue("Temporal Coherence", report.temporalAnalysis);
    addKeyValue("Acoustic Spectrogram", report.audioAnalysis);
  }
  addKeyValue("Multimodal Fusion Method", report.fusionMethod);
  addKeyValue("Fused Fake Probability", report.fusedFakeProbability);
  addKeyValue("Decision Threshold", "50.0% (fake_probability >= 0.50 -> FAKE)");
  addKeyValue("Decision Margin", report.decisionMargin);
  addKeyValue("Authenticity Verification", report.authenticityVerified);
  if (report.groundTruth && report.groundTruth !== "None supplied") {
    addKeyValue("Known Ground Truth", report.groundTruth);
    addKeyValue("Evaluation Outcome", report.evaluationOutcome);
  }
  addKeyValue("Score Type", "Model heuristic score (NOT a statistically calibrated probability)");
  addKeyValue("Confidence Calibration Status", report.confidenceCalibration);
  addWrappedText(
    "NOTE: DCT frequency distribution is a supporting metric only. A normal frequency spectrum " +
    "does not confirm authentic camera capture. An anomalous spectrum is corroborating evidence, " +
    "not definitive proof of manipulation. Camera EXIF metadata is used only to flag absence of " +
    "hardware signatures — missing metadata does not prove synthetic generation.",
    [100, 116, 139], 7.5, "italic"
  );

  // 6. DETECTED FORENSIC EVIDENCE & ANOMALY FINDINGS
  addSectionHeader("4. Detected Evidence & Artifact Trail", [245, 158, 11]);
  addKeyValue("Technical Summary", report.technicalSummary);
  addKeyValue("Observed Evidence", report.gradCamEvidence);
  if (report.suspiciousFrames && !report.suspiciousFrames.includes("No suspicious")) {
    addKeyValue("Keyframe Anomalies", report.suspiciousFrames);
  }

  // 7. INPUT SIGNAL QUALITY ASSESSMENT
  addSectionHeader("5. Input Signal Quality Assessment", [139, 92, 246]);
  addKeyValue("Input Quality Status", report.qualityStatus);
  addKeyValue("Compression Indicator", report.compressionIndicators);
  addKeyValue("Sensor Blur & Noise Variance", report.blurNoiseIndicators);
  if (report.qualityWarning) {
    addKeyValue("Quality Advisory", report.qualityWarning);
  }

  // 8. MODEL GOVERNANCE, LIMITATIONS & DISCLOSURE
  addSectionHeader("6. Model Governance, Limitations & Disclosure", [100, 116, 139]);
  addKeyValue("Inference Engine", `${report.modelName} (${report.modelVersion})`);
  addKeyValue("Processing Duration", `${report.inferenceTime} ms`);
  addWrappedText(
    "IMPORTANT: The model score reported here is NOT a statistically calibrated probability. " +
    "No held-out calibration dataset has been used. The confidence value reflects the model's " +
    "output distance from the 0.5 decision threshold. It does not represent a verified accuracy rate.",
    [153, 27, 27], 7.5, "italic"
  );
  addWrappedText(report.accuracyDisclosure, [100, 116, 139], 7.5, "italic");
  addWrappedText(report.limitations, [100, 116, 139], 7.5, "normal");

  // Multi-page running header and footer
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    if (i > 1) {
      doc.setFillColor(7, 14, 27);
      doc.rect(0, 0, pageWidth, 26, "F");
      doc.setFont("helvetica", "bold");
      doc.setFontSize(8);
      doc.setTextColor(255, 255, 255);
      doc.text("REALLENS AI — FORENSIC MEDIA VERIFICATION REPORT", margin, 17);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(148, 163, 184);
      const safeFile = cleanPdfText(report.fileName);
      doc.text(safeFile.length > 40 ? `${safeFile.slice(0, 37)}...` : safeFile, pageWidth - margin - 160, 17);
    }
    // Footer on all pages
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.5);
    doc.line(margin, pageHeight - 24, pageWidth - margin, pageHeight - 24);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text("RealLens AI Forensic Lab | Automated Deepfake Detection Report | Confidential", margin, pageHeight - 12);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth - margin - 45, pageHeight - 12);
  }

  const fileName = getReportFileName(analysis);
  
  // Reliable standard PDF output and download
  const pdfBlob = doc.output("blob");
  const blobUrl = typeof URL !== "undefined" && URL.createObjectURL ? URL.createObjectURL(pdfBlob) : null;

  if (autoDownload && typeof document !== "undefined" && blobUrl) {
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => {
      try {
        URL.revokeObjectURL(blobUrl);
      } catch {
        // ignore
      }
    }, 60000);
  } else if (autoDownload) {
    try {
      doc.save(fileName);
    } catch {
      // fallback
    }
  }

  let base64 = "";
  try {
    base64 = doc.output("datauristring");
  } catch {
    // optional
  }

  return {
    fileName,
    blob: pdfBlob,
    url: blobUrl,
    base64,
    doc,
    predictionLabel: report.predictionLabel,
    confidencePercent: report.confidencePercent,
  };
};
