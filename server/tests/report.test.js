/**
 * RealLens AI — Report Generation Tests
 * Coverage: report path persistence, AI-unavailable handling, analyze endpoint
 * Uses: node:test + supertest
 */
import test from "node:test";
import assert from "node:assert/strict";
import supertest from "supertest";
import app from "../app.js";

const request = supertest(app);

// ─── Helpers ─────────────────────────────────────────────────────────────────

const uniqueEmail = (prefix = "report") =>
  `${prefix}_${Date.now()}_${Math.floor(Math.random() * 9999)}@test.reallens.ai`;

const registerUser = async (prefix = "reporter") => {
  const res = await request.post("/api/auth/register").send({
    name: "Reporter User",
    email: uniqueEmail(prefix),
    password: "Report1234",
  });
  assert.equal(res.status, 201, `Register failed: ${JSON.stringify(res.body)}`);
  return { token: res.body.token, userId: res.body.user.id };
};

// ─── Report path persisted in analysis record ─────────────────────────────────

test("POST /api/analyses — report path is stored and returned in create response", async () => {
  const { token } = await registerUser("rp_create");
  const reportPath = "reports/forensic_report_test_001.pdf";

  const res = await request
    .post("/api/analyses")
    .set("Authorization", `Bearer ${token}`)
    .send({
      mediaId: `med_${Date.now()}`,
      mediaType: "image",
      filename: "report_test.jpg",
      status: "COMPLETED",
      prediction: "FAKE",
      confidence: 0.91,
      quality: "GOOD",
      qualityScore: 0.85,
      reportPath,
    });

  assert.equal(res.status, 201, `Expected 201, got ${res.status}: ${JSON.stringify(res.body)}`);
  assert.ok(
    res.body.reportPath !== undefined,
    "reportPath field must exist in created record"
  );
});

test("GET /api/analyses/:id — retrieved record includes reportPath field", async () => {
  const { token } = await registerUser("rp_get");
  const reportPath = "reports/forensic_report_retrieve_test.pdf";

  // Create with report path
  const created = await request
    .post("/api/analyses")
    .set("Authorization", `Bearer ${token}`)
    .send({
      mediaId: `med_${Date.now()}`,
      mediaType: "video",
      filename: "report_retrieve.mp4",
      status: "COMPLETED",
      prediction: "REAL",
      confidence: 0.96,
      quality: "GOOD",
      qualityScore: 0.93,
      reportPath,
    });

  assert.equal(created.status, 201);
  const id = created.body.id;

  // Retrieve it
  const res = await request
    .get(`/api/analyses/${id}`)
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  assert.ok(
    "reportPath" in res.body,
    "reportPath must be present in retrieved analysis"
  );
});

test("POST /api/analyses — analysis without reportPath has empty string or undefined", async () => {
  const { token } = await registerUser("rp_empty");

  const res = await request
    .post("/api/analyses")
    .set("Authorization", `Bearer ${token}`)
    .send({
      mediaId: `med_${Date.now()}`,
      mediaType: "audio",
      filename: "audio_no_report.wav",
      status: "COMPLETED",
      prediction: "UNCERTAIN",
      confidence: 0.55,
      quality: "FAIR",
      qualityScore: 0.6,
      // No reportPath
    });

  assert.equal(res.status, 201);
  const rp = res.body.reportPath;
  assert.ok(
    rp === "" || rp === null || rp === undefined,
    `Expected empty/null reportPath, got: ${JSON.stringify(rp)}`
  );
});

// ─── AI service unavailable → analyze endpoint ────────────────────────────────

test("POST /api/media/analyze — returns 400 when mediaId is missing", async () => {
  const { token } = await registerUser("analyze_no_mid");

  const res = await request
    .post("/api/media/analyze")
    .set("Authorization", `Bearer ${token}`)
    .send({}); // no mediaId

  assert.equal(res.status, 400, `Expected 400, got ${res.status}`);
  assert.equal(res.body.success, false);
  assert.match(res.body.error, /media id|mediaId/i);
});

test("POST /api/media/analyze — unknown mediaId returns 404", async () => {
  const { token } = await registerUser("analyze_no_record");

  const res = await request
    .post("/api/media/analyze")
    .set("Authorization", `Bearer ${token}`)
    .send({ mediaId: "med_nonexistent_99999" });

  assert.ok(
    res.status === 404 || res.status === 400,
    `Expected 404/400 for unknown mediaId, got ${res.status}`
  );
  assert.equal(res.body.success, false);
});

test("POST /api/media/analyze — no token returns 401", async () => {
  const res = await request
    .post("/api/media/analyze")
    .send({ mediaId: "med_any" });

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

// ─── AI health endpoint ───────────────────────────────────────────────────────

test("GET /api/health/ai — returns JSON with aiServiceStatus field", async () => {
  const res = await request.get("/api/health/ai");

  // AI service may or may not be running — we assert on structure, not liveness
  assert.ok(
    res.status === 200 || res.status === 503,
    `Expected 200 or 503, got ${res.status}`
  );
  assert.ok(
    "aiServiceStatus" in res.body,
    "aiServiceStatus field must always be present"
  );
  assert.ok(
    res.body.aiServiceStatus === "reachable" ||
      res.body.aiServiceStatus === "unreachable",
    `aiServiceStatus must be 'reachable' or 'unreachable', got: ${res.body.aiServiceStatus}`
  );
});

test("GET /api/health/ai — when AI is unreachable returns 503 with error message", async () => {
  // We can't guarantee AI is down, but if it is we check the structure
  const res = await request.get("/api/health/ai");

  if (res.status === 503) {
    assert.equal(res.body.success, false);
    assert.ok(res.body.error, "Error message must be present when AI unreachable");
    assert.equal(res.body.aiServiceStatus, "unreachable");
  }
  // If 200, AI happened to be up — that's fine, not a failure
});
