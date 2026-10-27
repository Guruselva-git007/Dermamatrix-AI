/* Factual Today, routine scheduling, full Journey search and educational guides. */
(() => {
  'use strict';
  let generation = 0, historyCursor = null, historyQuery = '', historyArea = '', historyEpisode='',historyBodyArea='',historyLoading = false, todayFlight = null;
  let historyRequestVersion=0;
  let schedule = null, scheduleId = '', scheduleLoadVersion = 0, guideVersion = 0;
  const $ = id => document.getElementById(id);
  const node = (tag, text, cls) => { const n = document.createElement(tag); if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n; };
  const action = (label, fn, cls='button quiet') => { const n=node('button',label,cls);n.type='button';n.onclick=fn;return n; };
  const signed = () => window.ConsumerClient?.enabled && Boolean(state.profile?.patient_id);
  const current = version => version === generation && signed();
  const status = (id,message) => { if($(id))$(id).textContent=message; };
  const put = (path,data,method='PUT',headers={}) => requestJSON(path,{method,headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(data)});
  const localDate = zone => new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());

  async function loadToday() {
    if(!signed()) { if($('todayTasks'))$('todayTasks').replaceChildren(node('p','Create an account to schedule routines and save check-ins. Guest assessments stay in this tab.'));return; }
    if(todayFlight)return todayFlight;
    const version=generation;
    const flight=(async()=>{
      try {
        const data=await requestJSON('/api/today');if(!current(version))return;
        const list=$('todayTasks');list.replaceChildren();
        if(!data.tasks.length)list.append(node('p','No scheduled steps today. Add a routine in Journey, then choose its steps and schedule.'));
        for(const task of data.tasks) {
          const row=node('article',undefined,'today-task');
          row.append(node('strong',task.label),node('p',`${task.routine_name} · ${task.time} · ${task.timezone}`),node('span',task.state==='pending'?'Not recorded':task.state==='completed'?'Completed — self-reported':'Skipped — self-reported'));
          if(task.state==='pending') for(const [label,value] of [['Done','completed'],['Skip','skipped']])row.append(action(label,async()=>{
            const buttons=[...row.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
            try { await put(`/api/routine-schedules/${encodeURIComponent(task.routine_id)}/events`,{action:value,step:task.step,date:task.date,time:task.time},'POST',{'Idempotency-Key':crypto.randomUUID()});if(current(version))await loadTodayFresh(); }
            catch(e){if(current(version))status('engagementStatus',e.message);buttons.forEach(b=>b.disabled=false);}
          }));
          list.append(row);
        }
        if(data.recent_result)list.append(action('Open your latest saved result',async()=>{
          const id=data.recent_result.assessment_id;
          if(!state.analyses.some(r=>r.assessment_id===id)) { const detail=await requestJSON(`/api/assessments/${encodeURIComponent(id)}`);if(!current(version))return;state.analyses.push({assessment_id:id,area:data.recent_result.area,summary:detail.assessment||detail,created_at:data.recent_result.created_at}); }
          showSavedReport(id);
        }));
      }catch(e){if(current(version))status('engagementStatus',e.message);}
      finally{if(todayFlight===flight)todayFlight=null;}
    })();todayFlight=flight;return flight;
  }
  async function loadTodayFresh(){todayFlight=null;return loadToday();}

  async function loadSchedule() {
    const id=$('scheduleRoutine').value;const version=generation;const load=++scheduleLoadVersion;
    scheduleId=id;schedule=null;$('scheduleEditor').hidden=!id;$('routineEventHistory').replaceChildren();if(!id)return;
    status('scheduleStatus','Loading schedule…');
    try {
      const data=await requestJSON(`/api/routine-schedules/${encodeURIComponent(id)}`);
      if(!current(version)||load!==scheduleLoadVersion||scheduleId!==id)return;
      schedule=data.schedule;
      const c=schedule||{steps:[],days:[0,1,2,3,4,5,6],times:['09:00'],timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,area:'General',status:'active',episode:'',body_area:'',reminders:false,quiet_start:'21:00',quiet_end:'08:00'};
      $('routineSteps').value=c.steps.join('\n');$('routineTimes').value=c.times.join(', ');$('routineTimezone').value=c.timezone;
      $('routineScheduleArea').value=c.area;$('routineScheduleStatus').value=c.status;$('routineEpisode').value=c.episode;$('routineBodyArea').value=c.body_area;
      $('routineReminderOptIn').checked=c.reminders;$('quietStart').value=c.quiet_start;$('quietEnd').value=c.quiet_end;
      document.querySelectorAll('[name=routine_day]').forEach(input=>input.checked=c.days.includes(Number(input.value)));
      status('scheduleStatus',schedule?'Schedule loaded. Edits preserve past completion records.':'Add your own steps and schedule. This does not create a medical treatment plan.');
      for(const event of data.events)$('routineEventHistory').append(node('li',`${event.date} ${event.time} · ${event.step_text} · ${event.action} · schedule version ${event.schedule_version}`));
      if(!data.events.length)$('routineEventHistory').append(node('li','No completion events recorded.'));
    }catch(e){if(current(version)&&load===scheduleLoadVersion)status('scheduleStatus',e.message);}
  }
  function updateRoutines(){
    if(!$('scheduleRoutine'))return;
    const selected=$('scheduleRoutine').value, select=$('scheduleRoutine');
    select.replaceChildren(new Option('Choose a saved routine',''));
    for(const r of state.routines)select.add(new Option(r.routine_name,r.routine_id));
    if(state.routines.some(r=>r.routine_id===selected))select.value=selected;
    $('scheduleWorkspace').hidden=!signed();
  }

  async function loadHistory(reset=false){
    if(!signed()||historyLoading&&!reset)return;
    if(reset){historyCursor=null;historyQuery=$('journeySearch').value.trim();historyArea=$('journeyArea').value;historyEpisode=$('journeyEpisode').value.trim();historyBodyArea=$('journeyBodyArea').value.trim();$('journeySearchResults').replaceChildren();}
    const version=generation, requestVersion=++historyRequestVersion;historyLoading=true;$('journeyMore').disabled=true;
    try{
      const params=new URLSearchParams({q:historyQuery,area:historyArea,episode:historyEpisode,body_area:historyBodyArea});if(historyCursor)params.set('cursor',historyCursor);
      const data=await requestJSON('/api/journey/assessments?'+params);if(!current(version)||requestVersion!==historyRequestVersion)return;
      if(!data.analyses.length&&reset)$('journeySearchResults').append(node('p','No saved results match these filters.'));
      for(const result of data.analyses){
        const row=node('article',undefined,'journey-search-row');
        const title=result.summary.assessment_result?.condition?.name||result.summary.condition_intelligence?.finding?.name||`${result.area} assessment`;
        row.append(node('h4',title),node('p',`${result.area} · ${new Date(result.created_at).toLocaleString()}${result.unavailable?' · Original record unavailable':''}`));
        if(result.context?.episode||result.context?.body_area)row.append(node('p',`Your labels: ${result.context.episode||'No episode'} · ${result.context.body_area||'No body area'}`));
        row.append(action('Organise result',()=>editContext(result)));
        if(!result.unavailable)row.append(action('Open result',()=>{const old=state.analyses.findIndex(r=>r.assessment_id===result.assessment_id);if(old<0)state.analyses.push(result);else state.analyses[old]=result;showSavedReport(result.assessment_id);}),action('Download PDF',()=>{if(!state.analyses.some(r=>r.assessment_id===result.assessment_id))state.analyses.push(result);downloadSavedReport(result.assessment_id);}));
        $('journeySearchResults').append(row);
      }
      historyCursor=data.next_cursor;$('journeyMore').hidden=!historyCursor;status('journeySearchStatus',`${$('journeySearchResults').querySelectorAll('article').length} matching results shown. Newest saved first.`);
    }catch(e){if(current(version)&&requestVersion===historyRequestVersion)status('journeySearchStatus',e.message);}
    finally{if(version===generation&&requestVersion===historyRequestVersion){historyLoading=false;$('journeyMore').disabled=false;}}
  }

  function editContext(result){
    $('contextEpisode').value=result.context?.episode||'';$('contextBodyArea').value=result.context?.body_area||'';
    const dialog=$('resultContextDialog'),version=generation;
    $('contextStatus').textContent='Your labels organise history; they do not alter findings or confirm a diagnosis.';
    $('resultContextForm').onsubmit=async event=>{event.preventDefault();const button=event.currentTarget.querySelector('[type=submit]');if(button.disabled)return;button.disabled=true;
      try{const data=await put('/api/journey/assessments/'+encodeURIComponent(result.assessment_id)+'/context',{episode:$('contextEpisode').value,body_area:$('contextBodyArea').value});if(current(version)){dialog.close();await loadHistory(true);toast(data.message);}}
      catch(e){if(current(version))status('contextStatus',e.message);}finally{button.disabled=false;}};
    dialog.showModal();$('contextEpisode').focus();
  }

  async function guides(){
    const query=$('learnSearch').value.trim().toLowerCase(),area=$('learnArea').value,version=++guideVersion;
    try{
      const data=await requestJSON('/api/knowledge/conditions'+(area?'?area='+encodeURIComponent(area):''));if(version!==guideVersion)return;
      const list=$('learnList');list.replaceChildren();
      const items=data.items.filter(r=>`${r.name} ${(r.aliases||[]).join(' ')}`.toLowerCase().includes(query));
      for(const entry of items){const row=node('article',undefined,'learn-row');row.append(node('h3',entry.name),node('p',entry.health_area),action('Read guide',()=>openGuide(entry.id)));list.append(row);}
      if(!items.length)list.append(node('p','No guides match. Try a different word or category.'));
    }catch(e){status('learnStatus',e.message);}
  }
  async function openGuide(id){
    const version=++guideVersion;
    try{
      const {topic}=await requestJSON('/api/knowledge/conditions/'+encodeURIComponent(id));if(version!==guideVersion)return;
      const body=$('learnDetail');body.replaceChildren(node('h2',topic.name),node('p',topic.medical_notice),node('p',topic.description));
      for(const [label,key] of [['Common symptoms','common_symptoms'],['General care context','care_options'],['Routine discussion','daily_routine'],['When to seek care','red_flags']]){
        body.append(node('h3',label));const list=node('ul');for(const value of topic[key]||[])list.append(node('li',value));body.append(list);
      }
      body.append(node('h3','Sources & content status'),node('p',`Content version: ${topic.version}. Recorded review date: ${topic.last_reviewed}. Clinical reviewer identity is not recorded; independent clinical review remains pending.`));
      const sources=node('ul');for(const source of topic.evidence_references||[]){const url=supportedExternalUrl(source.url);if(url){const li=node('li'),a=node('a',source.title||source.name||url);a.href=url;a.target='_blank';a.rel='noopener noreferrer';li.append(a);sources.append(li);}}body.append(sources);
      body.append(action('Report a correction',()=>{showPage('settings');if(signed()){document.querySelector('#rightsRequestForm [name=kind]').value='content_correction';document.querySelector('#rightsRequestForm [name=note]').value=`Guide: ${topic.id}; version: ${topic.version}\n`;document.querySelector('#rightsRequestForm textarea').focus();}else{toast('Sign in to record a local correction request. No monitored support service is configured.');}}));
      body.hidden=false;body.tabIndex=-1;body.focus();body.scrollIntoView({block:'start',behavior:'auto'});
    }catch(e){status('learnStatus',e.message);}
  }

  window.EngagementUI={
    clear(){generation++;scheduleLoadVersion++;historyRequestVersion++;historyLoading=false;todayFlight=null;historyCursor=null;schedule=null;scheduleId='';$('resultContextDialog')?.close();for(const id of ['todayTasks','journeySearchResults','routineEventHistory'])$(id)?.replaceChildren();for(const id of ['routineSteps','routineEpisode','routineBodyArea','journeySearch','journeyEpisode','journeyBodyArea','contextEpisode','contextBodyArea'])if($(id))$(id).value='';if($('scheduleWorkspace'))$('scheduleWorkspace').hidden=true;},
    page(page){if(page==='dashboard')loadToday();if(page==='progress'){updateRoutines();if(signed()&&!$('journeySearchResults').children.length)loadHistory(true);}if(page==='learn')guides();},
    progress(){updateRoutines();},
    welcome(){if(!sessionStorage.getItem('dermamatrix_intro_seen'))$('welcomeDialog')?.showModal();}
  };
  function install(){
    const today=node('section',undefined,'consumer-panel today-panel');today.id='consumerToday';today.innerHTML='<h2>Your next step</h2><p>Record the routine you chose to follow and meaningful changes over time.</p><p id="engagementStatus" role="status" aria-live="polite"></p><div id="todayTasks"></div><div class="consumer-actions"><button class="button quiet" id="todayNewCheck" type="button">Start a check</button><button class="button quiet" id="todayJourney" type="button">Manage routines</button><button class="text-button" id="openWelcome" type="button">How this works</button></div>';
    document.querySelector('#dashboard .dashboard-heading')?.after(today);
    if(!today.isConnected)$('dashboard').prepend(today);
    $('todayNewCheck').onclick=()=>showPage('home');$('todayJourney').onclick=()=>showPage('progress');
    const schedulePanel=node('section',undefined,'consumer-panel');schedulePanel.id='scheduleWorkspace';schedulePanel.hidden=true;
    schedulePanel.innerHTML=`<h3>Routine steps & schedule</h3><p>Your own tracking plan. This app does not prescribe treatment.</p><label>Saved routine<select id="scheduleRoutine"><option value="">Choose a saved routine</option></select></label><p id="scheduleStatus" role="status" aria-live="polite"></p><form id="scheduleEditor" hidden><label>Steps (one per line)<textarea id="routineSteps" required maxlength="3620" aria-describedby="routineStepsHelp"></textarea></label><small id="routineStepsHelp">1–20 steps, up to 180 characters each.</small><fieldset><legend>Days</legend><div class="routine-day-options">${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((d,i)=>`<label><input name="routine_day" type="checkbox" value="${i}" checked>${d}</label>`).join('')}</div></fieldset><label>Times (comma separated)<input id="routineTimes" required placeholder="09:00, 18:00" aria-describedby="routineTimesHelp"></label><small id="routineTimesHelp">Up to four times, using 24-hour HH:MM.</small><label>Timezone<input id="routineTimezone" required list="routineZones" aria-describedby="timezoneHelp"></label><datalist id="routineZones"><option value="Asia/Kolkata"><option value="UTC"><option value="America/New_York"><option value="Europe/London"></datalist><small id="timezoneHelp">Use an IANA name such as Asia/Kolkata. Scheduling follows local daylight-saving rules.</small><label>Area<select id="routineScheduleArea">${['General','Skin','Hair','Nails','Sweat'].map(x=>`<option>${x}</option>`).join('')}</select></label><label>Concern / episode (optional)<input id="routineEpisode" maxlength="120"></label><label>Body area (optional)<input id="routineBodyArea" maxlength="80"></label><label>Status<select id="routineScheduleStatus"><option value="active">Active</option><option value="paused">Paused</option><option value="archived">Archived</option></select></label><label class="consumer-checkbox"><input id="routineReminderOptIn" type="checkbox">I want generic email reminders for this routine</label><label>Quiet hours start<input id="quietStart" type="time" value="21:00" required></label><label>Quiet hours end<input id="quietEnd" type="time" value="08:00" required></label><p>Quiet-hour occurrences are skipped; identical start/end means no quiet window. Email must be verified. Delivery needs a configured transport and an explicitly run worker. This local app does not install a scheduler.</p><button class="button primary" type="submit">Save steps & schedule</button></form><details><summary>Recorded completion history</summary><ul id="routineEventHistory" class="consumer-list"></ul></details><button class="text-button" id="showReminders" type="button">Check reminder status</button><p id="reminderStatus" role="status"></p>`;
    document.querySelector('#progress .progress-layout')?.after(schedulePanel);
    $('scheduleRoutine').onchange=loadSchedule;
    $('scheduleEditor').onsubmit=async event=>{event.preventDefault();const b=event.currentTarget.querySelector('[type=submit]');if(b.disabled)return;b.disabled=true;const version=generation,id=scheduleId;
      try{const payload={version:schedule?.version||0,steps:$('routineSteps').value.split('\n').map(s=>s.trim()).filter(Boolean),days:[...document.querySelectorAll('[name=routine_day]:checked')].map(i=>Number(i.value)),times:$('routineTimes').value.split(',').map(s=>s.trim()),timezone:$('routineTimezone').value,area:$('routineScheduleArea').value,status:$('routineScheduleStatus').value,episode:$('routineEpisode').value,body_area:$('routineBodyArea').value,reminders:$('routineReminderOptIn').checked,quiet_start:$('quietStart').value,quiet_end:$('quietEnd').value};const data=await put('/api/routine-schedules/'+encodeURIComponent(id),payload);if(current(version)&&scheduleId===id){schedule=data.schedule;status('scheduleStatus',data.message);await loadTodayFresh();await loadProgress({force:true});}}
      catch(e){if(current(version))status('scheduleStatus',e.message);}finally{b.disabled=false;}};
    $('showReminders').onclick=async()=>{const v=generation;try{const d=await requestJSON('/api/reminders');if(!current(v))return;status('reminderStatus',`Transport: ${d.transport}. ${d.jobs.length} recent jobs. ${d.jobs.map(j=>j.state.replaceAll('_',' ')).join(', ')||'No jobs scheduled yet.'} Delivery is not confirmed by queueing.`);}catch(e){if(current(v))status('reminderStatus',e.message);}};
    const history=node('section',undefined,'consumer-panel');history.id='completeJourney';history.innerHTML='<h3>Search all saved results</h3><form id="journeySearchForm" class="consumer-filter"><label>Search<input id="journeySearch" type="search" maxlength="120" placeholder="Concern or result text"></label><label>Area<select id="journeyArea"><option value="">All areas</option><option>Skin</option><option>Hair</option><option>Nails</option><option>Sweat</option></select></label><label>Episode / concern group<input id="journeyEpisode" maxlength="120" placeholder="Exact saved label"></label><label>Body area<input id="journeyBodyArea" maxlength="80" placeholder="Exact saved label"></label><button class="button quiet" type="submit">Search results</button></form><p id="journeySearchStatus" role="status" aria-live="polite"></p><div id="journeySearchResults"></div><button id="journeyMore" type="button" class="button quiet" hidden>Load next results</button>';
    schedulePanel.after(history);$('journeySearchForm').onsubmit=e=>{e.preventDefault();loadHistory(true);};$('journeyMore').onclick=()=>loadHistory();
    const contextDialog=node('dialog',undefined,'consumer-dialog');contextDialog.id='resultContextDialog';contextDialog.setAttribute('aria-labelledby','contextTitle');contextDialog.innerHTML='<form id="resultContextForm"><h2 id="contextTitle">Organise this result</h2><p id="contextStatus" role="status"></p><label>Episode / concern group<input id="contextEpisode" maxlength="120"></label><label>Body area<input id="contextBodyArea" maxlength="80"></label><div class="consumer-actions"><button id="cancelResultContext" type="button" class="button quiet">Cancel</button><button type="submit" class="button primary">Save labels</button></div></form>';document.body.append(contextDialog);$('cancelResultContext').onclick=()=>contextDialog.close();
    const learn=node('section',undefined,'learn-section');learn.id='learn';learn.dataset.page='learn';learn.setAttribute('aria-labelledby','learnTitle');learn.innerHTML='<h1 id="learnTitle">Understand your concerns</h1><p>Source-linked education, separate from your assessment. These guides do not diagnose or prescribe.</p><form id="learnForm" class="consumer-filter"><label>Search guides<input id="learnSearch" type="search" maxlength="120" placeholder="Search a topic"></label><label>Category<select id="learnArea"><option value="">All categories</option><option>Skin</option><option>Hair</option><option>Nails</option><option>Sweat</option></select></label><button class="button quiet" type="submit">Find guides</button></form><p id="learnStatus" role="status"></p><div id="learnList"></div><article id="learnDetail" class="consumer-panel" hidden></article>';
    $('products').after(learn);$('learnForm').onsubmit=e=>{e.preventDefault();guides();};
    const link=node('a','Learn');link.prepend(node('span','▤'),document.createTextNode(' '));link.href='#learn';link.dataset.pageNav='learn';link.onclick=e=>{e.preventDefault();showPage('learn');};document.querySelector('[data-page-nav=progress]').after(link);
    const intro=node('dialog',undefined,'consumer-dialog');intro.id='welcomeDialog';intro.setAttribute('aria-labelledby','welcomeTitle');intro.innerHTML='<h2 id="welcomeTitle">A clearer way to keep track</h2><ol><li>Choose a concern and provide the appropriate photo or questionnaire.</li><li>Read the supported evidence, uncertainty and next steps. Research rankings are not diagnoses.</li><li>Save with an account, track your own routine and prepare a clinician discussion.</li></ol><p>Guest results remain in the current tab. Creating an account does not silently transfer a guest assessment. Source photos are not retained by the assessment service.</p><button id="closeWelcome" type="button" class="button primary">Continue</button>';
    document.body.append(intro);$('openWelcome').onclick=()=>intro.showModal();$('closeWelcome').onclick=()=>{sessionStorage.setItem('dermamatrix_intro_seen','true');intro.close();};
    updateRoutines();if(document.querySelector('.page-active')?.id==='dashboard')loadToday();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
