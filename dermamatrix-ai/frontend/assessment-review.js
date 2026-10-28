/* Last current-tab review. Confirmation never substitutes for backend consent. */
(() => {
  let version=0;
  const el=id=>document.getElementById(id);
  window.AssessmentUX={
    clear(){version++;el('assessmentReviewDialog')?.close();el('assessmentReviewFields')?.replaceChildren();},
    review(){
      if(state.assessmentInFlight||!state.areaSelected||state.area!=='Sweat'&&!state.file||!el('imageConsent').checked||state.area!=='Sweat'&&el('imageContext').value==='dermoscopic_lesion'&&!el('dermoscopyConsent').checked)return analyze();
      const body=el('assessmentReviewFields');body.replaceChildren();
      const add=(label,value)=>{const term=document.createElement('dt'),detail=document.createElement('dd');term.textContent=label;detail.textContent=value;body.append(term,detail);};
      add('Concern area',state.area);
      if(window.ContinuityUI?.enabled())add('Linked concern',el('assessmentEpisode')?.selectedOptions[0]?.textContent||'No concern selected');
      add('Input',state.area==='Sweat'?'Questionnaire; no photo is used':`${state.file.name} · ${(state.file.size/1024/1024).toFixed(2)} MB`);
      if(state.area==='Sweat')for(const id of ['sweatPattern','sweatFrequency','sweatDuration','sweatLocation']){const input=el(id);add(input.closest('label')?.firstChild.textContent.trim()||id,input.selectedOptions?.[0]?.textContent||input.value);}
      else {add('Capture type',el('imageContext').selectedOptions[0].textContent);for(const id of ['duration','discomfort','change']){const input=el(id);add(input.closest('label')?.textContent.split('\n')[0].trim().slice(0,90)||id,input.selectedOptions?.[0]?.textContent||input.value);}}
      add('Save status',state.profile?.patient_id?'Derived result saved to this account if storage succeeds. Source photo is not retained.':'Guest result remains in this tab; no account record is created.');
      const opened=version;
      el('confirmAssessmentReview').onclick=()=>{if(opened!==version)return;el('assessmentReviewDialog').close();analyze();};
      el('assessmentReviewDialog').showModal();el('assessmentReviewTitle').focus();
    }
  };
  function install(){
    const dialog=document.createElement('dialog');dialog.id='assessmentReviewDialog';dialog.className='consumer-dialog';dialog.setAttribute('aria-labelledby','assessmentReviewTitle');dialog.innerHTML='<h2 id="assessmentReviewTitle" tabindex="-1">Review your check</h2><p>Your input and consent will be validated by the server. Image quality does not confirm the body area or a diagnosis.</p><dl id="assessmentReviewFields" class="assessment-review-fields"></dl><p>Available image models give research rankings. Hair has no condition classifier; sweating uses questionnaire rules. Unavailable components stay explicit.</p><div class="consumer-actions"><button id="backToAssessment" type="button" class="button quiet">Back to edit</button><button id="confirmAssessmentReview" type="button" class="button primary">Confirm and check</button></div>';
    document.body.append(dialog);el('backToAssessment').onclick=()=>dialog.close();
    const help=document.createElement('details');help.className='capture-help';help.innerHTML='<summary>How to prepare your input</summary><ol><li>Choose the concern and answer relevant questions.</li><li>For a photo, use even light, a steady close-up and the appropriate capture type. Use an ordinary photo unless you actually have dermoscopy.</li><li>Review your input and the data-handling notice, then consent before checking.</li></ol><p>Photos: up to 10 MB and 16 megapixels. Export a smaller copy from your gallery if needed; the app does not silently resize a large original. HEIC/HEIF decoding stays in server memory. No source photos are retained.</p>';
    document.getElementById('moduleStatus')?.after(help);
    if(!help.isConnected)el('screen').prepend(help);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
})();
