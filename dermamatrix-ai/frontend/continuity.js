/* Connected consumer flows. All private truth comes from owner-scoped APIs.
 * Drafts and retry identifiers live only in this tab and clear on account change. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const el = (tag, text, cls) => {const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const button = (text, fn, cls='button quiet') => {const n=el('button',text,cls);n.type='button';n.onclick=fn;return n;};
  const signed = () => Boolean(window.ConsumerClient?.enabled && state.profile?.patient_id);
  const owner = () => state.profile?.patient_id || '';
  let epoch=0, loadedOwner='', episodes=[], links={}, bookmarks=[], loading=null, scheduleLink={}, searchCursor=null, searchQuery='', searchCategory='',briefSignature='',searchVersion=0,loadVersion=0,reminderVersion=0;
  const retryKeys=new Map();
  const active = (version, account) => epoch===version && owner()===account;
  const message = (id, text) => {if($(id))$(id).textContent=text;};
  async function write(path, payload, method='POST') {
    const version=epoch,account=owner();
    const signature=JSON.stringify([path,payload,method]);
    if(!retryKeys.has(signature))retryKeys.set(signature,crypto.randomUUID());
    return requestJSON(path,{method,headers:{'Content-Type':'application/json','Idempotency-Key':retryKeys.get(signature)},body:method==='DELETE'?undefined:JSON.stringify(payload),ownerGuard:()=>active(version,account)});
  }
  function choices(select, selected='', empty='No concern selected') {
    select.replaceChildren(new Option(empty,''));
    for(const item of episodes)select.add(new Option(`${item.label} · ${item.body_area}`,item.episode_id));
    select.value=selected;
  }
  function pick(id, title) {const label=el('label',title),select=el('select');select.id=id;label.append(select);choices(select);return label;}
  async function load(force=false) {
    if(!signed())return;
    if(loading&&!force)return loading;
    const version=epoch,account=owner(),requestVersion=++loadVersion;
    const flight=(async()=>{try{
      const [ep,associations,saved]=await Promise.all([requestJSON('/api/episodes'),requestJSON('/api/episode-links'),requestJSON('/api/bookmarks')]);
      if(!active(version,account)||requestVersion!==loadVersion)return;
      episodes=ep.episodes;links=associations.links;bookmarks=saved.bookmarks;loadedOwner=account;
      for(const id of ['assessmentEpisode','checkinEpisode','journeyEpisodeId','scheduleEpisode','briefEpisode'])if($(id))choices($(id),$(id).value,id==='journeyEpisodeId'?'All concerns':'No concern selected');
      if($('episodeBody')&&!$('episodeBody').options.length)for(const value of ep.body_areas)$('episodeBody').add(new Option(value,value));
      renderBookmarks();renderCheckinHistory();
    }catch(error){if(active(version,account)&&requestVersion===loadVersion)message('continuityStatus',`${error.message} Your current input remains in this tab. Retry by reopening Journey.`);}
    finally{if(loading===flight)loading=null;}})();loading=flight;return flight;
  }
  async function changed() {
    const version=epoch,account=owner();if(!signed())return;
    await load(true);if(!active(version,account))return;
    briefSignature='';$('briefSelection')?.replaceChildren();message('briefStatus','Your records changed. Preview again before downloading; your dates and questions are preserved.');
    await loadProgress({force:true});if(!active(version,account))return;
    await window.EngagementUI?.refresh();
    if($('unifiedSearchDialog')?.open)await search(true);
  }
  function dialog(title, content, save, label='Save correction') {
    const opener=document.activeElement,d=$('continuityDialog');d.replaceChildren();const form=el('form');form.append(el('h2',title));
    const heading=form.firstChild;heading.id='continuityDialogTitle';d.setAttribute('aria-labelledby',heading.id);
    form.append(content);const status=el('p');status.id='continuityDialogStatus';status.setAttribute('role','status');form.append(status);
    const actions=el('div',undefined,'consumer-actions'),submit=el('button',label,'button primary');submit.type='submit';
    actions.append(button('Back',()=>d.close()),submit);form.append(actions);d.append(form);
    const version=epoch,account=owner();
    form.onsubmit=async event=>{event.preventDefault();if(submit.disabled)return;submit.disabled=true;message('continuityDialogStatus','Saving…');try{await save();if(active(version,account)){d.close();await changed();if(active(version,account)){const focus=opener?.isConnected?opener:(document.querySelector('.page-active [role=tab][aria-selected=true]')||document.querySelector('.page-active h1'));if(focus){if(focus.tagName==='H1')focus.tabIndex=-1;focus.focus({preventScroll:true});}toast('Saved. Your original records are preserved.');}}}catch(error){if(active(version,account))message('continuityDialogStatus',`${error.message} This attempt was not confirmed. Your input remains here; retry the same details or reload if another tab changed the record.`);}finally{submit.disabled=false;}};
    d.showModal();requestAnimationFrame(()=>form.querySelector('select,input,textarea,button')?.focus());
  }
  function correctEvent(id, revision, title) {
    const content=el('div');content.append(el('p',title),el('p','The original action remains in history. Choose the effective status now.'));
    const label=el('label','Correct status'),select=el('select');select.id='correctionAction';
    for(const [value,text] of [['pending','Not recorded (undo)'],['completed','Completed — self-reported'],['skipped','Skipped — self-reported']])select.add(new Option(text,value));label.append(select);content.append(label);
    const reason=el('label','Reason (optional)'),note=el('textarea');note.maxLength=500;reason.append(note);content.append(reason);
    dialog('Correct routine action',content,()=>write('/api/corrections/event/'+encodeURIComponent(id),{revision,action:select.value,reason:note.value}));
  }
  function checkinFields(content, item) {
    const fields={};
    for(const [name,title,source,value] of [['trend','Current trend','checkinTrend',item.reported_trend],['discomfort','Discomfort','checkinDiscomfort',String(item.discomfort_score)],['change','Recent change','checkinChange',String(item.change_score)]]){
      const label=el('label',title),select=$(source).cloneNode(true);select.removeAttribute('id');select.id='correct-'+name;
      if(![...select.options].some(o=>o.value===value))select.add(new Option('Recorded input: '+value,value));select.value=value;label.append(select);content.append(label);fields[name]=select;
    }
    const dateLabel=el('label','Date'),day=el('input');day.type='date';day.required=true;day.value=item.checkin_date;dateLabel.append(day);content.append(dateLabel);fields.date=day;
    const noteLabel=el('label','Note (optional)'),note=el('textarea');note.maxLength=2000;note.value=item.note||'';noteLabel.append(note);content.append(noteLabel);fields.note=note;
    return fields;
  }
  function correctCheckin(item) {
    const content=el('div');content.append(el('p','This corrects your self-report, not an image measurement. The original remains available in your account export.'));
    const fields=checkinFields(content,item),remove=el('label','Remove this mistaken check-in from current tracking'),check=el('input');check.type='checkbox';remove.prepend(check);content.append(remove);
    dialog('Correct check-in',content,()=>write('/api/corrections/checkin/'+encodeURIComponent(item.checkin_id),check.checked?{revision:item.revision||0,voided:true}:{revision:item.revision||0,reported_trend:fields.trend.value,discomfort:fields.discomfort.value,change:fields.change.value,checkin_date:fields.date.value,note:fields.note.value}));
  }
  function renderCheckinHistory() {
    const list=$('checkinCorrections');if(!list)return;list.hidden=!signed();if($('progressHistory'))$('progressHistory').hidden=signed();if(!signed())return;list.replaceChildren();
    for(const item of state.checkins||[]){const row=el('article',undefined,'continuity-row');row.append(el('strong',item.voided?'Removed from current tracking':`${readableStatus(item.reported_trend)} — self-reported`),el('p',`${item.checkin_date} · ${item.routine_name}`));
      if(item.note)row.append(el('p',item.note));const link=links['checkin:'+item.checkin_id];if(link?.label)row.append(el('p','Concern: '+link.label));
      row.append(button('Correct check-in',()=>correctCheckin(item)));
      if(item.corrections?.length){const details=el('details');details.append(el('summary','Correction history'),el('p',`Original: ${item.original.reported_trend} · ${item.original.checkin_date}`));for(const revision of item.corrections)details.append(el('p',`${new Date(revision.created_at).toLocaleString()} · ${revision.data.effective.voided?'Removed from tracking':revision.data.effective.reported_trend} · account actor ${revision.data.actor_id}`));row.append(details);}list.append(row);
    }
    if(!list.children.length)list.append(el('p','No saved check-ins. Choose a routine above to record your first update.'));
    // One history list owns the correction actions; avoid two competing lists.
    if($('progressHistory'))$('progressHistory').hidden=true;
  }
  async function reviewCheckin() {
    const form=$('checkinForm');if(!form.reportValidity())return;
    const payload={routine_id:$('checkinRoutine').value,checkin_date:$('checkinDate').value,reported_trend:$('checkinTrend').value,discomfort:$('checkinDiscomfort').value,change:$('checkinChange').value,note:$('checkinNote').value,episode_id:$('checkinEpisode').value};
    const content=el('div');const routine=state.routines.find(r=>r.routine_id===payload.routine_id);const episode=episodes.find(r=>r.episode_id===payload.episode_id);
    content.append(el('p',`${routine?.routine_name||'Choose a routine'} · ${payload.checkin_date}`),el('p',`${readableStatus(payload.reported_trend)} — self-reported`),el('p',`Discomfort: ${$('checkinDiscomfort').selectedOptions[0].textContent}. Change: ${$('checkinChange').selectedOptions[0].textContent}.`),el('p',`Concern: ${episode?.label||'Unassigned'}. Confirm this is the right concern.`));if(payload.note)content.append(el('p',payload.note));content.append(el('p','No image is used to measure healing or saved with this check-in.'));
    const version=epoch,account=owner();
    dialog('Review your check-in',content,async()=>{await write('/api/progress-checkins',payload);if(active(version,account)){form.reset();$('checkinDate').value=currentDate();}},'Save check-in');
  }
  function linkAssessment(result) {
    const content=el('div');content.append(el('p','Choose explicitly. Matching labels never merge assessments automatically. Existing labels and original findings remain unchanged.'));
    const choice=pick('linkConcernPicker','Concern');content.append(choice);choice.querySelector('select').value=result.episode_link?.episode_id||'';
    dialog('Link saved result',content,()=>write('/api/episode-links/assessment/'+encodeURIComponent(result.assessment_id),{episode_id:choice.querySelector('select').value,version:result.episode_link?.version||0},'PUT'),'Save concern link');
  }
  function followup() {
    const episode=episodes.find(e=>e.episode_id===$('journeyEpisodeId').value);if(!episode){message('continuityStatus','Choose a concern before starting its follow-up.');return;}
    if(episode.area==='General'){state.areaSelected=false;showPage('home');}else startAreaAssessment(episode.area);$('assessmentEpisode').value=episode.episode_id;$('assessmentEpisode').focus();
    toast('Follow-up concern selected. Review it before submitting.');
  }
  function renderBookmarks() {
    const list=$('savedGuideList');if(!list)return;list.replaceChildren();
    for(const item of bookmarks.filter(b=>b.saved)){const row=el('article',undefined,'continuity-row');row.append(el('strong',item.title),el('p',`Saved content version ${item.content_version} · recorded date ${item.content_date}`),button('Read saved guide',()=>window.EngagementUI.openGuide(item.guide_id)),button('Remove bookmark',()=>changeBookmark(item.guide_id,false,item.version)));list.append(row);}
    if(!list.children.length)list.append(el('p','No saved guides yet. Open a topic and choose Save guide.'));
  }
  async function changeBookmark(id, save, version) {
    const generation=epoch,account=owner();
    try{await write('/api/bookmarks/'+encodeURIComponent(id)+(save?'':'?version='+version),{version},save?'PUT':'DELETE');if(active(generation,account)){await load(true);const control=$('guideBookmark');if(control?.dataset.guide===id)updateGuideBookmark(control,id);message('learnStatus',save?'Guide saved.':'Bookmark removed.');}}
    catch(error){if(active(generation,account))message('learnStatus',`${error.message} The bookmark change was not confirmed. Reopen the guide to retry.`);}
  }
  function updateGuideBookmark(control,id) {const current=bookmarks.find(r=>r.guide_id===id);control.textContent=current?.saved?'Remove bookmark':'Save guide';control.onclick=()=>changeBookmark(id,!current?.saved,current?.version||0);}
  function guide(topic) {
    if(!signed())return;
    const control=button('Save guide',()=>{});control.id='guideBookmark';control.dataset.guide=topic.id;updateGuideBookmark(control,topic.id);$('learnDetail').prepend(control);
  }
  async function search(reset=true) {
    const generation=epoch,account=owner(),requestVersion=++searchVersion;
    if(reset){searchCursor=null;searchQuery=$('unifiedQuery').value.trim();searchCategory=$('unifiedCategory').value;$('unifiedResults').replaceChildren();}
    const params=new URLSearchParams({q:searchQuery,category:searchCategory});if(searchCursor)params.set('cursor',searchCursor);
    $('unifiedMore').disabled=true;message('unifiedStatus','Searching…');
    try{const data=await requestJSON('/api/search?'+params);if(!active(generation,account)||requestVersion!==searchVersion)return;
      for(const item of data.results){const row=el('article',undefined,'continuity-row');row.append(el('small',`${item.category}${item.bookmarked?' · Saved guide':''}`),el('h3',item.title),el('p',item.detail||''),button('Open '+item.category,async()=>{const d=$('unifiedSearchDialog');
        try{if(item.category==='guide'){d.close();showPage('learn');await window.EngagementUI.openGuide(item.id);}
        else if(item.category==='assessment'){d.close();await showSavedReport(item.id);}
        else{let checkin;if(item.category==='checkin'){checkin=(await requestJSON('/api/checkins/'+encodeURIComponent(item.id))).checkin;if(!active(generation,account))return;}d.close();showPage('progress');if(item.category==='episode'){$('journeyEpisodeId').value=item.id;window.EngagementUI.filterEpisode(item.id);window.WorkspaceUI.reveal('results');}
        if(item.category==='routine'){window.WorkspaceUI.reveal('routines');await window.EngagementUI.configureRoutine(item.id);}
        if(item.category==='checkin'){window.WorkspaceUI.reveal('checkins');if(checkin)correctCheckin(checkin);}}}
        catch(error){message('unifiedStatus',`${error.message} The record could not be opened; start the search again.`);}
      }));$('unifiedResults').append(row);}
      searchCursor=data.next_cursor;$('unifiedMore').hidden=!searchCursor;message('unifiedStatus',data.results.length?`${$('unifiedResults').children.length} results shown. ${data.private_results?'Private results belong to this account.':'Sign in to search your private records.'}`:'No matches. Try another word or category.');
    }catch(error){if(active(generation,account)&&requestVersion===searchVersion)message('unifiedStatus',`${error.message} Start this search again to refresh its results.`);}finally{if(active(generation,account)&&requestVersion===searchVersion)$('unifiedMore').disabled=false;}
  }
  function openSearch(query) {$('unifiedQuery').value=query||'';$('unifiedSearchDialog').showModal();$('unifiedQuery').focus();search(true);}
  function schedulePayload(){return{steps:$('routineSteps').value.split('\n').map(s=>s.trim()).filter(Boolean),days:[...document.querySelectorAll('[name=routine_day]:checked')].map(i=>Number(i.value)),times:$('routineTimes').value.split(',').map(s=>s.trim()),timezone:$('routineTimezone').value,status:$('routineScheduleStatus').value,area:$('routineScheduleArea').value,reminders:$('routineReminderOptIn').checked,quiet_start:$('quietStart').value,quiet_end:$('quietEnd').value};}
  async function previewReminder(){const generation=epoch,account=owner(),requestVersion=++reminderVersion;try{const data=await write('/api/reminders/preview',schedulePayload());if(!active(generation,account)||requestVersion!==reminderVersion)return;const p=data.preview;message('reminderPreview',`${p.status==='active'?'Active schedule':'Paused or archived schedule'} · ${p.timezone}. Next eligible occurrence: ${p.next_occurrence_utc?new Date(p.next_occurrence_utc).toLocaleString(undefined,{timeZone:p.timezone})+' ('+p.timezone+')':'None in the next 15 days'}. Quiet hours: ${p.quiet_start}–${p.quiet_end}; suppressed times: ${p.suppressed_times.join(', ')||'none'}. Reminder preference ${p.opted_in?'on':'off'}. Preview only; no work queued. ${data.transport==='disabled'?'Delivery provider unavailable.':'Configured transport does not confirm delivery.'} ${p.meaning}`);}catch(error){if(active(generation,account)&&requestVersion===reminderVersion)message('reminderPreview',`${error.message} No reminder was queued or sent.`);}}
  async function explain(data) {
    const root=$('patientResultContent');if(!root||!data)return;$('resultPlainExplanation')?.remove();
    const consumer=data.assessment_result?.consumer||{},primary=consumer.primary_result||{},findings=data.canonical_evidence?.image_findings||data.image_findings||{};
    const block=el('section',undefined,'result-plain-explanation');block.id='resultPlainExplanation';block.append(el('h3','Understand this result'));
    const pairs=[['What was observed?',data.input_type==='questionnaire'?'Your reported questionnaire answers; no image was assessed.':findings.available?(findings.summary||'See the recorded image measurements below.'):'Separate image measurements are unavailable in this result. See the evidence status below.'],['What does the evidence support?',data.input_type==='questionnaire'?'A self-reported pattern for discussion and tracking, not an image classification.':primary.title?'Recorded output: '+primary.title+'. Research rankings are not clinical probabilities.':'The recorded evidence status below describes which components were available.'],['What remains uncertain?',data.input_type==='questionnaire'?'The questionnaire does not establish a cause or confirm a diagnosis.':`Evidence status: ${readableStatus(consumer.state||data.assessment_state||'not established')}. Research rankings and educational interpretations do not confirm a diagnosis. Photo clarity alone does not establish anatomical suitability.`],['What next?',data.urgent_notice||consumer.professional_support?.summary||'Review the existing care and professional-support guidance below. Use a follow-up to record changes; self-reports do not measure healing.']];
    const list=el('dl');for(const [label,value] of pairs)list.append(el('dt',label),el('dd',value));block.append(list);
    // The actual finding and its next action lead; explanations still precede technical details.
    const lead=root.querySelector(':scope > .assessment-state-card, :scope > .consumer-hero, :scope > .patient-result-hero');
    if(lead)lead.after(block);else root.prepend(block);
    let warning=root.querySelector(':scope > .patient-urgent-alert');
    if(data.urgent_notice&&!warning){warning=el('section',undefined,'patient-urgent-alert');warning.setAttribute('role','alert');warning.append(el('strong','Reported warning signs'),el('p',data.urgent_notice),button('Find a doctor',()=>{closeResult();showPage('support');}));}
    if(warning)root.prepend(warning);
    if(signed()&&state.resultPersistence==='mysql'){const version=epoch,account=owner();try{const associations=await requestJSON('/api/episode-links');if(!active(version,account)||!block.isConnected)return;links=associations.links;const link=links['assessment:'+(state.assessmentId||'')];block.prepend(el('p',link?.label?'Concern: '+link.label+' · '+link.body_area:'No concern linked. You can organise this result in Journey.'));const effective=contextualProgress(data,link);if(effective.status==='CONCERN_SCOPE_CHANGED'){block.append(el('p',effective.summary));const old=root.querySelector('[data-result-action=progress]')?.parentElement?.querySelector('p:not(.eyebrow)');if(old)old.textContent=effective.summary;}}catch{if(block.isConnected&&active(version,account))block.prepend(el('p','Concern context could not be loaded. The saved assessment evidence below remains available.'));}}
  }
  function install() {
    if($('continuityDialog'))return;
    const mobileSearch=button('Search',()=>openSearch(''));mobileSearch.id='mobileWorkspaceSearch';mobileSearch.setAttribute('aria-label','Search records and guides');$('themeToggle').before(mobileSearch);
    const d=el('dialog',undefined,'consumer-dialog');d.id='continuityDialog';document.body.append(d);
    const assessment=pick('assessmentEpisode','Concern (optional)');assessment.id='assessmentEpisodeField';assessment.append(el('small','Only the selected concern is linked when an account saves this assessment.'));document.querySelector('#screen .area-choice').after(assessment);
    const workspace=el('section',undefined,'consumer-panel');workspace.id='episodeWorkspace';workspace.innerHTML='<h3>Keep a concern together</h3><p>Link related checks explicitly. Older unassigned results and your existing labels stay available.</p><details><summary>Create a concern</summary><form id="episodeForm" class="continuity-form"><label>Concern label<input id="episodeLabel" required maxlength="120" placeholder="A label you recognise"></label><label>Category<select id="episodeArea"><option>Skin</option><option>Hair</option><option>Nails</option><option>Sweat</option><option>General</option></select></label><label>Body area<select id="episodeBody"></select></label><button class="button primary" type="submit">Create concern</button></form></details><p id="continuityStatus" role="status"></p>';
    $('completeJourney').before(workspace);const picker=pick('journeyEpisodeId','Concern filter');const concernControls=el('div',undefined,'concern-controls');concernControls.append(picker);workspace.querySelector('details').before(concernControls);picker.querySelector('select').onchange=()=>window.EngagementUI.filterEpisode(picker.querySelector('select').value);concernControls.append(button('Start follow-up',followup));
    $('episodeForm').onsubmit=async event=>{event.preventDefault();const submit=event.currentTarget.querySelector('[type=submit]');if(submit.disabled)return;submit.disabled=true;const version=epoch,account=owner();try{const data=await write('/api/episodes',{label:$('episodeLabel').value,area:$('episodeArea').value,body_area:$('episodeBody').value});if(active(version,account)){await load(true);$('journeyEpisodeId').value=data.episode_id;$('assessmentEpisode').value=data.episode_id;$('episodeForm').reset();workspace.querySelector('details').open=false;$('journeyEpisodeId').focus();window.EngagementUI.filterEpisode(data.episode_id);message('continuityStatus','Concern created. Choose it for a new check or link an existing result.');}}catch(error){if(active(version,account))message('continuityStatus',`${error.message} Creation was not confirmed. Your input remains here; retry the same details.`);}finally{submit.disabled=false;}};
    $('scheduleEditor').prepend(pick('scheduleEpisode','Linked concern (optional)'));
    const preview=el('div');preview.append(button('Preview reminder schedule',previewReminder));const note=el('p');note.id='reminderPreview';note.setAttribute('role','status');preview.append(note);$('scheduleEditor').append(preview);$('scheduleEditor').addEventListener('input',()=>{reminderVersion++;message('reminderPreview','Schedule input changed. Preview again to calculate the next occurrence. No reminder was queued.');});
    $('checkinRoutine').closest('label').after(pick('checkinEpisode','Concern (confirm before saving)'));
    $('checkinRoutine').addEventListener('change',()=>{$('checkinEpisode').value=links['routine:'+$('checkinRoutine').value]?.episode_id||'';});
    const history=el('section');history.id='checkinCorrections';$('progressHistory')?.after(history);
    const brief=el('details');brief.id='visitBrief';brief.innerHTML='<summary>Prepare a clinician-visit brief</summary><form id="visitBriefForm" class="continuity-form"><label>From<input id="briefStart" type="date" required></label><label>To<input id="briefEnd" type="date" required></label><label>Personal questions (optional)<textarea id="briefQuestions" maxlength="3000"></textarea></label><p>Assessment dates use UTC save times; check-ins and routine actions use recorded local dates. Original photos are unavailable. Full reports and account JSON remain available.</p><button type="button" class="button quiet" id="previewBrief">Choose assessments / preview</button><div id="briefSelection"></div><button class="button primary" type="submit">Download visit brief PDF</button><p id="briefStatus" role="status"></p></form>';
    brief.className='consumer-panel';$('completeJourney').after(brief);if($('historyExport'))$('historyExport').querySelector('summary').textContent='Download recent history (all concerns)';$('visitBriefForm').prepend(pick('briefEpisode','Concern'));$('briefEnd').value=currentDate();$('briefStart').value=new Date(Date.now()-30*86400000).toISOString().slice(0,10);
    briefSignature='';
    const briefInput=()=>({episode_id:$('briefEpisode').value,start:$('briefStart').value,end:$('briefEnd').value,questions:$('briefQuestions').value});
    $('previewBrief').onclick=async()=>{const generation=epoch,account=owner(),payload=briefInput();try{const {brief:data}=await write('/api/visit-brief',payload);if(!active(generation,account))return;briefSignature=JSON.stringify(payload);const box=$('briefSelection');box.replaceChildren();for(const row of data.assessments){const label=el('label',`${row.area} assessment · ${new Date(row.created_at).toLocaleString()} (saved time)`),input=el('input');input.type='checkbox';input.checked=true;input.value=row.assessment_id;label.prepend(input);box.append(label);}message('briefStatus',`Available: ${data.counts.assessments} assessments, ${data.counts.checkins} active self-reported check-ins, ${data.counts.routine_actions} routine actions. Uncheck any assessment to omit it. ${data.photo_notice}`);}catch(error){if(active(generation,account))message('briefStatus',`${error.message} No brief was generated.`);}};
    $('visitBriefForm').onsubmit=async event=>{event.preventDefault();const submit=event.currentTarget.querySelector('[type=submit]');if(submit.disabled)return;const payload=briefInput();if(briefSignature!==JSON.stringify(payload)){message('briefStatus','Preview this concern and date range before downloading.');return;}submit.disabled=true;const generation=epoch,account=owner(),controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);try{const options=await window.ConsumerClient.prepare({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,assessment_ids:[...$('briefSelection').querySelectorAll('input:checked')].map(n=>n.value),format:'pdf'})});if(!active(generation,account))return;const response=await fetch('/api/visit-brief',{...options,credentials:'same-origin',signal:controller.signal});if(!response.ok)throw Error((await response.json()).error||'Brief generation failed.');const blob=await response.blob();if(!active(generation,account))return;const url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='dermamatrix-visit-brief.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);message('briefStatus','Brief generated from the selected saved metadata. Original records are unchanged.');}catch(error){if(active(generation,account))message('briefStatus',`${error.message} No download was confirmed. Retry after previewing.`);}finally{clearTimeout(timeout);submit.disabled=false;}};
    const saved=el('details');saved.id='savedGuides';saved.innerHTML='<summary>Saved guides</summary><div id="savedGuideList"></div>';$('learnList').before(saved);
    const searchDialog=el('dialog',undefined,'consumer-dialog');searchDialog.id='unifiedSearchDialog';searchDialog.setAttribute('aria-labelledby','unifiedTitle');searchDialog.innerHTML='<h2 id="unifiedTitle">Search your workspace</h2><form id="unifiedSearchForm" class="continuity-form"><label>Search<input id="unifiedQuery" type="search" maxlength="120"></label><label>Category<select id="unifiedCategory"><option value="">All categories</option><option value="assessment">Assessments</option><option value="episode">Concerns</option><option value="routine">Routines</option><option value="checkin">Check-ins</option><option value="guide">Educational guides</option></select></label><button class="button primary" type="submit">Search</button></form><p id="unifiedStatus" role="status"></p><div id="unifiedResults"></div><button id="unifiedMore" type="button" class="button quiet" hidden>Load more results</button>';searchDialog.append(button('Close search',()=>searchDialog.close()));document.body.append(searchDialog);$('unifiedSearchForm').onsubmit=e=>{e.preventDefault();search(true);};$('unifiedMore').onclick=()=>search(false);
    const feedback=el('details');feedback.id='productFeedback';feedback.innerHTML='<summary>Share product feedback</summary><p>Collected in this local account. No monitored support channel is configured. Do not include health notes, identifying details or photographs.</p><form id="feedbackForm" class="continuity-form"><label>Problem category<select id="feedbackCategory"><option>Confusing screen</option><option>Save or loading problem</option><option>Accessibility</option><option>Other</option></select></label><label>Page<select id="feedbackPage"><option>Today</option><option>Check</option><option>Journey</option><option>Learn</option><option>Profile</option></select></label><label>Explanation (optional)<textarea id="feedbackNote" maxlength="2000"></textarea></label><p>Application version: consumer-continuity-v1. No account records or photos are attached automatically.</p><button class="button quiet" type="submit">Save local feedback</button><p id="feedbackStatus" role="status"></p></form>';$('profile-privacy').append(feedback);
    $('feedbackForm').onsubmit=async event=>{event.preventDefault();const submit=event.currentTarget.querySelector('[type=submit]');if(submit.disabled)return;submit.disabled=true;const generation=epoch,account=owner();try{const data=await write('/api/feedback',{category:$('feedbackCategory').value,page:$('feedbackPage').value,note:$('feedbackNote').value});if(active(generation,account)){$('feedbackForm').reset();message('feedbackStatus',data.message);}}catch(error){if(active(generation,account))message('feedbackStatus',`${error.message} Feedback was not confirmed; retry the same details.`);}finally{submit.disabled=false;}};
    const capture=el('details');capture.id='captureGuidance';capture.innerHTML='<summary>Prepare a useful photo</summary><p>Use bright, even light; keep the camera steady and the area in focus. Include the full area of concern without digital zoom, filters or glare. Choose a distance that keeps detail sharp, and check the preview before continuing. Rotate the device if that gives a clearer frame.</p><p>An ordinary camera photo and a dermoscopic image are different capture types. Select the actual type in Add context; do not label an ordinary photo as dermoscopy. A clear photo alone cannot establish medical or anatomical suitability.</p><p>If the camera is unavailable, choose an existing supported image from your gallery. If a photo is blurred, too dark or rejected, use Choose / replace image to retake it. The existing upload limits still apply; photos stay in this tab until submitted and source pixels are not retained by the assessment service.</p>';
    const gallery=button('Choose / replace image',()=>{$('imageInput').removeAttribute('capture');$('imageInput').click();});const camera=button('Use device camera',()=>{$('imageInput').setAttribute('capture','environment');$('imageInput').click();});capture.append(camera,gallery);$('dropZone').after(capture);const priorHelp=document.querySelector('.capture-help');if(priorHelp){const formats=priorHelp.querySelector('p');if(formats)capture.append(formats);priorHelp.remove();}
    page(document.querySelector('.page-active')?.id);
  }
  function page() {
    const enabled=Boolean(window.ConsumerClient?.enabled),account=signed();
    for(const id of ['episodeWorkspace','visitBrief','savedGuides','productFeedback','assessmentEpisodeField'])if($(id))$(id).hidden=!account;
    $('workspaceSearch').placeholder=enabled?'Search records and guides':'Search health guides';$('workspaceSearch').setAttribute('aria-label',$('workspaceSearch').placeholder);
    if($('checkinImage'))$('checkinImage').closest('label').hidden=enabled;
    if(account&&loadedOwner!==owner())load();
  }
  window.ContinuityUI={enabled:()=>Boolean(window.ConsumerClient?.enabled),retryKey(path,payload){const signature=JSON.stringify([path,payload]);if(!retryKeys.has(signature))retryKeys.set(signature,crypto.randomUUID());return retryKeys.get(signature);},assessmentEpisode:()=>signed()?$('assessmentEpisode')?.value||'':'',page,changed,correctEvent,linkAssessment,reviewCheckin,guide,explain,search:openSearch,
    routineSelected(id){$('checkinEpisode').value=links['routine:'+id]?.episode_id||'';},
    scheduleLoaded(link){reminderVersion++;message('reminderPreview','');scheduleLink=link;$('scheduleEpisode').value=link.episode_id||'';},scheduleLink:()=>({episode_id:$('scheduleEpisode')?.value||'',link_version:scheduleLink.version||0}),
    progress(){page();renderCheckinHistory();},
    clear(){epoch++;loadVersion++;reminderVersion++;loadedOwner='';episodes=[];links={};bookmarks=[];loading=null;scheduleLink={};briefSignature='';searchVersion++;retryKeys.clear();searchCursor=null;$('continuityDialog')?.close();$('unifiedSearchDialog')?.close();
      for(const id of ['episodeForm','visitBriefForm','feedbackForm','unifiedSearchForm'])$(id)?.reset();
      for(const id of ['assessmentEpisode','checkinEpisode','journeyEpisodeId','scheduleEpisode','briefEpisode'])if($(id))choices($(id));
      for(const id of ['unifiedResults','savedGuideList','checkinCorrections','briefSelection','briefStatus','continuityStatus','feedbackStatus','reminderPreview','unifiedStatus'])$(id)?.replaceChildren();$('continuityDialog')?.replaceChildren();}
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
