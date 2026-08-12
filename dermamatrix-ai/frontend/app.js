const state = { area: 'Skin', imageUrl: null, file: null, assessmentId: null, profile: null, productFilter: 'all' };
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
    grid.innerHTML = '<article class="product-empty"><span>✚</span><h3>Keep your routine simple</h3><p>Browse the general care shelf above. Avoid adding new products to a painful, rapidly changing, or broken-skin concern without professional advice.</p></article>';
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
    $('#researchHeading').textContent = 'Image scope';
    $('#researchPrediction').textContent = researchClassifier?.reason || 'General photos receive visual-quality feedback and screening support only. They are not disease-classified.';
    research.hidden = false; map.hidden = true; $('#attentionLabel').textContent = 'Image preview'; return;
  }
  const top = researchClassifier.top_predictions[0];
  $('#researchHeading').textContent = 'Research lesion model';
  $('#researchPrediction').textContent = `${top.label} · ${Math.round(top.probability * 100)}% research confidence. Not a diagnosis; only for dermatoscopic lesion images.`;
  $('#attentionLabel').textContent = 'Grad-CAM research attention — not lesion segmentation';
  map.src = researchClassifier.attention_map.image; map.hidden = false; research.hidden = false;
}

async function analyze() {
  if (!state.imageUrl) return;
  if (!$('#imageConsent').checked) return toast('Confirm image consent before continuing.');
  if ($('#imageContext').value === 'dermoscopic_lesion' && !$('#dermoscopyConsent').checked) return toast('Confirm that the image is a dermatoscopic single-lesion photo.');
  const button = $('#analyzeButton'); button.disabled = true; button.innerHTML = 'Reviewing <span>…</span>';
  const form = new FormData();
  [['image', state.file], ['area', state.area], ['duration', $('#duration').value], ['discomfort', $('#discomfort').value], ['change', $('#change').value], ['image_context', $('#imageContext').value], ['patient_id', state.profile?.patient_id || ''], ['image_consent', String($('#imageConsent').checked)], ['urgent_concern', String($('#urgentConcern').checked)], ['dermoscopy_attestation', String($('#dermoscopyConsent').checked)]].forEach(([key, value]) => form.append(key, value));
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
    setResearchAttention(data.research_classifier); showCarePlan(data.care_plan);
    const note = $('#concernNote').value.trim();
    $('#progressText').textContent = note ? `Tracking note: “${note}” Your image is not saved; save this summary to compare future reported changes.` : 'Save this non-diagnostic snapshot to compare your reported changes over time. Uploaded images are not saved.';
    if (data.quality.issues?.length) toast(data.quality.issues[0]);
    if (data.urgent_notice) toast(data.urgent_notice);
    $('#resultModal').classList.add('show'); $('#resultModal').setAttribute('aria-hidden', 'false');
    $('#stepCount').textContent = 'STEP 3 OF 3'; loadProducts(data.area, score);
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
  $('#care').scrollIntoView({ behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth', block: 'start' });
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

function clearLocalProfile() {
  localStorage.removeItem('dermamatrix_profile'); state.profile = null;
  $('#profileName').textContent = 'Guest profile'; $('#profileMeta').textContent = 'Save health details';
  toast('Your local profile has been cleared from this browser.');
}

function updateImageContext() {
  const dermoscopy = $('#imageContext').value === 'dermoscopic_lesion';
  $('#dermoscopyAttestation').hidden = !dermoscopy;
  $('#dermoscopyConsent').required = dermoscopy;
  if (!dermoscopy) $('#dermoscopyConsent').checked = false;
}

$$('.area-choice button').forEach(button => { button.onclick = () => selectArea(button.dataset.area); });
$('#imageInput').onchange = event => setImage(event.target.files[0]);
$('#imageContext').onchange = updateImageContext;
const drop = $('#dropZone');
['dragenter', 'dragover'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.remove('dragging'); }));
drop.addEventListener('drop', event => setImage(event.dataTransfer.files[0]));
$('#analyzeButton').onclick = analyze; $('#saveProgressButton').onclick = saveProgress; $('#viewCareButton').onclick = viewCare;
$('#doctorSearchForm').onsubmit = searchDoctors; $('#profileButton').onclick = openProfile; $('#topProfileButton').onclick = openProfile; $('#profileForm').onsubmit = saveProfile;
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
restoreProfile();
restoreSettings();
renderDiscoveryCatalog();
updateImageContext();
