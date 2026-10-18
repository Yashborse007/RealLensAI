import dotenv from "dotenv";
dotenv.config();

import mongoose from "mongoose";
import app from "./app.js";
import { connectDB } from "./config/db.js";
import { cleanupStaleFiles } from "./utils/fileCleanup.js";
import { getSafeJwtSecret } from "./config/securityConfig.js";
import {
  AI_SERVICE_PORT,
  DEFAULT_BACKEND_PORT,
  getBackendPort,
} from "./config/serverConfig.js";

const configuredPort = Number.parseInt(process.env.PORT, 10);
const PORT = getBackendPort(process.env.PORT);

// Security startup audit
const auditEnvironmentSecurity = () => {
  const isProduction = process.env.NODE_ENV === "production";
  const jwtSecret = getSafeJwtSecret();

  if (isProduction) {
    if (
      !jwtSecret ||
      jwtSecret === "reallens_ai_jwt_secret_key_change_in_production" ||
      jwtSecret.length < 32
    ) {
      console.error(
        "[CRITICAL SECURITY ERROR] JWT_SECRET must be unique and at least 32 characters in production. Server startup halted.",
      );
      process.exit(1);
    }
  }

  // Prune any abandoned uploads older than 24 hours
  cleanupStaleFiles("uploads", 24);
};

// Initialize Database Connection & Start Server
const startServer = async () => {
  auditEnvironmentSecurity();
  await connectDB();

  if (configuredPort === AI_SERVICE_PORT) {
    console.warn(
      `[Startup Warning] PORT=${AI_SERVICE_PORT} is reserved for the AI service; the backend will use port ${DEFAULT_BACKEND_PORT}.`,
    );
  }

  const listen = (port, usedFallback = false) => {
    const server = app.listen(port, () => {
      console.log(`====================================================`);
      console.log(`  RealLens AI Backend Gateway running on port ${port}`);
      console.log(`  Health Check: http://localhost:${port}/api/health`);
      console.log(`  AI Bridge Check: http://localhost:${port}/api/health/ai`);
      console.log(`====================================================`);
    });

    server.once("error", async (error) => {
      if (error.code === "EADDRINUSE" && port !== DEFAULT_BACKEND_PORT && !usedFallback) {
        console.warn(
          `[Startup Warning] Port ${port} is already in use. Retrying the backend on port ${DEFAULT_BACKEND_PORT}.`,
        );
        listen(DEFAULT_BACKEND_PORT, true);
        return;
      }

      if (error.code === "EADDRINUSE") {
        console.error(
          `[Startup Error] Backend port ${port} is already in use. The AI service uses port ${AI_SERVICE_PORT}; keep the backend on port ${DEFAULT_BACKEND_PORT} or stop only a confirmed duplicate RealLens backend.`,
        );
      } else {
        console.error(`[Server Error] ${error.message}`);
      }

      try {
        await mongoose.disconnect();
      } catch (disconnectError) {
        console.error(
          `[Shutdown Error] Could not disconnect MongoDB cleanly: ${disconnectError.message}`,
        );
      }
      process.exitCode = 1;
    });
  };

  listen(PORT);
};

startServer().catch((error) => {
  console.error(`[Startup Error] ${error.message}`);
  process.exitCode = 1;
});
