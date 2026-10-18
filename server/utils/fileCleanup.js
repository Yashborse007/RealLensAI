import fs from "fs";
import path from "path";
import os from "os";

// Safe directory roots that can have temporary files deleted
const ALLOWED_CLEANUP_ROOTS = [
  path.resolve(process.cwd(), "uploads"),
  path.resolve(process.cwd(), "reports"),
  path.resolve(process.cwd(), "scratch"),
  path.resolve(os.tmpdir()),
];

/**
 * Validate that a given target path is strictly inside an allowed directory
 */
const isPathInsideAllowedRoots = (targetPath) => {
  if (!targetPath || typeof targetPath !== "string") return false;
  if (targetPath.includes("\0")) return false;

  const normalized = path.resolve(targetPath);
  return ALLOWED_CLEANUP_ROOTS.some((root) => {
    return (
      normalized === root ||
      normalized.startsWith(`${root}${path.sep}`)
    );
  });
};

/**
 * Safely delete a file from disk with strict path traversal prevention.
 * @param {string} filePath - Absolute or relative path to file
 */
export const deleteFile = (filePath) => {
  if (!filePath || typeof filePath !== "string") return;

  try {
    const absolutePath = path.isAbsolute(filePath)
      ? path.resolve(filePath)
      : path.resolve(process.cwd(), filePath);

    if (!isPathInsideAllowedRoots(absolutePath)) {
      console.warn(
        `[File Cleanup Security Warning] Attempted to delete path outside allowed boundaries: ${path.basename(filePath)}`,
      );
      return;
    }

    if (fs.existsSync(absolutePath)) {
      fs.unlinkSync(absolutePath);
      console.log(`[File Cleanup] Safely removed temporary file: ${path.basename(filePath)}`);
    }
  } catch (error) {
    console.error(
      `[File Cleanup Error] Failed to delete file ${path.basename(filePath)}: ${error.message}`,
    );
  }
};

/**
 * Clean up stale files older than maxAgeHours from a safe directory
 */
export const cleanupStaleFiles = (dirRelativePath = "uploads", maxAgeHours = 24) => {
  try {
    const targetDir = path.resolve(process.cwd(), dirRelativePath);
    if (!isPathInsideAllowedRoots(targetDir) || !fs.existsSync(targetDir)) {
      return;
    }

    const now = Date.now();
    const maxAgeMs = maxAgeHours * 60 * 60 * 1000;
    const files = fs.readdirSync(targetDir);

    for (const file of files) {
      if (file === ".gitkeep" || file === ".gitignore") continue;
      const fullPath = path.join(targetDir, file);
      try {
        const stats = fs.statSync(fullPath);
        if (stats.isFile() && now - stats.mtimeMs > maxAgeMs) {
          fs.unlinkSync(fullPath);
          console.log(`[File Cleanup] Pruned stale file: ${file}`);
        }
      } catch (_err) {
        // Skip inaccessible file
      }
    }
  } catch (error) {
    console.error(`[File Cleanup Error] Stale files cleanup failed: ${error.message}`);
  }
};
