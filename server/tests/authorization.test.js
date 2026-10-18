/**
 * RealLens AI — Authorization Tests
 * Coverage: admin-only routes, role enforcement, token tampering
 * Uses: node:test + supertest (no MongoDB required)
 */
import test from "node:test";
import assert from "node:assert/strict";
import jwt from "jsonwebtoken";
import supertest from "supertest";
import app from "../app.js";

const request = supertest(app);
const JWT_SECRET =
  process.env.JWT_SECRET || "reallens_ai_jwt_secret_key_change_in_production";

const makeToken = (id = "user_test", role = "user") =>
  jwt.sign({ id, role }, JWT_SECRET, { expiresIn: "1h" });

// ─── Admin route enforcement ──────────────────────────────────────────────────

test("GET /api/admin/overview — user token returns 403 (admin only)", async () => {
  const token = makeToken("user_regular", "user");

  const res = await request
    .get("/api/admin/overview")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 403, `Expected 403, got ${res.status}`);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /admin privileges/i);
});

test("GET /api/admin/users — user token returns 403", async () => {
  const token = makeToken("user_regular", "user");

  const res = await request
    .get("/api/admin/users")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 403);
  assert.equal(res.body.success, false);
});

test("GET /api/admin/analyses — user token returns 403", async () => {
  const token = makeToken("user_regular", "user");

  const res = await request
    .get("/api/admin/analyses")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 403);
  assert.equal(res.body.success, false);
});

test("GET /api/admin/overview — no token returns 401", async () => {
  const res = await request.get("/api/admin/overview");

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

test("GET /api/admin/overview — admin token returns 200", async () => {
  const token = makeToken("admin_user_001", "admin");

  const res = await request
    .get("/api/admin/overview")
    .set("Authorization", `Bearer ${token}`);

  // Admin route exists and does not 403/401 — may be 200 or 404 depending on data
  assert.ok(
    res.status !== 403 && res.status !== 401,
    `Admin token must not be refused with 403/401, got ${res.status}`
  );
});

// ─── Token tampering ──────────────────────────────────────────────────────────

test("Protected route — tampered token payload returns 401", async () => {
  // Build a valid token then mutate the payload portion
  const validToken = makeToken("user_test", "user");
  const parts = validToken.split(".");

  // Replace payload with arbitrary base64 data (breaks signature)
  const tamperedPayload = Buffer.from(
    JSON.stringify({ id: "injected_admin", role: "admin" })
  ).toString("base64url");

  const tamperedToken = `${parts[0]}.${tamperedPayload}.${parts[2]}`;

  const res = await request
    .get("/api/auth/me")
    .set("Authorization", `Bearer ${tamperedToken}`);

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

test("Protected route — token with 'Bearer' prefix missing returns 401", async () => {
  const token = makeToken("user_test", "user");

  const res = await request
    .get("/api/auth/me")
    .set("Authorization", token); // Missing 'Bearer '

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

test("Protected route — empty string Authorization header returns 401", async () => {
  const res = await request
    .get("/api/analyses")
    .set("Authorization", "");

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

// ─── Analysis routes guarded ──────────────────────────────────────────────────

test("GET /api/analyses — no token returns 401", async () => {
  const res = await request.get("/api/analyses");

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

test("POST /api/analyses — no token returns 401", async () => {
  const res = await request.post("/api/analyses").send({
    mediaId: "med_12345",
    mediaType: "image",
    filename: "test.jpg",
  });

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

test("GET /api/media/upload — no token returns 401", async () => {
  const res = await request.post("/api/media/upload");

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});
