import test from "node:test";
import assert from "node:assert/strict";
import supertest from "supertest";

process.env.NODE_ENV = "development";
process.env.CORS_ORIGINS = "https://portal.example.org";

const { default: app } = await import("../app.js");
const request = supertest(app);

test("CORS allows configured frontend origins", async () => {
  const response = await request
    .get("/api/health")
    .set("Origin", "https://portal.example.org");

  assert.equal(response.status, 200);
  assert.equal(
    response.headers["access-control-allow-origin"],
    "https://portal.example.org",
  );
});

test("CORS allows local Vite apps opened over a private network", async () => {
  const response = await request
    .get("/api/health")
    .set("Origin", "http://192.168.1.42:5173");

  assert.equal(response.status, 200);
  assert.equal(
    response.headers["access-control-allow-origin"],
    "http://192.168.1.42:5173",
  );
});

test("CORS still rejects unconfigured public origins", async () => {
  const response = await request
    .get("/api/health")
    .set("Origin", "https://untrusted.example.org");

  assert.equal(response.status, 403);
  assert.equal(response.body.error, "Request rejected by CORS security policy.");
  assert.equal(response.headers["access-control-allow-origin"], undefined);
});

test("CORS does not allow private-network origins in production", async () => {
  const originalNodeEnv = process.env.NODE_ENV;
  process.env.NODE_ENV = "production";

  try {
    const response = await request
      .get("/api/health")
      .set("Origin", "http://192.168.1.42:5173");

    assert.equal(response.status, 403);
    assert.equal(response.headers["access-control-allow-origin"], undefined);
  } finally {
    process.env.NODE_ENV = originalNodeEnv;
  }
});
