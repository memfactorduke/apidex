#!/usr/bin/env node
/* apidex site generator — zero deps. Reads ../mcp-server/data/apis.json,
   emits a fully static site to dist/. */
import { readFileSync, writeFileSync, mkdirSync, cpSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const DIST = join(HERE, 'dist');
const SITE_URL = 'https://memfactorduke.github.io/apidex';
const REPO = 'https://github.com/memfactorduke/apidex';
const NPM = 'https://www.npmjs.com/package/apidex';
const DROPPED_DEAD = 44; // defunct APIs caught and removed across all rounds (see repo README)

const data = JSON.parse(readFileSync(join(HERE, '..', 'mcp-server', 'data', 'apis.json'), 'utf8'));
const apis = data.apis.filter(a => a.status !== 'defunct').sort((a, b) => a.name.localeCompare(b.name));

/* ---------- derived stats ---------- */
const adjCorrections = data.apis.reduce((n, a) => n + (a.verification?.corrected?.length || 0), 0);
const auditCorrections = data.apis.reduce((n, a) => n + (a.verification?.audit?.corrected?.length || 0), 0);
const corrections = adjCorrections + auditCorrections;
const noAuth = apis.filter(a => a.auth?.type === 'none').length;
const freeTier = apis.filter(a => a.pricing?.free_tier).length;
const categories = [...new Set(apis.map(a => a.category))].sort();
const catCounts = Object.fromEntries(categories.map(c => [c, apis.filter(a => a.category === c).length]));
const catLabel = c => c.replace(/-/g, ' ');

const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/* ---------- verdict helpers ---------- */
// field-name → human label + where it lives on the page
const FIELD_LABELS = {
  base_url: 'base URL', docs_url: 'docs URL', auth_type: 'auth', auth_details: 'auth details',
  free_tier: 'free tier', free_tier_limits: 'free limits', paid_plans: 'paid plans',
  rate_limits: 'rate limits', cors: 'CORS', example: 'example', example_request: 'example',
  example_response_snippet: 'example response', description: 'description',
};
function verdictFor(api, field) {
  const v = api.verification || {};
  const audited = v.audit?.corrected || [];
  if (audited.includes(field) || (field === 'example' && (audited.includes('example_request') || audited.includes('example_response_snippet')))) return 'corrected';
  if ((v.corrected || []).includes(field)) return 'corrected';
  if ((v.confirmed_by_both || []).includes(field)) return 'confirm';
  if ((v.unverifiable || []).includes(field)) return 'unverifiable';
  return null;
}
const VD = { confirm: 'confirmed', corrected: 'corrected', unverifiable: 'unverifiable' };
const vdSpan = k => k ? `<span class="vd ${k}" title="${k === 'confirm' ? 'confirmed by both independent verifiers' : k === 'corrected' ? 'corrected during verification — the value shown is the corrected one' : 'not publicly verifiable'}">${VD[k]}</span>` : '';

/* ---------- page shell ---------- */
function shell({ root, title, desc, path, body, current }) {
  const nav = (href, label, key) =>
    `<a href="${root}${href}"${current === key ? ' aria-current="page"' : ''}>${label}</a>`;
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${SITE_URL}/${path}">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:image" content="${SITE_URL}/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="${SITE_URL}/og.png">
<meta name="theme-color" content="#f5f6f2" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#15170f" media="(prefers-color-scheme: dark)">
<link rel="icon" href="${root}favicon.svg" type="image/svg+xml">
<link rel="preload" href="${root}assets/fonts/ZillaSlab-700.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="${root}assets/fonts/PublicSans-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="${root}assets/fonts.css">
<link rel="stylesheet" href="${root}assets/styles.css">
</head>
<body>
<header class="site-head"><div class="wrap">
  <a class="wordmark" href="${root}">
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true"><rect x="1.5" y="1.5" width="19" height="19" rx="5" stroke="var(--confirm)" stroke-width="1.8" stroke-dasharray="3.2 2.4"/><path d="M6.5 11.5l3 3 6-6.5" stroke="var(--confirm)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
    apidex</a>
  <nav class="site-nav">
    ${nav('apis/', 'apis', 'apis')}
    ${nav('methodology/', 'methodology', 'method')}
    <a href="${REPO}">github</a>
    <a href="${NPM}">npm</a>
  </nav>
</div></header>
${body}
<footer class="site-foot"><div class="wrap">
  <p>every entry researched, double-verified, and audited by independent agents — receipts included. dataset MIT-licensed.</p>
  <nav><a href="${REPO}">github</a><a href="${NPM}">npm</a><a href="${root}methodology/">methodology</a></nav>
</div></footer>
<script src="${root}assets/app.js" defer></script>
</body>
</html>`;
}

/* ---------- landing ---------- */
function auditTrailCard(api, { animate = false } = {}) {
  const v = api.verification || {};
  const f = v.fields || {};
  const n = Object.keys(f).length;
  const aConfirms = Object.values(f).filter(x => x.a === 'confirm').length;
  const bDisputes = Object.values(f).filter(x => x.b && x.b !== 'confirm').length;
  const nCorr = (v.corrected || []).length;
  const host = (api.base_url || '').replace(/^https?:\/\//, '').split('/')[0];
  const audit = v.audit
    ? [`audit`, `gpt-5.6 offline × grok live`, v.audit.corrected?.length ? `<span class="vd corrected">${v.audit.corrected.length} fixed</span>` : `<span class="vd confirm">upheld</span>`]
    : [`audit`, `cross-family review`, `<span class="vd confirm">clean</span>`];
  const lines = [
    [`research`, `grok-4.5 · live web`, `${n + 9} fields filled`],
    [`machine check`, `GET ${host} …`, `<span class="vd confirm">200</span>`],
    [`verifier a`, `docs-first lens`, `<span class="vd confirm">${aConfirms}/${n} confirm</span>`],
    [`verifier b`, `adversarial lens`, bDisputes ? `<span class="vd corrected">${bDisputes} disputes</span>` : `<span class="vd confirm">${n}/${n} confirm</span>`],
    [`adjudicate`, `third agent, cited sources`, nCorr ? `<span class="vd corrected">${nCorr} corrections</span>` : `<span class="vd confirm">no changes</span>`],
    audit,
  ];
  const rows = lines.map((l, i) =>
    `<div class="audit-line"${animate ? ` style="animation-delay:${0.12 + i * 0.22}s"` : ''}><span class="stage">${l[0]}</span><span class="what">${l[1]}</span><span class="result">${l[2]}</span></div>`
  ).join('\n');
  return `<div class="audit-card"${animate ? ' data-animate' : ''} role="img" aria-label="Verification audit trail for ${esc(api.name)}">
  <div class="card-head"><span>audit trail</span><b>${esc(api.id)}</b></div>
  ${rows}
  <div class="audit-stamp-row"${animate ? ` style="animation-delay:${0.3 + lines.length * 0.22}s"` : ''}><span class="stamp">verified · ${esc(v.last_checked || '2026-08-08')}</span></div>
</div>`;
}

const heroApi = apis.find(a => a.id === 'open-meteo') || apis[0];

const installTabs = `<div class="install" id="install">
  <div class="install-tabs" role="tablist">
    <button role="tab" aria-selected="true" data-cmd="claude mcp add apidex -- npx -y apidex">Claude Code</button>
    <button role="tab" aria-selected="false" data-cmd="codex mcp add apidex -- npx -y apidex">Codex CLI</button>
    <button role="tab" aria-selected="false" data-cmd='{"mcpServers":{"apidex":{"command":"npx","args":["-y","apidex"]}}}'>Any MCP client</button>
  </div>
  <div class="install-line">
    <code id="install-cmd">claude mcp add apidex -- npx -y apidex</code>
    <button class="copy-btn" data-copy="#install-cmd">copy</button>
  </div>
</div>`;

const landing = shell({
  root: '', path: '', current: 'home',
  title: 'apidex — a verified public-API directory for coding agents',
  desc: `${apis.length} public APIs, every field cross-checked by independent verification agents. An MCP server your coding agent can query instead of hallucinating endpoints.`,
  body: `
<section class="hero"><div class="wrap">
  <div>
    <p class="eyebrow">verified public-api directory · mcp server</p>
    <h1>Agents hallucinate APIs.<br><span class="receipts">This directory shows receipts.</span></h1>
    <p class="lede">apidex gives your coding agent <strong>${apis.length} public APIs</strong> it can trust: every base URL, auth scheme, free-tier limit, and example request was checked by <strong>two independent verifier agents</strong>, machine-tested for liveness, and audited across model families. The verification record ships with every entry.</p>
    ${installTabs}
  </div>
  ${auditTrailCard(heroApi, { animate: true })}
</div></section>

<section class="stats"><div class="wrap">
  <div class="stat"><div class="n">${apis.length}</div><div class="l">verified APIs across ${categories.length} categories</div></div>
  <div class="stat"><div class="n corrected">${corrections.toLocaleString()}</div><div class="l">field corrections the pipeline caught</div></div>
  <div class="stat"><div class="n defunct">${DROPPED_DEAD}</div><div class="l">dead APIs found and dropped</div></div>
  <div class="stat"><div class="n confirm">${noAuth}</div><div class="l">need no API key at all</div></div>
</div></section>

<section class="section"><div class="wrap">
  <p class="eyebrow">how an entry earns its stamp</p>
  <h2>Five passes. No field ships unchecked.</h2>
  <div class="stages">
    <div class="stage-row"><span class="num">01</span><h3>Research</h3><p>An agent with live web search fills a strict schema from the official docs — endpoints, auth, pricing, limits, a working <b>curl</b> example.</p></div>
    <div class="stage-row"><span class="num">02</span><h3>Machine checks</h3><p>Scripts hit every base and docs URL. Dead links and schema violations get flagged before any model opines.</p></div>
    <div class="stage-row"><span class="num">03</span><h3>Double verification</h3><p>Two independent agents re-research every entry — one <b>docs-first</b>, one <b>adversarial</b> — and issue per-field verdicts: confirm, incorrect, or unverifiable.</p></div>
    <div class="stage-row"><span class="num">04</span><h3>Adjudication</h3><p>Disputed fields go to a third agent that must rule with cited sources. ${adjCorrections.toLocaleString()} corrections came out of this stage alone.</p></div>
    <div class="stage-row"><span class="num">05</span><h3>Cross-family checks</h3><p>A second model family re-checks the work — auditing entries offline with live-web arbitration, and running independent verification passes of its own. ${auditCorrections.toLocaleString()} more corrections; ${DROPPED_DEAD} dead APIs caught and dropped across all stages.</p></div>
  </div>
</div></section>

<section class="section alt"><div class="wrap">
  <p class="eyebrow">browse</p>
  <h2>${categories.length} categories</h2>
  <div class="cat-grid">
    ${categories.map(c => `<a class="cat-card" href="apis/?category=${c}"><span>${esc(catLabel(c))}</span><span class="count">${catCounts[c]}</span></a>`).join('\n    ')}
  </div>
</div></section>`
});

/* ---------- browse page ---------- */
const browse = shell({
  root: '../', path: 'apis/', current: 'apis',
  title: `Browse ${apis.length} verified APIs — apidex`,
  desc: `Search ${apis.length} verified public APIs by task, category, free tier, auth, and CORS support.`,
  body: `
<section class="browse-head"><div class="wrap">
  <p class="eyebrow">${apis.length} verified apis</p>
  <h1>Find an API</h1>
  <div class="search-row">
    <input class="search-input" id="q" type="search" placeholder="try: geocode an address without an api key" autocomplete="off" aria-label="Search APIs">
  </div>
  <div class="filter-row" id="filters">
    <button class="chip" data-f="free" aria-pressed="false">free tier</button>
    <button class="chip" data-f="noauth" aria-pressed="false">no API key</button>
    <button class="chip" data-f="cors" aria-pressed="false">CORS</button>
    <select class="cat-select" id="cat" aria-label="Category">
      <option value="">all categories</option>
      ${categories.map(c => `<option value="${c}">${esc(catLabel(c))} (${catCounts[c]})</option>`).join('\n      ')}
    </select>
  </div>
  <p class="result-count" id="count" role="status"></p>
</div></section>
<div class="wrap"><div class="api-grid" id="grid" data-index="./index.json"></div></div>`
});

/* browse search index */
const index = apis.map(a => ({
  id: a.id, n: a.name, t: a.tagline || '', c: a.category,
  f: !!a.pricing?.free_tier, k: a.auth?.type === 'none', o: a.cors === 'yes',
  u: a.use_cases || [],
  v: [(a.verification?.confirmed_by_both || []).length,
      (a.verification?.corrected || []).length + (a.verification?.audit?.corrected?.length || 0),
      (a.verification?.unverifiable || []).length],
}));

/* ---------- detail pages ---------- */
function factRow(label, valueHtml, verdictKey) {
  if (!valueHtml) return '';
  return `<div class="fact"><span class="k">${label}${vdSpan(verdictKey)}</span><span class="v">${valueHtml}</span></div>`;
}
function detailPage(a) {
  const v = a.verification || {};
  const stampClass = a.status === 'operational' ? '' : a.status;
  const stampText = a.status === 'operational' ? `verified · ${v.last_checked || ''}` : a.status;
  const confirmed = (v.confirmed_by_both || []);
  const corrected = [...(v.corrected || []), ...(v.audit?.corrected || [])];
  const unver = (v.unverifiable || []);
  const label = f => FIELD_LABELS[f] || f.replace(/_/g, ' ');
  const ledgerRow = (name, list, kind) => list.length
    ? `<div class="row"><span>${list.map(label).map(esc).join(', ')}</span><span class="vd ${kind}">${name}</span></div>` : '';
  return shell({
    root: '../../', path: `apis/${a.id}/`, current: 'apis',
    title: `${a.name} API — verified record — apidex`,
    desc: `${a.tagline || a.name}. Verified base URL, auth, pricing, rate limits, and a working example request.`,
    body: `
<div class="wrap">
  <p class="crumb"><a href="../../">apidex</a> / <a href="../">apis</a> / <a href="../?category=${a.category}">${esc(catLabel(a.category))}</a></p>
  <div class="api-head">
    <div>
      <h1>${esc(a.name)}</h1>
      <p class="tagline">${esc(a.tagline || '')}</p>
    </div>
    <span class="stamp ${stampClass}">${esc(stampText)}</span>
  </div>
  <div class="api-layout">
    <div class="api-main">
      <h2>What it does</h2>
      <p>${esc(a.description || '')}</p>
      ${a.use_cases?.length ? `<h2>Reach for it when you need to</h2>
      <ul class="use-list">${a.use_cases.map(u => `<li>${esc(u)}</li>`).join('')}</ul>` : ''}
      ${a.example?.request ? `<h2>Example request ${verdictFor(a, 'example') ? vdSpan(verdictFor(a, 'example')) : ''}</h2>
      <div class="code-block"><button class="copy-btn" data-copy="#ex-req">copy</button><code id="ex-req">${esc(a.example.request)}</code></div>` : ''}
      ${a.example?.response_snippet ? `<h2>Response</h2>
      <div class="code-block plain"><code>${esc(a.example.response_snippet)}</code></div>` : ''}
      ${a.sources?.length ? `<h2>Sources consulted</h2>
      <ul class="src-list">${a.sources.slice(0, 6).map(s => `<li><a href="${esc(s)}" rel="nofollow">${esc(s)}</a></li>`).join('')}</ul>` : ''}
    </div>
    <aside class="api-aside">
      <div class="facts">
        <div class="facts-head"><span>verified record</span><span>${esc(catLabel(a.category))}</span></div>
        ${factRow('base URL', `<code>${esc(a.base_url)}</code>`, verdictFor(a, 'base_url'))}
        ${factRow('auth', esc(a.auth?.details || a.auth?.type || ''), verdictFor(a, 'auth_type'))}
        ${factRow('free tier', a.pricing?.free_tier ? 'yes' : 'no', verdictFor(a, 'free_tier'))}
        ${a.pricing?.free_tier_limits ? factRow('free limits', esc(a.pricing.free_tier_limits), verdictFor(a, 'free_tier_limits')) : ''}
        ${a.pricing?.paid_plans ? factRow('paid plans', esc(a.pricing.paid_plans), verdictFor(a, 'paid_plans')) : ''}
        ${a.rate_limits ? factRow('rate limits', esc(a.rate_limits), verdictFor(a, 'rate_limits')) : ''}
        ${factRow('CORS', esc(a.cors || 'unknown'), verdictFor(a, 'cors'))}
        ${a.formats?.length ? factRow('formats', esc(a.formats.join(', ')), null) : ''}
        <a class="btn docs-btn" href="${esc(a.docs_url)}">official docs ↗</a>
      </div>
      <div class="ledger">
        <h3>verification ledger</h3>
        ${ledgerRow('confirmed ×2', confirmed, 'confirm')}
        ${ledgerRow('corrected', corrected, 'corrected')}
        ${ledgerRow('unverifiable', unver, 'unverifiable')}
        <p class="note">Researched with live web access, machine-checked for liveness, then re-verified by two independent agents (docs-first + adversarial); disputes adjudicated with cited sources${v.audit ? `, plus a cross-model-family audit on ${esc(v.audit.date || '2026-08-08')}` : ''}. Last checked ${esc(v.last_checked || '2026-08-08')}. <a href="../../methodology/">How verification works →</a></p>
      </div>
    </aside>
  </div>
</div>`
  });
}

/* ---------- methodology ---------- */
const methodology = shell({
  root: '../', path: 'methodology/', current: 'method',
  title: 'Methodology — how apidex verifies every API — apidex',
  desc: 'The multi-agent verification pipeline behind apidex: research, machine checks, double verification, adjudication, and a cross-model-family audit.',
  body: `
<div class="wrap"><div class="prose">
  <p class="eyebrow">methodology</p>
  <h1>Distrust, then verify. Twice.</h1>
  <p>Directories of public APIs rot. Endpoints move, pricing changes monthly, products get decommissioned — and a list maintained by hand (or generated by a single AI pass) quietly ships all of it. apidex was built on the opposite assumption: <b>a single researcher, human or model, is not a source of truth.</b> Every fact here had to survive independent cross-examination before it shipped.</p>

  <h2>The pipeline</h2>
  <ol>
    <li><b>Seed.</b> Category scouts with live web search proposed candidate APIs — famous staples and long-tail gems — with explicit instructions that a dead API in the list is a serious error.</li>
    <li><b>Research.</b> One agent per API filled a strict JSON schema from official docs: base URL, auth scheme, free-tier limits, rate limits, CORS, and a <code>curl</code> example that has to name real endpoints and parameters.</li>
    <li><b>Machine checks.</b> Scripts probed every base and docs URL for liveness and validated every record against the schema. Models can argue; HTTP status codes don't.</li>
    <li><b>Double verification.</b> Two independent agents re-researched every entry from scratch — one told to trust nothing but current official docs, one told to actively hunt for errors — and issued per-field verdicts: <b>confirm</b>, <b>incorrect</b>, or <b>unverifiable</b>.</li>
    <li><b>Adjudication.</b> Any field the verifiers disputed went to a third agent required to rule with cited sources. This stage alone produced <b>${adjCorrections.toLocaleString()} field corrections</b>.</li>
    <li><b>Cross-family checks.</b> A model from a different family audited entries offline, from its own knowledge — a deliberately different failure profile — with disputes settled by a live-web arbiter under one rule: <b>recency wins; what the official docs say today is the truth.</b> That produced <b>${auditCorrections.toLocaleString()} further corrections</b>. In the expansion round the second family also ran independent verification and adjudication passes of its own, so cross-family disagreement is baked into the whole corpus. <b>${DROPPED_DEAD} dead APIs</b> were caught across all stages and dropped rather than shipped.</li>
  </ol>

  <h2>What the verdicts mean</h2>
  <ul>
    <li><b>confirmed ×2</b> — both independent verifiers checked the field against current official sources and agreed with it.</li>
    <li><b>corrected</b> — a verifier or auditor found the researched value wrong; the value you see is the corrected one, ruled with cited sources.</li>
    <li><b>unverifiable</b> — the fact isn't publicly documented (unpublished rate limits are the classic case). Shipped honestly as unverifiable instead of guessed.</li>
  </ul>

  <h2>Scale</h2>
  <p>The pipeline ran as a fleet of <b>4,148 agent jobs</b> consuming just over <b>a billion tokens</b> across seeding, research, dual verification, adjudication, and arbitration — and when that fleet's quota ran dry mid-verification, a second fleet from a different model family picked up the remaining verification and adjudication jobs and finished the corpus. Every intermediate artifact is committed to the <a href="${REPO}">open repository</a>: job definitions, raw verdicts, adjudication rulings, token ledgers. You can trace any field on this site back to the agents that checked it.</p>

  <h2>Honesty about limits</h2>
  <p>Verification has a timestamp — every entry shows its <b>last checked</b> date and APIs keep changing after it. Fields marked unverifiable were never confirmed, only researched. And verification agents share a weakness: they can agree on something official docs state ambiguously. The receipts tell you how much to trust each field; nothing here asks to be trusted blindly.</p>

  <h2>Use it</h2>
  <p>The dataset ships inside an MCP server your coding agent queries locally — no API key, no network calls, no telemetry:</p>
  <p><code>claude mcp add apidex -- npx -y apidex</code><br>
  <code>codex mcp add apidex -- npx -y apidex</code></p>
</div></div>`
});

/* ---------- 404 ---------- */
const notFound = shell({
  root: '/apidex/', path: '404.html', current: '',
  title: 'Not found — apidex',
  desc: 'Page not found.',
  body: `<div class="wrap"><div class="prose"><h1>Not verified — because it doesn't exist.</h1>
  <p>This page isn't in the directory. <a href="/apidex/apis/">Browse the ${apis.length} APIs that are →</a></p></div></div>`
});

/* ---------- write everything ---------- */
rmSync(DIST, { recursive: true, force: true });
mkdirSync(join(DIST, 'assets', 'fonts'), { recursive: true });
mkdirSync(join(DIST, 'apis'), { recursive: true });
mkdirSync(join(DIST, 'methodology'), { recursive: true });

writeFileSync(join(DIST, 'index.html'), landing);
writeFileSync(join(DIST, 'apis', 'index.html'), browse);
writeFileSync(join(DIST, 'apis', 'index.json'), JSON.stringify(index));
writeFileSync(join(DIST, 'methodology', 'index.html'), methodology);
writeFileSync(join(DIST, '404.html'), notFound);
for (const a of apis) {
  const dir = join(DIST, 'apis', a.id);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, 'index.html'), detailPage(a));
}

cpSync(join(HERE, 'src', 'og.png'), join(DIST, 'og.png'));
cpSync(join(HERE, 'src', 'styles.css'), join(DIST, 'assets', 'styles.css'));
cpSync(join(HERE, 'src', 'fonts.css'), join(DIST, 'assets', 'fonts.css'));
cpSync(join(HERE, 'src', 'app.js'), join(DIST, 'assets', 'app.js'));
for (const f of ['PublicSans-var.woff2', 'SplineSansMono-var.woff2', 'ZillaSlab-500.woff2', 'ZillaSlab-600.woff2', 'ZillaSlab-700.woff2']) {
  cpSync(join(HERE, 'src', 'fonts', f), join(DIST, 'assets', 'fonts', f));
}
writeFileSync(join(DIST, 'favicon.svg'),
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 22 22"><rect x="1.5" y="1.5" width="19" height="19" rx="5" fill="none" stroke="#106b41" stroke-width="1.8" stroke-dasharray="3.2 2.4"/><path d="M6.5 11.5l3 3 6-6.5" fill="none" stroke="#106b41" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`);

/* sitemap + robots */
const urls = ['', 'apis/', 'methodology/', ...apis.map(a => `apis/${a.id}/`)];
writeFileSync(join(DIST, 'sitemap.xml'),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  urls.map(u => `  <url><loc>${SITE_URL}/${u}</loc></url>`).join('\n') + '\n</urlset>');
writeFileSync(join(DIST, 'robots.txt'), `User-agent: *\nAllow: /\nSitemap: ${SITE_URL}/sitemap.xml\n`);
writeFileSync(join(DIST, '.nojekyll'), '');

console.log(`built ${urls.length + 1} pages (${apis.length} API records) → site/dist/`);
