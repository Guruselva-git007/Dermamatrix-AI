/* Consumer presentation controller. No API, scoring, health storage or new claims. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let installed = false, journeyView = 'results', profileView = 'preferences';
  const paths = {
    mark:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h7v7h-7z"/>',
    dashboard:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
    home:'<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M9 5V3h6v2M8 11h8m-8 5h5"/>',
    progress:'<path d="M5 4v16h16M8 15l4-4 4 2 5-7"/>',
    learn:'<path d="M12 5c-3-2-7-2-10-1v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1v15"/>',
    products:'<path d="M5 8h14l1 13H4L5 8Zm3 0V6a4 4 0 0 1 8 0v2"/>',
    support:'<path d="M5 21V5h14v16M3 21h18M9 21v-5h6v5M9 8h6m-3-3v6"/>',
    settings:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    logout:'<path d="M9 4H4v16h5m5-13 5 5-5 5m-6-5h11"/>',
    menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
    skin:'<path d="M5 18c-3-5 0-13 7-14 6 1 8 7 6 12-2 5-8 6-11 3M9 10h.01M14 14h.01M9 16h.01"/>',
    hair:'<path d="M5 20C3 12 7 3 12 3c6 0 8 9 7 17M8 20c-1-7 0-11 4-14m0 14c2-5 3-8 2-12"/>',
    nails:'<path d="M7 21V9a5 5 0 0 1 10 0v12M8 6h8v8H8z"/>',
    sweat:'<path d="M12 3C9 7 5 11 5 15a7 7 0 0 0 14 0c0-4-4-8-7-12Zm-3 12c0 2 1 3 3 3"/>',
    moon:'<path d="M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10Z"/>',
    sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>'
  };
  const icon = name => `<svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${paths[name] || paths.home}</svg>`;
  const signed = () => Boolean(state.profile?.patient_id);
  const move = (node, parent) => { if(node && parent && node.parentNode !== parent)parent.append(node); };
  function panel(id) { const el=document.createElement('section');el.id=id;el.className='workspace-panel';el.setAttribute('role','tabpanel');return el; }

  function tabs(id, entries, select) {
    const nav=document.createElement('div');nav.id=id;nav.className='workspace-tabs';nav.setAttribute('role','tablist');
    nav.setAttribute('aria-label',id==='journeyTabs'?'Journey views':'Profile sections');
    for(const [value,label,target] of entries){
      const button=document.createElement('button');button.type='button';button.id=id+'-'+value;button.textContent=label;
      button.dataset.view=value;button.setAttribute('role','tab');button.setAttribute('aria-controls',target);
      $(target)?.setAttribute('aria-labelledby',button.id);button.onclick=()=>select(value);
      button.onkeydown=event=>{
        const keys=['ArrowLeft','ArrowRight','Home','End'];if(!keys.includes(event.key))return;
        event.preventDefault();const buttons=[...nav.querySelectorAll('button')].filter(item=>!item.hidden),index=buttons.indexOf(button);
        const next=event.key==='Home'?0:event.key==='End'?buttons.length-1:(index+(event.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length;
        buttons[next].click();buttons[next].focus();
      };nav.append(button);
    }return nav;
  }
  function selectTabs(id, view) {
    for(const button of $(id)?.querySelectorAll('button')||[]){const selected=button.dataset.view===view;button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;}
  }
  function journey(value=journeyView) {
    journeyView=value;selectTabs('journeyTabs',value);
    for(const name of ['results','routines','checkins'])if($('journey-'+name))$('journey-'+name).hidden=!signed()||name!==value;
  }
  function profile(value=profileView) {
    if(!signed())value='preferences';
    if(value==='security'&&!window.ConsumerClient?.enabled)value='preferences';
    profileView=value;selectTabs('profileTabs',value);
    for(const name of ['preferences','security','privacy'])if($('profile-'+name))$('profile-'+name).hidden=name!==value;
    if($('profileTabs'))$('profileTabs').hidden=!signed();
    if($('profileTabs-security'))$('profileTabs-security').hidden=!window.ConsumerClient?.enabled;
    if($('profileGuest'))$('profileGuest').hidden=signed();
  }
  function assessment() {
    if(!installed)return;
    const chosen=state.areaSelected;
    document.querySelector('#home h1').textContent='Start a check';
    document.querySelector('#home p:last-child').textContent='Choose a concern, add your input, then review the result.';
    $('screen').classList.toggle('needs-area',!chosen);
    $('checkStartHint').hidden=Boolean(chosen);
    if(!chosen){
      $('screenTitle').textContent='Choose a concern';$('screenTitle').nextElementSibling.textContent='We will show the right input for the area you choose.';
      $('assessmentStatus').textContent='Choose an area';
      document.querySelector('#home h1').textContent='Start a check';document.querySelector('#home p:last-child').textContent='Choose a concern, add your input, then review the result.';
      document.querySelectorAll('.area-choice button').forEach(button=>{button.classList.remove('selected');button.setAttribute('aria-pressed','false');});
    }
    if($('teachingTools'))$('teachingTools').hidden=!chosen||state.area==='Sweat';
  }
  function theme() {const span=document.querySelector('#themeToggle > span');if(span)span.innerHTML=icon(document.body.dataset.theme==='dark'?'sun':'moon');}
  function update() {
    if(!installed)return;
    move($('reportRegister'),$('journey-results'));
    if($('reportRegister'))$('reportRegister').hidden=!signed()||Boolean(window.ConsumerClient?.enabled);
    $('journeyTabs').hidden=!signed();
    $('historyExport').hidden=!signed();
    const snapshot=document.querySelector('.health-snapshot');
    if(snapshot)snapshot.hidden=!(state.analyses?.length||state.routines?.length||state.checkins?.length);
    const careNote=document.querySelector('.dashboard-care-note');if(careNote)careNote.hidden=snapshot?.hidden;
    const routineAction=$('todayJourney');
    if(routineAction){routineAction.textContent=signed()?'Manage routines':'Create an account';routineAction.onclick=()=>{if(signed()){showPage('progress');journey('routines');}else showAuthGate('register');};}
    journey();profile();assessment();
    const empty=$('journeyEmptyState');
    if(empty&&!empty.querySelector('[data-create-account]')){
      empty.querySelector('p:not(.eyebrow)').textContent='Sign in to keep your results, track a routine and prepare a clinician discussion. Guest checks stay in this tab.';
      const actions=document.createElement('div');actions.className='consumer-actions';
      const start=empty.querySelector('button');start.textContent='Start a check';actions.append(start);
      const create=document.createElement('button');create.type='button';create.className='button quiet';create.dataset.createAccount='';create.textContent='Create an account';create.onclick=()=>showAuthGate('register');actions.append(create);empty.querySelector('div').append(actions);
    }
    if($('historyExportNote'))$('historyExportNote').hidden=!signed();
  }
  function organiseJourney(){
    const container=$('progress');
    for(const name of ['results','routines','checkins'])container.append(panel('journey-'+name));
    move(document.querySelector('.progress-layout'),$('journey-routines'));move($('scheduleWorkspace'),$('journey-routines'));
    const editor=document.querySelector('.routine-form-card'),disclosure=document.createElement('details');disclosure.id='routineEditorDisclosure';disclosure.className='routine-editor-disclosure';
    const summary=document.createElement('summary');summary.textContent='Add a routine';disclosure.append(summary);editor.before(disclosure);disclosure.append(editor);
    move(document.querySelector('.journey-status-section'),$('journey-checkins'));move(document.querySelector('.checkin-card'),$('journey-checkins'));move(document.querySelector('.history-card'),$('journey-checkins'));
    move($('completeJourney'),$('journey-results'));
    const exports=document.createElement('details');exports.id='historyExport';exports.className='history-export';exports.innerHTML='<summary>Prepare a clinician-visit summary</summary>';
    move($('historyExportNote'),exports);move($('downloadHistoryButton'),exports);$('journey-results').append(exports);
    const navigation=tabs('journeyTabs',[['results','Results','journey-results'],['routines','Routines','journey-routines'],['checkins','Check-ins','journey-checkins']],journey);
    document.querySelector('.progress-heading').after(navigation);
    const filters=$('journeySearchForm');if(filters){
      const details=document.createElement('details');details.className='advanced-filters';details.innerHTML='<summary>More filters</summary><div class="advanced-filter-fields"></div>';
      for(const id of ['journeyEpisode','journeyBodyArea'])move($(id).closest('label'),details.querySelector('div'));
      filters.append(details);
    }
  }
  function organiseProfile(){
    const container=$('settings'),preferences=panel('profile-preferences');preferences.classList.add('profile-preferences');
    const groups=document.querySelector('.settings-groups');groups.before(preferences);
    for(const id of ['appearanceSettings','notificationSettings'])move($(id).closest('.settings-group'),preferences);
    const account=$('consumerAccount');
    if(account){
      const security=panel('profile-security'),privacy=panel('profile-privacy');
      for(const id of ['consumerEmailTitle','sessionTitle'])move($(id).closest('.consumer-panel'),security);
      for(const id of ['privacyTitle','rightsTitle'])move($(id).closest('.consumer-panel'),privacy);
      move($('accountSettings').closest('.settings-group'),privacy);
      account.append(security,privacy);
    }
    if(!groups.children.length)groups.remove();
    const guest=document.createElement('section');guest.id='profileGuest';guest.className='profile-guest';guest.hidden=true;
    guest.innerHTML='<h2>Your account, your control</h2><p>Sign in to manage account access, security and saved information. Guest checks do not create an account record.</p><button class="button primary" type="button">Sign in or create an account</button>';
    guest.querySelector('button').onclick=()=>showAuthGate('login');container.append(guest);
    const navigation=tabs('profileTabs',[['preferences','Preferences','profile-preferences'],['security','Security','profile-security'],['privacy','Privacy & data','profile-privacy']],profile);
    document.querySelector('.settings-heading').after(navigation);
    const notes=$('navProfileButton');notes.className='button quiet';notes.textContent='Health notes';document.querySelector('.settings-heading').prepend(notes);
  }
  function install(){
    if(installed)return;
    for(const node of document.querySelectorAll('[data-ui-icon]'))node.innerHTML=icon(node.dataset.uiIcon);
    for(const node of document.querySelectorAll('[data-page-nav]')){
      const span=node.querySelector('span');if(span)span.innerHTML=icon(node.dataset.pageNav);
    }
    document.querySelector('.brand-mark').innerHTML=icon('mark');document.querySelector('.auth-brand > span').innerHTML=icon('mark');
    document.querySelector('.menu-button').innerHTML=icon('menu');
    const signout=$('navLogoutButton');signout.querySelector('span').innerHTML=icon('logout');
    const today=$('consumerToday'),heading=document.createElement('div');heading.className='section-heading';heading.append(today.querySelector('h2'),$('openWelcome'));today.prepend(heading);
    const groups=document.querySelectorAll('.nav-group');groups[0].textContent='Your workspace';groups[1].textContent='Care resources';if(groups[2])groups[2].remove();
    const profileLink=document.querySelector('[data-page-nav=settings]');document.querySelector('[data-page-nav=learn]').after(profileLink);
    for(const node of document.querySelectorAll('.area-choice button'))node.querySelector('span').innerHTML=icon(({Skin:'skin',Hair:'hair',Nails:'nails',Sweat:'sweat'})[node.dataset.area]);
    const preparation=document.querySelector('.capture-help');if(preparation)$('moduleStatus').after(preparation);
    const hint=document.createElement('p');hint.id='checkStartHint';hint.textContent='Photo checks for skin, hair and nails. A questionnaire for sweating. You can review everything before submitting.';document.querySelector('.area-choice').after(hint);
    const teaching=document.querySelector('.presentation-case-option');if(teaching){const details=document.createElement('details');details.id='teachingTools';details.className='teaching-tools';details.innerHTML='<summary>Teaching tools</summary>';teaching.before(details);details.append(teaching);}
    organiseJourney();organiseProfile();installed=true;update();theme();
  }
  window.WorkspaceUI={
    update,assessment,theme,
    page(page){if(!installed)return;if(page==='progress')journey();if(page==='settings')profile();},
    reveal(view){if(!installed)return;journey(view);if(view==='routines')$('routineEditorDisclosure').open=true;},
    async routineSaved(id){
      if(!installed||!window.ConsumerClient?.enabled||!signed())return;
      const owner=state.profile?.patient_id;
      journey('routines');$('routineEditorDisclosure').open=false;
      await window.EngagementUI?.configureRoutine(id);
      if(owner===state.profile?.patient_id&&document.querySelector('.page-active')?.id==='progress'&&journeyView==='routines'){$('routineSteps').focus();$('scheduleWorkspace').scrollIntoView({block:'start',behavior:'auto'});}
    },
    privacy(){if(installed){if(document.querySelector('.page-active')?.id!=='settings')showPage('settings');profile('privacy');}},
    clear(){journeyView='results';profileView='preferences';if(installed){$('routineEditorDisclosure').open=false;journey();profile();}}
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
