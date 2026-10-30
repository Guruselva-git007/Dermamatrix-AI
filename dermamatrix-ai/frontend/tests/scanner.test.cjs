const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../scanner.js'), 'utf8');
function harness() {
  const classes = new Set(), listeners = {};
  const stage = { innerHTML: '', dataset: {}, classList: { add: x => classes.add(x), remove: x => classes.delete(x), toggle: (x, on) => on ? classes.add(x) : classes.delete(x) } };
  const document = { hidden: false, getElementById: () => stage, addEventListener: (type, fn) => { listeners[type] = fn; } }, window = {};
  // Deliberately no timers, image APIs, storage or network. Art cannot use them.
  vm.runInNewContext(source, { document, window });
  return { api: window.AssessmentScanner, document, stage, classes, listeners };
}
test('all original category motifs replace prior artwork and stop clears transient graphics', () => {
  const h = harness(), graphics = new Set();
  for (const area of ['Skin', 'Hair', 'Nails', 'Sweat']) {
    h.api.start(area); assert.equal(h.stage.dataset.variant, area.toLowerCase());
    assert(h.classes.has('is-scanning')); assert.match(h.stage.innerHTML, /aria-hidden="true"/);
    assert.match(h.stage.innerHTML, /scanner-beam/); graphics.add(h.stage.innerHTML);
    h.api.stop(); assert.equal(h.stage.innerHTML, ''); assert.equal(h.stage.dataset.variant, undefined); assert(!h.classes.has('is-scanning'));
  }
  assert.equal(graphics.size, 4);
});
test('visibility pauses and resumes the active illustration without timers or changing its content', () => {
  const h = harness(); h.document.hidden = true; h.api.start('Hair'); const art = h.stage.innerHTML;
  assert(h.classes.has('is-paused')); h.document.hidden = false; h.listeners.visibilitychange();
  assert(!h.classes.has('is-paused')); assert.equal(h.stage.innerHTML, art);
  h.api.stop(); h.document.hidden = true; h.listeners.visibilitychange(); assert.equal(h.stage.innerHTML, '');
});
test('unsupported and inherited object names cannot leave or create an active illustration', () => {
  const h = harness();
  for (const invalid of ['Unknown', 'constructor', '__proto__', null]) {
    h.api.start('Skin'); h.api.start(invalid); assert.equal(h.stage.innerHTML, ''); assert(!h.classes.has('is-scanning'));
  }
});
