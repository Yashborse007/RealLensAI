import mongoose from "mongoose";
import { redactMongoUri } from "./securityConfig.js";
import {
  recordMongoCommand,
  requestPerformanceContext,
} from "../utils/performanceMetrics.js";

const activeMongoCommands = new Map();

const attachMongoPerformanceListeners = (client) => {
  client.on("commandStarted", (event) => {
    activeMongoCommands.set(event.requestId, {
      startedAt: performance.now(),
      context: requestPerformanceContext.getStore(),
    });
  });

  const finishCommand = (event) => {
    const command = activeMongoCommands.get(event.requestId);
    if (!command) return;
    activeMongoCommands.delete(event.requestId);
    recordMongoCommand(performance.now() - command.startedAt, command.context);
  };

  client.on("commandSucceeded", finishCommand);
  client.on("commandFailed", finishCommand);
};

export const connectDB = async () => {
  try {
    const mongoUri =
      process.env.MONGO_URI || "mongodb://localhost:27017/reallens_ai";
    const conn = await mongoose.connect(mongoUri, {
      serverSelectionTimeoutMS: 5000,
      monitorCommands: true,
    });
    attachMongoPerformanceListeners(conn.connection.getClient());
    console.log(
      `[MongoDB] Database connected successfully: ${conn.connection.host}`,
    );
  } catch (error) {
    const safeErrorMsg = redactMongoUri(
      error.message || "Unknown database connection error",
    );
    console.log(
      `[Storage] Running with In-Memory Storage for development (MongoDB optional: ${safeErrorMsg}).`,
    );
    if (process.env.NODE_ENV === "production") {
      throw new Error(
        "MongoDB is required for production startup; durable user and analysis storage is unavailable.",
      );
    }
  }
};
