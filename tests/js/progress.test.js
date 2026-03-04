import test from "node:test";
import assert from "node:assert/strict";

const { evolveProgressState } = await import("../../webui/js/progress.js");

test("evolveProgressState starts timer when moving to in_progress", () => {
  const next = evolveProgressState(null, "in_progress", "Working", "", 1_000);
  assert.equal(next.status, "in_progress");
  assert.equal(next.startedAt, 1_000);
  assert.equal(next.elapsedMs, 0);
  assert.equal(next.message, "Working");
});

test("evolveProgressState finalizes elapsed time when completed", () => {
  const prev = {
    status: "in_progress",
    startedAt: 1_000,
    elapsedMs: 0,
    message: "Working",
    error: "",
  };
  const next = evolveProgressState(prev, "completed", "Done", "", 3_500);
  assert.equal(next.status, "completed");
  assert.equal(next.startedAt, null);
  assert.equal(next.elapsedMs, 2_500);
  assert.equal(next.message, "Done");
});

test("evolveProgressState keeps previous message when empty message supplied", () => {
  const prev = {
    status: "pending",
    startedAt: null,
    elapsedMs: 0,
    message: "Pending",
    error: "",
  };
  const next = evolveProgressState(prev, "failed", "", "Boom", 2_000);
  assert.equal(next.message, "Pending");
  assert.equal(next.error, "Boom");
});
