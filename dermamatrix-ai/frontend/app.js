const state = { area: 'Skin', imageUrl: null, file: null, assessmentId: null, profile: null, productFilter: 'all', routines: [], checkins: [], analyses: [], progressLoadedFor: null, progressLoadPromise: null };
let processingTimers = [];
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

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
  $$('.area-choice button').forEach(button => button.classList.toggle('selected', button.dataset.area === area));
  const sweat = area === 'Sweat';
  const labels = {
    Skin: { title: 'Start with a skin image', status: 'Skin research model: dermatoscopic single-lesion images only.', upload: 'Upload a clear dermatoscopic image', copy: 'The research model accepts attested, in-focus dermatoscopic lesion images only.' },
    Hair: { title: 'Start with a scalp or hair image', status: 'Hair/scalp model adapter: no trained weights are configured in this deployment.', upload: 'Upload a clear scalp or hair image', copy: 'Image-quality feedback and shared screening support are available; no hair disorder label is generated.' },
    Nails: { title: 'Start with a nail image', status: 'Nail model adapter: no trained weights are configured in this deployment.', upload: 'Upload a clear nail image', copy: 'Image-quality feedback and shared screening support are available; no nail disorder label is generated.' },
    Sweat: { title: 'Assess a sweat pattern', status: 'Sweat tabular adapter: transparent questionnaire rules are active; no validated XGBoost model is configured.', upload: '', copy: '' },
  }[area];
  $('#screenTitle').textContent = labels.title;
  $('#screenTitle').nextElementSibling.textContent = sweat ? 'Complete the questionnaire, then review a transparent summary.' : 'Choose one area, then upload a clear image.';
  $('#home h1').textContent = sweat ? 'Assess a sweat pattern.' : 'Analyze an image.';
  $('#home p:last-child').textContent = sweat
    ? 'Use symptoms, context, and daily impact for a transparent questionnaire summary and general guidance.'
    : 'Upload a clear image for transparent quality feedback, scoped model outputs when eligible, and structured care guidance.';
  $('#moduleStatus').textContent = labels.status;
  $('#imageWorkflow').hidden = sweat;
  $('#sweatWorkflow').hidden = !sweat;
  $('#uploadStepTitle').textContent = labels.upload;
  $('#uploadStepCopy').textContent = labels.copy;
  $('#imageContext').closest('label').hidden = area !== 'Skin';
  if (area !== 'Skin') $('#imageContext').value = 'general_photo';
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
}

function setImage(file) {
  if (state.area === 'Sweat') return toast('Sweat patterns use the questionnaire instead of an image.');
  if (!file || !file.type.startsWith('image/')) return toast('Choose a JPG, PNG, or WEBP image.');
  if (file.size > 10 * 1024 * 1024) return toast('Choose an image smaller than 10 MB.');
  if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
  state.file = file; state.imageUrl = URL.createObjectURL(file);
  const zone = $('#dropZone'); zone.style.backgroundImage = `url("${state.imageUrl}")`; zone.classList.add('has-image');
  $('#uploadPreviewImage').src = state.imageUrl;
  $('#uploadPreviewName').textContent = file.name;
  $('#uploadPreview').hidden = false;
  $('#analyzeButton').disabled = false; $('#stepCount').textContent = 'STEP 2 OF 3';
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
}

function openProfile() { $('#profileModal').classList.add('show'); $('#profileModal').setAttribute('aria-hidden', 'false'); }
function closeProfile() { $('#profileModal').classList.remove('show'); $('#profileModal').setAttribute('aria-hidden', 'true'); }
function closeResult() { $('#resultModal').classList.remove('show'); $('#resultModal').setAttribute('aria-hidden', 'true'); }

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
  overlay.innerHTML = '<div class="processing-card" role="status" aria-live="polite"><span class="processing-orbit" aria-hidden="true"></span><p class="eyebrow">ANALYSIS IN PROGRESS</p><h2 id="processingTitle">Preparing your screening summary</h2><p id="processingCopy">Each completed stage is shown clearly. This app will not represent an unavailable model as a result.</p><ol id="processingSteps" class="processing-steps"></ol></div>';
  document.body.append(overlay);
}

function processingStages(area) {
  if (area === 'Skin') return ['Checking image quality', 'Preparing the image', 'Checking the eligible research-model path', 'Organising the screening summary'];
  if (area === 'Hair') return ['Checking image quality', 'Preparing the image', 'Checking the hair/scalp model adapter', 'Organising the screening summary'];
  if (area === 'Nails') return ['Checking image quality', 'Preparing the image', 'Checking the nail model adapter', 'Organising the screening summary'];
  return ['Validating questionnaire responses', 'Normalising reported inputs', 'Calculating transparent input contributions', 'Organising the screening summary'];
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
  processingTimers.forEach(window.clearTimeout); processingTimers = stages.slice(1).map((_, index) => window.setTimeout(() => {
    const rows = $$('#processingSteps li');
    rows.forEach((row, rowIndex) => { row.classList.toggle('done', rowIndex < index + 1); row.classList.toggle('active', rowIndex === index + 1); });
    const current = rows[index + 1]?.querySelector('span'); if (current) current.textContent = '…';
    const previous = rows[index]?.querySelector('span'); if (previous) previous.textContent = '✓';
  }, 170 * (index + 1)));
}

async function finishProcessing(startedAt) {
  const remaining = 620 - (performance.now() - startedAt);
  if (remaining > 0) await new Promise(resolve => window.setTimeout(resolve, remaining));
  processingTimers.forEach(window.clearTimeout); processingTimers = [];
  const modal = $('#processingModal');
  if (modal) { modal.classList.remove('show'); modal.setAttribute('aria-hidden', 'true'); }
}

function showPage(page, { syncHistory = true } = {}) {
  const allowed = ['dashboard', 'home', 'products', 'progress', 'support', 'settings'];
  const target = allowed.includes(page) ? page : 'dashboard';
  $$('[data-page]').forEach(section => section.classList.toggle('page-active', section.dataset.page === target));
  $$('[data-page-nav]').forEach(link => link.classList.toggle('active', link.dataset.pageNav === target));
  const titles = { dashboard: 'Dashboard', home: 'Analyze image', progress: 'My reports', products: 'Care guidance', support: 'Doctor directory', settings: 'Settings' };
  $('#workspaceTitle').textContent = titles[target];
  if (target === 'progress' || target === 'dashboard') loadProgress();
  if (syncHistory && window.location.hash !== `#${target}`) history.pushState({ page: target }, '', `#${target}`);
  window.scrollTo({ top: 0, behavior: document.body.classList.contains('reduce-motion') ? 'auto' : 'smooth' });
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
  if (Array.isArray(classifier.top_predictions)) return classifier.top_predictions;
  if (classifier.top_prediction) {
    const prediction = classifier.top_prediction;
    return [{ label: prediction.label || prediction.condition || 'Research label', probability: Number(prediction.probability ?? prediction.confidence ?? classifier.model_confidence ?? 0) }];
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
  const confidence = Math.round((researchClassifier.model_confidence ?? top.probability) * 100);
  const lowConfidence = researchClassifier.low_confidence ? ' Low confidence: the model cannot confidently classify this image.' : '';
  $('#researchHeading').textContent = 'Research lesion model';
  $('#researchPrediction').textContent = `${top.label} · AI model confidence ${confidence}%. ${researchClassifier.confidence_notice || 'This is not a diagnosis.'}${lowConfidence}`;
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

function renderAnalysisDashboard(data) {
  const segmentation = data.segmentation || {};
  const candidateRegion = data.candidate_region || {};
  const classifier = data.research_classifier || data.classification || {};
  const predictionsList = classifierPredictions(classifier);
  const predictions = classifier.available && predictionsList.length ? predictionsList.map(item => `${escapeHTML(item.label)} ${Math.round(item.probability * 100)}%`).join(' · ') : 'No disease classification run for this image type.';
  const confidence = classifier.available && predictionsList.length ? `AI model confidence: ${Math.round((classifier.model_confidence ?? predictionsList[0].probability) * 100)}%. ${escapeHTML(classifier.confidence_notice || 'Not a diagnosis.')}${classifier.low_confidence ? ' Low confidence: discuss the image with a clinician rather than relying on this output.' : ''}` : '';
  const region = segmentation.available ? `Model segmentation: ${segmentation.affected_area_percent}% of frame.` : candidateRegion.available && candidateRegion.reliable ? `Visual candidate region: ${candidateRegion.affected_area_percent}% of frame. This is not trained model segmentation.` : segmentation.message || candidateRegion.message || 'No visual-region extraction run.';
  const explainability = classifier.available ? (classifier.explainability?.explanation_text || 'Grad-CAM highlights image regions contributing to the research classifier.') : 'Explainability is available only when the scoped research classifier runs.';
  const questionnaireExplanation = (data.explainability?.features || []).map(item => `<li>${escapeHTML(item.feature)}: ${escapeHTML(item.value)} (${escapeHTML(item.points)} priority points)</li>`).join('');
  const xaiBlock = questionnaireExplanation
    ? `<p><strong>Questionnaire explanation:</strong> ${escapeHTML(data.explainability.notice || '')}</p><ul>${questionnaireExplanation}</ul>`
    : `<p><strong>Why the AI looked there:</strong> ${escapeHTML(explainability)}</p>`;
  const pirs = data.pirs?.score === undefined ? '' : `<p><strong>Shared PIRS:</strong> ${escapeHTML(data.pirs.score)}/100 — ${escapeHTML(data.pirs.label)}</p>`;
  $('#analysisPipeline').innerHTML = `<p><strong>Quality:</strong> ${escapeHTML(data.quality.label)}${data.quality.issues?.length ? ` — ${escapeHTML(data.quality.issues.join(' '))}` : ''}</p><p><strong>Region:</strong> ${escapeHTML(region)}</p><p><strong>Classification:</strong> ${predictions}</p>${confidence ? `<p><strong>Confidence:</strong> ${confidence}</p>` : ''}${pirs}${xaiBlock}`;
  const recommendation = data.recommendations || {};
  const section = (title, values) => `<div><strong>${title}</strong><ul>${(values || []).map(value => `<li>${escapeHTML(value)}</li>`).join('')}</ul></div>`;
  const products = (recommendation.products || []).map(product => `<li><strong>${escapeHTML(product.name)}</strong> — ${escapeHTML(product.purpose)} <em>${escapeHTML(product.precautions)}</em>${product.url ? ` <a href="${escapeHTML(product.url)}" target="_blank" rel="noopener sponsored">View partner ↗</a>` : ''}</li>`).join('');
  $('#recommendationPanel').innerHTML = `${section('Morning', recommendation.routine?.morning)}${section('Evening', recommendation.routine?.evening)}${section('Diet & nutrients', recommendation.diet)}${section('Supplements', recommendation.supplements)}<div><strong>Care categories</strong><ul>${products}</ul></div><p class="recommendation-note">${escapeHTML(recommendation.research_note || '')} ${escapeHTML(recommendation.affiliate_disclosure || '')}</p>`;
}

async function analyze() {
  const sweat = state.area === 'Sweat';
  if (!sweat && !state.imageUrl) return;
  if (!$('#imageConsent').checked) return toast('Confirm image consent before continuing.');
  if (!sweat && $('#imageContext').value === 'dermoscopic_lesion' && !$('#dermoscopyConsent').checked) return toast('Confirm that the image is a dermatoscopic single-lesion photo.');
  const button = $('#analyzeButton'); button.disabled = true; button.innerHTML = 'Reviewing <span>…</span>';
  const processingStarted = performance.now(); openProcessing(state.area);
  try {
    let data;
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
    await finishProcessing(processingStarted);
    state.assessmentId = data.assessment_id;
    const score = data.risk.score;
    const questionnaire = data.input_type === 'questionnaire';
    $('.segmentation-stage').classList.toggle('sweat-summary', questionnaire);
    $('#resultImage').hidden = questionnaire;
    if (questionnaire) $('#resultImage').removeAttribute('src');
    else $('#resultImage').src = state.imageUrl;
    $('#resultRisk').textContent = data.risk.level;
    $('#resultRisk').className = `risk-label ${score < 40 ? 'low' : 'moderate'}`;
    $('#findingTitle').textContent = data.screening.title; $('#findingText').textContent = data.screening.summary;
    $('#qualityScore').textContent = Number.isFinite(data.quality?.score) ? `${data.quality.score}% · ${data.quality.label}` : data.quality?.label || 'Not applicable';
    const confidence = data.model?.confidence;
    $('#modelStatus').textContent = Number.isFinite(confidence) ? `${Math.round(confidence * 100)}% · screening support` : data.model?.status === 'rule_based_prototype' ? 'Questionnaire contribution summary' : 'Model adapter unavailable';
    $('#clinicalStatus').textContent = 'Ready to save locally';
    setSegmentation(data.candidate_region, data.segmentation); setResearchAttention(data.research_classifier); renderAnalysisDashboard(data); showCarePlan(data.care_plan);
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
  } catch (error) { await finishProcessing(processingStarted); toast(error.message || 'Unable to review this image.'); }
  button.disabled = false; button.innerHTML = sweat ? 'Review questionnaire <span>→</span>' : 'Review image <span>→</span>';
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
  openDirectorySearch($('#doctorLocation').value);
}

function openDirectorySearch(locationValue) {
  const location = String(locationValue || '').trim();
  if (!location) return;
  const query = encodeURIComponent(`dermatologist near ${location}`);
  window.open(`https://www.google.com/maps/search/?api=1&query=${query}`, '_blank', 'noopener,noreferrer');
}

function searchDirectory(event) {
  event.preventDefault();
  openDirectorySearch($('#directoryLocation').value);
}

async function saveProfile(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget); const payload = Object.fromEntries(form.entries());
  payload.health_data_consent = form.get('health_data_consent') === 'on';
  const button = event.currentTarget.querySelector('[type="submit"]'); button.disabled = true;
  try {
    const data = await requestJSON('/api/profiles', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    state.profile = { ...data, past_history: payload.past_history, current_history: payload.current_history };
    persistBrowserProfile();
    $('#profileName').textContent = data.full_name; $('#profileMeta').textContent = data.patient_id; updateDashboardIdentity(); closeProfile(); await loadProgress({ force: true }); toast('Profile saved in the local project database.');
  } catch (error) { toast(error.message || 'Unable to save profile.'); }
  button.disabled = false;
}

function persistBrowserProfile() {
  if (!state.profile?.patient_id) return;
  localStorage.setItem('dermamatrix_profile', JSON.stringify({ patient_id: state.profile.patient_id, full_name: state.profile.full_name }));
}

function restoreProfile() {
  try {
    const profile = JSON.parse(localStorage.getItem('dermamatrix_profile'));
    if (profile?.full_name && profile?.patient_id) {
      state.profile = { patient_id: profile.patient_id, full_name: profile.full_name };
      persistBrowserProfile();
      $('#profileName').textContent = profile.full_name; $('#profileMeta').textContent = profile.patient_id;
    }
  } catch { /* no local profile */ }
  updateDashboardIdentity();
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
  $('#productCatalog').innerHTML = visible.length ? visible.map(item => `<article class="catalog-card" data-category="${item.category}"><span class="catalog-icon">${item.icon}</span><span class="catalog-type">${item.type}</span><h3>${item.name}</h3><p>${item.copy}</p><button class="text-button" data-discuss-product="${item.name}">View discussion points →</button></article>`).join('') : '<div class="catalog-empty">No matching topics. Try “barrier”, “scalp”, or “vitamin”.</div>';
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

function clearLocalProfile() {
  localStorage.removeItem('dermamatrix_profile'); state.profile = null;
  $('#profileName').textContent = 'Guest profile'; $('#profileMeta').textContent = 'Save health details';
  state.routines = []; state.checkins = []; state.analyses = []; state.progressLoadedFor = null; updateDashboardIdentity(); renderProgress();
  toast('Your local profile has been cleared from this browser.');
}

const escapeHTML = value => String(value || '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));

function currentDate() { return new Date().toISOString().slice(0, 10); }

function updateDashboardIdentity() {
  const name = state.profile?.full_name?.trim().split(/\s+/)[0] || 'there';
  $('#dashboardUser').textContent = name;
}

function renderDashboard() {
  const analyses = state.analyses || [];
  $('#dashboardActivity').innerHTML = !analyses.length
    ? '<p class="empty-state">No saved analyses yet. Start with a clear image when you are ready.</p>'
    : analyses.slice(0, 4).map(item => {
      const classification = item.summary?.classification?.top_prediction;
      const title = classification ? classification.condition : 'Visual screening snapshot';
      const meta = classification ? `${Math.round(classification.confidence * 100)}% AI model confidence` : 'No scoped classifier output';
      return `<article class="dashboard-record"><span>◌</span><div><strong>${escapeHTML(title)}</strong><small>${escapeHTML(item.area)} · ${escapeHTML(meta)}</small></div><time>${escapeHTML(String(item.created_at).slice(0, 10))}</time></article>`;
    }).join('');
}

function resetRoutineForm() {
  $('#routineForm').reset(); $('#editingRoutineId').value = ''; $('#routineStartDate').value = currentDate();
  $('#routineFormTitle').textContent = 'Add a routine'; $('#cancelRoutineEdit').hidden = true;
}

function reportClassification(summary) {
  const classifier = summary?.classification || {};
  const prediction = classifierPredictions(classifier)[0];
  return prediction ? `${prediction.label} · ${Math.round(prediction.probability * 100)}% research confidence` : 'Screening summary only';
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
    return `<div class="report-row"><time>${escapeHTML(String(item.created_at).slice(0, 10))}</time><span>${escapeHTML(item.area)}</span><strong>${escapeHTML(reportClassification(summary))}</strong><span>${escapeHTML(priority)}</span><span>${escapeHTML(xai)}</span><div><button class="text-button" data-view-report="${escapeHTML(item.assessment_id)}">View</button><button class="text-button" data-download-report="${escapeHTML(item.assessment_id)}">Export</button></div></div>`;
  }).join('') : '<p class="empty-state">Saved analysis metadata will appear here after an analysis. Image pixels are never retained in this prototype.</p>';
  register.innerHTML = `<div class="report-register-heading"><div><p class="eyebrow">SAVED REPORTS</p><h3>Analysis history</h3><p>Open a saved report or export a concise discussion brief. Images and Grad-CAM overlays are not retained.</p></div><span>${analyses.length} saved</span></div><div class="report-table" role="table"><div class="report-row report-head" role="row"><span>Date</span><span>Area</span><span>Result scope</span><span>Priority</span><span>Evidence</span><span>Action</span></div>${rows}</div>`;
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
  $('#resultRisk').className = `risk-label ${(data.risk?.score || 0) < 40 ? 'low' : 'moderate'}`;
  $('#findingTitle').textContent = data.screening?.title || 'Saved screening summary';
  $('#findingText').textContent = data.screening?.summary || 'This report contains saved screening metadata only.';
  $('#qualityScore').textContent = data.quality?.score === null || data.quality?.score === undefined ? data.quality?.label || 'Not applicable' : `${data.quality.score}% · ${data.quality.label}`;
  $('#modelStatus').textContent = data.classification?.available ? 'Research model record retained' : questionnaire ? 'Questionnaire contribution summary' : 'No scoped classifier output';
  $('#clinicalStatus').textContent = 'Saved metadata · no image retained';
  setSegmentation(data.candidate_region, data.segmentation); setResearchAttention(data.research_classifier); renderAnalysisDashboard(data); showCarePlan(data.care_plan || {});
  $('#progressText').textContent = `Saved ${String(item.created_at).slice(0, 10)}. This report can support a clinician discussion; it does not confirm a diagnosis or treatment response.`;
  $('.result-footnote').textContent = 'This is a saved metadata report. The original image, visual candidate overlay, and Grad-CAM image were intentionally not retained.';
  showResultTab('summary'); $('#resultModal').classList.add('show'); $('#resultModal').setAttribute('aria-hidden', 'false');
}

function downloadSavedReport(assessmentId) {
  const item = state.analyses.find(analysis => analysis.assessment_id === assessmentId);
  if (!item) return toast('This saved report is no longer available.');
  const summary = item.summary || {};
  const lines = [
    'DERMAMATRIX AI — SCREENING DISCUSSION BRIEF',
    `Saved: ${String(item.created_at).slice(0, 19)}`,
    `Area: ${item.area}`,
    `Screening summary: ${summary.screening?.title || 'Not available'}`,
    `Priority: ${summary.risk?.score ?? '—'}/100 — ${summary.risk?.label || 'Not a disease risk'}`,
    `Classifier scope: ${reportClassification(summary)}`,
    `Segmentation: ${summary.segmentation?.status || 'Not run'}`,
    `Explainability: ${summary.classification?.available ? 'Grad-CAM was produced during the original research inference; its image was not retained.' : summary.input_type === 'questionnaire' ? 'Questionnaire input-contribution summary.' : 'No scoped classifier explanation available.'}`,
    '',
    'Important: This educational prototype provides screening support only. It is not a diagnosis, prescription, or substitute for a registered medical practitioner. Discuss new routines, products, supplements, or treatment with a clinician or pharmacist.',
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob); const link = document.createElement('a');
  link.href = url; link.download = `dermamatrix-discussion-brief-${String(item.created_at).slice(0, 10)}.txt`; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
  toast('Discussion brief exported.');
}

function renderProgress() {
  const hasProfile = Boolean(state.profile?.patient_id);
  const routines = state.routines || []; const checkins = state.checkins || []; const analyses = state.analyses || [];
  const latest = checkins[0];
  $('#progressSummary').innerHTML = `<article><span>◔</span><strong>${routines.length}</strong><small>active routines</small></article><article><span>⌁</span><strong>${latest ? escapeHTML(latest.reported_trend) : '—'}</strong><small>latest self-reported trend</small></article><article><span>◌</span><strong>${latest ? `${latest.priority_score}/100` : '—'}</strong><small>reported-concern priority</small></article>`;
  $('#openProfileFromProgress').textContent = hasProfile ? 'Profile connected' : 'Set up profile';
  $('#routineList').innerHTML = !hasProfile ? '<p class="empty-state">Set up a profile to store routines and progress securely in this local app.</p>' : !routines.length ? '<p class="empty-state">No routines yet. Add a clinician-recorded condition and its routine.</p>' : routines.map(routine => `<article class="routine-item"><div><span>${escapeHTML(routine.condition_label)}</span><h4>${escapeHTML(routine.routine_name)}</h4><p>Started ${escapeHTML(routine.start_date)} · ${routine.checkin_count || 0} check-in${Number(routine.checkin_count) === 1 ? '' : 's'}</p>${routine.notes ? `<small>${escapeHTML(routine.notes)}</small>` : ''}</div><div class="routine-actions"><button class="text-button" data-edit-routine="${routine.routine_id}">Edit</button><button class="text-button danger-button" data-delete-routine="${routine.routine_id}">Delete</button></div></article>`).join('');
  $('#checkinRoutine').innerHTML = `<option value="">Choose a saved routine</option>${routines.map(routine => `<option value="${routine.routine_id}">${escapeHTML(routine.condition_label)} · ${escapeHTML(routine.routine_name)}</option>`).join('')}`;
  const medicalHistory = hasProfile && (state.profile.past_history || state.profile.current_history) ? `<div class="medical-history-summary"><strong>Profile medical history</strong>${state.profile.past_history ? `<p>Past: ${escapeHTML(state.profile.past_history)}</p>` : ''}${state.profile.current_history ? `<p>Current: ${escapeHTML(state.profile.current_history)}</p>` : ''}</div>` : '';
  const timeline = !hasProfile ? '<p class="empty-state">Your progress timeline is available after profile setup.</p>' : !checkins.length ? '<p class="empty-state">Save your first check-in to create a timeline.</p>' : checkins.map(item => `<article class="history-item"><div><strong>${escapeHTML(item.reported_trend)} · ${item.priority_score}/100</strong><p>${escapeHTML(item.condition_label)} · ${escapeHTML(item.routine_name)}</p>${item.note ? `<small>${escapeHTML(item.note)}</small>` : ''}</div><time>${escapeHTML(item.checkin_date)}</time></article>`).join('');
  const analysisHistory = !hasProfile ? '' : !analyses.length ? '<p class="empty-state">Saved image-analysis metadata will appear here after an analysis.</p>' : `<div class="analysis-history-group"><strong>Saved analysis metadata</strong>${analyses.map(item => { const classification = item.summary?.classification?.top_prediction; const label = classification ? `${classification.condition} · ${Math.round(classification.confidence * 100)}% AI model confidence` : 'No scoped classifier output'; return `<article class="history-item"><div><strong>${escapeHTML(label)}</strong><p>${escapeHTML(item.area)} · ${escapeHTML(item.summary?.segmentation?.status || 'segmentation not run')}</p><small>${escapeHTML(item.summary?.image_stored ? 'Image stored with consent' : 'Image pixels were not stored')}</small></div><time>${escapeHTML(String(item.created_at).slice(0, 10))}</time></article>`; }).join('')}</div>`;
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
  const payload = { patient_id: state.profile.patient_id, condition_label: $('#conditionLabel').value, routine_name: $('#routineName').value, start_date: $('#routineStartDate').value, notes: $('#routineNotes').value };
  const editingId = $('#editingRoutineId').value;
  try {
    await requestJSON(editingId ? `/api/routines/${editingId}` : '/api/routines', { method: editingId ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    resetRoutineForm(); await loadProgress({ force: true }); toast(editingId ? 'Routine updated.' : 'Routine added.');
  } catch (error) { toast(error.message || 'Could not save this routine.'); }
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
  const file = $('#checkinImage').files[0];
  const payload = { patient_id: state.profile.patient_id, routine_id: $('#checkinRoutine').value, checkin_date: $('#checkinDate').value, reported_trend: $('#checkinTrend').value, discomfort: $('#checkinDiscomfort').value, change: $('#checkinChange').value, note: $('#checkinNote').value };
  try {
    const data = await requestJSON('/api/progress-checkins', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    event.currentTarget.reset(); $('#checkinDate').value = currentDate(); await loadProgress({ force: true });
    toast(file ? `${data.progress_label}. The comparison image was not stored.` : `${data.progress_label}. Check-in saved.`);
  } catch (error) { toast(error.message || 'Could not save this check-in.'); }
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
$('#imageInput').onchange = event => setImage(event.target.files[0]);
$('#imageContext').onchange = updateImageContext;
const drop = $('#dropZone');
['dragenter', 'dragover'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(name => drop.addEventListener(name, event => { event.preventDefault(); drop.classList.remove('dragging'); }));
drop.addEventListener('drop', event => setImage(event.dataTransfer.files[0]));
$('#analyzeButton').onclick = analyze; $('#saveProgressButton').onclick = saveProgress; $('#viewCareButton').onclick = viewCare;
$$('[data-result-tab]').forEach(button => { button.onclick = () => showResultTab(button.dataset.resultTab); });
$('#doctorSearchForm').onsubmit = searchDoctors; $('#directorySearchForm').onsubmit = searchDirectory; $('#profileButton').onclick = openProfile; $('#topProfileButton').onclick = openProfile; $('#openProfileFromProgress').onclick = openProfile; $('#profileForm').onsubmit = saveProfile;
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
$('#routineForm').onsubmit = saveRoutine; $('#cancelRoutineEdit').onclick = resetRoutineForm; $('#checkinForm').onsubmit = saveCheckin;
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
  $('#imageContext').querySelector('option[value="general_photo"]').textContent = 'General skin, hair, or nail photo';
  updateImageContext();
  resetRoutineForm();
  $('#checkinDate').value = currentDate();
  await hydrateProfile();
  await loadProgress();
  showPage(location.hash.replace('#', '') || 'dashboard', { syncHistory: false });
}

initialiseApp();
