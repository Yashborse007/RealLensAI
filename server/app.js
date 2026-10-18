import "./config/mongooseRuntime.js";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import axios from "axios";
import path from "path";
import authRoutes from "./routes/authRoutes.js";
import mediaRoutes from "./routes/mediaRoutes.js";
import analysisRoutes from "./routes/analysisRoutes.js";
import adminRoutes from "./routes/adminRoutes.js";
import analyticsRoutes from "./routes/analyticsRoutes.js";
import {
  getAllowedOrigins,
  isLocalDevelopmentOrigin,
  SECURITY_LIMITS,
} from "./config/securityConfig.js";
import { requestPerformanceMiddleware } from "./utils/performanceMetrics.js";
import { authLimiter, uploadLimiter } from "./middleware/rateLimiters.js";

const app = express();

/**
 * Deep sanitization for NoSQL injection prevention and XSS mitigation
 * Strips MongoDB operators ($gt, $ne, $where, etc.), prototype pollution, null bytes,
 * and dangerous HTML tags.
 */
const sanitizeInputData = (value) => {
  if (value === null || value === undefined) return value;
  if (Array.isArray(value)) return value.map(sanitizeInputData);

  if (typeof value === "string") {
    return value.replace(/\0/g, "").replace(/[<>]/g, "").trim();
  }

  if (typeof value === "object") {
    const safeObject = {};
    for (const [key, nestedValue] of Object.entries(value)) {
      // 1. Prototype pollution defense
      if (["__proto__", "constructor", "prototype"].includes(key)) {
        continue;
      }

      // 2. MongoDB operator injection defense ($ and dot notation)
      if (key.startsWith("$") || key.includes(".")) {
        continue;
      }

      safeObject[key] = sanitizeInputData(nestedValue);
    }
    return safeObject;
  }

  return value;
};

const allowedOrigins = getAllowedOrigins();

app.disable("x-powered-by");
app.set("trust proxy", 1);
app.use(requestPerformanceMiddleware);

// 1. Helmet Security Headers
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        fontSrc: ["'self'", "https://fonts.gstatic.com"],
        imgSrc: ["'self'", "data:", "blob:"],
        connectSrc: ["'self'"],
        objectSrc: ["'none'"],
        frameAncestors: ["'none'"],
      },
    },
    crossOriginResourcePolicy: { policy: "cross-origin" },
    crossOriginOpenerPolicy: { policy: "same-origin" },
    frameguard: { action: "deny" },
    noSniff: true,
    referrerPolicy: { policy: "strict-origin-when-cross-origin" },
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true,
    },
  }),
);

// 2. Additional Security Headers
app.use((_req, res, next) => {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("X-Frame-Options", "DENY");
  res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
  res.setHeader(
    "Permissions-Policy",
    "camera=(self), microphone=(self), geolocation=()",
  );
  next();
});

// 3. CORS Configuration
const corsOptions = {
  origin: (origin, callback) => {
    // Allow requests with no origin (e.g. mobile apps, curl, server-to-server)
    if (
      !origin ||
      allowedOrigins.includes(origin) ||
      isLocalDevelopmentOrigin(origin)
    ) {
      callback(null, true);
      return;
    }
    console.warn(`[CORS] Rejected browser origin: ${origin}`);
    callback(new Error("Origin not allowed by CORS policy."));
  },
  credentials: true,
  methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization", "X-Requested-With"],
  maxAge: 600,
};

app.use(cors(corsOptions));
app.options("*", cors(corsOptions));

// 4. Rate Limiting (skipped during automated test runs)
const isTestEnv = process.env.NODE_ENV === "test";

const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: Number(process.env.RATE_LIMIT_MAX) || 200,
  standardHeaders: true,
  legacyHeaders: false,
  skip: () => isTestEnv,
  message: {
    success: false,
    error: "Too many requests. Please try again later.",
  },
});
app.use(globalLimiter);

// 5. Body Parsers (run BEFORE sanitizers so req.body is parsed)
app.use(express.json({ limit: SECURITY_LIMITS.MAX_BODY_SIZE }));
app.use(
  express.urlencoded({ extended: true, limit: SECURITY_LIMITS.MAX_BODY_SIZE }),
);

// 6. Deep Input Sanitization (NoSQL injection & XSS defense)
app.use((req, _res, next) => {
  if (req.body) req.body = sanitizeInputData(req.body);
  if (req.query) req.query = sanitizeInputData(req.query);
  if (req.params) req.params = sanitizeInputData(req.params);
  next();
});

// 7. Serve Static Upload Directory (hardened with attachment disposition & no execute)
app.use(
  "/uploads",
  express.static(path.join(process.cwd(), "uploads"), {
    index: false,
    extensions: false,
    dotfiles: "deny",
    setHeaders: (res) => {
      res.setHeader("Content-Disposition", "attachment");
      res.setHeader("X-Content-Type-Options", "nosniff");
      res.setHeader("Content-Security-Policy", "default-src 'none'");
    },
  }),
);

// 8. Health Check Endpoints
// GET /api/health - Express Gateway Health Check
app.get("/api/health", (_req, res) => {
  res.status(200).json({
    success: true,
    service: "RealLens AI Backend",
    status: "running",
  });
});

// GET /api/health/ai - Proxy Health Check for Python FastAPI AI Service
app.get("/api/health/ai", async (_req, res) => {
  const aiServiceUrl = process.env.AI_SERVICE_URL || "http://127.0.0.1:8000";
  try {
    const response = await axios.get(`${aiServiceUrl}/health`, {
      timeout: 3000,
    });
    return res.status(200).json({
      success: true,
      service: "RealLens AI Backend",
      aiServiceStatus: "reachable",
      aiService: response.data,
    });
  } catch (_error) {
    return res.status(503).json({
      success: false,
      service: "RealLens AI Backend",
      aiServiceStatus: "unreachable",
      error:
        "Failed to connect to Python AI Service. Service may be offline or starting.",
    });
  }
});

// 9. API Routes
app.use("/api/auth", authRoutes);
app.use("/api/media", mediaRoutes);
app.use("/api/analyses", analysisRoutes);
app.use("/api/admin", adminRoutes);
app.use("/api/analytics", analyticsRoutes);

// 10. Global 404 Route Handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: `Cannot ${req.method} ${req.originalUrl} - Endpoint not found.`,
  });
});

// 11. Centralized Security Error Handler (prevents stack/internal error leaks)
app.use((err, req, res, _next) => {
  // Handle CORS rejection
  if (err && err.message && err.message.includes("CORS")) {
    return res.status(403).json({
      success: false,
      error: "Request rejected by CORS security policy.",
    });
  }

  // Handle JSON parsing syntax error
  if (err instanceof SyntaxError && err.status === 400 && "body" in err) {
    return res.status(400).json({
      success: false,
      error: "Malformed JSON payload in request body.",
    });
  }

  // Log internal error server-side with stack trace (never exposed to client)
  console.error(
    `[Server Error] ${req.method} ${req.originalUrl}:`,
    err.message || err,
  );

  return res.status(500).json({
    success: false,
    error: "An unexpected server error occurred.",
  });
});

export default app;
