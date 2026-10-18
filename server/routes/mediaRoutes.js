import express from "express";
import multer from "multer";
import {
  uploadMedia,
  analyzeMedia,
  getMediaAnalysis,
  getReport,
  saveReport,
} from "../controllers/mediaController.js";
import { protect } from "../middleware/authMiddleware.js";
import { upload } from "../middleware/uploadMiddleware.js";
import { uploadLimiter } from "../middleware/rateLimiters.js";

const router = express.Router();

/**
 * Handle Multer errors explicitly
 */
const handleUploadMiddleware = (req, res, next) => {
  upload.single("file")(req, res, (err) => {
    if (err && err.code === "LIMIT_FILE_SIZE") {
      return res.status(413).json({
        success: false,
        error:
          "File size limit exceeded. Maximum allowed upload size is 100MB.",
      });
    }
    if (err) {
      const sendError = () => {
        if (!res.headersSent) {
          res.status(400).json({
            success: false,
            error: err.message || "Invalid upload request.",
          });
        }
      };

      if (req.readableEnded) {
        return sendError();
      }

      req.once("end", sendError);
      req.resume();
      return;
    }
    next();
  });
};

router.post(
  "/upload",
  protect,
  uploadLimiter,
  handleUploadMiddleware,
  uploadMedia,
);

// POST /api/media/analyze
router.post("/analyze", protect, uploadLimiter, analyzeMedia);

// GET /api/media/analysis/:id
router.get("/analysis/:id", protect, getMediaAnalysis);
router.get("/reports/:id", protect, getReport);
router.post("/reports/:id", protect, saveReport);

export default router;
