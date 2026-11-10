/* Connected consumer flows. All private truth comes from owner-scoped APIs.
 * Drafts and retry identifiers live only in this tab and clear on account change. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const el = (tag, text, cls) => {const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const button = (text, fn, cls='button quiet') => {const n=el('button',text,cls);n.type='button';n.onclick=fn;return n;};
  const signed = () => Boolean(window.ConsumerClient?.enabled && state.profile?.patient_id);
  const owner = () => state.profile?.patient_id || '';
  let epoch=0, loadedOwner='', episodes=[], links={}, bookmarks=[], loading=null, scheduleLink={}, searchCursor=null, searchQuery='', searchCategory='',briefSignature='',searchVersion=0,loadVersion=0,reminderVersion=0,briefVersion=0,dialogVersion=0;
  let concernRequest = null;
  let briefDownload = null;
  const retryKeys=new Map();
  const active = (version, account) => epoch===version && owner()===account;
  const message = (id, text) => {if($(id))$(id).textContent=text;};
  async function write(path, payload, method='POST') {
    const version=epoch,account=owner();
    const signature=JSON.stringify([path,payload,method]);
    if(!retryKeys.has(signature))retryKeys.set(signature,crypto.randomUUID());
    return requestJSON(path,{method,headers:{'Content-Type':'application/json','Idempotency-Key':retryKeys.get(signature)},body:method==='DELETE'?undefined:JSON.stringify(payload),ownerGuard:()=>active(version,account)});
  }
  function choices(select, selected='', empty='No concern selected', items=episodes) {
    select.replaceChildren(new Option(empty,''));
    for(const item of items)select.add(new Option(`${item.label} · ${item.body_area}`,item.episode_id));
    select.value=items.some(item=>item.episode_id===selected)?selected:'';
  }
  function pick(id, title) {const label=el('label',title),select=el('select');select.id=id;label.append(select);choices(select);return label;}
  function assessmentAreaChanged() {
    const select = $('assessmentEpisode');
    if (!select) return;
    const compatible = episodes.filter(episode => episode.area === state.area || episode.area === 'General');
    choices(select, select.value, 'No concern selected', compatible);
  }
  async function load(force=false) {
    if(!signed())return;
    if(loading&&!force)return loading;
    const version=epoch,account=owner(),requestVersion=++loadVersion;
    const flight=(async()=>{try{
      const [ep,associations,saved]=await Promise.all([requestJSON('/api/episodes'),requestJSON('/api/episode-links'),requestJSON('/api/bookmarks')]);
      if(!active(version,account)||requestVersion!==loadVersion)return;
      episodes=ep.episodes;links=associations.links;bookmarks=saved.bookmarks;loadedOwner=account;
      for(const id of ['checkinEpisode','journeyEpisodeId','scheduleEpisode','briefEpisode','searchConcern'])if($(id))choices($(id),$(id).value,['journeyEpisodeId','searchConcern'].includes(id)?'All concerns':'No concern selected');
      assessmentAreaChanged();
      if($('episodeBody')&&!$('episodeBody').options.length)for(const value of ep.body_areas)$('episodeBody').add(new Option(value,value));
      renderBookmarks();renderCheckinHistory();
    }catch(error){if(active(version,account)&&requestVersion===loadVersion)message('continuityStatus',`${error.message} Your current input remains in this tab. Retry by reopening Journey.`);}
    finally{if(loading===flight)loading=null;}})();loading=flight;return flight;
  }
  async function changed() {
    const version=epoch,account=owner();if(!signed())return;
    invalidateBrief('Your records changed. Preview again before downloading; your dates and questions are preserved.');
    await load(true);if(!active(version,account))return;
    await loadProgress({force:true});if(!active(version,account))return;
    await window.EngagementUI?.refresh();
    if (!active(version, account)) return;
    refreshConcernOnJourney(true);
    window.ProductUpgrade?.recordsChanged();
    if($('unifiedSearchDialog')?.open)await search(true);
  }
  const chosenConcern = () => episodes.find(episode => episode.episode_id === $('journeyEpisodeId')?.value);
  const areaName = area => ({ Hair: 'Hair & scalp', Sweat: 'Sweating' })[area] || area;
  const briefDate = value => new Date(`${value}T12:00:00Z`).toLocaleDateString('en-GB', { dateStyle: 'medium', timeZone: 'UTC' });

  function clearConcernOverview() {
    concernRequest?.controller.abort();
    concernRequest = null;
    if (!$('concernOverview')) return;
    $('concernOverview').hidden = true;
    $('concernFacts').replaceChildren();
    $('concernFacts').hidden = true;
    $('retryConcernOverview').hidden = true;
    message('concernOverviewStatus', '');
    message('concernTitle', '');
    message('concernMeta', '');
  }

  function renderConcernFacts(overview) {
    const { latest_assessment: assessment, latest_checkin: checkin, linked_routine_count: routines } = overview;
    const facts = $('concernFacts');
    const fact = (label, value, action) => {
      const row = el('div');
      const description = el('dd', value);
      if (action) description.append(action);
      row.append(el('dt', label), description);
      return row;
    };
    const assessmentDate = assessment ? new Date(assessment.created_at).toLocaleDateString('en-GB', { dateStyle: 'medium' }) : '';
    const assessmentAction = assessment && !assessment.unavailable
      ? button('Open latest result', () => showSavedReport(assessment.assessment_id), 'text-button') : null;
    const assessmentLabel = assessment
      ? `${assessmentDate} · ${areaName(assessment.area)}${assessment.unavailable ? ' · Record unavailable' : ''}` : 'No linked results yet';
    const checkinLabel = checkin
      ? `${readableStatus(checkin.reported_trend)} · ${briefDate(checkin.checkin_date)}` : 'No linked check-ins yet';
    facts.replaceChildren(fact('Latest saved result', assessmentLabel, assessmentAction), fact('Latest self-reported check-in', checkinLabel), fact('Linked routines', String(routines)));
    facts.hidden = false;
  }

  async function refreshConcernOverview(force = false) {
    if (!$('concernOverview')) return;
    const concern = signed() && chosenConcern();
    if (!concern) { clearConcernOverview(); return; }
    const id = concern.episode_id;
    const workspaceVersion = state.workspaceVersion;
    if (!force && concernRequest?.id === id && concernRequest.workspaceVersion === workspaceVersion) return;
    clearConcernOverview();
    const version = epoch, account = owner();
    const request = { id, workspaceVersion, controller: new AbortController() };
    concernRequest = request;
    const current = () => concernRequest === request && active(version, account)
      && state.workspaceVersion === workspaceVersion && $('journeyEpisodeId').value === id;
    message('concernTitle', concern.label);
    message('concernMeta', `${areaName(concern.area)} · ${concern.body_area}`);
    message('concernOverviewStatus', 'Loading saved activity…');
    $('concernOverview').hidden = false;
    try {
      const { overview } = await requestJSON(`/api/episodes/${encodeURIComponent(id)}/overview`, {
        signal: request.controller.signal, ownerGuard: current
      });
      if (!current()) return;
      if (overview?.episode_id !== id || !Number.isInteger(overview.linked_routine_count)) throw Error('Incomplete concern activity.');
      renderConcernFacts(overview);
      message('concernOverviewStatus', '');
    } catch {
      if (current()) {
        message('concernOverviewStatus', 'Saved activity could not be loaded.');
        $('retryConcernOverview').hidden = false;
      }
    } finally {
      if (concernRequest === request) concernRequest = null;
    }
  }

  function refreshConcernOnJourney(force = false) {
    if (document.querySelector('.page-active')?.id === 'progress') void refreshConcernOverview(force);
  }

  function filterJourneyConcern(id) {
    $('journeyEpisodeId').value = id;
    window.EngagementUI.filterEpisode(id);
    void refreshConcernOverview();
  }
  function dialog(title, content, save, label='Save correction', trigger) {
    const opener=trigger||document.activeElement,d=$('continuityDialog'),instance=++dialogVersion;window.DraftUX?.forget(d.firstChild);d.replaceChildren();const form=el('form');form.append(el('h2',title));
    const heading=form.firstChild;heading.id='continuityDialogTitle';d.setAttribute('aria-labelledby',heading.id);
    heading.tabIndex=-1;
    form.append(content);const status=el('p');status.id='continuityDialogStatus';status.setAttribute('role','status');form.append(status);
    const actions=el('div',undefined,'consumer-actions'),submit=el('button',label,'button primary');submit.type='submit';
    actions.append(button('Back',()=>{if(submit.disabled||!window.DraftUX||window.DraftUX.allowDiscard(form))d.close();}),submit);form.append(actions);d.append(form);
    window.DraftUX?.clean(form);
    d.oncancel=event=>{if(!submit.disabled&&window.DraftUX&&!window.DraftUX.allowDiscard(form))event.preventDefault();};
    const version=epoch,account=owner();
    const sameDialog=()=>active(version,account)&&dialogVersion===instance&&d.firstChild===form;
    const restoreFocus=()=>{if(!sameDialog()||d.open)return;const focus=opener?.isConnected?opener:(document.querySelector('.page-active [role=tab][aria-selected=true]')||document.querySelector('.page-active h1'));if(focus){if(focus.tagName==='H1')focus.tabIndex=-1;focus.focus({preventScroll:true});}};
    let saved=false;
    d.onclose=()=>{if(!d.open){window.DraftUX?.forget(form);if(!saved)restoreFocus();}};
    form.onsubmit=async event=>{
      event.preventDefault();if(submit.disabled||!sameDialog()||!d.open)return;
      const controls=[...form.querySelectorAll('input,select,textarea')].map(input=>[input,input.disabled]);
      controls.forEach(([input])=>{input.disabled=true;});
      submit.disabled=true;status.textContent='Saving… You can go back, but this request may already be saved.';
      try{
        await save();if(!active(version,account))return;
        const wasOpen=sameDialog()&&d.open;saved=true;if(wasOpen)d.close();
        await changed();
        if(wasOpen&&sameDialog()&&!d.open){restoreFocus();toast('Saved. Your original records are preserved.');}
      }catch(error){if(sameDialog()&&d.open)status.textContent=`${error.message} This attempt was not confirmed. Your input remains here; retry the same details or reload if another tab changed the record.`;}
      finally{controls.forEach(([input,disabled])=>{input.disabled=disabled;});submit.disabled=false;}
    };
    d.showModal();d.scrollTop=0;const initialFocus=document.activeElement;
    requestAnimationFrame(()=>{if(sameDialog()&&d.open&&document.activeElement===initialFocus)heading.focus({preventScroll:true});});
  }
  function correctEvent(id, revision, title, currentAction = 'pending') {
    const content=el('div');content.append(el('p',title),el('p','The original action remains in history. Choose the effective status now.'));
    const label=el('label','Correct status'),select=el('select');select.id='correctionAction';
    for(const [value,text] of [['pending','Not recorded (undo)'],['completed','Completed — self-reported'],['skipped','Skipped — self-reported']])select.add(new Option(text,value));select.value=currentAction;label.append(select);content.append(label);
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
  function correctCheckin(item, trigger) {
    const content=el('div');content.append(el('p','This corrects your self-report, not an image measurement. The original remains available in your account export.'));
    const fields=checkinFields(content,item),remove=el('label','Remove this mistaken check-in from current tracking'),check=el('input');check.type='checkbox';remove.prepend(check);content.append(remove);
    dialog('Correct check-in',content,()=>write('/api/corrections/checkin/'+encodeURIComponent(item.checkin_id),check.checked?{revision:item.revision||0,voided:true}:{revision:item.revision||0,reported_trend:fields.trend.value,discomfort:fields.discomfort.value,change:fields.change.value,checkin_date:fields.date.value,note:fields.note.value}),'Save correction',trigger);
  }
  function renderCheckinHistory() {
    const list=$('checkinCorrections');if(!list)return;list.hidden=!signed();if($('progressHistory'))$('progressHistory').hidden=signed();if(!signed())return;list.replaceChildren();
    for(const item of state.checkins||[]){const row=el('article',undefined,'continuity-row');row.append(el('strong',item.voided?'Removed from current tracking':`${readableStatus(item.reported_trend)} — self-reported`),el('p',`${item.checkin_date} · ${item.routine_name}`));
      if(item.note)row.append(el('p',item.note));const link=links['checkin:'+item.checkin_id];if(link?.label)row.append(el('p','Concern: '+link.label));
      row.append(button('Correct check-in',event=>correctCheckin(item,event.currentTarget)));
      if(item.corrections?.length){const details=el('details');details.append(el('summary','Correction history'),el('p',`Original: ${item.original.reported_trend} · ${item.original.checkin_date}`));for(const revision of item.corrections)details.append(el('p',`${new Date(revision.created_at).toLocaleString()} · ${revision.data.effective.voided?'Removed from tracking':revision.data.effective.reported_trend} · account actor ${revision.data.actor_id}`));row.append(details);}list.append(row);
    }
    if(!list.children.length)list.append(el('p','No saved check-ins. Choose a routine above to record your first update.'));
    // One history list owns the correction actions; avoid two competing lists.
    if($('progressHistory'))$('progressHistory').hidden=true;
  }
  function checkinInput() {return{routine_id:$('checkinRoutine').value,checkin_date:$('checkinDate').value,reported_trend:$('checkinTrend').value,discomfort:$('checkinDiscomfort').value,change:$('checkinChange').value,note:$('checkinNote').value,episode_id:$('checkinEpisode').value};}
  async function reviewCheckin() {
    const form=$('checkinForm');if(!form.reportValidity())return;
    const payload=checkinInput(),signature=JSON.stringify(payload),submittedDraft=window.DraftUX?.snapshot(form);
    const content=el('div');const routine=state.routines.find(r=>r.routine_id===payload.routine_id);const episode=episodes.find(r=>r.episode_id===payload.episode_id);
    const summary=el('dl',undefined,'review-summary');
    for(const [name,value] of [['Routine',routine?.routine_name||'Choose a routine'],['Date',payload.checkin_date],['Trend',`${readableStatus(payload.reported_trend)} — self-reported`],['Discomfort',$('checkinDiscomfort').selectedOptions[0].textContent],['Recent change',$('checkinChange').selectedOptions[0].textContent],['Concern',episode?.label||'Unassigned'],...(payload.note?[['Note',payload.note]]:[])])summary.append(el('dt',name),el('dd',value));
    content.append(summary,el('p','Confirm this is the right concern. No image is used to measure healing or saved with this check-in.'));
    const version=epoch,account=owner();
    dialog('Review your check-in',content,async()=>{await write('/api/progress-checkins',payload);if(!active(version,account))return;if(JSON.stringify(checkinInput())===signature){form.reset();$('checkinRoutine').dataset.confirmed='';$('checkinDate').value=currentDate();window.DraftUX?.clean(form);}else window.DraftUX?.clean(form,submittedDraft);},'Save check-in',form.querySelector('[type=submit]'));
  }
  function briefInput() {return{episode_id:$('briefEpisode').value,start:$('briefStart').value,end:$('briefEnd').value,questions:$('briefQuestions').value};}
  function resetBriefDates() {
    if(!$('briefStart')||!$('briefEnd'))return;
    const end=currentDate(),start=new Date(end+'T12:00:00');start.setDate(start.getDate()-30);
    $('briefEnd').value=end;$('briefStart').value=`${start.getFullYear()}-${String(start.getMonth()+1).padStart(2,'0')}-${String(start.getDate()).padStart(2,'0')}`;
  }
  function invalidateBrief(text = 'Preview the records for your chosen concern and dates.') {
    briefVersion++;
    briefSignature = '';
    briefDownload?.abort();
    briefDownload = null;
    $('briefSelection')?.replaceChildren();
    if ($('briefPreview')) $('briefPreview').hidden = true;
    for (const id of ['briefScope', 'briefSelectionSummary', 'briefIncludes', 'briefLimits']) message(id, '');
    if ($('downloadBrief')) $('downloadBrief').disabled = true;
    if ($('previewBrief')) {
      $('previewBrief').disabled = false;
      $('previewBrief').removeAttribute('aria-busy');
    }
    message('briefStatus', text);
  }

  function briefChoices() {
    return [...$('briefSelection').querySelectorAll('input')];
  }

  function updateBriefCount() {
    const choices = briefChoices();
    message('briefSelectionSummary', `${choices.filter(input => input.checked).length} of ${choices.length} assessments selected`);
  }

  function prepareConcernBrief() {
    const concern = chosenConcern();
    if (!concern) return;
    const picker = $('briefEpisode');
    if (picker.value !== concern.episode_id) {
      picker.value = concern.episode_id;
      invalidateBrief('Concern changed. Review your dates and questions before previewing.');
    }
    $('visitBrief').open = true;
    picker.focus();
  }

  async function previewBrief() {
    const control = $('previewBrief');
    if (control.disabled || !$('visitBriefForm').reportValidity()) return;
    invalidateBrief('Loading saved records…');
    const generation = epoch, account = owner(), workspaceVersion = state.workspaceVersion;
    const requestVersion = briefVersion, payload = briefInput(), signature = JSON.stringify(payload);
    const samePreview = () => active(generation, account) && briefVersion === requestVersion;
    const current = () => samePreview() && state.workspaceVersion === workspaceVersion && JSON.stringify(briefInput()) === signature;
    control.disabled = true;
    control.setAttribute('aria-busy', 'true');
    try {
      const { brief } = await write('/api/visit-brief', payload);
      if (!current()) return;
      const box = $('briefSelection');
      brief.assessments.forEach((row, index) => {
        const date = new Date(row.created_at).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'medium', timeZone: 'UTC' });
        const title = row.unavailable ? 'Record unavailable'
          : row.summary?.assessment_result?.consumer?.primary_result?.title || row.summary?.screening?.title || 'Saved assessment';
        const input = el('input');
        input.type = 'checkbox';
        input.checked = true;
        input.value = row.assessment_id;
        const label = el('label');
        const detail = el('span');
        detail.append(el('strong', `${index + 1}. ${title}`), el('small', `${areaName(row.area)} · ${date} UTC`));
        label.append(input, detail);
        box.append(label);
      });
      const { checkins, routines, routine_actions: actions } = brief.counts;
      const count = (total, singular, plural) => `${total} ${total === 1 ? singular : plural}`;
      message('briefScope', `${brief.episode.label} · ${briefDate(brief.start)} – ${briefDate(brief.end)}`);
      message('briefIncludes', `Also included: ${count(checkins, 'self-reported check-in', 'self-reported check-ins')}, ${count(routines, 'routine plan', 'routine plans')} and ${count(actions, 'routine action', 'routine actions')}. These sections use saved records at download time.`);
      message('briefLimits', brief.photo_notice);
      updateBriefCount();
      briefSignature = signature;
      $('briefPreview').hidden = false;
      $('downloadBrief').disabled = false;
      message('briefStatus', brief.assessments.length ? 'Uncheck any assessment you want to leave out.' : 'No assessments match this concern and date range.');
    } catch (error) {
      if (current()) message('briefStatus', `${error.message} Preview again to retry.`);
    } finally {
      if (samePreview()) {
        control.disabled = false;
        control.removeAttribute('aria-busy');
        if (state.workspaceVersion !== workspaceVersion) message('briefStatus', 'Preview the records again after your session resumes.');
      }
    }
  }

  async function downloadVisitBrief(event) {
    event.preventDefault();
    const submit = $('downloadBrief'), payload = briefInput();
    if (submit.disabled || briefDownload || briefSignature !== JSON.stringify(payload)) return;
    const generation = epoch, account = owner(), workspaceVersion = state.workspaceVersion, requestVersion = briefVersion;
    const controller = new AbortController();
    const current = () => briefDownload === controller && active(generation, account)
      && state.workspaceVersion === workspaceVersion && briefVersion === requestVersion;
    briefDownload = controller;
    submit.disabled = true;
    const choices = briefChoices();
    const assessment_ids = choices.filter(input => input.checked).map(input => input.value);
    for (const input of choices) input.disabled = true;
    message('briefStatus', 'Preparing your PDF…');
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetchForWorkspace('/api/visit-brief', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, assessment_ids, format: 'pdf' }),
        credentials: 'same-origin', signal: controller.signal, ownerGuard: current
      });
      if (!response.ok) throw Error((await response.json().catch(() => ({}))).error || 'Brief generation failed.');
      if (!response.headers.get('content-type')?.startsWith('application/pdf')) throw Error('The server did not return a PDF.');
      const blob = await response.blob();
      if (!current()) return;
      const url = URL.createObjectURL(blob), link = el('a');
      link.href = url;
      link.download = 'dermamatrix-visit-brief.pdf';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      message('briefStatus', 'PDF download started.');
    } catch (error) {
      if (current()) message('briefStatus', controller.signal.aborted
        ? 'The PDF request timed out. Retry the download.'
        : `${error.message} Preview again or retry the download.`);
    } finally {
      clearTimeout(timeout);
      if (briefDownload === controller) {
        if (!current()) invalidateBrief();
        else {
          briefDownload = null;
          submit.disabled = false;
          for (const input of choices) input.disabled = false;
        }
      }
    }
  }
  function linkAssessment(result) {
    const content=el('div');content.append(el('p','Choose explicitly. Matching labels never merge assessments automatically. Existing labels and original findings remain unchanged.'));
    const choice=pick('linkConcernPicker','Concern');content.append(choice);choice.querySelector('select').value=result.episode_link?.episode_id||'';
    dialog('Link saved result',content,()=>write('/api/episode-links/assessment/'+encodeURIComponent(result.assessment_id),{episode_id:choice.querySelector('select').value,version:result.episode_link?.version||0},'PUT'),'Save concern link');
  }
  function followup() {
    const episode = chosenConcern();
    if (!episode) return;
    if (episode.area === 'General') {
      if (state.assessmentInFlight) { toast('Wait for your current check to finish before starting a follow-up.'); return; }
      state.areaSelected = false;
      showPage('home');
    } else if (!startAreaAssessment(episode.area)) return;
    $('assessmentEpisode').value = episode.episode_id;
    if (episode.area !== 'General') $('assessmentEpisode').focus();
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
    const control=button('Save guide',()=>{});control.id='guideBookmark';control.dataset.guide=topic.id;updateGuideBookmark(control,topic.id);($('learnDetail').querySelector('.guide-toolbar')||$('learnDetail')).append(control);
  }
  function returnSearch() {
    closeResult();
    $('recordReadDialog').close();
    $('unifiedSearchDialog').showModal();
    $('unifiedQuery').focus();
  }
  async function viewCheckin(id,{fromSearch=false}={}) {
    invalidateSavedReportOpen();
    const requestVersion=state.savedReportRequestVersion;
    const generation=epoch,account=owner(),workspace=state.workspaceVersion;
    const current=()=>active(generation,account)&&workspace===state.workspaceVersion&&requestVersion===state.savedReportRequestVersion;
    try {
      const {checkin}=await requestJSON('/api/checkins/'+encodeURIComponent(id));
      if(!current())return;
      const reader=$('recordReadDialog'),body=$('recordReadContent');
      body.replaceChildren(el('h2','Saved check-in'),el('p',checkin.checkin_date+' · '+readableStatus(checkin.reported_trend)+' — self-reported'),
        el('p',checkin.note||'No note supplied.'),el('p','Correction revision '+(checkin.revision||0)));
      if(checkin.voided)body.append(el('p','Removed from current tracking.'));
      for(const revision of checkin.corrections||[])body.append(el('p','Corrected '+new Date(revision.created_at).toLocaleString()+' · '+Object.entries(revision.data.effective).map(([key,value])=>readableStatus(key)+': '+String(value)).join(' · ')));
      body.append(button('Correct this check-in',()=>{reader.close();correctCheckin(checkin);}));
      if(fromSearch)body.append(button('Back to search',returnSearch));
      body.append(button('Close',()=>reader.close()));
      reader.showModal();
      body.querySelector('h2').tabIndex=-1;body.querySelector('h2').focus();
    }catch(error){if(current())toast(error.message);}
  }
  function searchScope() {
    const params=new URLSearchParams({q:$('unifiedQuery').value.trim(),category:$('unifiedCategory').value});
    for(const [key,id]of [['area','searchArea'],['episode_id','searchConcern'],['start','searchStart'],['end','searchEnd']])if($(id)?.value)params.set(key,$(id).value);
    return params.toString();
  }
  async function search(reset=true) {
    const generation=epoch,account=owner(),workspace=state.workspaceVersion,requestVersion=++searchVersion,scope=searchScope();
    const current=()=>active(generation,account)&&workspace===state.workspaceVersion&&requestVersion===searchVersion&&searchScope()===scope;
    if(!$('unifiedSearchForm').reportValidity())return;
    if(reset){searchCursor=null;searchQuery=scope;$('unifiedResults').replaceChildren();}
    else if(scope!==searchQuery)return;
    const params=new URLSearchParams(scope);if(searchCursor)params.set('cursor',searchCursor);
    $('unifiedMore').disabled=true;message('unifiedStatus','Searching…');
    try {
      const data=await requestJSON('/api/search?'+params,{ownerGuard:current});
      if(!current())return;
      for(const item of data.results) {
        const row=el('article',undefined,'continuity-row');
        const categoryLabel=item.category==='checkin'?'check-in':item.category;
        const saved=item.created_at?'Saved '+new Date(item.created_at).toLocaleString('en-GB',{timeZone:'UTC'})+' UTC · Record '+item.id.slice(-8):'';
        const meta=[categoryLabel,item.bookmarked?'Saved guide':'',item.recorded_date||'',item.area||'',saved,item.revision?'Corrected '+item.revision+' times':''].filter(Boolean).join(' · ');
        row.append(el('small',meta),el('h3',item.title),el('p',item.detail||''),button('Open '+categoryLabel,async()=>{
          try {
            if(item.category==='guide'){$('unifiedSearchDialog').close();showPage('learn');await window.EngagementUI.openGuide(item.id);return;}
            if(item.category==='assessment') {
              $('unifiedSearchDialog').close();await showSavedReport(item.id);
              if(active(generation,account)&&workspace===state.workspaceVersion&&state.assessmentId===item.id&&$('resultModal').classList.contains('show'))$('returnWorkspaceSearch').hidden=false;
              return;
            }
            if(item.category==='checkin'){$('unifiedSearchDialog').close();await viewCheckin(item.id,{fromSearch:true});return;}
            if(item.category==='routine') {
              const data=await requestJSON('/api/routine-schedules/'+encodeURIComponent(item.id));
              if(!current()||!$('unifiedSearchDialog').open)return;
              $('unifiedSearchDialog').close();
              const body=$('recordReadContent'),reader=$('recordReadDialog');
              body.replaceChildren(el('h2',item.title),el('p',readableStatus(data.schedule?.status||'active')+' · '+(data.schedule?.timezone||'No schedule yet')));
              for(const step of data.schedule?.steps||[])body.append(el('p',step));
              body.append(button('Edit this routine',async()=>{reader.close();showPage('progress');window.WorkspaceUI.reveal('routines');await window.EngagementUI.configureRoutine(item.id);}),button('Back to search',returnSearch),button('Close',()=>reader.close()));
              reader.showModal();return;
            }
            $('unifiedSearchDialog').close();showPage('progress');window.WorkspaceUI.reveal('results');filterJourneyConcern(item.id);
          } catch(error) {if(active(generation,account))message('unifiedStatus',error.message+' Reopen search to retry.');}
        }));
        $('unifiedResults').append(row);
      }
      searchCursor=data.next_cursor;$('unifiedMore').hidden=!searchCursor;
      message('unifiedStatus',data.results.length?$('unifiedResults').children.length+' results shown. '+(data.private_results?'Private records belong to this account.':'Sign in to search private records.'):'No matches. Try different words or clear filters.');
    }catch(error){if(current())message('unifiedStatus',error.message+' Search again to refresh.');}
    finally{if(active(generation,account)&&requestVersion===searchVersion)$('unifiedMore').disabled=false;}
  }
  function openSearch(query) {
    if(query!==undefined)$('unifiedQuery').value=query;
    $('unifiedSearchDialog').showModal();$('unifiedQuery').focus();search(true);
  }
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
    window.WorkspaceUI?.result(root);
    if(signed()&&state.resultPersistence==='mysql'){const version=epoch,account=owner();try{const associations=await requestJSON('/api/episode-links');if(!active(version,account)||!block.isConnected)return;links=associations.links;const link=links['assessment:'+(state.assessmentId||'')];block.prepend(el('p',link?.label?'Concern: '+link.label+' · '+link.body_area:'No concern linked. You can organise this result in Journey.'));const effective=contextualProgress(data,link);if(effective.status==='CONCERN_SCOPE_CHANGED'){block.append(el('p',effective.summary));const old=root.querySelector('[data-result-action=progress]')?.parentElement?.querySelector('p:not(.eyebrow)');if(old)old.textContent=effective.summary;}}catch{if(block.isConnected&&active(version,account))block.prepend(el('p','Concern context could not be loaded. The saved assessment evidence below remains available.'));}}
  }
  const episodeInput=()=>({label:$('episodeLabel').value,area:$('episodeArea').value,body_area:$('episodeBody').value});
  async function createEpisode(event) {
    event.preventDefault();const form=event.currentTarget,submit=form.querySelector('[type=submit]');if(submit.disabled)return;
    const version=epoch,account=owner(),workspaceVersion=state.workspaceVersion,payload=episodeInput(),signature=JSON.stringify(payload),draft=window.DraftUX?.snapshot(form);
    const current=()=>active(version,account)&&state.workspaceVersion===workspaceVersion;
    submit.disabled=true;
    try {
      const data=await write('/api/episodes',payload);if(!current())return;
      await load(true);if(!current())return;
      const unchanged=JSON.stringify(episodeInput())===signature;
      if (unchanged) {
        filterJourneyConcern(data.episode_id);
        form.reset();
        window.DraftUX?.clean(form);
        $('episodeWorkspace').querySelector('details').open = false;
        $('journeyEpisodeId').focus();
      }
      else window.DraftUX?.clean(form,draft);
      message('continuityStatus',unchanged?'Concern created. Choose it for a new check or link an existing result.':'Submitted concern created. Your newer input is still here and has not been saved.');
    }catch(error){if(current())message('continuityStatus',`${error.message} Creation was not confirmed. Your input remains here; retry the same details.`);}
    finally{if(active(version,account))submit.disabled=false;}
  }
  function install() {
    if($('continuityDialog'))return;
    const mobileSearch=button('Search',()=>openSearch(''));mobileSearch.id='mobileWorkspaceSearch';mobileSearch.setAttribute('aria-label','Search records and guides');$('themeToggle').before(mobileSearch);
    const d=el('dialog',undefined,'consumer-dialog');d.id='continuityDialog';document.body.append(d);
    const reader=el('dialog',undefined,'consumer-dialog');reader.id='recordReadDialog';reader.setAttribute('aria-label','Saved record details');
    const readBody=el('div');readBody.id='recordReadContent';reader.append(readBody);document.body.append(reader);
    const backSearch=button('Back to search results',returnSearch,'text-button');backSearch.id='returnWorkspaceSearch';backSearch.hidden=true;
    document.querySelector('#resultModal .modal-card').prepend(backSearch);

    const assessment = pick('assessmentEpisode', 'Saved concern (optional)');
    assessment.id = 'assessmentEpisodeField';
    assessment.append(el('small', 'Choose a matching saved concern to link this check.'));
    document.querySelector('#screen .area-choice').after(assessment);
    const workspace = el('section', undefined, 'consumer-panel');
    workspace.id = 'episodeWorkspace';
    workspace.setAttribute('aria-labelledby', 'episodeWorkspaceTitle');
    workspace.innerHTML = `
      <div class="concern-controls">
        <div>
          <h2 id="episodeWorkspaceTitle">Saved concerns</h2>
          <p>Choose a concern to review its linked activity or start a follow-up.</p>
        </div>
      </div>
      <section id="concernOverview" class="concern-overview" aria-labelledby="concernTitle" hidden>
        <div class="concern-overview-head">
          <div>
            <h3 id="concernTitle" tabindex="-1"></h3>
            <p id="concernMeta"></p>
          </div>
          <div class="concern-actions">
            <button id="startConcernFollowup" class="button primary" type="button">Start follow-up</button>
            <button id="prepareConcernBrief" class="button quiet" type="button">Prepare visit brief</button>
          </div>
        </div>
        <dl id="concernFacts" hidden></dl>
        <p id="concernOverviewStatus" role="status"></p>
        <button id="retryConcernOverview" class="button quiet" type="button" hidden>Retry saved activity</button>
      </section>
      <details>
        <summary>Create a concern</summary>
        <form id="episodeForm" class="continuity-form">
          <label>Concern label<input id="episodeLabel" required maxlength="120" placeholder="A label you recognise"></label>
          <label>Category<select id="episodeArea"><option>Skin</option><option>Hair</option><option>Nails</option><option>Sweat</option><option>General</option></select></label>
          <label>Body area<select id="episodeBody"></select></label>
          <button class="button primary" type="submit">Create concern</button>
        </form>
      </details>
      <p id="continuityStatus" role="status"></p>`;
    $('completeJourney').before(workspace);
    const picker = pick('journeyEpisodeId', 'Filter results by concern');
    workspace.querySelector('.concern-controls').append(picker);
    $('journeyEpisodeId').onchange = event => filterJourneyConcern(event.target.value);
    $('startConcernFollowup').onclick = followup;
    $('prepareConcernBrief').onclick = prepareConcernBrief;
    $('retryConcernOverview').onclick = () => {
      void refreshConcernOverview();
      $('concernTitle').focus();
    };
    $('episodeForm').onsubmit=createEpisode;window.DraftUX?.clean($('episodeForm'));
    $('scheduleEditor').prepend(pick('scheduleEpisode','Linked concern (optional)'));
    const preview=el('div');preview.append(button('Preview reminder schedule',previewReminder));const note=el('p');note.id='reminderPreview';note.setAttribute('role','status');preview.append(note);$('scheduleEditor').append(preview);$('scheduleEditor').addEventListener('input',()=>{reminderVersion++;message('reminderPreview','Schedule input changed. Preview again to calculate the next occurrence. No reminder was queued.');});
    $('checkinRoutine').closest('label').after(pick('checkinEpisode','Concern (confirm before saving)'));
    $('checkinRoutine').addEventListener('change',()=>selectCheckinRoutine($('checkinRoutine').value));
    const history=el('section');history.id='checkinCorrections';$('progressHistory')?.after(history);
    const brief = el('details', undefined, 'consumer-panel');
    brief.id = 'visitBrief';
    brief.innerHTML = `
      <summary>Prepare a clinician-visit brief</summary>
      <form id="visitBriefForm" class="continuity-form">
        <div class="brief-fields">
          <h3>Choose the scope</h3>
          <div class="brief-dates">
            <label>From<input id="briefStart" type="date" required></label>
            <label>To<input id="briefEnd" type="date" required></label>
          </div>
          <label>Questions to discuss (optional)<textarea id="briefQuestions" maxlength="3000"></textarea></label>
          <p class="brief-note">Assessment dates use UTC save times. Check-ins and routine actions use their recorded local dates.</p>
          <button type="button" class="button quiet" id="previewBrief">Preview selected records</button>
        </div>
        <section class="brief-review" aria-labelledby="briefReviewTitle">
          <h3 id="briefReviewTitle">Review the PDF contents</h3>
          <p id="briefStatus" role="status"></p>
          <div id="briefPreview" hidden>
            <p id="briefScope"></p>
            <p id="briefSelectionSummary" role="status"></p>
            <div id="briefSelection"></div>
            <p id="briefIncludes"></p>
            <p id="briefLimits" class="brief-note"></p>
          </div>
          <button id="downloadBrief" class="button primary" type="submit" aria-describedby="briefStatus" disabled>Download visit brief PDF</button>
        </section>
      </form>`;
    $('completeJourney').after(brief);
    brief.querySelector('h3').after(pick('briefEpisode', 'Concern'));
    $('briefEpisode').required = true;
    if ($('historyExport')) $('historyExport').querySelector('summary').textContent = 'Download recent history (all concerns)';
    resetBriefDates();
    invalidateBrief();
    $('previewBrief').onclick = previewBrief;
    $('visitBriefForm').addEventListener('input', event => {
      if (event.target.closest('#briefSelection')) updateBriefCount();
      else invalidateBrief('Scope or questions changed. Preview the records again before downloading.');
    });
    $('visitBriefForm').onsubmit = downloadVisitBrief;
    const saved=el('details');saved.id='savedGuides';saved.innerHTML='<summary>Saved guides</summary><div id="savedGuideList"></div>';$('learnList').before(saved);
    const searchDialog=el('dialog',undefined,'consumer-dialog');searchDialog.id='unifiedSearchDialog';searchDialog.setAttribute('aria-labelledby','unifiedTitle');searchDialog.innerHTML='<h2 id="unifiedTitle">Search your workspace</h2><form id="unifiedSearchForm" class="continuity-form"><label>Search<input id="unifiedQuery" type="search" maxlength="120"></label><label>Category<select id="unifiedCategory"><option value="">All categories</option><option value="assessment">Assessments</option><option value="episode">Concerns</option><option value="routine">Routines</option><option value="checkin">Check-ins</option><option value="guide">Educational guides</option></select></label><button class="button primary" type="submit">Search</button></form><p id="unifiedStatus" role="status"></p><div id="unifiedResults"></div><button id="unifiedMore" type="button" class="button quiet" hidden>Load more results</button>';searchDialog.append(button('Close search',()=>searchDialog.close()));document.body.append(searchDialog);$('unifiedSearchForm').onsubmit=e=>{e.preventDefault();search(true);};$('unifiedMore').onclick=()=>search(false);

    const filters=el('details');filters.className='search-refinements';
    filters.innerHTML='<summary>Refine your search</summary><div class="consumer-filter"><label>Area<select id="searchArea"><option value="">All areas</option><option>Skin</option><option>Hair</option><option>Nails</option><option>Sweat</option><option>General</option></select></label><label>From<input id="searchStart" type="date"></label><label>To<input id="searchEnd" type="date"></label></div>';
    filters.querySelector('div').prepend(pick('searchConcern','Concern'));
    $('unifiedSearchForm').append(filters);
    $('unifiedSearchForm').append(button('Clear filters',()=>{for(const id of ['searchArea','searchConcern','searchStart','searchEnd'])$(id).value='';search(true);},'text-button'));
    $('unifiedSearchForm').addEventListener('input',()=>{searchVersion++;message('unifiedStatus','Search filters changed. Select Search to apply them.');});
    const feedback=el('details');feedback.id='productFeedback';feedback.innerHTML='<summary>Share product feedback</summary><p>Collected in this local account. No monitored support channel is configured. Do not include health notes, identifying details or photographs.</p><form id="feedbackForm" class="continuity-form"><label>Problem category<select id="feedbackCategory"><option>Confusing screen</option><option>Save or loading problem</option><option>Accessibility</option><option>Other</option></select></label><label>Page<select id="feedbackPage"><option>Today</option><option>Check</option><option>Journey</option><option>Learn</option><option>Profile</option></select></label><label>Explanation (optional)<textarea id="feedbackNote" maxlength="2000"></textarea></label><p>Application version: consumer-continuity-v1. No account records or photos are attached automatically.</p><button class="button quiet" type="submit">Save local feedback</button><p id="feedbackStatus" role="status"></p></form>';$('profile-privacy').append(feedback);
    $('feedbackForm').onsubmit=async event=>{event.preventDefault();const submit=event.currentTarget.querySelector('[type=submit]');if(submit.disabled)return;submit.disabled=true;const generation=epoch,account=owner();try{const data=await write('/api/feedback',{category:$('feedbackCategory').value,page:$('feedbackPage').value,note:$('feedbackNote').value});if(active(generation,account)){$('feedbackForm').reset();message('feedbackStatus',data.message);}}catch(error){if(active(generation,account))message('feedbackStatus',`${error.message} Feedback was not confirmed; retry the same details.`);}finally{submit.disabled=false;}};
    const capture=el('details');capture.id='captureGuidance';capture.innerHTML='<summary>Prepare a useful photo</summary><p>Use bright, even light; keep the camera steady and the area in focus. Include the full area of concern without digital zoom, filters or glare. Choose a distance that keeps detail sharp, and check the preview before continuing. Rotate the device if that gives a clearer frame.</p><p>An ordinary camera photo and a dermoscopic image are different capture types. Select the actual type in Add context; do not label an ordinary photo as dermoscopy. A clear photo alone cannot establish medical or anatomical suitability.</p><p>If the camera is unavailable, use Choose photo to select an existing supported image from your gallery. If a photo is blurred, too dark or rejected, use Take photo or Choose photo to replace it. The existing upload limits still apply; photos stay in this tab until submitted and source pixels are not retained by the assessment service.</p>';
    const gallery=button('Choose photo',()=>{$('imageInput').removeAttribute('capture');$('imageInput').click();});const camera=button('Take photo',()=>{$('imageInput').setAttribute('capture','environment');$('imageInput').click();});
    const captureActions=el('div',undefined,'capture-actions');captureActions.setAttribute('role','group');captureActions.setAttribute('aria-label','Add an assessment photo');captureActions.append(gallery,camera);$('dropZone').after(captureActions);captureActions.after(capture);
    const priorHelp=document.querySelector('.capture-help');if(priorHelp){const formats=priorHelp.querySelector('p');if(formats)capture.append(formats);priorHelp.remove();}
    page(document.querySelector('.page-active')?.id);
  }
  function page(target) {
    const enabled=Boolean(window.ConsumerClient?.enabled),account=signed();
    for(const id of ['episodeWorkspace','visitBrief','savedGuides','productFeedback','assessmentEpisodeField'])if($(id))$(id).hidden=!account;
    $('workspaceSearch').placeholder=enabled?'Search records and guides':'Search health guides';$('workspaceSearch').setAttribute('aria-label',$('workspaceSearch').placeholder);
    if($('checkinImage'))$('checkinImage').closest('label').hidden=enabled;
    if (account && loadedOwner !== owner()) {
      const version = epoch, currentOwner = owner();
      void load().then(() => {
        if (target === 'progress' && active(version, currentOwner)) refreshConcernOnJourney();
      });
    } else if (account && target === 'progress') refreshConcernOnJourney();
  }
  window.ContinuityUI={enabled:()=>Boolean(window.ConsumerClient?.enabled),retryKey(path,payload){const signature=JSON.stringify([path,payload]);if(!retryKeys.has(signature))retryKeys.set(signature,crypto.randomUUID());return retryKeys.get(signature);},assessmentEpisode:()=>signed()?$('assessmentEpisode')?.value||'':'',assessmentAreaChanged,page,changed,correctEvent,linkAssessment,reviewCheckin,viewCheckin,guide,explain,search:openSearch,isBookmarked:id=>bookmarks.some(item=>item.guide_id===id&&item.saved),
    routineSelected(id){$('checkinEpisode').value=links['routine:'+id]?.episode_id||'';},
    scheduleLoaded(link){reminderVersion++;message('reminderPreview','');scheduleLink=link;$('scheduleEpisode').value=link.episode_id||'';},scheduleLink:()=>({episode_id:$('scheduleEpisode')?.value||'',link_version:scheduleLink.version||0}),
    progress(){page();renderCheckinHistory();},
    clear(){epoch++;dialogVersion++;loadVersion++;reminderVersion++;loadedOwner='';episodes=[];links={};bookmarks=[];loading=null;scheduleLink={};briefSignature='';searchVersion++;retryKeys.clear();searchCursor=null;$('continuityDialog')?.close();$('unifiedSearchDialog')?.close();$('recordReadDialog')?.close();$('recordReadContent')?.replaceChildren();if($('returnWorkspaceSearch'))$('returnWorkspaceSearch').hidden=true;
      clearConcernOverview();
      if ($('visitBrief')) $('visitBrief').open = false;
      for(const id of ['episodeForm','visitBriefForm','feedbackForm','unifiedSearchForm'])$(id)?.reset();const episodeSubmit=$('episodeForm')?.querySelector('[type=submit]');if(episodeSubmit)episodeSubmit.disabled=false;resetBriefDates();invalidateBrief();
      for(const id of ['assessmentEpisode','checkinEpisode','journeyEpisodeId','scheduleEpisode','briefEpisode'])if($(id))choices($(id),'',id==='journeyEpisodeId'?'All concerns':undefined);
      for(const id of ['unifiedResults','savedGuideList','checkinCorrections','continuityStatus','feedbackStatus','reminderPreview','unifiedStatus'])$(id)?.replaceChildren();$('continuityDialog')?.replaceChildren();}
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
