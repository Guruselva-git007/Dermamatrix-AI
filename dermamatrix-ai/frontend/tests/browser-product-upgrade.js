async (page,options={})=>{
  const checks=[],errors=[],root=options.artifactRoot||'../local-artifacts/whole-product-upgrade-2026-11-10/';
  const assert=(value,message)=>{if(!value)throw Error(message);};
  const nav=route=>page.locator('[data-page-nav='+route+']').click();
  const confirm=async(work,accept)=>{const ready=page.waitForEvent('dialog'),pending=work();const dialog=await ready;accept?await dialog.accept():await dialog.dismiss();await pending;};
  page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.context().clearCookies();await page.setViewportSize({width:1440,height:960});
    await page.goto('http://127.0.0.1:8001/');
    await page.locator('[data-auth-tab=register]').click();const form=page.locator('#registerForm');
    for(const [name,value]of Object.entries({full_name:'Synthetic Product Upgrade',email_address:'whole-upgrade-'+Date.now()+'@example.invalid',password:'Synthetic-Upgrade-Only-84!',confirm_password:'Synthetic-Upgrade-Only-84!'}))await form.locator('[name='+name+']').fill(value);
    await form.locator('[name=account_consent]').check();await form.locator('[type=submit]').click();
    await page.waitForFunction(()=>state.profile&&state.progressLoadedFor===state.profile.patient_id&&!document.querySelector('#registerForm [type=submit]').disabled);
    if(await page.locator('#welcomeDialog').evaluate(d=>d.open))await page.locator('#closeWelcome').click();
    const ids=await page.evaluate(async()=>{
      const post=(url,data)=>requestJSON(url,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify(data)});
      const episode=(await post('/api/episodes',{label:'Synthetic palms observation',area:'Sweat',body_area:'Hand'})).episode_id;
      const routines=[];
      for(const name of ['Evening observation','Morning observation'])routines.push((await post('/api/routines',{condition_label:'My own tracking',routine_name:name,start_date:currentDate()})).routine_id);
      const assessments=[];
      for(const pattern of ['usual','excessive'])assessments.push((await post('/api/sweat-assessments',{questionnaire_consent:true,consent_notice_version:processingNoticeVersion('questionnaire_assessment'),pattern,body_location:'Palms',episode_id:episode})).assessment_id);
      await loadProgress({force:true});await ContinuityUI.changed();return{episode,routines,assessments};
    });
    await nav('home');await page.locator('.area-choice [data-area=Sweat]').click();
    await page.locator('#sweatStress').selectOption('3');await page.locator('#sweatHeat').selectOption('2');await page.locator('#sweatMedication').check();await page.locator('#sweatImpact').check();
    await page.locator('#assessmentEpisode').selectOption(ids.episode);await page.locator('#imageConsent').check();await page.locator('#analyzeButton').click();
    const review=page.locator('#assessmentReviewDialog');await review.waitFor();
    for(const label of ['Stress trigger','Heat trigger','Recent medication change','Daily impact','Urgent concern','Linked concern'])assert(await review.locator('dt').filter({hasText:label}).count()===1,'Review omitted '+label);
    await review.getByRole('button',{name:'Change stress trigger',exact:true}).click();
    await page.waitForFunction(()=>document.activeElement.id==='sweatStress');assert(await page.locator('#sweatStress').inputValue()==='3','Change lost input');
    await page.locator('#sweatStress').selectOption('2');await page.locator('#analyzeButton').click();
    const sent=page.waitForRequest(r=>r.url().endsWith('/api/sweat-assessments')&&r.method()==='POST');
    await page.locator('#confirmAssessmentReview').click();const payload=(await sent).postDataJSON();
    assert(payload.stress==='2'&&payload.heat==='2'&&payload.medication_change&&payload.daily_impact&&payload.episode_id===ids.episode,'Reviewed values differ from submitted values');
    await page.locator('#resultModal.show').waitFor();await page.locator('#resultModal .modal-close').click();
    checks.push('complete questionnaire review, precise Change focus and matching committed request');

    await nav('progress');await page.locator('#journeyTabs-routines').click();
    await page.locator('[data-checkin-routine="'+ids.routines[0]+'"]').click();await page.locator('#checkinNote').fill('This belongs only to evening');await page.locator('#checkinTrend').selectOption('worsening');
    await confirm(()=>page.locator('#checkinRoutine').selectOption(ids.routines[1]),false);
    assert(await page.locator('#checkinRoutine').inputValue()===ids.routines[0]&&await page.locator('#checkinNote').inputValue()==='This belongs only to evening','Cancelled selector switch changed the draft');
    await confirm(()=>page.locator('#checkinRoutine').selectOption(ids.routines[1]),true);
    assert(await page.locator('#checkinNote').inputValue()===''&&await page.locator('#checkinTrend').inputValue()==='improving','Accepted selector switch reassociated old input');
    checks.push('cancelled and accepted check-in selector switches protect the original association');
    await page.locator('#checkinNote').fill('Newer morning draft');await page.locator('#journeyTabs-routines').click();
    await confirm(()=>page.locator('[data-checkin-routine="'+ids.routines[0]+'"]').click(),false);
    assert(await page.locator('#checkinNote').inputValue()==='Newer morning draft'&&await page.locator('#checkinRoutine').inputValue()===ids.routines[1],'Cancelled row switch lost the check-in');
    await confirm(()=>page.locator('[data-checkin-routine="'+ids.routines[0]+'"]').click(),true);
    assert(await page.locator('#checkinNote').inputValue()==='','Accepted row switch kept another routine’s note');
    await page.locator('#checkinNote').fill('Synthetic journal note');await page.locator('#checkinEpisode').selectOption(ids.episode);
    await page.locator('#checkinForm [type=submit]').click();await page.locator('#continuityDialog').getByRole('button',{name:'Save check-in',exact:true}).click();
    await page.waitForFunction(()=>!document.getElementById('continuityDialog').open&&state.checkins.length===1);
    checks.push('row-action switching and review save one correctly linked check-in');

    await page.locator('#journeyTabs-routines').click();await page.evaluate(id=>EngagementUI.configureRoutine(id),ids.routines[0]);
    await page.locator('#routineSteps').fill('My first observation\nMy second observation');await page.locator('#routineTimes').fill('09:00, 18:00');
    await page.locator('#quietStart').fill('00:00');await page.locator('#quietEnd').fill('00:00');
    await page.getByRole('button',{name:'3. Review your plan'}).click();
    assert((await page.locator('#routinePlanReview').textContent()).includes('My second observation'),'Plan review omitted steps');
    await page.locator('#scheduleEditor [type=submit]').click();await page.waitForFunction(()=>document.getElementById('scheduleStatus').textContent.includes('saved'));
    await page.locator('#routineJournal summary').first().click();await page.locator('#journalRoutine').selectOption(ids.routines[0]);
    await page.locator('#journalDate').fill(await page.evaluate(()=>currentDate()));await page.locator('#showRoutineDay').click();
    await page.waitForFunction(()=>document.getElementById('routineDayStatus').textContent.includes('Scheduled means'));
    assert((await page.locator('#routineDayStatus').textContent()).includes('Neither proves a missed routine'),'Daily view overstates missing actions');
    await page.waitForFunction(()=>document.getElementById('journalList').textContent.includes('Synthetic journal note'));
    checks.push('guided plan review, saved schedule and selected-date routine journal');

    await page.locator('#journeyTabs-results').click();await page.locator('#concernActivity summary').first().click();await page.locator('#activityConcern').selectOption(ids.episode);
    await page.locator('#activityForm [type=submit]').click();await page.waitForFunction(()=>document.querySelectorAll('#activityList article').length===4);
    await page.locator('#activityKind').selectOption('checkin');await page.locator('#activityForm [type=submit]').click();await page.waitForFunction(()=>document.querySelectorAll('#activityList article').length===1);
    assert((await page.locator('#activityList').textContent()).includes('Synthetic journal note'),'Linked activity lost check-in');
    await page.locator('#activityList').getByRole('button',{name:'View check-in'}).click();await page.locator('#recordReadDialog').waitFor();assert(await page.locator('#recordReadDialog').isVisible()&&await page.locator('#correct-trend').count()===0,'Reading immediately opened correction');
    await page.locator('#recordReadDialog').getByRole('button',{name:'Close',exact:true}).click();
    checks.push('concern/date/type workspace reads effective records before offering correction');
    for(const id of ids.assessments)await page.locator('[data-assessment-id="'+id+'"] .compare-choice input').check();
    await page.locator('#compareAssessments').click();await page.waitForFunction(()=>document.querySelectorAll('#comparisonResult article').length===2);
    assert(await page.locator('#comparisonResult').getByRole('button',{name:'Open original report'}).count()===2,'Comparison lost original reports');
    assert((await page.locator('#comparisonResult').textContent()).includes('do not establish healing'),'Comparison lost evidence limitation');
    await page.screenshot({path:root+'comparison.png'});checks.push('two original same-concern records compare through existing compatibility rules');

    await page.evaluate(()=>ContinuityUI.search(''));await page.waitForFunction(()=>document.querySelectorAll('#unifiedResults article').length===20);
    const originalResult=page.locator('#unifiedResults').getByRole('button',{name:'Open assessment',exact:true}).last();
    await originalResult.evaluate(button=>{
      const dialog=button.closest('dialog');
      button.scrollIntoView({block:'start',behavior:'instant'});
      // Measure the visible position at activation, after pointer actionability scrolling.
      button.addEventListener('click',()=>{dialog.dataset.testOpenScroll=String(dialog.scrollTop);},{capture:true,once:true});
    });
    await originalResult.click();await page.locator('#returnWorkspaceSearch').waitFor();
    const originalScroll=Number(await page.locator('#unifiedSearchDialog').getAttribute('data-test-open-scroll'));
    assert(originalScroll>0,'Search fixture did not open a scrolled result');
    await page.locator('#returnWorkspaceSearch').click();
    const restored=await originalResult.evaluate(async button=>{
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      return {scroll:button.closest('dialog').scrollTop,focused:document.activeElement===button};
    });
    assert(Math.abs(originalScroll-restored.scroll)<=2&&restored.focused,'Search return lost position or focus: '+originalScroll+' -> '+JSON.stringify(restored));
    await page.locator('#unifiedCategory').selectOption('checkin');await page.locator('.search-refinements summary').click();
    await page.locator('#searchArea').selectOption('Sweat');await page.locator('#searchConcern').selectOption(ids.episode);await page.locator('#unifiedSearchForm [type=submit]').click();
    await page.waitForFunction(()=>document.querySelector('#unifiedResults h3'));
    await page.locator('#unifiedResults').getByRole('button',{name:'Open check-in'}).click();await page.locator('#recordReadDialog').waitFor();
    await page.locator('#recordReadDialog').getByRole('button',{name:'Back to search',exact:true}).click();
    assert(await page.locator('#searchArea').inputValue()==='Sweat'&&await page.locator('#searchConcern').inputValue()===ids.episode&&await page.locator('#unifiedResults article').count()===1,'Search return lost scope or position');
    await page.locator('#unifiedSearchDialog').press('Escape');checks.push('filtered search opens read-only details and preserves scope/results on return');
    await page.evaluate(()=>ContinuityUI.search(''));await page.locator('#unifiedCategory').selectOption('guide');await page.getByRole('button',{name:'Clear filters',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#unifiedResults button'));
    await page.locator('#unifiedResults').getByRole('button',{name:'Open guide'}).first().click();await page.locator('#returnGuideSearch').waitFor();await page.locator('#guideBookmark').click();await page.waitForFunction(()=>document.getElementById('guideBookmark').textContent==='Remove bookmark');await page.locator('#returnGuideSearch').click();
    assert(await page.locator('[data-search-guide]:visible').count()===1,'Saved guide badge did not update in existing search');
    await page.locator('#unifiedResults').getByRole('button',{name:'Open guide'}).first().click();await page.locator('#returnGuideSearch').waitFor();await page.locator('#guideBookmark').click();await page.waitForFunction(()=>document.getElementById('guideBookmark').textContent==='Save guide');await page.locator('#returnGuideSearch').click();
    assert(await page.locator('[data-search-guide]:visible').count()===0,'Removed bookmark remained in search');
    assert(await page.locator('#unifiedCategory').inputValue()==='guide'&&await page.locator('#unifiedResults article').count()>0,'Guide return lost its search');await page.locator('#unifiedSearchDialog').press('Escape');
    checks.push('saved results restore actual search scroll/focus and guides retain a search return path');

    await nav('learn');await page.waitForFunction(()=>document.querySelector('#learnList button'));
    await page.locator('#learnList button').first().click();await page.locator('#guideBookmark').click();await page.waitForFunction(()=>document.getElementById('guideBookmark').textContent==='Remove bookmark');
    await page.getByRole('button',{name:'← Back to guides',exact:true}).click();await page.locator('#learnSaved').selectOption('saved');await page.waitForFunction(()=>document.querySelectorAll('#learnList article').length===1);
    await page.locator('#learnList button').click();await page.locator('#guideBookmark').click();await page.waitForFunction(()=>document.getElementById('guideBookmark').textContent==='Save guide');
    await page.getByRole('button',{name:'← Back to guides',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('#learnList article').length===0);
    checks.push('All/Saved guides reuse bookmarks and removal updates the returned library');

    await nav('settings');await page.evaluate(()=>WorkspaceUI.privacy());const rights=page.locator('#rightsRequestForm');
    await rights.locator('[name=note]').fill('Committed original request');
    let release,received;const held=new Promise(resolve=>release=resolve),ready=new Promise(resolve=>received=resolve);
    await page.route('**/api/privacy/requests',async route=>{const response=await route.fetch();received();await held;await route.fulfill({response});},{times:1});
    await rights.locator('[type=submit]').click();await ready;await rights.locator('[name=note]').fill('Newer unsaved request');release();
    await page.waitForFunction(()=>!document.querySelector('#rightsRequestForm [type=submit]').disabled);
    assert(await rights.locator('[name=note]').inputValue()==='Newer unsaved request','Late success cleared newer request');
    checks.push('a genuinely committed delayed privacy request preserves newer input');

    let releaseOld,oldReady,accountReads=0;const oldHeld=new Promise(resolve=>releaseOld=resolve),oldReceived=new Promise(resolve=>oldReady=resolve);
    const ordering=async route=>{const index=++accountReads,response=await route.fetch(),body=await response.json();body.email_verified=index>1;if(index===1){oldReady();await oldHeld;}await route.fulfill({response,json:body});};
    await page.route('**/api/security/account',ordering);
    await page.evaluate(()=>{window.upgradeOlderRefresh=ConsumerUI.refresh();});await oldReceived;
    await page.evaluate(()=>ConsumerUI.refresh());releaseOld();await page.evaluate(()=>window.upgradeOlderRefresh);
    await page.unroute('**/api/security/account',ordering);
    assert(await page.locator('#emailVerificationState').textContent()==='Email verified','Older overlapping security response overrode the newer view');
    checks.push('overlapping account refreshes keep the newest response');

    await page.setViewportSize({width:390,height:844});await page.locator('#mobileTabBar [data-mobile-page=progress]').click();
    assert(await page.locator('#mobileTabBar [aria-current=page]').textContent()==='Journey','Mobile tab did not update');
    await page.locator('#mobileTabBar [data-mobile-page=dashboard]').click();await page.goBack();
    await page.waitForFunction(()=>document.querySelector('.page-active').id==='progress');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile shell overflows');checks.push('reachable mobile navigation follows browser Back without horizontal overflow');
    await page.setViewportSize({width:1440,height:960});
    page.once('dialog',dialog=>dialog.accept());await page.locator('#navLogoutButton').click();
    await page.waitForFunction(()=>!state.profile);
    assert(await page.locator('#activityList article,#journalList article,#comparisonResult article').count()===0,'Account data remained in added views after sign-out');
    assert(!(await page.locator('#journalRoutine,#activityConcern').evaluateAll(nodes=>nodes.map(node=>node.textContent).join(' '))).includes('observation'),'Private picker labels remained after sign-out');
    checks.push('sign-out clears activity, journal, comparison and pending account state');
    return{checks,errors};
  }catch(error){await page.screenshot({path:root+'failure.png'});throw error;}
}
