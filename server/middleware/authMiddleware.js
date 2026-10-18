import jwt from "jsonwebtoken";
import User from "../models/User.js";
import { getSafeJwtSecret } from "../config/securityConfig.js";

// In-memory user store fallback if MongoDB connection is inactive during testing
import { findUserById } from "../services/store/inMemoryStore.js";

const rejectRequest = (req, res, statusCode, body) => {
  const sendResponse = () => {
    if (!res.headersSent) {
      res.status(statusCode).json(body);
    }
  };

  if (req.readableEnded) {
    return sendResponse();
  }

  req.once("end", sendResponse);
  req.resume();
};

export const protect = async (req, res, next) => {
  let token;

  const authHeader = req.headers.authorization;
  if (
    authHeader &&
    typeof authHeader === "string" &&
    authHeader.startsWith("Bearer ")
  ) {
    try {
      token = authHeader.substring(7).trim();

      if (!token) {
        return rejectRequest(req, res, 401, {
          success: false,
          error: "Access denied. Token is missing.",
        });
      }

      const jwtSecret = getSafeJwtSecret();
      if (!jwtSecret) {
        return rejectRequest(req, res, 500, {
          success: false,
          error: "Authentication is not configured on this server.",
        });
      }

      // Enforce strict HS256 algorithm to prevent algorithm switching attacks
      const decoded = jwt.verify(token, jwtSecret, {
        algorithms: ["HS256"],
      });

      let user = null;
      try {
        user = await User.findById(decoded.id).select("-passwordHash");
      } catch (dbErr) {
        user = null;
      }

      if (!user) {
        user = findUserById(decoded.id);
      }

      const reqUser = user
        ? {
            id: user._id || user.id,
            name: user.name,
            email: user.email,
            role: user.role,
            createdAt: user.createdAt,
          }
        : {
            id: decoded.id,
            name: decoded.name || "Token User",
            email: decoded.email || `${decoded.id}@token.local`,
            role: decoded.role || "user",
            createdAt: decoded.createdAt || new Date().toISOString(),
          };

      req.user = reqUser;

      next();
    } catch (error) {
      return rejectRequest(req, res, 401, {
        success: false,
        error: "Invalid or expired token.",
      });
    }
  } else {
    return rejectRequest(req, res, 401, {
      success: false,
      error: "Access denied. No Authorization header provided.",
    });
  }
};

export const adminOnly = (req, res, next) => {
  if (req.user && req.user.role === "admin") {
    next();
  } else {
    return res.status(403).json({
      success: false,
      error: "Access denied. Admin privileges required.",
    });
  }
};
