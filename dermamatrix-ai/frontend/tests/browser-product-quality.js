async (page, options = {}) => {
  // Synthetic local stack only. This does not activate delivery or touch normal accounts.
  const checks = [], errors = [], samples = [];
  const root = options.artifactRoot || '../local-artifacts/product-maturity-2026-10-28/';
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

    await nav('learn');
    await page.locator('#learnSearch').fill('Acne');
    await page.locator('#learnForm [type=submit]').click();
    await page.waitForFunction(() => document.querySelector('#learnStatus').textContent === '1 guide found.');
    const guideButton=page.locator('#learnList button').first();
    await guideButton.click();await page.locator('#learn.is-reading').waitFor();
    assert(!await page.locator('#learnList').isVisible()&&!await page.locator('#learnForm').isVisible(), 'Catalogue competes with reading');
    assert(await page.locator('#guideTitle').evaluate(e=>e===document.activeElement), 'Guide heading did not receive focus');
    assert(await page.locator('.guide-toolbar > button').first().evaluate(e=>e.getBoundingClientRect().width<e.parentElement.getBoundingClientRect().width),'Guide toolbar actions stretch across the reading column');
    await page.locator('#learnDetail').getByRole('button',{name:'Back to guides'}).click();
    assert(await page.locator('#learnSearch').inputValue()==='Acne'&&await guideButton.evaluate(e=>e===document.activeElement), 'Back lost the search or invoking control');
    checks.push('guide reader and Back preserve filtered matches and keyboard focus');

    await page.route('**/api/knowledge/conditions/acne',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Synthetic temporary guide failure'})}));
    await guideButton.click();await page.locator('#learnRetry').waitFor();
    assert((await page.locator('#learnStatus').textContent()).includes('could not be opened'), 'Guide failure has no recovery feedback');
    await page.unroute('**/api/knowledge/conditions/acne');
    await page.locator('#learnRetry').click();await page.locator('#learn.is-reading').waitFor();
    await page.locator('#learnDetail').getByRole('button',{name:'Back to guides'}).click();
    checks.push('interrupted guide opens through the visible retry without losing the search');

    let releaseGuide,guideCaptured;
    const guideGate=new Promise(resolve=>{releaseGuide=resolve;}),guideReady=new Promise(resolve=>{guideCaptured=resolve;});
    await page.route('**/api/knowledge/conditions/acne',async route=>{const response=await route.fetch();guideCaptured();await guideGate;await route.fulfill({response});});
    await guideButton.click();await guideReady;await nav('home');
    const guideResponse=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/knowledge/conditions/acne');releaseGuide();await (await guideResponse).finished();await page.waitForTimeout(50);
    await page.unroute('**/api/knowledge/conditions/acne');
    assert(!await page.locator('#learnDetail').isVisible()&&await page.evaluate(()=>document.activeElement.id!=='guideTitle'), 'Late guide stole focus from the next task');
    checks.push('late guide response cannot reopen the reader after navigation');

    await page.locator('.area-choice [data-area=Skin]').click();
    assert(await page.getByRole('button',{name:'Take photo',exact:true}).isVisible()&&await page.getByRole('button',{name:'Choose photo',exact:true}).isVisible(), 'Capture actions remain hidden in help');
    let assessmentPosts=0;const captureRequest=request=>{if(request.method()==='POST'&&new URL(request.url()).pathname==='/api/assessments')assessmentPosts++;};page.on('request',captureRequest);
    // The CLI pauses a run-code cell on a native file dialog. Record the native
    // input handoff without opening that dialog; real device capture stays external.
    await page.evaluate(()=>{const input=document.querySelector('#imageInput');window.captureIntentProbe={click:input.click,intents:[]};input.click=()=>window.captureIntentProbe.intents.push(input.getAttribute('capture'));});
    try{for(const name of ['Take photo','Choose photo'])await page.getByRole('button',{name,exact:true}).click();}
    finally{await page.evaluate(()=>{document.querySelector('#imageInput').click=window.captureIntentProbe.click;});}
    assert(await page.evaluate(()=>JSON.stringify(window.captureIntentProbe.intents)==='["environment",null]'),'Wrong camera or gallery handoff');
    await page.evaluate(()=>delete window.captureIntentProbe);
    page.removeListener('request',captureRequest);
    assert(assessmentPosts===0&&!await page.locator('#imageConsent').isChecked(),'Opening/cancelling a picker submitted or consented');
    checks.push('visible gallery and camera controls forward the right intent without assessment or consent');

    await nav('progress');await page.locator('#journeyTabs-routines').click();
    if(!await page.locator('#routineEditorDisclosure').evaluate(e=>e.open))await page.locator('#routineEditorDisclosure summary').click();
    assert(await page.locator('#routineNotes').evaluate(e=>getComputedStyle(e).fontSize==='16px'&&getComputedStyle(e).fontFamily.includes('IBM Plex Sans')),'Routine notes retain the legacy tiny font');
    checks.push('routine notes use readable IBM Plex control typography');

    await nav('products');
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
    await page.locator('.result-contents').getByRole('button',{name:'Meaning & limits',exact:true}).click();
    assert(await page.locator('#resultPlainExplanation h3').evaluate(e=>e===document.activeElement),'Result section jump lost focus');
    await page.locator('#resultModal .modal-card').evaluate(e=>e.scrollTop=0);
    await page.locator('.result-contents').getByRole('button',{name:'Technical details',exact:true}).click();
    assert(await page.locator('#patientTechnicalSlot details').evaluate(e=>e.open),'Result navigation did not open technical evidence');
    assert(await page.locator('#resultModal .modal-close').evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;}),'Close is unavailable after reading a long result');
    await page.locator('.result-back-top').click();
    assert(await page.locator('#patientResultContent > .assessment-state-card h3').evaluate(e=>e===document.activeElement),'Back to overview lost the lead');
    checks.push('result contents, evidence disclosure, persistent Close and return-to-overview work by keyboard focus');
    await page.keyboard.press('Escape');
    assert(!await page.locator('#resultModal').evaluate(e => e.classList.contains('show')), 'Result keyboard dismissal failed');
    checks.push('result keyboard dismissal and existing focus lifecycle');

    await page.setViewportSize({width:1440,height:960});await nav('progress');await page.locator('#journeyTabs-results').click();
    assert(await page.locator('#briefEnd').inputValue()===await page.evaluate(()=>currentDate())&&Boolean(await page.locator('#briefStart').inputValue()),'Account entry cleared the brief date defaults');
    assert(await page.locator('#downloadBrief').isDisabled(),'Brief download is enabled before preview');
    await page.evaluate(()=>document.querySelector('#visitBrief').open=true);
    let releaseBrief,briefCaptured,briefRequests=0;const briefGate=new Promise(resolve=>releaseBrief=resolve),briefReady=new Promise(resolve=>briefCaptured=resolve);
    const briefFixture=(id,notice)=>({brief:{assessments:id?[{assessment_id:id,area:'Sweat',created_at:'2026-10-30T12:00:00Z'}]:[],counts:{assessments:id?1:0,checkins:0,routine_actions:0},photo_notice:notice}});
    await page.route('**/api/visit-brief',async route=>{briefRequests++;if(briefRequests===1){briefCaptured();await briefGate;await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(briefFixture('synthetic-obsolete','Older preview'))});}else await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(briefFixture(null,'Latest preview'))});});
    await page.locator('#briefQuestions').fill('Synthetic previous question');await page.locator('#previewBrief').click();await briefReady;
    await page.locator('#briefQuestions').fill('Synthetic latest question');await page.locator('#previewBrief').click();await page.waitForFunction(()=>document.querySelector('#briefStatus').textContent.includes('Latest preview'));
    const oldBriefResponse=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/visit-brief');releaseBrief();await (await oldBriefResponse).finished();await page.waitForTimeout(40);await page.unroute('**/api/visit-brief');
    assert((await page.locator('#briefStatus').textContent()).includes('Latest preview')&&await page.locator('#briefSelection input').count()===0,'Old clinician preview replaced the latest selection');
    checks.push('default brief dates survive sign-in and out-of-order previews preserve the latest selection');
    await page.locator('#briefQuestions').fill('Synthetic changed question');assert(await page.locator('#downloadBrief').isDisabled()&&await page.locator('#briefSelection input').count()===0,'Edited brief can download an obsolete preview');
    assert((await page.locator('#briefStatus').textContent()).includes('Selection changed'),'Brief editing has no recovery instruction');
    checks.push('brief editing invalidates download until its selected records are previewed again');

    await page.evaluate(async()=>{
      const write=(url,payload)=>requestJSON(url,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify(payload)});
      const routine=await write('/api/routines',{condition_label:'Synthetic lifecycle observation',routine_name:'Synthetic lifecycle routine',start_date:currentDate(),notes:'Synthetic only'});
      for(const note of ['First synthetic lifecycle entry','Second synthetic lifecycle entry'])await write('/api/progress-checkins',{routine_id:routine.routine_id,checkin_date:currentDate(),reported_trend:'unchanged',discomfort:0,change:0,note});
      await loadProgress({force:true});await window.ContinuityUI.changed();
    });
    for(const theme of ['light','dark'])for(const width of [320,390,768,1440]){
      await page.setViewportSize({width,height:960});await page.evaluate(theme=>applyTheme(theme),theme);
      const readability=await page.evaluate(()=>{
        const luminance=color=>color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
        const targets=[...document.querySelectorAll('.section-label h3,.progress-summary strong')];
        const ratios=targets.map(e=>{const surface=e.closest('.checkin-card,.routine-form-card,.routine-list-card,.history-card,.journey-status-section');const foreground=luminance(getComputedStyle(e).color),background=luminance(getComputedStyle(surface).backgroundColor);return(Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05);});
        const fields=[...document.querySelectorAll('#routineForm input:not([type=checkbox]),#checkinForm input:not([type=file]),#checkinForm select')];
        return{minContrast:Math.min(...ratios),readableFields:fields.every(e=>parseFloat(getComputedStyle(e).fontSize)>=16&&getComputedStyle(e).fontFamily.includes('IBM Plex Sans'))&&targets.every(e=>getComputedStyle(e).fontFamily.includes('IBM Plex Sans'))};
      });
      assert(readability.minContrast>=4.5&&readability.readableFields,'Journey heading/field readability failed in '+theme+' at '+width);
    }
    await page.setViewportSize({width:1440,height:960});await page.evaluate(()=>applyTheme('light'));
    checks.push('Journey headings, summary values and routine/check-in fields remain readable in both themes');
    await page.locator('#journeyTabs-checkins').click();const correctedId=await page.evaluate(()=>state.checkins[0].checkin_id);await page.locator('#checkinCorrections button').first().click();
    assert(await page.locator('#continuityDialogTitle').evaluate(e=>e===document.activeElement),'Correction heading did not receive focus');
    let releaseCorrection,correctionCaptured;const correctionGate=new Promise(resolve=>releaseCorrection=resolve),correctionReady=new Promise(resolve=>correctionCaptured=resolve);
    await page.route('**/api/corrections/checkin/*',async route=>{const response=await route.fetch();correctionCaptured();await correctionGate;await route.fulfill({response});});
    await page.locator('#correct-trend').selectOption('improving');await page.locator('#continuityDialog [type=submit]').click();await correctionReady;
    await page.locator('#continuityDialog').getByRole('button',{name:'Back',exact:true}).click();await page.locator('#checkinCorrections button').nth(1).click();
    await page.locator('#continuityDialog textarea').fill('Synthetic new correction draft');
    const oldCorrection=page.waitForResponse(r=>new URL(r.url()).pathname.startsWith('/api/corrections/checkin/'));releaseCorrection();await (await oldCorrection).finished();await page.waitForFunction(id=>state.checkins.find(r=>r.checkin_id===id)?.revision===1,correctedId);await page.unroute('**/api/corrections/checkin/*');
    assert(await page.locator('#continuityDialog').evaluate(e=>e.open)&&await page.locator('#continuityDialog textarea').inputValue()==='Synthetic new correction draft','Old save closed or changed the current correction');
    assert((await page.locator('#checkinCorrections').textContent()).includes('Original: unchanged'),'Completed correction lost its original record');await page.keyboard.press('Escape');
    checks.push('late correction completion preserves a replacement dialog, its draft and immutable history');

    const routineId=await page.evaluate(()=>state.routines.find(r=>r.routine_name==='Synthetic lifecycle routine').routine_id);await page.locator('#checkinRoutine').selectOption(routineId);await page.locator('#checkinNote').fill('Synthetic reviewed submission');
    await page.locator('#checkinForm [type=submit]').click();
    for(const width of [320,390,768,1440]){
      await page.setViewportSize({width,height:960});
      assert(await page.locator('#continuityDialogTitle').evaluate(e=>e.getBoundingClientRect().top>=0),'Review heading is off screen at '+width);
      assert(await page.locator('#continuityDialog').evaluate(e=>e.scrollWidth<=e.clientWidth),'Review overflows at '+width);
      assert(await page.locator('.review-summary dt').count()===7,'Review omits an entered field');
      if([390,1440].includes(width))await page.screenshot({path:root+`quality-checkin-review-${width}.png`});
    }
    await page.setViewportSize({width:1440,height:960});let releaseCheckin,checkinCaptured;const checkinGate=new Promise(resolve=>releaseCheckin=resolve),checkinReady=new Promise(resolve=>checkinCaptured=resolve);
    await page.route('**/api/progress-checkins',async route=>{if(route.request().method()==='POST'){const response=await route.fetch();checkinCaptured();await checkinGate;await route.fulfill({response});}else await route.continue();});
    await page.locator('#continuityDialog [type=submit]').click();await checkinReady;await page.locator('#continuityDialog').getByRole('button',{name:'Back',exact:true}).click();await page.locator('#checkinNote').fill('Synthetic next unsaved draft');
    const oldCheckin=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/progress-checkins'&&r.request().method()==='POST');releaseCheckin();await (await oldCheckin).finished();await page.waitForFunction(()=>state.checkins.some(r=>r.note==='Synthetic reviewed submission'));await page.unroute('**/api/progress-checkins');
    assert(await page.locator('#checkinNote').inputValue()==='Synthetic next unsaved draft','Delayed check-in cleared the next unsaved draft');
    const savedCount=await page.evaluate(async()=>{const data=await requestJSON('/api/progress-checkins');return data.checkins.filter(r=>r.note==='Synthetic reviewed submission').length;});assert(savedCount===1,'Delayed save duplicated or lost the reviewed check-in');
    checks.push('structured responsive check-in review and delayed save preserve the next draft without duplicates');

    // These states previously inherited color/font/focus declarations from older
    // sheets. Assert rendered behavior rather than CSS source spelling.
    async function settledTheme(theme) {
      await page.evaluate(theme => applyTheme(theme), theme);
      await page.evaluate(async () => { await Promise.all(document.getAnimations().filter(a => a.effect.getTiming().iterations !== Infinity).map(a => a.finished.catch(() => {}))); });
    }
    async function readable(selector) {
      return page.locator(selector).evaluateAll(elements => {
        const rgba = value => value.match(/[\d.]+/g).map(Number);
        const luminance = c => c.slice(0,3).map(v => { v /= 255; return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }).reduce((sum,v,i) => sum + v * [.2126,.7152,.0722][i],0);
        function background(e) {
          const result = [0,0,0,0];
          while(e && result[3] < 1) { const c=rgba(getComputedStyle(e).backgroundColor),a=c[3]??1; for(let i=0;i<3;i++) result[i] += c[i]*a*(1-result[3]); result[3] += a*(1-result[3]); e=e.parentElement; }
          return result;
        }
        return elements.filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden').map(e => {
          const style=getComputedStyle(e), fg=luminance(rgba(style.color)), bg=luminance(background(e));
          return {id:e.id,tag:e.tagName,text:e.textContent.trim().slice(0,80),ratio:(Math.max(fg,bg)+.05)/(Math.min(fg,bg)+.05),font:style.fontFamily,size:parseFloat(style.fontSize)};
        });
      });
    }
    await page.setViewportSize({width:1440,height:960});await nav('home');await page.locator('.area-choice [data-area=Skin]').click();
    await page.evaluate(()=>{document.querySelector('#screenDetails').open=true;document.querySelector('.symptom-details').open=true;});
    await page.locator('#concernNote').fill('Synthetic context retained across theme changes');await page.locator('#previousTreatment').fill('Synthetic care context, not medical advice');
    const aliasSamples=[];
    for(const theme of ['light','dark'])for(const width of [320,390,768,1280,1440]){
      await page.setViewportSize({width,height:960});await settledTheme(theme);
      const aliases=await page.evaluate(()=>{
        const style=getComputedStyle(document.body),pairs={'--ink':'--dm-ink','--muted':'--dm-muted','--line':'--dm-line','--teal':'--dm-blue','--teal-deep':'--dm-blue-strong','--paper':'--dm-bg','--mint':'--dm-blue-soft','--shadow':'--dm-shadow'};
        return Object.entries(pairs).map(([alias,target])=>({alias,value:style.getPropertyValue(alias).trim(),expected:style.getPropertyValue(target).trim()}));
      });
      assert(aliases.every(a=>a.value===a.expected),'Legacy theme alias froze a different theme: '+JSON.stringify(aliases));aliasSamples.push({theme,width,aliases});
      const values=await readable('.concern-note,.previous-treatment,.symptom-details > summary,#concernNote,#previousTreatment');
      assert(values.length===5&&values.every(v=>v.ratio>=4.5&&v.font.includes('IBM Plex Sans')&&v.size>=14),'Opened context text is unreadable: '+JSON.stringify(values));
      assert(await page.locator('#concernNote').inputValue()==='Synthetic context retained across theme changes','Theme changes lost entered context');
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Opened assessment context overflows');
      samples.push({state:'opened-context',theme,width,values});
      if([390,1440].includes(width))await page.screenshot({path:root+`quality-open-context-${theme}-${width}.png`,animations:'disabled'});
    }
    samples.push({state:'legacy-theme-aliases',values:aliasSamples});
    checks.push('legacy semantic aliases resolve against the active theme at five widths');
    checks.push('expanded context panels and filled fields preserve readable Plex text, input and reflow in both themes');
    for(const theme of ['light','dark']){
      await page.setViewportSize({width:390,height:844});await settledTheme(theme);
      await page.locator('#concernNote').focus();await page.keyboard.press('Tab');await page.keyboard.press('Shift+Tab');
      await page.waitForFunction(()=>{const e=document.querySelector('#concernNote'),r=e.getBoundingClientRect();return e===document.activeElement&&r.top>=64&&r.bottom<=innerHeight;});
      const focus=await page.locator('#concernNote').evaluate(e=>({visible:e.matches(':focus-visible'),style:getComputedStyle(e).outlineStyle,width:parseFloat(getComputedStyle(e).outlineWidth)}));
      assert(focus.visible&&focus.style!=='none'&&focus.width>=2,'Tracking-note keyboard focus is absent: '+JSON.stringify(focus));
      samples.push({state:'tracking-note-focus',theme,...focus});await page.screenshot({path:root+`quality-context-focus-${theme}.png`});
    }
    checks.push('tracking-note keyboard focus is visible and in view in both themes');
    await questionnaire(false);await page.locator('#patientTechnicalSlot .technical-details').evaluate(e=>e.open=true);
    for(const theme of ['light','dark'])for(const width of [320,390,768,1280,1440]){
      await page.setViewportSize({width,height:960});await settledTheme(theme);
      const values=await readable('#patientTechnicalSlot .evidence-summary strong');
      assert(values.length===3&&values.every(v=>v.ratio>=4.5&&v.font.includes('IBM Plex Sans')),'Technical values are unreadable: '+JSON.stringify(values));
      samples.push({state:'technical-values',theme,width,values});
      const geometry=await page.locator('#resultModal .modal-card').evaluate(card=>{const slot=card.querySelector('#patientTechnicalSlot');return{cardOverflow:card.scrollWidth>card.clientWidth+1,slotOverflow:slot.scrollWidth>slot.clientWidth+1,values:[...slot.querySelectorAll('dd')].map(e=>e.textContent)};});
      assert(!geometry.cardOverflow&&!geometry.slotOverflow&&geometry.values.some(v=>v.includes('NOT_AVAILABLE_NO_VALIDATED_TABULAR_MODEL')),'Expanded technical evidence clips or loses original values: '+JSON.stringify(geometry));

      if([390,1440].includes(width)){await page.locator('#patientTechnicalSlot').scrollIntoViewIfNeeded();await page.screenshot({path:root+`quality-technical-values-${theme}-${width}.png`,animations:'disabled'});}
    }
    await page.setViewportSize({width:320,height:844});
    const largeTechnical=await page.addStyleTag({content:'.patient-technical, .patient-technical p, .patient-technical dt, .patient-technical dd {font-size:30px}'});
    for(const theme of ['light','dark']){
      await settledTheme(theme);
      const large=await page.locator('#resultModal .modal-card').evaluate(card=>({overflow:card.scrollWidth>card.clientWidth+1,size:parseFloat(getComputedStyle(card.querySelector('.patient-technical dd')).fontSize)}));
      assert(!large.overflow&&large.size>=30,'Enlarged technical text is clipped: '+JSON.stringify(large));
      samples.push({state:'technical-text-200',theme,width:320,...large});
      await page.screenshot({path:root+`quality-technical-text-200-${theme}.png`,animations:'disabled'});
    }
    await largeTechnical.evaluate(e=>e.remove());
    await page.locator('#resultModal .modal-close').click();
    checks.push('actual questionnaire technical values remain readable in both themes at five widths');
    checks.push('expanded technical evidence wraps full original values without horizontal overflow at five widths');

    await page.setViewportSize({ width: 1440, height: 960 }); await logout();
    assert(await page.evaluate(() => !state.profile && !document.querySelector('#patientResultContent') && document.querySelector('#authGate').classList.contains('show') && document.querySelector('.app-shell').inert), 'Sign-out did not clear and isolate the private workspace');
    await page.locator('#continueGuestButton').click();
    await page.waitForFunction(() => state.isGuest && !document.querySelector('#authGate').classList.contains('show'));
    assert(await page.evaluate(() => !state.profile && !document.querySelector('#patientResultContent') && !document.querySelector('.app-shell').inert), 'Guest workspace retained private evidence');
    checks.push('final account clearing preserves guest boundary');
    await page.setViewportSize({width:1440,height:960});
    for(const theme of ['light','dark'])for(const width of [320,390,768,1280,1440]){
      await page.setViewportSize({width,height:960});await settledTheme(theme);
      for(const route of ['settings','products']){
        await page.evaluate(route=>showPage(route,{scrollToTop:false}),route);
        const values=await readable(route==='settings'?'#settings h2':'.products-heading p:not(.eyebrow)');
        assert(values.length>0&&values.every(v=>v.ratio>=4.5&&v.font.includes('IBM Plex Sans')&&v.size>=14),'Heading/description lost readable theme styling: '+JSON.stringify(values));
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Profile/product entry overflows');
        samples.push({state:route+'-readability',theme,width,values});
        if([390,1440].includes(width))await page.screenshot({path:root+`quality-${route}-readability-${theme}-${width}.png`,animations:'disabled'});
      }
    }
    checks.push('guest Profile headings and Products descriptions retain readable theme typography at five widths');

    assert(!errors.length, errors.join('; '));
    return { checks, errors, samples };
  } catch (error) {
    throw Error(error.message + ' | Completed: ' + checks.join(', ') + ' | Browser errors: ' + errors.join('; '));
  }
}
