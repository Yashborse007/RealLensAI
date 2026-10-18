import axios from "axios";
import {
  MOCK_DASHBOARD_STATS,
  MOCK_RECENT_ANALYSES,
  MOCK_DISTRIBUTION_DATA,
  MOCK_USER_PROFILE,
} from "../mock/data";

const asSampleData = (data) => {
  const sample = Array.isArray(data) ? [...data] : { ...data };
  sample.isSampleData = true;
  return sample;
};

/**
 * Central API base URL.
 * In dev: Vite proxy handles '/api' → localhost:5000
 * In production: VITE_API_BASE_URL should be set to the full backend URL.
 */
const API_BASE = import.meta.env.DEV
  ? "/api"
  : import.meta.env.VITE_API_BASE_URL || "/api";

// Create base Axios instance
const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
  withCredentials: false,
});

export const recordClientPerformance = (
  name,
  startedAt,
  endedAt = performance.now(),
) => {
  if (
    typeof performance === "undefined" ||
    typeof performance.measure !== "function"
  )
    return;
  try {
    performance.measure(name, { start: startedAt, end: endedAt });
  } catch {
    // Ignore unsupported or invalid performance entries.
  }
};

// Attach performance start time and auth token on every request
apiClient.interceptors.request.use((config) => {
  config.performanceStartedAt = performance.now();

  // Always attach the auth token if available
  const token = localStorage.getItem("reallens_auth_token");
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }

  return config;
});

const recordApiResponseTime = (config) => {
  if (config?.performanceStartedAt !== undefined) {
    try {
      const path = new URL(config.url || "", window.location.origin).pathname;
      recordClientPerformance(
        `api:${String(config.method || "get").toUpperCase()}:${path}`,
        config.performanceStartedAt,
      );
    } catch {
      // Ignore URL parse errors
    }
  }
};

apiClient.interceptors.response.use(
  (response) => {
    recordApiResponseTime(response.config);
    return response;
  },
  (error) => {
    recordApiResponseTime(error.config);

    // Auto-logout on 401 Unauthorized (expired / invalid token)
    if (error.response?.status === 401) {
      const token = localStorage.getItem("reallens_auth_token");
      if (token) {
        // Clear stale credentials and reload to login page
        localStorage.removeItem("reallens_auth_token");
        delete axios.defaults.headers.common["Authorization"];
        // Dispatch a custom event so AuthContext can react if needed
        window.dispatchEvent(new CustomEvent("reallens:auth:expired"));
      }
    }

    return Promise.reject(error);
  },
);

// ─── Helper ────────────────────────────────────────────────────────────────

const getAuthHeaders = () => {
  const token = localStorage.getItem("reallens_auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// ─── Health Check API Calls ────────────────────────────────────────────────

/**
 * Check Node.js backend health
 */
export const checkBackendHealth = async () => {
  try {
    const res = await apiClient.get("/health");
    return { status: "online", data: res.data };
  } catch (err) {
    return { status: "offline", error: err.message };
  }
};

/**
 * Check Python AI service health (proxied through backend)
 */
export const checkAiHealth = async () => {
  try {
    const res = await apiClient.get("/health/ai");
    return { status: "online", data: res.data };
  } catch (err) {
    return { status: "offline", error: err.message };
  }
};

// ─── Upload Media ──────────────────────────────────────────────────────────

/**
 * Upload Media File API Call
 * POST /api/media/upload
 */
export const uploadMediaFile = async (file, onProgress) => {
  const uploadStartedAt = performance.now();
  const formData = new FormData();
  formData.append("file", file);

  const token = localStorage.getItem("reallens_auth_token");
  const headers = {
    "Content-Type": "multipart/form-data",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await apiClient.post("/media/upload", formData, {
      headers,
      timeout: 60000, // 60 seconds for upload
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total,
          );
          onProgress(percent);
        }
      },
    });
    recordClientPerformance("upload-duration", uploadStartedAt);
    return res.data;
  } catch (err) {
    recordClientPerformance("upload-duration", uploadStartedAt);
    const message =
      err.response?.data?.error ||
      err.response?.data?.message ||
      err.message ||
      "Media file upload failed.";
    throw new Error(message);
  }
};

// ─── Dashboard & Analytics ─────────────────────────────────────────────────

export const getDashboardStats = async () => {
  try {
    const res = await apiClient.get("/analytics/dashboard");
    return res.data;
  } catch (err) {
    return asSampleData(MOCK_DASHBOARD_STATS);
  }
};

export const getDistributionData = async () => {
  try {
    const res = await apiClient.get("/analytics/distribution");
    return res.data;
  } catch (err) {
    return asSampleData(MOCK_DISTRIBUTION_DATA);
  }
};

// ─── Analysis API Calls ────────────────────────────────────────────────────

export const getRecentAnalyses = async () => {
  try {
    const res = await apiClient.get("/analyses", { headers: getAuthHeaders() });
    const payload = res.data?.data || res.data || [];
    return Array.isArray(payload) ? payload : [];
  } catch (err) {
    return asSampleData(MOCK_RECENT_ANALYSES);
  }
};

export const getAnalysisById = async (id) => {
  const res = await apiClient.get(`/analyses/${id}`, {
    headers: getAuthHeaders(),
  });
  return res.data?.data || res.data || null;
};

export const getUserAnalyses = async ({
  page = 1,
  limit = 10,
  mediaType = "all",
  result = "all",
  sort = "newest",
  search = "",
} = {}) => {
  try {
    const params = new URLSearchParams({
      page,
      limit,
      mediaType,
      result,
      sort,
      search,
    });
    const res = await apiClient.get(`/analyses?${params.toString()}`, {
      headers: getAuthHeaders(),
    });
    return res.data || { data: [], total: 0, page, limit, totalPages: 1 };
  } catch (err) {
    return {
      data: asSampleData(MOCK_RECENT_ANALYSES),
      total: MOCK_RECENT_ANALYSES.length,
      page,
      limit,
      totalPages: 1,
      isSampleData: true,
    };
  }
};

export const deleteAnalysisById = async (id) => {
  try {
    const res = await apiClient.delete(`/analyses/${id}`, {
      headers: getAuthHeaders(),
    });
    return res.data;
  } catch (err) {
    return { success: false, error: err.message || "Delete failed." };
  }
};

/**
 * Trigger AI analysis on an already-uploaded media file.
 * POST /api/media/analyze
 */
export const analyzeMediaFile = async (mediaId, onProgress) => {
  const token = localStorage.getItem("reallens_auth_token");
  const headers = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const res = await apiClient.post(
      "/media/analyze",
      { mediaId },
      {
        headers,
        timeout: 300000, // 5 minutes for AI analysis
      },
    );
    return res.data;
  } catch (err) {
    const message =
      err.response?.data?.error ||
      err.response?.data?.message ||
      err.message ||
      "Media analysis failed.";
    throw new Error(message);
  }
};

export const submitMediaAnalysis = async (file, mediaType, onProgress) => {
  return await uploadMediaFile(file, onProgress);
};

// ─── Reports & User APIs ───────────────────────────────────────────────────

export const getReportsList = async () => {
  const res = await apiClient.get("/analyses?limit=100", {
    headers: getAuthHeaders(),
  });
  const analyses = res.data?.data;
  if (!Array.isArray(analyses)) {
    throw new Error("The server returned an invalid analysis report list.");
  }

  return analyses
    .filter((analysis) =>
      ["COMPLETED", "PARTIAL"].includes(
        String(analysis.status || "").toUpperCase(),
      ),
    )
    .map((analysis) => {
      const fileName =
        analysis.fileName || analysis.filename || "Unknown media";
      return {
        ...analysis,
        id: analysis.id || analysis.analysisId || analysis.mediaId,
        title: `Analysis report - ${fileName}`,
        fileName,
        result: analysis.prediction || analysis.result || "UNCERTAIN",
      };
    });
};

export const saveReportToDatabase = async (analysisId, reportFileName, pdfBase64) => {
  try {
    const res = await apiClient.post(
      `/media/reports/${analysisId}`,
      { reportFileName, pdfBase64 },
      { headers: getAuthHeaders() }
    );
    return res.data;
  } catch (err) {
    console.warn("Could not sync report to backend database:", err.message);
    return null;
  }
};

export const getUserProfile = async () => {
  try {
    const res = await apiClient.get("/auth/me", { headers: getAuthHeaders() });
    return res.data?.user || res.data || null;
  } catch (err) {
    return asSampleData(MOCK_USER_PROFILE);
  }
};

// ─── Admin APIs ────────────────────────────────────────────────────────────

export const getAdminOverview = async () => {
  const res = await apiClient.get("/admin/overview", {
    headers: getAuthHeaders(),
  });
  return res.data;
};

export const getAdminUsers = async () => {
  const res = await apiClient.get("/admin/users", {
    headers: getAuthHeaders(),
  });
  return res.data;
};

export const getAdminAnalyses = async () => {
  const res = await apiClient.get("/admin/analyses", {
    headers: getAuthHeaders(),
  });
  return res.data;
};

export const getAdminModels = async () => {
  const res = await apiClient.get("/admin/models", {
    headers: getAuthHeaders(),
  });
  return res.data;
};

export default apiClient;
