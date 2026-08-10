/* apidex client script: copy buttons, install tabs, browse search. */
(function () {
  'use strict';

  /* ---------- copy buttons ---------- */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.copy-btn');
    if (!btn) return;
    var src = document.querySelector(btn.getAttribute('data-copy'));
    if (!src) return;
    navigator.clipboard.writeText(src.textContent).then(function () {
      btn.classList.add('copied');
      btn.textContent = 'copied';
      setTimeout(function () { btn.classList.remove('copied'); btn.textContent = 'copy'; }, 1600);
    });
  });

  /* ---------- install tabs ---------- */
  var tabs = document.querySelectorAll('.install-tabs [role="tab"]');
  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      tabs.forEach(function (o) { o.setAttribute('aria-selected', o === t ? 'true' : 'false'); });
      document.getElementById('install-cmd').textContent = t.getAttribute('data-cmd');
    });
  });

  /* ---------- browse ---------- */
  var grid = document.getElementById('grid');
  if (!grid) return;

  var STOP = new Set(['a', 'an', 'the', 'for', 'to', 'of', 'in', 'on', 'with', 'and', 'or', 'api', 'apis', 'get', 'i', 'my', 'me', 'that', 'this', 'is', 'it']);
  function tokens(s) {
    return String(s).toLowerCase().split(/[^a-z0-9]+/).filter(function (t) { return t.length > 1 && !STOP.has(t); });
  }

  var all = [];
  fetch(grid.getAttribute('data-index')).then(function (r) { return r.json(); }).then(function (rows) {
    all = rows.map(function (r) {
      r.words = new Set(
        tokens(r.n).map(function (t) { return [t, 5]; })
          .concat(r.u.join(' ') ? tokens(r.u.join(' ')).map(function (t) { return [t, 4]; }) : [])
          .concat(tokens(r.t).map(function (t) { return [t, 3]; }))
          .concat(tokens(r.c).map(function (t) { return [t, 2]; }))
          .map(function (p) { return p.join(':'); })
      );
      // weight map: token -> max weight
      r.wmap = {};
      r.words.forEach(function (tw) {
        var i = tw.lastIndexOf(':');
        var t = tw.slice(0, i), w = +tw.slice(i + 1);
        if (!r.wmap[t] || r.wmap[t] < w) r.wmap[t] = w;
      });
      return r;
    });
    initFromURL();
    render();
  });

  var q = document.getElementById('q');
  var cat = document.getElementById('cat');
  var chips = document.querySelectorAll('#filters .chip');
  var count = document.getElementById('count');
  var state = { free: false, noauth: false, cors: false };

  function initFromURL() {
    var p = new URLSearchParams(location.search);
    if (p.get('q')) q.value = p.get('q');
    if (p.get('category')) cat.value = p.get('category');
    ['free', 'noauth', 'cors'].forEach(function (f) {
      if (p.get(f) === '1') { state[f] = true; }
    });
    chips.forEach(function (c) { c.setAttribute('aria-pressed', state[c.getAttribute('data-f')] ? 'true' : 'false'); });
  }
  function syncURL() {
    var p = new URLSearchParams();
    if (q.value) p.set('q', q.value);
    if (cat.value) p.set('category', cat.value);
    ['free', 'noauth', 'cors'].forEach(function (f) { if (state[f]) p.set(f, '1'); });
    var qs = p.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
  }

  function score(r, qtoks) {
    if (!qtoks.length) return 1;
    var s = 0, hits = 0;
    qtoks.forEach(function (t) {
      if (r.wmap[t]) { s += r.wmap[t]; hits++; return; }
      if (t.length >= 4) {
        for (var w in r.wmap) {
          if (w.indexOf(t) === 0) { s += r.wmap[w] * 0.6; hits++; return; }
        }
      }
    });
    if (!hits) return 0;
    return s * (hits / qtoks.length);
  }

  function render() {
    var qtoks = tokens(q.value || '');
    var rows = all.filter(function (r) {
      if (state.free && !r.f) return false;
      if (state.noauth && !r.k) return false;
      if (state.cors && !r.o) return false;
      if (cat.value && r.c !== cat.value) return false;
      return true;
    }).map(function (r) { return { r: r, s: score(r, qtoks) }; })
      .filter(function (x) { return x.s > 0; });
    rows.sort(function (a, b) { return b.s - a.s || a.r.n.localeCompare(b.r.n); });

    count.textContent = rows.length + ' of ' + all.length + ' verified APIs';
    grid.innerHTML = rows.map(function (x) {
      var r = x.r;
      var badges = [];
      if (r.k) badges.push('<span class="badge free">no key</span>');
      else if (r.f) badges.push('<span class="badge free">free tier</span>');
      if (r.o) badges.push('<span class="badge">cors</span>');
      var v = [];
      if (r.v[0]) v.push('<span class="vd confirm">' + r.v[0] + '</span>');
      if (r.v[1]) v.push('<span class="vd corrected">' + r.v[1] + '</span>');
      if (r.v[2]) v.push('<span class="vd unverifiable">' + r.v[2] + '</span>');
      return '<a class="api-card" href="./' + r.id + '/">' +
        '<div class="top"><h3>' + esc(r.n) + '</h3><span class="cat">' + esc(r.c.replace(/-/g, ' ')) + '</span></div>' +
        '<p class="tag">' + esc(r.t) + '</p>' +
        '<div class="meta">' + badges.join('') + '<span style="flex:1"></span>' + v.join(' ') + '</div>' +
        '</a>';
    }).join('');
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  var deb;
  q.addEventListener('input', function () { clearTimeout(deb); deb = setTimeout(function () { render(); syncURL(); }, 120); });
  cat.addEventListener('change', function () { render(); syncURL(); });
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      var f = c.getAttribute('data-f');
      state[f] = !state[f];
      c.setAttribute('aria-pressed', state[f] ? 'true' : 'false');
      render(); syncURL();
    });
  });
})();
