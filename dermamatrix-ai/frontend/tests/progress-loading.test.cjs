/* Controlled source-executing regressions; no browser, server or real account. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const definitions = source.slice(0, source.indexOf("\n$$('.area-choice button')"));

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

async function flush() {
  // Permit nested Promise.all and a queued refresh to settle without timers.
  for (let index = 0; index < 12; index += 1) await Promise.resolve();
}

function harness() {
  const requests = [], toasts = [], pages = [];
  const elements = new Map();
  const get = selector => {
    if (!elements.has(selector)) elements.set(selector, { textContent: 'Before refresh' });
    return elements.get(selector);
  };
  const bridge = {
    request(url) {
      const request = { url, ...deferred() };
      requests.push(request);
      return request.promise;
    },
    render() {},
    toast(message) { toasts.push(message); },
    close() { bridge.closed += 1; },
    page(name) { pages.push(name); },
    closed: 0,
    refreshResult: false,
  };
  const context = vm.createContext({
    document: { querySelector: get, querySelectorAll: () => [] },
    window: {}, console, __bridge: bridge,
  });
  vm.runInContext(definitions + `
    requestJSON = __bridge.request;
    renderProgress = __bridge.render;
    toast = __bridge.toast;
    closeResult = __bridge.close;
    showPage = __bridge.page;
    globalThis.api = { state, loadProgress, saveProgress };
  `, context);
  const state = context.api.state;
  Object.assign(state, { profile: { patient_id: 'OWNER-A' }, workspaceVersion: 1 });
  function finishBatch(index, label) {
    const batch = requests.slice(index * 3, index * 3 + 3);
    assert.equal(batch.length, 3, `batch ${index} has all existing endpoints`);
    for (const request of batch) {
      if (request.url === '/api/routines') request.resolve({ routines: [{ routine_id: label }] });
      else if (request.url === '/api/progress-checkins') request.resolve({ checkins: [{ checkin_id: label }] });
      else if (request.url === '/api/analysis-history') request.resolve({ analyses: [{ assessment_id: label }] });
      else assert.fail(`unexpected endpoint ${request.url}`);
    }
  }
  return { api: context.api, state, context, requests, toasts, pages, bridge, get, finishBatch };
}

test('ordinary concurrent history loads share one batch and cache successful data', async () => {
  const h = harness();
  const first = h.api.loadProgress(), second = h.api.loadProgress();
  await flush();
  assert.equal(h.requests.length, 3);
  h.finishBatch(0, 'original');
  assert.deepEqual(await Promise.all([first, second]), [true, true]);
  assert.equal(h.state.analyses[0].assessment_id, 'original');
  assert.equal(h.state.progressLoadedFor, 'OWNER-A');
  assert.equal(await h.api.loadProgress(), true);
  assert.equal(h.requests.length, 3, 'cached navigation does not fetch again');
});

test('forced refreshes during a pending load coalesce into one fresh batch', async () => {
  const h = harness();
  const first = h.api.loadProgress();
  await flush();
  const forcedA = h.api.loadProgress({ force: true });
  const forcedB = h.api.loadProgress({ force: true });
  let forcedFinished = false;
  forcedA.then(() => { forcedFinished = true; });
  h.finishBatch(0, 'before-new-assessment');
  await flush();
  assert.equal(h.requests.length, 6, 'one extra batch serves all forced waiters');
  assert.equal(forcedFinished, false, 'forced result waits for the fresh snapshot');
  assert.equal(h.state.analyses.length, 0, 'superseded data is not presented as refreshed');
  h.finishBatch(1, 'new-assessment');
  assert.deepEqual(await Promise.all([first, forcedA, forcedB]), [true, true, true]);
  assert.equal(h.state.analyses[0].assessment_id, 'new-assessment');
  assert.equal(h.requests.length, 6);
});

for (const nextOwner of ['OWNER-A', 'OWNER-B']) {
  test(`stale workspace cannot apply or clear the active flight for ${nextOwner}`, async () => {
    const h = harness();
    const old = h.api.loadProgress();
    await flush();
    // Match the reset performed by clearWorkspaceEvidence, including relogin
    // to the same owner: patient ID alone does not identify the workspace.
    Object.assign(h.state, {
      workspaceVersion: 2, profile: { patient_id: nextOwner },
      progressLoadPromise: null, progressLoadContext: null, progressLoadedFor: null,
    });
    const current = h.api.loadProgress();
    await flush();
    assert.equal(h.requests.length, 6);
    const currentFlight = h.state.progressLoadPromise;
    h.finishBatch(0, 'stale');
    assert.equal(await old, false);
    assert.equal(h.state.analyses.length, 0, 'stale response cannot restore cleared history');
    assert.equal(h.state.progressLoadPromise, currentFlight, 'old cleanup preserves current flight');
    const joined = h.api.loadProgress();
    await flush();
    assert.equal(h.requests.length, 6, 'joining current flight does not create a third batch');
    h.finishBatch(1, 'current');
    assert.deepEqual(await Promise.all([current, joined]), [true, true]);
    assert.equal(h.state.analyses[0].assessment_id, 'current');
    assert.equal(h.state.progressLoadedFor, nextOwner);
  });
}

test('failed history loads resolve false, retain old data and remain retryable', async () => {
  const h = harness();
  h.state.analyses = [{ assessment_id: 'retained' }];
  const first = h.api.loadProgress();
  await flush();
  h.requests[0].reject(Error('Synthetic history outage'));
  h.requests[1].resolve({ checkins: [] });
  h.requests[2].resolve({ analyses: [{ assessment_id: 'partial' }] });
  assert.equal(await first, false);
  assert.equal(h.state.progressLoadedFor, null);
  assert.equal(h.state.analyses[0].assessment_id, 'retained');
  assert.equal(h.state.progressLoadPromise, null);
  const retry = h.api.loadProgress();
  await flush();
  h.finishBatch(1, 'recovered');
  assert.equal(await retry, true);
  assert.equal(h.state.analyses[0].assessment_id, 'recovered');
});

test('saveProgress never claims refresh success or navigates when loading fails', async () => {
  const h = harness();
  Object.assign(h.state, { assessmentId: 'saved-assessment', resultPersistence: 'mysql' });
  vm.runInContext('loadProgress = async () => __bridge.refreshResult;', h.context);
  await h.api.saveProgress();
  assert.equal(h.bridge.closed, 0);
  assert.deepEqual(h.pages, []);
  assert.equal(h.get('#clinicalStatus').textContent, 'Before refresh');
  assert.equal(h.toasts.some(message => /Saved assessment metadata is available/.test(message)), false);
  h.bridge.refreshResult = true;
  await h.api.saveProgress();
  assert.equal(h.bridge.closed, 1);
  assert.deepEqual(h.pages, ['progress']);
  assert.match(h.get('#clinicalStatus').textContent, /Saved/);
});
