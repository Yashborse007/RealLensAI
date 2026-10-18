import express from "express";
import {
  getAdminOverview,
  getAdminUsers,
  getAdminAnalyses,
  getAdminModels,
} from "../controllers/adminController.js";
import { protect, adminOnly } from "../middleware/authMiddleware.js";

const router = express.Router();

router.use(protect);
router.use(adminOnly);

router.get("/overview", getAdminOverview);
router.get("/users", getAdminUsers);
router.get("/analyses", getAdminAnalyses);
router.get("/models", getAdminModels);

export default router;
