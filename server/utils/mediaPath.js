import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { resolveSafeSubpath } from "../config/securityConfig.js";

const serverDirectory = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);

const getUploadDirectories = () =>
  [
    path.resolve(process.cwd(), "uploads"),
    path.resolve(process.cwd(), "server", "uploads"),
    path.resolve(process.cwd(), "..", "uploads"),
    path.resolve(serverDirectory, "uploads"),
    path.resolve(serverDirectory, "..", "uploads"),
  ].filter((directory, index, directories) => directories.indexOf(directory) === index);

export const resolveUploadedMediaPath = (record) => {
  const directories = getUploadDirectories();
  const candidates = [];

  if (typeof record?.path === "string") {
    for (const directory of directories) {
      candidates.push(resolveSafeSubpath(record.path, directory));
    }
  }

  const generatedFilename = record?.filename;
  if (
    typeof generatedFilename === "string" &&
    path.basename(generatedFilename) === generatedFilename &&
    /^media_\d+_[a-f0-9]{16}\.[a-z0-9]+$/i.test(generatedFilename)
  ) {
    for (const directory of directories) {
      candidates.push(resolveSafeSubpath(generatedFilename, directory));
    }
  }

  return candidates.find(
    (candidate) => candidate && fs.existsSync(candidate),
  ) || null;
};
