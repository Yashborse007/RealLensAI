import test from "node:test";
import assert from "node:assert/strict";
import supertest from "supertest";
import app from "../app.js";

test("GET /api/health returns the backend health contract", async () => {
  const response = await supertest(app).get("/api/health");

  assert.equal(response.status, 200);
  assert.deepEqual(response.body, {
    success: true,
    service: "RealLens AI Backend",
    status: "running",
  });
});
