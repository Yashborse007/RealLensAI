import express from "express";
import {
  getDashboardAnalytics,
  getDistributionAnalytics,
} from "../controllers/analyticsController.js";
import { protect } from "../middleware/authMiddleware.js";

const router = express.Router();

router.use(protect);

router.get("/dashboard", getDashboardAnalytics);
router.get("/distribution", getDistributionAnalytics);

export default router;
