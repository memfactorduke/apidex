import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { search, tokenize, applyFilters, score } from "../dist/search.js";

const { apis } = JSON.parse(readFileSync(new URL("../data/apis.json", import.meta.url), "utf8"));

test("tokenize drops stopwords and short tokens", () => {
  assert.deepEqual(tokenize("I need an API for the weather"), ["weather"]);
});

test("weather query surfaces weather APIs at the top", () => {
  const hits = search(apis, "current weather forecast", {}, 5);
  assert.ok(hits.length >= 1);
  assert.ok(hits.some((h) => h.category === "weather-environment"),
    `expected weather APIs, got ${hits.map((h) => h.id)}`);
});

test("task phrasing matches use_cases", () => {
  const hits = search(apis, "get stock price quotes", {}, 5);
  assert.ok(hits.length >= 1);
  const stockish = hits.slice(0, 3).filter(
    (h) => h.category === "finance" || h.use_cases.join(" ").includes("stock"));
  assert.ok(stockish.length >= 2, `expected stock APIs on top, got ${hits.map((h) => h.id)}`);
});

test("no_auth_only filter excludes keyed APIs", () => {
  const f = applyFilters(apis, { no_auth_only: true });
  assert.ok(f.every((e) => e.auth.type === "none"));
  assert.ok(f.some((e) => e.id === "open-meteo"));
});

test("category filter", () => {
  const f = applyFilters(apis, { category: "finance" });
  assert.ok(f.every((e) => e.category === "finance"));
});

test("irrelevant query returns nothing", () => {
  assert.deepEqual(search(apis, "zzzqqqxyzzy", {}, 5), []);
});

test("defunct entries are always excluded", () => {
  const dead = { ...apis[0], id: "dead-api", status: "defunct" };
  assert.deepEqual(applyFilters([dead], {}), []);
});

test("score is zero for empty query", () => {
  assert.equal(score(apis[0], []), 0);
});
