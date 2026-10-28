const{test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../engagement.js'),'utf8');
function harness(request=async()=>({analyses:[],next_cursor:null})){
 class Element{
  constructor(tag='div'){this.tag=tag;this.children=[];this.options=[];this.hidden=false;this.value='';this.textContent='';this.closed=false;this.attributes={};const classes=new Set();this.classList={add:c=>classes.add(c),remove:c=>classes.delete(c),contains:c=>classes.has(c)};}
  replaceChildren(...children){this.children=children;this.textContent='';if(this.options)this.options=children.filter(child=>child&&'value' in child);}
  add(option){this.options.push(option);}
  append(...children){this.children.push(...children);}
  close(){this.closed=true;}
  reset(){this.resetCount=(this.resetCount||0)+1;this.onReset?.();}
  setAttribute(key,value){this.attributes[key]=value;}
  focus(){this.focused=true;}
  scrollIntoView(){this.scrolled=true;}
  querySelectorAll(tag){return this.children.filter(child=>child.tag===tag);}
 }
 const nodes=new Map();const element=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
 const state={profile:{patient_id:'synthetic-owner'},routines:[],analyses:[{assessment_id:'saved-one',created_at:'2026-10-27'}]};
 let page='progress';const requests=[];
 const context={window:{ConsumerClient:{enabled:true}},state,document:{readyState:'loading',addEventListener(){},getElementById:element,querySelector:()=>({id:page}),createElement:tag=>new Element(tag)},Option:function(label,value){this.label=label;this.value=value;},requestJSON:(url)=>{requests.push(url);return request(url);},URLSearchParams,console};
 vm.createContext(context);vm.runInContext(source,context);
 return{ui:context.window.EngagementUI,state,nodes,element,requests,setPage:value=>page=value};
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
