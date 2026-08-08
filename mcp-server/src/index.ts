#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import type { ApiEntry } from "./types.js";
import { summarize } from "./types.js";
import { search, applyFilters } from "./search.js";

const here = dirname(fileURLToPath(import.meta.url));
const dataset: { generated: string; count: number; apis: ApiEntry[] } = JSON.parse(
  readFileSync(join(here, "..", "data", "apis.json"), "utf8"),
);
const APIS = dataset.apis;

const filterShape = {
  category: z.string().optional().describe("Restrict to one category (see list_categories)"),
  free_only: z.boolean().optional().describe("Only APIs with a usable free tier"),
  no_auth_only: z.boolean().optional().describe("Only APIs requiring no authentication at all"),
  cors_only: z.boolean().optional().describe("Only APIs confirmed callable from browsers (CORS)"),
  limit: z.number().int().min(1).max(25).optional().describe("Max results (default 8)"),
};

function json(payload: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(payload, null, 1) }] };
}

const server = new McpServer({ name: "apidex", version: "0.1.0" });

server.registerTool(
  "search_apis",
  {
    title: "Search public APIs",
    description:
      "Search a verified directory of public APIs by keyword (name, purpose, category). " +
      "Every entry was cross-checked by independent verification passes. " +
      "Returns compact summaries; call get_api for full details including a working example request.",
    inputSchema: {
      query: z.string().describe("Keywords, e.g. 'weather forecast' or 'stock prices'"),
      ...filterShape,
    },
  },
  async ({ query, limit, ...filters }) => {
    const hits = search(APIS, query, filters, limit ?? 8);
    if (hits.length === 0) {
      return json({ results: [], hint: "No matches. Try broader keywords or list_categories." });
    }
    return json({ results: hits.map(summarize) });
  },
);

server.registerTool(
  "find_api_for_task",
  {
    title: "Find an API for a task",
    description:
      "Describe what you're trying to build or fetch in plain language (e.g. 'convert an address " +
      "to coordinates for free without an API key') and get the best-matching verified public APIs. " +
      "Prefer this over search_apis when you have a goal rather than a known API name.",
    inputSchema: {
      task: z.string().describe("The task, in plain language"),
      ...filterShape,
    },
  },
  async ({ task, limit, ...filters }) => {
    const hits = search(APIS, task, filters, limit ?? 5);
    if (hits.length === 0) {
      return json({ results: [], hint: "No matches. Try different wording or drop filters." });
    }
    return json({
      results: hits.map((e) => ({ ...summarize(e), use_cases: e.use_cases })),
      next: "Call get_api with an id for auth details, rate limits, and a working example request.",
    });
  },
);

server.registerTool(
  "get_api",
  {
    title: "Get full API details",
    description:
      "Full verified record for one API: base URL, auth, pricing/free tier, rate limits, CORS, " +
      "a working example request, docs link, and the verification record showing which fields " +
      "were independently confirmed.",
    inputSchema: { id: z.string().describe("The API id from search results") },
  },
  async ({ id }) => {
    const e = APIS.find((a) => a.id === id);
    if (!e) {
      const near = search(APIS, id.replace(/-/g, " "), {}, 3).map((a) => a.id);
      return json({ error: `No API with id '${id}'`, did_you_mean: near });
    }
    return json(e);
  },
);

server.registerTool(
  "list_categories",
  {
    title: "List API categories",
    description: "All categories in the directory with entry counts, plus dataset stats.",
    inputSchema: {},
  },
  async () => {
    const counts: Record<string, number> = {};
    for (const e of applyFilters(APIS, {})) counts[e.category] = (counts[e.category] ?? 0) + 1;
    return json({
      generated: dataset.generated,
      total: APIS.length,
      categories: Object.fromEntries(Object.entries(counts).sort((a, b) => b[1] - a[1])),
    });
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
