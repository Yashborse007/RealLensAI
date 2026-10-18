import multer from "multer";
import path from "path";
import crypto from "crypto";
import fs from "fs";

// Ensure uploads directory exists
const UPLOAD_DIR = path.resolve(process.cwd(), "uploads");
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

/**
 * Strict filename sanitizer to strip path traversal, null bytes, control characters,
 * and dangerous symbols.
 */
export const sanitizeFilename = (originalName = "upload") => {
  const safeName = String(originalName || "upload")
    .replace(/\0/g, "")
    .replace(/[\x00-\x1f\x7f]/g, "")
    .replace(/[\\/]+/g, "_")
    .replace(/\.{2,}/g, ".") // prevent directory traversal sequences ..
    .replace(/[^a-zA-Z0-9_.-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .trim()
    .slice(0, 100);

  return safeName || "upload";
};

// Whitelisted file extension mapping to media categories
const ALLOWED_EXTENSIONS = {
  // Image formats
  jpg: "image",
  jpeg: "image",
  png: "image",
  webp: "image",
  // Video formats
  mp4: "video",
  mov: "video",
  avi: "video",
  mkv: "video",
  webm: "video",
  // Audio formats
  mp3: "audio",
  wav: "audio",
  m4a: "audio",
  aac: "audio",
  flac: "audio",
};

// Whitelisted MIME type mapping
const ALLOWED_MIME_TYPES = {
  // Images
  "image/jpeg": "image",
  "image/png": "image",
  "image/webp": "image",
  // Videos
  "video/mp4": "video",
  "video/quicktime": "video", // .mov
  "video/x-msvideo": "video", // .avi
  "video/x-matroska": "video", // .mkv
  "video/webm": "video",
  // Audio
  "audio/mpeg": "audio", // .mp3
  "audio/mp3": "audio",
  "audio/wav": "audio",
  "audio/x-wav": "audio",
  "audio/m4a": "audio",
  "audio/x-m4a": "audio",
  "audio/mp4": "audio",
  "audio/aac": "audio",
  "audio/x-aac": "audio",
  "audio/flac": "audio",
  "audio/x-flac": "audio",
};

/**
 * Configure Multer Storage Engine
 * Generates unique cryptographic filenames (never trusts original filename)
 */
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, UPLOAD_DIR);
  },
  filename: (req, file, cb) => {
    const safeName = sanitizeFilename(file.originalname || "upload");
    const rawExt = path.extname(safeName).toLowerCase().replace(".", "");
    const ext = ALLOWED_EXTENSIONS[rawExt] ? `.${rawExt}` : ".bin";
    const uniqueSuffix = `${Date.now()}_${crypto.randomBytes(8).toString("hex")}`;
    const sanitizedFilename = `media_${uniqueSuffix}${ext}`;
    file.sanitizedOriginalName = safeName;
    cb(null, sanitizedFilename);
  },
});

/**
 * File Filter Function validating both MIME type & Extension
 */
const fileFilter = (req, file, cb) => {
  const safeOriginalName = sanitizeFilename(file.originalname || "upload");
  const ext = path.extname(safeOriginalName).toLowerCase().replace(".", "");
  const mimeType = (file.mimetype || "").toLowerCase().trim();

  const categoryByExt = ALLOWED_EXTENSIONS[ext];
  const categoryByMime = ALLOWED_MIME_TYPES[mimeType];

  // 1. Check extension whitelist
  if (!categoryByExt) {
    return cb(
      new Error(
        `Unsupported file extension '.${ext}'. Allowed formats: jpg, jpeg, png, webp, mp4, mov, avi, mkv, webm, mp3, wav, m4a, aac, flac`,
      ),
      false,
    );
  }

  // 2. Check MIME type whitelist
  if (!categoryByMime) {
    return cb(
      new Error(
        `Invalid MIME type '${mimeType}'. File content type does not match supported media formats.`,
      ),
      false,
    );
  }

  // 3. Ensure extension and MIME category match
  if (categoryByExt !== categoryByMime) {
    return cb(
      new Error(
        `MIME type '${mimeType}' conflicts with file extension '.${ext}'. Upload rejected.`,
      ),
      false,
    );
  }

  // Attach determined mediaType category to req for controller use
  req.detectedMediaType = categoryByExt;
  cb(null, true);
};

// Configurable maximum file size limit (default 100 MB)
const MAX_FILE_SIZE =
  parseInt(process.env.MAX_FILE_SIZE_BYTES, 10) || 100 * 1024 * 1024;

export const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: MAX_FILE_SIZE,
    files: 1, // Only 1 file per request
    fields: 10,
    parts: 15,
  },
});
