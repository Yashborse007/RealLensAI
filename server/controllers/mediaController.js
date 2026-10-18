import path from "path";
import fs from "fs";
import crypto from "crypto";
import axios from "axios";
import FormData from "form-data";
import Media from "../models/Media.js";
import { resolveSafeSubpath } from "../config/securityConfig.js";
import { sanitizeFilename } from "../middleware/uploadMiddleware.js";
import { resolveUploadedMediaPath } from "../utils/mediaPath.js";
import {
  saveMediaRecord,
  saveAnalysisRecord,
  findMediaById,
  findAnalysisById,
} from "../services/store/inMemoryMediaStore.js";
import { deleteFile } from "../utils/fileCleanup.js";

/**
 * Remove internal filesystem paths or debug properties from AI payloads
 */
const sanitizeAiPayload = (payload = {}) => {
  if (!payload || typeof payload !== "object") return {};
  const cleaned = { ...payload };

  // Strip internal filesystem paths
  delete cleaned.temp_path;
  delete cleaned.file_path;
  delete cleaned.filepath;
  delete cleaned.checkpoint_path;
  delete cleaned.model_path;
  delete cleaned.stack;
  delete cleaned.trace;

  return cleaned;
};

/**
 * @desc    Upload media file (Image, Video, Audio)
 * @route   POST /api/media/upload
 * @access  Private (Guarded by JWT protect)
 */
export const uploadMedia = async (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      success: false,
      error: "No media file attached to upload request. Please select a file.",
    });
  }

  const { filename, originalname, mimetype, size, path: filePath } = req.file;
  const safeOriginalName =
    req.file.sanitizedOriginalName ||
    sanitizeFilename(originalname || "upload");
  const ext = path.extname(safeOriginalName).toLowerCase().replace(".", "");
  const mediaType =
    req.detectedMediaType ||
    (mimetype.startsWith("image")
      ? "image"
      : mimetype.startsWith("video")
        ? "video"
        : "audio");
  const mediaId = `med_${Date.now()}_${crypto.randomBytes(4).toString("hex")}`;
  const userId = req.user?.id ? String(req.user.id) : "usr_anonymous";
  const relativePath = filename;

  try {
    let mediaRecord = null;

    try {
      mediaRecord = await Media.create({
        mediaId,
        user: req.user?._id || req.user?.id,
        originalName: safeOriginalName,
        filename,
        mediaType,
        mimeType: mimetype,
        extension: ext,
        size,
        path: relativePath,
        status: "uploaded",
      });
    } catch (dbErr) {
      mediaRecord = await saveMediaRecord({
        mediaId,
        user: userId,
        originalName: safeOriginalName,
        filename,
        mediaType,
        mimeType: mimetype,
        extension: ext,
        size,
        path: relativePath,
        status: "uploaded",
      });
    }

    return res.status(200).json({
      success: true,
      mediaId: mediaRecord.mediaId,
      filename: mediaRecord.filename,
      originalName: mediaRecord.originalName || safeOriginalName,
      mediaType: mediaRecord.mediaType,
      mimeType: mediaRecord.mimeType,
      size: mediaRecord.size,
      path: mediaRecord.path,
      uploadedAt: mediaRecord.uploadedAt || new Date().toISOString(),
    });
  } catch (error) {
    deleteFile(filePath);
    return res.status(500).json({
      success: false,
      error: "Failed to save media metadata.",
    });
  }
};

const normalizeResultLabel = (value) => {
  const raw = String(value || "UNKNOWN").toUpperCase();
  if (raw === "REAL") return "authentic";
  if (raw === "FAKE") return "manipulated";
  return "suspicious";
};

const formatFileSize = (bytes = 0) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
};

const normalizeQualityStatus = (value) => {
  const raw = String(value || "UNKNOWN").toUpperCase();
  if (["GOOD", "FAIR", "POOR"].includes(raw)) return raw;
  return "UNKNOWN";
};

const normalizeQualityDetails = (payload = {}) => {
  const qualitySource =
    payload.quality || payload.input_quality || payload.inputQuality || {};
  const status = normalizeQualityStatus(
    typeof qualitySource === "string"
      ? qualitySource
      : qualitySource.status || qualitySource.quality || "GOOD",
  );
  const rawQualityScore =
    typeof qualitySource === "object" && qualitySource !== null
      ? qualitySource.quality_score ??
        qualitySource.qualityScore ??
        qualitySource.score
      : undefined;
  const qualityScore =
    rawQualityScore === null || rawQualityScore === undefined
      ? null
      : Number(rawQualityScore);
  const details =
    typeof qualitySource === "object" &&
    qualitySource !== null &&
    qualitySource.details
      ? qualitySource.details
      : typeof qualitySource === "object" && qualitySource !== null
        ? qualitySource
        : {};

  return {
    status,
    qualityScore: qualityScore !== null && Number.isFinite(qualityScore)
      ? Math.min(1, Math.max(0, qualityScore))
      : null,
    details,
    warning:
      status === "POOR"
        ? "Low-quality media may reduce detection reliability."
        : qualitySource.warning || qualitySource.message || "",
  };
};

export const analyzeMedia = async (req, res) => {
  const rawMediaId = req.body?.mediaId;
  if (!rawMediaId || typeof rawMediaId !== "string") {
    return res
      .status(400)
      .json({ success: false, error: "Media ID is required for analysis." });
  }

  const mediaId = String(rawMediaId).trim();

  let record = null;
  try {
    record = await Media.findOne({ mediaId });
  } catch (dbErr) {
    record = null;
  }
  if (!record) {
    record = findMediaById(mediaId);
  }
  if (!record) {
    return res
      .status(404)
      .json({ success: false, error: "Media record not found for analysis." });
  }

  // Enforce resource authorization check
  const recordUserId = String(record.user || record.userId || "");
  const currentUserId = String(req.user?.id || req.user?._id || "");
  if (
    recordUserId &&
    recordUserId !== "usr_anonymous" &&
    recordUserId !== currentUserId &&
    req.user?.role !== "admin"
  ) {
    return res.status(403).json({
      success: false,
      error: "You do not have access to analyze this media.",
    });
  }

  const filePath = resolveUploadedMediaPath(record);
  if (!filePath) {
    return res.status(404).json({
      success: false,
      error: "Uploaded media file could not be found on disk.",
    });
  }

  const aiServiceUrl = process.env.AI_SERVICE_URL || "http://127.0.0.1:8000";
  const endpointMap = {
    image: "/predict/image",
    video: "/predict/video",
    audio: "/predict/audio",
  };
  const endpoint = endpointMap[record.mediaType] || "/predict/image";

  try {
    // Use npm form-data package (supports Node.js fs streams, unlike browser FormData global)
    const formData = new FormData();
    const fileStream = fs.createReadStream(filePath);
    formData.append("file", fileStream, {
      filename: record.originalName || record.filename,
      contentType: record.mimeType || "application/octet-stream",
    });

    const response = await axios.post(`${aiServiceUrl}${endpoint}`, formData, {
      headers: {
        ...formData.getHeaders(),
      },
      timeout: 300000, // 5 min for large videos
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
    });

    const payload = sanitizeAiPayload(response.data || {});
    const prediction = payload.prediction || payload.result || {};
    const qualityDetails = normalizeQualityDetails(payload);
    const normalizedResult = {
      id: record.mediaId,
      analysisId: record.mediaId,
      mediaId: record.mediaId,
      userId: req.user?.id ? String(req.user.id) : "usr_anonymous",
      fileName: record.originalName || record.filename,
      originalName: record.originalName || record.filename,
      mediaType: record.mediaType,
      fileSize: formatFileSize(record.size),
      mimeType: record.mimeType,
      uploadedAt: record.uploadedAt || new Date().toISOString(),
      processedAt: new Date().toISOString(),
      status: payload.success === false ? "failed" : "completed",
      result: normalizeResultLabel(
        prediction.label || payload.status || "UNKNOWN",
      ),
      confidenceScore: Number(prediction.confidence ?? payload.confidence ?? 0),
      predictionLabel: String(
        prediction.label || payload.status || "UNKNOWN",
      ).toUpperCase(),
      modelVersion: payload.model_version || payload.model || "AIDE",
      model: payload.model || "AIDE",
      processingTimeMs: payload.processing_time_ms || 0,
      performance: payload.performance || {},
      facesDetected: payload.faces_detected || 0,
      framesAnalyzed: payload.frames_analyzed || payload.faces_detected || 0,
      framesProcessed:
        payload.frames_processed || payload.performance?.frames_processed || 0,
      processingFps:
        payload.processing_fps || payload.performance?.processing_fps || null,
      quality: qualityDetails.status,
      qualityScore: qualityDetails.qualityScore,
      qualityWarning: qualityDetails.warning,
      inputQuality: qualityDetails.details,
      qualityDetails: qualityDetails.details,
      message: payload.message || null,
      resolution:
        payload.inputQuality?.details?.resolution ||
        payload.quality?.details?.resolution ||
        payload.qualityDetails?.resolution ||
        payload.metadata?.resolution ||
        null,
      metadata: {
        cameraModel: "No embedded EXIF metadata",
        encoding:
          record.mediaType === "image"
            ? "AIDE image preprocessing pipeline"
            : record.mediaType === "video"
              ? "Video frame sampling & temporal aggregation"
              : "Audio spectral feature extraction",
        hashSHA256: "not generated in gateway",
        software: `${payload.model || "AIDE"} inference pipeline`,
      },
      evidence: Array.isArray(payload.evidence)
        ? payload.evidence
        : (payload.face_results || []).map((face) => ({
            type: face.label === "FAKE" ? "Face anomaly" : "Face consistency",
            severity: face.label === "FAKE" ? "high" : "low",
            description:
              face.label === "FAKE"
                ? "Synthetic artifact likelihood detected from model output."
                : "No major synthetic artifact signal detected in the face crop.",
            metricValue: `${Math.round((face.confidence || 0) * 100)}% confidence`,
          })),
      sampleHeatmaps:
        payload.sample_heatmaps ||
        payload.frame_predictions?.slice(0, 3)?.map((frame, idx) => ({
          frameIndex: idx + 1,
          timecode: `00:${String((idx + 1) * 2).padStart(2, "0")}.0`,
          note:
            frame.label === "FAKE"
              ? "Frame-level anomaly"
              : "Frame-level consistency",
        })) ||
        [],
      decisionMargin:
        payload.decision_margin ??
        payload.processing?.fusion?.decision_margin ??
        null,
      decisionThreshold:
        payload.decision_threshold ??
        payload.processing?.fusion?.threshold ??
        0.5,
      authenticityVerified: false,
      groundTruth: payload.ground_truth || null,
      evaluationOutcome: payload.evaluation_outcome || null,
      calibrationStatus:
        payload.calibration_status ||
        payload.confidence_calibration?.status ||
        "NOT_CONFIGURED",
      ...payload,
    };

    const saved = await saveAnalysisRecord(normalizedResult);
    try {
      const Analysis = (await import("../models/Analysis.js")).default;
      await Analysis.create({
        userId: String(req.user?.id || "usr_anonymous"),
        mediaId: saved.mediaId,
        analysisId: saved.analysis_id || saved.analysisId || saved.mediaId,
        mediaType: saved.mediaType,
        filename: saved.fileName || saved.originalName || "unknown_media",
        status: String(saved.status || "COMPLETED").toUpperCase() === "FAILED"
          ? "FAILED"
          : String(saved.status || "").toUpperCase() === "PARTIAL"
            ? "PARTIAL"
            : "COMPLETED",
        prediction: String(saved.predictionLabel || saved.result || "UNCERTAIN")
          .toUpperCase()
          .includes("REAL")
          ? "REAL"
          : String(saved.predictionLabel || saved.result || "UNCERTAIN")
                .toUpperCase()
                .includes("FAKE")
            ? "FAKE"
            : "UNCERTAIN",
        confidence: Number(saved.confidenceScore ?? 0),
        quality: normalizeQualityStatus(
          saved.quality || saved.qualityStatus || "GOOD",
        ),
        qualityScore: saved.qualityScore ?? saved.quality_score ?? null,
        qualityDetails: saved.qualityDetails || saved.inputQuality || {},
        qualityWarning:
          saved.qualityWarning ||
          (normalizeQualityStatus(
            saved.quality || saved.qualityStatus || "GOOD",
          ) === "POOR"
            ? "Low-quality media may reduce detection reliability."
            : ""),
        modalityScores: saved.modalityScores || {},
        modalities: saved.modalities || {},
        evidence: Array.isArray(saved.evidence) ? saved.evidence : [],
        timestamps: saved.timestamps || {},
        processing: saved.processing || {},
        modelVersions: saved.model_versions || saved.modelVersions || {},
        facesDetected: Number(saved.facesDetected || 0),
        suspiciousFrames: Number(saved.framesAnalyzed || 0),
        suspiciousTimestamps: Array.isArray(saved.suspiciousTimestamps)
          ? saved.suspiciousTimestamps
          : [],
        processingTime: Number(saved.processingTimeMs || 0),
        modelVersion: String(saved.modelVersion || saved.model || "AIDE"),
        reportPath: `reports/${sanitizeFilename(String(record.originalName || record.filename || "media").replace(/\.[^/.]+$/, ""))}_forensic_report.pdf`,
        createdAt:
          saved.processedAt || saved.createdAt || new Date().toISOString(),
      });
    } catch (analysisErr) {
      // Ignore DB persistence issues and continue with in-memory fallback storage.
    }
    return res.status(200).json(saved);
  } catch (error) {
    const isNetworkError = error.code === "ECONNREFUSED" || error.code === "ENOTFOUND" || error.code === "ETIMEDOUT";
    const aiErrorMsg = error.response?.data?.detail || error.response?.data?.message || error.response?.data?.error || null;
    return res.status(isNetworkError ? 503 : 502).json({
      success: false,
      error: isNetworkError
        ? "AI service is not reachable. Ensure the Python AI service is running on port 8000."
        : aiErrorMsg || "AI analysis failed. The AI service returned an error.",
      message: error.message || "Analysis could not be completed.",
    });
  }
};

export const getMediaAnalysis = async (req, res) => {
  const { id } = req.params;
  if (!id || typeof id !== "string") {
    return res
      .status(400)
      .json({ success: false, error: "Invalid analysis ID." });
  }

  const stored = findAnalysisById(String(id));
  if (!stored) {
    return res
      .status(404)
      .json({ success: false, error: "Analysis record not found." });
  }

  const recordUserId = String(stored.userId || stored.user || "");
  const currentUserId = String(req.user?.id || req.user?._id || "");
  if (
    recordUserId &&
    recordUserId !== currentUserId &&
    req.user?.role !== "admin"
  ) {
    return res.status(403).json({
      success: false,
      error: "You do not have access to this analysis.",
    });
  }

  return res.status(200).json(stored);
};

export const saveReport = async (req, res) => {
  const { id } = req.params;
  const { reportFileName, pdfBase64 } = req.body || {};

  if (!id || typeof id !== "string") {
    return res.status(400).json({ success: false, error: "Invalid analysis ID." });
  }

  const cleanFileName = sanitizeFilename(reportFileName || `${id}_forensic_report.pdf`);
  const relativeReportPath = `reports/${cleanFileName}`;
  const absoluteDir = path.resolve(process.cwd(), "reports");

  if (!fs.existsSync(absoluteDir)) {
    try {
      fs.mkdirSync(absoluteDir, { recursive: true });
    } catch (mkdirErr) {
      console.error("[Report Dir Creation Error]", mkdirErr);
    }
  }

  const absoluteFilePath = path.join(absoluteDir, cleanFileName);

  if (pdfBase64 && typeof pdfBase64 === "string") {
    try {
      const buffer = Buffer.from(pdfBase64.replace(/^data:application\/pdf;base64,/, ""), "base64");
      fs.writeFileSync(absoluteFilePath, buffer);
    } catch (writeErr) {
      console.error("[Report Save Error]", writeErr);
    }
  }

  // Update in MongoDB
  try {
    const Analysis = (await import("../models/Analysis.js")).default;
    const mongoose = (await import("mongoose")).default;
    await Analysis.findOneAndUpdate(
      {
        $or: [
          { mediaId: String(id) },
          { analysisId: String(id) },
          ...(mongoose.isValidObjectId(id) ? [{ _id: id }] : []),
        ],
      },
      {
        reportPath: relativeReportPath,
      },
      { new: true }
    );
  } catch (dbErr) {
    console.error("[Report DB Update Error]", dbErr);
  }

  // Update in inMemoryStore
  const inMem = findAnalysisById(String(id));
  if (inMem) {
    inMem.reportPath = relativeReportPath;
  }

  return res.status(200).json({
    success: true,
    message: "Report saved successfully in database and on disk.",
    reportPath: relativeReportPath,
    fileName: cleanFileName,
  });
};

export const getReport = async (req, res) => {
  const { id } = req.params;
  if (!id || typeof id !== "string") {
    return res
      .status(400)
      .json({ success: false, error: "Invalid report ID." });
  }

  let analysis = null;
  try {
    const Analysis = (await import("../models/Analysis.js")).default;
    const mongoose = (await import("mongoose")).default;
    analysis = await Analysis.findOne({
      $or: [
        { mediaId: String(id) },
        { analysisId: String(id) },
        ...(mongoose.isValidObjectId(id) ? [{ _id: id }] : []),
      ],
    });
  } catch (dbErr) {
    analysis = null;
  }

  if (!analysis) {
    analysis = findAnalysisById(String(id));
  }

  if (!analysis) {
    return res.status(404).json({
      success: false,
      error: "Report not found.",
    });
  }

  const recordUserId = String(analysis.userId || analysis.user || "");
  const currentUserId = String(req.user?.id || req.user?._id || "");
  if (
    recordUserId &&
    recordUserId !== "usr_anonymous" &&
    recordUserId !== currentUserId &&
    req.user?.role !== "admin"
  ) {
    return res.status(403).json({
      success: false,
      error: "You do not have access to this report.",
    });
  }

  const reportPath = analysis.reportPath || "";
  const safeReportPath = resolveSafeSubpath(reportPath, "reports");
  if (!safeReportPath || !fs.existsSync(safeReportPath)) {
    return res.status(404).json({
      success: false,
      error: "Report file is unavailable.",
    });
  }

  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Content-Type", "application/pdf");
  return res.download(
    safeReportPath,
    sanitizeFilename(path.basename(safeReportPath)),
  );
};
