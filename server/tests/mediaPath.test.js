import test from "node:test";
import assert from "node:assert/strict";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { resolveUploadedMediaPath } from "../utils/mediaPath.js";

test("resolveUploadedMediaPath finds a file when stored and runtime upload roots differ", () => {
  const serverDirectory = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    "..",
  );
  const uploadDirectory = path.join(serverDirectory, "uploads");
  const filename = `media_${Date.now()}_${Math.random()
    .toString(16)
    .slice(2, 10)
    .padEnd(16, "0")}.mp4`;
  const expectedPath = path.join(uploadDirectory, filename);

  fs.mkdirSync(uploadDirectory, { recursive: true });
  fs.writeFileSync(expectedPath, "test media");

  try {
    assert.equal(
      resolveUploadedMediaPath({
        path: `uploads/${filename}`,
        filename,
      }),
      expectedPath,
    );
  } finally {
    fs.unlinkSync(expectedPath);
  }
});

test("resolveUploadedMediaPath rejects a filename that is not server-generated", () => {
  assert.equal(
    resolveUploadedMediaPath({
      path: "missing.mp4",
      filename: "..\\outside.mp4",
    }),
    null,
  );
});
