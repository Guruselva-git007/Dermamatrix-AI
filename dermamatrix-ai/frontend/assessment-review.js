/* Last current-tab review. Confirmation never substitutes for backend consent. */
(() => {
  let version=0, reviewOpener=null;
  const el=id=>document.getElementById(id);
  window.AssessmentUX={
    clear(){version++;reviewOpener=null;el('assessmentReviewDialog')?.close();el('assessmentReviewFields')?.replaceChildren();},
    review(){
      if(state.assessmentInFlight||!state.areaSelected||state.area!=='Sweat'&&!state.file||!el('imageConsent').checked||state.area!=='Sweat'&&el('imageContext').value==='dermoscopic_lesion'&&!el('dermoscopyConsent').checked)return analyze();
      const body=el('assessmentReviewFields');body.replaceChildren();
      const add = (label, value, targetId) => {
        const term = document.createElement('dt'), detail = document.createElement('dd');
        term.textContent = label;
        const text = document.createElement('span');
        text.textContent = value;
        detail.append(text);
        if (targetId) {
          const change = document.createElement('button');
          change.type = 'button';
          change.className = 'text-button';
          change.textContent = 'Change';
          change.setAttribute('aria-label', 'Change ' + label.toLowerCase());
          change.onclick = () => {
            const target = el(targetId);
            for (let parent = target?.parentElement; parent; parent = parent.parentElement) {
              if (parent.tagName === 'DETAILS') parent.open = true;
            }
            reviewOpener = target;
            el('assessmentReviewDialog').close();
            target?.scrollIntoView({block:'center', behavior:'instant'});
          };
          detail.append(change);
        }
        body.append(term, detail);
      };
      const field = (id, label) => {
        const input = el(id);
        const value = input.type === 'checkbox' ? (input.checked ? 'Yes' : 'No')
          : input.selectedOptions?.[0]?.textContent || input.value || 'Not provided';
        add(label, value, id);
      };
      add('Concern area',state.area,'screenTitle');
      if(window.ContinuityUI?.enabled())add('Linked concern',el('assessmentEpisode')?.selectedOptions[0]?.textContent||'No concern selected','assessmentEpisode');
      add('Input',state.area==='Sweat'?'Questionnaire; no photo is used':`${state.file.name} · ${(state.file.size/1024/1024).toFixed(2)} MB`);
      if (state.area === 'Sweat') {
        for (const [id,label] of [['sweatPattern','Pattern'],['sweatFrequency','Frequency'],['sweatDuration','Duration'],
          ['sweatLocation','Location'],['sweatStress','Stress trigger'],['sweatHeat','Heat trigger'],
          ['sweatMedication','Recent medication change'],['sweatImpact','Daily impact']]) field(id,label);
      } else {
        for (const [id,label] of [['imageContext','Capture type'],['duration','Duration'],['discomfort','Discomfort'],
          ['change','Recent change'],['previousTreatment','Previous care']]) field(id,label);
        const symptoms = [...document.querySelectorAll('#symptomChips input:checked')].map(input=>input.parentElement.textContent.trim());
        add('Reported symptoms',symptoms.join(', ') || 'None selected','symptomChips');
        if (el('imageContext').value === 'dermoscopic_lesion') field('dermoscopyConsent','Dermoscopic capture confirmation');
        if (el('presentationCaseEnabled').checked) field('presentationCaseEnabled','Teaching case matching');
      }
      field('urgentConcern','Urgent concern');
      add('Processing consent',el('imageConsent').checked ? 'Confirmed for this check' : 'Required','imageConsent');
      add('Save status',state.profile?.patient_id?'Derived result saved to this account if storage succeeds. Source photo is not retained.':'Guest result remains in this tab; no account record is created.');
      const opened=++version, workspace=state.workspaceVersion, draft=window.DraftUX?.snapshot(el('screen'));
      el('confirmAssessmentReview').onclick=()=>{
        if(opened!==version || workspace!==state.workspaceVersion)return;
        if(draft!==window.DraftUX?.snapshot(el('screen')))return window.AssessmentUX.review();
        el('assessmentReviewDialog').close();analyze();
      };
      reviewOpener=el('analyzeButton');
      el('assessmentReviewDialog').showModal();el('assessmentReviewTitle').focus();
    }
  };
  function install(){
    const dialog=document.createElement('dialog');dialog.id='assessmentReviewDialog';dialog.className='consumer-dialog';dialog.setAttribute('aria-labelledby','assessmentReviewTitle');dialog.innerHTML='<h2 id="assessmentReviewTitle" tabindex="-1">Review your check</h2><p>Your input and consent will be validated by the server. Image quality does not confirm the body area or a diagnosis.</p><dl id="assessmentReviewFields" class="assessment-review-fields"></dl><p>Available image models give research rankings. Hair has no condition classifier; sweating uses questionnaire rules. Unavailable components stay explicit.</p><div class="consumer-actions"><button id="backToAssessment" type="button" class="button quiet">Back to edit</button><button id="confirmAssessmentReview" type="button" class="button primary">Confirm and check</button></div>';
    document.body.append(dialog);el('backToAssessment').onclick=()=>dialog.close();
    dialog.addEventListener('close',()=>{
      const target=reviewOpener;reviewOpener=null;
      if(target?.isConnected&&!target.disabled&&target.getClientRects().length&&!target.closest('[inert]')){
        if (!target.matches('button,input,select,textarea,[tabindex]')) target.tabIndex=-1;
        target.focus({preventScroll:true});
      }
    });
    const help=document.createElement('details');help.className='capture-help';help.innerHTML='<summary>How to prepare your input</summary><ol><li>Choose the concern and answer relevant questions.</li><li>For a photo, use even light, a steady close-up and the appropriate capture type. Use an ordinary photo unless you actually have dermoscopy.</li><li>Review your input and the data-handling notice, then consent before checking.</li></ol><p>Photos: up to 10 MB and 16 megapixels. Export a smaller copy from your gallery if needed; the app does not silently resize a large original. HEIC/HEIF decoding stays in server memory. No source photos are retained.</p>';
    document.getElementById('moduleStatus')?.after(help);
    if(!help.isConnected)el('screen').prepend(help);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
