/**
 * RealLens AI — Analysis CRUD, History & Filtering Tests
 * Coverage: create, retrieve, paginate, filter by type/result, sort, search,
 *           cross-user access, delete, unauthorized access, report path storage.
 * Uses: node:test + supertest (in-memory store fallback — no MongoDB needed)
 */
import test from "node:test";
import assert from "node:assert/strict";
import supertest from "supertest";
import app from "../app.js";

const request = supertest(app);

// ─── Helpers ─────────────────────────────────────────────────────────────────

const uniqueEmail = (prefix = "analysis") =>
  `${prefix}_${Date.now()}_${Math.floor(Math.random() * 9999)}@test.reallens.ai`;

/**
 * Register a test user and return their JWT token + userId.
 */
const registerUser = async (prefix = "analyst") => {
  const res = await request.post("/api/auth/register").send({
    name: "Test Analyst",
    email: uniqueEmail(prefix),
    password: "Analyst1234",
  });
  assert.equal(res.status, 201, `Register failed: ${JSON.stringify(res.body)}`);
  return { token: res.body.token, userId: res.body.user.id };
};

/**
 * Create an analysis record for the authenticated user.
 */
const createAnalysis = (token, overrides = {}) =>
  request
    .post("/api/analyses")
    .set("Authorization", `Bearer ${token}`)
    .send({
      mediaId: `med_${Date.now()}`,
      mediaType: "image",
      filename: "sample_face.jpg",
      status: "COMPLETED",
      prediction: "FAKE",
      confidence: 0.87,
      quality: "GOOD",
      qualityScore: 0.82,
      facesDetected: 1,
      processingTime: 1430,
      modelVersion: "AIDE-CNN-v1.0",
      ...overrides,
    });

// ─── Create Analysis ──────────────────────────────────────────────────────────

test("POST /api/analyses — creates record and returns normalized fields", async () => {
  const { token } = await registerUser("create");
  const res = await createAnalysis(token);

  assert.equal(res.status, 201, `Expected 201, got ${res.status}: ${JSON.stringify(res.body)}`);
  assert.ok(res.body.id, "id must be present");
  assert.equal(res.body.prediction, "FAKE");
  assert.equal(res.body.status, "COMPLETED");
  assert.equal(res.body.mediaType, "image");
  assert.ok(typeof res.body.confidence === "number");
});

test("POST /api/analyses — prediction value 'fake' is normalized to 'FAKE'", async () => {
  const { token } = await registerUser("norm_fake");
  const res = await createAnalysis(token, { prediction: "fake" });

  assert.equal(res.status, 201);
  assert.equal(res.body.prediction, "FAKE");
});

test("POST /api/analyses — prediction 'REAL' is accepted", async () => {
  const { token } = await registerUser("real_pred");
  const res = await createAnalysis(token, { prediction: "REAL", mediaType: "video" });

  assert.equal(res.status, 201);
  assert.equal(res.body.prediction, "REAL");
});

test("POST /api/analyses — unknown prediction becomes 'UNCERTAIN'", async () => {
  const { token } = await registerUser("uncertain_pred");
  const res = await createAnalysis(token, { prediction: "MAYBE" });

  assert.equal(res.status, 201);
  assert.equal(res.body.prediction, "UNCERTAIN");
});

test("POST /api/analyses — report path stored and returned", async () => {
  const { token } = await registerUser("report_path");
  const res = await createAnalysis(token, {
    reportPath: "reports/rl_report_12345.pdf",
  });

  assert.equal(res.status, 201);
  assert.ok(res.body.reportPath !== undefined, "reportPath must exist in response");
});

// ─── Get Analysis History ─────────────────────────────────────────────────────

test("GET /api/analyses — returns paginated list for authenticated user", async () => {
  const { token } = await registerUser("hist");

  // Create 3 records
  await createAnalysis(token, { filename: "file_a.jpg" });
  await createAnalysis(token, { filename: "file_b.jpg" });
  await createAnalysis(token, { filename: "file_c.jpg" });

  const res = await request
    .get("/api/analyses?page=1&limit=10")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  assert.equal(res.body.success, true);
  assert.ok(Array.isArray(res.body.data), "data must be an array");
  assert.ok(res.body.data.length >= 3, `Expected >= 3 records, got ${res.body.data.length}`);
  assert.ok(typeof res.body.total === "number");
  assert.ok(typeof res.body.totalPages === "number");
  assert.ok(typeof res.body.page === "number");
});

test("GET /api/analyses — pagination: page=1&limit=2 returns max 2 records", async () => {
  const { token } = await registerUser("paginate");

  for (let i = 0; i < 5; i++) {
    await createAnalysis(token, { filename: `paged_file_${i}.jpg` });
  }

  const res = await request
    .get("/api/analyses?page=1&limit=2")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  assert.ok(
    res.body.data.length <= 2,
    `Expected at most 2 results, got ${res.body.data.length}`
  );
  assert.equal(res.body.limit, 2);
});

test("GET /api/analyses — filter by mediaType=video returns only video records", async () => {
  const { token } = await registerUser("filter_type");

  await createAnalysis(token, { mediaType: "image", filename: "img.jpg" });
  await createAnalysis(token, { mediaType: "video", filename: "vid.mp4" });
  await createAnalysis(token, { mediaType: "video", filename: "vid2.mp4" });

  const res = await request
    .get("/api/analyses?mediaType=video")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  const nonVideo = res.body.data.filter((d) => d.mediaType !== "video");
  assert.equal(
    nonVideo.length,
    0,
    `Filter returned non-video records: ${JSON.stringify(nonVideo)}`
  );
});

test("GET /api/analyses — filter by result=fake returns only FAKE records", async () => {
  const { token } = await registerUser("filter_result");

  await createAnalysis(token, { prediction: "REAL", filename: "real.jpg" });
  await createAnalysis(token, { prediction: "FAKE", filename: "fake.jpg" });
  await createAnalysis(token, { prediction: "FAKE", filename: "fake2.jpg" });

  const res = await request
    .get("/api/analyses?result=fake")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  const nonFake = res.body.data.filter(
    (d) => d.prediction !== "FAKE"
  );
  assert.equal(
    nonFake.length,
    0,
    `Filter returned non-FAKE records: ${JSON.stringify(nonFake)}`
  );
});

test("GET /api/analyses — sort=oldest returns items in ascending createdAt order", async () => {
  const { token } = await registerUser("sort_oldest");

  for (let i = 0; i < 3; i++) {
    await createAnalysis(token, { filename: `sorted_${i}.jpg` });
    await new Promise((r) => setTimeout(r, 10)); // ensure distinct timestamps
  }

  const res = await request
    .get("/api/analyses?sort=oldest&limit=50")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  const dates = res.body.data.map((d) => new Date(d.createdAt).getTime());
  for (let i = 1; i < dates.length; i++) {
    assert.ok(
      dates[i] >= dates[i - 1],
      `Records are not sorted oldest-first: ${dates[i - 1]} > ${dates[i]}`
    );
  }
});

test("GET /api/analyses — search by filename returns matching records", async () => {
  const { token } = await registerUser("search");

  await createAnalysis(token, { filename: "unique_target_file_xyz.jpg" });
  await createAnalysis(token, { filename: "other_file.jpg" });

  const res = await request
    .get("/api/analyses?search=unique_target")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  const hasTarget = res.body.data.some((d) =>
    (d.filename || d.fileName || "").includes("unique_target")
  );
  assert.ok(hasTarget, "Search should return the file with matching filename");
});

// ─── Get Single Analysis ──────────────────────────────────────────────────────

test("GET /api/analyses/:id — returns correct record for owner", async () => {
  const { token } = await registerUser("getbyid");

  const created = await createAnalysis(token, { filename: "getbyid.jpg" });
  const id = created.body.id;

  const res = await request
    .get(`/api/analyses/${id}`)
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  assert.equal(res.body.id || res.body._id, id);
});

test("GET /api/analyses/:id — returns 404 for non-existent ID", async () => {
  const { token } = await registerUser("notfound");

  const res = await request
    .get("/api/analyses/nonexistent_id_999999")
    .set("Authorization", `Bearer ${token}`);

  assert.ok(
    res.status === 404 || res.status === 400,
    `Expected 404/400, got ${res.status}`
  );
  assert.equal(res.body.success, false);
});

test("GET /api/analyses/:id — user B cannot access user A's record", async () => {
  const userA = await registerUser("crossuser_a");
  const userB = await registerUser("crossuser_b");

  // User A creates an analysis
  const created = await createAnalysis(userA.token, { filename: "private.jpg" });
  const id = created.body.id;

  // User B tries to access it
  const res = await request
    .get(`/api/analyses/${id}`)
    .set("Authorization", `Bearer ${userB.token}`);

  assert.ok(
    res.status === 404 || res.status === 403,
    `Expected 404/403 for cross-user access, got ${res.status}`
  );
  assert.equal(res.body.success, false);
});

// ─── Delete Analysis ──────────────────────────────────────────────────────────

test("DELETE /api/analyses/:id — owner can delete own record", async () => {
  const { token } = await registerUser("delete_own");

  const created = await createAnalysis(token, { filename: "to_delete.jpg" });
  const id = created.body.id;

  const res = await request
    .delete(`/api/analyses/${id}`)
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  assert.equal(res.body.success, true);
});

test("DELETE /api/analyses/:id — user B cannot delete user A's record", async () => {
  const userA = await registerUser("del_a");
  const userB = await registerUser("del_b");

  const created = await createAnalysis(userA.token, { filename: "a_private.jpg" });
  const id = created.body.id;

  const res = await request
    .delete(`/api/analyses/${id}`)
    .set("Authorization", `Bearer ${userB.token}`);

  assert.ok(
    res.status === 404 || res.status === 403,
    `Expected 404/403, got ${res.status}`
  );
  assert.equal(res.body.success, false);
});

test("DELETE /api/analyses/:id — deleting non-existent ID returns 404", async () => {
  const { token } = await registerUser("del_missing");

  const res = await request
    .delete("/api/analyses/totally_fake_id_000")
    .set("Authorization", `Bearer ${token}`);

  assert.ok(
    res.status === 404 || res.status === 400,
    `Expected 404/400, got ${res.status}`
  );
  assert.equal(res.body.success, false);
});

// ─── Unauthenticated ─────────────────────────────────────────────────────────

test("GET /api/analyses — no token returns 401", async () => {
  const res = await request.get("/api/analyses");

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});

test("POST /api/analyses — no token returns 401", async () => {
  const res = await request.post("/api/analyses").send({
    mediaId: "med_test",
    mediaType: "image",
    filename: "test.jpg",
  });

  assert.equal(res.status, 401);
  assert.equal(res.body.success, false);
});
