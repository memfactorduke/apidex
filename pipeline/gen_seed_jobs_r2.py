#!/usr/bin/env python3
"""Generate round-2 seed jobs: 8 new categories + depth listers over the
existing 22 categories with per-category exclusion lists (what we already have)."""
import json, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NEW_CATEGORIES = {
    "legal-compliance": "case law, legislation search, sanctions/watchlists, trademarks, patents, company registries, KYC",
    "real-estate-housing": "property records, valuations, rentals, mortgage rates, zoning, housing market data",
    "jobs-careers": "job listings, salary data, resume parsing, skills taxonomies, hiring platforms",
    "energy-utilities": "electricity prices, grid/carbon intensity data, EV charging stations, solar/renewables, fuel prices",
    "agriculture": "crop and soil data, plant identification, livestock, farming markets, fisheries",
    "travel-hospitality": "hotels, bookings, tourist attractions, visas, travel advisories, currency for travel",
    "events-holidays": "public holidays, event listings, ticketing, conferences, calendar data",
    "iot-devices": "device clouds, MQTT/messaging for devices, GPS and asset tracking, smart-home platforms",
}

NEW_PROMPT = """You are compiling the seed list for a rigorously verified public-API directory (2026 edition).

Category: {cat} — {hint}

Use web search extensively. List 12 to 25 public HTTP APIs in this category that are CURRENTLY operational in 2026. Rules:
1. VERIFY each API still exists and is operational — search for its docs/status. Public APIs die constantly; a dead API in your list is a serious error. If unsure about one, leave it out. Quality over count: fewer real APIs beats padding the list.
2. Mix the famous staples every developer knows with lesser-known high-quality gems.
3. Only include APIs a third-party developer can actually call today (public, or self-serve signup). No internal-only, partner-only, waitlist-only, or sunset APIs.
4. docs_url must be the API's real, current documentation page.
5. free_tier is true only if a developer can make real calls at $0.
6. slug: lowercase-kebab-case unique identifier, e.g. "openweathermap".

Set category to exactly "{cat}"."""

DEPTH_PROMPT = """You are expanding one category of a rigorously verified public-API directory (2026 edition).

Category: {cat} — {hint}

The directory ALREADY CONTAINS these APIs — do NOT list any of them, nor alternate endpoints/mirrors of them:
{existing}

Use web search extensively. List 8 to 25 ADDITIONAL public HTTP APIs in this category that are CURRENTLY operational in 2026 and not in the list above. Rules:
1. VERIFY each API still exists and is operational — search for its docs/status. A dead API in your list is a serious error. Quality over count: if you can only find a handful of genuine new ones, return a short list — do NOT pad with dead, duplicate, or barely-related APIs.
2. Hunt the long tail: niche-but-solid APIs, newer 2024-2026 launches, regional favorites, open-data endpoints developers actually use.
3. Only include APIs a third-party developer can actually call today (public, or self-serve signup). No internal-only, partner-only, waitlist-only, or sunset APIs.
4. docs_url must be the API's real, current documentation page.
5. free_tier is true only if a developer can make real calls at $0.
6. slug: lowercase-kebab-case unique identifier.

Set category to exactly "{cat}"."""

# hints for existing categories, reused from round 1
R1 = {
    "weather-environment": "weather forecasts, climate, air quality, environmental data",
    "geo-maps": "geocoding, maps, routing, IP geolocation, places, timezones",
    "finance": "stocks, forex, banking, market data, economic indicators",
    "crypto": "cryptocurrency prices, exchanges, on-chain data, wallets",
    "sports": "scores, fixtures, stats for football, basketball, F1, esports, etc.",
    "news-media": "news headlines, articles, RSS, journalism, fact-checking",
    "ai-ml": "model inference, embeddings, vision, speech, translation, moderation",
    "dev-tools": "CI/CD, git hosting, code search, package registries, monitoring, testing",
    "government-open-data": "census, official statistics, legislation, city/national open data portals",
    "transportation": "transit schedules, flights, vehicle data, shipping/logistics",
    "health-fitness": "medical reference, nutrition databases, exercise, epidemiology",
    "food-drink": "recipes, cocktails, beer/wine/coffee, restaurant data",
    "entertainment": "movies, TV, music metadata, podcasts, books, anime",
    "games-comics": "video game databases, board games, comics, trading cards, chess",
    "science-space": "astronomy, space launches, physics, chemistry, biology datasets",
    "social-communication": "social platforms, messaging, email sending/validation, forums",
    "ecommerce-payments": "payments, invoicing, product data, currency of commerce, tax",
    "security-identity": "breach lookup, vulnerability databases, TLS/DNS analysis, auth services",
    "education-reference": "dictionaries, encyclopedias, universities, courses, quotes, language learning",
    "fun-novelty": "jokes, memes, random facts, placeholder images, novelty generators",
    "utilities": "PDF/QR generation, unit/currency conversion, time/date, URL shortening, OCR, screenshots",
    "data-analytics": "general datasets, web scraping services, search indexes, knowledge graphs",
}


def main():
    # Build per-category exclusion lists from the shipped dataset.
    by_cat = {}
    for f in glob.glob(str(ROOT / "data" / "final" / "*.json")):
        e = json.loads(Path(f).read_text())
        dom = e["base_url"].split("//")[-1].split("/")[0]
        by_cat.setdefault(e["category"], []).append(f"- {e['name']} ({e['id']}, {dom})")

    jobs = []
    for cat, hint in NEW_CATEGORIES.items():
        jobs.append({
            "id": f"seed2-{cat}",
            "prompt": NEW_PROMPT.format(cat=cat, hint=hint),
            "schema": str(ROOT / "schema" / "seed2.schema.json"),
            "out": str(ROOT / "data" / "seeds-r2" / f"{cat}.json"),
        })
    for cat, hint in R1.items():
        existing = "\n".join(sorted(by_cat.get(cat, []))) or "(none)"
        jobs.append({
            "id": f"seed2-{cat}",
            "prompt": DEPTH_PROMPT.format(cat=cat, hint=hint, existing=existing),
            "schema": str(ROOT / "schema" / "seed2.schema.json"),
            "out": str(ROOT / "data" / "seeds-r2" / f"{cat}.json"),
        })
    out = ROOT / "pipeline" / "jobs-seed-r2.jsonl"
    out.write_text("\n".join(json.dumps(j) for j in jobs) + "\n")
    print(f"wrote {len(jobs)} round-2 seed jobs to {out}")


if __name__ == "__main__":
    main()
