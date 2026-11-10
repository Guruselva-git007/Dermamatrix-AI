/* Consumer activity, comparison and plan views over existing account records. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const action = (text, handler, className = 'button quiet') => {
    const element = node('button', text, className);
    element.type = 'button';
    element.onclick = handler;
    return element;
  };
  let installed = false, generation = 0, comparisonVersion = 0;
  let activityVersion = 0, activityCursor = null, activityScope = '';
  let routineVersion = 0, routineCursor = null, routineScope = '', dayVersion = 0;
  const selected = new Set();
  const signed = () => Boolean(state.profile?.patient_id && window.ConsumerClient?.enabled);
  const date = value => value ? new Date(value).toLocaleString('en-GB', {dateStyle:'medium', timeStyle:'short', timeZone:'UTC'}) + ' UTC' : 'Not recorded';
  const text = (id, value) => { if ($(id)) $(id).textContent = value; };
  const readable = value => {
    if (value === null || value === undefined || value === '') return 'Not recorded';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (Array.isArray(value)) return value.map(readable).join(', ') || 'None recorded';
    if (typeof value === 'object') return Object.entries(value).map(([key,item])=>readableStatus(key)+': '+readable(item)).join('; ') || 'Not recorded';
    return String(value);
  };

  function scopePicker() {
    const select = $('activityConcern'), previous = select.value;
    const signature = [...$('journeyEpisodeId').options].map(option=>option.value).join('|');
    if (select.dataset.options === signature) return;
    select.replaceChildren(new Option('All concerns',''), new Option('Unassigned records','unassigned'));
    for (const option of $('journeyEpisodeId').options) if (option.value) select.add(new Option(option.textContent,option.value));
    select.value = [...select.options].some(option=>option.value===previous) ? previous : '';
    select.dataset.options = signature;
  }

  function scopeParameters(routine) {
    const params = new URLSearchParams();
    params.set(routine ? 'routine_id' : 'episode_id', $(routine ? 'journalRoutine' : 'activityConcern').value);
    for (const [key, suffix] of [['start','Start'],['end','End'],['kind','Kind']]) {
      const value = $((routine ? 'journal' : 'activity') + suffix).value;
      if (value) params.set(key,value);
    }
    return params;
  }

  async function loadActivity(routine = false, more = false) {
    if (!signed()) return;
    const prefix = routine ? 'journal' : 'activity';
    const params = scopeParameters(routine), scope = params.toString();
    const root = $(prefix+'List'), status = $(prefix+'Status');
    const version = routine ? ++routineVersion : ++activityVersion;
    const owner = state.profile.patient_id, workspace = state.workspaceVersion, epoch = generation;
    const current = () => generation === epoch && state.profile?.patient_id === owner && state.workspaceVersion === workspace
      && version === (routine ? routineVersion : activityVersion) && scopeParameters(routine).toString() === scope;
    if (routine && !params.get('routine_id')) {
      root.replaceChildren();
      status.textContent = 'Choose a routine to read its recorded activity.';
      $(prefix+'More').hidden = true;
      return;
    }
    if (!$(prefix+'Form').reportValidity()) return;
    if (more) {
      if (scope !== (routine ? routineScope : activityScope)) return;
      params.set('cursor',routine ? routineCursor : activityCursor);
    } else {
      root.replaceChildren();
      if (routine) routineCursor = null;
      else activityCursor = null;
    }
    $(prefix+'More').disabled = true;
    status.textContent = 'Loading recorded activity…';
    try {
      const data = await requestJSON('/api/journey/activity?'+params,{ownerGuard:current});
      if (!current()) return;
      if (!Array.isArray(data.activity)) throw Error('Activity could not be read.');
      for (const item of data.activity) {
        const row = node('article',undefined,'activity-entry');
        row.append(node('small',item.recorded_date+' · '+({assessment:'Assessment',checkin:'Check-in',event:'Routine action'})[item.kind]),
          node('h3',item.title),node('p',item.detail || (item.kind==='assessment' ? 'Saved findings and their original evidence.' : 'Self-reported activity.')));
        if (item.action) row.append(node('p',readableStatus(item.action)+' — self-reported'));
        row.append(node('small','Saved '+date(item.saved_at)));
        if (item.kind === 'assessment' && !item.unavailable) row.append(action('Open result',()=>showSavedReport(item.id)));
        if (item.kind === 'checkin') row.append(action('View check-in',()=>window.ContinuityUI.viewCheckin(item.id)));
        if (item.corrections.length) {
          const history = node('details');
          history.append(node('summary',item.corrections.length+' correction'+(item.corrections.length===1?'':'s')));
          history.append(node('p','Original record · '+readable(item.original)));
          for (const revision of item.corrections) history.append(node('p',date(revision.created_at)+' · '+readable(revision.data.effective)));
          row.append(history);
        }
        root.append(row);
      }
      if (routine) {routineCursor = data.next_cursor; routineScope = scope;}
      else {activityCursor = data.next_cursor; activityScope = scope;}
      $(prefix+'More').hidden = !data.next_cursor;
      status.textContent = root.children.length ? root.children.length+' records shown. '+data.meaning : 'No recorded activity matches these filters.';
    } catch (error) {
      if (current()) {
        status.textContent = error.message+' Select Show activity to retry.';
        $(prefix+'More').hidden = true;
      }
    } finally {
      if (current()) $(prefix+'More').disabled = false;
    }
  }

  function comparisonCount() {
    text('comparisonStatus', selected.size+' of 2 assessments selected. Choose records from the same concern and area.');
    $('compareAssessments').disabled = selected.size !== 2;
  }
  function historyRendered() {
    if (!installed) return;
    for (const row of $('journeySearchResults').querySelectorAll('article[data-assessment-id]')) {
      if (row.querySelector('.compare-choice')) continue;
      const label = node('label',undefined,'compare-choice');
      const input = node('input');
      input.type = 'checkbox';
      input.checked = selected.has(row.dataset.assessmentId);
      input.setAttribute('aria-label','Select '+row.querySelector('h3').textContent+' for comparison');
      input.onchange = () => {
        if (input.checked && selected.size === 2) {
          input.checked = false;
          text('comparisonStatus','Two assessments are already selected. Clear a selection to choose another.');
          return;
        }
        if (input.checked) selected.add(row.dataset.assessmentId);
        else selected.delete(row.dataset.assessmentId);
        comparisonVersion++;
        $('comparisonResult').replaceChildren();
        comparisonCount();
      };
      label.append(input,node('span','Compare'));
      row.querySelector('.journey-row-actions').append(label);
    }
  }
  async function compare() {
    if (selected.size !== 2 || !signed()) return;
    const version = ++comparisonVersion, epoch = generation, workspace = state.workspaceVersion;
    const current = () => version === comparisonVersion && epoch === generation && state.workspaceVersion === workspace;
    $('compareAssessments').disabled = true;
    $('comparisonResult').replaceChildren();
    text('comparisonStatus','Reading the original saved evidence…');
    try {
      const data = await requestJSON('/api/journey/compare',{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({assessment_ids:[...selected]}),ownerGuard:current
      });
      if (!current()) return;
      const grid = node('div',undefined,'comparison-grid');
      for (const record of data.records) {
        const column = node('article');
        column.append(node('h3',record.title),node('p',date(record.created_at)));
        const facts = node('dl',undefined,'record-facts');
        let destination = facts;
        const fact = (label,value) => {destination.append(node('dt',label),node('dd',value));};
        fact('Area',record.area);
        fact('Recorded status',record.status.label || record.status.code || 'Unrecorded');
        fact('Concern indicator',record.indicator.score === undefined ? 'Unavailable' : String(record.indicator.score));
        const detail = node('details',undefined,'comparison-evidence'), evidence = node('dl',undefined,'record-facts');
        detail.append(node('summary','Recorded inputs and evidence versions'),evidence);
        destination = evidence;
        fact('Methodology',record.indicator.methodology_version || record.indicator.version || 'Unrecorded');
        fact('Model',record.model_id || 'Unavailable');
        fact('Model version',record.model_version || 'Unrecorded');
        fact('Pipeline / calibration',[record.pipeline_version || 'Unrecorded',record.calibration_version || 'Unavailable'].join(' / '));
        fact('Reported context',readable(record.context));
        fact('Recorded inputs',readable(record.inputs));
        column.append(facts,action('Open original report',()=>showSavedReport(record.assessment_id)),detail);
        grid.append(column);
      }
      $('comparisonResult').append(node('p',data.meaning),grid,node('p',data.comparison.summary.replace(/^Follow-up saved\.\s*/,'')));
      text('comparisonStatus','Two original records from '+data.concern.label+'. Source photos are unavailable.');
    } catch (error) {
      if (current()) text('comparisonStatus',error.message+' Clear the selection to choose another pair.');
    } finally {
      if (current()) $('compareAssessments').disabled = false;
    }
  }

  function planReview() {
    const form = $('scheduleEditor');
    if (!form.reportValidity()) return;
    const days = [...form.querySelectorAll('[name=routine_day]:checked')].map(input=>['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][Number(input.value)]);
    const lines = $('routineSteps').value.split('\n').map(value=>value.trim()).filter(Boolean);
    const name = $('scheduleRoutine').selectedOptions[0]?.textContent || 'Your routine';
    $('routinePlanReview').replaceChildren(node('h4',name),node('p',days.join(', ')+' at '+$('routineTimes').value+' · '+$('routineTimezone').value),
      node('p','Status · '+readableStatus($('routineScheduleStatus').value)),
      node('p','Concern · '+($('scheduleEpisode').selectedOptions[0]?.textContent || 'Unassigned')));
    const steps = node('ol');
    for (const line of lines) steps.append(node('li',line));
    $('routinePlanReview').append(steps,node('p','Quiet hours · '+$('quietStart').value+'–'+$('quietEnd').value),
      node('p',$('routineReminderOptIn').checked?'Reminder preference is on. Email delivery requires a configured provider.':'Reminder preference is off.'));
    $('routinePlanReview').hidden = false;
  }

  async function loadDay() {
    const routine=$('journalRoutine').value, day=$('journalDate').value, version=++dayVersion, epoch=generation, workspace=state.workspaceVersion;
    const current=()=>version===dayVersion&&epoch===generation&&workspace===state.workspaceVersion&&routine===$('journalRoutine').value&&day===$('journalDate').value;
    $('routineDayList').replaceChildren();
    if(!signed()||!routine||!day){text('routineDayStatus','Choose a routine and date to read the saved plan and recorded actions.');return;}
    text('routineDayStatus','Reading this date’s plan and actions…');
    try {
      const data=await requestJSON('/api/journey/routines/'+encodeURIComponent(routine)+'/day?date='+encodeURIComponent(day),{ownerGuard:current});
      if(!current())return;
      for(const slot of data.slots){
        const row=node('article',undefined,'activity-entry');
        row.append(node('h4',slot.step_text),node('p',slot.time+' · '+slot.timezone+' · '+readableStatus(slot.state)),node('small','Plan version '+slot.schedule_version+(slot.revision?' · Corrected '+slot.revision+' times':'')));
        if(slot.recorded_outside_plan)row.append(node('p','Recorded against this saved plan version; outside its effective scheduled interval.'));
        $('routineDayList').append(row);
      }
      text('routineDayStatus',data.date+' · '+data.meaning+(!data.slots.length?' No scheduled occurrences or actions on this date.':'')+(!data.history_available?' Earlier plan history is unavailable; only recorded actions can be shown.':''));
    }catch(error){if(current())text('routineDayStatus',error.message+' Choose Show day to retry.');}
  }

  function refresh() {
    if (!installed) return;
    const account = signed();
    $('concernActivity').hidden = !account;
    $('routineJournal').hidden = !account;
    $('assessmentComparison').hidden = !account;
    const status = $('routineStatusFilter').value;
    let visible = 0;
    for (const row of $('routineList').querySelectorAll('[data-routine-id]')) {
      row.hidden = Boolean(status && row.dataset.status !== status);
      if (!row.hidden) visible++;
    }
    text('routineFilterStatus',account ? visible+' routines shown.' : '');
    const picker = $('journalRoutine'), signature = state.routines.map(r=>r.routine_id+':'+r.routine_name).join('|');
    if (picker.dataset.options !== signature) {
      const current = picker.value;
      picker.replaceChildren(new Option('Choose a routine',''));
      for (const routine of state.routines) picker.add(new Option(routine.routine_name,routine.routine_id));
      picker.value = current;
      picker.dataset.options = signature;
    }
    scopePicker();
    historyRendered();
    for (const button of $('mobileTabBar').querySelectorAll('button')) {
      const active = button.dataset.mobilePage === document.querySelector('.page-active')?.dataset.page;
      button.setAttribute('aria-current',active ? 'page' : 'false');
    }
  }

  function page(target) {
    refresh();
    if (target === 'progress' && signed()) {
      if ($('concernActivity').open) void loadActivity();
      if ($('routineJournal').open) void loadActivity(true);
    }
  }
  function clear() {
    generation++; activityVersion++; routineVersion++; comparisonVersion++; dayVersion++;
    selected.clear(); activityCursor=null; routineCursor=null;
    if (!installed) return;
    for (const id of ['activityList','journalList','comparisonResult','routinePlanReview','routineDayList']) $(id).replaceChildren();
    for (const id of ['activityForm','journalForm']) $(id).reset();
    $('routineStatusFilter').value = '';
    $('concernActivity').open = false;
    $('routineJournal').open = false;
    $('routinePlanReview').hidden = true;
    $('journalDate').value='';text('routineDayStatus','');
    comparisonCount();
    for(const id of ['activityConcern','journalRoutine']){$(id).replaceChildren(new Option('Choose a record',''));delete $(id).dataset.options;}
    for(const id of ['concernActivity','routineJournal','assessmentComparison'])$(id).hidden=true;
  }
  function activityPanel(id, prefix, title, pickerMarkup) {
    const panel = node('details',undefined,'consumer-panel activity-panel');
    panel.id = id;
    panel.innerHTML = `<summary>${title}</summary>
      <form id="${prefix}Form" class="consumer-filter">
        ${pickerMarkup}
        <label>From<input id="${prefix}Start" type="date"></label>
        <label>To<input id="${prefix}End" type="date"></label>
        <label>Record type<select id="${prefix}Kind"><option value="">All activity</option><option value="checkin">Check-ins</option><option value="event">Routine actions</option>${prefix==='activity'?'<option value="assessment">Assessments</option>':''}</select></label>
        <button class="button quiet" type="submit">Show activity</button>
      </form>
      <p id="${prefix}Status" role="status"></p><div id="${prefix}List"></div>
      <button id="${prefix}More" type="button" class="button quiet" hidden>Load more activity</button>`;
    return panel;
  }
  function install() {
    const nav = node('nav',undefined,'mobile-tab-bar');
    nav.id = 'mobileTabBar';
    nav.setAttribute('aria-label','Quick navigation');
    for (const [route,label] of [['dashboard','Today'],['home','Check'],['progress','Journey'],['learn','Learn'],['settings','Profile']]) {
      const button = action(label,()=>{showPage(route);const title=document.querySelector('.page-active h1');if(title){title.tabIndex=-1;title.focus({preventScroll:true});}},'mobile-tab');
      button.dataset.mobilePage = route;
      nav.append(button);
    }
    document.querySelector('.app-shell > main').append(nav);
    const activity = activityPanel('concernActivity','activity','Concern activity','<label>Concern<select id="activityConcern"></select></label>');
    $('episodeWorkspace').after(activity);
    $('activityForm').onsubmit = event=>{event.preventDefault();void loadActivity();};
    $('activityMore').onclick = ()=>loadActivity(false,true);
    activity.addEventListener('toggle',()=>{if(activity.open)void loadActivity();});
    const comparison = node('section',undefined,'consumer-panel assessment-comparison');
    comparison.id = 'assessmentComparison';
    comparison.innerHTML = '<h2>Compare saved assessments</h2><p>Select two records below from the same concern and area to read their original evidence together.</p><p id="comparisonStatus" role="status"></p><div class="consumer-actions"><button id="compareAssessments" type="button" class="button quiet" disabled>Compare selected records</button><button id="clearComparison" type="button" class="text-button">Clear selection</button></div><div id="comparisonResult"></div>';
    $('completeJourney').before(comparison);
    $('compareAssessments').onclick = compare;
    $('clearComparison').onclick = ()=>{selected.clear();comparisonVersion++;$('comparisonResult').replaceChildren();comparisonCount();for(const input of $('journeySearchResults').querySelectorAll('.compare-choice input'))input.checked=false;};
    const statusLabel = node('label','Show routines');
    const statusFilter = node('select');
    statusFilter.id = 'routineStatusFilter';
    for (const [value,label] of [['','All statuses'],['active','Active'],['paused','Paused'],['archived','Archived']]) statusFilter.add(new Option(label,value));
    statusLabel.append(statusFilter);
    const filterStatus=node('p');filterStatus.id='routineFilterStatus';filterStatus.setAttribute('role','status');
    $('routineList').before(statusLabel,filterStatus);
    statusFilter.onchange=refresh;
    const journal=activityPanel('routineJournal','journal','Routine journal','<label>Routine<select id="journalRoutine"></select></label>');
    $('scheduleWorkspace').after(journal);
    $('journalForm').onsubmit=event=>{event.preventDefault();void loadActivity(true);};
    $('journalMore').onclick=()=>loadActivity(true,true);
    journal.addEventListener('toggle',()=>{if(journal.open)void loadActivity(true);});
    const day=node('section',undefined,'routine-day-view');
    day.innerHTML='<h3>Plan and actions for a date</h3><p>Read the plan saved at each scheduled time, including earlier versions.</p><label>Date<input id="journalDate" type="date"></label><button id="showRoutineDay" type="button" class="button quiet">Show day</button><p id="routineDayStatus" role="status"></p><div id="routineDayList"></div>';
    $('journalForm').after(day);
    $('showRoutineDay').onclick=loadDay;
    $('journalRoutine').addEventListener('change',()=>{void loadActivity(true);void loadDay();});
    $('journalDate').addEventListener('change',()=>void loadDay());
    const form=$('scheduleEditor');
    for(const id of ['routineSteps','routineTimes','routineTimezone']){
      const input=$(id),help=$(input.getAttribute('aria-describedby'));
      if(help)input.closest('label').append(help);
    }
    const heading=node('h4','2. Build your schedule');
    form.prepend(heading);
    const review=node('section',undefined,'plan-review');review.id='routinePlanReview';review.hidden=true;review.setAttribute('aria-live','polite');
    const preview=action('3. Review your plan',planReview);
    form.querySelector('[type=submit]').before(preview,review);
    form.addEventListener('input',()=>{review.hidden=true;});
    const creation=$('routineFormTitle');
    if(creation)creation.textContent='1. Name your routine';
    $('scheduleWorkspace').querySelector('h3').textContent='Steps, schedule and review';
    const summary=node('section',undefined,'consumer-panel privacy-summary');
    summary.id='accountPrivacySummary';
    summary.innerHTML='<h2>Your account at a glance</h2><p id="accountPrivacyState"></p><p>Source photos are processed in memory. Saved findings and self-reported records can be viewed and exported from this account.</p>';
    $('consumerAccount').prepend(summary);
    const updatePrivacy=()=>text('accountPrivacyState',[$('processingState').textContent,$('emailVerificationState').textContent,$('consumerDeliveryState').textContent].filter(Boolean).join(' '));
    for(const id of ['processingState','emailVerificationState','consumerDeliveryState'])new MutationObserver(updatePrivacy).observe($(id),{childList:true,characterData:true,subtree:true});
    installed=true;comparisonCount();refresh();
  }
  window.ProductUpgrade={refresh,page,clear,historyRendered,recordsChanged(){
    comparisonVersion++;selected.clear();
    if(!installed)return;
    $('comparisonResult').replaceChildren();comparisonCount();
    for(const input of $('journeySearchResults').querySelectorAll('.compare-choice input'))input.checked=false;
    refresh();if($('concernActivity').open)void loadActivity();if($('routineJournal').open){void loadActivity(true);void loadDay();}
  }};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
