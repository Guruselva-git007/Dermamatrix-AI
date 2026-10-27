const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
function harness(file, marker, names){
  const nodes=new Map(),pending=[];
  const node=()=>({value:'',checked:false,options:[],children:[],textContent:'',disabled:false,hidden:false,append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;},add(){},setAttribute(){}});
  const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
  const context=vm.createContext({window:{ConsumerClient:{enabled:true}},state:{profile:{patient_id:'synthetic-owner'},checkins:[]},document:{getElementById:get,createElement:node,readyState:'loading',addEventListener(){},querySelectorAll:()=>[]},crypto:require('node:crypto').webcrypto,requestJSON:(url)=>new Promise((resolve,reject)=>pending.push({url,resolve,reject})),URLSearchParams,Option:class{},console});
  let source=fs.readFileSync(path.join(__dirname,'..',file),'utf8');source=source.replace(marker,`globalThis.api={${names.join(',')}};\n${marker}`);vm.runInContext(source,context);
  return{api:context.api,get,pending};
}
test('an older failed Today request cannot replace a newer successful refresh',async()=>{
  const h=harness('engagement.js','window.EngagementUI={',['loadToday','loadTodayFresh']);
  const old=h.api.loadToday(),latest=h.api.loadTodayFresh();
  h.pending[1].resolve({tasks:[],recent_result:null});await latest;
  h.pending[0].reject(Error('superseded failure'));await old;
  assert.equal(h.get('engagementStatus').textContent,'');assert.equal(h.get('todayTasks').children.length,1);
});
test('an older failed search cannot enable paging or overwrite the latest result state',async()=>{
  const h=harness('continuity.js','window.ContinuityUI={',['search']);
  const old=h.api.search(true),latest=h.api.search(true);
  h.pending[0].reject(Error('superseded failure'));await old;assert.equal(h.get('unifiedMore').disabled,true);
  h.pending[1].resolve({results:[],next_cursor:null});await latest;
  assert.match(h.get('unifiedStatus').textContent,/No matches/);assert.equal(h.get('unifiedMore').disabled,false);
});
test('a slower reminder preview cannot replace a newer timezone calculation',async()=>{
  const h=harness('continuity.js','window.ContinuityUI={',['previewReminder']);
  for(const [id,value] of Object.entries({routineSteps:'Step',routineTimes:'09:00',routineTimezone:'UTC',routineScheduleStatus:'active',routineScheduleArea:'General',quietStart:'21:00',quietEnd:'08:00'}))h.get(id).value=value;
  const old=h.api.previewReminder(),latest=h.api.previewReminder();
  h.pending[1].resolve({transport:'disabled',preview:{status:'active',timezone:'Europe/London',next_occurrence_utc:null,quiet_start:'21:00',quiet_end:'08:00',suppressed_times:[],opted_in:false,meaning:'Preview only'}});await latest;
  h.pending[0].reject(Error('superseded failure'));await old;
  assert.match(h.get('reminderPreview').textContent,/Europe\/London/);assert.doesNotMatch(h.get('reminderPreview').textContent,/superseded/);
});
