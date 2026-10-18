import assert from "node:assert/strict";
import test from "node:test";
import request from "supertest";
import app from "../app.js";

test("health requests expose gateway and MongoDB timing headers", async () => {
  const response = await request(app).get("/api/health").expect(200);

  assert.ok(Number.isFinite(Number(response.headers["x-request-time-ms"])));
  assert.ok(Number.isFinite(Number(response.headers["x-mongo-query-time-ms"])));
  assert.ok(Number.isFinite(Number(response.headers["x-mongo-query-count"])));
  assert.match(response.headers["server-timing"], /app;dur=/);
  assert.match(response.headers["server-timing"], /mongo;dur=/);
});
