/* Delayed account work must never cross a workspace boundary. Synthetic only. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const definitions = source.slice(0, source.indexOf("\n$$('.area-choice button')"));
const deferred = () => { let resolve; const promise = new Promise(yes => { resolve = yes; }); return { promise, resolve }; };

function harness() {
  const elements = new Map(), effects = [], preferences = [], requests = [];
  const element = id => {
    if (!elements.has(id)) elements.set(id, { textContent: '', disabled: false, value: '', focus() {} });
    return elements.get(id);
  };
  const bridge = {
    effects, preferences, element,
    request: async () => ({}),
  };
  const context = vm.createContext({
    document: { querySelector: element }, console, __bridge: bridge,
    window: {}, FormData: class { constructor(form) { this.data = form.data; } entries() { return Object.entries(this.data); } get(key) { return this.data[key]; } },
  });
  vm.runInContext(definitions + `
    requestJSON = (...args) => __bridge.request(...args);
    toast = message => __bridge.effects.push(['toast', message]);
    updateDashboardIdentity = () => __bridge.effects.push(['identity']);
    persistBrowserProfile = () => __bridge.effects.push(['persist']);
    closeProfile = () => __bridge.effects.push(['close']);
    loadProgress = async () => __bridge.effects.push(['progress']);
    handleChangedProcessingNotice = () => __bridge.effects.push(['notice']);
    processingNoticeVersion = () => 'synthetic-notice';
    applyPreferences = preferences => __bridge.preferences.push(preferences);
    applyAccount = account => { state.profile = {...account}; state.workspaceVersion += 1; };
    hideAuthGate = () => {};
    showPage = () => {};
    globalThis.api = {state, hydrateProfile, saveProfile, persistPreferences, enterAccount, restoreAuthentication};
  `, context);
  const state = context.api.state;
  Object.assign(state, { profile: { patient_id: 'OWNER-A', full_name: 'Account A' }, workspaceVersion: 1 });
  bridge.request = async (...args) => { requests.push(args); return {}; };
  return { ...context.api, context, bridge, effects, preferences, requests, element };
}

for (const change of ['another owner', 'same owner after sign-out/sign-in', 'guest']) {
  test('profile hydration ignores a response for ' + change, async () => {
    const h = harness(), response = deferred(); h.bridge.request = () => response.promise;
    const pending = h.hydrateProfile();
    h.state.workspaceVersion += 1;
    h.state.profile = change === 'guest' ? null : { patient_id: change === 'another owner' ? 'OWNER-B' : 'OWNER-A', full_name: 'Current account' };
    response.resolve({ patient_id: 'OWNER-A', full_name: 'Old account', past_history: 'Synthetic private note' });
    await pending;
    assert.equal(h.state.profile?.full_name, change === 'guest' ? undefined : 'Current account');
    assert.equal(h.state.profile?.past_history, undefined);
    assert.deepEqual(h.effects, []);
  });
}

test('profile save cannot submit an old draft after asynchronous request preparation', async () => {
  const h = harness(), preparation = deferred(); let sent = 0;
  h.bridge.request = async (_path, options) => {
    await preparation.promise;
    if (options.ownerGuard && !options.ownerGuard()) throw Error('Account changed');
    sent += 1; return { profile: { patient_id: 'OWNER-A', past_history: 'Old draft' } };
  };
  const pending = h.saveProfile({ preventDefault() {}, currentTarget: { data: { full_name: 'Account A', past_history: 'Old draft', health_data_consent: 'on' }, querySelector: () => h.element('submit') } });
  h.state.profile = { patient_id: 'OWNER-B' }; h.state.workspaceVersion += 1;
  preparation.resolve(); await pending;
  assert.equal(sent, 0); assert.equal(h.state.profile.patient_id, 'OWNER-B');
  assert.deepEqual(h.effects, []);
});

test('a committed profile save response cannot paint or close the next account workspace', async () => {
  const h = harness(), response = deferred(); h.bridge.request = () => response.promise;
  const pending = h.saveProfile({ preventDefault() {}, currentTarget: { data: { full_name: 'Account A', health_data_consent: 'on' }, querySelector: () => h.element('submit') } });
  h.state.profile = { patient_id: 'OWNER-B' }; h.state.workspaceVersion += 1;
  response.resolve({ profile: { patient_id: 'OWNER-A', full_name: 'Old response' } }); await pending;
  assert.equal(h.state.profile.patient_id, 'OWNER-B'); assert.deepEqual(h.effects, []);
});

test('profile hydration and save still update the same current account', async () => {
  const h = harness();
  h.bridge.request = async path => path === '/api/profile' ? { patient_id: 'OWNER-A', full_name: 'Current profile' } : {};
  await h.hydrateProfile(); assert.equal(h.state.profile.full_name, 'Current profile');
  h.bridge.request = async () => ({ profile: { patient_id: 'OWNER-A', full_name: 'Saved profile' } });
  await h.saveProfile({ preventDefault() {}, currentTarget: { data: { full_name: 'Saved profile', health_data_consent: 'on' }, querySelector: () => h.element('submit') } });
  assert.equal(h.state.profile.full_name, 'Saved profile'); assert.ok(h.effects.some(([kind]) => kind === 'progress'));
});

test('old account-entry continuation cannot refresh or announce success in a new workspace', async () => {
  const h = harness(), response = deferred(); h.bridge.request = () => response.promise;
  const pending = h.enterAccount({ user: { patient_id: 'OWNER-A' } }, 'Old account signed in');
  h.state.profile = { patient_id: 'OWNER-B' }; h.state.workspaceVersion += 1;
  response.resolve({ patient_id: 'OWNER-A' }); await pending;
  assert.equal(h.state.profile.patient_id, 'OWNER-B'); assert.deepEqual(h.effects, []);
});

test('startup authentication cannot replace a newer explicitly selected account', async () => {
  const h = harness(), response = deferred(); h.bridge.request = () => response.promise;
  const pending = h.restoreAuthentication(); h.state.profile = { patient_id: 'OWNER-B' }; h.state.workspaceVersion += 1;
  response.resolve({ authenticated: true, user: { patient_id: 'OWNER-A' } });
  assert.equal(await pending, true); assert.equal(h.state.profile.patient_id, 'OWNER-B');
});

test('preference submission and failure feedback stop at an account switch', async () => {
  const h = harness(), preparation = deferred(); let sent = 0;
  h.bridge.request = async (_path, options) => { await preparation.promise; if (options.ownerGuard && !options.ownerGuard()) throw Error('Account changed'); sent += 1; throw Error('Offline'); };
  const pending = h.persistPreferences({ theme: 'dark' }); h.state.profile = { patient_id: 'OWNER-B' }; h.state.workspaceVersion += 1;
  preparation.resolve(); await pending;
  assert.equal(sent, 0); assert.deepEqual(h.effects, []); assert.equal(h.preferences.length, 1);
});
