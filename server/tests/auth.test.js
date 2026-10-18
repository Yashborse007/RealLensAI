/**
 * RealLens AI — Backend Auth Tests
 * Coverage: register, login, /me, token guards, edge cases
 * Uses: node:test + supertest (no MongoDB required — in-memory store fallback)
 */
import test from "node:test";
import assert from "node:assert/strict";
import jwt from "jsonwebtoken";
import supertest from "supertest";
import app from "../app.js";

const request = supertest(app);
const JWT_SECRET =
  process.env.JWT_SECRET || "reallens_ai_jwt_secret_key_change_in_production";

// ─── Helpers ────────────────────────────────────────────────────────────────

const uniqueEmail = (prefix = "user") =>
  `${prefix}_${Date.now()}_${Math.floor(Math.random() * 9999)}@test.reallens.ai`;

const makeToken = (payload = {}, opts = {}) =>
  jwt.sign({ id: "user_test", role: "user", ...payload }, JWT_SECRET, {
    expiresIn: "1h",
    ...opts,
  });

// ─── Registration ────────────────────────────────────────────────────────────

test("POST /api/auth/register — valid payload creates user + returns JWT", async () => {
  const email = uniqueEmail("register_ok");

  const res = await request.post("/api/auth/register").send({
    name: "Test Analyst",
    email,
    password: "SecurePass1",
  });

  test("POST /api/auth/register — Gmail plus alias is normalized and can sign in", async () => {
    const email = `RealLens.User+${Date.now()}@GMAIL.COM`;
    const password = "SecurePass1";

    const registration = await request.post("/api/auth/register").send({
      name: "Gmail Analyst",
      email,
      password,
    });

    assert.equal(registration.status, 201);
    assert.equal(registration.body.user.email, email.toLowerCase());

    const login = await request.post("/api/auth/login").send({
      email: email.toLowerCase(),
      password,
    });

    assert.equal(login.status, 200);
    assert.equal(login.body.user.email, email.toLowerCase());
  });

  assert.equal(res.status, 201, `Expected 201, got ${res.status}: ${JSON.stringify(res.body)}`);
  assert.equal(res.body.success, true);
  assert.ok(res.body.token, "JWT token must be present in response");
  assert.equal(res.body.user.email, email.toLowerCase());
  assert.equal(res.body.user.role, "user", "Default role must be 'user'");
  assert.ok(res.body.user.id, "User id must be present");
  assert.ok(!res.body.user.passwordHash, "Password hash must not be exposed");
});

test("POST /api/auth/register — duplicate email returns 400", async () => {
  const email = uniqueEmail("dup");

  await request.post("/api/auth/register").send({
    name: "First User",
    email,
    password: "Password1",
  });

  const res = await request.post("/api/auth/register").send({
    name: "Second User",
    email, // same email
    password: "Password2",
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /already registered/i);
});

test("POST /api/auth/register — missing name returns 400", async () => {
  const res = await request.post("/api/auth/register").send({
    email: uniqueEmail("noname"),
    password: "Password1",
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /name|email|password/i);
});

test("POST /api/auth/register — missing email returns 400", async () => {
  const res = await request.post("/api/auth/register").send({
    name: "No Email",
    password: "Password1",
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
});

test("POST /api/auth/register — missing password returns 400", async () => {
  const res = await request.post("/api/auth/register").send({
    name: "No Pass",
    email: uniqueEmail("nopass"),
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
});

test("POST /api/auth/register — invalid email format returns 400", async () => {
  const res = await request.post("/api/auth/register").send({
    name: "Bad Email",
    email: "not-an-email",
    password: "Password1",
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /valid email/i);
});

test("POST /api/auth/register — short password (< 6 chars) returns 400", async () => {
  const res = await request.post("/api/auth/register").send({
    name: "Short Pass",
    email: uniqueEmail("shortpass"),
    password: "abc",
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /at least 6/i);
});

test("POST /api/auth/register — role is normalized to 'user' when not provided", async () => {
  const res = await request.post("/api/auth/register").send({
    name: "No Role User",
    email: uniqueEmail("norole"),
    password: "Password1",
  });

  assert.equal(res.status, 201);
  assert.equal(res.body.user.role, "user");
});

test("POST /api/auth/register — public registration cannot grant admin role", async () => {
  const res = await request.post("/api/auth/register").send({
    name: "Admin User",
    email: uniqueEmail("adminreg"),
    password: "AdminPass1",
    role: "admin",
  });

  assert.equal(res.status, 201);
  assert.equal(res.body.user.role, "user");
});

// ─── Login ───────────────────────────────────────────────────────────────────

test("POST /api/auth/login — correct credentials return 200 + JWT", async () => {
  const email = uniqueEmail("login_ok");
  const password = "MyPass123";

  await request.post("/api/auth/register").send({ name: "Login OK", email, password });

  const res = await request.post("/api/auth/login").send({ email, password });

  assert.equal(res.status, 200, `Expected 200, got ${res.status}: ${JSON.stringify(res.body)}`);
  assert.equal(res.body.success, true);
  assert.ok(res.body.token, "JWT token must be present");
  assert.equal(res.body.user.email, email.toLowerCase());
});

test("POST /api/auth/register and /login — syntactically valid dummy email needs no inbox verification", async () => {
  const email = `Siddhesh.Bidve+${Date.now()}@example.invalid`;
  const password = "sidd@123";

  const registration = await request.post("/api/auth/register").send({
    name: "Siddhesh Bidve",
    email,
    password,
  });

  assert.equal(
    registration.status,
    201,
    `Registration failed: ${JSON.stringify(registration.body)}`,
  );
  assert.equal(registration.body.user.email, email.toLowerCase());
  assert.ok(registration.body.token);

  const login = await request.post("/api/auth/login").send({
    email: email.toUpperCase(),
    password,
  });

  assert.equal(login.status, 200, `Login failed: ${JSON.stringify(login.body)}`);
  assert.equal(login.body.user.email, email.toLowerCase());
  assert.ok(login.body.token);
});

test("POST /api/auth/login — wrong password returns 401", async () => {
  const email = uniqueEmail("wrongpass");

  await request.post("/api/auth/register").send({
    name: "WrongPass",
    email,
    password: "CorrectPass1",
  });

  const res = await request.post("/api/auth/login").send({
    email,
    password: "WrongPass1",
  });

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /invalid email or password/i);
});

test("POST /api/auth/login — non-existent user returns 401", async () => {
  const res = await request.post("/api/auth/login").send({
    email: "ghost_user_nobody@test.com",
    password: "SomePass1",
  });

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

test("POST /api/auth/login — missing email returns 400", async () => {
  const res = await request.post("/api/auth/login").send({
    password: "SomePass1",
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
});

test("POST /api/auth/login — missing password returns 400", async () => {
  const res = await request.post("/api/auth/login").send({
    email: uniqueEmail("nopwdlogin"),
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
});

test("POST /api/auth/login — malformed email returns 400", async () => {
  const res = await request.post("/api/auth/login").send({
    email: "plainstring",
    password: "SomePass1",
  });

  assert.equal(res.status, 400);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /valid email/i);
});

// ─── /me (protected profile) ─────────────────────────────────────────────────

test("GET /api/auth/me — valid token returns user profile", async () => {
  const email = uniqueEmail("getme");
  const regRes = await request.post("/api/auth/register").send({
    name: "Get Me User",
    email,
    password: "GetMe1234",
  });

  const token = regRes.body.token;
  const res = await request
    .get("/api/auth/me")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  assert.equal(res.body.success, true);
  assert.ok(res.body.user, "user object must be present");
  assert.equal(res.body.user.email, email.toLowerCase());
});

test("GET /api/auth/me — no Authorization header returns 401", async () => {
  const res = await request.get("/api/auth/me");

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /authorization header|no authorization/i);
});

test("GET /api/auth/me — malformed Bearer token returns 401", async () => {
  const res = await request
    .get("/api/auth/me")
    .set("Authorization", "Bearer this.is.not.valid");

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /invalid|expired/i);
});

test("GET /api/auth/me — expired token returns 401", async () => {
  const expiredToken = jwt.sign(
    { id: "user_expired", role: "user" },
    JWT_SECRET,
    { expiresIn: "0s" }
  );

  // Short delay to ensure token has expired
  await new Promise((r) => setTimeout(r, 50));

  const res = await request
    .get("/api/auth/me")
    .set("Authorization", `Bearer ${expiredToken}`);

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

test("GET /api/auth/me — token signed with wrong secret returns 401", async () => {
  const wrongToken = jwt.sign({ id: "user_bad", role: "user" }, "wrong_secret");

  const res = await request
    .get("/api/auth/me")
    .set("Authorization", `Bearer ${wrongToken}`);

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

// ─── Health endpoint ──────────────────────────────────────────────────────────

test("GET /api/health — returns 200 with service name", async () => {
  const res = await request.get("/api/health");

  assert.equal(res.status, 200);
  assert.equal(res.body.success, true);
  assert.ok(res.body.service, "service name must be in response");
  assert.equal(res.body.status, "running");
});
