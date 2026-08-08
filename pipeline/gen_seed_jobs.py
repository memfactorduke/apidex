#!/usr/bin/env python3
"""Generate Phase 0 seed-lister jobs (one Grok agent per category)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CATEGORIES = {
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

PROMPT = """You are compiling the seed list for a rigorously verified public-API directory (2026 edition).

Category: {cat} — {hint}

Use web search extensively. List 18 to 28 public HTTP APIs in this category that are CURRENTLY operational in 2026. Rules:
1. VERIFY each API still exists and is operational — search for its docs/status. Public APIs die constantly; a dead API in your list is a serious error. If unsure about one, leave it out.
2. Mix the famous staples every developer knows with lesser-known high-quality gems.
3. Only include APIs a third-party developer can actually call today (public, or self-serve signup). No internal-only, partner-only, waitlist-only, or sunset APIs.
4. docs_url must be the API's real, current documentation page.
5. free_tier is true only if a developer can make real calls at $0.
6. slug: lowercase-kebab-case unique identifier, e.g. "openweathermap".

Set category to exactly "{cat}"."""


def main():
    jobs = []
    for cat, hint in CATEGORIES.items():
        jobs.append({
            "id": f"seed-{cat}",
            "prompt": PROMPT.format(cat=cat, hint=hint),
            "schema": str(ROOT / "schema" / "seed.schema.json"),
            "out": str(ROOT / "data" / "seeds" / f"{cat}.json"),
        })
    out = ROOT / "pipeline" / "jobs-seed.jsonl"
    out.write_text("\n".join(json.dumps(j) for j in jobs) + "\n")
    print(f"wrote {len(jobs)} seed jobs to {out}")


if __name__ == "__main__":
    main()
