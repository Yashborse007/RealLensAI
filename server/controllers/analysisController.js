import Analysis from "../models/Analysis.js";
import {
  saveAnalysisRecord,
  findAnalysisById,
  findAnalysesByUser,
  deleteAnalysisRecord,
} from "../services/store/inMemoryMediaStore.js";

const normalizePrediction = (value) => {
  const raw = String(value || "UNCERTAIN").toUpperCase();
  if (raw === "REAL" || raw === "AUTHENTIC") return "REAL";
  if (raw === "FAKE" || raw === "MANIPULATED" || raw === "DEEPFAKE")
    return "FAKE";
  return "UNCERTAIN";
};

const normalizeStatus = (value) => {
  const raw = String(value || "UPLOADED").toUpperCase();
  if (["UPLOADED", "PROCESSING", "COMPLETED", "PARTIAL", "FAILED"].includes(raw))
    return raw;
  return "UPLOADED";
};

const normalizeQuality = (value) => {
  const raw = String(value || "UNKNOWN").toUpperCase();
  if (["GOOD", "FAIR", "POOR"].includes(raw)) return raw;
  return "UNKNOWN";
};

const serializeListItem = (analysisDoc) => {
  const source =
    analysisDoc && analysisDoc.toJSON ? analysisDoc.toJSON() : analysisDoc;
  if (!source) return null;

  const result = {
    ...source,
    id: String(
      source.id || source._id || source.analysisId || source.mediaId || "",
    ),
    prediction: normalizePrediction(
      source.prediction || source.result || "UNCERTAIN",
    ),
    status: normalizeStatus(source.status || "UPLOADED"),
    confidence: Number(source.confidence ?? source.confidenceScore ?? 0),
    quality: normalizeQuality(
      source.quality || source.qualityStatus || "UNKNOWN",
    ),
    qualityScore:
      source.qualityScore === null
        ? null
        : Number(
            source.qualityScore ??
              source.quality_score ??
              source.inputQuality?.qualityScore ??
              0,
          ),
    qualityDetails: source.qualityDetails || source.inputQuality || {},
    qualityWarning:
      source.qualityWarning ||
      (source.quality === "POOR" || source.qualityStatus === "POOR"
        ? "Low-quality media may reduce detection reliability."
        : ""),
    createdAt: source.createdAt || new Date().toISOString(),
  };

  // Strip any internal server filesystem paths
  delete result.filePath;
  delete result.temp_path;
  delete result.checkpoint_path;

  if (result.modelVersion === undefined) {
    result.modelVersion = "AIDE";
  }

  return result;
};

export const createAnalysis = async (req, res) => {
  const body = req.body || {};
  const safeReportPath =
    typeof body.reportPath === "string"
      ? body.reportPath.replace(/\0/g, "").replace(/\.\./g, "").trim()
      : "";

  const record = {
    userId: String(req.user.id),
    mediaId:
      body.mediaId && typeof body.mediaId === "string"
        ? String(body.mediaId).slice(0, 100)
        : `med_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
    analysisId:
      typeof body.analysis_id === "string"
        ? body.analysis_id.slice(0, 100)
        : typeof body.analysisId === "string"
          ? body.analysisId.slice(0, 100)
          : "",
    mediaType: ["image", "video", "audio"].includes(body.mediaType)
      ? body.mediaType
      : "image",
    filename:
      body.filename && typeof body.filename === "string"
        ? String(body.filename).slice(0, 150)
        : body.fileName && typeof body.fileName === "string"
          ? String(body.fileName).slice(0, 150)
          : "unknown_media",
    status: normalizeStatus(body.status || "COMPLETED"),
    prediction: normalizePrediction(
      body.prediction || body.result || "UNCERTAIN",
    ),
    confidence: Math.max(0, Math.min(1, Number(body.confidence ?? body.confidenceScore ?? 0))),
    quality: normalizeQuality(body.quality || body.qualityStatus || "UNKNOWN"),
    qualityScore:
      body.qualityScore === null || body.quality_score === null
        ? null
        : Math.max(
            0,
            Math.min(
              1,
              Number(
                body.qualityScore ??
                  body.quality_score ??
                  body.inputQuality?.qualityScore ??
                  body.qualityDetails?.qualityScore ??
                  0,
              ),
            ),
          ),
    qualityDetails: body.qualityDetails || body.inputQuality || {},
    qualityWarning:
      body.qualityWarning ||
      (normalizeQuality(body.quality || body.qualityStatus || "UNKNOWN") ===
      "POOR"
        ? "Low-quality media may reduce detection reliability."
        : ""),
    modalityScores: body.modalityScores || {},
    modalities: body.modalities || {},
    evidence: Array.isArray(body.evidence) ? body.evidence : [],
    timestamps: body.timestamps || {},
    processing: body.processing || {},
    modelVersions: body.model_versions || body.modelVersions || {},
    facesDetected: Math.max(0, Number(body.facesDetected || 0)),
    suspiciousFrames: Math.max(0, Number(body.suspiciousFrames || body.framesAnalyzed || 0)),
    suspiciousTimestamps: Array.isArray(body.suspiciousTimestamps)
      ? body.suspiciousTimestamps.slice(0, 50).map((t) => String(t).slice(0, 20))
      : [],
    processingTime: Math.max(0, Number(body.processingTime ?? body.processingTimeMs ?? 0)),
    modelVersion:
      body.modelVersion && typeof body.modelVersion === "string"
        ? String(body.modelVersion).slice(0, 50)
        : "AIDE",
    reportPath: safeReportPath,
    createdAt: new Date().toISOString(),
  };

  try {
    const saved = await Analysis.create(record);
    return res.status(201).json(serializeListItem(saved));
  } catch (dbErr) {
    const fallback = await saveAnalysisRecord(record);
    return res.status(201).json(serializeListItem(fallback));
  }
};

export const getAnalyses = async (req, res) => {
  const {
    mediaType,
    result,
    sort = "newest",
    search = "",
    page = 1,
    limit = 10,
  } = req.query;
  const userId = String(req.user.id);

  let records = [];
  try {
    records = await Analysis.find({ userId }).sort({ createdAt: -1 }).lean();
  } catch (dbErr) {
    records = findAnalysesByUser(userId);
  }

  const cleanSearch = typeof search === "string" ? search.slice(0, 100).toLowerCase() : "";

  let filtered = records.filter((item) => {
    const fileName = String(item.filename || item.fileName || "").toLowerCase();
    const recordId = String(
      item.id || item._id || item.mediaId || "",
    ).toLowerCase();
    const matchesSearch =
      !cleanSearch ||
      fileName.includes(cleanSearch) ||
      recordId.includes(cleanSearch);
    const matchesMedia =
      !mediaType ||
      mediaType === "all" ||
      String(item.mediaType).toLowerCase() === String(mediaType).toLowerCase();
    const normalizedResult = normalizePrediction(
      item.prediction || item.result || "UNCERTAIN",
    ).toLowerCase();
    const matchesResult =
      !result ||
      result === "all" ||
      normalizedResult === String(result).toLowerCase();
    return matchesSearch && matchesMedia && matchesResult;
  });

  filtered = filtered.sort((a, b) => {
    const left = new Date(a.createdAt || a.uploadedAt || 0).getTime();
    const right = new Date(b.createdAt || b.uploadedAt || 0).getTime();
    return sort === "oldest" ? left - right : right - left;
  });

  // Strict page and limit bounds to prevent DoS
  const currentPage = Math.max(1, Number(page) || 1);
  const pageSize = Math.min(100, Math.max(1, Number(limit) || 10));
  const total = filtered.length;
  const start = (currentPage - 1) * pageSize;
  const paged = filtered.slice(start, start + pageSize);

  return res.status(200).json({
    success: true,
    total,
    page: currentPage,
    limit: pageSize,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
    data: paged.map(serializeListItem),
  });
};

export const getAnalysisById = async (req, res) => {
  const { id } = req.params;
  if (!id || typeof id !== "string") {
    return res.status(400).json({ success: false, error: "Invalid ID parameter." });
  }

  const userId = String(req.user.id);
  const cleanId = String(id).trim();

  let record = null;
  try {
    record = await Analysis.findOne({ _id: cleanId, userId }).lean();
  } catch (dbErr) {
    record = null;
  }
  if (!record) {
    try {
      record = await Analysis.findOne({ mediaId: cleanId, userId }).lean();
    } catch (dbErr) {
      record = null;
    }
  }
  if (!record) {
    try {
      record = await Analysis.findOne({ analysisId: cleanId, userId }).lean();
    } catch (dbErr) {
      record = null;
    }
  }
  if (!record) {
    record = findAnalysisById(cleanId);
  }

  if (!record) {
    record = findAnalysisById(cleanId);
  }

  if (!record || String(record.userId || record.user) !== userId) {
    return res
      .status(404)
      .json({ success: false, error: "Analysis not found for this user." });
  }

  return res.status(200).json(serializeListItem(record));
};

export const deleteAnalysis = async (req, res) => {
  const { id } = req.params;
  if (!id || typeof id !== "string") {
    return res.status(400).json({ success: false, error: "Invalid ID parameter." });
  }

  const userId = String(req.user.id);
  const cleanId = String(id).trim();

  let deleted = false;
  try {
    const result = await Analysis.findOneAndDelete({ _id: cleanId, userId });
    deleted = !!result;
  } catch (dbErr) {
    const result = deleteAnalysisRecord(userId, cleanId);
    deleted = !!result;
  }

  if (!deleted) {
    return res
      .status(404)
      .json({ success: false, error: "Analysis not found for this user." });
  }

  return res
    .status(200)
    .json({ success: true, message: "Analysis deleted successfully." });
};
