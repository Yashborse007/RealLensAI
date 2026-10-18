import User from "../models/User.js";
import Analysis from "../models/Analysis.js";

const normalizePrediction = (value) => {
  const raw = String(value || "UNCERTAIN").toUpperCase();
  if (raw === "REAL" || raw === "AUTHENTIC") return "REAL";
  if (raw === "FAKE" || raw === "MANIPULATED" || raw === "DEEPFAKE")
    return "FAKE";
  return "UNCERTAIN";
};

const normalizeMediaType = (value) => {
  const raw = String(value || "").toLowerCase();
  if (["image", "video", "audio"].includes(raw)) return raw;
  return "image";
};

const computeModelPerformance = (analyses) => {
  const buckets = new Map();

  for (const analysis of analyses) {
    const modelVersion = analysis.modelVersion || "AIDE";
    const bucket = buckets.get(modelVersion) || {
      modelVersion,
      analyses: 0,
      totalConfidence: 0,
      totalProcessingTimeMs: 0,
      real: 0,
      fake: 0,
      uncertain: 0,
      failed: 0,
    };

    bucket.analyses += 1;
    bucket.totalConfidence += Number(analysis.confidence ?? 0);
    bucket.totalProcessingTimeMs += Number(analysis.processingTime ?? 0);

    const prediction = normalizePrediction(
      analysis.prediction || analysis.result,
    );
    if (prediction === "REAL") bucket.real += 1;
    if (prediction === "FAKE") bucket.fake += 1;
    if (prediction === "UNCERTAIN") bucket.uncertain += 1;
    if (String(analysis.status || "").toUpperCase() === "FAILED")
      bucket.failed += 1;

    buckets.set(modelVersion, bucket);
  }

  return [...buckets.values()].map((entry) => ({
    modelVersion: entry.modelVersion,
    analysisCount: entry.analyses,
    averageConfidence: entry.analyses
      ? Number((entry.totalConfidence / entry.analyses).toFixed(3))
      : 0,
    avgProcessingTimeMs: entry.analyses
      ? Math.round(entry.totalProcessingTimeMs / entry.analyses)
      : 0,
    realRate: entry.analyses
      ? Number((entry.real / entry.analyses).toFixed(3))
      : 0,
    fakeRate: entry.analyses
      ? Number((entry.fake / entry.analyses).toFixed(3))
      : 0,
    uncertainRate: entry.analyses
      ? Number((entry.uncertain / entry.analyses).toFixed(3))
      : 0,
    failedRate: entry.analyses
      ? Number((entry.failed / entry.analyses).toFixed(3))
      : 0,
  }));
};

const buildChartSeries = (analyses) => {
  const analysisVolume = [];
  const predictionDistribution = [
    { name: "REAL", value: 0 },
    { name: "FAKE", value: 0 },
    { name: "UNCERTAIN", value: 0 },
  ];
  const mediaTypeDistribution = [
    { name: "Image", value: 0 },
    { name: "Video", value: 0 },
    { name: "Audio", value: 0 },
  ];
  const processingTime = [];

  const usageByDay = new Map();
  const processingByDay = new Map();

  for (const item of analyses) {
    const prediction = normalizePrediction(item.prediction || item.result);
    if (prediction === "REAL") predictionDistribution[0].value += 1;
    if (prediction === "FAKE") predictionDistribution[1].value += 1;
    if (prediction === "UNCERTAIN") predictionDistribution[2].value += 1;

    const mediaType = normalizeMediaType(item.mediaType);
    if (mediaType === "image") mediaTypeDistribution[0].value += 1;
    if (mediaType === "video") mediaTypeDistribution[1].value += 1;
    if (mediaType === "audio") mediaTypeDistribution[2].value += 1;

    const created = new Date(item.createdAt || Date.now());
    const dayKey = created.toISOString().slice(0, 10);
    usageByDay.set(dayKey, (usageByDay.get(dayKey) || 0) + 1);
    processingByDay.set(
      dayKey,
      (processingByDay.get(dayKey) || 0) + Number(item.processingTime || 0),
    );
  }

  const sortedDays = [...usageByDay.entries()]
    .sort(([a], [b]) => new Date(a) - new Date(b))
    .slice(-7);
  for (const [dayKey, count] of sortedDays) {
    analysisVolume.push({
      name: new Date(dayKey).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      }),
      total: count,
      averageMs: Math.round((processingByDay.get(dayKey) || 0) / count),
    });
    processingTime.push({
      name: new Date(dayKey).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      }),
      avgMs: Math.round((processingByDay.get(dayKey) || 0) / count),
    });
  }

  if (analysisVolume.length === 0) {
    analysisVolume.push({ name: "No data", total: 0, averageMs: 0 });
    processingTime.push({ name: "No data", avgMs: 0 });
  }

  return {
    analysisVolume,
    predictionDistribution,
    mediaTypeDistribution,
    processingTime,
  };
};

export const getAdminOverview = async (req, res) => {
  try {
    const [userDocs, analysisDocs] = await Promise.all([
      User.find({}).select("-passwordHash").sort({ createdAt: -1 }).lean(),
      Analysis.find({}).sort({ createdAt: -1 }).lean(),
    ]);

    const totalUsers = userDocs.length;
    const totalAnalyses = analysisDocs.length;
    const realPredictions = analysisDocs.filter(
      (item) => normalizePrediction(item.prediction || item.result) === "REAL",
    ).length;
    const fakePredictions = analysisDocs.filter(
      (item) => normalizePrediction(item.prediction || item.result) === "FAKE",
    ).length;
    const uncertainPredictions = analysisDocs.filter(
      (item) =>
        normalizePrediction(item.prediction || item.result) === "UNCERTAIN",
    ).length;
    const imageAnalyses = analysisDocs.filter(
      (item) => normalizeMediaType(item.mediaType) === "image",
    ).length;
    const videoAnalyses = analysisDocs.filter(
      (item) => normalizeMediaType(item.mediaType) === "video",
    ).length;
    const audioAnalyses = analysisDocs.filter(
      (item) => normalizeMediaType(item.mediaType) === "audio",
    ).length;
    const failedAnalyses = analysisDocs.filter(
      (item) => String(item.status || "").toUpperCase() === "FAILED",
    ).length;
    const totalProcessingTime = analysisDocs.reduce(
      (sum, item) => sum + Number(item.processingTime || 0),
      0,
    );
    const averageProcessingTimeMs = totalAnalyses
      ? Math.round(totalProcessingTime / totalAnalyses)
      : 0;

    const charts = buildChartSeries(analysisDocs);
    const modelPerformance = computeModelPerformance(analysisDocs);

    return res.status(200).json({
      success: true,
      stats: {
        totalUsers,
        totalAnalyses,
        realPredictions,
        fakePredictions,
        uncertainPredictions,
        imageAnalyses,
        videoAnalyses,
        audioAnalyses,
        failedAnalyses,
        averageProcessingTimeMs,
        modelVersions: [
          ...new Set(
            (analysisDocs || []).map((item) => item.modelVersion || "AIDE"),
          ),
        ],
        modelPerformance,
      },
      charts,
      users: userDocs.slice(0, 8).map((u) => ({
        id: u._id || u.id,
        name: u.name,
        email: u.email,
        role: u.role,
        createdAt: u.createdAt,
      })),
      recentAnalyses: analysisDocs.slice(0, 8).map((a) => ({
        id: a._id || a.id,
        filename: a.filename,
        mediaType: a.mediaType,
        prediction: normalizePrediction(a.prediction || a.result),
        confidence: Number(a.confidence ?? 0),
        status: a.status,
        modelVersion: a.modelVersion || "AIDE",
        createdAt: a.createdAt,
      })),
    });
  } catch (_error) {
    return res.status(500).json({
      success: false,
      error: "Unable to compile admin dashboard metrics.",
    });
  }
};

export const getAdminUsers = async (req, res) => {
  try {
    const users = await User.find({})
      .select("-passwordHash")
      .sort({ createdAt: -1 })
      .lean();
    return res.status(200).json({
      success: true,
      total: users.length,
      data: users.map((user) => ({
        id: user._id || user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt,
      })),
    });
  } catch (_error) {
    return res
      .status(500)
      .json({ success: false, error: "Unable to load user list." });
  }
};

export const getAdminAnalyses = async (req, res) => {
  try {
    const analyses = await Analysis.find({}).sort({ createdAt: -1 }).lean();
    return res.status(200).json({
      success: true,
      total: analyses.length,
      data: analyses.map((item) => ({
        id: item._id || item.id,
        filename: item.filename,
        mediaType: item.mediaType,
        prediction: normalizePrediction(item.prediction || item.result),
        status: item.status,
        confidence: Number(item.confidence ?? 0),
        modelVersion: item.modelVersion || "AIDE",
        processingTime: Number(item.processingTime || 0),
        createdAt: item.createdAt,
      })),
    });
  } catch (_error) {
    return res
      .status(500)
      .json({ success: false, error: "Unable to load analysis records." });
  }
};

export const getAdminModels = async (req, res) => {
  try {
    const analyses = await Analysis.find({}).lean();
    const modelPerformance = computeModelPerformance(analyses);

    return res.status(200).json({
      success: true,
      data: modelPerformance,
    });
  } catch (_error) {
    return res
      .status(500)
      .json({ success: false, error: "Unable to load model information." });
  }
};
