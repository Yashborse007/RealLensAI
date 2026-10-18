import test from "node:test";
import assert from "node:assert/strict";
import path from "path";
import { resolveSafeSubpath } from "../config/securityConfig.js";

test("resolveSafeSubpath accepts paths relative to the allowed directory", () => {
  const storedPath = "uploads/media_123.jpg";

  assert.equal(
    resolveSafeSubpath(storedPath, "uploads"),
    path.resolve(process.cwd(), "uploads", "media_123.jpg"),
  );
});

test("resolveSafeSubpath continues to accept an absolute path inside the directory", () => {
  const absolutePath = path.resolve(process.cwd(), "uploads", "media_123.jpg");

  assert.equal(resolveSafeSubpath(absolutePath, "uploads"), absolutePath);
});

test("resolveSafeSubpath rejects absolute paths outside the allowed directory", () => {
  const outsidePath = path.resolve(process.cwd(), "private", "media_123.jpg");

  assert.equal(resolveSafeSubpath(outsidePath, "uploads"), null);
});
