export interface ApiEntry {
  id: string;
  name: string;
  category: string;
  tagline: string;
  description: string;
  status: "operational" | "degraded" | "defunct";
  base_url: string;
  docs_url: string;
  signup_url?: string | null;
  auth: { type: "none" | "apiKey" | "oauth2" | "basic" | "jwt" | "other"; details: string };
  https: boolean;
  cors: "yes" | "no" | "unknown";
  formats: string[];
  pricing: { free_tier: boolean; free_tier_limits: string; paid_plans?: string | null };
  rate_limits: string;
  example: { request: string; response_snippet: string };
  use_cases: string[];
  sources: string[];
  researcher_confidence: "high" | "medium" | "low";
  verification: {
    mode: "double-confirmed" | "adjudicated";
    last_checked: string;
    confirmed_by_both: string[];
    corrected: string[];
    unverifiable: string[];
  };
}

/** Compact shape returned by search tools — keeps agent context small. */
export interface ApiSummary {
  id: string;
  name: string;
  tagline: string;
  category: string;
  auth: string;
  free_tier: boolean;
  cors: string;
  verification: string;
}

export function summarize(e: ApiEntry): ApiSummary {
  return {
    id: e.id,
    name: e.name,
    tagline: e.tagline,
    category: e.category,
    auth: e.auth.type,
    free_tier: e.pricing.free_tier,
    cors: e.cors,
    verification: e.verification.mode,
  };
}
