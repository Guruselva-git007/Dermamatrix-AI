async page => {
  // Synthetic local stack only. This does not activate delivery or touch normal accounts.
  const checks = [], errors = [], samples = [];
  const root = '../local-artifacts/product-maturity-2026-10-28/';
  const password = 'Synthetic-quality-only-84!';
  const emailA = 'quality-a-' + Date.now() + '@example.invalid';
  const emailB = 'quality-b-' + Date.now() + '@example.invalid';
  page.on('pageerror', error => errors.push(error.message));
  const assert = (value, message) => { if (!value) throw Error(message); };
  const nav = route => page.locator(`[data-page-nav="${route}"]`).click();
  async function authenticate(email, name = '') {
    await page.evaluate(tab => showAuthGate(tab), name ? 'register' : 'login');
    const form = page.locator(name ? '#registerForm' : '#loginForm');
    if (name) await form.locator('[name=full_name]').fill(name);
    await form.locator('[name=email_address]').fill(email);
    await form.locator('[name=password]').fill(password);
    if (name) {
      await form.locator('[name=confirm_password]').fill(password);
      await form.locator('[name=account_consent]').check();
    }
    await form.locator('[type=submit]').click();
    await page.waitForFunction(email => state.profile?.email_address === email && !document.querySelector('#authGate').classList.contains('show') && !document.querySelector('#registerForm [type=submit]').disabled && !document.querySelector('#loginForm [type=submit]').disabled, email);
    if (await page.locator('#welcomeDialog').evaluate(e => e.open)) await page.locator('#closeWelcome').click();
  }
  async function logout() {
    await page.locator('#navLogoutButton').click();
    await page.waitForFunction(() => !state.profile);
  }
  async function questionnaire(urgent) {
    await page.setViewportSize({ width: 1440, height: 960 });
    await nav('home');
    await page.locator('.area-choice [data-area=Sweat]').click();
    await page.evaluate(() => {
      let details = document.querySelector('#urgentConcern').closest('details');
      while (details) { details.open = true; details = details.parentElement?.closest('details'); }
    });
    await page.locator('#urgentConcern').setChecked(urgent);
    await page.locator('#imageConsent').check();
    await page.locator('#analyzeButton').click();
    await page.locator('#confirmAssessmentReview').click();
    await page.locator('#resultModal.show').waitFor();
    await page.locator('#resultPlainExplanation').waitFor();
  }
  try {
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.context().clearCookies();
    let releaseStartup;
    const startupGate = new Promise(resolve => { releaseStartup = resolve; });
    await page.route('**/api/auth/me', async route => {
      const response = await route.fetch(); await startupGate; await route.fulfill({ response });
    });
    await page.goto('http://127.0.0.1:8001/');
    await page.evaluate(() => showAuthGate('register'));
    await page.locator('#registerForm [name=full_name]').fill('Synthetic chosen registration');
    const startupResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/auth/me');
    releaseStartup(); await (await startupResponse).finished(); await page.waitForTimeout(80);
    await page.unroute('**/api/auth/me');
    assert(await page.locator('#registerForm').isVisible() && await page.locator('#registerForm [name=full_name]').inputValue() === 'Synthetic chosen registration', 'Startup replaced the chosen authentication form');
    checks.push('slow startup preserves the chosen account form and input');
    await authenticate(emailA, 'Synthetic quality account A');

    let held = false, resume, captured;
    const gate = new Promise(resolve => { resume = resolve; });
    const ready = new Promise(resolve => { captured = resolve; });
    await page.route('**/api/profile', async route => {
      if (route.request().method() === 'GET' && !held) {
        held = true;
        const response = await route.fetch();
        captured(); await gate; await route.fulfill({ response });
      } else await route.continue();
    });
    await page.evaluate(() => { window.qualityHydration = hydrateProfile(); });
    await ready; await logout(); await authenticate(emailB, 'Synthetic quality account B');
    resume(); await page.evaluate(() => window.qualityHydration); await page.unroute('**/api/profile');
    assert(await page.evaluate(email => state.profile?.email_address === email && document.querySelector('#profileName').textContent === 'Synthetic quality account B', emailB), 'Delayed profile crossed the account boundary');
    checks.push('delayed profile response cannot replace the next account');

    await nav('settings'); await page.getByRole('button', { name: 'Health notes', exact: true }).click();
    await page.locator('#profileForm [name=past_history]').fill('Synthetic private draft belonging to account B');
    await page.locator('#profileForm [name=health_data_consent]').check();
    await page.evaluate(() => {
      const original = window.ConsumerClient.prepare;
      let release;
      const gate = new Promise(resolve => { release = resolve; });
      window.qualityPreparation = { original, release, started: false };
      window.ConsumerClient.prepare = async options => {
        const prepared = await original(options);
        if (options.method === 'PATCH' && !window.qualityPreparation.started) {
          window.qualityPreparation.started = true; await gate;
        }
        return prepared;
      };
    });
    let patches = 0;
    const recordPatch = request => { if (request.method() === 'PATCH' && new URL(request.url()).pathname === '/api/profile') patches += 1; };
    page.on('request', recordPatch);
    await page.locator('#profileForm [type=submit]').click();
    await page.waitForFunction(() => window.qualityPreparation.started);
    await page.locator('#profileForm .profile-actions [data-close-profile]').click();
    await logout(); await authenticate(emailA);
    await page.evaluate(() => { window.qualityPreparation.release(); window.ConsumerClient.prepare = window.qualityPreparation.original; });
    await page.waitForTimeout(100);
    page.removeListener('request', recordPatch);
    assert(patches === 0, 'A private profile draft was submitted under the new account');
    const cleanProfile = await page.evaluate(() => requestJSON('/api/profile'));
    assert(cleanProfile.email_address === emailA && !cleanProfile.past_history, 'Profile isolation failed after preparation');
    assert(!await page.locator('#profileForm [type=submit]').isDisabled(), 'New account inherited the old save lock');
    checks.push('account switch during CSRF preparation sends no old private draft');

    for (const route of ['dashboard', 'home', 'progress', 'learn', 'settings', 'support', 'products']) {
      await nav(route);
      assert(await page.locator('[data-page-nav][aria-current=page]').count() === 1, 'Current page is ambiguous');
      assert(await page.locator(`[data-page-nav="${route}"]`).getAttribute('aria-current') === 'page', 'Current page announcement is wrong');
    }
    checks.push('one accurate current-page navigation cue across all destinations');

    await page.waitForSelector('#productCatalog .catalog-card--product');
    assert(await page.locator('#productCatalog .catalog-card--product').count() > 3, 'Catalogue fixture is too small to exercise wrapping');
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => applyTheme(theme), theme);
      for (const width of [320, 390, 768, 1280, 1440]) {
        await page.setViewportSize({ width, height: 960 }); await page.waitForTimeout(300);
        const geometry = await page.evaluate(() => {
          const cards = [...document.querySelectorAll('#productCatalog .catalog-card--product')];
          const controls = [...document.querySelectorAll('#productCatalog a')];
          const luminance = color => color.match(/[\d.]+/g).slice(0, 3).map(Number).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((sum, value, i) => sum + value * [.2126, .7152, .0722][i], 0);
          const ratios = cards.flatMap(card => [...card.querySelectorAll('h3,.catalog-type,.catalog-key-attributes,a')].map(e => {
            const foreground = luminance(getComputedStyle(e).color), background = luminance(getComputedStyle(card).backgroundColor);
            return (Math.max(foreground, background) + .05) / (Math.min(foreground, background) + .05);
          }));
          return { count: cards.length, clipped: controls.filter(e => { const r = e.getBoundingClientRect(); return r.left < 0 || r.right > innerWidth + 1; }).length, rows: new Set(cards.map(e => Math.round(e.getBoundingClientRect().top))).size, overflow: document.documentElement.scrollWidth > innerWidth, targets: controls.every(e => e.getBoundingClientRect().height >= 43), contrastMin: Math.min(...ratios), plex: document.fonts.check('16px "IBM Plex Sans"') && cards.every(e => getComputedStyle(e.querySelector('h3')).fontFamily.includes('IBM Plex Sans')) };
        });
        assert(!geometry.clipped && !geometry.overflow && geometry.rows > 1 && geometry.targets && geometry.contrastMin >= 4.5 && geometry.plex, `Catalogue reflow, contrast or font failure at ${width} in ${theme}`);
        samples.push({ theme, width, ...geometry });
        if ([390, 1440].includes(width)) await page.screenshot({ path: root + `quality-products-${theme}-${width}.png` });
      }
    }
    checks.push('all catalogue cards and external controls reflow at five widths in both themes');
    await page.setViewportSize({ width: 1440, height: 960 }); await page.evaluate(() => applyTheme('light'));
    await page.locator('[data-filter=nails]').click();
    assert(await page.locator('#productCatalog article').count() > 0, 'Category filter lost results');
    assert(await page.locator('#productCatalog article:not([data-category=nails])').count() === 0, 'Category filter mixed unrelated results');
    await page.locator('[data-filter=all]').click(); await page.locator('#productFiltersToggle').click();
    assert(await page.locator('#productFilterPanel').isVisible(), 'Filters did not open');
    await page.locator('#productSort').selectOption('name');
    const link = page.locator('#productCatalog a').last(); await link.focus();
    await page.waitForFunction(() => {
      const e = [...document.querySelectorAll('#productCatalog a')].at(-1), r = e.getBoundingClientRect();
      return document.activeElement === e && r.top >= 64 && r.bottom <= innerHeight + 1;
    });
    assert(await link.evaluate(e => { const r = e.getBoundingClientRect(); return document.activeElement === e && r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight + 1; }), 'Last product link cannot be reached visibly by keyboard');
    checks.push('existing category filters, sorting and last-card keyboard access');

    await questionnaire(true);
    const warning = await page.evaluate(async () => {
      const detail = await requestJSON('/api/assessments/' + encodeURIComponent(state.assessmentId));
      const root = document.querySelector('#patientResultContent');
      return { original: detail.summary.urgent_notice, visible: root.firstElementChild.textContent, isAlert: root.firstElementChild.getAttribute('role') === 'alert' };
    });
    assert(warning.original && warning.isAlert && warning.visible.includes(warning.original), 'Recorded warning was not prioritized accurately');
    await page.locator('#patientResultContent > .patient-urgent-alert button').click();
    assert(await page.locator('#support').evaluate(e => e.classList.contains('page-active')), 'Warning care handoff failed');
    checks.push('actual questionnaire warning leads and opens existing professional support');

    await questionnaire(false);
    for (const width of [320, 390, 768, 1280, 1440]) {
      await page.setViewportSize({ width, height: 960 }); await page.waitForTimeout(160);
      const order = await page.evaluate(() => {
        const root = document.querySelector('#patientResultContent');
        const lead = root.querySelector('.assessment-state-card, .consumer-hero, .patient-result-hero');
        const explanation = root.querySelector('#resultPlainExplanation'), technical = root.querySelector('#patientTechnicalSlot');
        return { leadFirst: Boolean(lead.compareDocumentPosition(explanation) & Node.DOCUMENT_POSITION_FOLLOWING), technicalLast: Boolean(explanation.compareDocumentPosition(technical) & Node.DOCUMENT_POSITION_FOLLOWING), titleY: lead.querySelector('h3').getBoundingClientRect().top, nextY: lead.querySelector('button').getBoundingClientRect().top, questions: explanation.querySelectorAll('dt').length };
      });
      assert(order.leadFirst && order.technicalLast && order.questions === 4 && order.titleY < 400 && order.nextY < 960, 'Main result or next action buried at ' + width);
      if ([390, 1440].includes(width)) await page.screenshot({ path: root + `quality-result-${width}.png` });
    }
    checks.push('supported finding and next action lead while all four explanations and technical evidence remain');
    await page.keyboard.press('Escape');
    assert(!await page.locator('#resultModal').evaluate(e => e.classList.contains('show')), 'Result keyboard dismissal failed');
    checks.push('result keyboard dismissal and existing focus lifecycle');

    await page.setViewportSize({ width: 1440, height: 960 }); await logout();
    assert(await page.evaluate(() => !state.profile && !document.querySelector('#patientResultContent') && document.querySelector('#authGate').classList.contains('show') && document.querySelector('.app-shell').inert), 'Sign-out did not clear and isolate the private workspace');
    await page.locator('#continueGuestButton').click();
    await page.waitForFunction(() => state.isGuest && !document.querySelector('#authGate').classList.contains('show'));
    assert(await page.evaluate(() => !state.profile && !document.querySelector('#patientResultContent') && !document.querySelector('.app-shell').inert), 'Guest workspace retained private evidence');
    checks.push('final account clearing preserves guest boundary');
    assert(!errors.length, errors.join('; '));
    return { checks, errors, samples };
  } catch (error) {
    throw Error(error.message + ' | Completed: ' + checks.join(', ') + ' | Browser errors: ' + errors.join('; '));
  }
}
