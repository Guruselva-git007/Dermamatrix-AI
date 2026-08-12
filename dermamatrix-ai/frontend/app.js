const state = { area: 'Skin', imageUrl: null, file: null, assessmentId: null, profile: null, productFilter: 'all', routines: [], checkins: [] };
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

function toast(message) {
  const element = $('#toast');
  element.textContent = message; element.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => element.classList.remove('show'), 3200);
}

function selectArea(area) {
  state.area = area;
  $$('.area-choice button').forEach(button => button.classList.toggle('selected', button.dataset.area === area));
}

function setImage(file) {
  if (!file || !file.type.startsWith('image/')) return toast('Choose a JPG, PNG, or WEBP image.');
  if (file.size > 10 * 1024 * 1024) return toast('Choose an image smaller than 10 MB.');
  if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
  state.file = file; state.imageUrl = URL.createObjectURL(file);
  const zone = $('#dropZone'); zone.style.backgroundImage = `url("${state.imageUrl}")`; zone.classList.add('has-image');
  $('#analyzeButton').disabled = false; $('#stepCount').textContent = 'STEP 2 OF 3';
}

function openProfile() { $('#profileModal').classList.add('show'); $('#profileModal').setAttribute('aria-hidden', 'false'); }
function closeProfile() { $('#profileModal').classList.remove('show'); $('#profileModal').setAttribute('aria-hidden', 'true'); }
function closeResult() { $('#resultModal').classList.remove('show'); $('#resultModal').setAttribute('aria-hidden', 'true'); }

function showPage(page) {
  const allowed = ['home', 'products', 'progress', 'settings'];
  const target = allowed.includes(page) ? page : 'home';
  $$('[data-page]').forEach(section => section.classList.toggle('page-active', section.dataset.page === target));
  $$('[data-page-nav]').forEach(link => link.classList.toggle('active', link.dataset.pageNav === target));
  if (target === 'progress') loadProgress();
  window.scrollTo({ top: 0, behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth' });
}

function showCarePlan(plan) {
  let box = $('#careRecommendation');
  if (!box) {
    box = document.createElement('div'); box.id = 'careRecommendation'; box.className = 'care-recommendation';
    $('#researchResult').insertAdjacentElement('afterend', box);
  }
  box.innerHTML = `<span>✚</span><p><strong>${plan.heading}</strong><br>${plan.next_step}<br><em>${plan.routine_guardrail}</em><br><em>${plan.diet_guidance}</em></p>`;
}

function setResearchAttention(researchClassifier) {
  const research = $('#researchResult');
  const map = $('#attentionMap');
  if (!researchClassifier?.available) {
    $('#researchHeading').textContent = 'Image scope';
    $('#researchPrediction').textContent = researchClassifier?.reason || 'General photos receive visual-quality feedback and screening support only. They are not disease-classified.';
    research.hidden = false; map.hidden = true; $('#attentionLabel').textContent = 'Image preview'; return;
  }
  const top = researchClassifier.top_predictions[0];
  const confidence = Math.round((researchClassifier.model_confidence ?? top.probability) * 100);
  const lowConfidence = researchClassifier.low_confidence ? ' Low confidence: the model cannot confidently classify this image.' : '';
  $('#researchHeading').textContent = 'Research lesion model';
  $('#researchPrediction').textContent = `${top.label} · AI model confidence ${confidence}%. ${researchClassifier.confidence_notice || 'This is not a diagnosis.'}${lowConfidence}`;
  $('#attentionLabel').textContent = 'Grad-CAM research attention — not lesion segmentation';
  map.src = researchClassifier.attention_map.image; map.hidden = false; research.hidden = false;
}

function setSegmentation(segmentation) {
  const overlay = $('#segmentationOverlay');
  if (segmentation?.available && segmentation.reliable && segmentation.overlay) {
    overlay.src = segmentation.overlay; overlay.hidden = false;
    $('#attentionLabel').textContent = `Research candidate region · ${segmentation.affected_area_percent}% of frame`;
    return;
  }
  overlay.hidden = true;
}

function renderAnalysisDashboard(data) {
  const segmentation = data.segmentation || {};
  const classifier = data.research_classifier || {};
  const predictions = classifier.available ? classifier.top_predictions.map(item => `${escapeHTML(item.label)} ${Math.round(item.probability * 100)}%`).join(' · ') : 'No disease classification run for this image type.';
  const confidence = classifier.available ? `AI model confidence: ${Math.round((classifier.model_confidence ?? classifier.top_predictions[0].probability) * 100)}%. ${escapeHTML(classifier.confidence_notice || 'Not a diagnosis.')}${classifier.low_confidence ? ' Low confidence: discuss the image with a clinician rather than relying on this output.' : ''}` : '';
  const region = segmentation.available ? segmentation.reliable ? `Candidate-region coverage: ${segmentation.affected_area_percent}% (research baseline)` : segmentation.message : segmentation.message || 'No candidate-region extraction run.';
  $('#analysisPipeline').innerHTML = `<p><strong>Quality:</strong> ${escapeHTML(data.quality.label)}${data.quality.issues?.length ? ` — ${escapeHTML(data.quality.issues.join(' '))}` : ''}</p><p><strong>Region:</strong> ${escapeHTML(region)}</p><p><strong>Classification:</strong> ${predictions}</p>${confidence ? `<p><strong>Confidence:</strong> ${confidence}</p>` : ''}<p><strong>Why the AI looked there:</strong> ${classifier.available ? 'Grad-CAM highlights image regions contributing to the research classifier.' : 'Explainability is available only when the scoped research classifier runs.'}</p>`;
  const recommendation = data.recommendations || {};
  const section = (title, values) => `<div><strong>${title}</strong><ul>${(values || []).map(value => `<li>${escapeHTML(value)}</li>`).join('')}</ul></div>`;
  const products = (recommendation.products || []).map(product => `<li><strong>${escapeHTML(product.name)}</strong> — ${escapeHTML(product.purpose)} <em>${escapeHTML(product.precautions)}</em>${product.url ? ` <a href="${escapeHTML(product.url)}" target="_blank" rel="noopener sponsored">View partner ↗</a>` : ''}</li>`).join('');
  $('#recommendationPanel').innerHTML = `${section('Morning', recommendation.routine?.morning)}${section('Evening', recommendation.routine?.evening)}${section('Diet & nutrients', recommendation.diet)}${section('Supplements', recommendation.supplements)}<div><strong>Care categories</strong><ul>${products}</ul></div><p class="recommendation-note">${escapeHTML(recommendation.research_note || '')} ${escapeHTML(recommendation.affiliate_disclosure || '')}</p>`;
}

async function analyze() {
  if (!state.imageUrl) return;
  if (!$('#imageConsent').checked) return toast('Confirm image consent before continuing.');
  if ($('#imageContext').value === 'dermoscopic_lesion' && !$('#dermoscopyConsent').checked) return toast('Confirm that the image is a dermatoscopic single-lesion photo.');
  const button = $('#analyzeButton'); button.disabled = true; button.innerHTML = 'Reviewing <span>…</span>';
  const form = new FormData();
  [['image', state.file], ['area', state.area], ['duration', $('#duration').value], ['discomfort', $('#discomfort').value], ['change', $('#change').value], ['image_context', $('#imageContext').value], ['patient_id', state.profile?.patient_id || ''], ['image_consent', String($('#imageConsent').checked)], ['urgent_concern', String($('#urgentConcern').checked)], ['dermoscopy_attestation', String($('#dermoscopyConsent').checked)], ['previous_treatment', $('#previousTreatment').value]].forEach(([key, value]) => form.append(key, value));
  $$('input[name="symptoms"]:checked').forEach(input => form.append('symptoms', input.value));
  try {
    const response = await fetch('/api/assessments', { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok) throw Error(data.error);
    state.assessmentId = data.assessment_id;
    const score = data.risk.score;
    $('#resultImage').src = state.imageUrl;
    $('#resultRisk').textContent = data.risk.level;
    $('#resultRisk').className = `risk-label ${score < 40 ? 'low' : 'moderate'}`;
    $('#findingTitle').textContent = data.screening.title; $('#findingText').textContent = data.screening.summary;
    $('#qualityScore').textContent = `${data.quality.score}% · ${data.quality.label}`;
    $('#modelStatus').textContent = `${Math.round(data.model.confidence * 100)}% · screening support`;
    $('#clinicalStatus').textContent = 'Ready to save locally';
    setSegmentation(data.segmentation); setResearchAttention(data.research_classifier); renderAnalysisDashboard(data); showCarePlan(data.care_plan);
    const note = $('#concernNote').value.trim();
    $('#progressText').textContent = note ? `Tracking note: “${note}” Your image is not saved; save this summary to compare future reported changes.` : 'Save this non-diagnostic snapshot to compare your reported changes over time. Uploaded images are not saved.';
    if (data.quality.issues?.length) toast(data.quality.issues[0]);
    if (data.urgent_notice) toast(data.urgent_notice);
    $('#resultModal').classList.add('show'); $('#resultModal').setAttribute('aria-hidden', 'false');
    $('#stepCount').textContent = 'STEP 3 OF 3';
  } catch (error) { toast(error.message || 'Unable to review this image.'); }
  button.disabled = false; button.innerHTML = 'Review image <span>→</span>';
}

function saveProgress() {
  if (!state.assessmentId) return toast('Complete a screen before saving progress.');
  const entries = JSON.parse(localStorage.getItem('dermamatrix_progress') || '[]');
  const entry = { id: state.assessmentId, date: new Date().toISOString(), area: state.area, priority: $('#resultRisk').textContent, note: $('#concernNote').value.trim(), imageStored: false };
  const unique = [entry, ...entries.filter(item => item.id !== entry.id)].slice(0, 12);
  localStorage.setItem('dermamatrix_progress', JSON.stringify(unique));
  $('#clinicalStatus').textContent = `${unique.length} local snapshot${unique.length === 1 ? '' : 's'} saved`;
  toast('Progress snapshot saved locally. Uploaded images are not kept.');
}

function viewCare() {
  closeResult();
  showPage('products');
}

function searchDoctors(event) {
  event.preventDefault();
  const location = $('#doctorLocation').value.trim();
  if (!location) return;
  const query = encodeURIComponent(`dermatologist near ${location}`);
  window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, '_blank', 'noopener,noreferrer');
}

async function saveProfile(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget); const payload = Object.fromEntries(form.entries());
  payload.health_data_consent = form.get('health_data_consent') === 'on';
  const button = event.currentTarget.querySelector('[type="submit"]'); button.disabled = true;
  try {
    const response = await fetch('/api/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json(); if (!response.ok) throw Error(data.error);
    state.profile = { ...data, past_history: payload.past_history, current_history: payload.current_history }; localStorage.setItem('dermamatrix_profile', JSON.stringify(state.profile));
    $('#profileName').textContent = data.full_name; $('#profileMeta').textContent = data.patient_id; closeProfile(); await loadProgress(); toast('Local profile saved.');
  } catch (error) { toast(error.message || 'Unable to save profile.'); }
  button.disabled = false;
}

function restoreProfile() {
  try {
    const profile = JSON.parse(localStorage.getItem('dermamatrix_profile'));
    if (profile?.full_name) { state.profile = profile; $('#profileName').textContent = profile.full_name; $('#profileMeta').textContent = profile.patient_id; }
  } catch { /* no local profile */ }
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
  $('#productCatalog').innerHTML = visible.length ? visible.map(item => `<article class="catalog-card" data-category="${item.category}"><span class="catalog-icon">${item.icon}</span><span class="catalog-type">${item.type}</span><h3>${item.name}</h3><p>${item.copy}</p><button class="text-button" data-discuss-product="${item.name}">Discuss benefit →</button></article>`).join('') : '<div class="catalog-empty">No matching items. Try “barrier”, “scalp”, or “vitamin”.</div>';
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
  document.querySelector('meta[name="theme-color"]').content = dark ? '#0b1426' : '#2474d8';
}

function restoreTheme() { applyTheme(localStorage.getItem('dermamatrix_theme') || 'light'); }

function clearLocalProfile() {
  localStorage.removeItem('dermamatrix_profile'); state.profile = null;
  $('#profileName').textContent = 'Guest profile'; $('#profileMeta').textContent = 'Save health details';
  state.routines = []; state.checkins = []; renderProgress();
  toast('Your local profile has been cleared from this browser.');
}

const escapeHTML = value => String(value || '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));

function currentDate() { return new Date().toISOString().slice(0, 10); }

function resetRoutineForm() {
  $('#routineForm').reset(); $('#editingRoutineId').value = ''; $('#routineStartDate').value = currentDate();
  $('#routineFormTitle').textContent = 'Add a routine'; $('#cancelRoutineEdit').hidden = true;
}

function renderProgress() {
  const hasProfile = Boolean(state.profile?.patient_id);
  const routines = state.routines || []; const checkins = state.checkins || [];
  const latest = checkins[0];
  $('#progressSummary').innerHTML = `<article><span>◔</span><strong>${routines.length}</strong><small>active routines</small></article><article><span>⌁</span><strong>${latest ? escapeHTML(latest.reported_trend) : '—'}</strong><small>latest self-reported trend</small></article><article><span>◌</span><strong>${latest ? `${latest.priority_score}/100` : '—'}</strong><small>reported-concern priority</small></article>`;
  $('#openProfileFromProgress').textContent = hasProfile ? 'Profile connected' : 'Set up profile';
  $('#routineList').innerHTML = !hasProfile ? '<p class="empty-state">Set up a profile to store routines and progress securely in this local app.</p>' : !routines.length ? '<p class="empty-state">No routines yet. Add a clinician-recorded condition and its routine.</p>' : routines.map(routine => `<article class="routine-item"><div><span>${escapeHTML(routine.condition_label)}</span><h4>${escapeHTML(routine.routine_name)}</h4><p>Started ${escapeHTML(routine.start_date)} · ${routine.checkin_count || 0} check-in${Number(routine.checkin_count) === 1 ? '' : 's'}</p>${routine.notes ? `<small>${escapeHTML(routine.notes)}</small>` : ''}</div><div class="routine-actions"><button class="text-button" data-edit-routine="${routine.routine_id}">Edit</button><button class="text-button danger-button" data-delete-routine="${routine.routine_id}">Delete</button></div></article>`).join('');
  $('#checkinRoutine').innerHTML = `<option value="">Choose a saved routine</option>${routines.map(routine => `<option value="${routine.routine_id}">${escapeHTML(routine.condition_label)} · ${escapeHTML(routine.routine_name)}</option>`).join('')}`;
  const medicalHistory = hasProfile && (state.profile.past_history || state.profile.current_history) ? `<div class="medical-history-summary"><strong>Profile medical history</strong>${state.profile.past_history ? `<p>Past: ${escapeHTML(state.profile.past_history)}</p>` : ''}${state.profile.current_history ? `<p>Current: ${escapeHTML(state.profile.current_history)}</p>` : ''}</div>` : '';
  const timeline = !hasProfile ? '<p class="empty-state">Your progress timeline is available after profile setup.</p>' : !checkins.length ? '<p class="empty-state">Save your first check-in to create a timeline.</p>' : checkins.map(item => `<article class="history-item"><div><strong>${escapeHTML(item.reported_trend)} · ${item.priority_score}/100</strong><p>${escapeHTML(item.condition_label)} · ${escapeHTML(item.routine_name)}</p>${item.note ? `<small>${escapeHTML(item.note)}</small>` : ''}</div><time>${escapeHTML(item.checkin_date)}</time></article>`).join('');
  $('#progressHistory').innerHTML = medicalHistory + timeline;
  $$('[data-edit-routine]').forEach(button => { button.onclick = () => editRoutine(button.dataset.editRoutine); });
  $$('[data-delete-routine]').forEach(button => { button.onclick = () => deleteRoutine(button.dataset.deleteRoutine); });
}

async function loadProgress() {
  if (!state.profile?.patient_id) { renderProgress(); return; }
  try {
    const patientId = encodeURIComponent(state.profile.patient_id);
    const [routineResponse, checkinResponse] = await Promise.all([fetch(`/api/routines?patient_id=${patientId}`), fetch(`/api/progress-checkins?patient_id=${patientId}`)]);
    const routineData = await routineResponse.json(); const checkinData = await checkinResponse.json();
    if (!routineResponse.ok || !checkinResponse.ok) throw Error(routineData.error || checkinData.error);
    state.routines = routineData.routines; state.checkins = checkinData.checkins; renderProgress();
  } catch (error) { toast(error.message || 'Progress data is unavailable right now.'); }
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
  const payload = { patient_id: state.profile.patient_id, condition_label: $('#conditionLabel').value, routine_name: $('#routineName').value, start_date: $('#routineStartDate').value, notes: $('#routineNotes').value };
  const editingId = $('#editingRoutineId').value;
  try {
    const response = await fetch(editingId ? `/api/routines/${editingId}` : '/api/routines', { method: editingId ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json(); if (!response.ok) throw Error(data.error);
    resetRoutineForm(); await loadProgress(); toast(editingId ? 'Routine updated.' : 'Routine added.');
  } catch (error) { toast(error.message || 'Could not save this routine.'); }
}

async function deleteRoutine(routineId) {
  if (!window.confirm('Delete this routine and its progress history?')) return;
  try {
    const response = await fetch(`/api/routines/${routineId}?patient_id=${encodeURIComponent(state.profile.patient_id)}`, { method: 'DELETE' });
    const data = await response.json(); if (!response.ok) throw Error(data.error);
    await loadProgress(); toast('Routine deleted.');
  } catch (error) { toast(error.message || 'Could not delete this routine.'); }
}

async function saveCheckin(event) {
  event.preventDefault();
  if (!state.profile?.patient_id) { openProfile(); return toast('Set up a profile before saving check-ins.'); }
  const file = $('#checkinImage').files[0];
  const payload = { patient_id: state.profile.patient_id, routine_id: $('#checkinRoutine').value, checkin_date: $('#checkinDate').value, reported_trend: $('#checkinTrend').value, discomfort: $('#checkinDiscomfort').value, change: $('#checkinChange').value, note: $('#checkinNote').value };
  try {
    const response = await fetch('/api/progress-checkins', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const data = await response.json(); if (!response.ok) throw Error(data.error);
    event.currentTarget.reset(); $('#checkinDate').value = currentDate(); await loadProgress();
    toast(file ? `${data.progress_label}. The comparison image was not stored.` : `${data.progress_label}. Check-in saved.`);
  } catch (error) { toast(error.message || 'Could not save this check-in.'); }
}

function updateImageContext() {
  const dermoscopy = $('#imageContext').value === 'dermoscopic_lesion';
  $('#dermoscopyAttestation').hidden = !dermoscopy;
  $('#dermoscopyConsent').required = dermoscopy;
  if (!dermoscopy) $('#dermoscopyConsent').checked = false;
}

$$('.area-choice button').forEach(button => { button.onclick = () => selectArea(button.dataset.area); });
$$('[data-page-nav]').forEach(link => { link.onclick = event => { event.preventDefault(); showPage(link.dataset.pageNav); }; });
$('#imageInput').onchange = event => setImage(event.target.files[0]);
$('#imageContext').onchange = updateImageContext;
const drop = $('#dropZone');
['dragenter', 'dragover'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.remove('dragging'); }));
drop.addEventListener('drop', event => setImage(event.dataTransfer.files[0]));
$('#analyzeButton').onclick = analyze; $('#saveProgressButton').onclick = saveProgress; $('#viewCareButton').onclick = viewCare;
$('#doctorSearchForm').onsubmit = searchDoctors; $('#profileButton').onclick = openProfile; $('#topProfileButton').onclick = openProfile; $('#openProfileFromProgress').onclick = openProfile; $('#profileForm').onsubmit = saveProfile;
$$('[data-close-modal]').forEach(button => { button.onclick = closeResult; });
$$('[data-close-profile]').forEach(button => { button.onclick = closeProfile; });
$('.menu-button').onclick = () => $('.sidebar').classList.toggle('open');
document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeResult(); closeProfile(); } });
$$('.product-tabs button').forEach(button => { button.onclick = () => { state.productFilter = button.dataset.filter; $$('.product-tabs button').forEach(tab => tab.classList.toggle('selected', tab === button)); renderDiscoveryCatalog(); }; });
$('#productSearch').oninput = renderDiscoveryCatalog;
$('#notificationsToggle').onchange = event => { localStorage.setItem('dermamatrix_notifications', String(event.target.checked)); toast(event.target.checked ? 'Local care reminders enabled.' : 'Local care reminders disabled.'); };
$('#motionToggle').onchange = event => { localStorage.setItem('dermamatrix_reduced_motion', String(event.target.checked)); document.body.classList.toggle('reduce-motion', event.target.checked); toast(event.target.checked ? 'Reduced motion enabled.' : 'Reduced motion disabled.'); };
$('#clearProfileButton').onclick = clearLocalProfile;
$('#affiliateInfoButton').onclick = () => toast('Partner links are labelled. They never change screening results or clinician-first guidance.');
$('#themeToggle').onclick = () => { const next = document.body.dataset.theme === 'dark' ? 'light' : 'dark'; localStorage.setItem('dermamatrix_theme', next); applyTheme(next); };
$('#routineForm').onsubmit = saveRoutine; $('#cancelRoutineEdit').onclick = resetRoutineForm; $('#checkinForm').onsubmit = saveCheckin;
restoreProfile();
restoreSettings();
restoreTheme();
renderDiscoveryCatalog();
updateImageContext();
resetRoutineForm();
$('#checkinDate').value = currentDate();
loadProgress();
showPage(location.hash.replace('#', '') || 'home');
