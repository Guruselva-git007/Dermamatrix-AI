const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

// Execute the real controller, with a small DOM and controllable network replies.
function harness(){
  const nodes=new Map(),frames=[],pending=[];let document;
  class Element{
    constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.options=[];this.value='';this.textContent='';this.hidden=false;this.open=false;this.disabled=false;this.attributes={};this.isConnected=true;this.valid=true;}
    set id(value){this._id=value;nodes.set(value,this);}get id(){return this._id||'';}
    get firstChild(){return this.children[0]||null;}
    append(...children){this.children.push(...children);}
    prepend(...children){this.children.unshift(...children);}
    replaceChildren(...children){this.children=children;this.textContent='';if(this.tagName==='SELECT')this.options=children;}
    add(option){this.options.push(option);}
    setAttribute(key,value){this.attributes[key]=value;}
    removeAttribute(key){delete this.attributes[key];}
    showModal(){this.open=true;}
    close(){this.open=false;this.onclose?.();}
    focus(){document.activeElement=this;}
    reset(){for(const child of this.children){child.value='';child.checked=false;child.reset?.();}}
    reportValidity(){return this.valid;}
    querySelector(selector){
      for(const child of this.children){if(selector==='[type=submit]'&&child.type==='submit')return child;const found=child.querySelector?.(selector);if(found)return found;}
      return null;
    }
  }
  const get=id=>{if(!nodes.has(id)){const node=new Element();node.id=id;}return nodes.get(id);};
  const fallback=new Element('h1'),trigger=new Element('button');
  document={getElementById:get,createElement:tag=>new Element(tag),readyState:'loading',addEventListener(){},querySelector:()=>fallback,activeElement:trigger};
  const context={window:{ConsumerClient:{enabled:true},EngagementUI:{refresh:async()=>{}}},state:{profile:{patient_id:'owner-A'},checkins:[],routines:[]},document,Option:class{constructor(text,value){this.text=text;this.value=value;}},crypto:require('node:crypto').webcrypto,currentDate:()=> '2026-10-30',Date,URLSearchParams,requestAnimationFrame:fn=>frames.push(fn),toast(){},loadProgress:async()=>true,console,
    requestJSON:url=>{
      if(url==='/api/episodes')return Promise.resolve({episodes:[],body_areas:[]});
      if(url==='/api/episode-links')return Promise.resolve({links:{}});
      if(url==='/api/bookmarks')return Promise.resolve({bookmarks:[]});
      return new Promise((resolve,reject)=>pending.push({url,resolve,reject}));
    }};
  let source=fs.readFileSync(path.join(__dirname,'../continuity.js'),'utf8');
  source=source.replace('  window.ContinuityUI={','  globalThis.api={dialog,previewBrief,invalidateBrief,resetBriefDates};\n  window.ContinuityUI={');
  vm.createContext(context);vm.runInContext(source,context);
  get('continuityDialog');const brief=get('visitBriefForm');for(const id of ['briefStart','briefEnd','briefQuestions'])brief.append(get(id));
  get('briefStart').value='2026-10-01';get('briefEnd').value='2026-10-30';
  return{api:context.api,ui:context.window.ContinuityUI,get,pending,frames,document,trigger,content:()=>new Element(),state:context.state};
}
const submit=h=>h.get('continuityDialog').firstChild.onsubmit({preventDefault(){}});
const preview=(id,notice)=>({brief:{assessments:id?[{assessment_id:id,area:'Sweat',created_at:'2026-10-30T12:00:00Z'}]:[],counts:{assessments:id?1:0,checkins:0,routine_actions:0},photo_notice:notice}});

test('a delayed correction success refreshes records without closing a replacement dialog',async()=>{
  const h=harness();let release;
  h.api.dialog('First correction',h.content(),()=>new Promise(resolve=>release=resolve));
  const old=submit(h);h.get('continuityDialog').close();h.api.dialog('Second correction',h.content(),async()=>{});
  const replacement=h.get('continuityDialog').firstChild;release();await old;
  assert.equal(h.get('continuityDialog').open,true);assert.equal(h.get('continuityDialog').firstChild,replacement);assert.equal(h.get('continuityDialogTitle').textContent,'Second correction');
});
test('a delayed correction error cannot write into the next correction status',async()=>{
  const h=harness();let reject;
  h.api.dialog('First correction',h.content(),()=>new Promise((_,fail)=>reject=fail));const old=submit(h);
  h.get('continuityDialog').close();h.api.dialog('Next correction',h.content(),async()=>{});reject(Error('Old failure'));await old;
  assert.equal(h.get('continuityDialogStatus').textContent,'');assert.equal(h.get('continuityDialog').open,true);
});
test('a correction completed after Back cannot steal focus from the next input',async()=>{
  const h=harness();let release;h.api.dialog('Correction',h.content(),()=>new Promise(resolve=>release=resolve));const old=submit(h);
  h.get('continuityDialog').close();h.get('briefQuestions').focus();release();await old;assert.equal(h.document.activeElement,h.get('briefQuestions'));
});
test('review starts at its heading and cancellation returns to the explicit invoking control',()=>{
  const h=harness();h.api.dialog('Review',h.content(),async()=>{},'Save',h.trigger);h.frames.shift()();
  assert.equal(h.document.activeElement,h.get('continuityDialogTitle'));h.get('continuityDialog').close();assert.equal(h.document.activeElement,h.trigger);
});
test('deferred dialog focus cannot run after cancellation or account clearing',()=>{
  const h=harness();h.api.dialog('Review',h.content(),async()=>{});h.ui.clear();h.state.profile=null;h.frames.shift()();
  assert.notEqual(h.document.activeElement,h.get('continuityDialogTitle'));assert.equal(h.get('continuityDialog').open,false);
});
test('the latest clinician preview wins when responses arrive out of order',async()=>{
  const h=harness();const old=h.api.previewBrief();h.get('briefQuestions').value='Latest';h.api.invalidateBrief();const latest=h.api.previewBrief();
  h.pending[1].resolve(preview('new-result','Latest selection'));await latest;
  h.pending[0].resolve(preview('old-result','Old selection'));await old;
  assert.match(h.get('briefStatus').textContent,/Latest selection/);assert.doesNotMatch(h.get('briefStatus').textContent,/Old selection/);assert.equal(h.get('briefSelection').firstChild.firstChild.value,'new-result');assert.equal(h.get('downloadBrief').disabled,false);
});
test('editing the brief invalidates its selection and discards an in-flight response',async()=>{
  const h=harness();const old=h.api.previewBrief();h.get('briefStart').value='2026-10-15';h.api.invalidateBrief('Selection changed.');
  h.pending[0].resolve(preview('old-result','Obsolete'));await old;
  assert.equal(h.get('briefSelection').children.length,0);assert.equal(h.get('downloadBrief').disabled,true);assert.equal(h.get('briefStatus').textContent,'Selection changed.');
});
test('an older preview failure cannot overwrite a newer success or unlock its pending request',async()=>{
  const h=harness();const old=h.api.previewBrief();h.api.invalidateBrief();const latest=h.api.previewBrief();h.pending[0].reject(Error('Old failure'));await old;
  assert.equal(h.get('previewBrief').disabled,true);h.pending[1].resolve(preview(null,'Latest empty selection'));await latest;
  assert.match(h.get('briefStatus').textContent,/Latest empty selection/);assert.equal(h.get('previewBrief').disabled,false);
});
test('account clear removes private brief input and restores a usable default date range',()=>{
  const h=harness();h.get('briefQuestions').value='Private question';h.get('briefSelection').append(h.content());h.ui.clear();
  assert.equal(h.get('briefQuestions').value,'');assert.equal(h.get('briefStart').value,'2026-09-30');assert.equal(h.get('briefEnd').value,'2026-10-30');assert.equal(h.get('briefSelection').children.length,0);assert.equal(h.get('downloadBrief').disabled,true);
});
test('invalid brief fields are rejected before sending a request',async()=>{
  const h=harness();h.get('visitBriefForm').valid=false;await h.api.previewBrief();assert.equal(h.pending.length,0);
});
