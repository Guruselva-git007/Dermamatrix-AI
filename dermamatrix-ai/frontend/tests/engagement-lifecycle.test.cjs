const{test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../engagement.js'),'utf8');
function harness(request=async()=>({analyses:[],next_cursor:null})){
 class Element{
  constructor(tag='div'){this.tag=tag;this.tagName=tag.toUpperCase();this.children=[];this.options=[];this.hidden=false;this.value='';this.textContent='';this.closed=false;this.open=false;this.disabled=false;this.isConnected=true;this.attributes={};const classes=new Set();this.classList={add:c=>classes.add(c),remove:c=>classes.delete(c),contains:c=>classes.has(c)};}
  replaceChildren(...children){this.children=children;this.textContent='';if(this.options)this.options=children.filter(child=>child&&'value' in child);}
  add(option){this.options.push(option);}
  append(...children){this.children.push(...children);}
  close(){this.closed=true;this.open=false;this.onclose?.();}
  showModal(){this.closed=false;this.open=true;}
  reset(){this.resetCount=(this.resetCount||0)+1;this.onReset?.();}
  setAttribute(key,value){this.attributes[key]=value;}
  focus(){this.focused=true;document.activeElement=this;}
  getClientRects(){return [{}];}
  scrollIntoView(){this.scrolled=true;}
  querySelectorAll(selector){const tags=selector.split(',').map(s=>s.trim());return this.children.flatMap(child=>[...(tags.includes(child.tag)?[child]:[]),...(child.querySelectorAll?.(selector)||[])]);}
  querySelector(selector){return this.children.find(child=>selector==='[type=submit]'&&child.type==='submit')||null;}
 }
 const nodes=new Map();const element=id=>{if(!nodes.has(id)){const e=new Element();e.id=id;nodes.set(id,e);}return nodes.get(id);};
 const field=(id,tag='input')=>{const e=element(id);e.tag=tag;e.tagName=tag.toUpperCase();return e;};
 const scheduleForm=element('scheduleEditor');
 for(const id of ['routineSteps','routineTimes','routineTimezone','routineScheduleArea','routineScheduleStatus','routineEpisode','routineBodyArea','routineReminderOptIn','quietStart','quietEnd','scheduleEpisode'])scheduleForm.append(field(id,id==='routineSteps'?'textarea':'input'));
 const scheduleSubmit=field('scheduleSubmit','button');scheduleSubmit.type='submit';scheduleForm.append(scheduleSubmit);
 const contextForm=element('resultContextForm');contextForm.append(field('contextEpisode'),field('contextBodyArea'));const contextSubmit=field('contextSubmit','button');contextSubmit.type='submit';contextForm.append(contextSubmit);
 const state={profile:{patient_id:'synthetic-owner'},routines:[],analyses:[{assessment_id:'saved-one',created_at:'2026-10-27'}]};
 let page='progress',confirm=true;const requests=[],toasts=[],baselines=new Map(),prompts=[];
 const snapshot=root=>JSON.stringify(root.querySelectorAll('input,select,textarea').map(e=>[e.id,e.value,e.checked]));
 const draft={snapshot,clean:(root,value=snapshot(root))=>baselines.set(root,value),forget:root=>baselines.delete(root),allowDiscard(root){if(!baselines.has(root)||baselines.get(root)===snapshot(root))return true;prompts.push(root.id);return confirm;}};
 const document={readyState:'loading',addEventListener(){},getElementById:element,querySelector:()=>({id:page}),querySelectorAll:()=>[],createElement:tag=>new Element(tag),activeElement:field('originalFocus','button')};
 const context={window:{ConsumerClient:{enabled:true},DraftUX:draft},state,document,Option:function(label,value){this.label=label;this.value=value;},requestJSON:(url,options)=>{requests.push(url);return request(url,options);},URLSearchParams,console,toast:message=>toasts.push(message),loadProgress:async()=>{}};
 const instrumented=source.replace('  window.EngagementUI={','  globalThis.controller={loadSchedule,editContext,saveSchedule,closeContext};\n  window.EngagementUI={');
 vm.createContext(context);vm.runInContext(instrumented,context);
 return{ui:context.window.EngagementUI,controller:context.controller,state,nodes,element,requests,toasts,prompts,draft,document,setConfirm:value=>confirm=value,setPage:value=>page=value};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('Journey refreshes when saved assessments change without duplicate unchanged refreshes',async()=>{
 const h=harness();h.ui.progress();await tick();assert.equal(h.requests.length,1);
 h.ui.progress();await tick();assert.equal(h.requests.length,1);
 h.state.analyses.unshift({assessment_id:'saved-two',created_at:'2026-10-27'});h.ui.progress();await tick();assert.equal(h.requests.length,2);
});
test('account clear removes private selectors, status text, results and guest-only dead controls',()=>{
 const h=harness();for(const id of ['reminderStatus','scheduleStatus','journeySearchStatus','engagementStatus']){h.element(id).textContent='previous-account status';}
 h.element('scheduleRoutine').options=[{label:'Private routine'}];h.element('routineSteps').value='Private step';h.element('journeySearchResults').append({tag:'article'});
 h.element('scheduleEditor').onReset=()=>{h.element('routineSteps').value='';};
 h.ui.clear();h.state.profile=null;h.ui.progress();
 for(const id of ['reminderStatus','scheduleStatus','journeySearchStatus','engagementStatus'])assert.equal(h.element(id).textContent,'');
 assert.equal(h.element('scheduleRoutine').options.length,1);assert.equal(h.element('routineSteps').value,'');assert.equal(h.element('journeySearchResults').children.length,0);assert.equal(h.element('completeJourney').hidden,true);assert.equal(h.element('scheduleWorkspace').hidden,true);
 for(const id of ['scheduleEditor','journeySearchForm','resultContextForm'])assert.equal(h.element(id).resetCount,1);
 assert.equal(h.element('scheduleEditor').hidden,true);assert.equal(h.element('journeyMore').hidden,true);
});
test('late history response cannot repopulate a signed-out workspace',async()=>{
 let release;const pending=new Promise(resolve=>release=resolve);const h=harness(()=>pending);
 h.ui.progress();h.ui.clear();h.state.profile=null;release({analyses:[{assessment_id:'private-old',summary:{},area:'Skin',created_at:'2026-10-27'}],next_cursor:null});await tick();assert.equal(h.element('journeySearchResults').children.length,0);assert.equal(h.element('journeySearchStatus').textContent,'');
});
test('guest Journey does not request or expose account search',async()=>{const h=harness();h.state.profile=null;h.ui.progress();await tick();assert.equal(h.requests.length,0);assert.equal(h.element('completeJourney').hidden,true);});
test('closing a guide invalidates its delayed response and preserves the search',async()=>{
 let release;const h=harness(()=>new Promise(resolve=>release=resolve));h.setPage('learn');h.element('learnSearch').value='saved search';
 const pending=h.ui.openGuide('synthetic-guide');h.ui.closeGuide({restoreFocus:false});release({topic:{name:'Late guide'}});await pending;
 assert.equal(h.element('learnDetail').hidden,true);assert.equal(h.element('learnDetail').children.length,0);assert.equal(h.element('learnSearch').value,'saved search');assert.equal(h.element('learnStatus').textContent,'');
});
test('account clearing invalidates a pending guide and removes account-specific reader controls',async()=>{
 let release;const h=harness(()=>new Promise(resolve=>release=resolve));h.setPage('learn');h.element('learnDetail').append({tag:'button',textContent:'Remove bookmark'});
 const pending=h.ui.openGuide('synthetic-guide');h.ui.clear();h.state.profile=null;release({topic:{name:'Late guide'}});await pending;
 assert.equal(h.element('learnDetail').children.length,0);assert.equal(h.element('learnDetail').hidden,true);assert.equal(h.element('learnRetry').hidden,true);assert.equal(h.element('learnForm').resetCount,1);
});
test('a guide request that fails after cancellation cannot replace the cleared status',async()=>{
 let reject;const h=harness(()=>new Promise((resolve,fail)=>reject=fail));h.setPage('learn');const pending=h.ui.openGuide('synthetic-guide');h.ui.closeGuide({restoreFocus:false});reject(Error('Old network failure'));await pending;
 assert.equal(h.element('learnStatus').textContent,'');assert.equal(h.element('learnRetry').hidden,true);
});

const schedule=(name='Saved step')=>({schedule:{version:1,steps:[name],days:[],times:['09:00'],timezone:'UTC',area:'General',status:'active',episode:'',body_area:'',reminders:false,quiet_start:'21:00',quiet_end:'08:00'},events:[]});
test('schedule switch cancellation preserves the selected routine and unsaved input',async()=>{
 const h=harness(async()=>schedule());await h.ui.configureRoutine('A');h.element('routineSteps').value='Synthetic unfinished plan';h.setConfirm(false);
 h.element('scheduleRoutine').value='B';await h.controller.loadSchedule();
 assert.equal(h.element('scheduleRoutine').value,'A');assert.equal(h.element('routineSteps').value,'Synthetic unfinished plan');assert.equal(h.requests.some(url=>url.endsWith('/B')),false);
});
test('an old label save cannot close a replacement result dialog or replace its input',async()=>{
 let release;const h=harness(url=>url.endsWith('/context')?new Promise(resolve=>release=resolve):Promise.resolve({analyses:[],next_cursor:null}));
 h.controller.editContext({assessment_id:'A',context:{}});h.element('contextEpisode').value='Submitted A';
 const old=h.element('resultContextForm').onsubmit({preventDefault(){},currentTarget:h.element('resultContextForm')});
 h.element('resultContextDialog').close();h.controller.editContext({assessment_id:'B',context:{}});h.element('contextEpisode').value='Synthetic unfinished B';release({message:'Old A saved'});await old;
 assert.equal(h.element('resultContextDialog').open,true);assert.equal(h.element('contextEpisode').value,'Synthetic unfinished B');assert.equal(h.element('contextSubmit').disabled,false);assert.equal(h.toasts.length,0);
});
test('explicitly discarding a schedule loads the chosen routine and establishes a clean draft',async()=>{
 const h=harness(async url=>schedule(url.endsWith('/B')?'Saved B':'Saved A'));await h.ui.configureRoutine('A');h.element('routineSteps').value='Unsaved A';
 h.element('scheduleRoutine').value='B';await h.controller.loadSchedule();
 assert.equal(h.element('scheduleRoutine').value,'B');assert.equal(h.element('routineSteps').value,'Saved B');assert.deepEqual(h.prompts,['scheduleEditor']);h.setConfirm(false);assert.equal(h.draft.allowDiscard(h.element('scheduleEditor')),true);
});
test('reopening the same routine refreshes history while retaining current input without a discard prompt',async()=>{
 const h=harness(async()=>schedule());await h.ui.configureRoutine('A');h.element('routineSteps').value='Unsubmitted A';h.setConfirm(false);await h.ui.configureRoutine('A');
 assert.equal(h.element('routineSteps').value,'Unsubmitted A');assert.equal(h.prompts.length,0);assert.equal(h.requests.filter(url=>url.endsWith('/A')).length,2);
});
test('initial schedule loading pauses fields and an old response cannot unlock or overwrite the next load',async()=>{
 const replies=[];const h=harness(url=>new Promise(resolve=>replies.push({url,resolve})));
 const first=h.ui.configureRoutine('A');assert.equal(h.element('routineSteps').disabled,true);assert.equal(h.element('scheduleSubmit').disabled,true);
 const second=h.ui.configureRoutine('B');replies[0].resolve(schedule('Saved A'));await first;assert.equal(h.element('routineSteps').disabled,true);assert.equal(h.element('scheduleSubmit').disabled,true);
 replies[1].resolve(schedule('Saved B'));await second;assert.equal(h.element('routineSteps').value,'Saved B');assert.equal(h.element('routineSteps').disabled,false);assert.equal(h.element('scheduleSubmit').disabled,false);
});
test('a failed initial schedule load cannot expose stale fields as the next routine editor',async()=>{
 const h=harness(async url=>{if(url.endsWith('/B'))throw Error('Synthetic unavailable');return schedule('Saved A');});await h.ui.configureRoutine('A');await h.ui.configureRoutine('B');
 assert.equal(h.element('scheduleEditor').hidden,true);assert.match(h.element('scheduleStatus').textContent,/not confirmed.*Choose the routine again/);
 const requests=h.requests.length;await h.controller.saveSchedule({preventDefault(){},currentTarget:h.element('scheduleEditor')});assert.equal(h.requests.length,requests);
});
test('account clearing invalidates a pending schedule load and restores usable controls for the next account',async()=>{
 let release;const h=harness(()=>new Promise(resolve=>release=resolve));const old=h.ui.configureRoutine('A');h.ui.clear();h.state.profile={patient_id:'next-owner'};h.element('routineSteps').value='Next workspace';release(schedule('Old private A'));await old;
 assert.equal(h.element('routineSteps').value,'Next workspace');assert.equal(h.element('routineSteps').disabled,false);assert.equal(h.element('scheduleEditor').hidden,true);assert.equal(h.element('scheduleStatus').textContent,'');
});
test('a confirmed schedule save cleans its submitted snapshot while retaining newer edits',async()=>{
 let release;const h=harness((url,options)=>options?.method==='PUT'?new Promise(resolve=>release=resolve):Promise.resolve(url==='/api/today'?{tasks:[]}:schedule()));
 await h.ui.configureRoutine('A');h.element('routineSteps').value='Submitted step';const pending=h.controller.saveSchedule({preventDefault(){},currentTarget:h.element('scheduleEditor')});h.element('routineSteps').value='Newer unsaved step';release({...schedule('Submitted step'),message:'Saved'});await pending;
 assert.equal(h.element('routineSteps').value,'Newer unsaved step');assert.equal(h.element('scheduleSubmit').disabled,false);assert.equal(h.element('scheduleStatus').textContent,'Submitted schedule saved. Your newer edits are still unsaved.');h.setConfirm(false);assert.equal(h.draft.allowDiscard(h.element('scheduleEditor')),false);
 h.element('routineSteps').value='Submitted step';assert.equal(h.draft.allowDiscard(h.element('scheduleEditor')),true);
});
test('an old schedule save cannot unlock the next routine while its schedule is loading',async()=>{
 let releaseSave,releaseLoad;const h=harness((url,options)=>options?.method==='PUT'?new Promise(resolve=>releaseSave=resolve):url.endsWith('/B')?new Promise(resolve=>releaseLoad=resolve):Promise.resolve(schedule()));
 await h.ui.configureRoutine('A');h.element('routineSteps').value='Submitted A';const pending=h.controller.saveSchedule({preventDefault(){},currentTarget:h.element('scheduleEditor')});const next=h.ui.configureRoutine('B');releaseSave({...schedule(),message:'Old A saved'});await pending;
 assert.equal(h.element('scheduleSubmit').disabled,true);releaseLoad(schedule('Saved B'));await next;assert.equal(h.element('routineSteps').value,'Saved B');assert.equal(h.element('scheduleSubmit').disabled,false);
});
test('label Cancel and Escape protect dirty input while explicit discard closes it',()=>{
 const h=harness();h.controller.editContext({assessment_id:'A',context:{}});h.element('contextEpisode').value='Synthetic unsaved label';h.setConfirm(false);
 assert.equal(h.controller.closeContext(),false);assert.equal(h.element('resultContextDialog').open,true);let prevented=false;h.element('resultContextDialog').oncancel({preventDefault(){prevented=true;}});assert.equal(prevented,true);assert.equal(h.element('contextEpisode').value,'Synthetic unsaved label');
 h.setConfirm(true);assert.equal(h.controller.closeContext(),true);assert.equal(h.element('resultContextDialog').open,false);
});
test('label fields pause during save, duplicate submits are ignored and failure preserves recoverable input',async()=>{
 let reject,calls=0;const h=harness(()=>{calls++;return new Promise((_,fail)=>reject=fail);});h.controller.editContext({assessment_id:'A',context:{}});h.element('contextEpisode').value='Submitted A';
 const event={preventDefault(){},currentTarget:h.element('resultContextForm')};const old=h.element('resultContextForm').onsubmit(event);assert.equal(h.element('contextEpisode').disabled,true);await h.element('resultContextForm').onsubmit(event);assert.equal(calls,1);
 reject(Error('Synthetic lost response'));await old;assert.equal(h.element('resultContextDialog').open,true);assert.equal(h.element('contextEpisode').value,'Submitted A');assert.equal(h.element('contextEpisode').disabled,false);assert.equal(h.element('contextSubmit').disabled,false);assert.match(h.element('contextStatus').textContent,/not confirmed.*input remains/);
});
test('an old label completion cannot unlock a newer label save or steal its focus',async()=>{
 const writes=[];const h=harness(url=>url.endsWith('/context')?new Promise(resolve=>writes.push(resolve)):Promise.resolve({analyses:[],next_cursor:null}));
 h.controller.editContext({assessment_id:'A',context:{}});const event={preventDefault(){},currentTarget:h.element('resultContextForm')};const first=h.element('resultContextForm').onsubmit(event);h.controller.closeContext();h.controller.editContext({assessment_id:'B',context:{}});const second=h.element('resultContextForm').onsubmit(event);
 writes[0]({message:'A saved'});await first;assert.equal(h.element('resultContextDialog').open,true);assert.equal(h.element('contextSubmit').disabled,true);assert.equal(h.element('contextEpisode').disabled,true);assert.equal(h.document.activeElement,h.element('contextEpisode'));
 writes[1]({message:'B saved'});await second;assert.equal(h.element('resultContextDialog').open,false);assert.deepEqual(h.toasts,['B saved']);
});
for(const failure of [false,true])test('an old label '+(failure?'failure':'success')+' cannot affect the next account dialog',async()=>{
 let finish;const h=harness(url=>url.endsWith('/context')?new Promise((resolve,reject)=>finish=failure?reject:resolve):Promise.resolve({analyses:[],next_cursor:null}));h.controller.editContext({assessment_id:'A',context:{}});
 const old=h.element('resultContextForm').onsubmit({preventDefault(){},currentTarget:h.element('resultContextForm')});h.ui.clear();h.state.profile={patient_id:'next-owner'};h.controller.editContext({assessment_id:'B',context:{episode:'Current B'}});const status=h.element('contextStatus').textContent;
 finish(failure?Error('Old private failure'):{message:'Old A saved'});await old;assert.equal(h.element('resultContextDialog').open,true);assert.equal(h.element('contextEpisode').value,'Current B');assert.equal(h.element('contextStatus').textContent,status);assert.equal(h.element('contextSubmit').disabled,false);assert.equal(h.toasts.length,0);
});
test('a label history refresh cannot steal focus chosen after the saved dialog closed',async()=>{
 let release;const h=harness(url=>url.endsWith('/context')?Promise.resolve({message:'Saved'}):new Promise(resolve=>release=resolve));h.controller.editContext({assessment_id:'A',context:{}});
 const pending=h.element('resultContextForm').onsubmit({preventDefault(){},currentTarget:h.element('resultContextForm')});await tick();assert.equal(h.element('resultContextDialog').open,false);h.element('briefQuestions').focus();release({analyses:[],next_cursor:null});await pending;
 assert.equal(h.document.activeElement,h.element('briefQuestions'));
});
