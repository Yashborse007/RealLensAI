import jwt from "jsonwebtoken";
import bcrypt from "bcryptjs";
import User from "../models/User.js";
import { getSafeJwtSecret, SECURITY_LIMITS } from "../config/securityConfig.js";
import {
  findUserByEmail,
  saveUser,
  compareInMemoryPassword,
} from "../services/store/inMemoryStore.js";

// Dummy bcrypt hash for timing attack mitigation on failed lookups
const DUMMY_HASH = "$2a$10$e8w6W2f39D5uKjL5U6zG9eN64Qv1rA/U2s0l.2jC79VwK9T2aU1O2";

/**
 * Generate JWT signed token with explicit algorithm
 */
const generateToken = (id, role) => {
  const secret = getSafeJwtSecret();
  if (!secret) {
    throw new Error("JWT secret is not configured.");
  }
  return jwt.sign({ id, role }, secret, {
    algorithm: "HS256",
    expiresIn: "24h",
  });
};

/**
 * Validate email format using standard RFC 5322 compliant regex
 */
const isValidEmail = (email) => {
  if (typeof email !== "string") return false;
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
  return emailRegex.test(email) && email.length <= SECURITY_LIMITS.MAX_EMAIL_LENGTH;
};

/**
 * Sanitize plain string input (strip tags and control characters)
 */
const sanitizeText = (str = "") => {
  if (typeof str !== "string") return "";
  return str
    .replace(/\0/g, "")
    .replace(/<[^>]*>/g, "")
    .trim();
};

/**
 * @desc    Register a new user
 * @route   POST /api/auth/register
 * @access  Public
 */
export const registerUser = async (req, res) => {
  try {
    const { name, email, password, role } = req.body || {};

    // 1. Validate required fields and types
    if (!name || !email || !password) {
      return res.status(400).json({
        success: false,
        error: "Please provide name, email, and password.",
      });
    }

    if (
      typeof name !== "string" ||
      typeof email !== "string" ||
      typeof password !== "string"
    ) {
      return res.status(400).json({
        success: false,
        error: "Invalid input types provided.",
      });
    }

    const cleanName = sanitizeText(name);
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanName || cleanName.length > SECURITY_LIMITS.MAX_NAME_LENGTH) {
      return res.status(400).json({
        success: false,
        error: "Name must be between 1 and 100 characters.",
      });
    }

    // 2. Validate email format
    if (!isValidEmail(cleanEmail)) {
      return res.status(400).json({
        success: false,
        error: "Please enter a valid email address.",
      });
    }

    // 3. Validate password strength/length (minimum 6, maximum 128 characters)
    if (password.length < SECURITY_LIMITS.MIN_PASSWORD_LENGTH) {
      return res.status(400).json({
        success: false,
        error: "Password must be at least 6 characters long.",
      });
    }

    if (password.length > SECURITY_LIMITS.MAX_PASSWORD_LENGTH) {
      return res.status(400).json({
        success: false,
        error: "Password exceeds maximum allowable length (128 characters).",
      });
    }

    // Role assignment: restrict admin registration unless authorized
    let userRole = "user";
    if (role === "admin") {
      if (process.env.ALLOW_ADMIN_REGISTRATION === "true") {
        userRole = "admin";
      }
    }

    // 4. Hash raw password using bcrypt with 10 salt rounds
    const salt = await bcrypt.genSalt(10);
    const passwordHash = await bcrypt.hash(password, salt);

    let user = null;
    let userExists = false;

    // Attempt Mongoose DB creation first
    try {
      userExists = await User.findOne({ email: cleanEmail });
      if (userExists) {
        return res.status(400).json({
          success: false,
          error:
            "Email is already registered. Please sign in or use a different email.",
        });
      }

      user = await User.create({
        name: cleanName,
        email: cleanEmail,
        passwordHash,
        role: userRole,
      });
    } catch (dbErr) {
      if (dbErr?.code === 11000) {
        return res.status(400).json({
          success: false,
          error:
            "Email is already registered. Please sign in or use a different email.",
        });
      }

      if (process.env.NODE_ENV === "production") {
        console.error("[Auth] Database unavailable during registration.");
        return res.status(503).json({
          success: false,
          error: "Registration is temporarily unavailable. Please try again.",
        });
      }

      // Keep ephemeral accounts limited to development and automated tests.
      if (findUserByEmail(cleanEmail)) {
        return res.status(400).json({
          success: false,
          error:
            "Email is already registered. Please sign in or use a different email.",
        });
      }

      user = await saveUser({
        name: cleanName,
        email: cleanEmail,
        passwordHash,
        role: userRole,
      });
    }

    const userId = user._id ? String(user._id) : String(user.id);
    const token = generateToken(userId, user.role);

    return res.status(201).json({
      success: true,
      message: "User registered successfully.",
      token,
      user: {
        id: userId,
        name: user.name,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt,
      },
    });
  } catch (_error) {
    return res.status(500).json({
      success: false,
      error: "Unable to complete registration.",
    });
  }
};

/**
 * @desc    Authenticate user & get token
 * @route   POST /api/auth/login
 * @access  Public
 */
export const loginUser = async (req, res) => {
  try {
    const { email, password } = req.body || {};

    // 1. Validate required fields and types
    if (!email || !password) {
      return res.status(400).json({
        success: false,
        error: "Please provide both email and password.",
      });
    }

    if (typeof email !== "string" || typeof password !== "string") {
      return res.status(400).json({
        success: false,
        error: "Invalid email or password format.",
      });
    }

    const cleanEmail = email.trim().toLowerCase();

    // 2. Validate email format
    if (!isValidEmail(cleanEmail)) {
      return res.status(400).json({
        success: false,
        error: "Please enter a valid email address.",
      });
    }

    // Limit password length check
    if (password.length > SECURITY_LIMITS.MAX_PASSWORD_LENGTH) {
      return res.status(401).json({
        success: false,
        error: "Invalid email or password.",
      });
    }

    let user = null;
    let isMatch = false;

    // Attempt Mongoose fetch first
    try {
      user = await User.findOne({ email: cleanEmail });
      if (user) {
        isMatch = await user.comparePassword(password);
      }
    } catch (dbErr) {
      if (process.env.NODE_ENV === "production") {
        console.error("[Auth] Database unavailable during login.");
        return res.status(503).json({
          success: false,
          error: "Login is temporarily unavailable. Please try again.",
        });
      }
      user = null;
    }

    // Fallback to in-memory store if not found in Mongoose DB
    if (!user) {
      user = findUserByEmail(cleanEmail);
      if (user) {
        isMatch = await compareInMemoryPassword(password, user.passwordHash);
      }
    }

    // Timing attack mitigation: always execute bcrypt compare even if user not found
    if (!user) {
      await bcrypt.compare(password, DUMMY_HASH);
      return res.status(401).json({
        success: false,
        error: "Invalid email or password.",
      });
    }

    if (!isMatch) {
      return res.status(401).json({
        success: false,
        error: "Invalid email or password.",
      });
    }

    const userId = user._id ? String(user._id) : String(user.id);
    const token = generateToken(userId, user.role);

    return res.status(200).json({
      success: true,
      message: "Login successful.",
      token,
      user: {
        id: userId,
        name: user.name,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt,
      },
    });
  } catch (_error) {
    return res.status(500).json({
      success: false,
      error: "Unable to complete login.",
    });
  }
};

/**
 * @desc    Get authenticated user profile
 * @route   GET /api/auth/me
 * @access  Private (Protected by JWT)
 */
export const getMe = async (req, res) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        success: false,
        error: "Unauthorized user session.",
      });
    }

    return res.status(200).json({
      success: true,
      user: {
        id: req.user.id,
        name: req.user.name,
        email: req.user.email,
        role: req.user.role,
        createdAt: req.user.createdAt,
      },
    });
  } catch (_error) {
    return res.status(500).json({
      success: false,
      error: "Failed to retrieve user profile.",
    });
  }
};
