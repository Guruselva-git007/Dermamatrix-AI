async (page, options = {}) => {
  const checks = [], errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const assert = (value, message) => { if (!value) throw Error(message); };
  const cachePaths = () => page.evaluate(async () => {
    const paths = [];
    for (const name of await caches.keys()) {
      if (!name.startsWith('dermamatrix-offline-')) continue;
      for (const request of await (await caches.open(name)).keys()) paths.push(new URL(request.url).pathname);
    }
    return paths;
  });
  try {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.context().clearCookies();
    await page.goto('http://127.0.0.1:8001/');
    await page.locator('#continueGuestButton').click();
    await page.waitForFunction(() => state.isGuest && !document.querySelector('#authGate').classList.contains('show'));
    if (await page.locator('#welcomeDialog').evaluate(e => e.open)) await page.locator('#closeWelcome').click();
    await page.evaluate(() => navigator.serviceWorker.ready);
    // Load a controlled document after activation before asserting offline behavior.
    await page.reload();
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
    checks.push('real service worker activates in the isolated guest browser');
    await page.evaluate(async () => {
      for (const path of ['/api/products', '/api/model-registry', '/api/auth/me']) await (await fetch(path, { cache: 'no-store' })).arrayBuffer();
    });
    const paths = await cachePaths();
    assert(paths.length === 1 && paths[0] === '/offline.html', 'Service worker cached an app page or API response');
    checks.push('only the static offline explanation is cached after actual API reads');
    await page.context().setOffline(true);
    // A hash-only/same-document navigation would never reach the service worker.
    await page.goto('http://127.0.0.1:8001/?offline-probe=1');
    assert((await page.locator('h1').textContent()).includes('offline'), 'Offline navigation did not explain the missing connection');
    assert((await page.locator('body').textContent()).includes('not cached for offline use'), 'Offline page implies health processing is available');
    const apiBlocked = await page.evaluate(async () => { try { await fetch('/api/account-data/download', { cache: 'no-store' }); return false; } catch { return true; } });
    assert(apiBlocked, 'Offline health endpoint unexpectedly returned cached data');
    if (options.artifactRoot) await page.screenshot({ path: options.artifactRoot + 'offline-mobile.png' });
    checks.push('offline navigation is explanatory and health API access fails rather than returning cached data');
    await page.context().setOffline(false);
    await page.getByRole('link', { name: 'Try again', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('#authGate')?.classList.contains('show'));
    assert(await page.evaluate(() => !state.profile && state.analyses.length === 0), 'Reconnection restored private guest evidence');
    assert(JSON.stringify(await cachePaths()) === JSON.stringify(paths), 'Reconnection changed the offline data boundary');
    checks.push('reconnection restores account entry without retaining guest health evidence');
    assert(!errors.length, errors.join('; '));
    return { checks, errors, cachedPaths: paths };
  } catch (error) {
    const context = await page.evaluate(() => ({ url: location.href, online: navigator.onLine, worker: Boolean(navigator.serviceWorker.controller), guest: typeof state === 'undefined' ? null : state.isGuest, authMessage: document.querySelector('#authMessage')?.textContent }));
    throw Error(error.message + ' | Completed: ' + checks.join(', ') + ' | Context: ' + JSON.stringify(context));
  } finally {
    await page.context().setOffline(false);
  }
}
