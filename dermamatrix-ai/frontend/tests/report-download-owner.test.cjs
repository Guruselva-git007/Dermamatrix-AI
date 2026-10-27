/* PDF response ownership checks with controlled body reads; no real account. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const definitions = source.slice(0, source.indexOf("\n$$('.area-choice button')"));

function deferred() {
  let resolve;
  const promise = new Promise(yes => { resolve = yes; });
  return { promise, resolve };
}

async function flush() {
  for (let index = 0; index < 6; index += 1) await Promise.resolve();
}

function harness(method) {
  const body = deferred();
  const urls = [], revoked = [], links = [], timers = [], toasts = [], requests = [];
  let bodyStarted = false;
  const bridge = { toast(message) { toasts.push(message); } };
  const context = vm.createContext({
    document: {
      createElement(tag) {
        assert.equal(tag, 'a');
        const link = { clicks: 0, click() { link.clicks += 1; } };
        links.push(link);
        return link;
      },
    },
    window: { setTimeout(callback) { timers.push(callback); } },
    URL: {
      createObjectURL(blob) { urls.push(blob); return 'blob:synthetic-owned-pdf'; },
      revokeObjectURL(url) { revoked.push(url); },
    },
    fetch: async url => {
      requests.push(url);
      return { ok: true, blob() { bodyStarted = true; return body.promise; } };
    },
    console, __bridge: bridge,
  });
  vm.runInContext(definitions + `
    toast = __bridge.toast;
    globalThis.api = { state, downloadSavedReport, downloadHistory };
  `, context);
  Object.assign(context.api.state, {
    profile: { patient_id: 'OWNER-A' }, workspaceVersion: 1,
    analyses: [{ assessment_id: 'saved-result', created_at: '2026-10-25T08:00:00Z' }],
  });
  return {
    state: context.api.state, urls, revoked, links, timers, toasts, requests,
    start: () => context.api[method](...(method === 'downloadSavedReport' ? ['saved-result'] : [])),
    bodyStarted: () => bodyStarted,
    finish: () => body.resolve({ type: 'application/pdf', size: 2048 }),
  };
}

const changes = {
  'different signed-in owner': state => { state.profile = { patient_id: 'OWNER-B' }; },
  'same owner in a newer workspace': state => { state.workspaceVersion += 1; },
  'signed-out workspace': state => { state.profile = null; },
};

for (const method of ['downloadSavedReport', 'downloadHistory']) {
  for (const [name, change] of Object.entries(changes)) {
    test(`${method} discards a delayed PDF for a ${name}`, async () => {
      const h = harness(method);
      const download = h.start();
      await flush();
      assert.equal(h.bodyStarted(), true, 'request reached its asynchronous body read');
      assert.equal(h.requests.length, 1);
      change(h.state);
      h.finish();
      await download;
      assert.equal(h.urls.length, 0, 'discard before creating a sensitive object URL');
      assert.equal(h.links.length, 0, 'discard before creating a download link');
      assert.equal(h.toasts.some(message => /downloaded/i.test(message)), false);
    });
  }

  test(`${method} downloads and releases a PDF for the unchanged owner/workspace`, async () => {
    const h = harness(method);
    const download = h.start();
    await flush();
    assert.equal(h.bodyStarted(), true);
    h.finish();
    await download;
    assert.equal(h.urls.length, 1);
    assert.equal(h.links.length, 1);
    assert.equal(h.links[0].clicks, 1);
    assert.equal(h.links[0].href, 'blob:synthetic-owned-pdf');
    assert.match(h.links[0].download, /\.pdf$/);
    assert.equal(h.toasts.some(message => /downloaded/i.test(message)), true);
    for (const timer of h.timers) timer();
    assert.deepEqual(h.revoked, ['blob:synthetic-owned-pdf']);
  });
}

test('a just-saved current result downloads before history refresh, without admitting unrelated IDs', async () => {
  const h = harness('downloadSavedReport');
  Object.assign(h.state, {
    assessmentId: 'saved-result', resultPersistence: 'mysql', analyses: [],
  });
  const download = h.start();
  await flush();
  assert.equal(h.requests.length, 1, 'the confirmed current save does not depend on cached history');
  assert.equal(h.bodyStarted(), true);
  h.finish();
  await download;
  assert.equal(h.links[0].clicks, 1);
  assert.match(h.links[0].download, /^dermamatrix-discussion-brief-\d{4}-\d{2}-\d{2}\.pdf$/);
  for (const timer of h.timers) timer();
  assert.deepEqual(h.revoked, ['blob:synthetic-owned-pdf']);

  h.state.assessmentId = 'different-current-result';
  await h.start();
  assert.equal(h.requests.length, 1, 'an unrelated missing ID cannot start a download');
  assert.equal(h.links.length, 1);
  assert.match(h.toasts.at(-1), /no longer available/);
});
