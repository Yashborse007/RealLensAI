/**
 * RealLens AI - Centralized Security Configuration & Utilities
 * Enforces production security standards across authentication, encryption, and storage.
 */
import path from "path";

/**
 * Validate and retrieve JWT secret key.
 * In production, fails closed if no secure secret is configured.
 */
export const getSafeJwtSecret = () => {
  const secret = process.env.JWT_SECRET;
  const isProduction = process.env.NODE_ENV === "production";

  if (secret) {
    if (isProduction && secret.length < 32) {
      console.warn(
        "[SECURITY WARNING] JWT_SECRET is shorter than 32 characters in production!",
      );
    }
    return secret;
  }

  if (isProduction) {
    return null;
  }

  // Development/Test fallback only
  return "reallens_ai_jwt_secret_key_change_in_production";
};

/**
 * Redact sensitive credentials from MongoDB URI before logging.
 */
export const redactMongoUri = (uri) => {
  if (!uri || typeof uri !== "string") return "";
  return uri.replace(
    /(mongodb(\+srv)?:\/\/)([^:@]+):([^@]+)@/i,
    "$1$3:****@",
  );
};

/**
 * Path traversal safe resolution.
 * Ensures the candidate path resolves strictly within the target allowed directory.
 */
export const resolveSafeSubpath = (candidatePath, allowedBaseDir) => {
  if (!candidatePath || typeof candidatePath !== "string") return null;

  // Reject paths containing null bytes
  if (candidatePath.includes("\0")) return null;

  const baseDir = path.resolve(process.cwd(), allowedBaseDir);
  let normalizedCandidate = path
    .normalize(candidatePath)
    .replace(/^(\.\.(\/|\\|$))+/, "");

  if (!path.isAbsolute(normalizedCandidate)) {
    const [candidateBase, ...remainingParts] = normalizedCandidate.split(path.sep);
    if (candidateBase === path.basename(baseDir)) {
      normalizedCandidate = remainingParts.join(path.sep);
    }
  }

  const resolved = path.isAbsolute(candidatePath)
    ? path.resolve(candidatePath)
    : path.resolve(baseDir, normalizedCandidate);

  // Must equal baseDir or start with baseDir + path.sep
  if (resolved === baseDir || resolved.startsWith(`${baseDir}${path.sep}`)) {
    return resolved;
  }

  return null;
};

/**
 * Strict whitelist of allowed origins for CORS.
 */
export const getAllowedOrigins = () => {
  const configuredOrigins = [process.env.CLIENT_URL, process.env.CORS_ORIGINS]
    .filter(Boolean)
    .flatMap((value) => value.split(","))
    .map((origin) => origin.trim().replace(/\/+$/, ""))
    .filter(Boolean);

  return [
    ...new Set([
      ...configuredOrigins,
      "http://localhost:5173",
      "http://localhost:5174",
      "http://localhost:5175",
      "http://localhost:5176",
      "http://localhost:5177",
      "http://localhost:3000",
      "http://127.0.0.1:5173",
      "http://127.0.0.1:5174",
      "http://127.0.0.1:5175",
      "http://127.0.0.1:5176",
      "http://127.0.0.1:5177",
      "http://127.0.0.1:3000",
    ]),
  ];
};

export const isLocalDevelopmentOrigin = (origin) => {
  if (process.env.NODE_ENV === "production") return false;

  let parsedOrigin;
  try {
    parsedOrigin = new URL(origin);
  } catch {
    return false;
  }

  if (parsedOrigin.protocol !== "http:" && parsedOrigin.protocol !== "https:") {
    return false;
  }

  const hostname = parsedOrigin.hostname.toLowerCase().replace(/^\[|\]$/g, "");
  if (["localhost", "127.0.0.1", "::1"].includes(hostname)) {
    return true;
  }

  const octets = hostname.split(".").map(Number);
  const isPrivateIpv4 =
    octets.length === 4 &&
    octets.every(
      (octet) =>
        Number.isInteger(octet) && octet >= 0 && octet <= 255,
    ) &&
    (octets[0] === 10 ||
      (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) ||
      (octets[0] === 192 && octets[1] === 168));

  return isPrivateIpv4;
};

/**
 * Security Limits
 */
export const SECURITY_LIMITS = {
  MAX_FILE_SIZE: parseInt(process.env.MAX_FILE_SIZE_BYTES, 10) || 100 * 1024 * 1024, // 100MB
  MAX_BODY_SIZE: "2mb",
  MAX_PASSWORD_LENGTH: 128,
  MIN_PASSWORD_LENGTH: 6,
  MAX_NAME_LENGTH: 100,
  MAX_EMAIL_LENGTH: 255,
  MAX_FILENAME_LENGTH: 150,
};
