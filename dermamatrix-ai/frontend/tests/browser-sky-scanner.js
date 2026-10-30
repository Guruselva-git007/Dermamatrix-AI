async (page, options = {}) => {
  // Synthetic loopback only. Held responses inspect real waiting UI, not model speed.
  const checks = [], samples = [], errors = [], measures = {};
  const root = options.artifactRoot;
  const assert = (ok, message) => { if (!ok) throw Error(message); };
  const capture = async name => { if (root) await page.screenshot({ path: root + name + '.png' }); };
  page.on('pageerror', e => errors.push(e.message));
  async function theme(value) {
    await page.evaluate(t => applyTheme(t), value);
    await page.waitForFunction(t => getComputedStyle(document.body).backgroundColor === (t === 'light' ? 'rgb(247, 251, 255)' : 'rgb(8, 24, 46)'), value);
    // Finish only finite theme transitions before computed-color assertions.
    await page.evaluate(async () => { await Promise.all(document.getAnimations().filter(a => a.effect.getTiming().iterations !== Infinity).map(a => a.finished.catch(() => {}))); });
  }
  async function choose(area) {
    await page.evaluate(() => showPage('home', { scrollToTop: false }));
    await page.locator(`.area-choice [data-area=${area}]`).click();
    if (area !== 'Sweat') {
      // Original synthetic PNG fixture made in memory; never a person's photo.
      const png = await page.evaluate(async () => {
        const c = document.createElement('canvas'); c.width = c.height = 240;
        const ctx = c.getContext('2d'); ctx.fillStyle = '#ae8e7a'; ctx.fillRect(0, 0, 240, 240);
        ctx.strokeStyle = '#776755'; for (let i = 0; i < 240; i += 8) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(240 - i, 240); ctx.stroke(); }
        return c.toDataURL('image/png').split(',')[1];
      });
      await page.locator('#imageInput').setInputFiles({ name: 'synthetic-scanner.png', mimeType: 'image/png', buffer: Buffer.from(png, 'base64') });
      await page.waitForFunction(() => !!state.file && state.imageReadiness?.status !== 'CHECKING');
    }
    await page.locator('#imageConsent').check();
  }
  async function begin() {
    await page.locator('#analyzeButton').click();
    await page.locator('#confirmAssessmentReview').click();
    await page.locator('#processingModal.show').waitFor();
  }
  async function held(path, action = 'abort') {
    let release, seen, handled;
    const gate = new Promise(r => { release = r; }), ready = new Promise(r => { seen = r; }), done = new Promise(r => { handled = r; });
    const handler = async route => {
      const response = action === 'complete' ? await route.fetch() : null;
      seen(); await gate;
      try {
        if (action === 'complete') await route.fulfill({ response });
        else if (action === 'error') await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: 'Synthetic temporary assessment failure' }) });
        else await route.abort();
      } finally { handled(); }
    };
    await page.route(path, handler);
    return { ready, async finish() { release(); await done; await page.unroute(path, handler); } };
  }
  try {
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.context().clearCookies(); await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto('http://127.0.0.1:8001/?sky-scanner=' + Date.now());
    await page.locator('#authGate.show').waitFor();
    for (const t of ['light', 'dark']) { await theme(t); await capture('auth-' + t); }
    await page.locator('#continueGuestButton').click();
    await page.waitForFunction(() => state.isGuest && !document.querySelector('#authGate').classList.contains('show'));
    if (await page.locator('#welcomeDialog').evaluate(e => e.open)) await page.locator('#closeWelcome').click();
    await page.waitForFunction(() => !document.querySelector('#imageConsent').disabled);
    await page.evaluate(() => { document.body.classList.remove('reduce-motion'); localStorage.setItem('dermamatrix_reduced_motion', 'false'); });
    for (const t of ['light', 'dark']) {
      await theme(t);
      for (const width of [320, 390, 768, 1280, 1440]) {
        await page.setViewportSize({ width, height: 960 });
        if (width <= 880) await page.waitForFunction(() => getComputedStyle(document.querySelector('.sidebar')).visibility === 'hidden');
        for (const route of ['dashboard', 'home', 'progress', 'learn', 'products', 'support', 'settings']) {
          await page.evaluate(r => showPage(r, { scrollToTop: false }), route);
          const sample = await page.evaluate(route => {
            const style = e => ({ bg: getComputedStyle(e).backgroundColor, color: getComputedStyle(e).color });
            const primary = document.querySelector('.dashboard-heading .primary');
            return { route, width: innerWidth, theme: document.body.dataset.theme, themeColor: document.querySelector('meta[name=theme-color]').content, overflow: document.documentElement.scrollWidth > innerWidth + 1, body: style(document.body), card: style(document.querySelector('.dashboard-actions-section')), primary: style(primary), font: getComputedStyle(document.body).fontFamily };
          }, route);
          assert(sample.themeColor === (t === 'light' ? '#f7fbff' : '#08182e'), 'Browser chrome retains an obsolete theme color');
          assert(!sample.overflow, 'Horizontal overflow: ' + JSON.stringify(sample));
          assert(sample.card.bg === (t === 'light' ? 'rgb(255, 255, 255)' : 'rgb(16, 43, 73)'), 'Legacy surface overrides restored palette');
          assert(sample.primary.bg === (t === 'light' ? 'rgb(8, 104, 175)' : 'rgb(120, 198, 255)'), 'Primary action not restored');
          assert(sample.font.includes('IBM Plex Sans'), 'Plex type lost'); samples.push(sample);
          if (root && (width === 1440 || ['dashboard', 'home'].includes(route))) await page.screenshot({ path: root + `${route}-${t}-${width}.png`, animations: 'disabled' });
        }
      }
    }
    checks.push('white/sky and navy/cyan computed tokens, Plex and reflow across seven destinations at five widths in both themes');
    const contrasts = [];
    for (const t of ['light', 'dark']) {
      await page.evaluate(() => showPage('dashboard', { scrollToTop: false })); await theme(t);
      await page.waitForFunction(t => getComputedStyle(document.querySelector('.nav-links a.active')).color === (t === 'light' ? 'rgb(8, 104, 175)' : 'rgb(120, 198, 255)'), t);
      const contrast = await page.evaluate(() => {
        const c = value => value.match(/[\d.]+/g).slice(0, 3).map(Number);
        const luminance = rgb => rgb.map(n => { const v = n / 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
        const ratio = (a, b) => { const v = [luminance(c(a)), luminance(c(b))].sort((a, b) => b - a); return (v[0] + .05) / (v[1] + .05); };
        const style = selector => getComputedStyle(document.querySelector(selector));
        const surface = style('.dashboard-actions-section').backgroundColor, body = style('body');
        return { theme: document.body.dataset.theme, ink: ratio(body.color, body.backgroundColor), secondary: ratio(style('.scope-note').color, surface), primary: ratio(style('.dashboard-heading .primary').color, style('.dashboard-heading .primary').backgroundColor), selectedNav: ratio(style('.nav-links a.active').color, style('.nav-links a.active').backgroundColor), control: ratio(style('.dashboard-action').borderTopColor, surface) };
      });
      assert([contrast.ink, contrast.secondary, contrast.primary, contrast.selectedNav].every(n => n >= 4.5) && contrast.control >= 3, 'Restored palette fails representative contrast: ' + JSON.stringify(contrast)); contrasts.push(contrast);
    }
    measures.contrasts = contrasts;
    checks.push('computed text, primary action, selected navigation and control boundaries meet applicable contrast thresholds in both themes');
    // Guest appearance persistence; no private health information enters storage.
    await page.locator('#themeToggle').click(); const chosen = await page.locator('body').getAttribute('data-theme');
    await page.reload(); await page.waitForFunction(() => state.isGuest || document.querySelector('#authGate').classList.contains('show')); await page.waitForFunction(t => document.body.dataset.theme === t, chosen);
    assert(await page.evaluate(() => localStorage.getItem('dermamatrix_theme')) === chosen, 'Appearance preference not retained');
    if (await page.locator('#authGate.show').count()) { await page.locator('#continueGuestButton').click(); await page.waitForFunction(() => state.isGuest && !document.querySelector('#authGate').classList.contains('show')); }
    if (await page.locator('#welcomeDialog').evaluate(e => e.open)) await page.locator('#closeWelcome').click();
    await page.waitForFunction(() => !document.querySelector('#imageConsent').disabled);
    checks.push('theme control and reload retain the selected guest appearance');
    await page.setViewportSize({ width: 1440, height: 960 });
    for (const area of ['Skin', 'Hair', 'Nails', 'Sweat']) {
      await choose(area);
      for (const t of ['light', 'dark']) {
        await theme(t);
        const fields = await page.locator('#screen select, #screen input:not([type=checkbox]):not([type=radio]):not([type=file]), #screen textarea').evaluateAll(elements => elements.filter(e => e.getClientRects().length).map(e => ({ id: e.id, bg: getComputedStyle(e).backgroundColor, color: getComputedStyle(e).color, font: getComputedStyle(e).fontFamily, size: parseFloat(getComputedStyle(e).fontSize) })));
        assert(fields.length && fields.every(e => e.bg === (t === 'light' ? 'rgb(255, 255, 255)' : 'rgb(16, 43, 73)') && e.color === (t === 'light' ? 'rgb(23, 52, 84)' : 'rgb(237, 247, 255)') && e.font.includes('IBM Plex Sans') && e.size >= 16), 'Selected pathway has legacy unreadable controls: ' + JSON.stringify(fields));
        if (root) await page.screenshot({ path: root + `input-${area.toLowerCase()}-${t}.png`, animations: 'disabled' });
      }
      const h = await held(area === 'Sweat' ? '**/api/sweat-assessments' : '**/api/assessments');
      await begin(); await h.ready;
      const stage = page.locator('#assessmentScanner');
      assert(await stage.getAttribute('data-variant') === area.toLowerCase(), 'Wrong scan variant');
      assert(await stage.getAttribute('aria-hidden') === 'true' && await stage.locator('svg').getAttribute('focusable') === 'false', 'Decorative art announced');
      assert(await page.locator('#processingStatus').getAttribute('role') === 'status', 'Processing status not accessible');
      assert(!/\d+%|diagnos|identified|detected/i.test(await page.locator('#processingStatus').textContent()), 'Invented progress/capability');
      assert(await page.evaluate(() => document.activeElement.id) === 'processingTitle', 'Processing title not focused');
      const motion = await stage.evaluate(async e => {
        const beam = e.querySelector('.scanner-beam'), before = getComputedStyle(beam).transform;
        await new Promise(resolve => setTimeout(resolve, 100));
        return { before, after: getComputedStyle(beam).transform, animations: e.getAnimations({ subtree: true }).length, children: e.querySelectorAll('*').length };
      });
      assert(motion.before !== motion.after && motion.animations === 2, 'Scan is static or has unexpected background work');
      for (const t of ['light', 'dark']) { await theme(t); await capture('scanner-' + area.toLowerCase() + '-' + t); }
      measures[area] = motion;
      if (area === 'Skin') measures.frameSample = await stage.evaluate(() => new Promise(resolve => {
        const deltas = [], shifts = []; let observer;
        if (typeof PerformanceObserver !== 'undefined' && PerformanceObserver.supportedEntryTypes.includes('layout-shift')) {
          observer = new PerformanceObserver(list => shifts.push(...list.getEntries().filter(e => !e.hadRecentInput).map(e => e.value)));
          observer.observe({ type: 'layout-shift' });
        }
        let last = performance.now(), start = last;
        function frame(now) {
          deltas.push(now - last); last = now;
          if (now - start < 600) requestAnimationFrame(frame);
          else { observer?.disconnect(); const sorted = [...deltas].sort((a,b) => a-b); resolve({ durationMs: now - start, frames: deltas.length, medianMs: sorted[Math.floor(sorted.length/2)], p95Ms: sorted[Math.floor(sorted.length*.95)], layoutShiftSupported: !!observer, activeStageLayoutShift: shifts.reduce((a,b) => a+b, 0) }); }
        }
        requestAnimationFrame(frame);
      }));
      assert(await page.evaluate(() => selectArea('Sweat')) === false, 'Category changed during the active assessment');
      await page.keyboard.press('Tab'); assert(await page.locator('#processingModal').evaluate(e => e.contains(document.activeElement)), 'Focus escaped processing');
      await page.locator('#cancelAssessmentButton').click(); await h.finish();
      assert(await stage.locator('*').count() === 0 && await stage.evaluate(e => e.getAnimations({ subtree: true }).length) === 0, 'Animation survives cancellation');
      assert(await page.evaluate(() => !state.assessmentInFlight && state.assessmentState === AssessmentState.CANCELLED), 'Cancel did not return safe state');
      if (area !== 'Sweat') assert(await page.evaluate(() => !!state.file && !!state.imageUrl), 'Cancellation lost safe current-tab photo');
      checks.push(area + ' real-request variant animates; decorative semantics, focus containment and cancellation dispose it without input loss');
    }
    // CSS pause is synchronous with actual visibilitychange; emulate only this
    // signal, not a physical locked-screen/browser-background acceptance claim.
    await choose('Sweat'); const motionHold = await held('**/api/sweat-assessments'); await begin(); await motionHold.ready;
    await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: true }); document.dispatchEvent(new Event('visibilitychange')); });
    assert(await page.locator('.scanner-beam').evaluate(e => getComputedStyle(e).animationPlayState) === 'paused', 'Hidden scanner not paused');
    await page.evaluate(() => { delete document.hidden; document.dispatchEvent(new Event('visibilitychange')); });
    checks.push('hidden-document signal pauses decorative motion without changing processing');
    for (const kind of ['system', 'account']) {
      if (kind === 'system') await page.emulateMedia({ reducedMotion: 'reduce' });
      else await page.evaluate(() => document.body.classList.add('reduce-motion'));
      assert(await page.locator('.scanner-beam').evaluate(e => getComputedStyle(e).animationName) === 'none', 'Motion preference ignored');
      assert(await page.locator('#processingStatus').isVisible(), 'Reduced motion removed processing information');
      await capture('scanner-reduced-' + kind);
      await page.emulateMedia({ reducedMotion: 'no-preference' }); await page.evaluate(() => document.body.classList.remove('reduce-motion'));
    }
    checks.push('system and in-app reduced motion stop movement while preserving status and Stop waiting');
    for (const width of [320, 390, 768, 1280, 1440]) {
      await page.setViewportSize({ width, height: width === 320 ? 600 : 960 });
      const box = await page.locator('.processing-card').evaluate(e => ({ overflow: e.scrollWidth > e.clientWidth + 1, width: innerWidth, height: e.getBoundingClientRect().height, available: innerHeight, title: e.querySelector('h2').getBoundingClientRect().top, cardBottom: e.getBoundingClientRect().bottom, stopBottom: e.querySelector('#cancelAssessmentButton').getBoundingClientRect().bottom }));
      assert(!box.overflow && box.height <= box.available && box.title >= 0 && box.stopBottom <= box.cardBottom,  'Scanner clips essential information');
      await capture('scanner-responsive-' + width); samples.push(box);
    }
    const fontStyle = await page.addStyleTag({ content: '.processing-card { font-size: 200%; } .processing-card h2 {font-size:2.75rem} .processing-card p, .processing-details summary, #cancelAssessmentButton {font-size:1.75rem}' });
    await page.setViewportSize({ width: 320, height: 800 }); await page.locator('#cancelAssessmentButton').scrollIntoViewIfNeeded();
    assert(await page.locator('.processing-card').evaluate(e => e.scrollWidth <= e.clientWidth + 1), 'Enlarged processing text overflows');
    await capture('scanner-text-200-320'); await fontStyle.evaluate(e => e.remove());
    await page.locator('#cancelAssessmentButton').click(); await motionHold.finish();
    checks.push('processing at five widths and enlarged text retains readable status and reachable cancellation');
    await page.setViewportSize({ width: 1440, height: 960 });
    const fail = await held('**/api/sweat-assessments', 'error'); await begin(); await fail.ready; await fail.finish();
    await page.locator('#processingModal.show').waitFor({ state: 'hidden' });
    assert(await page.locator('#assessmentScanner *').count() === 0 && await page.locator('#assessmentFeedback').isVisible() && !await page.locator('#resultModal').evaluate(e => e.classList.contains('show')), 'Failure left scanner or displayed success');
    checks.push('server failure removes scanner, preserves inputs and provides retry without a successful result');
    let posts = 0; const count = req => { if (req.method() === 'POST' && new URL(req.url()).pathname === '/api/sweat-assessments') posts++; }; page.on('request', count);
    const success = await held('**/api/sweat-assessments', 'complete'); await begin(); await success.ready;
    await page.evaluate(() => analyze()); assert(posts === 1, 'Duplicate assessment submitted while busy');
    const started = Date.now(); await success.finish(); await page.locator('#resultModal.show').waitFor(); measures.responseReleaseToResultMs = Date.now() - started;
    assert(await page.locator('#assessmentScanner *').count() === 0, 'Completed scanner remains');
    assert(!await page.locator('#toast').isVisible(), 'Earlier failure message obscures the successful retry');
    assert(await page.evaluate(() => state.resultPersistence === 'not-persisted-guest' && state.reviewResultReady), 'Guest result not ready or persisted');
    for (const t of ['light', 'dark']) { await theme(t); await capture('result-' + t); }
    checks.push('real questionnaire result replaces scanning immediately, blocks duplicate submission and preserves guest privacy');
    await page.locator('#resultModal .modal-close').click(); page.off('request', count);
    const accountHold = await held('**/api/sweat-assessments'); await begin(); await accountHold.ready;
    await page.evaluate(() => clearWorkspaceEvidence()); await accountHold.finish();
    assert(await page.locator('#assessmentScanner *').count() === 0 && !await page.locator('#processingModal').evaluate(e => e.classList.contains('show')), 'Workspace clearing left a stale scanner');
    assert(await page.evaluate(() => !state.file && !state.imageUrl && !state.assessmentInFlight), 'Workspace clearing retained transient evidence');
    checks.push('workspace/account clearing disposes the scanner and temporary input; late work cannot reopen it');
    if (errors.length) throw Error(errors.join('; '));
    return { checks, samples, measures, errors };
  } catch (error) { return { checks, samples, measures, errors: [...errors, error.message] }; }
}
