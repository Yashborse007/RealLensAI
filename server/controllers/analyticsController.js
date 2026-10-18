import Analysis from "../models/Analysis.js";
import { findAnalysesByUser } from "../services/store/inMemoryMediaStore.js";

export const getDashboardAnalytics = async (req, res) => {
  try {
    const userId = String(req.user?.id || req.user?._id || "");
    let records = [];

    try {
      if (userId) {
        records = await Analysis.find({ userId }).sort({ createdAt: -1 }).lean();
      }
    } catch {
      records = [];
    }

    if (!records || records.length === 0) {
      records = findAnalysesByUser(userId);
    }

    const totalAnalyses = records.length;
    let realMediaCount = 0;
    let potentialDeepfakesCount = 0;
    let uncertainCount = 0;
    let processingCount = 0;
    let reportsGenerated = 0;

    let imageCount = 0;
    let videoCount = 0;
    let audioCount = 0;

    for (const r of records) {
      const pred = String(r.prediction || r.result || r.predictionLabel || "").toUpperCase();
      if (pred === "REAL" || pred === "AUTHENTIC") realMediaCount++;
      else if (pred === "FAKE" || pred === "MANIPULATED" || pred === "DEEPFAKE") potentialDeepfakesCount++;
      else uncertainCount++;

      const stat = String(r.status || "").toUpperCase();
      if (stat === "PROCESSING" || stat === "UPLOADED") processingCount++;

      if (r.reportPath || r.pdfBase64) reportsGenerated++;

      const mType = String(r.mediaType || "image").toLowerCase();
      if (mType === "video") videoCount++;
      else if (mType === "audio") audioCount++;
      else imageCount++;
    }

    return res.status(200).json({
      success: true,
      isSampleData: false,
      totalAnalyses,
      realMediaCount,
      potentialDeepfakesCount,
      uncertainMediaCount: uncertainCount,
      reportsGenerated,
      processingCount,
      weeklyGrowthRate: totalAnalyses > 0 ? "+100%" : "0%",
      mediaTypeBreakdown: [
        { name: "Image Forensics", value: imageCount, color: "#00f0ff" },
        { name: "Video Frames", value: videoCount, color: "#6366f1" },
        { name: "Audio Spectral", value: audioCount, color: "#a855f7" },
      ],
      authenticitySummary: [
        { name: "Authentic / Real", value: realMediaCount, color: "#10b981" },
        { name: "Deepfake / Manipulated", value: potentialDeepfakesCount, color: "#f43f5e" },
        { name: "Uncertain", value: uncertainCount, color: "#a16207" },
      ],
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: error.message || "Failed to load dashboard analytics.",
      isSampleData: false,
    });
  }
};

export const getDistributionAnalytics = async (req, res) => {
  try {
    const userId = String(req.user?.id || req.user?._id || "");
    let records = [];

    try {
      if (userId) {
        records = await Analysis.find({ userId }).sort({ createdAt: -1 }).lean();
      }
    } catch {
      records = [];
    }

    if (!records || records.length === 0) {
      records = findAnalysesByUser(userId);
    }

    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const dayMap = {};
    for (const d of days) {
      dayMap[d] = { name: d, images: 0, video: 0, audio: 0, deepfakes: 0 };
    }

    for (const r of records) {
      const date = new Date(r.createdAt || r.uploadedAt || Date.now());
      const dayName = days[date.getDay()];
      const mType = String(r.mediaType || "image").toLowerCase();
      const pred = String(r.prediction || r.result || r.predictionLabel || "").toUpperCase();

      if (mType === "video") dayMap[dayName].video++;
      else if (mType === "audio") dayMap[dayName].audio++;
      else dayMap[dayName].images++;

      if (pred === "FAKE" || pred === "MANIPULATED" || pred === "DEEPFAKE") {
        dayMap[dayName].deepfakes++;
      }
    }

    // Ordered Mon -> Sun
    const distribution = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((name) => dayMap[name]);

    return res.status(200).json(distribution);
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: error.message || "Failed to load distribution analytics.",
    });
  }
};
