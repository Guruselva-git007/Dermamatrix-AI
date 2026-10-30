const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const definitions = source.slice(0, source.indexOf("\n$$('.area-choice button')"));
function harness() {
  const elements = new Map();
  const node = () => ({ children:[{}], options:[{}], value:'face_skin', checked:false, disabled:false, dataset:{}, style:{},
    textContent:'', innerHTML:'original', nextElementSibling:{textContent:''},
    classList:{add(){},remove(){},contains(){return false;},toggle(){}},
    setAttribute(){}, removeAttribute(){}, querySelector(){return null;}, querySelectorAll(){return [];},
    closest(){return node();}, focus(){} });
  const get = key => { if (!elements.has(key)) elements.set(key,node()); return elements.get(key); };
  const context = vm.createContext({document:{querySelector:get,querySelectorAll:()=>[],body:node()},window:{location:{protocol:'http:'},setTimeout,clearTimeout},localStorage:{setItem(){},getItem(){return null;}},getComputedStyle:()=>({getPropertyValue:()=> 'synthetic-css-token'}),console,AbortController,setTimeout,clearTimeout,URL,crypto:require('node:crypto').webcrypto});
  vm.runInContext(definitions+'\nglobalThis.api={state,analyze,requestJSON,selectArea,persistenceMessage,AssessmentState,transitionAssessment,persistPreferences};',context);
  return {context,api:context.api,get};
}
test('same-area selection retains checked context and capture selector without rebuilding them',()=>{
  const h=harness();h.get('#imageContext').value='dermoscopic_lesion';h.get('#symptomChips').innerHTML='checked symptoms';
  h.api.selectArea('Skin');
  assert.equal(h.get('#imageContext').value,'dermoscopic_lesion');
  assert.equal(h.get('#symptomChips').innerHTML,'checked symptoms');
});
test('duplicate analyze entry returns before network or form access',async()=>{
  const h=harness();h.api.state.assessmentInFlight=true;
  h.context.fetch=()=>{throw Error('duplicate network request');};
  await h.api.analyze();
});
test('abort preserves a distinguishable interruption and cleans the request timer',async()=>{
  const h=harness();
  h.context.fetch=(_url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Object.assign(Error(),{name:'AbortError'}))));
  const controller=new AbortController();const request=h.api.requestJSON('/api/assessments',{signal:controller.signal});controller.abort();
  await assert.rejects(request,e=>e.interrupted===true && /cancelled/.test(e.message));
});
test('timed out requests also carry interruption rather than successful completion',async()=>{
  const h=harness();h.context.fetch=(_url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Object.assign(Error(),{name:'AbortError'}))));
  await assert.rejects(h.api.requestJSON('/api/assessments',{},1),e=>e.interrupted===true && /too long/.test(e.message));
});
test('an account switch during CSRF preparation prevents the old draft from being sent',async()=>{
  const h=harness();let release,valid=true,calls=0;
  h.context.window.ConsumerClient={prepare:options=>new Promise(resolve=>{release=()=>resolve(options);})};
  h.context.fetch=async()=>{calls++;throw Error('old draft must never reach fetch');};
  const pending=h.api.requestJSON('/api/episodes',{method:'POST',body:'private draft',ownerGuard:()=>valid});
  valid=false;release();await assert.rejects(pending,/account changed.*Nothing was sent/);assert.equal(calls,0);
});
test('all API clients inherit the workspace guard even without a caller-supplied guard',async()=>{
  const h=harness();let release,calls=0;
  h.api.state.profile={patient_id:'OWNER-A'};
  h.context.window.ConsumerClient={prepare:options=>new Promise(resolve=>{release=()=>resolve(options);})};
  h.context.fetch=async()=>{calls++;throw Error('old action must not reach the next account');};
  const pending=h.api.requestJSON('/api/privacy/processing',{method:'PUT',body:'old account action'});
  h.api.state.profile={patient_id:'OWNER-B'};h.api.state.workspaceVersion++;
  release();await assert.rejects(pending,/account changed/i);assert.equal(calls,0);
});
for(const switchAccount of [false,true])test('revoked-session response '+(switchAccount?'cannot end a newer account':'still ends its current account'),async()=>{
  const h=harness();let release;const events=[];
  h.api.state.profile={patient_id:'OWNER-A'};
  h.context.CustomEvent=class{constructor(type){this.type=type;}};
  h.context.window.dispatchEvent=event=>events.push(event.type);
  h.context.fetch=()=>new Promise(resolve=>{release=()=>resolve({ok:false,status:401,json:async()=>({code:'SESSION_REVOKED',error:'Session revoked'})});});
  const pending=h.api.requestJSON('/api/profile');
  if(switchAccount){h.api.state.profile={patient_id:'OWNER-B'};h.api.state.workspaceVersion++;}
  release();await assert.rejects(pending,/Session revoked/);
  assert.deepEqual(events,switchAccount?[]:['dermamatrix-session-ended']);
});
test('the owner guard stays in the client and preserves normal request headers',async()=>{
  const h=harness();let sent;
  h.context.fetch=async(_url,options)=>{sent=options;return{ok:true,json:async()=>({saved:true})};};
  await h.api.requestJSON('/api/episodes',{method:'POST',headers:{'Idempotency-Key':'stable-synthetic-key'},body:'draft',ownerGuard:()=>true});
  assert.equal(sent.ownerGuard,undefined);assert.equal(sent.headers['Idempotency-Key'],'stable-synthetic-key');assert.equal(sent.body,'draft');
});
test('database failure and incomplete priority are never labelled as guest results',()=>{
  const h=harness();
  assert.match(h.api.persistenceMessage('not-persisted-guest'),/Guest/);
  assert.match(h.api.persistenceMessage('mysql'),/Saved/);
  for(const state of ['not-persisted-mysql-unavailable','not-saved-incomplete-priority']){
    assert.match(h.api.persistenceMessage(state),/Not saved/);assert.doesNotMatch(h.api.persistenceMessage(state),/Guest/);
  }
});
test('cancelled assessment can restart through the existing state machine',()=>{
  const h=harness();h.api.state.assessmentState=h.api.AssessmentState.ANALYZING;
  assert.equal(h.api.transitionAssessment(h.api.AssessmentState.CANCELLED),true);
  assert.equal(h.api.transitionAssessment(h.api.AssessmentState.INPUT_VALIDATING),true);
});
test('older preference response cannot override the latest choice',async()=>{
  const h=harness();h.api.state.profile={patient_id:'synthetic'};const responses=[];
  h.context.fetch=()=>new Promise(resolve=>responses.push(resolve));
  const first=h.api.persistPreferences({theme:'dark'});const second=h.api.persistPreferences({theme:'light'});
  responses[1]({ok:true,json:async()=>({preferences:{theme:'light'}})});await second;
  responses[0]({ok:true,json:async()=>({preferences:{theme:'dark'}})});await first;
  assert.equal(h.api.state.preferences.theme,'light');
});
test('successful HTTP with unreadable or non-object JSON cannot fabricate success',async()=>{
  const h=harness();
  for(const payload of [null, [], 'wrong']){
    h.context.fetch=async()=>({ok:true,json:async()=>payload});
    await assert.rejects(h.api.requestJSON('/api/assessments'),/incomplete response/);
  }
  h.context.fetch=async()=>({ok:true,json:async()=>{throw Error('invalid JSON');}});
  await assert.rejects(h.api.requestJSON('/api/assessments'),/unreadable response/);
});
test('cancellation cannot turn an idle screen or an interrupted request into a fabricated result',()=>{
  const h=harness();assert.equal(h.api.transitionAssessment(h.api.AssessmentState.CANCELLED),false);
  h.api.state.assessmentState=h.api.AssessmentState.ANALYZING;h.api.transitionAssessment(h.api.AssessmentState.CANCELLED);
  assert.equal(h.api.transitionAssessment(h.api.AssessmentState.RESULT_READY),false);
});
test('saved report list exposes older loaded results six at a time without another fetch',()=>{
  const h=harness();vm.runInContext('globalThis.renderReports=renderReportRegister;',h.context);
  h.api.state.profile={patient_id:'synthetic'};
  h.api.state.analyses=Array.from({length:14},(_,i)=>({assessment_id:`report-${i}`,created_at:'2026-10-25',area:'Hair',summary:{assessment_result:{consumer:{primary_result:{title:`Finding ${i}`}}}}}));
  const more={};const register=h.get('#reportRegister');register.querySelector=selector=>selector==='[data-show-more-reports]'?more:null;
  h.context.fetch=()=>{throw Error('Local expansion must not refetch history');};
  h.context.renderReports();assert.equal((register.innerHTML.match(/data-view-report=/g)||[]).length,6);assert.match(register.innerHTML,/Showing 6 of 14/);
  more.onclick();assert.equal((register.innerHTML.match(/data-view-report=/g)||[]).length,12);assert.match(register.innerHTML,/Show 2 more/);
  more.onclick();assert.equal((register.innerHTML.match(/data-view-report=/g)||[]).length,14);assert.doesNotMatch(register.innerHTML,/data-show-more-reports/);
});
test('small saved histories have no unnecessary expansion control',()=>{
  const h=harness();vm.runInContext('globalThis.renderReports=renderReportRegister;',h.context);h.api.state.profile={patient_id:'synthetic'};
  h.api.state.analyses=[{assessment_id:'one',created_at:'2026-10-25',area:'Sweat',summary:{assessment_result:{consumer:{primary_result:{title:'Questionnaire'}}}}}];
  h.context.renderReports();assert.equal((h.get('#reportRegister').innerHTML.match(/data-view-report=/g)||[]).length,1);assert.doesNotMatch(h.get('#reportRegister').innerHTML,/data-show-more-reports/);
});
