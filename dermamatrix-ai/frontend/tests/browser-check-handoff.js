async (page, options = {}) => {
  const checks = [], errors = [];
  const base = 'http://127.0.0.1:8001/';
  const assert = (condition, message) => { if (!condition) throw Error(message); };
  const nav = route => page.locator(`[data-page-nav="${route}"]`).click();
  const closeWelcome = async () => {
    if (await page.locator('#welcomeDialog').evaluate(dialog => dialog.open)) await page.locator('#closeWelcome').click();
  };
  const openLatest = page.locator('[data-dashboard-result]');
  const continueCheck = page.locator('#continueDashboardCheck');
  const result = page.locator('#resultModal');
  const view = () => page.locator('#journeyTabs [aria-selected=true]').getAttribute('data-view');
  const focused = id => page.evaluate(id => document.activeElement.id === id, id);
  const addPhoto = async () => {
    const bytes = await page.evaluate(() => {
      const canvas = document.createElement('canvas');
      canvas.width = 480;
      canvas.height = 360;
      const context = canvas.getContext('2d');
      context.fillStyle = '#5685a8';
      context.fillRect(0, 0, canvas.width, canvas.height);
      return canvas.toDataURL('image/png').split(',')[1];
    });
    await page.locator('#imageInput').setInputFiles({
      name: 'synthetic-check.png', mimeType: 'image/png', buffer: Buffer.from(bytes, 'base64')
    });
    await page.waitForFunction(() => state.file?.name === 'synthetic-check.png' && state.imageReadiness?.status !== 'CHECKING');
  };
  const review = async () => {
    await page.locator('#analyzeButton').click();
    await page.locator('#assessmentReviewDialog').waitFor();
    await page.locator('#confirmAssessmentReview').click();
  };
  page.on('pageerror', error => errors.push(error.message));

  try {
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.context().clearCookies();
    await page.goto(base);
    await page.locator('#continueGuestButton').click();
    await page.waitForFunction(() => state.isGuest && !document.getElementById('authGate').classList.contains('show'));
    await closeWelcome();
    assert(await continueCheck.isHidden() && await page.locator('#dashboardLowerGrid').isHidden(), 'Guest Today shows an invented draft or saved activity');
    assert(await page.locator('[data-dashboard-area]:visible').count() === 4, 'Guest concern choices are missing');
    await page.locator('[data-dashboard-area=Hair]').click();
    await addPhoto();
    await nav('dashboard');
    await continueCheck.press('Enter');
    assert(await focused('screenTitle') && await page.evaluate(() => state.area === 'Hair' && state.file?.name === 'synthetic-check.png'), 'Continuing lost the photo, area or focus');
    await page.locator('#analyzeButton').click();
    assert(await page.locator('#consentError').isVisible(), 'Continuing bypassed image consent');
    await page.locator('#imageConsent').check();
    await review();
    await page.locator('#resultModal.show').waitFor();
    assert((await page.locator('#resultWorkflowStatus').textContent()).includes('Guest result · not stored'), 'Guest photo has an incorrect save state');
    await result.locator('.modal-close').click();
    await nav('dashboard');
    assert(await continueCheck.isHidden(), 'Completed guest photo was labelled unfinished');
    checks.push('guest area choices, photo continuation, consent and real guest result');

    await page.locator('#navLogoutButton').click();
    await page.locator('[data-auth-tab=register]').click();
    const form = page.locator('#registerForm');
    const email = 'check-handoff-' + Date.now() + '@example.invalid';
    const password = 'Synthetic-Handoff-Only-84!';
    await form.locator('[name=full_name]').fill('Synthetic Check Handoff');
    await form.locator('[name=email_address]').fill(email);
    await form.locator('[name=password]').fill(password);
    await form.locator('[name=confirm_password]').fill(password);
    await form.locator('[name=account_consent]').check();
    await form.locator('[type=submit]').click();
    await page.waitForFunction(() => state.profile?.patient_id && state.progressLoadedFor === state.profile.patient_id && !document.querySelector('#registerForm [type=submit]').disabled);
    await closeWelcome();
    assert(await page.evaluate(() => !state.file && !state.areaSelected && !state.analyses.length), 'Previous guest check leaked into the new account');
    assert(await continueCheck.isHidden() && await page.locator('#dashboardLowerGrid').isHidden(), 'New account has a false draft or recent result');
    await page.getByRole('button', { name: 'Add a routine', exact: true }).click();
    assert(await view() === 'routines' && await focused('conditionLabel'), 'Add a routine did not open and focus the editor');
    await page.locator('#conditionLabel').fill('Synthetic observation');
    await page.locator('#routineName').fill('Synthetic evening log');
    await page.locator('#routineForm [type=submit]').click();
    await page.waitForFunction(() => state.routines.length === 1 && !document.querySelector('#routineForm [type=submit]').disabled);
    checks.push('fresh-account privacy and direct routine creation');

    await nav('dashboard');
    await page.locator('[data-dashboard-area=Sweat]').click();
    await page.locator('#sweatPattern').selectOption('excessive');
    await page.locator('#imageConsent').check();
    let savedId, submissionKey;
    const questionnaire = base + 'api/sweat-assessments';
    await page.route(questionnaire, async route => {
      submissionKey = route.request().headers()['idempotency-key'];
      const stored = await route.fetch();
      savedId = (await stored.json()).assessment_id;
      await route.abort('failed');
    }, { times: 1 });
    await review();
    await page.getByText(/The server may have saved this assessment/).waitFor();
    assert(savedId && submissionKey, 'Response interruption did not follow an actual saved request');
    await nav('dashboard');
    await continueCheck.click();
    assert(await page.locator('#sweatPattern').inputValue() === 'excessive' && await page.locator('#imageConsent').isChecked(), 'Retry lost the questionnaire answers or consent');
    const retried = page.waitForResponse(response => response.url() === questionnaire);
    await review();
    const response = await retried;
    const recovered = await response.json();
    await page.locator('#resultModal.show').waitFor();
    assert(recovered.assessment_id === savedId && response.request().headers()['idempotency-key'] === submissionKey, 'Resume created a different submission');
    const records = await page.evaluate(async () => (await requestJSON('/api/analysis-history')).analyses);
    assert(records.length === 1 && records[0].assessment_id === savedId, 'Retry created duplicate saved records');
    assert((await page.locator('#resultWorkflowStatus').textContent()).includes('Saved to your local account'), 'Recovered save state is unclear');
    checks.push('questionnaire return and duplicate-free recovery after a dropped committed response');

    await result.getByRole('button', { name: /Edit your answers/ }).click();
    await page.waitForFunction(() => document.activeElement.id === 'sweatPattern');
    assert(await page.evaluate(() => state.area === 'Sweat' && !state.reviewResultReady) && await page.locator('#sweatPattern').inputValue() === 'excessive', 'Live result did not return to its own editable answers');
    await nav('progress');
    await page.locator('#journeyTabs-checkins').click();
    await nav('dashboard');
    await page.locator('#dashboardRecent').getByRole('button', { name: /View saved results/ }).click();
    assert(await view() === 'results' && await focused('journeyTabs-results'), 'Saved-results link opened the prior tab');
    await nav('dashboard');
    await page.getByRole('button', { name: 'Manage routines', exact: true }).click();
    assert(await view() === 'routines' && await focused('journeyTabs-routines'), 'Routine link did not focus Routines');
    checks.push('live questionnaire editing and exact dashboard destinations');

    await nav('dashboard');
    const detail = base + 'api/assessments/' + savedId;
    await page.route(detail, route => route.fulfill({
      status: 503, contentType: 'application/json', body: '{"error":"Synthetic saved-result interruption"}'
    }), { times: 1 });
    await openLatest.press('Enter');
    await page.locator('#toast.show').filter({ hasText: 'Synthetic saved-result interruption' }).waitFor();
    assert(await openLatest.getAttribute('aria-busy') === null && await result.getAttribute('aria-hidden') === 'true', 'Failed read disabled recovery or opened a result');
    await openLatest.press('Enter');
    await page.locator('#resultModal.show').waitFor();
    assert(await page.evaluate(id => state.assessmentId === id && document.getElementById('workspaceTitle').textContent === 'Today', savedId), 'Latest result did not open directly');
    await result.locator('.modal-close').click();
    assert(await openLatest.evaluate(button => button === document.activeElement), 'Closing the result lost the dashboard opener focus');
    checks.push('direct saved result, read-error retry and keyboard focus restoration');

    let release, captured;
    const gate = new Promise(resolve => { release = resolve; });
    const ready = new Promise(resolve => { captured = resolve; });
    await page.route(detail, async route => {
      const response = await route.fetch();
      captured();
      await gate;
      await route.fulfill({ response });
    }, { times: 1 });
    const opener = await openLatest.elementHandle();
    await openLatest.click();
    await ready;
    assert(await openLatest.getAttribute('aria-busy') === 'true', 'Held read did not display a loading state');
    await nav('home');
    await page.locator('.area-choice [data-area=Hair]').click();
    await addPhoto();
    await nav('dashboard');
    release();
    await page.waitForFunction(button => !button.hasAttribute('aria-busy'), opener);
    assert(await result.getAttribute('aria-hidden') === 'true' && await continueCheck.isVisible(), 'Old result reopened over the current draft');
    checks.push('delayed saved result is ignored after leaving and returning to Today');

    await openLatest.click();
    await page.locator('#resultModal.show').waitFor();
    assert(await result.getByRole('button', { name: /Edit your answers/ }).count() === 0, 'Historical questionnaire offers to edit current input');
    await result.getByRole('button', { name: /View saved results/ }).click();
    assert(await view() === 'results' && await focused('journeyTabs-results'), 'Historical result did not lead to saved results');
    await nav('dashboard');
    await continueCheck.click();
    assert(await page.evaluate(() => state.area === 'Hair' && state.file?.name === 'synthetic-check.png'), 'Viewing a historical result changed the new draft');
    checks.push('historical questionnaire leaves a different current draft intact');

    await nav('dashboard');
    await page.locator('#navLogoutButton').click();
    await page.waitForFunction(() => !state.profile && document.getElementById('authGate').classList.contains('show'));
    await page.locator('#continueGuestButton').click();
    await page.waitForFunction(() => state.isGuest && !document.getElementById('authGate').classList.contains('show'));
    assert(await openLatest.count() === 0 && await continueCheck.isHidden() && await page.locator('#dashboardLowerGrid').isHidden(), 'Saved activity or draft remained visible after sign-out');
    assert(await page.evaluate(() => !state.file && !state.areaSelected && !state.assessmentId), 'Private check state survived the account transition');
    checks.push('account switch clears Today results and draft continuation');
    assert(errors.length === 0, 'Browser errors: ' + errors.join(', '));
    return { checks, errors };
  } catch (error) {
    if (options.artifactRoot) await page.screenshot({ path: options.artifactRoot + 'failure.png' }).catch(() => {});
    const pageState = await page.evaluate(() => ({
      page: document.getElementById('workspaceTitle')?.textContent,
      area: state.area, focus: document.activeElement?.id
    })).catch(() => ({}));
    throw Error(error.message + ' | Completed: ' + checks.join(', ') + ' | ' + JSON.stringify(pageState) + ' | ' + errors.join(', '));
  }
}
