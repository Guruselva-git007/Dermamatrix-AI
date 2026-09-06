const AssessmentState = Object.freeze({
  IDLE: 'IDLE', CATEGORY_SELECTED: 'CATEGORY_SELECTED', INPUT_REQUIRED: 'INPUT_REQUIRED', UPLOADING: 'UPLOADING',
  INPUT_VALIDATING: 'INPUT_VALIDATING', PREPROCESSING: 'PREPROCESSING', ANALYZING: 'ANALYZING', GENERATING_EXPLANATION: 'GENERATING_EXPLANATION',
  FINALIZING: 'FINALIZING', RESULT_READY: 'RESULT_READY', LOW_CONFIDENCE: 'LOW_CONFIDENCE', INVALID_IMAGE: 'INVALID_IMAGE', OOD_IMAGE: 'OOD_IMAGE', ERROR: 'ERROR'
});
const assessmentTransitions = Object.freeze({
  IDLE: [AssessmentState.CATEGORY_SELECTED],
  CATEGORY_SELECTED: [AssessmentState.INPUT_REQUIRED, AssessmentState.UPLOADING, AssessmentState.CATEGORY_SELECTED],
  INPUT_REQUIRED: [AssessmentState.CATEGORY_SELECTED, AssessmentState.UPLOADING, AssessmentState.INPUT_VALIDATING],
  UPLOADING: [AssessmentState.INPUT_REQUIRED, AssessmentState.ERROR],
  INPUT_VALIDATING: [AssessmentState.PREPROCESSING, AssessmentState.ERROR],
  PREPROCESSING: [AssessmentState.ANALYZING, AssessmentState.ERROR],
  ANALYZING: [AssessmentState.GENERATING_EXPLANATION, AssessmentState.ERROR],
  GENERATING_EXPLANATION: [AssessmentState.FINALIZING, AssessmentState.ERROR],
  FINALIZING: [AssessmentState.RESULT_READY, AssessmentState.LOW_CONFIDENCE, AssessmentState.INVALID_IMAGE, AssessmentState.OOD_IMAGE, AssessmentState.ERROR],
  RESULT_READY: [AssessmentState.CATEGORY_SELECTED, AssessmentState.INPUT_REQUIRED, AssessmentState.UPLOADING, AssessmentState.INPUT_VALIDATING],
  LOW_CONFIDENCE: [AssessmentState.CATEGORY_SELECTED, AssessmentState.INPUT_REQUIRED, AssessmentState.UPLOADING, AssessmentState.INPUT_VALIDATING],
  INVALID_IMAGE: [AssessmentState.CATEGORY_SELECTED, AssessmentState.INPUT_REQUIRED, AssessmentState.UPLOADING, AssessmentState.INPUT_VALIDATING],
  OOD_IMAGE: [AssessmentState.CATEGORY_SELECTED, AssessmentState.INPUT_REQUIRED, AssessmentState.UPLOADING, AssessmentState.INPUT_VALIDATING],
  ERROR: [AssessmentState.CATEGORY_SELECTED, AssessmentState.INPUT_REQUIRED, AssessmentState.UPLOADING, AssessmentState.INPUT_VALIDATING]
});
const state = { area: 'Skin', imageUrl: null, file: null, assessmentId: null, profile: null, isGuest: false, assessmentState: AssessmentState.IDLE, productFilter: 'all', routines: [], checkins: [], analyses: [], progressLoadedFor: null, progressLoadPromise: null, nearbySearchLocation: '', latestRisk: null, recommendedSpecialty: 'dermatologist' };
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const areaInputProfiles = Object.freeze({
  Skin: [
    ['face_skin', 'Face skin'], ['body_skin', 'Body skin'], ['affected_skin', 'Affected skin close-up'], ['dermoscopic_lesion', 'Dermatoscopic single lesion'],
  ],
  Hair: [
    ['scalp', 'Scalp'], ['hair_loss_area', 'Hair-loss / thinning area'], ['hair_scalp_close_up', 'Hair / scalp close-up'],
  ],
  Nails: [
    ['fingernail', 'Fingernail'], ['toenail', 'Toenail'], ['nail_close_up', 'Nail / surrounding-area close-up'],
  ],
});
const areaSymptoms = Object.freeze({
  Skin: [['itching', 'Itching'], ['pain', 'Pain'], ['redness', 'Redness'], ['swelling', 'Swelling'], ['scaling', 'Scaling'], ['bleeding', 'Bleeding'], ['discharge', 'Discharge'], ['spreading', 'Spreading / enlarging']],
  Hair: [['hair_loss', 'Hair loss / thinning'], ['sudden_onset', 'Sudden onset'], ['scalp_itching', 'Scalp itching'], ['scalp_scaling', 'Scalp scaling'], ['scalp_pain', 'Scalp pain'], ['recent_stress', 'Recent illness or stress'], ['family_history', 'Family history reported']],
  Nails: [['nail_change', 'Colour or texture change'], ['thickening', 'Thickening'], ['nail_pain', 'Pain'], ['nail_separation', 'Nail separation / lifting'], ['trauma', 'Recent trauma'], ['previous_infection', 'Previous infection reported']],
  Sweat: [],
});

function renderAreaSymptoms(area) {
  const container = $('#symptomChips');
  if (!container) return;
  const options = areaSymptoms[area] || [];
  container.innerHTML = options.length
    ? options.map(([value, label]) => `<label><input type="checkbox" name="symptoms" value="${value}" /> ${label}</label>`).join('')
    : '<small>The dedicated sweat questionnaire below collects the relevant symptom details.</small>';
}

function renderImageContexts(area) {
  const select = $('#imageContext');
  const contexts = areaInputProfiles[area] || [];
  select.innerHTML = contexts.map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
  select.closest('label').hidden = !contexts.length;
}

function transitionAssessment(nextState, detail = '') {
  const allowed = assessmentTransitions[state.assessmentState] || [];
  if (nextState !== state.assessmentState && !allowed.includes(nextState)) return false;
  state.assessmentState = nextState;
  document.body.dataset.assessmentState = nextState.toLowerCase();
  const status = $('#assessmentStatus');
  if (status) status.textContent = detail || nextState.replaceAll('_', ' ');
  return true;
}

async function requestJSON(url, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw Error(payload.error || `Request failed (${response.status}).`);
    return payload;
  } catch (error) {
    if (error.name === 'AbortError') throw Error('The request took too long. Please retry.');
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

function toast(message) {
  const element = $('#toast');
  element.textContent = message; element.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => element.classList.remove('show'), 3200);
}

function selectArea(area) {
  const areaChanged = state.area !== area;
  if (areaChanged) resetImage();
  state.area = area;
  transitionAssessment(AssessmentState.CATEGORY_SELECTED, `${area.toUpperCase()} SELECTED`);
  $$('.area-choice button').forEach(button => {
    const selected = button.dataset.area === area;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  const sweat = area === 'Sweat';
  const labels = {
    Skin: { title: 'Start with a skin image', status: 'Skin photos receive image-quality and context support. The scoped lesion research classifier runs only for an attested dermatoscopic single lesion.', upload: 'Upload a clear skin image', copy: 'Choose face skin, body skin, affected-area close-up, or dermatoscopic lesion. Ordinary photos are never forced into the lesion classifier.' },
    Hair: { title: 'Start with a scalp or hair image', status: 'Hair/scalp model adapter: no trained weights are configured in this deployment.', upload: 'Upload a clear scalp or hair image', copy: 'Image-quality feedback and shared screening support are available; no hair disorder label is generated.' },
    Nails: { title: 'Start with a nail image', status: 'Nail model adapter: no trained weights are configured in this deployment.', upload: 'Upload a clear nail image', copy: 'Image-quality feedback and shared screening support are available; no nail disorder label is generated.' },
    Sweat: { title: 'Assess a sweat pattern', status: 'Sweat tabular adapter: transparent questionnaire rules are active; no validated XGBoost model is configured.', upload: '', copy: '' },
  }[area];
  $('#screenTitle').textContent = labels.title;
  $('#screenTitle').nextElementSibling.textContent = sweat ? 'Complete the questionnaire, then review a transparent summary.' : 'Choose one area, then upload a clear image.';
  $('#home h1').textContent = sweat ? 'Assess a sweat pattern.' : 'Check My Health.';
  $('#home p:last-child').textContent = sweat
    ? 'Use symptoms, context, and daily impact for a transparent questionnaire summary and general guidance.'
    : 'Upload a clear image for quality feedback, scoped model outputs when eligible, and structured care guidance.';
  $('#moduleStatus').textContent = labels.status;
  renderAreaSymptoms(area);
  $('#imageWorkflow').hidden = sweat;
  $('#sweatWorkflow').hidden = !sweat;
  $('#uploadStepTitle').textContent = labels.upload;
  $('#uploadStepCopy').textContent = labels.copy;
  renderImageContexts(area);
  $('#consentCopy').textContent = sweat
    ? 'I consent to use this questionnaire for screening support and understand it does not provide a diagnosis.'
    : 'I have consent to upload this image and understand this tool provides screening support, not a diagnosis.';
  $('#reviewStepCopy').textContent = sweat
    ? 'Review a transparent questionnaire summary and general guidance.'
    : 'Step 3: Review your image with transparent AI scope and guidance.';
  $('#analyzeButton').innerHTML = sweat ? 'Review questionnaire <span>→</span>' : 'Review image <span>→</span>';
  $('#analyzeButton').disabled = sweat ? false : !state.file;
  if (sweat) {
    $('#dermoscopyAttestation').hidden = true;
    $('#dermoscopyConsent').checked = false;
    $('#stepCount').textContent = 'STEP 1 OF 2';
  } else {
    updateImageContext();
    $('#stepCount').textContent = state.file ? 'STEP 2 OF 3' : 'STEP 1 OF 3';
  }
  transitionAssessment(AssessmentState.INPUT_REQUIRED, sweat ? 'QUESTIONNAIRE REQUIRED' : 'IMAGE REQUIRED');
}

function setImage(file) {
  if (state.area === 'Sweat') return toast('Sweat patterns use the questionnaire instead of an image.');
  const supported = /\.(jpe?g|png|webp)$/i.test(file?.name || '');
  if (!file || !supported) return toast('Choose a JPG, PNG, or WEBP image.');
  if (file.size > 10 * 1024 * 1024) return toast('Choose an image smaller than 10 MB.');
  transitionAssessment(AssessmentState.UPLOADING, 'PREPARING IMAGE PREVIEW');
  if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
  state.file = file; state.imageUrl = URL.createObjectURL(file);
  const zone = $('#dropZone'); zone.style.backgroundImage = `url("${state.imageUrl}")`; zone.classList.add('has-image');
  $('#uploadPreviewImage').src = state.imageUrl;
  $('#uploadPreviewName').textContent = file.name;
  $('#uploadPreview').hidden = false;
  $('#analyzeButton').disabled = false; $('#stepCount').textContent = 'STEP 2 OF 3';
  transitionAssessment(AssessmentState.INPUT_REQUIRED, 'IMAGE READY FOR REVIEW');
}

function resetImage() {
  if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
  state.imageUrl = null; state.file = null;
  const zone = $('#dropZone');
  if (zone) { zone.style.backgroundImage = ''; zone.classList.remove('has-image'); }
  const preview = $('#uploadPreview');
  if (preview) preview.hidden = true;
  const input = $('#imageInput');
  if (input) input.value = '';
  if (state.assessmentState !== AssessmentState.IDLE) transitionAssessment(AssessmentState.CATEGORY_SELECTED, 'IMAGE REQUIRED');
}

function openProfile() {
  if (!state.profile?.patient_id) { showAuthGate('register'); return; }
  const form = $('#profileForm');
  form.elements.full_name.value = state.profile.full_name || '';
  form.elements.phone_number.value = state.profile.phone_number || '';
  form.elements.email_address.value = state.profile.email_address || '';
  form.elements.past_history.value = state.profile.past_history || '';
  form.elements.current_history.value = state.profile.current_history || '';
  $('#profileModal').classList.add('show'); $('#profileModal').setAttribute('aria-hidden', 'false');
}
function closeProfile() { $('#profileModal').classList.remove('show'); $('#profileModal').setAttribute('aria-hidden', 'true'); }
function closeResult() { $('#resultModal').classList.remove('show'); $('#resultModal').setAttribute('aria-hidden', 'true'); }

function setAuthMessage(message = '', success = false) {
  const element = $('#authMessage');
  element.textContent = message; element.hidden = !message; element.classList.toggle('success', success);
}

function setAuthTab(tab) {
  const target = tab === 'login' ? 'login' : 'register';
  $$('.auth-tabs button').forEach(button => { const selected = button.dataset.authTab === target; button.classList.toggle('selected', selected); button.setAttribute('aria-selected', String(selected)); });
  $('#registerForm').hidden = target !== 'register'; $('#loginForm').hidden = target !== 'login';
  $('#authFormTitle').textContent = target === 'register' ? 'Create your secure workspace' : 'Sign in to your workspace';
  setAuthMessage('');
}

function showAuthGate(tab = 'register') {
  closeProfile(); closeResult(); setAuthTab(tab);
  $('#authGate').classList.add('show'); $('#authGate').setAttribute('aria-hidden', 'false'); document.body.classList.add('auth-open');
}

function hideAuthGate() {
  $('#authGate').classList.remove('show'); $('#authGate').setAttribute('aria-hidden', 'true'); document.body.classList.remove('auth-open');
}

function applyAccount(account) {
  state.profile = { ...account }; state.isGuest = false; state.progressLoadedFor = null;
  $('#profileName').textContent = account.full_name; $('#profileMeta').textContent = account.patient_id;
  updateDashboardIdentity(); persistBrowserProfile();
}

async function enterAccount(account, message) {
  applyAccount(account); hideAuthGate();
  await hydrateProfile(); await loadProgress({ force: true });
  if (message) toast(message);
}

async function registerAccount(event) {
  event.preventDefault();
  const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form).entries());
  payload.account_consent = form.account_consent.checked;
  const button = form.querySelector('[type="submit"]'); button.disabled = true; setAuthMessage('');
  try {
    const data = await requestJSON('/api/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    form.reset(); await enterAccount(data.account, 'Account created. Add health details only when you are ready.');
  } catch (error) { setAuthMessage(error.message || 'Unable to create your account.'); }
  button.disabled = false;
}

async function loginAccount(event) {
  event.preventDefault();
  const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form).entries());
  const button = form.querySelector('[type="submit"]'); button.disabled = true; setAuthMessage('');
  try {
    const data = await requestJSON('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    form.reset(); await enterAccount(data.account, 'Signed in to your local workspace.');
  } catch (error) { setAuthMessage(error.message || 'Unable to sign in.'); }
  button.disabled = false;
}

async function continueAsGuest() {
  // Guest mode must not leave a previously authenticated server session available
  // for a later reload in the same browser.
  try { await requestJSON('/api/auth/logout', { method: 'POST' }); } catch { /* guest mode remains available offline */ }
  localStorage.removeItem('dermamatrix_profile'); state.profile = null; state.isGuest = true;
  state.assessmentId = null; state.latestRisk = null; state.recommendedSpecialty = 'dermatologist'; state.nearbySearchLocation = '';
  state.routines = []; state.checkins = []; state.analyses = []; state.progressLoadedFor = null; resetImage();
  $('#profileName').textContent = 'Guest workspace'; $('#profileMeta').textContent = 'Nothing saved'; updateDashboardIdentity(); renderProgress(); hideAuthGate();
  toast('Guest workspace opened. Create an account to save reports and routines.');
}

async function restoreAuthentication() {
  try {
    const data = await requestJSON('/api/auth/session', {}, 10000);
    if (!data.authenticated || !data.account) return false;
    applyAccount(data.account); return true;
  } catch {
    return false;
  }
}

function installImagePreview() {
  if ($('#uploadPreview')) return;
  const preview = document.createElement('section');
  preview.id = 'uploadPreview'; preview.className = 'upload-preview'; preview.hidden = true;
  preview.innerHTML = '<img id="uploadPreviewImage" alt="Selected image preview" /><div><span class="eyebrow">IMAGE READY</span><strong>Check the photo before continuing</strong><small id="uploadPreviewName"></small></div><button type="button" class="text-button" id="replaceImageButton">Replace</button>';
  $('#dropZone').insertAdjacentElement('afterend', preview);
  $('#replaceImageButton').onclick = () => $('#imageInput').click();
}

function installProcessingOverlay() {
  if ($('#processingModal')) return;
  const overlay = document.createElement('div');
  overlay.id = 'processingModal'; overlay.className = 'processing-modal'; overlay.setAttribute('aria-hidden', 'true');
  overlay.innerHTML = '<div class="processing-card" role="status" aria-live="polite"><div class="scan-visual" aria-hidden="true"><span class="scan-corner corner-one"></span><span class="scan-corner corner-two"></span><span class="scan-corner corner-three"></span><span class="scan-corner corner-four"></span><span class="scan-line"></span><span class="scan-glow"></span></div><p class="eyebrow">ANALYSIS IN PROGRESS</p><h2 id="processingTitle">Preparing your screening summary</h2><p id="processingCopy">Each completed stage is shown clearly. This app will not represent an unavailable model as a result.</p><ol id="processingSteps" class="processing-steps"></ol></div>';
  document.body.append(overlay);
}

function processingStages(area) {
  if (area === 'Skin') return ['Image received', 'Image-quality check', 'Input relevance and preprocessing', 'Configured model and explanation path', 'Reported-priority and structured summary'];
  if (area === 'Hair') return ['Image received', 'Image-quality check', 'Hair/scalp relevance and preprocessing', 'Configured model-path check', 'Reported-priority and structured summary'];
  if (area === 'Nails') return ['Image received', 'Image-quality check', 'Nail relevance and preprocessing', 'Configured model-path check', 'Reported-priority and structured summary'];
  return ['Questionnaire received', 'Response validation', 'Transparent contribution summary', 'Reported-priority calculation', 'Preparing structured guidance'];
}

function openProcessing(area) {
  installProcessingOverlay();
  const modal = $('#processingModal');
  const stages = processingStages(area);
  $('#processingTitle').textContent = area === 'Sweat' ? 'Preparing your questionnaire summary' : 'Preparing your image summary';
  $('#processingCopy').textContent = area === 'Skin'
    ? 'Image quality and research-model eligibility are checked before any scoped output is shown.'
    : area === 'Sweat' ? 'Questionnaire inputs are explained with transparent contributions; no image model runs.' : 'Image quality is checked first. A disorder label is shown only if this deployment has compatible trained weights.';
  $('#processingSteps').innerHTML = stages.map((stage, index) => `<li class="${index === 0 ? 'active' : ''}"><span>${index === 0 ? '…' : index + 1}</span>${stage}</li>`).join('');
  modal.classList.add('show'); modal.setAttribute('aria-hidden', 'false');
}

function finishProcessing(succeeded = false) {
  const modal = $('#processingModal');
  if (succeeded) {
    $$('#processingSteps li').forEach(row => { row.classList.remove('active'); row.classList.add('done'); const icon = row.querySelector('span'); if (icon) icon.textContent = '✓'; });
  }
  if (modal) { modal.classList.remove('show'); modal.setAttribute('aria-hidden', 'true'); }
}

function showPage(page, { syncHistory = true } = {}) {
  const allowed = ['dashboard', 'home', 'products', 'progress', 'support', 'settings'];
  const target = allowed.includes(page) ? page : 'dashboard';
  $$('[data-page]').forEach(section => section.classList.toggle('page-active', section.dataset.page === target));
  $$('[data-page-nav]').forEach(link => link.classList.toggle('active', link.dataset.pageNav === target));
  const titles = { dashboard: 'Home', home: 'Check My Health', progress: 'My Journey', products: 'Care Hub', support: 'Find a Doctor', settings: 'Settings' };
  $('#workspaceTitle').textContent = titles[target];
  if (target === 'progress' || target === 'dashboard') loadProgress();
  if (syncHistory && window.location.hash !== `#${target}`) history.pushState({ page: target }, '', `#${target}`);
  window.scrollTo({ top: 0, behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth' });
}

function startAreaAssessment(area) {
  selectArea(area);
  showPage('home');
  window.setTimeout(() => $('#screenTitle')?.scrollIntoView({ behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth', block: 'start' }), 120);
}

function showCarePlan(plan) {
  let box = $('#careRecommendation');
  if (!box) {
    box = document.createElement('div'); box.id = 'careRecommendation'; box.className = 'care-recommendation';
    $('#carePlanSlot').append(box);
  }
  box.innerHTML = `<span>✚</span><p><strong>${escapeHTML(plan.heading)}</strong><br>${escapeHTML(plan.next_step)}<br><em>${escapeHTML(plan.routine_guardrail)}</em><br><em>${escapeHTML(plan.diet_guidance)}</em></p>`;
}

function showResultTab(tab) {
  const target = ['summary', 'evidence', 'care', 'progress', 'support'].includes(tab) ? tab : 'summary';
  $$('[data-result-tab]').forEach(button => {
    const selected = button.dataset.resultTab === target;
    button.classList.toggle('selected', selected); button.setAttribute('aria-selected', String(selected));
  });
  $$('[data-result-panel]').forEach(panel => panel.classList.toggle('active', panel.dataset.resultPanel === target));
}

function classifierPredictions(classifier) {
  if (!classifier?.available) return [];
  if (Array.isArray(classifier.top_predictions)) return classifier.top_predictions.map(prediction => ({
    label: prediction.label || prediction.condition || 'Research label',
    calibratedProbability: Number.isFinite(prediction.calibrated_probability) ? prediction.calibrated_probability : null,
    relativeScore: Number.isFinite(prediction.relative_score) ? prediction.relative_score : null,
  }));
  if (classifier.top_prediction) {
    const prediction = classifier.top_prediction;
    return [{
      label: prediction.label || prediction.condition || 'Research label',
      calibratedProbability: Number.isFinite(prediction.calibrated_probability) ? prediction.calibrated_probability : null,
      relativeScore: Number.isFinite(prediction.relative_score) ? prediction.relative_score : null,
    }];
  }
  return [];
}

function setResearchAttention(researchClassifier) {
  const research = $('#researchResult');
  const map = $('#attentionMap');
  if (!researchClassifier?.available) {
    $('#researchHeading').textContent = 'Image scope';
    $('#researchPrediction').textContent = researchClassifier?.reason || 'General photos receive visual-quality feedback and screening support only. They are not disease-classified.';
    research.hidden = false; map.hidden = true; $('#attentionLabel').textContent = 'Image preview'; return;
  }
  const top = classifierPredictions(researchClassifier)[0];
  if (!top) {
    $('#researchHeading').textContent = 'Research model record';
    $('#researchPrediction').textContent = 'A model record is available, but no prediction detail was retained in this report.';
    research.hidden = false; map.hidden = true; return;
  }
  const likelihood = researchClassifier.condition_likelihood || {};
  const uncertainty = researchClassifier.uncertainty || {};
  $('#researchHeading').textContent = 'Research lesion model';
  $('#researchPrediction').textContent = likelihood.available && Number.isFinite(top.calibratedProbability)
    ? `${top.label} · Estimated likelihood ${Math.round(top.calibratedProbability * 100)}%. Assessment certainty: ${uncertainty.certainty || 'not available'}. ${researchClassifier.confidence_notice || 'This is not a diagnosis.'}`
    : `${top.label} is the highest-ranked research label. No estimated likelihood is shown because a version-matched calibration artifact is unavailable. ${researchClassifier.confidence_notice || 'This is not a diagnosis.'}`;
  if (!researchClassifier.attention_map?.image) {
    $('#attentionLabel').textContent = 'Saved report · attention image not retained';
    map.hidden = true; research.hidden = false; return;
  }
  $('#attentionLabel').textContent = 'Grad-CAM research attention — not lesion segmentation';
  map.src = researchClassifier.attention_map.image; map.hidden = false; research.hidden = false;
}

function setSegmentation(candidateRegion, segmentation) {
  const overlay = $('#segmentationOverlay');
  const visualRegion = segmentation?.available ? segmentation : candidateRegion;
  if (visualRegion?.available && visualRegion.overlay && (segmentation?.available || candidateRegion?.reliable)) {
    overlay.src = visualRegion.overlay; overlay.hidden = false;
    $('#attentionLabel').textContent = segmentation?.available ? `Model segmentation · ${segmentation.affected_area_percent}% of frame` : `Visual candidate region · ${candidateRegion.affected_area_percent}% of frame`;
    return;
  }
  overlay.hidden = true;
}

function renderResultOverview(data) {
  const findings = $('.findings');
  if (!findings) return;
  let overview = $('#resultOverview');
  if (!overview) {
    overview = document.createElement('section');
    overview.id = 'resultOverview'; overview.className = 'result-overview';
    $('#findingText').insertAdjacentElement('afterend', overview);
  }
  const classifier = data.research_classifier || data.classification || {};
  const likelihood = classifier.condition_likelihood || {};
  const prediction = classifierPredictions(classifier)[0];
  const uncertainty = classifier.uncertainty || {};
  const severity = data.severity || {};
  const risk = data.risk || {};
  const riskScore = Number.isFinite(risk.score) ? Math.max(0, Math.min(100, risk.score)) : null;
  const likelihoodText = likelihood.available && Number.isFinite(prediction?.calibratedProbability)
    ? `${Math.round(prediction.calibratedProbability * 100)}%`
    : 'Not available';
  const severityText = severity.level || 'Not reported';
  const certaintyText = uncertainty.certainty || (classifier.available ? 'Not available' : 'Not assessed');
  overview.style.setProperty('--result-score', `${riskScore ?? 0}%`);
  overview.innerHTML = `<div class="result-priority"><div class="priority-gauge" aria-label="Reported concern priority ${riskScore === null ? 'not available' : `${riskScore} out of 100`}"><span>${riskScore === null ? '—' : riskScore}</span><small>/100</small></div><div><small>REPORTED PRIORITY</small><strong>Score</strong><p>Separate from condition likelihood.</p></div></div><div class="result-metrics"><div><small>ESTIMATED LIKELIHOOD</small><strong>${escapeHTML(likelihoodText)}</strong><p>${likelihood.available ? 'Calibrated model output' : 'Not shown without calibration'}</p></div><div><small>SYMPTOM SEVERITY</small><strong>${escapeHTML(severityText)}</strong><p>Based on reported context</p></div><div><small>ASSESSMENT CERTAINTY</small><strong>${escapeHTML(certaintyText)}</strong><p>Model uncertainty where available</p></div></div>`;
}

function renderAnalysisDashboard(data) {
  const segmentation = data.segmentation || {};
  const candidateRegion = data.candidate_region || {};
  const classifier = data.research_classifier || data.classification || {};
  const predictionsList = classifierPredictions(classifier);
  const likelihood = classifier.condition_likelihood || {};
  const uncertainty = classifier.uncertainty || {};
  const predictions = classifier.available && predictionsList.length
    ? likelihood.available
      ? predictionsList.map(item => `${escapeHTML(item.label)} ${Math.round(item.calibratedProbability * 100)}%`).join(' · ')
      : `${escapeHTML(predictionsList[0].label)} (research ranking only; calibrated likelihood unavailable)`
    : 'No disease classification run for this image type.';
  const confidence = classifier.available && predictionsList.length
    ? likelihood.available
      ? `Estimated likelihood is calibrated with ${escapeHTML(classifier.calibration?.method || 'the configured method')}. Assessment certainty: ${escapeHTML(uncertainty.certainty || 'not available')}. ${escapeHTML(classifier.confidence_notice || 'Not a diagnosis.')}`
      : `${escapeHTML(likelihood.notice || classifier.calibration?.notice || 'Calibration is unavailable, so raw model scores are not displayed as condition likelihoods.')} ${escapeHTML(uncertainty.notice || '')}`
    : '';
  const region = segmentation.available ? `Model segmentation: ${segmentation.affected_area_percent}% of frame.` : candidateRegion.available && candidateRegion.reliable ? `Visual candidate region: ${candidateRegion.affected_area_percent}% of frame. This is not trained model segmentation.` : segmentation.message || candidateRegion.message || 'No visual-region extraction run.';
  const explainability = classifier.available ? (classifier.explainability?.explanation_text || 'Grad-CAM highlights image regions contributing to the research classifier.') : 'Explainability is available only when the scoped research classifier runs.';
  const questionnaireExplanation = (data.explainability?.features || []).map(item => `<li>${escapeHTML(item.feature)}: ${escapeHTML(item.value)} (${escapeHTML(item.points)} priority points)</li>`).join('');
  const validation = data.input_validation || {};
  const validationBlock = validation.status ? `<p><strong>Input validation:</strong> ${escapeHTML(validation.status)}. ${escapeHTML(validation.category_relevance || validation.notice || '')}</p>` : '';
  const xaiBlock = questionnaireExplanation
    ? `<p><strong>Questionnaire explanation:</strong> ${escapeHTML(data.explainability.notice || '')}</p><ul>${questionnaireExplanation}</ul>`
    : `<p><strong>Why the AI looked there:</strong> ${escapeHTML(explainability)}</p>`;
  const pirs = data.pirs?.score === undefined ? '' : `<p><strong>Shared PIRS:</strong> ${escapeHTML(data.pirs.score)}/100 — ${escapeHTML(data.pirs.label)}<br/><em>${escapeHTML(data.pirs.explanation || '')}</em></p>`;
  const severity = data.severity || {};
  const severityBlock = severity.level ? `<p><strong>Reported symptom severity:</strong> ${escapeHTML(severity.level)} · ${escapeHTML(severity.label || 'Self-reported context only.')}</p>` : '';
  const cdss = data.clinical_decision_support || {};
  const cdssBlock = cdss.status ? `<p><strong>Clinical decision support:</strong> ${escapeHTML(cdss.status)}. ${escapeHTML(cdss.next_step || cdss.notice || '')}</p>` : '';
  const patientContext = data.patient_context || {};
  const contextBlock = patientContext.context_sources?.length ? `<p><strong>Context scope:</strong> ${escapeHTML(patientContext.context_sources.join(' · '))}. ${escapeHTML(patientContext.image_model_context || '')}</p>` : '';
  const intelligence = data.condition_intelligence || {};
  const finding = intelligence.finding || {};
  const findingBlock = finding.label ? `<p><strong>Possible finding:</strong> ${finding.name ? `${escapeHTML(finding.name)} — ` : ''}${escapeHTML(finding.label)}${Number.isFinite(finding.estimated_likelihood) ? ` Estimated likelihood: ${Math.round(finding.estimated_likelihood * 100)}%.` : ''}${Number.isFinite(finding.relative_score) ? ` Relative model score: ${Math.round(finding.relative_score * 100)}% (not a likelihood).` : ''} ${escapeHTML(finding.notice || '')}</p>` : '';
  const contributors = (intelligence.reported_context_factors || []).map(factor => `<li><strong>${escapeHTML(factor.label)}</strong> — ${escapeHTML(factor.interpretation)}</li>`).join('');
  const contributorBlock = `<p><strong>Possible contributors:</strong> ${contributors ? 'These are reported context signals, not confirmed causes.' : 'No specific contributor is inferred from this assessment.'}</p>${contributors ? `<ul>${contributors}</ul>` : ''}`;
  const followUp = (intelligence.symptom_follow_up || []).map(item => `<li>${escapeHTML(item)}</li>`).join('');
  const pathway = intelligence.care_pathway || {};
  const pathwayBlock = pathway.category ? `<p><strong>Care pathway:</strong> ${escapeHTML(pathway.category)}. ${escapeHTML(pathway.next_step || '')} ${escapeHTML(pathway.prescription_status || '')}</p>` : '';
  const followUpBlock = followUp ? `<p><strong>Follow-up:</strong></p><ul>${followUp}</ul>` : '';
  const lineage = data.model_metadata || classifier;
  const lineageBlock = lineage?.model_version ? `<p><strong>Model lineage:</strong> ${escapeHTML(lineage.model_id || classifier.model_id || 'model')} · ${escapeHTML(lineage.model_version || classifier.model_version)} · calibration ${escapeHTML(classifier.calibration?.calibration_version || 'not configured')}</p>` : '';
  $('#analysisPipeline').innerHTML = `${validationBlock}<p><strong>Quality:</strong> ${escapeHTML(data.quality.label)}${data.quality.status ? ` (${escapeHTML(data.quality.status)})` : ''}${data.quality.issues?.length ? ` — ${escapeHTML(data.quality.issues.join(' '))}` : ''}</p><p><strong>Region:</strong> ${escapeHTML(region)}</p><p><strong>Classification:</strong> ${predictions}</p>${confidence ? `<p><strong>Likelihood & uncertainty:</strong> ${confidence}</p>` : ''}${findingBlock}${severityBlock}${cdssBlock}${contextBlock}${contributorBlock}${pathwayBlock}${followUpBlock}${lineageBlock}${pirs}${xaiBlock}`;
  const recommendation = data.recommendations || {};
  const section = (title, values) => `<div><strong>${title}</strong><ul>${(values || []).map(value => `<li>${escapeHTML(value)}</li>`).join('')}</ul></div>`;
  const products = (recommendation.products || []).map(product => `<li><strong>${escapeHTML(product.name)}</strong> — ${escapeHTML(product.purpose)} <em>${escapeHTML(product.precautions)}</em>${product.url ? ` <a href="${escapeHTML(product.url)}" target="_blank" rel="noopener sponsored">View partner ↗</a>` : ''}</li>`).join('');
  const followUpGuidance = intelligence.follow_up || {};
  const doctor = intelligence.doctor || {};
  const knowledgeReferences = (intelligence.knowledge?.references || []).map(reference => escapeHTML(reference.title)).join(' · ');
  $('#recommendationPanel').innerHTML = `${section('Morning', recommendation.routine?.morning)}${section('Evening', recommendation.routine?.evening)}${section('Diet & nutrients', recommendation.diet)}${section('Supplements', recommendation.supplements)}<div><strong>Treatment / care pathway</strong><p>${escapeHTML(pathway.category || 'General educational support')}. ${escapeHTML(pathway.next_step || '')}</p></div><div><strong>Expected follow-up</strong><p>${escapeHTML(followUpGuidance.guidance || 'Record a check-in when there is a meaningful change.')} ${escapeHTML(followUpGuidance.timeline || '')}</p></div><div><strong>Professional support</strong><p>${escapeHTML(doctor.specialty || 'Qualified clinician')}. ${escapeHTML(doctor.appointment || '')}</p></div><div><strong>Care categories</strong><ul>${products || '<li>Product choices are deferred for this assessment.</li>'}</ul></div>${knowledgeReferences ? `<p class="recommendation-note"><strong>Knowledge references:</strong> ${knowledgeReferences}</p>` : ''}<p class="recommendation-note"><strong>Medicine safety:</strong> ${escapeHTML(recommendation.medicine_policy || 'No medicine, dose, or diagnosis-specific treatment is suggested from an uploaded image.')} ${escapeHTML(recommendation.product_notice || '')} ${escapeHTML(recommendation.research_note || '')} ${escapeHTML(recommendation.affiliate_disclosure || '')}</p>`;
}

async function analyze() {
  const sweat = state.area === 'Sweat';
  if (!sweat && !state.imageUrl) return;
  if (!$('#imageConsent').checked) return toast('Confirm image consent before continuing.');
  if (!sweat && $('#imageContext').value === 'dermoscopic_lesion' && !$('#dermoscopyConsent').checked) return toast('Confirm that the image is a dermatoscopic single-lesion photo.');
  const button = $('#analyzeButton'); button.disabled = true; button.innerHTML = 'Reviewing <span>…</span>';
  transitionAssessment(AssessmentState.INPUT_VALIDATING, 'VALIDATING INPUT');
  openProcessing(state.area);
  try {
    let data;
    transitionAssessment(AssessmentState.PREPROCESSING, 'SERVER-SIDE PREPROCESSING');
    transitionAssessment(AssessmentState.ANALYZING, 'ASSESSMENT RUNNING');
    if (sweat) {
      const payload = {
        patient_id: state.profile?.patient_id || '', questionnaire_consent: true, urgent_concern: $('#urgentConcern').checked,
        pattern: $('#sweatPattern').value, frequency: $('#sweatFrequency').value, duration: $('#sweatDuration').value,
        body_location: $('#sweatLocation').value, stress: $('#sweatStress').value, heat: $('#sweatHeat').value,
        medication_change: $('#sweatMedication').checked, daily_impact: $('#sweatImpact').checked,
      };
      data = await requestJSON('/api/sweat-assessments', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    } else {
      const form = new FormData();
      [['image', state.file], ['area', state.area], ['duration', $('#duration').value], ['discomfort', $('#discomfort').value], ['change', $('#change').value], ['image_context', $('#imageContext').value], ['patient_id', state.profile?.patient_id || ''], ['image_consent', String($('#imageConsent').checked)], ['urgent_concern', String($('#urgentConcern').checked)], ['dermoscopy_attestation', String($('#dermoscopyConsent').checked)], ['previous_treatment', $('#previousTreatment').value]].forEach(([key, value]) => form.append(key, value));
      $$('input[name="symptoms"]:checked').forEach(input => form.append('symptoms', input.value));
      data = await requestJSON('/api/assessments', { method: 'POST', body: form }, 60000);
    }
    transitionAssessment(AssessmentState.GENERATING_EXPLANATION, 'PREPARING EXPLANATION');
    transitionAssessment(AssessmentState.FINALIZING, 'FINALIZING RESULT');
    const inputStatus = data.input_validation?.status;
    const oodStatus = data.research_classifier?.uncertainty?.ood_status;
    const finalState = inputStatus === 'LOW_QUALITY' || ['INVALID', 'UNSUPPORTED'].includes(inputStatus)
      ? AssessmentState.INVALID_IMAGE
      : oodStatus === 'OUT_OF_DISTRIBUTION'
        ? AssessmentState.OOD_IMAGE
        : data.research_classifier?.uncertainty?.status === 'LOW_CONFIDENCE'
          ? AssessmentState.LOW_CONFIDENCE
          : AssessmentState.RESULT_READY;
    finishProcessing(true);
    transitionAssessment(finalState, finalState === AssessmentState.INVALID_IMAGE ? 'IMAGE NEEDS IMPROVEMENT' : finalState === AssessmentState.LOW_CONFIDENCE ? 'LOW-CONFIDENCE RESULT' : 'RESULT READY');
    state.assessmentId = data.assessment_id;
    const score = data.risk.score;
    const questionnaire = data.input_type === 'questionnaire';
    $('.segmentation-stage').classList.toggle('sweat-summary', questionnaire);
    $('#resultImage').hidden = questionnaire;
    if (questionnaire) $('#resultImage').removeAttribute('src');
    else $('#resultImage').src = state.imageUrl;
    $('#resultRisk').textContent = data.risk.level;
    const severityClass = { LOW: 'low', MODERATE: 'moderate', HIGH: 'high', URGENT: 'urgent' }[data.risk.severity] || (score < 40 ? 'low' : 'moderate');
    $('#resultRisk').className = `risk-label ${severityClass}`;
    $('#findingTitle').textContent = data.screening.title; $('#findingText').textContent = data.screening.summary; renderResultOverview(data);
    $('#qualityScore').textContent = Number.isFinite(data.quality?.score) ? `${data.quality.score}% · ${data.quality.label}` : data.quality?.label || 'Not applicable';
    const confidence = data.model?.confidence;
    $('#modelStatus').textContent = Number.isFinite(confidence) ? `${Math.round(confidence * 100)}% · screening support` : data.model?.status === 'rule_based_prototype' ? 'Questionnaire contribution summary' : 'Model adapter unavailable';
    $('#clinicalStatus').textContent = data.persistence === 'mysql' ? 'Saved to your local account · no image retained' : 'Guest result · not stored';
    $('#saveProgressButton').innerHTML = data.persistence === 'mysql' ? 'Refresh saved reports <span>→</span>' : 'Create account to save <span>→</span>';
    setSegmentation(data.candidate_region, data.segmentation); setResearchAttention(data.research_classifier); renderAnalysisDashboard(data); showCarePlan(data.care_plan); updateDoctorSupport(data.risk, data.condition_intelligence?.doctor);
    if (questionnaire) {
      $('#attentionLabel').textContent = 'Questionnaire summary';
      $('.result-footnote').textContent = 'Questionnaire inputs use a transparent contribution summary. Grad-CAM and image-region visualisation do not apply to tabular input.';
    } else {
      $('.result-footnote').textContent = 'The overlay shows a visual candidate region or configured segmentation when available. The blue attention layer is Grad-CAM from the real classifier run.';
    }
    const note = $('#concernNote').value.trim();
    const comparison = data.progress_comparison?.summary || 'Analysis metadata is saved for a registered profile. Uploaded images are not stored.';
    $('#progressText').textContent = note ? `Tracking note: “${note}” ${comparison}` : comparison;
    if (data.quality.issues?.length) toast(data.quality.issues[0]);
    if (data.urgent_notice) toast(data.urgent_notice);
    showResultTab('summary'); $('#resultModal').classList.add('show'); $('#resultModal').setAttribute('aria-hidden', 'false');
    $('#stepCount').textContent = questionnaire ? 'STEP 2 OF 2' : 'STEP 3 OF 3';
  } catch (error) { finishProcessing(false); transitionAssessment(AssessmentState.ERROR, 'ASSESSMENT UNAVAILABLE'); toast(error.message || 'Unable to review this image.'); }
  button.disabled = false; button.innerHTML = sweat ? 'Review questionnaire <span>→</span>' : 'Review image <span>→</span>';
}

async function saveProgress() {
  if (!state.assessmentId) return toast('Complete a screen before saving progress.');
  if (!state.profile?.patient_id) {
    showAuthGate('register');
    return toast('Guest results are not stored. Create an account to save future reports and routines.');
  }
  try {
    await loadProgress({ force: true });
    $('#clinicalStatus').textContent = 'Saved to your local account · no image retained';
    toast('Saved assessment metadata is available in My Journey. Uploaded images are not kept.');
  } catch (error) {
    toast(error.message || 'Unable to refresh your saved reports.');
  }
}

function viewCare() {
  closeResult();
  showPage('products');
}

function searchDoctors(event) {
  event.preventDefault();
  openDirectorySearch($('#doctorLocation').value);
}

function directoryLocationStatus(message) {
  const status = $('#directoryLocationStatus');
  if (status) status.textContent = message;
}

function openDirectorySearch(locationValue, { appointment = false } = {}) {
  const location = String(locationValue || '').trim();
  if (!location) return toast('Enter a city or area, or use your device location first.');
  state.nearbySearchLocation = location;
  const specialty = state.recommendedSpecialty || 'dermatologist';
  const query = encodeURIComponent(appointment ? `${specialty} appointment options near ${location}` : `${specialty} near ${location}`);
  window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, '_blank', 'noopener,noreferrer');
}

function searchDirectory(event) {
  event.preventDefault();
  openDirectorySearch($('#directoryLocation').value);
}

function useNearbyLocation({ target = 'directory' } = {}) {
  if (!navigator.geolocation) return toast('This browser does not provide device location. Enter a city or locality instead.');
  directoryLocationStatus('Requesting your device location. It is used only to open a Maps search and is not saved.');
  navigator.geolocation.getCurrentPosition(
    position => {
      const coordinates = `${position.coords.latitude.toFixed(4)},${position.coords.longitude.toFixed(4)}`;
      state.nearbySearchLocation = coordinates;
      if (target === 'result') $('#doctorLocation').value = 'Current device location';
      else $('#directoryLocation').value = 'Current device location';
      directoryLocationStatus('Location received in this browser. Opening nearby dermatologist results in Maps.');
      openDirectorySearch(coordinates);
    },
    () => {
      directoryLocationStatus('Location was not shared. Enter a city or locality to search manually.');
      toast('Location was not shared. You can still search by city or area.');
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
  );
}

function openAppointmentOptions(locationValue) {
  const location = String(locationValue || state.nearbySearchLocation || '').trim();
  openDirectorySearch(location, { appointment: true });
}

function updateDoctorSupport(risk = {}, doctor = {}) {
  state.latestRisk = risk;
  const specialty = doctor.specialty || 'Dermatologist';
  state.recommendedSpecialty = specialty === 'Dermatologist' ? 'dermatologist' : 'doctor';
  const highPriority = ['HIGH', 'URGENT'].includes(risk.severity);
  const title = highPriority || doctor.recommended ? 'Professional review is recommended' : 'Optional professional support';
  const copy = highPriority
    ? `Your reported-concern priority is high. Use your location to open nearby ${specialty.toLowerCase()} listings with current ratings and contact details. Appointment availability is confirmed only by the clinic or booking provider.`
    : `Suggested discussion specialty: ${specialty}. Search Google Maps for current directory details such as ratings, contact options, and directions; verify registration and the listing directly before booking.`;
  const heading = $('#doctorSupportTitle'); const description = $('#doctorSupportCopy');
  if (heading) heading.textContent = title;
  if (description) description.textContent = copy;
  const directoryCopy = $('#directorySpecialtyCopy');
  if (directoryCopy) directoryCopy.textContent = doctor.specialty
    ? `Recommended discussion specialty: ${specialty}. Search Maps for current contact details, ratings, availability, and booking options; verify the listing and credentials directly.`
    : 'Search for a dermatologist or another specialist recommended by your latest assessment. Directory information is provided directly by Maps and clinics.';
}

async function saveProfile(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget); const payload = Object.fromEntries(form.entries());
  payload.health_data_consent = form.get('health_data_consent') === 'on';
  const button = event.currentTarget.querySelector('[type="submit"]'); button.disabled = true;
  try {
    const data = await requestJSON('/api/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    state.profile = { ...state.profile, ...data, past_history: payload.past_history, current_history: payload.current_history };
    persistBrowserProfile();
    $('#profileName').textContent = data.full_name; $('#profileMeta').textContent = data.patient_id; updateDashboardIdentity(); closeProfile(); await loadProgress({ force: true }); toast('Profile saved in the local project database.');
  } catch (error) { toast(error.message || 'Unable to save profile.'); }
  button.disabled = false;
}

function persistBrowserProfile() {
  // The signed HTTP-only session cookie is the identity source. Do not mirror account
  // identifiers or health details into browser storage.
}

function restoreProfile() {
  // Earlier builds kept a profile identifier in local storage. Authentication now restores
  // identity only from the signed server session, so stale browser references are removed.
  localStorage.removeItem('dermamatrix_profile');
}

async function hydrateProfile() {
  if (!state.profile?.patient_id) return;
  try {
    const profile = await requestJSON(`/api/profiles/${encodeURIComponent(state.profile.patient_id)}`, {}, 10000);
    state.profile = { ...state.profile, ...profile };
    $('#profileName').textContent = state.profile.full_name; $('#profileMeta').textContent = state.profile.patient_id;
    updateDashboardIdentity();
  } catch {
    // A local project database may be offline; routine loading displays the same recoverable state.
  }
}

const discoveryItems = [
  { category: 'skin', icon: '◌', type: 'SKIN ESSENTIAL', name: 'Barrier moisturiser', copy: 'A simple, fragrance-conscious option to discuss for everyday dryness or barrier comfort.', keywords: 'barrier moisture dry gentle sensitive skin comfort' },
  { category: 'skin', icon: '☼', type: 'SKIN ESSENTIAL', name: 'Daily sun protection', copy: 'Explore broad-spectrum sun protection choices with a clinician or pharmacist for your skin needs.', keywords: 'sun sunscreen uv broad spectrum protection pigmentation' },
  { category: 'skin', icon: '◍', type: 'SKIN ESSENTIAL', name: 'Gentle cleanser', copy: 'A minimal cleanser category for a routine review; stop use if irritation develops.', keywords: 'cleanser gentle wash irritation routine' },
  { category: 'hair', icon: '〰', type: 'HAIR + SCALP', name: 'Gentle scalp cleanser', copy: 'A product category to discuss for routine scalp cleansing and comfort.', keywords: 'hair scalp shampoo cleanser flakes comfort' },
  { category: 'hair', icon: '⌁', type: 'HAIR + SCALP', name: 'Hair-care basics', copy: 'Review heat, traction, and product build-up habits before adding new products.', keywords: 'hair care breakage traction heat routine' },
  { category: 'hair', icon: '✦', type: 'HAIR + SCALP', name: 'Scalp care routine', copy: 'Use a clinician discussion to decide whether a scalp concern needs examination.', keywords: 'scalp itch comfort routine dermatologist' },
  { category: 'vitamins', icon: 'D', type: 'SUPPLEMENT INFO', name: 'Vitamin D information', copy: 'Ask a clinician whether testing or supplementation is relevant to your history. No self-dosing.', keywords: 'vitamin d sunlight test deficiency bone wellbeing use case' },
  { category: 'vitamins', icon: 'B', type: 'SUPPLEMENT INFO', name: 'Vitamin B12 information', copy: 'Discuss testing when a clinician considers it appropriate for your symptoms and history.', keywords: 'vitamin b12 energy diet test nutrition use case' },
  { category: 'vitamins', icon: 'Fe', type: 'SUPPLEMENT INFO', name: 'Iron & folate information', copy: 'Testing and professional advice come before starting iron or folate products.', keywords: 'iron folate blood test nutrition tablet use case' },
  { category: 'vitamins', icon: 'Bi', type: 'SUPPLEMENT INFO', name: 'Biotin information', copy: 'Hair and nail changes have many causes; ask a pharmacist about medicine interactions.', keywords: 'biotin hair nails supplement interaction pharmacist' }
];

function renderDiscoveryCatalog() {
  const query = $('#productSearch').value.trim().toLowerCase();
  const visible = discoveryItems.filter(item => {
    const matchesCategory = state.productFilter === 'all' || item.category === state.productFilter;
    return matchesCategory && (!query || `${item.name} ${item.copy} ${item.keywords}`.toLowerCase().includes(query));
  });
  $('#productCatalog').innerHTML = visible.length ? visible.map(item => `<article class="catalog-card" data-category="${item.category}"><span class="catalog-icon">${item.icon}</span><span class="catalog-type">${item.type}</span><h3>${item.name}</h3><p>${item.copy}</p><button class="text-button" data-discuss-product="${item.name}">Explore topic →</button></article>`).join('') : '<div class="catalog-empty">No matching topics. Try “barrier”, “scalp”, or “vitamin”.</div>';
  $$('[data-discuss-product]').forEach(button => { button.onclick = () => toast(`${button.dataset.discussProduct}: discuss suitability with an RMP or pharmacist first.`); });
}

function restoreSettings() {
  const notifications = localStorage.getItem('dermamatrix_notifications');
  const reducedMotion = localStorage.getItem('dermamatrix_reduced_motion') === 'true';
  $('#notificationsToggle').checked = notifications !== 'false'; $('#motionToggle').checked = reducedMotion;
  document.body.classList.toggle('reduce-motion', reducedMotion);
}

function applyTheme(theme) {
  const dark = theme === 'dark';
  document.body.dataset.theme = dark ? 'dark' : 'light';
  $('#themeToggle').setAttribute('aria-pressed', String(dark));
  $('#themeToggle').setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
  $('#themeToggle').innerHTML = dark ? '<span aria-hidden="true">☀</span><b>Day</b>' : '<span aria-hidden="true">☾</span><b>Night</b>';
  document.querySelector('meta[name="theme-color"]').content = dark ? '#071a33' : '#f6f8fb';
}

function restoreTheme() { applyTheme(localStorage.getItem('dermamatrix_theme') || 'light'); }

async function clearLocalProfile() {
  try { await requestJSON('/api/auth/logout', { method: 'POST' }); } catch { /* local sign-out still continues */ }
  localStorage.removeItem('dermamatrix_profile'); state.profile = null; state.isGuest = false;
  $('#profileName').textContent = 'Guest workspace'; $('#profileMeta').textContent = 'Sign in to save';
  state.assessmentId = null; state.latestRisk = null; state.recommendedSpecialty = 'dermatologist'; state.nearbySearchLocation = '';
  state.routines = []; state.checkins = []; state.analyses = []; state.progressLoadedFor = null; resetImage(); updateDashboardIdentity(); renderProgress();
  showAuthGate('login'); setAuthMessage('You have been signed out.', true);
}

const escapeHTML = value => String(value || '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));

function currentDate() { return new Date().toISOString().slice(0, 10); }

function updateDashboardIdentity() {
  const name = state.profile?.full_name?.trim().split(/\s+/)[0] || 'there';
  $('#dashboardUser').textContent = name;
}

function renderDashboard() {
  const analyses = state.analyses || [];
  const routines = state.routines || [];
  const checkins = state.checkins || [];
  const latestAnalysis = analyses[0];
  const latestCheckin = checkins[0];
  const latestRisk = latestAnalysis?.summary?.risk;
  const latestFinding = latestAnalysis?.summary?.condition_intelligence?.finding;
  const snapshot = $('#dashboardSnapshot');
  if (snapshot) {
    const cards = [];
    if (latestAnalysis) {
      const result = latestFinding?.name || latestAnalysis.summary?.classification?.top_prediction?.condition || 'Screening summary saved';
      cards.push(`<article class="snapshot-card"><span>◌</span><div><small>LATEST ASSESSMENT</small><strong>${escapeHTML(result)}</strong><p>${escapeHTML(String(latestAnalysis.created_at).slice(0, 10))} · ${escapeHTML(latestAnalysis.area)} assessment</p></div><button class="text-button" data-dashboard-nav="progress">View →</button></article>`);
      cards.push(`<article class="snapshot-card"><span>⌁</span><div><small>REPORTED PRIORITY</small><strong>${latestRisk?.score === undefined ? 'Not available' : `${escapeHTML(latestRisk.score)}/100 · ${escapeHTML(latestRisk.level || 'recorded')}`}</strong><p>Priority is separate from condition likelihood.</p></div></article>`);
    }
    if (routines.length) {
      cards.push(`<article class="snapshot-card"><span>◔</span><div><small>ACTIVE ROUTINES</small><strong>${routines.length} ${routines.length === 1 ? 'routine' : 'routines'} in progress</strong><p>${escapeHTML(routines[0].routine_name)}${routines.length > 1 ? ` + ${routines.length - 1} more` : ''}</p></div><button class="text-button" data-dashboard-nav="progress">Manage →</button></article>`);
    }
    if (latestCheckin) {
      cards.push(`<article class="snapshot-card"><span>⌁</span><div><small>LATEST CHECK-IN</small><strong>${escapeHTML(latestCheckin.reported_trend)}</strong><p>Self-reported on ${escapeHTML(latestCheckin.checkin_date)} · not a healing score.</p></div></article>`);
    }
    snapshot.innerHTML = cards.length
      ? cards.slice(0, 4).join('')
      : '<article class="snapshot-card snapshot-empty"><span>◌</span><div><small>FIRST STEP</small><strong>Your first assessment starts here</strong><p>Choose skin, hair, nails, or sweating to begin a structured screening summary.</p></div><button class="text-button" data-dashboard-nav="home">Check My Health →</button></article>';
  }
  $('#dashboardActivity').innerHTML = !analyses.length
    ? '<p class="empty-state">No saved activity yet. Your assessments, routines, and follow-ups will appear here after you save them.</p>'
    : analyses.slice(0, 4).map(item => {
      const classification = item.summary?.classification || {};
      const prediction = classification.top_prediction;
      const title = prediction ? prediction.condition : 'Visual screening snapshot';
      const meta = prediction
        ? Number.isFinite(prediction.calibrated_probability) ? `${Math.round(prediction.calibrated_probability * 100)}% calibrated likelihood` : 'Research ranking; calibration unavailable'
        : 'No scoped classifier output';
      return `<article class="dashboard-record"><span>◌</span><div><strong>${escapeHTML(title)}</strong><small>${escapeHTML(item.area)} · ${escapeHTML(meta)}</small></div><time>${escapeHTML(String(item.created_at).slice(0, 10))}</time></article>`;
    }).join('');
  const nextStep = $('#nextStepCard');
  if (nextStep) {
    const highPriority = ['HIGH', 'URGENT'].includes(latestRisk?.severity);
    if (highPriority) {
      nextStep.innerHTML = '<p class="eyebrow">YOUR NEXT STEP</p><h2>Professional review is recommended</h2><p>Use the doctor finder to open current local specialist listings. Clinic availability and booking are confirmed outside DermaMatrix.</p><button class="button primary" data-dashboard-nav="support">Find a Doctor <span>→</span></button>';
    } else if (latestAnalysis && routines.length === 0) {
      nextStep.innerHTML = '<p class="eyebrow">YOUR NEXT STEP</p><h2>Turn your result into a routine</h2><p>Add a clinician-recorded routine and log meaningful changes over time. This app does not infer recovery between entries.</p><button class="button primary" data-dashboard-nav="progress">Open My Journey <span>→</span></button>';
    } else if (latestCheckin) {
      nextStep.innerHTML = '<p class="eyebrow">YOUR NEXT STEP</p><h2>Keep your story up to date</h2><p>Your latest self-reported check-in is saved. Add another only when there is a meaningful change.</p><button class="button primary" data-dashboard-nav="progress">View My Journey <span>→</span></button>';
    } else {
      nextStep.innerHTML = '<p class="eyebrow">YOUR NEXT STEP</p><h2>Start a focused assessment</h2><p>Get image-quality feedback and a structured screening summary. Uploaded images are not retained.</p><button class="button primary" data-dashboard-nav="home">Check My Health <span>→</span></button>';
    }
  }
  $$('[data-dashboard-nav]').forEach(button => { button.onclick = () => showPage(button.dataset.dashboardNav); });
}

function resetRoutineForm() {
  $('#routineForm').reset(); $('#editingRoutineId').value = ''; $('#routineStartDate').value = currentDate();
  $('#routineFormTitle').textContent = 'Add a routine'; $('#cancelRoutineEdit').hidden = true;
}

function reportClassification(summary) {
  const classifier = summary?.classification || {};
  const prediction = classifierPredictions(classifier)[0];
  return prediction
    ? Number.isFinite(prediction.calibratedProbability) ? `${prediction.label} · ${Math.round(prediction.calibratedProbability * 100)}% estimated likelihood` : `${prediction.label} · research ranking only`
    : 'Screening summary only';
}

function renderReportRegister() {
  let register = $('#reportRegister');
  if (!register) {
    register = document.createElement('section'); register.id = 'reportRegister'; register.className = 'report-register';
    $('#progressSummary').insertAdjacentElement('afterend', register);
  }
  if (!state.profile?.patient_id) {
    register.innerHTML = '<div class="report-register-heading"><div><p class="eyebrow">SAVED REPORTS</p><h3>Analysis history</h3><p>Create a local profile to retain report metadata without retaining the uploaded image.</p></div></div><p class="empty-state">No profile is connected yet.</p>';
    return;
  }
  const analyses = state.analyses || [];
  const rows = analyses.length ? analyses.map(item => {
    const summary = item.summary || {};
    const priority = summary.risk?.score === undefined ? '—' : `${summary.risk.score}/100`;
    const xai = summary.classification?.available ? 'Grad-CAM run' : summary.input_type === 'questionnaire' ? 'Input contributions' : 'Scope recorded';
    return `<div class="report-row"><time>${escapeHTML(String(item.created_at).slice(0, 10))}</time><span>${escapeHTML(item.area)}</span><strong>${escapeHTML(reportClassification(summary))}</strong><span>${escapeHTML(priority)}</span><span>${escapeHTML(xai)}</span><div><button class="text-button" data-view-report="${escapeHTML(item.assessment_id)}">View</button><button class="text-button" data-download-report="${escapeHTML(item.assessment_id)}">PDF</button></div></div>`;
  }).join('') : '<p class="empty-state">Saved analysis metadata will appear here after an analysis. Image pixels are never retained in this prototype.</p>';
  register.innerHTML = `<div class="report-register-heading"><div><p class="eyebrow">SAVED REPORTS</p><h3>Analysis history</h3><p>Open a saved report or download a generated PDF discussion brief. Images and Grad-CAM overlays are not retained.</p></div><span>${analyses.length} saved</span></div><div class="report-table" role="table"><div class="report-row report-head" role="row"><span>Date</span><span>Area</span><span>Result scope</span><span>Priority</span><span>Evidence</span><span>Action</span></div>${rows}</div>`;
  $$('[data-view-report]').forEach(button => { button.onclick = () => showSavedReport(button.dataset.viewReport); });
  $$('[data-download-report]').forEach(button => { button.onclick = () => downloadSavedReport(button.dataset.downloadReport); });
}

function showSavedReport(assessmentId) {
  const item = state.analyses.find(analysis => analysis.assessment_id === assessmentId);
  if (!item) return toast('This saved report is no longer available.');
  const data = { ...item.summary, research_classifier: item.summary?.classification || {} };
  const questionnaire = data.input_type === 'questionnaire';
  state.assessmentId = assessmentId;
  $('.segmentation-stage').classList.toggle('sweat-summary', questionnaire);
  $('#resultImage').hidden = true; $('#resultImage').removeAttribute('src'); $('#segmentationOverlay').hidden = true; $('#attentionMap').hidden = true;
  $('#resultRisk').textContent = data.risk?.level || 'SAVED REPORT';
  const severityClass = { LOW: 'low', MODERATE: 'moderate', HIGH: 'high', URGENT: 'urgent' }[data.risk?.severity] || ((data.risk?.score || 0) < 40 ? 'low' : 'moderate');
  $('#resultRisk').className = `risk-label ${severityClass}`;
  $('#findingTitle').textContent = data.screening?.title || 'Saved screening summary';
  $('#findingText').textContent = data.screening?.summary || 'This report contains saved screening metadata only.';
  renderResultOverview(data);
  $('#qualityScore').textContent = data.quality?.score === null || data.quality?.score === undefined ? data.quality?.label || 'Not applicable' : `${data.quality.score}% · ${data.quality.label}`;
  $('#modelStatus').textContent = data.classification?.available ? 'Research model record retained' : questionnaire ? 'Questionnaire contribution summary' : 'No scoped classifier output';
  $('#clinicalStatus').textContent = 'Saved metadata · no image retained';
  setSegmentation(data.candidate_region, data.segmentation); setResearchAttention(data.research_classifier); renderAnalysisDashboard(data); showCarePlan(data.care_plan || {}); updateDoctorSupport(data.risk || {}, data.condition_intelligence?.doctor);
  $('#progressText').textContent = `Saved ${String(item.created_at).slice(0, 10)}. This report can support a clinician discussion; it does not confirm a diagnosis or treatment response.`;
  $('.result-footnote').textContent = 'This is a saved metadata report. The original image, visual candidate overlay, and Grad-CAM image were intentionally not retained.';
  showResultTab('summary'); $('#resultModal').classList.add('show'); $('#resultModal').setAttribute('aria-hidden', 'false');
}

async function downloadSavedReport(assessmentId) {
  const item = state.analyses.find(analysis => analysis.assessment_id === assessmentId);
  if (!item) return toast('This saved report is no longer available.');
  try {
    const response = await fetch(`/api/reports/${encodeURIComponent(assessmentId)}/download`);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw Error(payload.error || 'Unable to generate the PDF report.');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob); const link = document.createElement('a');
    link.href = url; link.download = `dermamatrix-discussion-brief-${String(item.created_at).slice(0, 10)}.pdf`; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    toast('PDF discussion brief downloaded.');
  } catch (error) {
    toast(error.message || 'Unable to generate the PDF report.');
  }
}

async function downloadHistory() {
  if (!state.profile?.patient_id) {
    showAuthGate('register');
    return toast('Create or sign in to an account before downloading saved history.');
  }
  try {
    const response = await fetch('/api/history/download');
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw Error(payload.error || 'Unable to generate the history export.');
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob); const link = document.createElement('a');
    link.href = url; link.download = `dermamatrix-personal-history-${currentDate()}.pdf`; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    toast('Personal history PDF downloaded.');
  } catch (error) {
    toast(error.message || 'Unable to generate the history export.');
  }
}

function renderProgress() {
  const hasProfile = Boolean(state.profile?.patient_id);
  const routines = state.routines || []; const checkins = state.checkins || []; const analyses = state.analyses || [];
  const latest = checkins[0];
  $('#progressSummary').innerHTML = `<article><span>◔</span><strong>${routines.length}</strong><small>active routines</small></article><article><span>⌁</span><strong>${latest ? escapeHTML(latest.reported_trend) : '—'}</strong><small>latest self-reported trend</small></article><article><span>◌</span><strong>${latest ? `${latest.priority_score}/100` : '—'}</strong><small>reported-concern priority</small></article>`;
  $('#openProfileFromProgress').textContent = hasProfile ? 'Profile connected' : 'Set up profile';
  $('#downloadHistoryButton').disabled = !hasProfile;
  $('#monitoringNote').textContent = !hasProfile
    ? 'Create an account to retain a check-in timeline and download history. This app never passively monitors you between entries.'
    : latest
      ? `Last self-reported check-in: ${latest.checkin_date}. Add another check-in whenever there is a meaningful change; this app does not passively observe you between entries.`
      : 'Ongoing monitoring is input-driven. Add your first check-in after starting a routine, then log meaningful changes over time.';
  $('#routineList').innerHTML = !hasProfile ? '<p class="empty-state">Set up a profile to store routines and progress securely in this local app.</p>' : !routines.length ? '<p class="empty-state">No routines yet. Add a clinician-recorded condition and its routine.</p>' : routines.map(routine => `<article class="routine-item"><div><span>${escapeHTML(routine.condition_label)}</span><h4>${escapeHTML(routine.routine_name)}</h4><p>Started ${escapeHTML(routine.start_date)} · ${routine.checkin_count || 0} check-in${Number(routine.checkin_count) === 1 ? '' : 's'}</p>${routine.notes ? `<small>${escapeHTML(routine.notes)}</small>` : ''}</div><div class="routine-actions"><button class="text-button" data-edit-routine="${routine.routine_id}">Edit</button><button class="text-button danger-button" data-delete-routine="${routine.routine_id}">Delete</button></div></article>`).join('');
  $('#checkinRoutine').innerHTML = `<option value="">Choose a saved routine</option>${routines.map(routine => `<option value="${routine.routine_id}">${escapeHTML(routine.condition_label)} · ${escapeHTML(routine.routine_name)}</option>`).join('')}`;
  const medicalHistory = hasProfile && (state.profile.past_history || state.profile.current_history) ? `<div class="medical-history-summary"><strong>Profile medical history</strong>${state.profile.past_history ? `<p>Past: ${escapeHTML(state.profile.past_history)}</p>` : ''}${state.profile.current_history ? `<p>Current: ${escapeHTML(state.profile.current_history)}</p>` : ''}</div>` : '';
  const timeline = !hasProfile ? '<p class="empty-state">Your progress timeline is available after profile setup.</p>' : !checkins.length ? '<p class="empty-state">Save your first check-in to create a timeline.</p>' : checkins.map(item => `<article class="history-item"><div><strong>${escapeHTML(item.reported_trend)} · ${item.priority_score}/100</strong><p>${escapeHTML(item.condition_label)} · ${escapeHTML(item.routine_name)}</p>${item.note ? `<small>${escapeHTML(item.note)}</small>` : ''}</div><time>${escapeHTML(item.checkin_date)}</time></article>`).join('');
  const analysisHistory = !hasProfile ? '' : !analyses.length ? '<p class="empty-state">Saved image-analysis metadata will appear here after an analysis.</p>' : `<div class="analysis-history-group"><strong>Saved analysis metadata</strong>${analyses.map(item => { const classification = item.summary?.classification?.top_prediction; const label = classification ? Number.isFinite(classification.calibrated_probability) ? `${classification.condition} · ${Math.round(classification.calibrated_probability * 100)}% estimated likelihood` : `${classification.condition} · research ranking only` : 'No scoped classifier output'; return `<article class="history-item"><div><strong>${escapeHTML(label)}</strong><p>${escapeHTML(item.area)} · ${escapeHTML(item.summary?.segmentation?.status || 'segmentation not run')}</p><small>${escapeHTML(item.summary?.image_stored ? 'Image stored with consent' : 'Image pixels were not stored')}</small></div><time>${escapeHTML(String(item.created_at).slice(0, 10))}</time></article>`; }).join('')}</div>`;
  $('#progressHistory').innerHTML = medicalHistory + timeline + analysisHistory;
  $$('[data-edit-routine]').forEach(button => { button.onclick = () => editRoutine(button.dataset.editRoutine); });
  $$('[data-delete-routine]').forEach(button => { button.onclick = () => deleteRoutine(button.dataset.deleteRoutine); });
  renderReportRegister();
  renderDashboard();
}

async function loadProgress({ force = false } = {}) {
  if (!state.profile?.patient_id) { renderProgress(); return; }
  const patientId = state.profile.patient_id;
  if (!force && state.progressLoadedFor === patientId) { renderProgress(); return; }
  if (state.progressLoadPromise) return state.progressLoadPromise;
  state.progressLoadPromise = (async () => {
    try {
      const encodedId = encodeURIComponent(patientId);
      const [routineData, checkinData, analysisData] = await Promise.all([
        requestJSON(`/api/routines?patient_id=${encodedId}`),
        requestJSON(`/api/progress-checkins?patient_id=${encodedId}`),
        requestJSON(`/api/analysis-history?patient_id=${encodedId}`),
      ]);
      if (state.profile?.patient_id !== patientId) return;
      state.routines = routineData.routines; state.checkins = checkinData.checkins; state.analyses = analysisData.analyses;
      state.progressLoadedFor = patientId;
      renderProgress();
    } catch (error) {
      toast(error.message || 'Progress data is unavailable right now.');
    } finally {
      state.progressLoadPromise = null;
    }
  })();
  return state.progressLoadPromise;
}

function editRoutine(routineId) {
  const routine = state.routines.find(item => item.routine_id === routineId);
  if (!routine) return;
  $('#editingRoutineId').value = routine.routine_id; $('#conditionLabel').value = routine.condition_label; $('#routineName').value = routine.routine_name;
  $('#routineStartDate').value = routine.start_date; $('#routineNotes').value = routine.notes || '';
  $('#routineFormTitle').textContent = 'Edit routine'; $('#cancelRoutineEdit').hidden = false;
  $('#routineForm').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

async function saveRoutine(event) {
  event.preventDefault();
  if (!state.profile?.patient_id) { openProfile(); return toast('Set up a profile before saving routines.'); }
  const submitButton = event.currentTarget.querySelector('[type="submit"]');
  if (submitButton.disabled) return;
  const payload = { patient_id: state.profile.patient_id, condition_label: $('#conditionLabel').value, routine_name: $('#routineName').value, start_date: $('#routineStartDate').value, notes: $('#routineNotes').value };
  const editingId = $('#editingRoutineId').value;
  submitButton.disabled = true;
  try {
    await requestJSON(editingId ? `/api/routines/${editingId}` : '/api/routines', { method: editingId ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    resetRoutineForm(); await loadProgress({ force: true }); toast(editingId ? 'Routine updated.' : 'Routine added.');
  } catch (error) { toast(error.message || 'Could not save this routine.'); }
  finally { submitButton.disabled = false; }
}

async function deleteRoutine(routineId) {
  if (!window.confirm('Delete this routine and its progress history?')) return;
  try {
    await requestJSON(`/api/routines/${routineId}?patient_id=${encodeURIComponent(state.profile.patient_id)}`, { method: 'DELETE' });
    await loadProgress({ force: true }); toast('Routine deleted.');
  } catch (error) { toast(error.message || 'Could not delete this routine.'); }
}

async function saveCheckin(event) {
  event.preventDefault();
  if (!state.profile?.patient_id) { openProfile(); return toast('Set up a profile before saving check-ins.'); }
  const submitButton = event.currentTarget.querySelector('[type="submit"]');
  if (submitButton.disabled) return;
  const file = $('#checkinImage').files[0];
  const payload = { patient_id: state.profile.patient_id, routine_id: $('#checkinRoutine').value, checkin_date: $('#checkinDate').value, reported_trend: $('#checkinTrend').value, discomfort: $('#checkinDiscomfort').value, change: $('#checkinChange').value, note: $('#checkinNote').value };
  submitButton.disabled = true;
  try {
    const data = await requestJSON('/api/progress-checkins', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    event.currentTarget.reset(); $('#checkinDate').value = currentDate(); await loadProgress({ force: true });
    toast(file ? `${data.progress_label}. The comparison image was not stored.` : `${data.progress_label}. Check-in saved.`);
  } catch (error) { toast(error.message || 'Could not save this check-in.'); }
  finally { submitButton.disabled = false; }
}

function updateImageContext() {
  const dermoscopy = state.area === 'Skin' && $('#imageContext').value === 'dermoscopic_lesion';
  $('#dermoscopyAttestation').hidden = !dermoscopy;
  $('#dermoscopyConsent').required = dermoscopy;
  if (!dermoscopy) $('#dermoscopyConsent').checked = false;
}

$$('.area-choice button').forEach(button => { button.onclick = () => selectArea(button.dataset.area); });
$$('[data-page-nav]').forEach(link => { link.onclick = event => { event.preventDefault(); showPage(link.dataset.pageNav); }; });
$$('[data-dashboard-nav]').forEach(button => { button.onclick = () => showPage(button.dataset.dashboardNav); });
$$('[data-dashboard-area]').forEach(button => { button.onclick = () => startAreaAssessment(button.dataset.dashboardArea); });
$('#imageInput').onchange = event => setImage(event.target.files[0]);
$('#imageContext').onchange = updateImageContext;
const drop = $('#dropZone');
['dragenter', 'dragover'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.remove('dragging'); }));
drop.addEventListener('drop', event => setImage(event.dataTransfer.files[0]));
$('#analyzeButton').onclick = analyze; $('#saveProgressButton').onclick = saveProgress; $('#viewCareButton').onclick = viewCare;
$$('[data-result-tab]').forEach(button => { button.onclick = () => showResultTab(button.dataset.resultTab); });
$('#doctorSearchForm').onsubmit = searchDoctors; $('#directorySearchForm').onsubmit = searchDirectory;
$('#useResultLocationButton').onclick = () => useNearbyLocation({ target: 'result' });
$('#useDirectoryLocationButton').onclick = () => useNearbyLocation({ target: 'directory' });
$('#resultAppointmentSearchButton').onclick = () => openAppointmentOptions($('#doctorLocation').value === 'Current device location' ? state.nearbySearchLocation : $('#doctorLocation').value);
$('#appointmentSearchButton').onclick = () => openAppointmentOptions($('#directoryLocation').value === 'Current device location' ? state.nearbySearchLocation : $('#directoryLocation').value);
$('#profileButton').onclick = openProfile; $('#topProfileButton').onclick = openProfile; $('#openProfileFromProgress').onclick = openProfile; $('#profileForm').onsubmit = saveProfile;
$$('[data-auth-tab]').forEach(button => { button.onclick = () => setAuthTab(button.dataset.authTab); });
$('#registerForm').onsubmit = registerAccount; $('#loginForm').onsubmit = loginAccount; $('#continueGuestButton').onclick = continueAsGuest;
$('#forgotPasswordButton').onclick = () => setAuthMessage('Password reset needs an email delivery service, which is not configured for this local college-project server. Create a new test account or ask the local project administrator for help.');
$$('[data-close-modal]').forEach(button => { button.onclick = closeResult; });
$$('[data-close-profile]').forEach(button => { button.onclick = closeProfile; });
$('.menu-button').onclick = () => $('.sidebar').classList.toggle('open');
document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeResult(); closeProfile(); } });
$$('.product-tabs button').forEach(button => { button.onclick = () => { state.productFilter = button.dataset.filter; $$('.product-tabs button').forEach(tab => tab.classList.toggle('selected', tab === button)); renderDiscoveryCatalog(); }; });
$('#productSearch').oninput = renderDiscoveryCatalog;
$('#workspaceSearch').onkeydown = event => {
  if (event.key !== 'Enter') return;
  const query = event.currentTarget.value.trim();
  if (!query) return;
  $('#productSearch').value = query; renderDiscoveryCatalog(); showPage('products');
};
$('#notificationsToggle').onchange = event => { localStorage.setItem('dermamatrix_notifications', String(event.target.checked)); toast(event.target.checked ? 'Local care reminders enabled.' : 'Local care reminders disabled.'); };
$('#motionToggle').onchange = event => { localStorage.setItem('dermamatrix_reduced_motion', String(event.target.checked)); document.body.classList.toggle('reduce-motion', event.target.checked); toast(event.target.checked ? 'Reduced motion enabled.' : 'Reduced motion disabled.'); };
$('#clearProfileButton').onclick = clearLocalProfile;
$('#affiliateInfoButton').onclick = () => toast('Partner links are labelled. They never change screening results or clinician-first guidance.');
$('#themeToggle').onclick = () => { const next = document.body.dataset.theme === 'dark' ? 'light' : 'dark'; localStorage.setItem('dermamatrix_theme', next); applyTheme(next); };
$('#routineForm').onsubmit = saveRoutine; $('#cancelRoutineEdit').onclick = resetRoutineForm; $('#checkinForm').onsubmit = saveCheckin; $('#downloadHistoryButton').onclick = downloadHistory;
window.addEventListener('popstate', () => showPage(location.hash.replace('#', '') || 'dashboard', { syncHistory: false }));
window.addEventListener('hashchange', () => showPage(location.hash.replace('#', '') || 'dashboard', { syncHistory: false }));
window.addEventListener('beforeunload', () => { if (state.imageUrl) URL.revokeObjectURL(state.imageUrl); });

async function initialiseApp() {
  installImagePreview();
  installProcessingOverlay();
  restoreProfile();
  restoreSettings();
  restoreTheme();
  renderDiscoveryCatalog();
  selectArea(state.area);
  resetRoutineForm();
  $('#checkinDate').value = currentDate();
  $('#clearProfileButton').textContent = 'Sign out';
  const accountSetting = $('#clearProfileButton').closest('article');
  accountSetting.querySelector('h3').textContent = 'Account';
  accountSetting.querySelector('p').textContent = 'End this browser session without deleting your local records.';
  $('#profileModal .profile-actions [data-close-profile]').textContent = 'Cancel';
  $('#resultTitle').textContent = 'Your assessment';
  $('[data-result-tab="care"]').textContent = 'Care Hub';
  $('[data-result-tab="progress"]').textContent = 'Track progress';
  $('[data-result-tab="support"]').textContent = 'Find a doctor';
  $('#viewCareButton').textContent = 'View Care Hub';
  const authenticated = await restoreAuthentication();
  if (authenticated) await hydrateProfile();
  await loadProgress();
  showPage(location.hash.replace('#', '') || 'dashboard', { syncHistory: false });
  if (!authenticated) showAuthGate('register');
}

initialiseApp();
