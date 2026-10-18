import test from "node:test";
import assert from "node:assert/strict";
import supertest from "supertest";
import app from "../app.js";

const request = supertest(app);

const uniqueEmail = (prefix = "analytics") =>
  `${prefix}_${Date.now()}_${Math.floor(Math.random() * 9999)}@test.reallens.ai`;

const registerUser = async (prefix = "analyst") => {
  const res = await request.post("/api/auth/register").send({
    name: "Analytics Analyst",
    email: uniqueEmail(prefix),
    password: "Analyst1234",
  });
  assert.equal(res.status, 201);
  return { token: res.body.token, userId: res.body.user.id };
};

test("GET /api/analytics/dashboard — returns live user dashboard stats", async () => {
  const { token } = await registerUser("dash");

  // Create two analyses
  await request
    .post("/api/analyses")
    .set("Authorization", `Bearer ${token}`)
    .send({
      mediaId: `med_${Date.now()}_1`,
      mediaType: "image",
      prediction: "FAKE",
      confidence: 0.92,
    });

  await request
    .post("/api/analyses")
    .set("Authorization", `Bearer ${token}`)
    .send({
      mediaId: `med_${Date.now()}_2`,
      mediaType: "video",
      prediction: "REAL",
      confidence: 0.88,
    });

  const res = await request
    .get("/api/analytics/dashboard")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  assert.equal(res.body.success, true);
  assert.equal(res.body.isSampleData, false);
  assert.equal(res.body.totalAnalyses, 2);
  assert.equal(res.body.realMediaCount, 1);
  assert.equal(res.body.potentialDeepfakesCount, 1);
});

test("GET /api/analytics/distribution — returns 7-day distribution array", async () => {
  const { token } = await registerUser("dist");

  const res = await request
    .get("/api/analytics/distribution")
    .set("Authorization", `Bearer ${token}`);

  assert.equal(res.status, 200);
  assert.ok(Array.isArray(res.body));
  assert.equal(res.body.length, 7);
  assert.equal(res.body[0].name, "Mon");
});

test("GET /api/analytics/dashboard — unauthenticated returns 401", async () => {
  const res = await request.get("/api/analytics/dashboard");
  assert.equal(res.status, 401);
});
