const state = { area: 'Skin', imageUrl: null, file: null, assessmentId: null, profile: null };
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

function renderProducts(items, eligible, disclosure) {
  const grid = $('#productGrid');
  if (!eligible) {
    grid.innerHTML = '<article class="product-empty"><span>✚</span><h3>Clinical review first</h3><p>This screen is not eligible for product guidance. Please consult an RMP.</p></article>';
    return;
  }
  const cards = items.map(item => {
    const partner = item.affiliate_url ? `<a class="partner-link" href="${item.affiliate_url}" target="_blank" rel="sponsored noopener noreferrer">View partner product ↗</a>` : '<button class="text-button" data-product>Discuss before use →</button>';
    return `<article class="product-card"><span class="product-type">${item.category}</span><span class="consult-gate">CONSULT RMP FIRST</span><h3>${item.name}</h3><p>${item.purpose}</p><p class="guardrail">${item.guardrail}</p>${partner}</article>`;
  }).join('');
  grid.innerHTML = `<p class="affiliate-disclosure">${disclosure}</p>${cards}`;
  $$('[data-product]').forEach(button => { button.onclick = () => toast('Consult an RMP or pharmacist before starting any product or routine.'); });
}

async function loadProducts(area, score) {
  try {
    const response = await fetch(`/api/products?area=${encodeURIComponent(area)}&risk_score=${score}`);
    const data = await response.json();
    if (!response.ok) throw Error();
    renderProducts(data.items, data.eligible, data.affiliate_disclosure);
  } catch { toast('Product guidance is unavailable right now.'); }
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
    research.hidden = true; map.hidden = true; $('#attentionLabel').textContent = 'Image preview'; return;
  }
  const top = researchClassifier.top_predictions[0];
  $('#researchPrediction').textContent = `${top.label} · ${Math.round(top.probability * 100)}% research confidence. Not a diagnosis; only for dermatoscopic lesion images.`;
  $('#attentionLabel').textContent = 'Grad-CAM research attention — not lesion segmentation';
  map.src = researchClassifier.attention_map.image; map.hidden = false; research.hidden = false;
}

async function analyze() {
  if (!state.imageUrl) return;
  const button = $('#analyzeButton'); button.disabled = true; button.innerHTML = 'Reviewing <span>…</span>';
  const form = new FormData();
  [['image', state.file], ['area', state.area], ['duration', $('#duration').value], ['discomfort', $('#discomfort').value], ['change', $('#change').value], ['image_context', $('#imageContext').value], ['patient_id', state.profile?.patient_id || '']].forEach(([key, value]) => form.append(key, value));
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
    $('#clinicalStatus').textContent = 'Awaiting RMP review';
    setResearchAttention(data.research_classifier); showCarePlan(data.care_plan);
    $('#resultModal').classList.add('show'); $('#resultModal').setAttribute('aria-hidden', 'false');
    $('#stepCount').textContent = 'STEP 3 OF 3'; loadProducts(data.area, score);
  } catch (error) { toast(error.message || 'Unable to review this image.'); }
  button.disabled = false; button.innerHTML = 'Review image <span>→</span>';
}

async function requestReview() {
  if (!state.assessmentId) return toast('Complete a screen before requesting review.');
  try {
    const response = await fetch('/api/clinical-review-requests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ assessment_id: state.assessmentId, patient_id: state.profile?.patient_id || '' }) });
    const data = await response.json(); if (!response.ok) throw Error(data.error);
    $('#clinicalStatus').textContent = 'RMP review requested'; toast('Review request saved. An RMP must independently assess the concern.');
  } catch (error) { toast(error.message || 'Could not request review.'); }
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
    state.profile = data; localStorage.setItem('dermamatrix_profile', JSON.stringify(data));
    $('#profileName').textContent = data.full_name; $('#profileMeta').textContent = data.patient_id; closeProfile(); toast('Local profile saved.');
  } catch (error) { toast(error.message || 'Unable to save profile.'); }
  button.disabled = false;
}

function restoreProfile() {
  try {
    const profile = JSON.parse(localStorage.getItem('dermamatrix_profile'));
    if (profile?.full_name) { state.profile = profile; $('#profileName').textContent = profile.full_name; $('#profileMeta').textContent = profile.patient_id; }
  } catch { /* no local profile */ }
}

$$('.area-choice button').forEach(button => { button.onclick = () => selectArea(button.dataset.area); });
$('#imageInput').onchange = event => setImage(event.target.files[0]);
const drop = $('#dropZone');
['dragenter', 'dragover'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.remove('dragging'); }));
drop.addEventListener('drop', event => setImage(event.dataTransfer.files[0]));
$('#analyzeButton').onclick = analyze; $('#requestReviewButton').onclick = requestReview;
$('#doctorSearchForm').onsubmit = searchDoctors; $('#profileButton').onclick = openProfile; $('#topProfileButton').onclick = openProfile; $('#profileForm').onsubmit = saveProfile;
$$('[data-close-modal]').forEach(button => { button.onclick = closeResult; });
$$('[data-close-profile]').forEach(button => { button.onclick = closeProfile; });
$('.menu-button').onclick = () => $('.sidebar').classList.toggle('open');
document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeResult(); closeProfile(); } });
restoreProfile();
