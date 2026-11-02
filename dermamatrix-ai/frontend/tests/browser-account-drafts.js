async (page, options = {}) => {
  // Existing isolated synthetic stack only; pages deliberately share cookies.
  const checks = [], errors = [], accounts = [], root = options.artifactRoot || '../local-artifacts/account-drafts-2026-11-02/';
  const stamp = Date.now(), password = 'Synthetic-boundaries-only-84!';
  const emailA = `boundaries-a-${stamp}@example.invalid`, emailB = `boundaries-b-${stamp}@example.invalid`;
  const assert = (value, message) => { if (!value) throw Error(message); };
  let other;
  page.on('pageerror', error => errors.push(error.message));
  async function auth(p, email, register = false) {
    if (await p.locator('#welcomeDialog').evaluate(e => e.open)) await p.locator('#closeWelcome').click();
    await p.evaluate(tab => showAuthGate(tab), register ? 'register' : 'login');
    const form = p.locator(register ? '#registerForm' : '#loginForm');
    if (register) await form.locator('[name=full_name]').fill('Synthetic boundary account');
    await form.locator('[name=email_address]').fill(email); await form.locator('[name=password]').fill(password);
    if (register) { await form.locator('[name=confirm_password]').fill(password); await form.locator('[name=account_consent]').check(); }
    await form.locator('[type=submit]').click();
    await p.waitForFunction(email => state.profile?.email_address === email && !document.querySelector('#authGate').classList.contains('show') && !document.querySelector('#loginForm [type=submit]').disabled && !document.querySelector('#registerForm [type=submit]').disabled, email);
    if (await p.locator('#welcomeDialog').evaluate(e => e.open)) await p.locator('#closeWelcome').click();
    return p.evaluate(() => state.profile.patient_id);
  }
  async function locked(p) { await p.waitForFunction(() => !state.profile && document.querySelector('#authGate').classList.contains('show')); }
  async function routines(p) { return p.evaluate(async () => (await requestJSON('/api/routines')).routines); }
  async function routineForm() {
    await page.locator('[data-page-nav=progress]').click(); await page.evaluate(() => WorkspaceUI.reveal('routines'));
    await page.locator('#conditionLabel').fill('Synthetic observed concern');
    await page.locator('#routineName').fill('Synthetic submitted routine');
    await page.locator('#routineStartDate').fill(new Date().toISOString().slice(0,10));
  }
  async function confirm(action, accept, type = 'confirm') {
    const dialog = page.waitForEvent('dialog');
    // WebKit rejects a cancelled reload immediately, before dismiss() resolves.
    // Attach its handler now so an expected cancellation is never unhandled.
    const work = action().then(() => null, error => error); const d = await dialog;
    assert(d.type() === type, 'Unexpected native dialog type: '+d.type());
    accept ? await d.accept() : await d.dismiss(); const error = await work;
    if (error && !(type === 'beforeunload' && !accept && /navigation cancel(?:led|ed) by beforeunload dialog|ERR_ABORTED/i.test(error.message))) throw error;
  }
  try {
    await page.setViewportSize({width:1440,height:960}); await page.context().clearCookies(); await page.goto('http://127.0.0.1:8001/');
    accounts.push(await auth(page,emailA,true)); await routineForm();
    const oldToken = await page.evaluate(async () => (await ConsumerClient.prepare({})).headers['X-CSRF-Token']);
    other = await page.context().newPage(); other.on('pageerror', error => errors.push(error.message)); await other.goto('http://127.0.0.1:8001/');
    accounts.push(await auth(other,emailB,true)); await locked(page);
    assert(await page.locator('#routineName').inputValue() === '', 'Another tab account change retained the old draft');
    assert((await routines(other)).length === 0, 'The stale draft was stored under the new account');
    checks.push('shared-cookie account change immediately clears the old tab and its unfinished private draft');

    const stale = await page.evaluate(async ({token,stamp}) => {
      const results = [];
      for (const path of ['/api/profile','/api/progress-checkins','/api/history/download','/api/account-data/download','/api/reports/synthetic-unavailable/download']) {
        const response = await fetch(path,{headers:{'X-CSRF-Token':token}});results.push({path,status:response.status,body:await response.json()});
      }
      for (const path of ['/api/routines','/api/progress-checkins','/api/sweat-assessments']) {
        const response = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify({condition_label:'Synthetic stale A',routine_name:'Synthetic wrong owner '+stamp,start_date:currentDate()})});
        results.push({path,status:response.status,body:await response.json()});
      }
      return results;
    }, {token:oldToken,stamp});
    assert(stale.slice(0,5).every(r=>r.status===409&&r.body.code==='WORKSPACE_CHANGED'), 'Stale private reads/exports reached another account: '+JSON.stringify(stale));
    assert(stale.slice(5).every(r=>r.status===403), 'A stale write was accepted');
    assert(stale.every(r=>!JSON.stringify(r.body).includes(emailB))&&(await routines(other)).length===0, 'Stale requests disclosed or stored private data');
    checks.push('server rejects stale-session private reads, exports and writes before side effects');

    await auth(page,emailB); let release,seen;
    const gate = new Promise(r=>release=r), ready = new Promise(r=>seen=r);
    const holdProfile = async route => { const response=await route.fetch();seen();await gate;await route.fulfill({response}); };
    await page.route('**/api/profile',holdProfile);
    const delayed = page.evaluate(() => requestJSON('/api/profile').then(()=>({accepted:true}),error=>({error:error.message})));
    await ready;await auth(other,emailA);await locked(page);release();const result=await delayed;await page.unroute('**/api/profile',holdProfile);
    assert(!result.accepted && /account changed/.test(result.error), 'Old private response was accepted after the tab changed session');
    checks.push('a delayed private response cannot reopen or paint an invalidated workspace');

    // Exercise the fallback used when cross-tab messaging is unavailable.
    await page.addInitScript(() => { window.BroadcastChannel=undefined; });await page.reload();await page.waitForFunction(()=>state.profile);
    await routineForm();
    await page.evaluate(()=>{const original=ConsumerClient.prepare.bind(ConsumerClient);window.boundaryPreparation={original,ready:false};ConsumerClient.prepare=async(options,path)=>{const prepared=await original(options,path);if(path==='/api/routines'&&options.method==='POST'){window.boundaryPreparation.ready=true;await new Promise(resolve=>window.boundaryPreparation.release=resolve);}return prepared;};});
    const pendingWrite=page.evaluate(stamp=>requestJSON('/api/routines',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({condition_label:'Synthetic held A',routine_name:'Synthetic raced draft '+stamp,start_date:currentDate()})}).then(()=>({accepted:true}),error=>({error:error.message})),stamp);
    await page.waitForFunction(()=>window.boundaryPreparation.ready);await auth(other,emailB);
    await page.evaluate(()=>{const held=window.boundaryPreparation;ConsumerClient.prepare=held.original;held.release();delete window.boundaryPreparation;});const blocked=await pendingWrite;await locked(page);
    assert(!blocked.accepted && !(await routines(other)).some(r=>r.routine_name==='Synthetic raced draft '+stamp),'An account change during preparation stored a stale draft');
    checks.push('an account change during token preparation cannot commit a stale draft without BroadcastChannel');

    await auth(page,emailA);await routineForm();await auth(other,emailB);await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await locked(page);
    assert(await page.locator('#routineName').inputValue()==='', 'Foreground verification did not clear the old private form');
    checks.push('foreground verification detects cookie changes when cross-tab messaging is unavailable');

    await auth(page,emailB);
    const revoked=await other.evaluate(async password=>{
      const token=(await (await fetch('/api/security/csrf')).json()).csrf_token;
      const account=await (await fetch('/api/security/account',{headers:{'X-CSRF-Token':token}})).json();
      const response=await fetch('/api/security/sessions/revoke',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify({current_password:password,session_id:account.sessions.find(s=>s.current).session_id})});return response.status;
    },password);
    assert(revoked===200,'Synthetic session revocation failed');await page.evaluate(()=>window.dispatchEvent(new Event('pageshow')));await locked(page);
    checks.push('resume verification detects actual server-side session revocation');

    await auth(page,emailA);await routineForm();await page.route('**/api/auth/me',route=>route.abort());await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
    await page.waitForFunction(()=>document.querySelector('#authGate').classList.contains('show')&&document.querySelector('.app-shell').inert&&document.querySelector('#retrySessionCheck').hidden===false);
    assert(await page.locator('#routineName').inputValue()==='Synthetic submitted routine','Temporary verification failure destroyed the draft');
    assert(await page.locator('#toast').evaluate(e=>e.hidden||!e.classList.contains('show')),'An obsolete success toast contradicts the session lock');
    for(const theme of ['light','dark'])for(const width of [320,390,768,1280,1440]){
      await page.setViewportSize({width,height:960});await page.evaluate(theme=>applyTheme(theme),theme);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Session recovery prompt overflows');
      await page.screenshot({path:root+`draft-recovery-${theme}-${width}.png`,animations:'disabled'});
    }
    await page.setViewportSize({width:1440,height:960});await page.unroute('**/api/auth/me');await page.locator('#retrySessionCheck').click();
    await page.waitForFunction(()=>!document.querySelector('#authGate').classList.contains('show')&&!document.querySelector('.app-shell').inert);
    assert(await page.locator('#routineName').inputValue()==='Synthetic submitted routine','Verified retry lost the unfinished form');
    checks.push('unverifiable identity hides private views and preserves memory-only input until a verified retry');
    await page.route('**/api/auth/me',route=>route.abort());await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await page.waitForFunction(()=>!document.querySelector('#retrySessionCheck').hidden);await page.unroute('**/api/auth/me');
    await page.locator('#continueGuestButton').click();await page.waitForFunction(()=>state.isGuest&&!document.querySelector('#authGate').classList.contains('show'));
    assert(await page.evaluate(async()=>(await fetch('/api/auth/me')).status===401&&(await fetch('/api/knowledge/conditions/acne')).ok),'Guest access retained an authenticated cookie or lost public guide access');
    assert(await page.locator('#routineName').inputValue()==='','Explicit guest access retained the suspended account draft');
    checks.push('explicit guest recovery discards suspended private input and preserves anonymous guide access');

    await auth(page,emailA);await routineForm();let releaseSave,saveSeen;const saveGate=new Promise(r=>releaseSave=r),saveReady=new Promise(r=>saveSeen=r);
    const holdSave=async route=>{const response=await route.fetch();saveSeen();await saveGate;await route.fulfill({response});};
    await page.route('**/api/routines',holdSave);await page.locator('#routineForm [type=submit]').click();await saveReady;
    await page.locator('#routineName').fill('Synthetic newer unsaved routine');releaseSave();await page.waitForFunction(()=>!document.querySelector('#routineForm [type=submit]').disabled);await page.unroute('**/api/routines',holdSave);
    const editing=await page.locator('#editingRoutineId').inputValue();
    assert(editing && await page.locator('#routineName').inputValue()==='Synthetic newer unsaved routine','A late save erased newer routine edits');
    await page.locator('#routineForm [type=submit]').click();await page.waitForFunction(()=>!document.querySelector('#routineForm [type=submit]').disabled&&document.querySelector('#routineName').value==='');
    const saved=await routines(page);assert(saved.length===1&&saved[0].routine_id===editing&&saved[0].routine_name==='Synthetic newer unsaved routine','Saving newer edits duplicated or lost the routine');
    checks.push('late routine saves preserve newer edits and their next save updates the same record');

    await page.locator('#journeyTabs-results').click();await page.locator('#historyExport summary').click();await page.evaluate(()=>loadProgress({force:true}));
    assert(await page.locator('#downloadHistoryButton').isVisible()&&await page.locator('#downloadHistoryButton').evaluate(e=>e.parentElement.id==='historyExport'),'Refreshing Journey hid the history export in the legacy register');
    const downloadReady=page.waitForEvent('download');await page.locator('#downloadHistoryButton').click();const historyDownload=await downloadReady;
    assert((await historyDownload.failure())===null&&historyDownload.suggestedFilename().endsWith('.pdf'),'Visible history export did not produce a completed PDF');
    await historyDownload.saveAs(root+'history-from-visible-control.pdf');
    checks.push('the visible history action survives refresh and completes a PDF download');

    await page.bringToFront();await page.evaluate(()=>openProfile());await page.locator('#profileForm [name=full_name]').fill('Synthetic unsaved profile');
    await confirm(()=>page.keyboard.press('Escape'),false);assert(await page.locator('#profileModal').evaluate(e=>e.classList.contains('show'))&&await page.locator('#profileForm [name=full_name]').inputValue()==='Synthetic unsaved profile','Cancelling discard lost profile input');
    for(const theme of ['light','dark'])for(const width of [320,390,768,1280,1440]){
      await page.setViewportSize({width,height:960});await page.evaluate(theme=>applyTheme(theme),theme);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Protected profile form overflows');
      await page.screenshot({path:root+`draft-profile-${theme}-${width}.png`,animations:'disabled'});
    }
    await page.setViewportSize({width:1440,height:960});await confirm(()=>page.keyboard.press('Escape'),true);
    checks.push('profile discard cancellation retains input and explicit discard works across both themes and five widths');

    await page.locator('[data-page-nav=home]').click();await page.locator('.area-choice [data-area=Skin]').click();await page.evaluate(()=>document.querySelector('#screenDetails').open=true);
    await page.locator('#concernNote').fill('Synthetic unfinished assessment');
    await page.locator('[data-page-nav=learn]').click();await page.locator('[data-page-nav=home]').click();
    assert(await page.locator('#concernNote').inputValue()==='Synthetic unfinished assessment','Ordinary navigation discarded assessment input');
    // A cancelled reload has no load event. Trigger the real browser reload
    // without asking Playwright to wait for a navigation that must not happen.
    await confirm(()=>page.evaluate(()=>location.reload()),false,'beforeunload');assert(await page.locator('#concernNote').inputValue()==='Synthetic unfinished assessment','Cancelled reload lost input');
    await page.locator('#concernNote').fill('');
    let cleanWarning=false;const unexpected=async d=>{cleanWarning=true;await d.accept();};page.on('dialog',unexpected);await page.reload();page.off('dialog',unexpected);
    assert(!cleanWarning,'Reverted clean form still blocks navigation');
    checks.push('ordinary navigation keeps assessment input and leave warnings clear after a true revert');

    await page.waitForFunction(()=>state.profile);await page.locator('[data-page-nav=progress]').click();await page.evaluate(()=>WorkspaceUI.reveal('checkins'));
    await page.evaluate(async id=>{await requestJSON('/api/progress-checkins',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({routine_id:id,checkin_date:currentDate(),reported_trend:'unchanged',discomfort:0,change:0,note:'Synthetic original check-in'})});await loadProgress({force:true});await ContinuityUI.changed();},editing);
    await page.locator('#checkinCorrections button').first().click();await page.locator('#continuityDialog textarea').fill('Synthetic unsaved correction');
    await confirm(()=>page.locator('#continuityDialog').getByRole('button',{name:'Back',exact:true}).click(),false);
    assert(await page.locator('#continuityDialog textarea').inputValue()==='Synthetic unsaved correction','Cancelled correction discard lost the draft');
    await confirm(()=>page.locator('#continuityDialog').getByRole('button',{name:'Back',exact:true}).click(),true);
    await page.locator('#checkinNote').fill('Synthetic private unfinished note');await page.locator('#navLogoutButton').click();await locked(page);
    assert(await page.locator('#checkinNote').inputValue()===''&&await page.evaluate(()=>!document.querySelector('#continuityDialog').textContent.includes('Synthetic unsaved correction')),'Sign-out retained private form/dialog contents');
    checks.push('correction discard respects cancellation while intentional sign-out clears every private draft');
    assert(!errors.length,errors.join('; '));return{checks,errors,accounts};
  } catch(error){throw Error(error.message+' | Completed: '+checks.join(', ')+' | Browser errors: '+errors.join('; '));}
  finally{if(other)await other.close();}
}
