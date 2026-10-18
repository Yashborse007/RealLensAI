import express from "express";
import {
  registerUser,
  loginUser,
  getMe,
} from "../controllers/authController.js";
import { protect } from "../middleware/authMiddleware.js";
import { authLimiter } from "../middleware/rateLimiters.js";

const router = express.Router();

// Public auth routes with dedicated rate limiting
router.post("/register", authLimiter, registerUser);
router.post("/login", authLimiter, loginUser);

// Private protected auth route
router.get("/me", protect, getMe);

export default router;
