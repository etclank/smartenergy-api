const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

(async () => {
  const listeners = [];
  const fetched = [];
  const nodes = Object.fromEntries(['health', 'cache', 'apiBase', 'openDocs', 'openRedoc', 'meter-detail', 'energy-charts', 'startDate', 'endDate'].map(id => [id, { innerHTML: '', appendChild() {}, value: '' }]));
  const window = { location: { search: '?mock=1' }, SITE_API_BASE: '/api', addEventListener: (_, fn) => listeners.push(fn) };
  const ctx = vm.createContext({
    window, URLSearchParams, console,
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    document: { documentElement: { dataset: {} }, getElementById: id => nodes[id] || null, createElement: () => ({}) },
    fetch: async url => {
      fetched.push(url);
      return { ok: true, headers: { get: () => 'application/json' }, json: async () => ({ redis: 'down' }) };
    },
  });
  vm.runInContext(fs.readFileSync('site/assets/js/api.js', 'utf8'), ctx);
  ctx.API = window.API;
  assert.equal(ctx.API.escapeHTML('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
  await ctx.API.metersList();
  assert(fetched.includes('/site/mock/meters.json'));
  listeners[0]();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(nodes.openDocs.href, '/docs');
  assert.equal(nodes.openRedoc.href, '/redoc');

  const oldTimestamp = '2020-01-01T00:00:00';
  window.location.search = '?id=1';
  ctx.renderBreadcrumb = () => {};
  ctx.renderEnergyChart = () => {};
  ctx.API.meterById = async () => ({ name: '<script>bad</script>', location: 'test', serial_number: 'one', type: 'electric' });
  for (const method of ['energyImported', 'energyExported', 'energyReactive', 'maxPower']) {
    ctx.API[method] = async () => [{ timestamp: oldTimestamp, measure_value: 1 }];
  }
  vm.runInContext(fs.readFileSync('site/assets/js/pages/meter.js', 'utf8'), ctx);
  await listeners.at(-1)();
  assert.equal(window.METER_DATA.imp[0].timestamp, oldTimestamp);
  assert(nodes['meter-detail'].innerHTML.includes('&lt;script&gt;bad&lt;/script&gt;'));
  assert(!nodes['meter-detail'].innerHTML.includes('<script>'));
  console.log('Dashboard escaping, mock URL, documentation links and unchanged timestamps: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
