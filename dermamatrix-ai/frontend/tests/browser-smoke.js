async page => {
  // Run only against the isolated local test stack. Never point this at an account service.
  await page.setViewportSize({width:1440,height:960});await page.context().clearCookies();
  const checks=[],errors=[];page.on('pageerror',error=>errors.push(error.message));
  const assert=(value,message)=>{if(!value)throw Error(message);};
  const nav=route=>page.locator(`[data-page-nav="${route}"]`).click();
  const email='workspace-'+Date.now()+'@example.invalid';
  const password='Synthetic-workspace-only-84!';
  try {
  await page.goto('http://127.0.0.1:8001/');
  await page.locator('#continueGuestButton').click();
  await page.waitForFunction(()=>state.isGuest&&!document.querySelector('#authGate').classList.contains('show'));
  if(await page.locator('#welcomeDialog').evaluate(e=>e.open))await page.locator('#closeWelcome').click();
  await page.waitForSelector('#journeyTabs',{state:'attached'});
  assert(await page.locator('.dashboard-actions button').count()===4,'Concern shortcuts missing');
  assert(await page.locator('.dashboard-heading .primary').count()===1,'Competing home actions');checks.push('focused home');
  await nav('home');
  assert(!await page.locator('#imageWorkflow').isVisible(),'Photo fields appear before concern selection');
  assert(!await page.locator('#sweatWorkflow').isVisible(),'Questionnaire appears before concern selection');
  await page.locator('[data-area="Skin"]').click();assert(await page.locator('#imageWorkflow').isVisible(),'Skin route missing');
  await page.locator('[data-area="Sweat"]').click();assert(await page.locator('#sweatWorkflow').isVisible(),'Questionnaire missing');
  assert(!await page.locator('#imageWorkflow').isVisible(),'Image fields leak into questionnaire');checks.push('progressive concern pathways');
  await page.locator('#imageConsent').check();await page.locator('#analyzeButton').click();
  await page.locator('#assessmentReviewDialog').waitFor({state:'visible'});
  await page.locator('#backToAssessment').click();assert(await page.locator('#sweatWorkflow').isVisible(),'Review back lost input');
  await page.locator('#analyzeButton').click();await page.locator('#confirmAssessmentReview').click();
  await page.locator('#resultModal.show').waitFor();
  assert(!await page.locator('#resultModal .result-tabs').isVisible(),'Duplicate legacy result panels are visible');
  for(const width of [390,1440]){
    await page.setViewportSize({width,height:960});
    await page.waitForFunction(()=>{const r=document.querySelector('#resultModal .modal-card').getBoundingClientRect();return r.left>=11&&r.right<=innerWidth-11&&Math.abs(r.left-(innerWidth-r.right))<=1;});
  }
  assert(await page.evaluate(()=>state.resultPersistence)!=='mysql','Guest result was saved');checks.push('review back and guest result');
  await page.locator('#resultModal .modal-close').click();
  await page.locator('#workspaceSearch').fill('Acne');await page.locator('#workspaceSearch').press('Enter');
  await page.waitForSelector('.learn-row');assert(await page.locator('#learnSearch').inputValue()==='Acne','Header search did not find health guides');checks.push('health guide search');
  await nav('progress');assert(await page.locator('#journeyEmptyState').isVisible(),'Guest guidance missing');
  assert(!await page.locator('#journeyTabs').isVisible(),'Account tabs shown to guest');checks.push('guest Journey');
  await page.locator('[data-create-account]').click();
  const form=page.locator('#registerForm');
  await form.locator('[name="full_name"]').fill('Synthetic Workspace');
  await form.locator('[name="email_address"]').fill(email);
  await form.locator('[name="password"]').fill(password);await form.locator('[name="confirm_password"]').fill(password);
  await form.locator('[name="account_consent"]').check();await form.locator('[type="submit"]').click();
  await page.waitForFunction(()=>Boolean(state.profile?.patient_id)&&!document.querySelector('#authGate').classList.contains('show')&&!document.querySelector('#registerForm [type=submit]').disabled);
  await nav('progress');assert(await page.evaluate(()=>state.analyses.length)===0,'Guest evidence transferred');checks.push('explicit account boundary');
  await page.locator('#journeyTabs-results').focus();await page.keyboard.press('ArrowRight');
  await page.locator('#journey-routines').waitFor({state:'visible'});
  assert(await page.locator('#journey-routines').isVisible(),'Keyboard tab did not show routines');
  assert(await page.locator('#journeyTabs-routines').getAttribute('aria-selected')==='true','Tab state missing');checks.push('keyboard accessible views');
  await page.locator('#routineEditorDisclosure > summary').click();
  await page.locator('#conditionLabel').fill('Synthetic skin concern');await page.locator('#routineName').fill('Synthetic daily routine');
  await page.locator('#routineForm [type="submit"]').click();
  await page.waitForFunction(()=>state.routines.length===1);
  const routine=await page.evaluate(()=>state.routines[0].routine_id);
  await page.waitForFunction(id=>document.querySelector('#scheduleRoutine').value===id,routine);
  assert(!await page.locator('#routineEditorDisclosure').evaluate(el=>el.open),'Routine creation did not hand off to its steps');
  await page.waitForFunction(()=>document.querySelector('#scheduleStatus').textContent.includes('Add your own steps'));
  await page.locator('#routineSteps').fill('Synthetic user-selected daily step');
  await page.locator('#routineTimes').fill('09:00');await page.locator('#routineTimezone').fill('UTC');
  await page.locator('#scheduleEditor [type="submit"]').click();
  await page.waitForFunction(()=>document.querySelector('#scheduleStatus').textContent.includes('Schedule saved'));
  checks.push('routine and schedule');
  await page.locator('[data-checkin-routine]').click();
  assert(await page.locator('#journey-checkins').isVisible(),'Check-in shortcut opened hidden form');
  assert(await page.locator('#checkinRoutine').inputValue()===routine,'Routine handoff missing');
  await page.locator('#checkinTrend').selectOption('unchanged');await page.locator('#checkinNote').fill('Synthetic browser check-in');
  await page.locator('#checkinForm [type="submit"]').click();
  await page.waitForFunction(()=>state.checkins.length===1);checks.push('check-in handoff and save');
  await nav('home');await page.locator('[data-area="Sweat"]').click();await page.locator('#imageConsent').check();
  await page.locator('#analyzeButton').click();await page.locator('#confirmAssessmentReview').click();await page.locator('#resultModal.show').waitFor();
  await page.locator('#resultModal .modal-close').click();await nav('progress');await page.locator('#journeyTabs-results').click();
  await page.waitForFunction(()=>document.querySelectorAll('#journeySearchResults article').length===1);
  assert(!await page.locator('#reportRegister').isVisible(),'Duplicate result lists displayed');checks.push('saved result in one searchable list');
  await nav('settings');await page.locator('#profileTabs-security').click();
  await page.waitForFunction(()=>document.querySelector('#consumerDeliveryState').textContent.includes('not configured'));
  assert(await page.locator('#changePasswordForm').isVisible()===false,'Collapsed security form unexpectedly expanded');
  assert(await page.locator('#resendVerification').isDisabled(),'Unconfigured delivery action is active');
  await page.locator('#profileTabs-privacy').click();assert(await page.locator('#rightsRequestForm').isVisible(),'Privacy form hidden');
  await page.locator('#rightsRequestForm [name="note"]').fill('Synthetic unsaved note');checks.push('focused security and privacy');
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:960});
    for(const route of ['dashboard','progress','settings','learn','home','support','products']){
      await page.evaluate(route=>showPage(route),route);
      if(route==='dashboard')assert(!await page.locator('#dashboardInsight').isVisible(),'One result is repeated as a baseline/trend panel');
      if(route==='products')await page.waitForFunction(()=>state.productCatalogLoaded&&!state.productLoading);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Horizontal overflow: '+route+' at '+width);
      const tiny=await page.evaluate(()=>[...document.querySelectorAll('.app-shell *')].filter(e=>e.getClientRects().length&&e.getBoundingClientRect().height>0&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<11).map(e=>e.id||e.className));
      assert(!tiny.length,'Unreadable text: '+route+' '+tiny.join(', '));
    }
  }checks.push('seven screens at four widths');
  const legacy=await page.evaluate(async()=>{
    const descriptor=Object.getOwnPropertyDescriptor(window.ConsumerClient,'enabled');
    try{
      Object.defineProperty(window.ConsumerClient,'enabled',{get:()=>false,configurable:true});
      window.WorkspaceUI.privacy();await window.ConsumerUI.refresh();
      return {exportAvailable:document.querySelector('#accountExportRow').getClientRects().length>0,securityHidden:document.querySelector('#profileTabs-security').hidden};
    }finally{Object.defineProperty(window.ConsumerClient,'enabled',descriptor);await window.ConsumerUI.refresh();window.WorkspaceUI.update();}
  });
  assert(legacy.exportAvailable&&legacy.securityHidden,'Legacy account export fallback missing');checks.push('capability-aware account fallback');
  await page.setViewportSize({width:1440,height:960});await nav('settings');
  await page.locator('#themeToggle').click();assert(await page.locator('body').getAttribute('data-theme')==='dark','Dark theme unavailable');
  await page.locator('#themeToggle').click();checks.push('light and dark themes');
  await page.locator('#navLogoutButton').click();await page.waitForFunction(()=>!state.profile);
  assert(await page.locator('#rightsRequestForm [name="note"]').inputValue()==='','Account note survived sign-out');
  assert(await page.locator('#routineTimes').inputValue()==='','Schedule survived sign-out');
  await page.locator('#continueGuestButton').click();await page.waitForFunction(()=>state.isGuest);
  if(await page.locator('#welcomeDialog').evaluate(e=>e.open))await page.locator('#closeWelcome').click();
  await nav('progress');assert(!await page.locator('#journeyTabs').isVisible(),'Private views survived sign-out');checks.push('complete sign-out clearing');
  assert(errors.length===0,'Uncaught browser exception: '+errors.join('; '));
  return{checks,errors,syntheticAccount:email};
  } catch(error) { throw Error('After '+checks.join(', ')+': '+error.message); }
}
