import type { ApiEntry } from "./types.js";

export interface SearchFilters {
  category?: string;
  free_only?: boolean;
  no_auth_only?: boolean;
  cors_only?: boolean;
}

const STOP = new Set([
  "a", "an", "the", "for", "to", "of", "in", "on", "with", "and", "or",
  "api", "apis", "data", "get", "find", "i", "need", "want", "that", "which",
  "some", "any", "my", "me", "using", "use",
]);

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((t) => t.length > 1 && !STOP.has(t));
}

function fieldTokens(e: ApiEntry): { name: Set<string>; use: Set<string>; tag: Set<string>; desc: Set<string>; cat: Set<string> } {
  return {
    name: new Set(tokenize(e.name + " " + e.id)),
    use: new Set(tokenize(e.use_cases.join(" "))),
    tag: new Set(tokenize(e.tagline)),
    desc: new Set(tokenize(e.description)),
    cat: new Set(tokenize(e.category)),
  };
}

/** Score one entry against query tokens. Field-weighted token overlap with a
 * small bonus for matching a high proportion of the query. */
export function score(e: ApiEntry, qTokens: string[]): number {
  if (qTokens.length === 0) return 0;
  const f = fieldTokens(e);
  let s = 0;
  let matched = 0;
  for (const t of qTokens) {
    let hit = 0;
    if (f.name.has(t)) hit = Math.max(hit, 5);
    if (f.use.has(t)) hit = Math.max(hit, 4);
    if (f.tag.has(t)) hit = Math.max(hit, 3);
    if (f.cat.has(t)) hit = Math.max(hit, 2);
    if (f.desc.has(t)) hit = Math.max(hit, 1);
    if (hit === 0 && t.length >= 4) {
      // prefix match fallback: query token "geocod" matches indexed "geocoding"
      for (const set of [f.name, f.use, f.tag, f.desc]) {
        for (const w of set) {
          if (w.startsWith(t)) { hit = Math.max(hit, 1); break; }
        }
        if (hit) break;
      }
    }
    if (hit > 0) matched++;
    s += hit;
  }
  return s * (1 + matched / qTokens.length);
}

export function applyFilters(entries: ApiEntry[], f: SearchFilters): ApiEntry[] {
  return entries.filter((e) => {
    if (e.status === "defunct") return false;
    if (f.category && e.category !== f.category) return false;
    if (f.free_only && !e.pricing.free_tier) return false;
    if (f.no_auth_only && e.auth.type !== "none") return false;
    if (f.cors_only && e.cors !== "yes") return false;
    return true;
  });
}

export function search(entries: ApiEntry[], query: string, filters: SearchFilters, limit: number): ApiEntry[] {
  const q = tokenize(query);
  return applyFilters(entries, filters)
    .map((e) => ({ e, s: score(e, q) }))
    .filter((r) => r.s > 0)
    .sort((a, b) => b.s - a.s || a.e.name.localeCompare(b.e.name))
    .slice(0, limit)
    .map((r) => r.e);
}
