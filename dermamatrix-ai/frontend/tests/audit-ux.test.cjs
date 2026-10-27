/* Focused source-executing checks. These are DOM logic tests, not browser or
   screen-reader verification. Run: node --test frontend/tests/audit-ux.test.cjs */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const definitions = source.slice(0, source.indexOf("\n$$('.area-choice button')"));

function harness(width = 375) {
  const elements = new Map();
  let document;
  function element() {
    const attrs = new Map(); const classes = new Set();
    return {
      hidden: false, disabled: false, checked: false, inert: false, dataset: {}, textContent: '', style: {},
      offsetLeft: 0, offsetWidth: 100, clientLeft: 0, clientWidth: 100, scrollWidth: 100, scrollLeft: 0,
      classList: { contains: name => classes.has(name), add: name => classes.add(name), remove: name => classes.delete(name), toggle(name, on) { on ? classes.add(name) : classes.delete(name); } },
      setAttribute: (name, value) => attrs.set(name, value), removeAttribute: name => attrs.delete(name), getAttribute: name => attrs.get(name),
      querySelector: () => null, querySelectorAll: () => [], closest: () => null,
      getClientRects: () => [1], contains: () => false,
      focus() { document.activeElement = this; },
    };
  }
  const get = selector => {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  };
  const steps = Array.from({ length: 4 }, (_, index) => {
    const item = element(); item.offsetLeft = index * 100;
    const marker = element(); item.querySelector = () => marker;
    return item;
  });
  const strip = get('.assessment-steps');
  strip.scrollWidth = 400; strip.clientWidth = 180;
  strip.getBoundingClientRect = () => ({ left: strip.offsetLeft, right: strip.offsetLeft + strip.clientWidth });
  steps.forEach(item => { item.getBoundingClientRect = () => ({ left: strip.offsetLeft + strip.clientLeft + item.offsetLeft - strip.scrollLeft, right: strip.offsetLeft + strip.clientLeft + item.offsetLeft - strip.scrollLeft + item.offsetWidth }); });
  strip.querySelector = () => steps.find(item => item.getAttribute('aria-current') === 'step');
  const body = element();
  document = { body, activeElement: body, querySelector: get, querySelectorAll: selector => selector === '.assessment-steps li' ? steps : [] };
  const context = vm.createContext({ document, window: { innerWidth: width }, URL: { revokeObjectURL() {} }, AbortController, console });
  vm.runInContext(definitions + '\nglobalThis.api = { state, updateAssessmentProgress, resetImage, syncInteractionInertness, containKeyboardFocus, setNavigationOpen, processingNoticeVersion, loadProcessingNotices, handleChangedProcessingNotice, downloadAccountData, updateAccountExportControls };', context);
  return { context, api: context.api, get, steps, strip, body, document, element };
}

function current(h) { return h.steps.findIndex(item => item.getAttribute('aria-current') === 'step') + 1; }

test('opening optional context cannot complete an absent image; real result and retry states remain distinct', () => {
  const h = harness(); const { state } = h.api;
  h.api.updateAssessmentProgress(); assert.equal(current(h), 1);
  state.areaSelected = true; h.api.updateAssessmentProgress(); assert.equal(current(h), 2);
  h.get('#screenDetails').open = true; h.api.updateAssessmentProgress();
  assert.equal(current(h), 2); assert.equal(h.steps[1].classList.contains('complete'), false);
  state.file = { name: 'synthetic.png' }; h.api.updateAssessmentProgress(); assert.equal(current(h), 3);
  state.assessmentInFlight = true; h.api.updateAssessmentProgress(); assert.equal(current(h), 3);
  state.reviewResultReady = true; h.api.updateAssessmentProgress(); assert.equal(current(h), 4);
  state.reviewResultReady = false; state.assessmentInFlight = false; h.api.updateAssessmentProgress(); assert.equal(current(h), 3);
  h.api.resetImage(); assert.equal(current(h), 2);
});

test('questionnaire progress reflects answers/review, never a phantom image', () => {
  const h = harness(); Object.assign(h.api.state, { area: 'Sweat', areaSelected: true });
  h.api.updateAssessmentProgress(); assert.equal(current(h), 2);
  h.api.state.questionnaireReviewed = true; h.api.updateAssessmentProgress(); assert.equal(current(h), 3);
  h.api.state.assessmentInFlight = true; h.api.updateAssessmentProgress(); assert.equal(current(h), 3);
  h.api.state.reviewResultReady = true; h.api.updateAssessmentProgress(); assert.equal(current(h), 4);
});

test('the active mobile stage scrolls into the strip without scrolling the page', () => {
  const h = harness(); Object.assign(h.api.state, { areaSelected: true, file: {}, reviewResultReady: true });
  h.api.updateAssessmentProgress(); assert.equal(h.strip.scrollLeft, 220);
  h.api.state.reviewResultReady = false; h.api.state.file = null; h.api.updateAssessmentProgress();
  assert.equal(h.strip.scrollLeft, 100);
});

test('mobile strip visibility compares matching coordinate spaces when its offset parent differs from its items', () => {
  const h = harness(320); Object.assign(h.api.state, { areaSelected: true });
  Object.assign(h.strip, { offsetLeft: 35, clientWidth: 250, scrollWidth: 561, scrollLeft: 20 });
  Object.assign(h.steps[1], { offsetLeft: 129, offsetWidth: 176 });
  h.api.updateAssessmentProgress();
  assert.equal(h.strip.scrollLeft, 55);
  const bounds = h.strip.getBoundingClientRect(); const active = h.steps[1].getBoundingClientRect();
  assert.ok(active.left >= bounds.left && active.right <= bounds.right);
  // Borders use the client viewport, not the outside edge of the strip.
  Object.assign(h.strip, { clientLeft: 2, scrollLeft: 20 });
  h.api.updateAssessmentProgress(); assert.equal(h.strip.scrollLeft, 55);
  h.api.state.areaSelected = false; h.api.updateAssessmentProgress();
  assert.equal(h.strip.scrollLeft, 0);
});

test('auth and result gates isolate the shell; closed mobile drawer is inert; desktop navigation stays available', () => {
  const h = harness(); h.api.syncInteractionInertness();
  assert.equal(h.get('.sidebar').inert, true); assert.equal(h.get('.sidebar').getAttribute('aria-hidden'), 'true');
  assert.equal(h.get('.app-shell').inert, false);
  h.get('#authGate').classList.add('show'); h.api.syncInteractionInertness();
  assert.equal(h.get('.app-shell').inert, true); assert.equal(h.get('#authGate').inert, false);
  h.get('#authGate').classList.remove('show'); h.get('#resultModal').classList.add('show'); h.api.syncInteractionInertness();
  assert.equal(h.get('.app-shell').inert, true);
  h.get('#resultModal').classList.remove('show'); h.body.classList.add('nav-open'); h.api.syncInteractionInertness();
  assert.equal(h.get('.sidebar').inert, false); assert.equal(h.get('.app-shell > main').inert, true);
  h.context.window.innerWidth = 1440; h.api.setNavigationOpen(false);
  assert.equal(h.get('.sidebar').inert, false); assert.equal(h.get('.app-shell > main').inert, false);
});

test('Tab and Shift+Tab loop within the gate, including when focus starts outside it', () => {
  const h = harness(); const first = h.element(); const last = h.element(); const root = h.element();
  root.querySelectorAll = () => [first, last]; root.contains = element => [first, last].includes(element);
  function press(active, shiftKey) {
    h.document.activeElement = active; let prevented = false;
    h.api.containKeyboardFocus({ key: 'Tab', shiftKey, preventDefault() { prevented = true; } }, root);
    return prevented;
  }
  assert.equal(press(last, false), true); assert.equal(h.document.activeElement, first);
  assert.equal(press(first, true), true); assert.equal(h.document.activeElement, last);
  assert.equal(press(h.body, false), true); assert.equal(h.document.activeElement, first);
});

test('notice version cannot be sent until server-owned text has loaded; unavailable notices stay unaccepted', async () => {
  const h = harness();
  assert.throws(() => h.api.processingNoticeVersion('account'), /unavailable/);
  vm.runInContext('requestJSON = async () => { throw Error("offline"); };', h.context);
  assert.equal(await h.api.loadProcessingNotices(), false);
  assert.throws(() => h.api.processingNoticeVersion('account'), /unavailable/);
  assert.match(h.get('#accountHandlingCopy').textContent, /could not be loaded/);
  const notices = Object.fromEntries(['account', 'health_history', 'image_assessment', 'questionnaire_assessment'].map(purpose => [purpose, { version: `server-${purpose}`, summary: 'Purpose shown', retained: 'Storage shown', guest_behavior: 'Guest behavior shown' }]));
  h.context.noticeFixture = { notices };
  vm.runInContext('requestJSON = async () => noticeFixture;', h.context);
  assert.equal(await h.api.loadProcessingNotices(), true);
  assert.equal(h.api.processingNoticeVersion('account'), 'server-account');
  assert.match(h.get('#accountHandlingCopy').textContent, /Purpose shown/);
  assert.match(h.get('#assessmentHandlingCopy').textContent, /Storage shown/);
  assert.equal(h.get('#imageConsent').checked, false);
});

function accountDownloadHarness() {
  const h = harness();
  h.messages = []; h.authTabs = []; h.downloads = []; h.revoked = [];
  h.context.testMessages = h.messages; h.context.testAuthTabs = h.authTabs;
  vm.runInContext('toast = message => testMessages.push(message); showAuthGate = tab => testAuthTabs.push(tab);', h.context);
  h.context.window.setTimeout = (callback, delay) => { if (delay === 0) callback(); return 1; };
  h.context.window.clearTimeout = () => {};
  h.context.URL.createObjectURL = () => 'blob:synthetic-account-data';
  h.context.URL.revokeObjectURL = url => h.revoked.push(url);
  h.document.createElement = tag => {
    assert.equal(tag, 'a');
    const anchor = { click() { h.downloads.push({ href: this.href, filename: this.download }); } };
    return anchor;
  };
  h.api.state.profile = { patient_id: 'synthetic-owner' };
  return h;
}

function jsonDownloadResponse() {
  return { ok: true, headers: { get: () => 'application/json; charset=utf-8' }, blob: async () => ({ type: 'application/json' }) };
}

test('account JSON download uses only the signed session, blocks repeated clicks and releases loading state', async () => {
  const h = accountDownloadHarness(); let resolveRequest; const calls = [];
  h.context.fetch = (url, options) => { calls.push({ url, options }); return new Promise(resolve => { resolveRequest = resolve; }); };
  const pending = h.api.downloadAccountData();
  assert.equal(h.get('#downloadAccountDataButton').disabled, true);
  assert.equal(h.get('#downloadAccountDataButton').getAttribute('aria-busy'), 'true');
  await h.api.downloadAccountData(); assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/api/account-data/download');
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[0].options.body, undefined);
  resolveRequest(jsonDownloadResponse()); await pending;
  assert.equal(h.downloads.length, 1);
  assert.match(h.downloads[0].filename, /^dermamatrix-local-account-data-\d{4}-\d{2}-\d{2}\.json$/);
  assert.deepEqual(h.revoked, ['blob:synthetic-account-data']);
  assert.equal(h.get('#downloadAccountDataButton').disabled, false);
  assert.equal(h.get('#downloadAccountDataButton').getAttribute('aria-busy'), undefined);
  assert.equal(h.get('#downloadAccountDataButton').textContent, 'Download account data (JSON)');
  assert.match(h.messages.at(-1), /download started/);
});

test('guest account-data action requests sign-in without making a download request', async () => {
  const h = accountDownloadHarness(); h.api.state.profile = null;
  h.context.fetch = () => { throw Error('Guests must not make an export request'); };
  h.api.updateAccountExportControls(); await h.api.downloadAccountData();
  assert.equal(h.get('#accountExportRow').hidden, true);
  assert.equal(h.get('#downloadAccountDataButton').disabled, true);
  assert.deepEqual(h.authTabs, ['login']); assert.equal(h.downloads.length, 0);
  assert.match(h.messages.at(-1), /Sign in/);
});

test('expired session and server failure never produce a misleading downloaded file', async () => {
  for (const [status, message] of [[401, 'Sign in to download your local account data.'], [503, 'Local database unavailable.']]) {
    const h = accountDownloadHarness();
    h.context.fetch = async () => ({ ok: false, status, json: async () => ({ error: message }) });
    await h.api.downloadAccountData();
    assert.equal(h.downloads.length, 0); assert.equal(h.messages.at(-1), message);
    assert.equal(h.get('#downloadAccountDataButton').disabled, false);
    assert.equal(h.get('#downloadAccountDataButton').getAttribute('aria-busy'), undefined);
    assert.deepEqual(h.authTabs, status === 401 ? ['login'] : []);
  }
});

test('an account change or non-JSON response cannot download the wrong records or an HTML error page', async () => {
  const switched = accountDownloadHarness();
  switched.context.fetch = async () => {
    switched.api.state.profile = { patient_id: 'another-synthetic-owner' };
    return jsonDownloadResponse();
  };
  await switched.api.downloadAccountData();
  assert.equal(switched.downloads.length, 0); assert.match(switched.messages.at(-1), /account changed/);
  const html = accountDownloadHarness();
  html.context.fetch = async () => ({ ok: true, headers: { get: () => 'text/html' }, blob: async () => { throw Error('HTML must not be downloaded'); } });
  await html.api.downloadAccountData();
  assert.equal(html.downloads.length, 0); assert.match(html.messages.at(-1), /did not return/);
});

test('aborted download restores its control and gives a retryable timeout message', async () => {
  const h = accountDownloadHarness();
  h.context.fetch = async () => { throw Object.assign(Error('request aborted'), { name: 'AbortError' }); };
  await h.api.downloadAccountData();
  assert.equal(h.get('#downloadAccountDataButton').disabled, false);
  assert.equal(h.get('#downloadAccountDataButton').getAttribute('aria-busy'), undefined);
  assert.equal(h.downloads.length, 0); assert.match(h.messages.at(-1), /took too long/);
});
