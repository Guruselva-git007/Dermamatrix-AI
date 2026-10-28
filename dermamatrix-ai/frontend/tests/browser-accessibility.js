async (page, options = {}) => {
  // Targeted semantics/keyboard checks, not an automated WCAG conformance claim.
  const checks = [], errors = [], snapshots = {}, samples = [];
  const assert = (value, message) => { if (!value) throw Error(message); };
  page.on('pageerror', error => errors.push(error.message));
  try {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.context().clearCookies();
  await page.goto('http://127.0.0.1:8001/?accessibility-probe=' + Date.now());
  await page.locator('#authGate.show').waitFor();
  assert(await page.locator('html').getAttribute('lang') === 'en', 'Page language changed');
  assert((await page.title()).includes('DermaMatrix'), 'Page title missing');
  assert(!/user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?:\D|$)/i.test(await page.locator('meta[name=viewport]').getAttribute('content')), 'Zoom is restricted');
  checks.push('English page identity and unrestricted viewport zoom');
  assert(await page.getByRole('textbox', { name: 'Email address', exact: true }).count() === 1, 'Login email name missing');
  assert(await page.getByRole('button', { name: 'Show password', exact: true }).count() === 1, 'Password toggle name missing');
  assert(await page.locator('#authMessage').getAttribute('role') === 'alert', 'Authentication errors lack alert semantics');
  checks.push('named authentication controls and error announcement semantics');
  await page.locator('#continueGuestButton').click();
  await page.waitForFunction(() => state.isGuest && !document.querySelector('#authGate').classList.contains('show'));
  if (await page.locator('#welcomeDialog').evaluate(e => e.open)) await page.locator('#closeWelcome').click();
  for (const route of ['dashboard', 'home', 'progress', 'learn', 'settings', 'products', 'support']) {
    await page.locator(`[data-page-nav="${route}"]`).click();
    const problems = await page.evaluate(() => {
      const visible = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && !e.closest('[inert],[hidden],details:not([open])');
      const root = document.querySelector('.page-active'), problems = [];
      for (const e of root.querySelectorAll('input:not([type=hidden]),select,textarea')) {
        if (!visible(e)) continue;
        const name = e.getAttribute('aria-label') || (e.getAttribute('aria-labelledby') || '').split(/\s+/).map(id => document.getElementById(id)?.textContent || '').join('').trim() || [...e.labels || []].map(label => label.textContent).join('').trim();
        if (!name) problems.push('unnamed ' + (e.id || e.tagName));
      }
      if ([...root.querySelectorAll('[tabindex]')].some(e => visible(e) && e.tabIndex > 0)) problems.push('positive tabindex');
      return problems;
    });
    assert(!problems.length, route + ': ' + problems.join('; '));
    assert(await page.locator('.page-active h1').count() === 1, route + ' primary heading missing');
  }
  checks.push('seven workspace routes retain labelled visible inputs and primary headings');
  await page.locator('[data-page-nav=home]').click();
  await page.locator('[data-area=Skin]').click();
  assert(await page.getByLabel('Choose or replace assessment image', { exact: true }).count() === 1, 'File chooser accessible name missing');
  const accepted = await page.locator('#imageInput').getAttribute('accept');
  assert(['image/heic', 'image/heif', '.heic', '.heif'].every(format => accepted.split(',').includes(format)), 'HEIC/HEIF selection missing');
  assert((await page.locator('#uploadFormat').textContent()).includes('HEIF'), 'Visible upload guidance omits supported formats');
  checks.push('file chooser has a usable name and preserves supported image selection');
  await page.locator('[data-area=Sweat]').click();
  await page.locator('#sweatLocation').fill('Synthetic palms');
  await page.locator('#analyzeButton').click();
  assert(await page.locator('#consentError').isVisible(), 'Missing consent did not show a recoverable error');
  assert(!await page.locator('#assessmentReviewDialog').evaluate(d => d.open), 'Missing consent opened review');
  checks.push('missing consent produces local feedback without opening a review');
  await page.locator('#imageConsent').check();
  for (const size of [{ width: 390, height: 844 }, { width: 320, height: 600 }]) {
    await page.setViewportSize(size);
    await page.locator('#analyzeButton').click();
    const sample = await page.locator('#assessmentReviewDialog').evaluate(d => {
      const heading = d.querySelector('h2'), r = heading.getBoundingClientRect(), box = d.getBoundingClientRect();
      return { width: innerWidth, focus: document.activeElement.id, top: r.top, bottom: r.bottom, dialogTop: box.top, dialogBottom: box.bottom, scrollTop: d.scrollTop, scrollWidth: d.scrollWidth, clientWidth: d.clientWidth };
    });
    samples.push(sample);
    assert(sample.focus === 'assessmentReviewTitle' && sample.top >= sample.dialogTop && sample.bottom <= sample.dialogBottom && sample.scrollWidth <= sample.clientWidth + 1, 'Review begins below its explanation: ' + JSON.stringify(sample));
    snapshots['review-' + size.width] = await page.locator('#assessmentReviewDialog').ariaSnapshot();
    if (options.artifactRoot) await page.screenshot({ path: options.artifactRoot + 'review-' + size.width + '.png' });
    // Safari's all-controls traversal can use Option-Tab under Mac preferences.
    let traversal;
    for (const key of ['Tab', 'Alt+Tab']) {
      for (let press = 0; press < 4; press++) {
        await page.keyboard.press(key);
        if (await page.evaluate(() => document.activeElement.id) === 'backToAssessment') { traversal = key; break; }
      }
      if (traversal) break;
    }
    assert(traversal, 'Review Back is not keyboard reachable');
    samples[samples.length - 1].traversal = traversal;
    await page.keyboard.press(traversal);
    assert(await page.evaluate(() => document.activeElement.id) === 'confirmAssessmentReview', 'Review confirmation is not keyboard reachable after Back');
    await page.keyboard.press('Escape');
    assert(!await page.locator('#assessmentReviewDialog').evaluate(d => d.open), 'Escape did not close review');
    await page.waitForFunction(()=>document.activeElement.id==='analyzeButton');
  }
  checks.push('narrow reviews initially expose the heading and opening explanation');
  checks.push('review keyboard reading order and Escape restore the invoking action');
  assert(await page.locator('#sweatLocation').inputValue() === 'Synthetic palms', 'Review cancellation lost answers');
  assert(await page.locator('#imageConsent').isChecked(), 'Review cancellation lost consent state');
  checks.push('cancelled review preserves the current-tab answers and consent');
  await page.locator('.menu-button').click();
  await page.locator('.sidebar').waitFor({state:'visible'});
  await page.waitForFunction(()=>document.querySelector('.sidebar').contains(document.activeElement));
  assert((await page.locator('.sidebar').ariaSnapshot()).startsWith('- dialog "Primary navigation"'), 'Mobile drawer name missing');
  await page.keyboard.press('Escape');
  assert(await page.locator('.menu-button').evaluate(e => e === document.activeElement), 'Drawer Escape lost focus');
  checks.push('mobile navigation has dialog semantics and restores keyboard focus');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  assert(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches && getComputedStyle(document.documentElement).scrollBehavior === 'auto'), 'Reduced motion still uses smooth page scrolling');
  checks.push('system reduced-motion preference disables smooth page scrolling');
  await page.locator('#analyzeButton').click();
  await page.locator('#confirmAssessmentReview').click();
  await page.locator('#resultModal.show').waitFor();
  snapshots.result = await page.locator('#resultModal').ariaSnapshot();
  assert(snapshots.result.includes('Review your sweat-pattern summary') && snapshots.result.includes('not a diagnosis'), 'Result meaning or uncertainty lost');
  await page.keyboard.press('Escape');
  assert(!await page.locator('#resultModal').evaluate(e => e.classList.contains('show')), 'Result Escape did not close');
  checks.push('guest questionnaire result retains clear evidence and keyboard dismissal');
  await page.reload();
  await page.locator('#authGate.show').waitFor();
  assert(await page.evaluate(() => !state.profile && !state.isGuest && !state.assessmentId && state.analyses.length === 0), 'Guest result survived reload as private account evidence');
  assert(!errors.length, errors.join('; '));
  checks.push('guest reload returns to account entry with no retained private evidence or uncaught errors');
  return { checks, errors, samples, snapshots, limits: ['Targeted DOM/keyboard checks do not establish actual screen-reader speech, native camera behavior or WCAG conformance.'] };
  } catch(error) {
    let context = {url: page.url()};
    try {context = await page.evaluate(()=>({url:location.href,focus:document.activeElement.id,area:state.area,guest:state.isGuest,inFlight:state.assessmentInFlight,status:document.querySelector('#assessmentStatus').textContent,toast:document.querySelector('#toast').textContent,consentError:document.querySelector('#consentError').textContent,reviewOpen:document.querySelector('#assessmentReviewDialog').open,processing:document.querySelector('#processingCopy')?.textContent}));} catch {}
    throw Error(error.message+' | Completed: '+checks.join('; ')+' | Context: '+JSON.stringify(context));
  }
}
