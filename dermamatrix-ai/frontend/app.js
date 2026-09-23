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
const state = { area: 'Skin', imageUrl: null, file: null, assessmentId: null, profile: null, preferences: null, isGuest: false, assessmentState: AssessmentState.IDLE, assessmentInFlight: false, assessmentRequestId: 0, productFilter: 'all', productTag: '', productSort: 'recommended', productCatalog: [], productCatalogMeta: null, productCatalogLoaded: false, productCatalogLoadPromise: null, productCatalogQuery: '', productCatalogRequestKey: 0, productLoading: false, routines: [], checkins: [], analyses: [], progressLoadedFor: null, progressLoadPromise: null, nearbySearchLocation: '', latestRisk: null, recommendedSpecialty: 'dermatologist', modelCapabilities: {} };
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

function updateAssessmentProgress(step) {
  const activeStep = Math.max(1, Math.min(4, Number(step) || 1));
  $$('.assessment-steps li').forEach((item, index) => {
    const itemStep = index + 1;
    item.classList.toggle('active', itemStep === activeStep);
    item.classList.toggle('complete', itemStep < activeStep);
    item.setAttribute('aria-current', itemStep === activeStep ? 'step' : 'false');
  });
}

async function requestJSON(url, options = {}, timeoutMs = 15000) {
  if (window.location.protocol === 'file:') {
    throw Error('Open DermaMatrix through the local app server at http://127.0.0.1:8000. Opening index.html directly cannot reach its secure local API.');
  }
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = Error(payload.error || `Request failed (${response.status}).`);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
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
  if (state.assessmentInFlight) return toast('Please wait for the current assessment to finish before changing the health area.');
  const areaChanged = state.area !== area;
  if (areaChanged) resetImage();
  state.area = area;
  updateAssessmentProgress(1);
  transitionAssessment(AssessmentState.CATEGORY_SELECTED, `${area.toUpperCase()} SELECTED`);
  $$('.area-choice button').forEach(button => {
    const selected = button.dataset.area === area;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  const sweat = area === 'Sweat';
  const labels = {
    Skin: { title: 'Check your skin', status: 'Start with a clear photo. If you have a dermatoscopic lesion image, choose that image type for a more focused research check.', upload: 'Add a clear skin photo', copy: 'Face, body, affected area, or dermatoscopic lesion photo.' },
    Hair: { title: 'Check hair & scalp', status: 'Start with a clear photo of your hair or scalp. Your result will explain what can be reviewed.', upload: 'Add a clear hair or scalp photo', copy: 'Choose the image type that best matches your concern.' },
    Nails: { title: 'Check your nails', status: 'Start with a clear nail photo. Your result will explain what can be reviewed.', upload: 'Add a clear nail photo', copy: 'Choose the image type that best matches your concern.' },
    Sweat: { title: 'Assess a sweat pattern', status: 'Answer a few questions to get a clear summary and next steps.', upload: '', copy: '' },
  }[area];
  const capability = state.modelCapabilities[area];
  $('#screenTitle').textContent = labels.title;
  $('#screenTitle').nextElementSibling.textContent = sweat ? 'Complete a short health assessment.' : 'Add a clear image, then review your summary.';
  $('#home h1').textContent = sweat ? 'Assess a sweat pattern.' : 'Check My Health.';
  $('#home p:last-child').textContent = sweat
    ? 'Complete a short questionnaire for a structured screening summary.'
    : 'Add a clear image for screening support and next-step guidance.';
  $('#moduleStatus').textContent = capability?.user_message || labels.status;
  renderAreaSymptoms(area);
  $('#imageWorkflow').hidden = sweat;
  $('#sweatWorkflow').hidden = !sweat;
  $('.presentation-case-toggle').hidden = sweat;
  $('#uploadStepTitle').textContent = labels.upload;
  $('#uploadStepCopy').textContent = labels.copy;
  renderImageContexts(area);
  $('#consentCopy').textContent = sweat
    ? 'I consent to this screening questionnaire and understand it is not a diagnosis.'
    : 'I have consent to upload this image for AI-assisted screening, not diagnosis.';
  $('#reviewStepCopy').textContent = sweat
    ? 'Review your screening summary and next steps.'
    : 'Review your image summary and next steps.';
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
  if (state.assessmentInFlight) return toast('The current image is being assessed. You can replace it when this review is complete.');
  if (state.area === 'Sweat') return toast('Sweat patterns use the questionnaire instead of an image.');
  const supported = /\.(jpe?g|png|webp|avif)$/i.test(file?.name || '');
  if (!file || !supported) return toast('Choose a JPG, PNG, WEBP, or AVIF image.');
  if (file.size > 10 * 1024 * 1024) return toast('Choose an image smaller than 10 MB.');
  transitionAssessment(AssessmentState.UPLOADING, 'PREPARING IMAGE PREVIEW');
  if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
  state.file = file; state.imageUrl = URL.createObjectURL(file);
  const zone = $('#dropZone'); zone.style.backgroundImage = `url("${state.imageUrl}")`; zone.classList.add('has-image');
  $('#uploadPreviewImage').src = state.imageUrl;
  $('#uploadPreviewName').textContent = file.name;
  $('#uploadPreview').hidden = false;
  $('#analyzeButton').disabled = false; $('#stepCount').textContent = 'STEP 2 OF 3';
  updateAssessmentProgress(2);
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

function setAssessmentInputBusy(busy) {
  const input = $('#imageInput');
  const zone = $('#dropZone');
  if (input) input.disabled = busy;
  if (zone) {
    zone.classList.toggle('is-busy', busy);
    zone.setAttribute('aria-busy', String(busy));
  }
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

function clearAuthFieldState(form) {
  form?.querySelectorAll('.auth-field').forEach(field => field.classList.remove('is-invalid'));
  form?.querySelectorAll('input').forEach(input => input.removeAttribute('aria-invalid'));
}

function markAuthFields(form, message = '') {
  const lower = String(message).toLowerCase();
  const names = lower.includes('email') ? ['email_address']
    : lower.includes('confirm') || lower.includes('match') ? ['confirm_password']
      : lower.includes('password') ? ['password']
        : lower.includes('name') ? ['full_name'] : [];
  names.forEach(name => {
    const input = form?.elements[name];
    if (!input) return;
    input.setAttribute('aria-invalid', 'true'); input.closest('.auth-field')?.classList.add('is-invalid');
  });
}

function setAuthSubmitting(form, submitting, label) {
  const button = form?.querySelector('[type="submit"]');
  if (!button) return;
  button.disabled = submitting; form.setAttribute('aria-busy', String(submitting));
  button.querySelector('.auth-button-label').textContent = submitting ? `${label}…` : label;
  button.classList.toggle('is-loading', submitting);
}

function authErrorMessage(error, fallback) {
  const message = String(error?.message || '').trim();
  if (error?.status === 401) return 'That email and password do not match. Please try again.';
  if (error?.status === 409) return 'An account already exists for this email. Sign in instead.';
  if (!message || error?.status >= 500 || /network|failed to fetch/i.test(message)) return fallback;
  return message;
}

function setAuthTab(tab) {
  const target = tab === 'login' ? 'login' : 'register';
  const isLogin = target === 'login';
  $$('[data-auth-tab]').forEach(button => {
    const selected = button.dataset.authTab === target;
    button.classList.toggle('active', selected);
    button.removeAttribute('aria-pressed');
  });
  $('#registerForm').hidden = target !== 'register'; $('#loginForm').hidden = target !== 'login';
  $('#authGate').dataset.mode = target;
  $('#authTitle').textContent = isLogin ? 'Welcome back' : 'Create your account';
  $('#authFormSubtitle').textContent = isLogin
    ? 'Sign in to continue to your DermaMatrix account.'
    : 'Join DermaMatrix to keep your health information and preferences in one place.';
  clearAuthFieldState($('#registerForm')); clearAuthFieldState($('#loginForm'));
  setAuthMessage('');
  window.requestAnimationFrame(() => {
    const input = (isLogin ? $('#loginForm') : $('#registerForm')).querySelector('input:not([type="checkbox"])');
    input?.focus();
  });
}

function showAuthGate(tab = 'login') {
  closeProfile(); closeResult(); setAuthTab(tab);
  $('#authGate').classList.add('show'); $('#authGate').setAttribute('aria-hidden', 'false'); document.body.classList.add('auth-open');
}

function hideAuthGate() {
  $('#authGate').classList.remove('show'); $('#authGate').setAttribute('aria-hidden', 'true'); document.body.classList.remove('auth-open');
}

function applyPreferences(preferences = {}) {
  const next = {
    theme: preferences.theme === 'dark' ? 'dark' : 'light',
    notifications_enabled: preferences.notifications_enabled !== false,
    reduced_motion: preferences.reduced_motion === true,
  };
  state.preferences = { ...state.preferences, ...next };
  $('#notificationsToggle').checked = next.notifications_enabled;
  $('#motionToggle').checked = next.reduced_motion;
  document.body.classList.toggle('reduce-motion', next.reduced_motion);
  applyTheme(next.theme);
  // These values contain no account identity. They are only a guest/offline
  // rendering fallback; signed-in preferences are persisted by the API.
  localStorage.setItem('dermamatrix_notifications', String(next.notifications_enabled));
  localStorage.setItem('dermamatrix_reduced_motion', String(next.reduced_motion));
  localStorage.setItem('dermamatrix_theme', next.theme);
}

async function persistPreferences(patch) {
  const next = { ...(state.preferences || {}), ...patch };
  applyPreferences(next);
  if (!state.profile?.patient_id) return;
  try {
    const data = await requestJSON('/api/preferences', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) });
    applyPreferences(data.preferences);
  } catch (error) {
    toast(error.status === 401 ? 'Your session ended. Sign in again to save preferences.' : 'Preference changed in this browser but could not be saved to your account.');
  }
}

function applyAccount(account, preferences = null) {
  state.profile = { ...account }; state.isGuest = false; state.progressLoadedFor = null;
  $('#profileName').textContent = account.full_name; $('#profileMeta').textContent = account.patient_id;
  if (preferences) applyPreferences(preferences);
  updateDashboardIdentity(); persistBrowserProfile();
}

async function enterAccount(authentication, message) {
  applyAccount(authentication.user || authentication.account, authentication.preferences); hideAuthGate();
  await hydrateProfile(); await loadProgress({ force: true });
  showPage('dashboard');
  if (message) toast(message);
}

async function registerAccount(event) {
  event.preventDefault();
  const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form).entries());
  payload.account_consent = form.account_consent.checked;
  clearAuthFieldState(form); setAuthSubmitting(form, true, 'Creating account'); setAuthMessage('');
  try {
    const data = await requestJSON('/api/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    form.reset(); await enterAccount(data, 'Account created. Add health details only when you are ready.');
  } catch (error) {
    const message = authErrorMessage(error, 'We could not create your account. Please check your connection and try again.');
    markAuthFields(form, message); setAuthMessage(message);
  } finally { setAuthSubmitting(form, false, 'Create account'); }
}

async function loginAccount(event) {
  event.preventDefault();
  const form = event.currentTarget; const payload = Object.fromEntries(new FormData(form).entries());
  clearAuthFieldState(form); setAuthSubmitting(form, true, 'Signing in'); setAuthMessage('');
  try {
    const data = await requestJSON('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    form.reset(); await enterAccount(data, 'Signed in to your local workspace.');
  } catch (error) {
    const message = authErrorMessage(error, 'We could not sign you in. Please check your connection and try again.');
    markAuthFields(form, message); setAuthMessage(message);
  } finally { setAuthSubmitting(form, false, 'Sign in'); }
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
    const data = await requestJSON('/api/auth/me', {}, 10000);
    if (!data.authenticated || !(data.user || data.account)) return false;
    applyAccount(data.user || data.account, data.preferences); return true;
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
  const configuredStages = state.modelCapabilities[area]?.processing_stages;
  if (Array.isArray(configuredStages) && configuredStages.length) return configuredStages;
  if (area === 'Skin') return ['Image received', 'Image-quality check', 'Input relevance and preprocessing', 'Configured model and explanation path', 'Reported-priority and structured summary'];
  if (area === 'Hair') return ['Image received', 'Image-quality check', 'Hair/scalp relevance and preprocessing', 'Configured model-path check', 'Reported-priority and structured summary'];
  if (area === 'Nails') return ['Image received', 'Image-quality check', 'Nail relevance and preprocessing', 'Configured model-path check', 'Reported-priority and structured summary'];
  return ['Questionnaire received', 'Response validation', 'Transparent contribution summary', 'Reported-priority calculation', 'Preparing structured guidance'];
}

function openProcessing(area) {
  installProcessingOverlay();
  updateAssessmentProgress(4);
  const modal = $('#processingModal');
  const stages = processingStages(area);
  $('#processingTitle').textContent = area === 'Sweat' ? 'Preparing your questionnaire summary' : 'Preparing your image summary';
  const fallbackCopy = area === 'Skin'
    ? 'Image quality and research-model eligibility are checked before any scoped output is shown.'
    : area === 'Sweat' ? 'Questionnaire inputs are explained with transparent contributions; no image model runs.' : 'Image quality is checked first. A disorder label is shown only if this deployment has compatible trained weights.';
  $('#processingCopy').textContent = state.modelCapabilities[area]?.user_message || fallbackCopy;
  $('#processingSteps').innerHTML = stages.map((stage, index) => `<li class="${index === 0 ? 'active' : ''}"><span>${index === 0 ? '…' : index + 1}</span>${stage}</li>`).join('');
  modal.classList.add('show'); modal.setAttribute('aria-hidden', 'false');
}

async function loadModelCapabilities() {
  try {
    const registry = await requestJSON('/api/model-registry', {}, 10000);
    const capabilities = Array.isArray(registry.capabilities) ? registry.capabilities : [];
    state.modelCapabilities = Object.fromEntries(
      capabilities.filter(item => item?.area).map(item => [item.area, item]),
    );
  } catch (_) {
    // The hard-coded copy remains a conservative offline fallback. It never
    // says an unavailable classifier can diagnose a condition.
    state.modelCapabilities = {};
  }
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
  const titles = { dashboard: 'Home', home: 'Check My Health', progress: 'My Journey', products: 'Products', support: 'Find a Doctor', settings: 'Settings' };
  $('#workspaceTitle').textContent = titles[target];
  if (target === 'progress' || target === 'dashboard') loadProgress();
  if (target === 'products') loadCommerceCatalog();
  if (syncHistory && window.location.hash !== `#${target}`) history.pushState({ page: target }, '', `#${target}`);
  window.scrollTo({ top: 0, behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth' });
}

function startAreaAssessment(area) {
  selectArea(area);
  showPage('home');
  window.setTimeout(() => $('#screenTitle')?.scrollIntoView({ behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth', block: 'start' }), 120);
}

function showCarePlan(plan) {
  const safePlan = plan || {};
  let box = $('#careRecommendation');
  if (!box) {
    box = document.createElement('div'); box.id = 'careRecommendation'; box.className = 'care-recommendation';
    $('#carePlanSlot').append(box);
  }
  box.hidden = true;
  box.innerHTML = `<span>✚</span><p><strong>${escapeHTML(safePlan.heading || 'Care guidance')}</strong><br>${escapeHTML(safePlan.next_step || 'No additional care guidance is available for this assessment.')}<br><em>${escapeHTML(safePlan.routine_guardrail || '')}</em><br><em>${escapeHTML(safePlan.diet_guidance || '')}</em></p>`;
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

function readableStatus(value, fallback = 'Not available') {
  if (value === undefined || value === null || value === '') return fallback;
  const readable = String(value).replace(/[_-]+/g, ' ').toLowerCase();
  return readable.charAt(0).toUpperCase() + readable.slice(1);
}

function patientImageQuality(value, fallback = 'Not assessed') {
  const label = String(value || '').toLowerCase();
  if (label.includes('suitable')) return 'Good';
  if (label.includes('retake')) return 'Needs improvement';
  return value || fallback;
}

function distinctStatusSummary(label, notice) {
  const heading = String(label || '').trim().replace(/[.\s]+$/, '');
  const detail = String(notice || '').trim();
  if (!heading) return detail;
  if (!detail) return heading;
  return detail.toLowerCase().startsWith(heading.toLowerCase()) ? detail : `${heading}. ${detail}`;
}

function normaliseAssessmentPresentation(data) {
  const result = data.assessment_result || {};
  const assessmentStatus = result.status || {};
  const classifier = data.research_classifier || data.classification || {};
  const prediction = classifierPredictions(classifier)[0];
  const likelihood = classifier.condition_likelihood || {};
  const severity = result.severity || data.severity || {};
  const priority = result.care_priority || data.risk || {};
  const quality = result.input?.quality || data.quality || {};
  const cdss = data.clinical_decision_support || {};
  const carePlan = result.guidance?.care_plan || data.care_plan || {};
  const finding = result.condition || data.condition_intelligence?.finding || {};
  const questionnaire = (result.input?.type || data.input_type) === 'questionnaire';
  const contractState = String(assessmentStatus.state || '').toUpperCase();
  const assessmentState = ['HEALTHY', 'CONDITION', 'UNCERTAIN'].includes(contractState)
    ? contractState
    : (!result.contract_version && classifier.available && prediction && (finding.name || prediction.label) ? 'CONDITION' : 'UNCERTAIN');
  const hasClassifierFinding = assessmentState === 'CONDITION' && (result.contract_version
    ? Boolean(finding.available && finding.name)
    : Boolean(classifier.available && prediction && (finding.name || prediction.label))
  );
  const likelihoodAvailable = result.contract_version
    ? Number.isFinite(finding.estimated_likelihood)
    : Boolean(likelihood.available && Number.isFinite(prediction?.calibratedProbability));
  const likelihoodValue = result.contract_version ? finding.estimated_likelihood : prediction?.calibratedProbability;
  const assessmentRisk = result.assessment_risk || data.assessment_risk || { available: false, score: null, level: 'NOT_ASSESSED', notice: 'Assessment concern indicator was not calculated.' };
  const pirs = data.pirs || {};
  const presentationCase = data.presentation_case || result.presentation_case || null;
  const isPresentationCase = Boolean(presentationCase?.matched);
  const visualEvidence = result.visual_evidence || data.visual_evidence || {};
  const statusCode = assessmentStatus.code || (questionnaire ? 'QUESTIONNAIRE_ASSESSMENT' : classifier.available ? 'RESEARCH_ONLY' : 'MODEL_UNAVAILABLE');
  const resultState = String(result.result_state || '').toLowerCase();
  const unavailableDescription = resultState === 'poor_quality' || statusCode === 'INPUT_UNSUITABLE'
    ? 'This photo needs a little improvement before it can support a clearer result.'
    : resultState === 'category_mismatch'
      ? 'This photo does not match the selected skin, hair, or nail image type. Choose the matching area and try again.'
      : resultState === 'unsupported_image' || statusCode === 'OUT_OF_DISTRIBUTION'
      ? 'This photo does not match the type this check can reliably review.'
      : resultState === 'uncertain' || statusCode === 'UNCERTAIN'
        ? 'This check was not clear enough to give a reliable condition label.'
        : 'We could not give a condition label from this photo. Use the image and the details you shared to decide what to do next.';

  return {
    questionnaire,
    classifier,
    prediction,
    likelihood,
    severity,
    priority,
    quality,
    finding,
    presentationCase,
    isPresentationCase,
    visualEvidence,
    assessmentState,
    resultState,
    primaryLabel: isPresentationCase ? 'Education example' : questionnaire ? 'Questionnaire summary' : assessmentState === 'HEALTHY' ? 'Healthy appearance' : hasClassifierFinding ? 'Possible condition' : 'Reassess image',
    primaryTitle: isPresentationCase ? presentationCase.teaching_label : questionnaire ? (cdss.title || 'Your sweat-pattern summary') : assessmentState === 'HEALTHY' ? `Your ${String(data.area || 'skin').toLowerCase()} looks healthy` : hasClassifierFinding ? (finding.name || prediction.label) : 'We need a clearer look',
    primaryDescription: isPresentationCase ? presentationCase.teaching_summary : hasClassifierFinding
      ? (likelihoodAvailable
        ? 'This research-only screening result is not a diagnosis and needs independent clinical assessment.'
        : 'This is the highest-ranked research label. A calibrated likelihood is not available, and it is not a diagnosis.')
      : (assessmentState === 'HEALTHY'
        ? 'No apparent concerns were identified by the validated normal-appearance signal. This is not a diagnosis; seek care for symptoms, change, or anything that worries you.'
        : questionnaire
        ? 'This questionnaire did not use condition classification. It provides a symptom and next-step summary.'
        : unavailableDescription),
    confidence: {
      available: Boolean(likelihoodAvailable),
      heading: isPresentationCase ? 'EXAMPLE MATCH' : 'RESULT CONFIDENCE',
      value: isPresentationCase ? 'Education example' : likelihoodAvailable ? `${Math.round(likelihoodValue * 100)}%` : 'Not available',
      note: isPresentationCase ? 'This result is based on a supplied education example.' : likelihoodAvailable ? 'An estimate from the available result.' : 'A percentage is not available for this check.',
    },
    severity: {
      value: severity.level || 'Not assessed',
      note: severity.level ? 'Based on the details you reported.' : 'No symptom severity was assessed.',
    },
    quality: {
      value: questionnaire ? 'Questionnaire complete' : patientImageQuality(quality.label),
      note: quality.issues?.length ? quality.issues.join(' ') : questionnaire ? 'No image was used for this assessment.' : 'Used to determine whether this image could be reviewed.',
    },
    priority: {
      score: Number.isFinite(priority.score) ? Math.max(0, Math.min(100, priority.score)) : null,
      level: priority.level ? readableStatus(priority.level) : 'Not assessed',
      note: 'Based on the details you shared.',
    },
    assessmentRisk: {
      score: assessmentRisk.available && Number.isFinite(assessmentRisk.score) ? Math.max(0, Math.min(100, assessmentRisk.score)) : null,
      value: assessmentRisk.available && Number.isFinite(assessmentRisk.score) ? `${assessmentRisk.score}/100` : 'Not assessed',
      level: assessmentRisk.level ? readableStatus(assessmentRisk.level) : 'Not assessed',
      urgency: assessmentRisk.urgency_label || readableStatus(assessmentRisk.urgency, 'Routine monitoring'),
      factors: assessmentRisk.factor_labels || (assessmentRisk.factors || []).map(factor => factor.label).filter(Boolean),
      note: assessmentRisk.explanation || assessmentRisk.notice || 'A guide to how soon you may want to seek support.',
    },
    pirs: {
      score: Number.isFinite(pirs.score) ? Math.max(0, Math.min(100, pirs.score)) : null,
      value: Number.isFinite(pirs.score) ? `${pirs.score}/100` : 'Not assessed',
      band: pirs.band ? readableStatus(pirs.band) : 'Not assessed',
      note: pirs.label || 'Reported-concern priority for tracking; not a clinical prediction.',
    },
    assessmentStatus: {
      code: statusCode,
      label: assessmentStatus.label || readableStatus(statusCode),
      notice: assessmentStatus.notice || '',
    },
    nextAction: isPresentationCase ? `Talk through this example with a ${presentationCase.doctor_specialty}.` : cdss.next_step || carePlan.next_step || 'No next step is available for this check.',
    scope: isPresentationCase
      ? 'An exact supplied teaching file matched after you enabled Presentation case matching. Reference metadata is shown alongside the same assessment concern calculation; neither is a diagnosis or disease probability.'
      : assessmentStatus.notice
        ? distinctStatusSummary(assessmentStatus.label || readableStatus(statusCode), assessmentStatus.notice)
      : questionnaire
      ? 'This assessment used your questionnaire responses. It did not use image classification.'
      : classifier.available
        ? 'A configured research image model was used for this declared image type.'
        : 'This assessment reviewed image quality and reported context. It did not assign a condition.',
  };
}

function technicalEvidenceSection(title, rows) {
  const availableRows = rows.filter(([, value]) => value !== undefined && value !== null && value !== '');
  if (!availableRows.length) return '';
  return `<section class="technical-evidence-section"><h4>${escapeHTML(title)}</h4><dl>${availableRows.map(([label, value]) => `<div><dt>${escapeHTML(label)}</dt><dd>${escapeHTML(String(value))}</dd></div>`).join('')}</dl></section>`;
}

function setResearchAttention(researchClassifier) {
  const research = $('#researchResult');
  const map = $('#attentionMap');
  research.hidden = true;
  map.hidden = true;
  if (!researchClassifier?.available) {
    $('#researchHeading').textContent = 'Image scope';
    $('#researchPrediction').textContent = researchClassifier?.reason || 'No condition classifier was used for this assessment.';
    $('#attentionLabel').textContent = 'Image preview'; return;
  }
  const top = classifierPredictions(researchClassifier)[0];
  if (!top) {
    $('#researchHeading').textContent = 'Research model record';
    $('#researchPrediction').textContent = 'A model record is available, but no prediction detail was retained in this report.';
    return;
  }
  const likelihood = researchClassifier.condition_likelihood || {};
  const uncertainty = researchClassifier.uncertainty || {};
  $('#researchHeading').textContent = 'Research lesion model';
  $('#researchPrediction').textContent = likelihood.available && Number.isFinite(top.calibratedProbability)
    ? `${top.label} · Estimated likelihood ${Math.round(top.calibratedProbability * 100)}%. Assessment certainty: ${uncertainty.certainty || 'not available'}. ${researchClassifier.confidence_notice || 'This is not a diagnosis.'}`
    : `${top.label} is the highest-ranked research label. No estimated likelihood is shown because a version-matched calibration artifact is unavailable. ${researchClassifier.confidence_notice || 'This is not a diagnosis.'}`;
  if (!researchClassifier.attention_map?.image) {
    $('#attentionLabel').textContent = 'Saved report · attention image not retained';
    return;
  }
  $('#attentionLabel').textContent = 'Image preview';
  map.src = researchClassifier.attention_map.image;
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
  const presentation = normaliseAssessmentPresentation(data);
  overview.style.setProperty('--result-score', `${presentation.assessmentRisk.score ?? 0}%`);
  overview.innerHTML = `<div class="result-priority"><div class="priority-gauge" aria-label="Assessment concern score ${presentation.assessmentRisk.score === null ? 'not assessed' : `${presentation.assessmentRisk.score} out of 100`}"><span>${presentation.assessmentRisk.score === null ? '—' : presentation.assessmentRisk.score}</span><small>/100</small></div><div><small>RISK SCORE</small><strong>${escapeHTML(presentation.assessmentRisk.level)}</strong><p>${escapeHTML(presentation.assessmentRisk.note)}</p></div></div><div class="result-metrics"><div><small>CONFIDENCE</small><strong>${escapeHTML(presentation.confidence.value)}</strong><p>${escapeHTML(presentation.confidence.note)}</p></div><div><small>SYMPTOM SEVERITY</small><strong>${escapeHTML(presentation.severity.value)}</strong><p>${escapeHTML(presentation.severity.note)}</p></div><div><small>URGENCY</small><strong>${escapeHTML(presentation.assessmentRisk.urgency)}</strong><p>Care-routing guidance based on available assessment evidence.</p></div></div><section class="next-action"><div><small>WHAT TO DO NEXT</small><strong>${escapeHTML(presentation.nextAction)}</strong><p>${escapeHTML(presentation.scope)}</p></div></section>`;
}

function renderAnalysisDashboard(data) {
  const presentation = normaliseAssessmentPresentation(data);
  const { classifier, prediction, likelihood, priority, quality, assessmentRisk } = presentation;
  const assessmentOutcome = data.assessment_result?.status || {};
  const metadata = data.model_metadata || {};
  const pipeline = data.model_pipeline || {};
  const recommendation = data.recommendations || {};
  const segmentation = data.segmentation || {};
  const candidateRegion = data.candidate_region || {};
  const validation = data.input_validation || {};
  const uncertainty = classifier.uncertainty || {};
  const presentationCase = data.presentation_case || {};
  const isPresentationCase = Boolean(presentationCase.matched);
  const calibration = classifier.calibration || {};
  const questionnaireFeatures = data.explainability?.features || [];
  const attentionImage = classifier.attention_map?.image || classifier.explainability?.heatmap;
  const classifierName = classifier.model || metadata.model_name || data.model?.name || null;
  const modelStatus = isPresentationCase
    ? 'No model ran; exact teaching-file match shown'
    : classifier.available
    ? 'Ran for this assessment'
    : presentation.questionnaire
      ? 'No image classifier; questionnaire pathway used'
      : 'No compatible classifier ran for this input';
  const segmentationStatus = segmentation.available
    ? `Completed${Number.isFinite(segmentation.affected_area_percent) ? ` · ${segmentation.affected_area_percent}% of frame` : ''}`
    : candidateRegion.available && candidateRegion.reliable
      ? `Visual candidate region only${Number.isFinite(candidateRegion.affected_area_percent) ? ` · ${candidateRegion.affected_area_percent}% of frame` : ''}`
      : segmentation.message || candidateRegion.message || 'Not run';
  const predictionValue = isPresentationCase
    ? presentationCase.teaching_label
    : classifier.available && prediction
    ? likelihood.available && Number.isFinite(prediction.calibratedProbability)
      ? `${prediction.label} · ${Math.round(prediction.calibratedProbability * 100)}% calibrated likelihood`
      : `${prediction.label} · research ranking only`
    : 'Not run';
  const visualExplanation = attentionImage && state.imageUrl
    ? `<section class="technical-visual-explanation"><h4>Visual explanation</h4><p>Highlighted areas indicate regions that contributed to this research-model output. They are not a lesion boundary or diagnosis.</p><div class="explainability-comparison"><figure><img data-technical-src="${escapeHTML(state.imageUrl)}" alt="Original submitted image" /><figcaption>Original submitted image</figcaption></figure><figure><img data-technical-src="${escapeHTML(attentionImage)}" alt="Grad-CAM research attention map" /><figcaption>Grad-CAM attention map</figcaption></figure></div></section>`
    : '<p class="technical-unavailable">Visual explanation is not available for this assessment.</p>';
  const featureRows = questionnaireFeatures.map(feature => `${feature.feature}: ${feature.value} (${feature.points} points)`).join(' · ');
  const technicalGroups = [
    technicalEvidenceSection('Model', [
      ['Assessment outcome', assessmentOutcome.code],
      ['Status', modelStatus],
      ['Model', classifierName || metadata.model_name || data.model?.name || 'Not configured'],
      ['Architecture', metadata.architecture],
      ['Version', classifier.model_version || metadata.model_version || data.model?.version],
      ['Input modality', metadata.input_modality],
    ]),
    technicalEvidenceSection('Image processing', [
      ['Input validation', validation.status],
      ['Image quality', `${presentation.quality.value}${data.quality?.status ? ` · ${data.quality.status}` : ''}`],
      ['Preprocessing', pipeline.preprocessing],
      ['Category relevance', pipeline.category_relevance || validation.category_relevance],
    ]),
    technicalEvidenceSection('Segmentation and region', [
      ['Status', segmentationStatus],
      ['Configured model', segmentation.model],
      ['Pipeline record', pipeline.segmentation],
    ]),
    technicalEvidenceSection('Classification', [
      ['Status', modelStatus],
      ['Output', predictionValue],
      ['Calibration', calibration.status || pipeline.calibration],
      ['Uncertainty', uncertainty.status || pipeline.uncertainty],
    ]),
    technicalEvidenceSection('Explainability', [
      ['Method', data.explainability?.method || classifier.explainability?.method || (attentionImage ? 'Grad-CAM' : 'Not available')],
      ['Status', data.explainability?.status || (attentionImage ? 'Available' : pipeline.explainability)],
      ['Input contributions', featureRows || undefined],
    ]),
    technicalEvidenceSection('Priority and tracking', [
      ['Assessment concern score', assessmentRisk.score === null ? 'Not assessed' : `${assessmentRisk.score}/100 · ${assessmentRisk.level}`],
      ['Assessment urgency', assessmentRisk.urgency],
      ['Assessment factors', assessmentRisk.factors.join(' · ') || undefined],
      ['Assessment method', data.assessment_risk?.methodology || data.assessment_result?.assessment_risk?.methodology],
      ['Assessment validation', data.assessment_risk?.validation_status || data.assessment_result?.assessment_risk?.validation_status],
      ['Reported concern priority', Number.isFinite(priority.score) ? `${priority.score}/100 · ${priority.level}` : 'Not assessed'],
      ['Priority method', priority.method],
      ['Priority validation', priority.validation_status],
      ['PIRS', data.pirs?.score === undefined ? undefined : `${data.pirs.score}/100 · ${data.pirs.validation_status || 'status unavailable'}`],
      ['PIRS method', data.pirs?.method],
    ]),
    technicalEvidenceSection('Recommendation configuration', [
      ['Research-model note', recommendation.research_note],
    ]),
    technicalEvidenceSection('Technical metadata', [
      ['Assessment type', data.input_type],
      ['Inference timestamp', data.created_at],
      ['Model ID', classifier.model_id || metadata.model_id],
      ['Dataset version', classifier.dataset_version || metadata.dataset_version],
      ['Pipeline version', classifier.pipeline_version || metadata.pipeline_version],
      ['Persistence', data.persistence],
      ['Presentation case', isPresentationCase ? `${presentationCase.case_id} · exact SHA-256 file match` : undefined],
    ]),
  ].join('');
  const evidenceFocus = isPresentationCase
    ? presentationCase.notice
    : presentation.questionnaire
    ? `${questionnaireFeatures.length} questionnaire factors were considered.`
    : classifier.available
      ? 'A configured research-model path produced this result.'
      : 'No condition classifier ran for this assessment.';
  $('#analysisPipeline').innerHTML = `<details class="technical-details"><summary>AI Evidence &amp; Technical Details</summary><div class="technical-details-content"><div class="evidence-summary"><article><small>ASSESSMENT INPUT</small><strong>${escapeHTML(patientImageQuality(quality.value || (presentation.questionnaire ? 'Questionnaire complete' : 'Not assessed')))}</strong><p>${escapeHTML(presentation.quality.note)}</p></article><article><small>WHAT WAS REVIEWED</small><strong>${isPresentationCase ? 'Exact supplied presentation file' : presentation.questionnaire ? 'Questionnaire responses' : 'Image and reported context'}</strong><p>${escapeHTML(presentation.scope)}</p></article><article><small>RESULT SCOPE</small><strong>${isPresentationCase ? 'Pre-labelled teaching case' : classifier.available ? 'Research output available' : 'Screening summary'}</strong><p>${escapeHTML(evidenceFocus)}</p></article></div>${visualExplanation}<div class="technical-evidence-grid">${technicalGroups}</div></div></details>`;
  const technicalDetails = $('#analysisPipeline .technical-details');
  technicalDetails?.addEventListener('toggle', () => {
    if (!technicalDetails.open) return;
    technicalDetails.querySelectorAll('img[data-technical-src]').forEach((image) => {
      image.src = image.dataset.technicalSrc;
      image.removeAttribute('data-technical-src');
    });
  });
  const intelligence = data.condition_intelligence || {};
  const pathway = intelligence.care_pathway || {};
  const section = (title, values) => `<div><strong>${title}</strong><ul>${(values || []).map(value => `<li>${escapeHTML(value)}</li>`).join('')}</ul></div>`;
  const products = (recommendation.products || []).map(product => {
    const primary = product.commerce?.primary || {};
    const url = supportedExternalUrl(primary.url || product.url);
    const link = url ? ` <a href="${escapeHTML(url)}" target="_blank" rel="noopener${primary.is_affiliate ? ' sponsored' : ''}">${primary.is_affiliate ? 'Visit partner' : 'Find product'} ↗</a>` : '';
    return `<li><strong>${escapeHTML(product.name)}</strong> — ${escapeHTML(product.purpose)} <em>${escapeHTML(product.precautions)}</em>${link}</li>`;
  }).join('');
  const followUpGuidance = intelligence.follow_up || {};
  const doctor = intelligence.doctor || {};
  const knowledgeReferences = (intelligence.knowledge?.references || []).map(reference => escapeHTML(reference.title)).join(' · ');
  $('#recommendationPanel').innerHTML = `${section('Morning', recommendation.routine?.morning)}${section('Evening', recommendation.routine?.evening)}${section('Diet & nutrients', recommendation.diet)}${section('Supplements', recommendation.supplements)}<div><strong>Care pathway</strong><p>${escapeHTML(readableStatus(pathway.category || 'General educational support'))}. ${escapeHTML(pathway.next_step || '')}</p></div><div><strong>Expected follow-up</strong><p>${escapeHTML(followUpGuidance.guidance || 'Record a check-in when there is a meaningful change.')}</p></div><div><strong>Professional support</strong><p>${escapeHTML(doctor.specialty || 'Qualified clinician')}. ${escapeHTML(doctor.appointment || '')}</p></div><div><strong>Care categories</strong><ul>${products || '<li>Product choices are deferred for this assessment.</li>'}</ul></div>${knowledgeReferences ? `<p class="recommendation-note"><strong>Knowledge references:</strong> ${knowledgeReferences}</p>` : ''}<p class="recommendation-note"><strong>Medicine safety:</strong> ${escapeHTML(recommendation.medicine_policy || 'No medicine, dose, or diagnosis-specific treatment is suggested from an uploaded image.')} ${escapeHTML(recommendation.product_notice || '')} ${escapeHTML(recommendation.affiliate_disclosure || '')}</p>`;
}

function patientList(items, emptyMessage) {
  const values = (items || []).filter(Boolean);
  return values.length
    ? `<ul class="patient-result-list">${values.map(value => `<li>${escapeHTML(String(value))}</li>`).join('')}</ul>`
    : `<p class="patient-empty-copy">${escapeHTML(emptyMessage)}</p>`;
}

function patientMetricRow(presentation) {
  const cards = [];
  if (presentation.pirs.score !== null) {
    cards.push(`<div><small>PIRS</small><strong>${escapeHTML(presentation.pirs.value)}</strong><p>${escapeHTML(presentation.pirs.note)}</p></div>`);
  }
  if (presentation.assessmentRisk.score !== null) {
    cards.push(`<div><small>RISK</small><strong>${escapeHTML(presentation.assessmentRisk.level)}</strong><p>${escapeHTML(`${presentation.assessmentRisk.value} assessment concern · ${presentation.assessmentRisk.urgency}`)}</p></div>`);
  }
  const severity = readableStatus(presentation.severity.value, 'Not assessed');
  if (severity !== 'Not assessed') {
    cards.push(`<div><small>SEVERITY</small><strong>${escapeHTML(severity)}</strong><p>${escapeHTML(presentation.severity.note)}</p></div>`);
  }
  if (presentation.confidence.available) {
    cards.push(`<div><small>CONFIDENCE</small><strong>${escapeHTML(presentation.confidence.value)}</strong><p>${escapeHTML(presentation.confidence.note)}</p></div>`);
  }
  return cards.length ? `<section class="patient-quick-summary patient-metric-row" aria-label="Assessment metrics">${cards.join('')}</section>` : '';
}

function supportedExternalUrl(value) {
  try {
    const url = new URL(String(value || ''));
    return ['https:', 'http:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
}

function renderPatientResult(data) {
  const presentation = normaliseAssessmentPresentation(data);
  const result = data.assessment_result || {};
  const classifier = presentation.classifier;
  const recommendation = result.guidance?.recommendations || data.recommendations || {};
  const intelligence = data.condition_intelligence || {};
  const carePlan = result.guidance?.care_plan || data.care_plan || {};
  const doctor = result.guidance?.doctor || intelligence.doctor || {};
  const progress = data.progress_comparison || {};
  const contextFactors = intelligence.reported_context_factors || [];
  const questionnaireFeatures = data.explainability?.features || [];
  const segmentation = data.segmentation || {};
  const attentionImage = classifier.attention_map?.image || classifier.explainability?.heatmap;
  const imageQuality = presentation.quality.value;
  const conditionFinding = presentation.finding || {};
  const presentationCase = presentation.presentationCase || {};
  const hasVisualExplanation = Boolean(attentionImage || (segmentation.available && segmentation.overlay));
  const hasImage = Boolean(!presentation.questionnaire && state.imageUrl);
  const reportedSymptoms = contextFactors.filter(factor => factor.type === 'reported_symptom').map(factor => factor.label);
  const questionnaireObservations = questionnaireFeatures.map(feature => `${feature.feature}: ${feature.value}`);
  const observations = [
    presentation.isPresentationCase ? 'Exact supplied presentation file matched after presentation mode was enabled; reference metadata was added while the shared assessment concern calculation remained active.' : '',
    !presentation.questionnaire && imageQuality !== 'Not assessed' ? `Image quality: ${imageQuality}.` : '',
    classifier.available ? 'A configured research image model was run for the declared dermatoscopic image type.' : '',
    segmentation.available ? 'A model segmentation output was generated for this assessment.' : '',
    ...reportedSymptoms,
    ...(presentation.questionnaire ? questionnaireObservations : []),
  ].filter(Boolean);
  const products = (recommendation.products || []).map(product => {
    return `<article class="patient-product"><div class="patient-product-top">${productPreviewMarkup(product, 'patient-product-preview')}<div><span>${escapeHTML(product.category || 'Personal care')}</span><h4>${escapeHTML(product.name || 'Care category')}</h4><p>${escapeHTML(product.purpose || 'General personal-care support.')}</p></div></div><small>${escapeHTML(product.precautions || '')}</small>${commerceDestinationMarkup(product, 'patient-product-destination', 'Compare online')}</article>`;
  }).join('');
  const hasAffiliateDestination = (recommendation.products || []).some(product => Boolean(product.commerce?.primary?.is_affiliate));
  const medicationInformation = result.guidance?.medication_information || recommendation.medication_information || {};
  const routineMorning = recommendation.routine?.morning || [];
  const routineEvening = recommendation.routine?.evening || [];
  const routineWeekly = intelligence.follow_up?.guidance ? [intelligence.follow_up.guidance] : [];
  const visualMarkup = presentation.questionnaire
    ? '<div class="patient-visual-empty"><span aria-hidden="true">◌</span><strong>Questionnaire assessment</strong><p>No image is used for sweat-pattern assessments.</p></div>'
    : hasImage
      ? `<div class="patient-image-frame"><img src="${escapeHTML(state.imageUrl)}" alt="Uploaded assessment image" /><span>Uploaded image</span></div>${hasVisualExplanation ? `<details class="patient-visual-details" data-deferred-visual><summary>View AI analysis</summary><div>${segmentation.available && segmentation.overlay ? `<figure><img data-patient-src="${escapeHTML(segmentation.overlay)}" alt="Model segmentation output" /><figcaption>Model segmentation output</figcaption></figure>` : ''}${attentionImage ? `<figure><img data-patient-src="${escapeHTML(attentionImage)}" alt="Grad-CAM research attention map" /><figcaption>AI attention map</figcaption></figure>` : ''}</div></details>` : '<p class="patient-visual-note">AI visual explanation is not available for this input.</p>'}`
      : '<div class="patient-visual-empty"><span aria-hidden="true">◌</span><strong>Image not retained</strong><p>Saved reports retain assessment metadata but not the original image or visual overlays.</p></div>';
  let root = $('#patientResultContent');
  if (!root) {
    root = document.createElement('div');
    root.id = 'patientResultContent';
    $('.disclaimer-details').insertAdjacentElement('afterend', root);
  }
  const technicalEvidence = $('#analysisPipeline');
  technicalEvidence?.remove();
  root.className = 'patient-result-content';
  const metricRow = patientMetricRow(presentation);
  // The normalized contract is the only source for the patient-facing result
  // state. Legacy records without it take the conservative uncertain branch.
  if (!presentation.isPresentationCase && ['HEALTHY', 'UNCERTAIN'].includes(presentation.assessmentState)) {
    const isHealthy = presentation.assessmentState === 'HEALTHY';
    const isQuestionnaire = presentation.questionnaire;
    const stateProducts = isHealthy && products
      ? `<section class="assessment-state-products"><p class="eyebrow">OPTIONAL EVERYDAY CARE</p><div class="patient-products">${products}</div><p>${escapeHTML(recommendation.product_notice || 'These are optional maintenance categories, not treatment products.')}</p></section>`
      : '';
    const action = isHealthy
      ? `<button type="button" class="button quiet" data-result-action="progress">${state.profile?.patient_id ? 'Open My Journey' : 'Save future check-ins'} <span>→</span></button>`
      : isQuestionnaire
        ? '<button type="button" class="button primary" data-result-action="edit-questionnaire">Edit your answers <span>→</span></button>'
        : '<button type="button" class="button primary" data-result-action="reassess">Use another photo <span>→</span></button>';
    const safetyNote = isHealthy
      ? recommendation.medicine_policy || 'No treatment or medicine is needed based on this assessment.'
      : isQuestionnaire
        ? 'This is a summary of the answers you provided. It cannot identify a sweat-gland condition or select medicine or treatment.'
        : 'No product, medicine, or condition-specific treatment is shown until an assessment can establish a reliable result.';
    root.innerHTML = `<section class="assessment-state-card ${isHealthy ? 'is-healthy' : 'is-uncertain'}"><div class="assessment-state-copy"><p class="eyebrow">${isHealthy ? 'APPEARANCE CHECK' : isQuestionnaire ? 'YOUR QUESTIONNAIRE' : 'IMAGE REVIEW'}</p><h3>${escapeHTML(presentation.primaryTitle)}</h3><p>${escapeHTML(presentation.primaryDescription)}</p><div class="assessment-state-next"><strong>${escapeHTML(presentation.nextAction)}</strong><p>${escapeHTML(safetyNote)}</p></div><div class="progress-actions">${action}<button type="button" class="button quiet" data-result-action="doctor">Find a doctor <span>→</span></button></div></div><div class="assessment-state-visual">${visualMarkup}</div></section>${metricRow}<section class="patient-technical" id="patientTechnicalSlot"></section>${stateProducts}`;
    if (technicalEvidence) $('#patientTechnicalSlot').append(technicalEvidence);
    root.querySelectorAll('details[data-deferred-visual]').forEach(details => {
      details.addEventListener('toggle', () => {
        if (!details.open) return;
        details.querySelectorAll('img[data-patient-src]').forEach(image => { image.src = image.dataset.patientSrc; image.removeAttribute('data-patient-src'); });
      });
    });
    root.querySelectorAll('[data-result-action]').forEach(button => {
      button.onclick = () => {
        if (button.dataset.resultAction === 'doctor') { closeResult(); showPage('support'); return; }
        if (button.dataset.resultAction === 'progress') {
          if (!state.profile?.patient_id) { showAuthGate('register'); return toast('Create an account to save assessments and future check-ins.'); }
          closeResult(); showPage('progress'); return;
        }
        if (button.dataset.resultAction === 'edit-questionnaire') {
          closeResult(); showPage('home');
          transitionAssessment(AssessmentState.INPUT_REQUIRED, 'QUESTIONNAIRE READY TO EDIT');
          updateAssessmentProgress(3);
          window.requestAnimationFrame(() => {
            const firstQuestion = $('#sweatPattern');
            firstQuestion?.focus({ preventScroll: true });
            firstQuestion?.scrollIntoView({ behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth', block: 'center' });
          });
          return;
        }
        closeResult(); showPage('home'); $('#imageInput')?.focus();
      };
    });
    $('#resultModal').classList.add('has-patient-result');
    return;
  }
  const treatmentTopics = (presentationCase.treatment_topics || []).map(item => `<li><strong>${escapeHTML(item.name || 'Treatment topic')}</strong>${item.note ? ` — ${escapeHTML(item.note)}` : ''}</li>`).join('');
  const caseNotice = presentation.isPresentationCase ? `<section class="patient-presentation-notice"><p class="eyebrow">PRESENTATION MODE</p><strong>Pre-labelled teaching case</strong><p>${escapeHTML(presentationCase.notice || '')}</p></section>` : '';
  const teachingDetails = presentation.isPresentationCase ? `<section class="patient-why patient-teaching-details"><div><p class="eyebrow">TEACHING CASE DETAILS</p><h3>Pattern, symptoms and contributors</h3><strong>Visible pattern</strong>${patientList(presentationCase.visual_features, 'Reference image details are recorded in the teaching summary.')}<strong>Common symptoms</strong>${patientList(presentationCase.common_symptoms, 'Symptoms vary by the underlying condition.')}<strong>Common contributors / causes</strong>${patientList(presentationCase.common_contributors, 'Causes require clinical context and cannot be determined from this image.')}</div><div class="patient-what-next"><p class="eyebrow">CLINICAL CONTEXT</p><strong>Alternatives to exclude</strong>${patientList(presentationCase.differential_diagnoses, 'A clinician determines the actual diagnosis.')}<strong>Red flags</strong>${patientList(presentationCase.red_flags, 'Seek care if the concern changes, persists, or worries you.')}<p>These are teaching prompts, not patient-specific findings or a substitute for examination.</p></div></section>` : '';
  const riskSummary = presentation.assessmentRisk.score === null
    ? 'Risk score was not assessed for this input.'
    : `Assessment concern score: ${presentation.assessmentRisk.level} · ${presentation.assessmentRisk.score}/100. ${presentation.assessmentRisk.urgency}. This is not a disease probability or diagnosis.`;
  root.innerHTML = `<section class="patient-result-hero"><div><p class="eyebrow">${escapeHTML(presentation.primaryLabel.toUpperCase())}</p><h3>${escapeHTML(presentation.primaryTitle)}</h3><p>${escapeHTML(presentation.primaryDescription)}</p></div>${metricRow}</section>${caseNotice}${teachingDetails}${data.urgent_notice ? `<section class="patient-urgent-alert" role="alert"><p class="eyebrow">IMPORTANT</p><strong>Prompt medical attention may be needed</strong><p>${escapeHTML(data.urgent_notice)}</p><button type="button" class="button primary" data-result-action="doctor">Find a doctor <span>→</span></button></section>` : ''}<section class="patient-result-main"><div class="patient-visual-card"><p class="eyebrow">IMAGE / AI VISUALIZATION</p>${visualMarkup}</div><section class="patient-meaning"><p class="eyebrow">WHAT THIS MEANS</p><h3>${presentation.isPresentationCase ? escapeHTML(presentation.primaryTitle) : conditionFinding.name ? escapeHTML(conditionFinding.name) : 'A condition was not classified'}</h3><p>${escapeHTML(presentation.primaryDescription)}</p></section></section><section class="patient-why"><div><p class="eyebrow">WHY THIS RESULT?</p><h3>Information considered</h3>${patientList(observations, 'The available assessment did not produce additional observations.')}</div><div class="patient-what-next"><p class="eyebrow">WHAT TO DO NEXT</p><strong>${escapeHTML(presentation.nextAction)}</strong><p>${escapeHTML(riskSummary)}</p></div></section><section class="patient-guidance-grid"><article><p class="eyebrow">CARE PLAN</p><h3>${escapeHTML(carePlan.heading || 'General care guidance')}</h3><p>${escapeHTML(carePlan.next_step || 'No personalized care plan is currently available.')}</p><small>${escapeHTML(carePlan.routine_guardrail || recommendation.medicine_policy || '')}</small>${treatmentTopics ? `<div class="patient-medication-note"><strong>Treatment topics to discuss</strong><ul class="patient-result-list">${treatmentTopics}</ul><small>${escapeHTML(presentationCase.medication_notice || '')}</small></div>` : ''}</article><article><p class="eyebrow">YOUR ROUTINE</p><div class="patient-routine-columns"><div><strong>Morning</strong>${patientList(routineMorning, 'No morning routine is available.')}</div><div><strong>Evening</strong>${patientList(routineEvening, 'No evening routine is available.')}</div></div>${routineWeekly.length ? `<div class="patient-weekly"><strong>Follow-up</strong>${patientList(routineWeekly, '')}</div>` : ''}</article><article><p class="eyebrow">LIFESTYLE &amp; DIET</p><div class="patient-routine-columns"><div><strong>Supportive habits</strong>${patientList(recommendation.diet, 'Maintain a balanced diet. No specific dietary intervention was identified from this assessment.')}</div><div><strong>Supplements</strong>${patientList(recommendation.supplements, 'No supplement guidance is available.')}</div></div></article><article><p class="eyebrow">PRODUCT CATEGORIES TO DISCUSS</p><div class="patient-products">${products || '<p class="patient-empty-copy">General product categories can be explored from the Products page.</p>'}</div>${products ? `<p class="patient-affiliate-note">${escapeHTML(recommendation.affiliate_disclosure || 'Partner links are optional and never influence medical suitability or assessment results.')}</p>` : ''}</article></section><section class="patient-support-grid"><article><p class="eyebrow">${doctor.recommended ? 'PROFESSIONAL SUPPORT' : 'NEED PROFESSIONAL SUPPORT?'}</p><h3>${doctor.recommended ? 'Professional evaluation is recommended' : `Find a ${escapeHTML(String(presentationCase.doctor_specialty || doctor.specialty || 'dermatologist').toLowerCase())}`}</h3><p>${escapeHTML(presentation.isPresentationCase ? `For this teaching scenario, discuss the differential with a ${presentationCase.doctor_specialty}.` : doctor.recommended ? 'Your assessment suggests a clinician discussion would be useful.' : 'Search current nearby listings, then confirm credentials and availability directly.')}</p><button type="button" class="button quiet" data-result-action="doctor">Find a doctor <span>→</span></button></article><article><p class="eyebrow">TRACK PROGRESS</p><h3>${state.profile?.patient_id ? 'Continue your care journey' : 'Save your progress'}</h3><p>${escapeHTML(progress.summary || (state.profile?.patient_id ? 'Record a future check-in when there is a meaningful change.' : 'Create an account to save assessment metadata, routines, and future check-ins.'))}</p><button type="button" class="button primary" data-result-action="progress">${state.profile?.patient_id ? 'Open My Journey' : 'Create account to track'} <span>→</span></button></article></section><section class="patient-technical" id="patientTechnicalSlot"></section>`;
  if (!hasAffiliateDestination) root.querySelector('.patient-affiliate-note')?.remove();
  const carePlanCard = root.querySelector('.patient-guidance-grid > article:first-child');
  if (carePlanCard && medicationInformation.notice) {
    carePlanCard.insertAdjacentHTML('beforeend', `<div class="patient-medication-note"><strong>Medication information</strong><p>${escapeHTML(medicationInformation.notice)}</p><small>${escapeHTML(medicationInformation.consultation_notice || '')}</small></div>`);
  }
  const lifestyleCard = root.querySelector('.patient-guidance-grid > article:nth-child(3)');
  if (lifestyleCard) {
    lifestyleCard.innerHTML = `<p class="eyebrow">LIFESTYLE &amp; DIET</p><div class="patient-routine-columns"><div><strong>Diet &amp; wellbeing</strong>${patientList(recommendation.diet, 'Maintain a balanced diet. No specific dietary intervention was identified from this assessment.')}</div><div><strong>Lifestyle</strong>${patientList(recommendation.lifestyle, 'Keep routines simple and record meaningful changes for a clinician discussion.')}</div></div>${recommendation.supplements?.length ? `<div class="patient-weekly"><strong>Supplements</strong>${patientList(recommendation.supplements, '')}</div>` : ''}`;
  }
  if (technicalEvidence) $('#patientTechnicalSlot').append(technicalEvidence);
  root.querySelectorAll('details[data-deferred-visual]').forEach(details => {
    details.addEventListener('toggle', () => {
      if (!details.open) return;
      details.querySelectorAll('img[data-patient-src]').forEach(image => {
        image.src = image.dataset.patientSrc;
        image.removeAttribute('data-patient-src');
      });
    });
  });
  root.querySelectorAll('[data-result-action]').forEach(button => {
    button.onclick = () => {
      if (button.dataset.resultAction === 'doctor') { closeResult(); showPage('support'); return; }
      if (button.dataset.resultAction === 'products') { closeResult(); showPage('products'); return; }
      if (button.dataset.resultAction === 'progress') {
        if (!state.profile?.patient_id) { showAuthGate('register'); return toast('Create an account to save assessments, routines, and check-ins.'); }
        closeResult(); showPage('progress');
      }
    };
  });
  $('#resultModal').classList.add('has-patient-result');
}

async function analyze() {
  const sweat = state.area === 'Sweat';
  if (!sweat && !state.imageUrl) return;
  if (!$('#imageConsent').checked) return toast('Confirm image consent before continuing.');
  if (!sweat && $('#imageContext').value === 'dermoscopic_lesion' && !$('#dermoscopyConsent').checked) return toast('Confirm that the image is a dermatoscopic single-lesion photo.');
  const button = $('#analyzeButton');
  const requestId = ++state.assessmentRequestId;
  state.assessmentInFlight = true;
  setAssessmentInputBusy(true);
  button.disabled = true; button.innerHTML = 'Reviewing <span>…</span>';
  transitionAssessment(AssessmentState.INPUT_VALIDATING, 'VALIDATING INPUT');
  openProcessing(state.area);
  try {
    let data;
    transitionAssessment(AssessmentState.PREPROCESSING, 'SERVER-SIDE PREPROCESSING');
    transitionAssessment(AssessmentState.ANALYZING, 'ASSESSMENT RUNNING');
    if (sweat) {
      const payload = {
        questionnaire_consent: true, urgent_concern: $('#urgentConcern').checked,
        pattern: $('#sweatPattern').value, frequency: $('#sweatFrequency').value, duration: $('#sweatDuration').value,
        body_location: $('#sweatLocation').value, stress: $('#sweatStress').value, heat: $('#sweatHeat').value,
        medication_change: $('#sweatMedication').checked, daily_impact: $('#sweatImpact').checked,
      };
      data = await requestJSON('/api/sweat-assessments', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    } else {
      const form = new FormData();
      [['image', state.file], ['area', state.area], ['duration', $('#duration').value], ['discomfort', $('#discomfort').value], ['change', $('#change').value], ['image_context', $('#imageContext').value], ['image_consent', String($('#imageConsent').checked)], ['presentation_case_enabled', String($('#presentationCaseEnabled').checked)], ['urgent_concern', String($('#urgentConcern').checked)], ['dermoscopy_attestation', String($('#dermoscopyConsent').checked)], ['previous_treatment', $('#previousTreatment').value]].forEach(([key, value]) => form.append(key, value));
      $$('input[name="symptoms"]:checked').forEach(input => form.append('symptoms', input.value));
      data = await requestJSON('/api/assessments', { method: 'POST', body: form }, 60000);
    }
    // A future request may complete first. Never allow an older response to
    // overwrite the image/result state the person is currently reviewing.
    if (requestId !== state.assessmentRequestId) return;
    transitionAssessment(AssessmentState.GENERATING_EXPLANATION, 'PREPARING EXPLANATION');
    transitionAssessment(AssessmentState.FINALIZING, 'FINALIZING RESULT');
    const inputStatus = data.input_validation?.status;
    const outcomeCode = data.assessment_result?.status?.code;
    const terminalResultState = String(data.assessment_result?.result_state || '').toLowerCase();
    const oodStatus = data.research_classifier?.uncertainty?.ood_status;
    const finalState = terminalResultState === 'poor_quality' || outcomeCode === 'INPUT_UNSUITABLE' || inputStatus === 'LOW_QUALITY' || ['INVALID', 'UNSUPPORTED'].includes(inputStatus)
      ? AssessmentState.INVALID_IMAGE
      : ['category_mismatch', 'unsupported_image'].includes(terminalResultState) || outcomeCode === 'OUT_OF_DISTRIBUTION' || oodStatus === 'OUT_OF_DISTRIBUTION'
        ? AssessmentState.OOD_IMAGE
        : terminalResultState === 'uncertain' || outcomeCode === 'UNCERTAIN' || data.research_classifier?.uncertainty?.status === 'LOW_CONFIDENCE'
          ? AssessmentState.LOW_CONFIDENCE
          : AssessmentState.RESULT_READY;
    finishProcessing(true);
    transitionAssessment(finalState, finalState === AssessmentState.INVALID_IMAGE ? 'IMAGE NEEDS IMPROVEMENT' : finalState === AssessmentState.OOD_IMAGE ? 'IMAGE OUTSIDE SUPPORTED SCOPE' : finalState === AssessmentState.LOW_CONFIDENCE ? 'RESULT UNCERTAIN' : 'RESULT READY');
    state.assessmentId = data.assessment_id;
    const responseRisk = data.risk || {};
    const score = Number.isFinite(responseRisk.score) ? responseRisk.score : null;
    const questionnaire = data.input_type === 'questionnaire';
    const presentation = normaliseAssessmentPresentation(data);
    $('.segmentation-stage').classList.toggle('sweat-summary', questionnaire);
    $('#resultImage').hidden = questionnaire;
    if (questionnaire) $('#resultImage').removeAttribute('src');
    else $('#resultImage').src = state.imageUrl;
    $('#resultRisk').textContent = presentation.primaryLabel.toUpperCase();
    const severityClass = { LOW: 'low', MODERATE: 'moderate', HIGH: 'high', URGENT: 'urgent' }[responseRisk.severity] || (score !== null && score < 40 ? 'low' : 'moderate');
    $('#resultRisk').className = `risk-label ${severityClass}`;
    $('#findingTitle').textContent = presentation.primaryTitle; $('#findingText').textContent = presentation.primaryDescription; renderResultOverview(data);
    $('#qualityScore').textContent = Number.isFinite(data.quality?.score) ? `${data.quality.score}% · ${data.quality.label}` : data.quality?.label || 'Not applicable';
    $('#modelStatus').textContent = presentation.scope;
    $('#clinicalStatus').textContent = data.persistence === 'mysql' ? 'Saved to your local account · no image retained' : 'Guest result · not stored';
    $('#saveProgressButton').innerHTML = data.persistence === 'mysql' ? 'Refresh saved reports <span>→</span>' : 'Create account to save <span>→</span>';
    setSegmentation(data.candidate_region, data.segmentation); setResearchAttention(data.research_classifier); renderAnalysisDashboard(data); showCarePlan(data.care_plan); updateDoctorSupport(data.assessment_risk || data.assessment_result?.assessment_risk || data.risk, data.condition_intelligence?.doctor); renderPatientResult(data);
    if (data.persistence === 'mysql' && state.profile?.patient_id) await loadProgress({ force: true });
    if (questionnaire) {
      $('#attentionLabel').textContent = 'Questionnaire summary';
      $('.result-footnote').textContent = 'Questionnaire inputs use a transparent contribution summary. Grad-CAM and image-region visualisation do not apply to tabular input.';
    } else {
      $('.result-footnote').textContent = 'The overlay shows a visual candidate region or configured segmentation when available. The blue attention layer is Grad-CAM from the real classifier run.';
    }
    const note = $('#concernNote').value.trim();
    const comparison = data.progress_comparison?.summary || 'Analysis metadata is saved for a registered profile. Uploaded images are not stored.';
    $('#progressText').textContent = note ? `Tracking note: “${note}” ${comparison}` : comparison;
    showResultTab('summary'); $('#resultModal').classList.add('show'); $('#resultModal').setAttribute('aria-hidden', 'false');
    $('#stepCount').textContent = questionnaire ? 'STEP 2 OF 2' : 'STEP 3 OF 3';
  } catch (error) {
    if (requestId !== state.assessmentRequestId) return;
    finishProcessing(false);
    const rejectedResultState = String(error?.payload?.assessment_result?.result_state || '').toLowerCase();
    const rejectionState = rejectedResultState === 'poor_quality'
      ? AssessmentState.INVALID_IMAGE
      : ['category_mismatch', 'unsupported_image'].includes(rejectedResultState)
        ? AssessmentState.OOD_IMAGE
        : AssessmentState.ERROR;
    transitionAssessment(
      rejectionState,
      rejectionState === AssessmentState.INVALID_IMAGE
        ? 'IMAGE NEEDS IMPROVEMENT'
        : rejectionState === AssessmentState.OOD_IMAGE
          ? 'IMAGE OUTSIDE SUPPORTED SCOPE'
          : 'ASSESSMENT UNAVAILABLE',
    );
    const message = error?.message || '';
    console.error('DermaMatrix assessment request or result rendering failed.', error);
    const internalFailure = /\b(?:ReferenceError|TypeError|SyntaxError)\b|is not defined|Failed to fetch|NetworkError/i.test(message);
    toast(internalFailure ? 'The assessment could not be completed. Reload the app, confirm it is open at http://127.0.0.1:8000, then try again.' : message || 'We couldn’t complete this assessment. Check your information and try again.');
  } finally {
    if (requestId !== state.assessmentRequestId) return;
    state.assessmentInFlight = false;
    setAssessmentInputBusy(false);
    button.disabled = sweat ? false : !state.file;
    button.innerHTML = sweat ? 'Review questionnaire <span>→</span>' : 'Review image <span>→</span>';
  }
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
  const suggestedSpecialty = state.recommendedSpecialty || 'dermatologist';
  const concern = String($('#directoryConcern')?.value || '').trim();
  const searchFocus = concern ? `${concern} dermatologist` : suggestedSpecialty;
  const query = encodeURIComponent(appointment ? `${searchFocus} appointment options near ${location}` : `${searchFocus} near ${location}`);
  const handoff = $('#directoryHandoffState');
  if (handoff) {
    handoff.classList.add('is-active');
    handoff.querySelector('strong').textContent = appointment ? 'Opening appointment options' : 'Opening nearby specialists';
    handoff.querySelector('p').textContent = `Current ${searchFocus} listings near ${location} open in a new tab. Check the provider’s details and booking options before you decide.`;
  }
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
  const highPriority = ['HIGH', 'VERY_HIGH'].includes(risk.level) || ['PROMPT_MEDICAL_EVALUATION', 'URGENT_EVALUATION'].includes(risk.urgency) || ['HIGH', 'URGENT'].includes(risk.severity);
  const title = highPriority || doctor.recommended ? 'Professional review is recommended' : 'Optional professional support';
  const copy = highPriority
    ? `A professional review could be helpful. Use your location to find a nearby ${specialty.toLowerCase()}.`
    : `If you would like support, find a nearby ${specialty.toLowerCase()} and choose a contact option that works for you.`;
  const heading = $('#doctorSupportTitle'); const description = $('#doctorSupportCopy');
  if (heading) heading.textContent = title;
  if (description) description.textContent = copy;
  const directoryCopy = $('#directorySpecialtyCopy');
  if (directoryCopy) directoryCopy.textContent = doctor.specialty
    ? `Your latest check suggests that a ${specialty.toLowerCase()} may be the right person to speak to.`
    : 'Describe what you need help with, then find a dermatologist near you.';
}

function chooseDirectoryQuery(query) {
  const concern = $('#directoryConcern');
  if (!concern) return;
  concern.value = query;
  concern.focus();
}

async function saveProfile(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget); const payload = Object.fromEntries(form.entries());
  payload.health_data_consent = form.get('health_data_consent') === 'on';
  const button = event.currentTarget.querySelector('[type="submit"]'); button.disabled = true;
  try {
    const data = await requestJSON('/api/profile', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const profile = data.profile;
    state.profile = { ...state.profile, ...profile };
    persistBrowserProfile();
    $('#profileName').textContent = profile.full_name; $('#profileMeta').textContent = profile.patient_id; updateDashboardIdentity(); closeProfile(); await loadProgress({ force: true }); toast('Profile saved in the local project database.');
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
    const profile = await requestJSON('/api/profile', {}, 10000);
    state.profile = { ...state.profile, ...profile };
    $('#profileName').textContent = state.profile.full_name; $('#profileMeta').textContent = state.profile.patient_id;
    updateDashboardIdentity();
  } catch {
    // A local project database may be offline; routine loading displays the same recoverable state.
  }
}

function productPreviewProfile(product) {
  const source = `${product?.id || ''} ${product?.name || ''} ${product?.category || ''}`.toLowerCase();
  if (source.includes('shampoo') || source.includes('cleanser')) return { kind: 'bottle', label: 'Cleansing care' };
  if (source.includes('vitamin') || source.includes('iron') || source.includes('supplement')) return { kind: 'jar', label: 'Wellness care' };
  if (source.includes('nail') || source.includes('cuticle')) return { kind: 'dropper', label: 'Nail care' };
  if (source.includes('search')) return { kind: 'search', label: 'Product search' };
  return { kind: 'tube', label: 'Topical care' };
}

function productPreviewMarkup(product, className = 'catalog-product-preview') {
  const image = product?.image || {};
  const source = supportedExternalUrl(typeof image === 'string' ? image : image.src);
  const alt = String((typeof image === 'object' && image.alt) || product?.image_alt || product?.name || 'Care product');
  if (source) {
    const fallback = productPreviewMarkup({ ...product, image: null }, className);
    return `<div class="${className} ${className}--image"><img class="product-image" src="${escapeHTML(source)}" alt="${escapeHTML(alt)}" loading="lazy" /><span class="product-image-fallback" hidden>${fallback}</span></div>`;
  }
  const preview = productPreviewProfile(product);
  return `<div class="${className} ${className}--${preview.kind}" role="img" aria-label="Illustrated ${escapeHTML(preview.label.toLowerCase())} category preview"><span class="${className}-pack"><i>${escapeHTML(preview.label)}</i></span><small>Category preview</small></div>`;
}

function commerceDestinationMarkup(product, className = 'catalog-destination', actionLabel = null) {
  const commerce = product.commerce || {};
  const primary = commerce.primary || {};
  const destination = supportedExternalUrl(primary.url || product.url);
  const primaryLabel = actionLabel || (primary.is_affiliate ? `Visit ${primary.merchant || 'partner'}` : primary.destination_type === 'DIRECT_PRODUCT_URL' ? 'View product' : 'Compare online');
  const action = destination
    ? `<a class="patient-text-link" href="${escapeHTML(destination)}" target="_blank" rel="noopener noreferrer${primary.is_affiliate ? ' sponsored' : ''}">${escapeHTML(primaryLabel)} ↗</a>`
    : '<button class="patient-text-link" type="button" data-result-action="products">Explore products →</button>';
  const marketplaceLinks = [primary, ...(commerce.alternatives || [])].filter(option => (
    option.destination_type === 'AMAZON_SEARCH' || option.destination_type === 'FLIPKART_SEARCH'
  )).map(option => {
    const url = supportedExternalUrl(option.url);
    const label = option.merchant === 'Amazon India' ? 'Amazon' : 'Flipkart';
    return url ? `<a class="commerce-marketplace-link" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Search ${label} <span aria-hidden="true">↗</span></a>` : '';
  }).filter(Boolean).join('');
  const partnerNote = primary.is_affiliate ? '<small class="commerce-affiliate-label">Partner link · may earn commission</small>' : '';
  return `<div class="${className}">${action}${partnerNote}${marketplaceLinks ? `<div class="commerce-marketplace-links" aria-label="Search this product on marketplaces">${marketplaceLinks}</div>` : ''}</div>`;
}

function consumerProductDescription(product) {
  const purpose = String(product?.purpose || 'Explore options for your routine.');
  const friendlyDescriptions = {
    'sun-protection': 'Everyday sun protection for a simple routine.',
    'scalp-cleanser': 'Gentle cleansing support for a comfortable scalp routine.',
    'gentle-cleanser': 'Gentle cleansing for a simple everyday routine.',
  };
  if (friendlyDescriptions[product?.id]) return friendlyDescriptions[product.id];
  if (/product category|external .*information|user-led/i.test(purpose)) return 'Explore options in this care category and check what suits you.';
  return purpose
    .replace(/^Everyday /, '')
    .replace(/ product discovery for a routine discussion\.?$/i, ' for a simple routine.')
    .replace(/ product discovery\.?$/i, '.')
    .replace(/User-led /gi, '')
    .replace(/ to discuss with (a |your )?(qualified )?clinician or pharmacist\.?/gi, ' and check that it suits you.');
}

function commerceCard(product) {
  const category = String(product.domain || 'care').toLowerCase();
  return `<article class="catalog-card catalog-card--product" data-category="${escapeHTML(category)}"><div class="catalog-media">${productPreviewMarkup(product)}</div><div class="catalog-card-body"><span class="catalog-type">${escapeHTML(product.category || 'CARE PRODUCT')}</span><h3>${escapeHTML(product.name || 'Product search')}</h3><p>${escapeHTML(consumerProductDescription(product))}</p><div class="catalog-key-attributes"><span>${escapeHTML(product.key_property || 'Confirm suitability before use.')}</span></div></div><div class="catalog-card-footer">${commerceDestinationMarkup(product, 'catalog-destination', category === 'search' ? 'Search online' : 'Compare online')}</div></article>`;
}

function installProductImageFallbacks() {
  $$('.product-image').forEach(image => {
    image.onerror = () => {
      image.hidden = true;
      const fallback = image.parentElement?.querySelector('.product-image-fallback');
      if (fallback) fallback.hidden = false;
    };
  });
}

function knowledgeList(items, emptyMessage) {
  const values = (items || []).filter(Boolean);
  return values.length ? `<ul>${values.map(item => `<li>${escapeHTML(String(item))}</li>`).join('')}</ul>` : `<p>${escapeHTML(emptyMessage)}</p>`;
}

function knowledgeMedicationCards(items) {
  if (!items?.length) return '<p>No medication topic is shown for this guide. Discuss persistent changes with a qualified clinician.</p>';
  return items.map(item => `<div class="knowledge-medication"><strong>${escapeHTML(item.name)}</strong><small>${escapeHTML(item.access)}</small><p>${escapeHTML(item.note)}</p></div>`).join('');
}

async function openKnowledgeTopic(topicId) {
  let panel = $('#knowledgeTopicPanel');
  if (!panel) {
    panel = document.createElement('section');
    panel.id = 'knowledgeTopicPanel';
    panel.className = 'knowledge-topic-panel';
    $('#careContext').insertAdjacentElement('afterend', panel);
  }
  panel.hidden = false;
  panel.innerHTML = '<p class="eyebrow">CONDITION GUIDE</p><p>Loading source-linked information…</p>';
  try {
    const payload = await requestJSON(`/api/knowledge/conditions/${encodeURIComponent(topicId)}`, {}, 10000);
    const topic = payload.topic || {};
    const references = (topic.evidence_references || []).map(reference => {
      const url = supportedExternalUrl(reference.url);
      return url ? `<a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(reference.title)} ↗</a>` : escapeHTML(reference.title || 'Source');
    }).join(' · ');
    panel.innerHTML = `<div class="knowledge-topic-head"><div><p class="eyebrow">EDUCATIONAL CONDITION GUIDE</p><h3>${escapeHTML(topic.name || 'Condition guide')}</h3><p>${escapeHTML(topic.description || '')}</p></div><button class="text-button" type="button" data-close-knowledge>Close</button></div><div class="knowledge-topic-grid"><article><strong>Common features</strong>${knowledgeList(topic.visual_features, 'Features can overlap with other conditions.')}</article><article><strong>What can contribute</strong>${knowledgeList(topic.common_contributors, 'A clinician can help identify relevant contributors.')}</article><article><strong>Care to discuss</strong>${knowledgeList(topic.care_options, 'Discuss suitable care with a clinician or pharmacist.')}</article><article><strong>When to seek care</strong>${knowledgeList(topic.red_flags, 'Seek care if the concern persists, changes, or worries you.')}</article></div><section class="knowledge-treatment"><strong>Medication topics to discuss</strong>${knowledgeMedicationCards(topic.medication_topics)}</section><div class="knowledge-topic-grid"><article><strong>Routine</strong>${knowledgeList(topic.daily_routine, 'No routine is suggested.')}</article><article><strong>Diet & lifestyle</strong>${knowledgeList(topic.diet_lifestyle, 'Use a balanced diet and avoid self-treating a presumed deficiency.')}</article></div><p class="knowledge-notice">${escapeHTML(topic.medical_notice || '')} ${escapeHTML(topic.medication_notice || '')}</p>${references ? `<p class="knowledge-sources"><strong>Sources:</strong> ${references}</p>` : ''}`;
    panel.querySelector('[data-close-knowledge]')?.addEventListener('click', () => { panel.hidden = true; });
    panel.scrollIntoView({ behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth', block: 'start' });
  } catch {
    panel.innerHTML = '<p class="eyebrow">CONDITION GUIDE</p><p>Information could not be loaded right now. Please try again.</p>';
  }
}

function productCatalogSkeletons() {
  return Array.from({ length: 8 }, () => '<article class="catalog-card catalog-skeleton" aria-hidden="true"><div></div><span></span><strong></strong><p></p><p></p></article>').join('');
}

function setProductTag(tag = '') {
  state.productTag = tag;
  renderDiscoveryCatalog();
}

function renderProductTagFilters(items) {
  const tagContainer = $('#productTagFilters');
  if (!tagContainer) return;
  const tags = [...new Set(items.flatMap(item => item.product.tags || []))]
    .sort((first, second) => first.localeCompare(second))
    .slice(0, 12);
  if (state.productTag && !tags.includes(state.productTag)) state.productTag = '';
  tagContainer.innerHTML = tags.length
    ? tags.map(tag => `<button class="${tag === state.productTag ? 'selected' : ''}" type="button" data-product-tag="${escapeHTML(tag)}" aria-pressed="${String(tag === state.productTag)}">${escapeHTML(tag)}</button>`).join('')
    : '<p class="filter-empty">No additional care-focus filters are available for this search.</p>';
  $$('[data-product-tag]').forEach(button => { button.onclick = () => setProductTag(button.dataset.productTag); });
}

function renderActiveProductFilters() {
  const container = $('#activeProductFilters');
  if (!container) return;
  const filters = [
    state.productFilter !== 'all' ? { label: state.productFilter === 'hair' ? 'Hair & scalp' : readableStatus(state.productFilter), action: 'category' } : null,
    state.productTag ? { label: state.productTag, action: 'tag' } : null,
  ].filter(Boolean);
  container.hidden = !filters.length;
  container.innerHTML = filters.length
    ? `<span>Applied</span>${filters.map(filter => `<button type="button" data-clear-product-filter="${filter.action}">${escapeHTML(filter.label)} <b aria-hidden="true">×</b></button>`).join('')}<button class="clear-product-filters" type="button" data-clear-product-filter="all">Clear all</button>`
    : '';
  $$('[data-clear-product-filter]').forEach(button => {
    button.onclick = () => {
      const target = button.dataset.clearProductFilter;
      if (target === 'all' || target === 'category') state.productFilter = 'all';
      if (target === 'all' || target === 'tag') state.productTag = '';
      $$('.product-tabs button').forEach(tab => {
        const selected = tab.dataset.filter === state.productFilter;
        tab.classList.toggle('selected', selected); tab.setAttribute('aria-selected', String(selected));
      });
      renderDiscoveryCatalog();
    };
  });
}

function renderDiscoveryCatalog() {
  if (state.productLoading) {
    $('#productCatalog').innerHTML = productCatalogSkeletons();
    $('#productResultCount').textContent = 'Loading products';
    $('#productResultMeta').textContent = 'Refreshing discovery categories';
    return;
  }
  const query = $('#productSearch').value.trim().toLowerCase();
  const commerceItems = state.productCatalog.map(product => ({
    category: String(product.domain || '').toLowerCase(), product,
    searchText: `${product.name || ''} ${product.purpose || ''} ${product.key_property || ''} ${(product.tags || []).join(' ')} ${(product.commerce || {}).query || ''}`.toLowerCase(),
  }));
  const isServerSearch = Boolean(state.productCatalogQuery) && query === state.productCatalogQuery.toLowerCase();
  const visible = commerceItems.filter(item => {
    const matchesCategory = state.productFilter === 'all' || item.category === state.productFilter;
    const matchesTag = !state.productTag || (item.product.tags || []).includes(state.productTag);
    return matchesCategory && matchesTag && (isServerSearch || !query || item.searchText.includes(query));
  });
  if (state.productSort === 'name') visible.sort((first, second) => String(first.product.name || '').localeCompare(String(second.product.name || '')));
  if (state.productSort === 'category') visible.sort((first, second) => String(first.product.category || '').localeCompare(String(second.product.category || '')) || String(first.product.name || '').localeCompare(String(second.product.name || '')));
  $('#productCatalog').innerHTML = visible.length
    ? visible.map(item => commerceCard(item.product)).join('')
    : '<div class="catalog-empty"><span aria-hidden="true">⌕</span><strong>No products found</strong><p>Try a broader search, remove a filter, or browse another category.</p><button class="text-button" type="button" data-clear-product-filter="all">Clear filters</button></div>';
  $('#productResultCount').textContent = `${visible.length} ${visible.length === 1 ? 'result' : 'results'}`;
  $('#productResultMeta').textContent = state.productCatalogQuery ? `Results for “${state.productCatalogQuery}”` : 'Care categories to explore';
  installProductImageFallbacks();
  renderProductTagFilters(commerceItems);
  renderActiveProductFilters();
}

async function loadCommerceCatalog({ force = false, query = null } = {}) {
  const requestedQuery = String(query ?? state.productCatalogQuery ?? '').trim();
  if (state.productCatalogLoadPromise && !force) return state.productCatalogLoadPromise;
  if (state.productCatalogLoaded && !force && requestedQuery === state.productCatalogQuery) return state.productCatalog;
  const endpoint = requestedQuery
    ? `/api/products/search?q=${encodeURIComponent(requestedQuery)}`
    : '/api/products?area=All&mode=discovery&risk_score=0';
  const requestKey = ++state.productCatalogRequestKey;
  state.productLoading = true;
  renderDiscoveryCatalog();
  state.productCatalogLoadPromise = requestJSON(endpoint, {}, 10000)
    .then(payload => {
      if (requestKey !== state.productCatalogRequestKey) return state.productCatalog;
      state.productCatalog = Array.isArray(payload.items) ? payload.items : [];
      state.productCatalogMeta = payload;
      state.productCatalogQuery = requestedQuery;
      state.productCatalogLoaded = true;
      renderDiscoveryCatalog();
      return state.productCatalog;
    })
    .catch(() => {
      if (requestKey !== state.productCatalogRequestKey) return state.productCatalog;
      state.productCatalog = [];
      state.productCatalogMeta = null;
      state.productCatalogQuery = requestedQuery;
      state.productCatalogLoaded = true;
      renderDiscoveryCatalog();
      return [];
    })
    .finally(() => {
      if (requestKey === state.productCatalogRequestKey) {
        state.productCatalogLoadPromise = null;
        state.productLoading = false;
        renderDiscoveryCatalog();
      }
    });
  return state.productCatalogLoadPromise;
}

function setProductFilter(filter = 'all') {
  state.productFilter = filter;
  state.productTag = '';
  $$('.product-tabs button').forEach(tab => {
    const selected = tab.dataset.filter === filter;
    tab.classList.toggle('selected', selected); tab.setAttribute('aria-selected', String(selected));
  });
}

async function searchProducts(event) {
  event?.preventDefault();
  const query = $('#productSearch').value.trim();
  setProductFilter('all');
  await loadCommerceCatalog({ force: true, query });
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
  const settingsButton = $('#settingsThemeButton');
  if (settingsButton) settingsButton.textContent = dark ? 'Use day theme' : 'Use night theme';
  document.querySelector('meta[name="theme-color"]').content = dark ? '#071a33' : '#f6f8fb';
}

function restoreTheme() { applyTheme(localStorage.getItem('dermamatrix_theme') || 'light'); }

function applyConsumerCopy() {
  $('#workspaceSearch').placeholder = 'Search your care';
  $('#workspaceSearch').setAttribute('aria-label', 'Search your care');
  const productEyebrow = $('#products .products-heading .eyebrow');
  const productTitle = $('#productsTitle');
  const productCopy = $('#products .products-heading p:not(.eyebrow)');
  if (productEyebrow) productEyebrow.textContent = 'CARE PRODUCTS';
  if (productTitle) productTitle.textContent = 'Find products for your routine.';
  if (productCopy) productCopy.textContent = 'Search by product, ingredient, brand, or everyday care need.';
  $('#careContext strong').textContent = 'Explore at your own pace';
  $('#careContext p').textContent = 'Browse product categories and compare options online.';
  $('.catalog-disclaimer').textContent = 'Shopping links are optional and do not change your health check.';
  $('#resultTitle').textContent = 'Your health check';
  $('.modal-disclaimer').textContent = 'AI health check';
  $('.disclaimer-details summary').textContent = 'Important information';
}

async function clearLocalProfile() {
  try { await requestJSON('/api/auth/logout', { method: 'POST' }); } catch { /* local sign-out still continues */ }
  localStorage.removeItem('dermamatrix_profile'); state.profile = null; state.isGuest = false;
  $('#profileName').textContent = 'Guest workspace'; $('#profileMeta').textContent = 'Sign in to save';
  state.assessmentId = null; state.latestRisk = null; state.recommendedSpecialty = 'dermatologist'; state.nearbySearchLocation = '';
  state.routines = []; state.checkins = []; state.analyses = []; state.progressLoadedFor = null; resetImage(); updateDashboardIdentity(); renderProgress();
  showAuthGate('login'); setAuthMessage('You have been signed out.', true);
}

const escapeHTML = value => String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));

function currentDate() { return new Date().toISOString().slice(0, 10); }

function updateDashboardIdentity() {
  const name = state.profile?.full_name?.trim().split(/\s+/)[0] || '';
  $('#dashboardUser').textContent = name;
  $('#dashboardUserGreeting').hidden = !name;
  const profileButton = $('#topProfileButton');
  if (profileButton) profileButton.textContent = state.profile?.patient_id ? 'Profile' : 'Create profile';
}

function assessmentConcernScore(analysis) {
  const value = analysis?.summary?.assessment_risk?.score ?? analysis?.summary?.assessment_result?.assessment_risk?.score ?? analysis?.summary?.risk?.score;
  const numeric = Number(value);
  return value !== null && value !== '' && Number.isFinite(numeric) ? numeric : null;
}

function renderDashboardInsight(analyses, routines) {
  let insight = $('#dashboardInsight');
  if (!insight) {
    insight = document.createElement('section');
    insight.id = 'dashboardInsight'; insight.className = 'dashboard-insight'; insight.hidden = true;
    $('#dashboardSnapshot')?.closest('.health-snapshot')?.insertAdjacentElement('afterend', insight);
  }
  const latest = analyses[0];
  const latestScore = assessmentConcernScore(latest);
  const earlierSameArea = latest && analyses.slice(1).find(item => item.area === latest.area && assessmentConcernScore(item) !== null);
  const previousScore = assessmentConcernScore(earlierSameArea);
  if (latest && latestScore !== null && earlierSameArea && previousScore !== null) {
    const delta = latestScore - previousScore;
    const direction = delta === 0 ? 'unchanged' : delta < 0 ? `${Math.abs(delta)} points lower` : `${delta} points higher`;
    insight.hidden = false;
    insight.innerHTML = `<div><p class="eyebrow">YOUR TREND</p><h2>${escapeHTML(String(latest.area))} score is ${escapeHTML(direction)}.</h2><p>Compare your saved check-ins when you notice a meaningful change.</p></div><div class="dashboard-insight-metric"><small>LATEST / PREVIOUS</small><strong>${latestScore}<span>/100</span> <b>·</b> ${previousScore}<span>/100</span></strong><button class="text-button" data-dashboard-nav="progress">View journey →</button></div>`;
    return;
  }
  if (latest) {
    insight.hidden = false;
    insight.innerHTML = `<div><p class="eyebrow">YOUR BASELINE</p><h2>Your first ${escapeHTML(String(latest.area).toLowerCase())} check-in is saved.</h2><p>Add another only when something meaningfully changes.</p></div><div class="dashboard-insight-metric"><small>SAVED CHECK-INS</small><strong>${analyses.length}</strong><button class="text-button" data-dashboard-nav="home">Check an area →</button></div>`;
    return;
  }
  if (routines.length) {
    insight.hidden = false;
    insight.innerHTML = `<div><p class="eyebrow">YOUR ROUTINE</p><h2>Your care plan is ready for a check-in.</h2><p>Log an update whenever your symptoms or routine changes.</p></div><div class="dashboard-insight-metric"><small>ACTIVE ROUTINES</small><strong>${routines.length}</strong><button class="text-button" data-dashboard-nav="progress">Open journey →</button></div>`;
    return;
  }
  insight.hidden = true;
  insight.innerHTML = '';
}

function renderDashboard() {
  const analyses = state.analyses || [];
  const routines = state.routines || [];
  const checkins = state.checkins || [];
  const latestAnalysis = analyses[0];
  const latestCheckin = checkins[0];
  const latestRisk = latestAnalysis?.summary?.assessment_risk || latestAnalysis?.summary?.assessment_result?.assessment_risk || latestAnalysis?.summary?.risk;
  const latestFinding = latestAnalysis?.summary?.condition_intelligence?.finding;
  const snapshot = $('#dashboardSnapshot');
  if (snapshot) {
    const cards = [];
    if (latestAnalysis) {
      const result = latestFinding?.name || latestAnalysis.summary?.classification?.top_prediction?.condition || 'Screening summary saved';
      cards.push(`<article class="snapshot-card"><span>◌</span><div><small>LATEST ASSESSMENT</small><strong>${escapeHTML(result)}</strong><p>${escapeHTML(String(latestAnalysis.created_at).slice(0, 10))} · ${escapeHTML(latestAnalysis.area)} assessment</p></div><button class="text-button" data-dashboard-nav="progress">View →</button></article>`);
      cards.push(`<article class="snapshot-card"><span>⌁</span><div><small>PERSONAL SCORE</small><strong>${latestRisk?.score === undefined || latestRisk?.score === null ? 'No score yet' : `${escapeHTML(latestRisk.score)}/100 · ${escapeHTML(readableStatus(latestRisk.level || 'recorded'))}`}</strong><p>Based on your latest saved check-in.</p></div></article>`);
    }
    if (routines.length) {
      cards.push(`<article class="snapshot-card"><span>◔</span><div><small>ACTIVE ROUTINES</small><strong>${routines.length} ${routines.length === 1 ? 'routine' : 'routines'} in progress</strong><p>${escapeHTML(routines[0].routine_name)}${routines.length > 1 ? ` + ${routines.length - 1} more` : ''}</p></div><button class="text-button" data-dashboard-nav="progress">Manage →</button></article>`);
    }
    if (latestCheckin) {
      cards.push(`<article class="snapshot-card"><span>⌁</span><div><small>LATEST CHECK-IN</small><strong>${escapeHTML(latestCheckin.reported_trend)}</strong><p>Recorded on ${escapeHTML(latestCheckin.checkin_date)}.</p></div></article>`);
    }
    snapshot.innerHTML = cards.length
      ? cards.slice(0, 4).join('')
      : '<article class="snapshot-card snapshot-empty"><span>◌</span><div><small>FIRST STEP</small><strong>Your journey starts here</strong><p>Complete an assessment to begin.</p></div><button class="text-button" data-dashboard-nav="home">Check My Health →</button></article>';
  }
  renderDashboardInsight(analyses, routines);
  $('#dashboardActivity').innerHTML = !analyses.length
    ? '<p class="empty-state">No assessments yet. Complete your first assessment to begin your timeline.</p>'
    : analyses.slice(0, 4).map(item => {
      const classification = item.summary?.classification || {};
      const prediction = classification.top_prediction;
      const title = prediction ? prediction.condition : `${readableStatus(item.area)} assessment`;
      const meta = prediction
        ? Number.isFinite(prediction.calibrated_probability) ? `${Math.round(prediction.calibrated_probability * 100)}% estimated likelihood` : 'Assessment saved'
        : 'Assessment saved';
      return `<article class="dashboard-record"><span>◌</span><div><strong>${escapeHTML(title)}</strong><small>${escapeHTML(item.area)} · ${escapeHTML(meta)}</small></div><time>${escapeHTML(String(item.created_at).slice(0, 10))}</time></article>`;
    }).join('');
  const nextStep = $('#nextStepCard');
  if (nextStep) {
    const highPriority = ['HIGH', 'VERY_HIGH'].includes(latestRisk?.level) || ['PROMPT_MEDICAL_EVALUATION', 'URGENT_EVALUATION'].includes(latestRisk?.urgency);
    if (highPriority) {
      nextStep.hidden = false;
      nextStep.innerHTML = '<p class="eyebrow">NEXT STEP</p><h2>Professional review is recommended</h2><p>Find current specialist listings near you.</p><button class="button primary" data-dashboard-nav="support">Find a Doctor <span>→</span></button>';
    } else if (latestAnalysis && routines.length === 0) {
      nextStep.hidden = false;
      nextStep.innerHTML = '<p class="eyebrow">NEXT STEP</p><h2>Start a routine</h2><p>Track a clinician-recorded care plan over time.</p><button class="button primary" data-dashboard-nav="progress">Open My Journey <span>→</span></button>';
    } else if (latestCheckin) {
      nextStep.hidden = false;
      nextStep.innerHTML = '<p class="eyebrow">NEXT STEP</p><h2>Review your journey</h2><p>Your latest self-reported check-in is saved.</p><button class="button primary" data-dashboard-nav="progress">View My Journey <span>→</span></button>';
    } else {
      nextStep.hidden = true;
      nextStep.innerHTML = '';
    }
  }
  $$('[data-dashboard-nav]').forEach(button => { button.onclick = () => showPage(button.dataset.dashboardNav); });
}

function resetRoutineForm() {
  $('#routineForm').reset(); $('#editingRoutineId').value = ''; $('#routineStartDate').value = currentDate();
  $('#routineFormTitle').textContent = 'Add a routine'; $('#cancelRoutineEdit').hidden = true;
}

function reportClassification(summary) {
  const result = summary?.assessment_result || {};
  if (result.contract_version) {
    const condition = result.condition || {};
    if (!condition.available || !condition.name) return 'Health check summary';
    return Number.isFinite(condition.estimated_likelihood)
      ? `${condition.name} · ${Math.round(condition.estimated_likelihood * 100)}% estimated likelihood`
      : `${condition.name} · research ranking only`;
  }
  const classifier = summary?.classification || {};
  const prediction = classifierPredictions(classifier)[0];
  return prediction
    ? Number.isFinite(prediction.calibratedProbability) ? `${prediction.label} · ${Math.round(prediction.calibratedProbability * 100)}% estimated likelihood` : `${prediction.label} · research ranking only`
    : 'Health check summary';
}

function renderReportRegister() {
  let register = $('#reportRegister');
  if (!register) {
    register = document.createElement('section'); register.id = 'reportRegister'; register.className = 'report-register';
    $('.history-card')?.insertAdjacentElement('afterend', register);
  }
  const downloadButton = $('#downloadHistoryButton');
  if (!state.profile?.patient_id) {
    if (downloadButton) downloadButton.hidden = true;
    register.innerHTML = '<div class="report-register-heading"><div><p class="eyebrow">PAST RESULTS</p><h3>Your previous checks</h3><p>Create an account to keep your results in one place.</p></div></div><p class="empty-state">Your past results will appear here once they are saved.</p>';
    return;
  }
  const analyses = state.analyses || [];
  const cards = analyses.length ? analyses.slice(0, 6).map(item => {
    const summary = item.summary || {};
    const assessmentRisk = summary.assessment_risk || summary.assessment_result?.assessment_risk || summary.risk || {};
    const concern = assessmentRisk.score === undefined || assessmentRisk.score === null ? 'Check saved' : `${readableStatus(assessmentRisk.level || 'recorded')} concern`;
    return `<article class="report-compact-card"><time>${escapeHTML(String(item.created_at).slice(0, 10))}</time><div><span>${escapeHTML(item.area)} check</span><strong>${escapeHTML(reportClassification(summary))}</strong><small>${escapeHTML(concern)}</small></div><div class="report-card-actions"><button class="text-button" data-view-report="${escapeHTML(item.assessment_id)}">View result</button><button class="text-button" data-download-report="${escapeHTML(item.assessment_id)}">PDF</button></div></article>`;
  }).join('') : '<p class="empty-state">Your saved results will appear here after a check.</p>';
  register.innerHTML = `<div class="report-register-heading"><div><p class="eyebrow">PAST RESULTS</p><h3>Your previous checks</h3><p>Open a saved result whenever you want to look back.</p></div><span>${analyses.length} saved</span><div class="report-register-actions"></div></div><div class="report-compact-list">${cards}</div>${analyses.length > 6 ? `<p class="report-list-note">Showing your six most recent results.</p>` : ''}`;
  if (downloadButton) {
    downloadButton.hidden = false;
    register.querySelector('.report-register-actions')?.append(downloadButton);
  }
  $$('[data-view-report]').forEach(button => { button.onclick = () => showSavedReport(button.dataset.viewReport); });
  $$('[data-download-report]').forEach(button => { button.onclick = () => downloadSavedReport(button.dataset.downloadReport); });
}

function showSavedReport(assessmentId) {
  const item = state.analyses.find(analysis => analysis.assessment_id === assessmentId);
  if (!item) return toast('This saved report is no longer available.');
  const data = { ...item.summary, research_classifier: item.summary?.classification || {} };
  const questionnaire = data.input_type === 'questionnaire';
  const presentation = normaliseAssessmentPresentation(data);
  state.assessmentId = assessmentId;
  $('.segmentation-stage').classList.toggle('sweat-summary', questionnaire);
  $('#resultImage').hidden = true; $('#resultImage').removeAttribute('src'); $('#segmentationOverlay').hidden = true; $('#attentionMap').hidden = true;
  $('#resultRisk').textContent = presentation.primaryLabel.toUpperCase();
  const severityClass = { LOW: 'low', MODERATE: 'moderate', HIGH: 'high', URGENT: 'urgent' }[data.risk?.severity] || ((data.risk?.score || 0) < 40 ? 'low' : 'moderate');
  $('#resultRisk').className = `risk-label ${severityClass}`;
  $('#findingTitle').textContent = presentation.primaryTitle;
  $('#findingText').textContent = presentation.primaryDescription;
  renderResultOverview(data);
  $('#qualityScore').textContent = data.quality?.score === null || data.quality?.score === undefined ? data.quality?.label || 'Not applicable' : `${data.quality.score}% · ${data.quality.label}`;
  $('#modelStatus').textContent = presentation.scope;
  $('#clinicalStatus').textContent = 'Saved metadata · no image retained';
  setSegmentation(data.candidate_region, data.segmentation); setResearchAttention(data.research_classifier); renderAnalysisDashboard(data); showCarePlan(data.care_plan || {}); updateDoctorSupport(data.assessment_risk || data.assessment_result?.assessment_risk || data.risk || {}, data.condition_intelligence?.doctor); renderPatientResult(data);
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
  let emptyJourney = $('#journeyEmptyState');
  if (!emptyJourney) {
    emptyJourney = document.createElement('section');
    emptyJourney.id = 'journeyEmptyState'; emptyJourney.className = 'journey-empty-state';
    emptyJourney.innerHTML = '<span aria-hidden="true">◔</span><div><p class="eyebrow">YOUR JOURNEY</p><h3>Your journey starts here.</h3><p>Complete your first assessment to begin tracking your health story.</p><button class="button primary" data-dashboard-nav="home">Check My Health <span>→</span></button></div>';
  }
  // Keep the guest empty state outside account-only sections.  It must remain
  // visible even while routines, check-ins, and saved reports are hidden.
  $('.progress-heading')?.insertAdjacentElement('afterend', emptyJourney);
  const workspaceSections = ['.journey-status-section', '#reportRegister', '.progress-layout', '.checkin-card', '.history-card'];
  workspaceSections.forEach(selector => { const element = $(selector); if (element) element.hidden = !hasProfile; });
  const progressActions = $('.progress-actions');
  if (progressActions) progressActions.hidden = !hasProfile;
  emptyJourney.hidden = hasProfile;
  const latest = checkins[0];
  $('#progressSummary').innerHTML = `<article><span>◔</span><strong>${routines.length}</strong><small>active routines</small></article><article><span>◷</span><strong>${latest ? escapeHTML(latest.checkin_date) : '—'}</strong><small>latest check-in</small></article><article><span>⌁</span><strong>${latest ? escapeHTML(readableStatus(latest.reported_trend)) : '—'}</strong><small>current trend</small></article>`;
  $('#openProfileFromProgress').textContent = hasProfile ? 'Profile connected' : 'Set up profile';
  $('#monitoringNote').textContent = !hasProfile
    ? 'Create an account to save routines, check-ins, and past results.'
    : latest
      ? `Last check-in: ${latest.checkin_date}. Add another whenever you notice a meaningful change.`
      : 'Add your first check-in after you begin a routine.';
  $('#routineList').innerHTML = !hasProfile ? '<p class="empty-state">Set up a profile to save routines and progress.</p>' : !routines.length ? '<p class="empty-state">No routines yet. Add the first routine you want to follow.</p>' : routines.map(routine => {
    const routineCheckins = checkins.filter(item => String(item.routine_id) === String(routine.routine_id));
    const lastCheckin = routineCheckins[0];
    const trend = lastCheckin ? readableStatus(lastCheckin.reported_trend) : 'Not checked in yet';
    const lastUpdate = lastCheckin ? `Last check-in: ${lastCheckin.checkin_date}` : `Started ${routine.start_date}`;
    return `<article class="routine-item"><div class="routine-item-main"><span>${escapeHTML(routine.condition_label)}</span><h4>${escapeHTML(routine.routine_name)}</h4><p>${escapeHTML(lastUpdate)} · ${escapeHTML(trend)}</p>${routine.notes ? `<small>${escapeHTML(routine.notes)}</small>` : ''}</div><div class="routine-actions"><button class="button quiet routine-checkin-button" data-checkin-routine="${routine.routine_id}">Check in</button><button class="text-button" data-edit-routine="${routine.routine_id}">Edit</button><button class="text-button danger-button" data-delete-routine="${routine.routine_id}">Delete</button></div></article>`;
  }).join('');
  $('#checkinRoutine').innerHTML = `<option value="">Choose a saved routine</option>${routines.map(routine => `<option value="${routine.routine_id}">${escapeHTML(routine.condition_label)} · ${escapeHTML(routine.routine_name)}</option>`).join('')}`;
  const medicalHistory = hasProfile && (state.profile.past_history || state.profile.current_history) ? `<details class="journey-history-details"><summary>Your saved health notes</summary><div>${state.profile.past_history ? `<p><strong>Past:</strong> ${escapeHTML(state.profile.past_history)}</p>` : ''}${state.profile.current_history ? `<p><strong>Current:</strong> ${escapeHTML(state.profile.current_history)}</p>` : ''}</div></details>` : '';
  const timeline = !hasProfile ? '<p class="empty-state">Your updates will be available after profile setup.</p>' : !checkins.length ? '<p class="empty-state">Save your first check-in to begin tracking progress.</p>' : checkins.slice(0, 6).map(item => `<article class="history-item"><div><strong>${escapeHTML(readableStatus(item.reported_trend))}</strong><p>${escapeHTML(item.condition_label)} · ${escapeHTML(item.routine_name)}</p>${item.note ? `<small>${escapeHTML(item.note)}</small>` : ''}</div><time>${escapeHTML(item.checkin_date)}</time></article>`).join('');
  $('#progressHistory').innerHTML = medicalHistory + timeline;
  $$('[data-edit-routine]').forEach(button => { button.onclick = () => editRoutine(button.dataset.editRoutine); });
  $$('[data-delete-routine]').forEach(button => { button.onclick = () => deleteRoutine(button.dataset.deleteRoutine); });
  $$('[data-checkin-routine]').forEach(button => { button.onclick = () => startRoutineCheckin(button.dataset.checkinRoutine); });
  renderReportRegister();
  const reportRegister = $('#reportRegister');
  if (reportRegister) reportRegister.hidden = !hasProfile;
  renderDashboard();
}

async function loadProgress({ force = false } = {}) {
  if (!state.profile?.patient_id) { renderProgress(); return; }
  const patientId = state.profile.patient_id;
  if (!force && state.progressLoadedFor === patientId) { renderProgress(); return; }
  if (state.progressLoadPromise) return state.progressLoadPromise;
  state.progressLoadPromise = (async () => {
    try {
      const [routineData, checkinData, analysisData] = await Promise.all([
        requestJSON('/api/routines'),
        requestJSON('/api/progress-checkins'),
        requestJSON('/api/analysis-history'),
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

function startRoutineCheckin(routineId) {
  const select = $('#checkinRoutine');
  if (!select) return;
  select.value = routineId;
  $('.checkin-card')?.scrollIntoView({ behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth', block: 'start' });
  window.setTimeout(() => $('#checkinTrend')?.focus({ preventScroll: true }), 250);
}

async function saveRoutine(event) {
  event.preventDefault();
  if (!state.profile?.patient_id) { openProfile(); return toast('Set up a profile before saving routines.'); }
  const submitButton = event.currentTarget.querySelector('[type="submit"]');
  if (submitButton.disabled) return;
  const payload = { condition_label: $('#conditionLabel').value, routine_name: $('#routineName').value, start_date: $('#routineStartDate').value, notes: $('#routineNotes').value };
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
    await requestJSON(`/api/routines/${routineId}`, { method: 'DELETE' });
    await loadProgress({ force: true }); toast('Routine deleted.');
  } catch (error) { toast(error.message || 'Could not delete this routine.'); }
}

async function saveCheckin(event) {
  event.preventDefault();
  if (!state.profile?.patient_id) { openProfile(); return toast('Set up a profile before saving check-ins.'); }
  const form = event.currentTarget;
  const submitButton = form.querySelector('[type="submit"]');
  if (submitButton.disabled) return;
  const file = $('#checkinImage').files[0];
  const payload = { routine_id: $('#checkinRoutine').value, checkin_date: $('#checkinDate').value, reported_trend: $('#checkinTrend').value, discomfort: $('#checkinDiscomfort').value, change: $('#checkinChange').value, note: $('#checkinNote').value };
  submitButton.disabled = true;
  try {
    const data = await requestJSON('/api/progress-checkins', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    form.reset(); $('#checkinDate').value = currentDate(); await loadProgress({ force: true });
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
$('#screenDetails').addEventListener('toggle', event => { if (event.currentTarget.open) updateAssessmentProgress(3); });
const drop = $('#dropZone');
['dragenter', 'dragover'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.remove('dragging'); }));
drop.addEventListener('drop', event => setImage(event.dataTransfer.files[0]));
$('#analyzeButton').onclick = analyze; $('#saveProgressButton').onclick = saveProgress; $('#viewCareButton').onclick = viewCare;
$$('[data-result-tab]').forEach(button => { button.onclick = () => showResultTab(button.dataset.resultTab); });
$('#doctorSearchForm').onsubmit = searchDoctors; $('#directorySearchForm').onsubmit = searchDirectory;
$('#useResultLocationButton').onclick = () => useNearbyLocation({ target: 'result' });
$('#useDirectoryLocationButton').onclick = () => useNearbyLocation({ target: 'directory' });
$$('[data-directory-query]').forEach(button => { button.onclick = () => chooseDirectoryQuery(button.dataset.directoryQuery || ''); });
$('#resultAppointmentSearchButton').onclick = () => openAppointmentOptions($('#doctorLocation').value === 'Current device location' ? state.nearbySearchLocation : $('#doctorLocation').value);
$('#appointmentSearchButton').onclick = () => openAppointmentOptions($('#directoryLocation').value === 'Current device location' ? state.nearbySearchLocation : $('#directoryLocation').value);
$('#profileButton').onclick = openProfile; $('#topProfileButton').onclick = openProfile; $('#openProfileFromProgress').onclick = openProfile; $('#navProfileButton').onclick = openProfile; $('#navLogoutButton').onclick = clearLocalProfile; $('#profileForm').onsubmit = saveProfile;
$$('[data-auth-tab]').forEach(button => { button.onclick = () => setAuthTab(button.dataset.authTab); });
$('#registerForm').onsubmit = registerAccount; $('#loginForm').onsubmit = loginAccount; $('#continueGuestButton').onclick = continueAsGuest;
$$('[data-auth-password-toggle]').forEach(button => {
  button.onclick = () => {
    const input = document.getElementById(button.dataset.authPasswordToggle);
    if (!input) return;
    const showing = input.type === 'text'; input.type = showing ? 'password' : 'text';
    button.setAttribute('aria-pressed', String(!showing));
    button.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
    button.querySelector('span').textContent = showing ? '◉' : '◌'; input.focus();
  };
});
$$('.auth-form input').forEach(input => {
  input.addEventListener('invalid', () => {
    input.setAttribute('aria-invalid', 'true'); input.closest('.auth-field')?.classList.add('is-invalid');
  });
  input.addEventListener('input', () => {
    input.removeAttribute('aria-invalid'); input.closest('.auth-field')?.classList.remove('is-invalid');
  });
});
$('#forgotPasswordButton').onclick = () => setAuthMessage('Password reset is not available yet. Please contact the person who manages your DermaMatrix account for help.');
$$('[data-close-modal]').forEach(button => { button.onclick = closeResult; });
$$('[data-close-profile]').forEach(button => { button.onclick = closeProfile; });
$('.menu-button').onclick = () => $('.sidebar').classList.toggle('open');
document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeResult(); closeProfile(); } });
$$('.product-tabs button').forEach(button => { button.onclick = () => { setProductFilter(button.dataset.filter); renderDiscoveryCatalog(); }; });
$('#productSearch').oninput = renderDiscoveryCatalog;
$('#productSearchForm').onsubmit = searchProducts;
$('#productSort').onchange = event => { state.productSort = event.target.value; renderDiscoveryCatalog(); };
$('#productFiltersToggle').onclick = event => {
  const panel = $('#productFilterPanel');
  const opening = panel.hidden;
  panel.hidden = !opening;
  event.currentTarget.setAttribute('aria-expanded', String(opening));
  event.currentTarget.classList.toggle('selected', opening);
};
$$('[data-product-query]').forEach(button => { button.onclick = () => { $('#productSearch').value = button.dataset.productQuery || ''; searchProducts(); }; });
$('#workspaceSearch').onkeydown = event => {
  if (event.key !== 'Enter') return;
  const query = event.currentTarget.value.trim();
  if (!query) return;
  $('#productSearch').value = query; showPage('products'); searchProducts();
};
$('#notificationsToggle').onchange = event => { persistPreferences({ notifications_enabled: event.target.checked }); toast(event.target.checked ? 'Care reminders enabled.' : 'Care reminders disabled.'); };
$('#motionToggle').onchange = event => { persistPreferences({ reduced_motion: event.target.checked }); toast(event.target.checked ? 'Reduced motion enabled.' : 'Reduced motion disabled.'); };
$('#clearProfileButton').onclick = clearLocalProfile;
$('#affiliateInfoButton').onclick = () => toast('Partner links are labelled. They never change screening results or clinician-first guidance.');
$('#themeToggle').onclick = () => { const next = document.body.dataset.theme === 'dark' ? 'light' : 'dark'; persistPreferences({ theme: next }); };
$('#settingsThemeButton').onclick = () => { const next = document.body.dataset.theme === 'dark' ? 'light' : 'dark'; persistPreferences({ theme: next }); };
$('#routineForm').onsubmit = saveRoutine; $('#cancelRoutineEdit').onclick = resetRoutineForm; $('#checkinForm').onsubmit = saveCheckin; $('#downloadHistoryButton').onclick = downloadHistory;
window.addEventListener('popstate', () => showPage(location.hash.replace('#', '') || 'dashboard', { syncHistory: false }));
window.addEventListener('hashchange', () => showPage(location.hash.replace('#', '') || 'dashboard', { syncHistory: false }));
window.addEventListener('beforeunload', () => { if (state.imageUrl) URL.revokeObjectURL(state.imageUrl); });

async function initialiseApp() {
  if (window.location.protocol === 'file:') {
    showAuthGate('login');
    setAuthMessage('Open DermaMatrix through the local app server at http://127.0.0.1:8000. Opening this file directly cannot connect to your local account or assessment service.');
    return;
  }
  installImagePreview();
  installProcessingOverlay();
  restoreProfile();
  restoreSettings();
  restoreTheme();
  applyConsumerCopy();
  await loadModelCapabilities();
  renderDiscoveryCatalog();
  selectArea(state.area);
  resetRoutineForm();
  $('#checkinDate').value = currentDate();
  $('#clearProfileButton').textContent = 'Sign out';
  $('#profileModal .profile-actions [data-close-profile]').textContent = 'Cancel';
  $('#resultTitle').textContent = 'Your health check';
  $('[data-result-tab="summary"]').textContent = 'Overview';
  $('[data-result-tab="evidence"]').textContent = 'Why this result?';
  $('[data-result-tab="care"]').textContent = 'Care plan';
  $('[data-result-tab="progress"]').textContent = 'Track progress';
  $('[data-result-tab="support"]').textContent = 'Find a doctor';
  $('#viewCareButton').textContent = 'View care guidance';
  const authenticated = await restoreAuthentication();
  if (authenticated) await hydrateProfile();
  await loadProgress();
  showPage(location.hash.replace('#', '') || 'dashboard', { syncHistory: false });
  if (!authenticated) showAuthGate('login');
}

initialiseApp();
