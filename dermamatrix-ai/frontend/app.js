const state = { area: 'Skin', imageUrl: null, file: null, assessmentId: null, profile: null };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function showToast(message) {
  const toast = $('#toast'); toast.textContent = message; toast.classList.add('show');
  clearTimeout(showToast.timeout); showToast.timeout = setTimeout(() => toast.classList.remove('show'), 3300);
}

function selectArea(area) {
  state.area = area;
  $$('.area-choice button').forEach(button => button.classList.toggle('selected', button.dataset.area === area));
  $('#assess').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setImage(file) {
  if (!file || !file.type.startsWith('image/')) return showToast('Please select an image file (JPG, PNG, or WEBP).');
  if (file.size > 10 * 1024 * 1024) return showToast('Please select an image smaller than 10 MB.');
  if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
  state.file = file; state.imageUrl = URL.createObjectURL(file);
  const zone = $('#dropZone'); zone.style.backgroundImage = `url("${state.imageUrl}")`; zone.classList.add('has-image');
  $('#analyzeButton').disabled = false; $('#stepCount').textContent = 'STEP 2 OF 3';
}

function openProfile() { $('#profileModal').classList.add('show'); $('#profileModal').setAttribute('aria-hidden', 'false'); }
function closeProfile() { $('#profileModal').classList.remove('show'); $('#profileModal').setAttribute('aria-hidden', 'true'); }
function closeModal() { $('#resultModal').classList.remove('show'); $('#resultModal').setAttribute('aria-hidden', 'true'); }

function renderProducts(items, eligible) {
  const grid = $('#productGrid');
  if (!eligible) {
    grid.innerHTML = '<article class="product-empty"><span>✚</span><h3>Clinical review comes first</h3><p>This assessment is not eligible for product discovery. Please arrange review by a registered medical practitioner before considering treatment.</p></article>';
    return;
  }
  grid.innerHTML = items.map(item => `<article class="product-card"><span class="product-type">${item.category}</span><h3>${item.name}</h3><p>${item.purpose}</p><p class="guardrail">${item.guardrail}</p><button class="text-button" data-toast="Product selection must be checked with a pharmacist or registered medical practitioner.">Ask a pharmacist →</button></article>`).join('');
  $$('#productGrid [data-toast]').forEach(button => button.addEventListener('click', () => showToast(button.dataset.toast)));
}

async function loadProducts(area, score) {
  try {
    const response = await fetch(`/api/products?area=${encodeURIComponent(area)}&risk_score=${score}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    renderProducts(result.items, result.eligible);
  } catch (_) { showToast('Personal-care recommendations are unavailable right now.'); }
}

async function analyze() {
  if (!state.imageUrl) return;
  const button = $('#analyzeButton'); button.disabled = true; button.innerHTML = 'Preparing secure screen <span>…</span>';
  const form = new FormData();
  form.append('image', state.file); form.append('area', state.area); form.append('duration', $('#duration').value); form.append('discomfort', $('#discomfort').value); form.append('change', $('#change').value); form.append('image_context', $('#imageContext').value); form.append('patient_id', state.profile?.patient_id || '');
  let result;
  try {
    const response = await fetch('/api/assessments', { method: 'POST', body: form }); result = await response.json();
    if (!response.ok) throw new Error(result.error || 'The local assessment service did not respond.');
  } catch (error) {
    showToast(error.message || 'Unable to connect to the local assessment service.'); button.disabled = false; button.innerHTML = 'Analyze image <span>→</span>'; return;
  }
  const score = result.risk.score; state.assessmentId = result.assessment_id;
  $('#resultImage').src = state.imageUrl; $('#resultRisk').textContent = result.risk.level;
  $('#resultRisk').className = `risk-label ${score < 40 ? 'low' : 'moderate'}`;
  $('#findingTitle').textContent = result.screening.title; $('#findingText').textContent = result.screening.summary;
  $('#qualityScore').textContent = `${result.quality.score}% · ${result.quality.label}`; $('#modelStatus').textContent = `${Math.round(result.model.confidence * 100)}% · ${result.model.version}`; $('#clinicalStatus').textContent = 'Awaiting RMP review';
  const researchBox = $('#researchResult');
  if (result.research_classifier?.available) {
    const top = result.research_classifier.top_predictions[0];
    $('#researchPrediction').textContent = `${top.label} · research confidence ${Math.round(top.probability * 100)}%. This output is only valid for dermatoscopic lesion images, never face photos.`;
    researchBox.hidden = false;
  } else { researchBox.hidden = true; }
  $('#resultModal').classList.add('show'); $('#resultModal').setAttribute('aria-hidden', 'false'); $('#stepCount').textContent = 'STEP 3 OF 3';
  $('#riskScore').textContent = score;
  $('#riskMessage').textContent = score < 40 ? 'Your current profile looks stable. Keep up your healthy routine.' : score < 65 ? 'A few factors need attention. Consider a clinician review if this persists.' : 'Your answers indicate a higher need for a professional assessment.';
  const today = new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  $('#timeline').insertAdjacentHTML('afterbegin', `<div class="timeline-item"><span class="timeline-dot today"></span><div><strong>${state.area} assessment added</strong><p>Prototype AI screen completed locally. Your image was not saved.</p></div><time>${today}</time></div>`);
  loadProducts(result.area, score); button.disabled = false; button.innerHTML = 'Analyze image <span>→</span>';
}

async function requestReview() {
  if (!state.assessmentId) return showToast('Complete an assessment before requesting clinical review.');
  try {
    const response = await fetch('/api/clinical-review-requests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ assessment_id: state.assessmentId, patient_id: state.profile?.patient_id || '' }) });
    const result = await response.json(); if (!response.ok) throw new Error(result.error);
    $('#clinicalStatus').textContent = 'RMP review requested'; showToast('Review request saved. An RMP must independently assess the concern.');
  } catch (error) { showToast(error.message || 'Could not create the review request.'); }
}

async function saveProfile(event) {
  event.preventDefault(); const form = new FormData(event.currentTarget); const payload = Object.fromEntries(form.entries());
  payload.health_data_consent = form.get('health_data_consent') === 'on';
  const submit = event.currentTarget.querySelector('[type="submit"]'); submit.disabled = true;
  try {
    const response = await fetch('/api/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const profile = await response.json(); if (!response.ok) throw new Error(profile.error);
    state.profile = profile; localStorage.setItem('dermamatrix_profile', JSON.stringify(profile));
    $('#profileName').textContent = profile.full_name; $('#profileMeta').textContent = profile.patient_id; closeProfile(); showToast('Your consent-based local profile has been saved.');
  } catch (error) { showToast(error.message || 'Unable to save the profile.'); }
  submit.disabled = false;
}

function restoreProfile() {
  try {
    const profile = JSON.parse(localStorage.getItem('dermamatrix_profile'));
    if (profile?.full_name) { state.profile = profile; $('#profileName').textContent = profile.full_name; $('#profileMeta').textContent = profile.patient_id; return; }
  } catch (_) { /* no saved profile */ }
  setTimeout(openProfile, 700);
}

$$('.assessment-card').forEach(card => card.addEventListener('click', () => selectArea(card.dataset.area)));
$$('.area-choice button').forEach(button => button.addEventListener('click', () => selectArea(button.dataset.area)));
$('#imageInput').addEventListener('change', event => setImage(event.target.files[0]));
const dropZone = $('#dropZone');
['dragenter', 'dragover'].forEach(event => dropZone.addEventListener(event, e => { e.preventDefault(); dropZone.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(event => dropZone.addEventListener(event, e => { e.preventDefault(); dropZone.classList.remove('dragging'); }));
dropZone.addEventListener('drop', event => setImage(event.dataTransfer.files[0]));
$('#analyzeButton').addEventListener('click', analyze); $('#requestReviewButton').addEventListener('click', requestReview);
$('#profileButton').addEventListener('click', openProfile); $('#profileForm').addEventListener('submit', saveProfile);
$$('[data-close-modal]').forEach(button => button.addEventListener('click', closeModal));
$$('[data-close-profile]').forEach(button => button.addEventListener('click', closeProfile));
$$('[data-toast]').forEach(button => button.addEventListener('click', () => showToast(button.dataset.toast)));
$('.menu-button').addEventListener('click', () => $('.sidebar').classList.toggle('open'));
document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeModal(); closeProfile(); } });
restoreProfile();
