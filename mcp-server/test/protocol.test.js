import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

/** Minimal JSON-RPC-over-stdio client: send requests, collect responses by id. */
function rpcSession(requests) {
  return new Promise((resolve, reject) => {
    const proc = spawn("node", [fileURLToPath(new URL("../dist/index.js", import.meta.url))], {
      stdio: ["pipe", "pipe", "inherit"],
    });
    const responses = new Map();
    let buf = "";
    const wanted = requests.filter((r) => r.id !== undefined).length;
    proc.stdout.on("data", (d) => {
      buf += d.toString();
      let nl;
      while ((nl = buf.indexOf("\n")) !== -1) {
        const line = buf.slice(0, nl);
        buf = buf.slice(nl + 1);
        if (!line.trim()) continue;
        const msg = JSON.parse(line);
        if (msg.id !== undefined) responses.set(msg.id, msg);
        if (responses.size === wanted) {
          proc.kill();
          resolve(responses);
        }
      }
    });
    proc.on("error", reject);
    const timer = setTimeout(() => { proc.kill(); reject(new Error("rpc timeout")); }, 10000);
    proc.on("exit", () => clearTimeout(timer));
    for (const r of requests) proc.stdin.write(JSON.stringify(r) + "\n");
  });
}

const init = {
  jsonrpc: "2.0", id: 1, method: "initialize",
  params: { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "test", version: "0" } },
};
const initialized = { jsonrpc: "2.0", method: "notifications/initialized" };

test("initialize + tools/list exposes the four tools", async () => {
  const rs = await rpcSession([init, initialized, { jsonrpc: "2.0", id: 2, method: "tools/list" }]);
  assert.equal(rs.get(1).result.serverInfo.name, "apidex");
  const names = rs.get(2).result.tools.map((t) => t.name).sort();
  assert.deepEqual(names, ["find_api_for_task", "get_api", "list_categories", "search_apis"]);
});

test("tools/call find_api_for_task returns results with ids", async () => {
  const rs = await rpcSession([init, initialized, {
    jsonrpc: "2.0", id: 3, method: "tools/call",
    params: { name: "find_api_for_task", arguments: { task: "get current weather for a city", free_only: true } },
  }]);
  const payload = JSON.parse(rs.get(3).result.content[0].text);
  assert.ok(payload.results.length >= 1);
  assert.ok(payload.results.some((r) => r.id === "open-meteo"),
    `expected open-meteo in results, got ${payload.results.map((r) => r.id)}`);
  assert.ok(payload.results.every((r) => typeof r.id === "string" && r.use_cases.length > 0));
});

test("'without an API key' task wording boosts no-auth APIs to the top", async () => {
  const rs = await rpcSession([init, initialized, {
    jsonrpc: "2.0", id: 5, method: "tools/call",
    params: { name: "find_api_for_task", arguments: { task: "get current weather for a city without an API key" } },
  }]);
  const payload = JSON.parse(rs.get(5).result.content[0].text);
  assert.ok(payload.results.length >= 1);
  assert.equal(payload.results[0].auth, "none",
    `expected a no-auth API first, got ${payload.results.map((r) => `${r.id}(${r.auth})`)}`);
});

test("tools/call get_api unknown id suggests alternatives", async () => {
  const rs = await rpcSession([init, initialized, {
    jsonrpc: "2.0", id: 4, method: "tools/call",
    params: { name: "get_api", arguments: { id: "open-meteo-wrong" } },
  }]);
  const payload = JSON.parse(rs.get(4).result.content[0].text);
  assert.ok(payload.error.includes("open-meteo-wrong"));
  assert.ok(payload.did_you_mean.includes("open-meteo"));
});
