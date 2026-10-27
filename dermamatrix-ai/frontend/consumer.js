/* Consumer account UI and CSRF client. No health drafts or tokens in storage. */
(() => {
  'use strict';
  let csrf = '', availability = null, probe = null, generation = 0, owner = null;
  const params = new URLSearchParams(location.hash.slice(1));
  let incomingAction = params.has('account_action') ? { purpose: params.get('account_action'), token: params.get('token') || '' } : null;
  let pendingAction = null, rightsKey = null, rightsSignature = null;
  if (incomingAction) history.replaceState(null, '', `${location.pathname}${location.search}#settings`);
  const el = id => document.getElementById(id);
  const text = (node, value) => { node.textContent = value; return node; };
  const item = (tag, value) => text(document.createElement(tag), value);
  const button = (label, action) => { const b = item('button', label); b.type = 'button'; b.className = 'button quiet'; b.onclick = action; return b; };
  const deliveryCopy = value => value?.state === 'sink_written' ? 'Saved to the isolated development mailbox. No real email was sent.' : value?.state === 'provider_accepted' ? 'The email provider accepted the message. Delivery has not been confirmed.' : 'Delivery has not been confirmed.';

  window.ConsumerClient = {
    async prepare(options = {}) {
      if (availability === null) {
        if (!probe) probe = fetch('/api/security/csrf', { credentials: 'same-origin', cache: 'no-store' }).then(async r => {
          if (r.status === 503 || r.status === 404) { availability = false; return; }
          if (!r.ok) throw Error('Account security could not be loaded. Retry.');
          const data = await r.json(); csrf = data.csrf_token; availability = true;
        }).finally(() => { probe = null; });
        await probe;
      }
      if (availability && !['GET', 'HEAD', 'OPTIONS'].includes((options.method || 'GET').toUpperCase())) {
        const response = await fetch('/api/security/csrf', {credentials:'same-origin',cache:'no-store'});
        if (!response.ok) throw Error('Account security could not be refreshed. Retry.');
        csrf = (await response.json()).csrf_token;
        return { ...options, headers: { ...options.headers, 'X-CSRF-Token': csrf } };
      }
      return options;
    },
    observe(response) { const next = response.headers.get('X-CSRF-Token'); if (next) csrf = next; },
    get enabled() { return availability === true; }
  };

  async function call(path, payload, method = 'POST', headers = {}) {
    return requestJSON(path, { method, headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(payload) });
  }
  function message(value, error = false) {
    const node = el('consumerStatus'); if (!node) return;
    node.textContent = value; node.dataset.error = String(error);
  }
  async function run(form, work) {
    const submit = form.querySelector('[type=submit]');
    if (submit?.disabled) return;
    if (submit) submit.disabled = true;
    const version = generation;
    try { const data = await work(); if (version === generation) return data; }
    catch (error) { if (version === generation) message(error.message || 'This action could not be completed.', true); }
    finally { if (submit) submit.disabled = false; form.querySelectorAll('input[type=password]').forEach(i => { i.value = ''; }); }
  }
  function showAction(action = null) {
    const dialog = el('accountActionDialog');
    el('accountActionTitle').textContent = action ? 'Confirm account action' : 'Reset your password';
    el('actionEmailField').hidden = Boolean(action);
    el('actionPasswordField').hidden = action?.purpose !== 'reset_password';
    el('actionEmail').required = !action;
    el('actionPassword').required = action?.purpose === 'reset_password';
    el('accountActionMessage').textContent = action ? 'Review this request, then confirm. Opening the link alone makes no account change.' : 'Enter your account email. A reset link is prepared only for a matching active account.';
    dialog.dataset.mode = action ? 'confirm' : 'request';
    pendingAction = action;
    dialog.querySelector('[type=submit]').hidden = false;
    el('cancelAccountAction').textContent = 'Cancel';
    el('accountActionForm').reset();
    dialog.showModal();
    (action?.purpose === 'reset_password' ? el('actionPassword') : action ? dialog.querySelector('[type=submit]') : el('actionEmail')).focus();
  }
  window.addEventListener('hashchange', () => {
    const values = new URLSearchParams(location.hash.slice(1));
    if (!values.has('account_action')) return;
    const action = {purpose: values.get('account_action'), token: values.get('token') || ''};
    history.replaceState(null, '', `${location.pathname}${location.search}#settings`);
    if (el('accountActionDialog')) showAction(action); else incomingAction = action;
  });

  async function refreshSecurity() {
    if (!owner || !el('consumerAccount')) return;
    const version = generation;
    el('consumerAccount').hidden = false;
    el('consumerAccount').querySelectorAll('[data-consumer-feature]').forEach(panel => { panel.hidden = !window.ConsumerClient.enabled; });
    if (!window.ConsumerClient.enabled) return;
    el('resendVerification').disabled = true;
    el('consumerDeliveryState').textContent = 'Checking email availability…';
    try {
      const [account, privacy] = await Promise.all([requestJSON('/api/security/account'), requestJSON('/api/privacy')]);
      if (version !== generation || !owner) return;
      el('emailVerificationState').textContent = account.email_verified ? 'Email verified' : 'Email not verified';
      el('processingState').textContent = privacy.processing_paused ? 'New health processing is paused.' : 'New health processing is enabled; consent is still required for each assessment.';
      el('processingPaused').value = String(!privacy.processing_paused);
      el('processingPauseButton').textContent = privacy.processing_paused ? 'Resume new processing' : 'Pause new processing';
      el('consumerDeliveryState').textContent = account.delivery_mode === 'sink' ? 'Isolated development mailbox. Real email delivery is not enabled.' : account.delivery_mode === 'disabled' ? 'Email delivery is not configured. Verification and recovery cannot send messages yet.' : 'Configured email transport. Delivery confirmation is separate.';
      el('resendVerification').disabled = account.email_verified || account.delivery_mode === 'disabled';
      el('resendVerification').textContent = account.email_verified ? 'Email verified' : account.delivery_mode === 'disabled' ? 'Email service unavailable' : 'Send verification link';
      const sessions = el('consumerSessions'); sessions.replaceChildren();
      for (const entry of account.sessions) {
        const row = document.createElement('li');
        row.append(item('strong', entry.current ? 'This browser' : 'Another browser'), item('p', `${entry.device_label.startsWith('Mozilla/') ? 'Browser (legacy device label)' : entry.device_label} · Expires ${new Date(entry.expires_at).toLocaleDateString()}`));
        if (!entry.current) row.append(button('Revoke session', () => { el('sessionTarget').value = entry.session_id; el('sessionPassword').focus(); message('Confirm your current password below to revoke this session.'); }));
        sessions.append(row);
      }
      const requests = el('privacyRequests'); requests.replaceChildren();
      for (const entry of privacy.requests) requests.append(item('li', `${entry.kind.replaceAll('_', ' ')} · Recorded locally, awaiting an operator · ${new Date(entry.created_at).toLocaleDateString()}`));
      if (!privacy.requests.length) requests.append(item('li', 'No requests recorded.'));
      const consents = el('consentHistory'); consents.replaceChildren();
      for (const entry of privacy.consents) consents.append(item('li', `${entry.purpose} · ${entry.consent_version} · ${new Date(entry.accepted_at).toLocaleDateString()}`));
    } catch (error) { if (version === generation) message(error.message, true); }
  }

  window.ConsumerUI = {
    clear() { generation++; owner = null; rightsKey = null; rightsSignature = null; el('consumerAccount')?.setAttribute('hidden', ''); el('consumerSessions')?.replaceChildren(); el('privacyRequests')?.replaceChildren(); el('consentHistory')?.replaceChildren(); document.querySelectorAll('#consumerAccount form').forEach(form => form.reset()); for(const id of ['consumerStatus','consumerDeliveryState','emailVerificationState','processingState'])if(el(id))el(id).textContent=''; if(el('resendVerification'))el('resendVerification').disabled=true; if (el('accountActionDialog')?.open) el('accountActionDialog').close(); pendingAction = null; },
    session(profile) { generation++; owner = profile?.patient_id || null; },
    ready() { if (incomingAction) { const action = incomingAction; incomingAction = null; showAction(action); } },
    refresh: refreshSecurity,
    recover() { showAction(); }
  };

  function install() {
    const section = document.createElement('section'); section.id = 'consumerAccount'; section.className = 'consumer-account'; section.hidden = true;
    section.innerHTML = `
      <header><h2>Security & privacy</h2><p>Manage your account access and the information you choose to process.</p></header>
      <p id="consumerStatus" class="consumer-status" role="status" aria-live="polite"></p>
      <section class="consumer-panel" aria-labelledby="consumerEmailTitle"><h3 id="consumerEmailTitle">Email & account security</h3><p id="emailVerificationState"></p><p id="consumerDeliveryState"></p><button id="resendVerification" class="button quiet" type="button" disabled>Send verification link</button>
      <details><summary>Change password</summary><form id="changePasswordForm"><label>Current password<input name="current_password" type="password" autocomplete="current-password" required maxlength="128"></label><label>New password<input name="new_password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required aria-describedby="newPasswordHelp"></label><p id="newPasswordHelp">Use 8–128 characters. Other sessions and outstanding account links will be revoked.</p><button type="submit" class="button primary">Change password</button></form></details>
      <details><summary>Change email address</summary><form id="changeEmailForm"><label>New email<input name="new_email" type="email" autocomplete="email" maxlength="254" required></label><label>Current password<input name="current_password" type="password" autocomplete="current-password" maxlength="128" required></label><p>The new address must be verified before it replaces your account email.</p><button type="submit" class="button primary">Request email change</button></form></details></section>
      <section class="consumer-panel" aria-labelledby="sessionTitle"><h3 id="sessionTitle">Active sessions</h3><ul id="consumerSessions" class="consumer-list"></ul><form id="revokeSessionForm"><input id="sessionTarget" type="hidden" name="session_id" value="others"><label>Current password<input id="sessionPassword" name="current_password" type="password" autocomplete="current-password" maxlength="128" required></label><button type="submit" class="button quiet">Revoke selected / other sessions</button></form></section>
      <section class="consumer-panel" aria-labelledby="privacyTitle"><h3 id="privacyTitle">Your health information</h3><p id="processingState"></p><p>Pausing stops new account health processing and cancels pending reminders. Existing records remain available for access and export. It does not erase records or apply to a separately chosen guest workspace.</p><form id="processingControlForm"><input id="processingPaused" name="paused" type="hidden"><label>Confirm current password<input name="current_password" type="password" autocomplete="current-password" maxlength="128" required></label><button id="processingPauseButton" type="submit" class="button quiet">Pause new processing</button></form><details><summary>Recorded consent history</summary><ul id="consentHistory" class="consumer-list"></ul></details><p>Use <strong>Download account data (JSON)</strong> below for your complete local account copy. Source photos are not retained.</p></section>
      <section class="consumer-panel" aria-labelledby="rightsTitle"><h3 id="rightsTitle">Requests & corrections</h3><p>Requests are recorded in this local workspace. No monitored support service or erasure policy has been approved. A recorded request does not mean it was reviewed or that data was deleted.</p><form id="rightsRequestForm"><label>Request type<select name="kind"><option value="correction">Correct account data</option><option value="deletion">Request data deletion</option><option value="account_closure">Request account closure</option><option value="support">Ask for help</option><option value="content_correction">Report educational content</option></select></label><label>Details<textarea name="note" maxlength="2000" aria-describedby="rightsNoteHelp"></textarea></label><small id="rightsNoteHelp">Up to 2,000 characters. Avoid adding photos or unnecessary health details.</small><label>Current password (required for deletion or closure)<input name="current_password" type="password" autocomplete="current-password" maxlength="128"></label><button type="submit" class="button primary">Record request locally</button></form><h4>Your request status</h4><ul id="privacyRequests" class="consumer-list"></ul></section>`;
    section.querySelectorAll('.consumer-panel').forEach(panel => { panel.dataset.consumerFeature = ''; });
    el('settings')?.querySelector('.settings-groups')?.before(section);
    const dialog = document.createElement('dialog'); dialog.id = 'accountActionDialog'; dialog.className = 'consumer-dialog';
    dialog.setAttribute('aria-labelledby', 'accountActionTitle');
    dialog.innerHTML = `<form id="accountActionForm"><h2 id="accountActionTitle">Account action</h2><p id="accountActionMessage" role="status" aria-live="polite"></p><label id="actionEmailField">Email address<input id="actionEmail" type="email" autocomplete="email" maxlength="254"></label><label id="actionPasswordField" hidden>New password<input id="actionPassword" type="password" autocomplete="new-password" minlength="8" maxlength="128" aria-describedby="actionPasswordHelp"><small id="actionPasswordHelp">Use 8–128 characters.</small></label><div class="consumer-actions"><button type="button" id="cancelAccountAction" class="button quiet">Cancel</button><button type="submit" class="button primary">Continue</button></div></form>`;
    document.body.append(dialog);
    el('cancelAccountAction').onclick = () => dialog.close();
    dialog.addEventListener('close', () => { pendingAction = null; el('accountActionForm').reset(); });
    el('accountActionForm').onsubmit = async event => {
      event.preventDefault(); const submit = event.currentTarget.querySelector('[type=submit]'); if (submit.disabled) return; submit.disabled = true;
      try {
        const action = pendingAction;
        const data = action ? await call('/api/security/action', { ...action, new_password: el('actionPassword').value }) : await call('/api/security/reset-password', { email_address: el('actionEmail').value });
        el('accountActionMessage').textContent = data.message + (data.delivery_mode === 'sink' ? ' Isolated development mailbox only; no real email sent.' : '');
        el('actionPassword').value = '';
        if (action) { pendingAction = null; submit.hidden = true; el('actionPasswordField').hidden = true; el('cancelAccountAction').textContent = 'Close'; if (action.purpose !== 'verify_email') { clearWorkspaceEvidence(); state.profile = null; showAuthGate('login'); setAuthMessage(data.message, true); } else refreshSecurity(); }
      } catch (error) { el('accountActionMessage').textContent = error.message; }
      finally { submit.disabled = false; }
    };
    el('resendVerification').onclick = async event => {
      event.currentTarget.disabled = true;
      try { const d = await call('/api/security/verify-email', {}); message(deliveryCopy(d.delivery)); }
      catch (error) { message(error.message, true); }
      finally { el('resendVerification').disabled = false; }
    };
    for (const [id, path] of [['changePasswordForm', '/api/security/password'], ['changeEmailForm', '/api/security/email'], ['revokeSessionForm', '/api/security/sessions/revoke'], ['processingControlForm', '/api/privacy/processing'], ['rightsRequestForm', '/api/privacy/requests']]) {
      el(id).onsubmit = async event => {
        event.preventDefault(); const form = event.currentTarget;
        const data = Object.fromEntries(new FormData(form));
        if (id === 'processingControlForm') data.paused = data.paused === 'true';
        if (id === 'rightsRequestForm') { const signature = JSON.stringify({kind: data.kind, note: data.note}); if (rightsSignature !== signature) { rightsSignature = signature; rightsKey = crypto.randomUUID(); } }
        const result = await run(form, () => call(path, data, id === 'processingControlForm' ? 'PUT' : 'POST', id === 'rightsRequestForm' ? { 'Idempotency-Key': rightsKey } : {}));
        if (result) { message(result.message || 'Request recorded locally, awaiting an operator.'); if (result.delivery) message(deliveryCopy(result.delivery)); if (id === 'rightsRequestForm') { form.reset(); rightsKey = null; rightsSignature = null; } await refreshSecurity(); }
      };
    }

  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install); else install();
})();
