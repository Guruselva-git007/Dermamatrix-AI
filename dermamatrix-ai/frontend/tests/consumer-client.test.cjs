const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../consumer.js'),'utf8');
function harness(fetch,hash=''){
 const replacements=[],events=[],listeners={};const context={window:{addEventListener(name,handler){listeners[name]=handler;},dispatchEvent(event){events.push(event);}},CustomEvent:class{constructor(type,options){this.type=type;this.detail=options?.detail;}},location:{hash,pathname:'/',search:''},history:{replaceState:(_state,_title,url)=>replacements.push(url)},URLSearchParams,AbortController,setTimeout,clearTimeout,document:{readyState:'loading',addEventListener(name,handler){listeners['document:'+name]=handler;}},fetch,console};
 vm.createContext(context);vm.runInContext(source,context);return{client:context.window.ConsumerClient,replacements,events,listeners};
}
const response=(token,status=200)=>({status,ok:status===200,headers:{get:name=>name==='X-CSRF-Token'?token:null},json:async()=>({csrf_token:token})});
test('parallel readers share security bootstrap; unsafe requests refresh the current token',async()=>{
 let calls=0;let release;const pending=new Promise(resolve=>release=resolve);
 const {client}=harness(async()=>{calls++;if(calls===1)await pending;return response('session-token');});
 const readers=[client.prepare({}),client.prepare({}),client.prepare({})];release();await Promise.all(readers);assert.equal(calls,1);
 const options=await client.prepare({method:'POST',headers:{'Idempotency-Key':'original-key'},body:'actual input'});
 assert.equal(calls,2);assert.equal(options.headers['X-CSRF-Token'],'session-token');assert.equal(options.headers['Idempotency-Key'],'original-key');assert.equal(options.body,'actual input');
});
test('fresh token from another session cannot silently rebind an old draft; locked reads do not retry',async()=>{
 let token='account-A',calls=0;const {client,events}=harness(async()=>{calls++;return response(token);});
 const read=await client.prepare({});assert.equal(read.headers['X-CSRF-Token'],'account-A');token='account-B';
 await assert.rejects(client.prepare({method:'POST',body:'private A draft'}),/session changed/);
 assert.equal(events.length,1);const attempts=calls;await assert.rejects(client.prepare({}),/session changed/);assert.equal(calls,attempts);
 const login=await client.prepare({method:'POST'},'/api/auth/login');client.observe(response('new-login'),login,'/api/auth/login');
 assert.equal((await client.prepare({})).headers['X-CSRF-Token'],'new-login');
});
test('cookie change after preparation rejects a private response; an older response cannot invalidate a newer login',async()=>{
 const {client,events}=harness(async()=>response('A'));const old=await client.prepare({});
 assert.throws(()=>client.observe(response('B',409),old),/session changed/);assert.equal(events.length,1);
 const login=await client.prepare({method:'POST'},'/api/auth/login');client.observe(response('C'),login,'/api/auth/login');
 assert.throws(()=>client.observe(response('A'),old),/earlier account/);assert.equal(events.length,1);
 assert.equal((await client.prepare({})).headers['X-CSRF-Token'],'C');
});
test('foreground revalidation detects revoked sessions without polling',async()=>{
 let calls=0;const h=harness(async path=>{calls++;return path==='/api/auth/me'?response('',401):response('A');});await h.client.prepare({});
 h.listeners.focus();await new Promise(resolve=>setImmediate(resolve));assert.equal(calls,3);assert.equal(h.events.length,1);
 h.listeners.focus();await new Promise(resolve=>setImmediate(resolve));assert.equal(calls,3);
});
test('temporary verification failure locks requests without destroying drafts and a verified retry resumes the session',async()=>{
 let offline=true;const h=harness(async path=>{if(path==='/api/auth/me'&&offline)throw Error('offline');return response('A');});await h.client.prepare({});
 await h.client.revalidate();assert.equal(h.events[0].type,'dermamatrix-session-uncertain');
 await assert.rejects(h.client.prepare({method:'POST',body:'unsaved'}),/remains in this tab/);
 offline=false;await h.client.revalidate();assert.equal(h.events[1].type,'dermamatrix-session-resumed');
 assert.equal((await h.client.prepare({})).headers['X-CSRF-Token'],'A');
});
test('a verified guest remains a guest when returning to the tab',async()=>{
 const h=harness(async path=>response('guest-token',path==='/api/auth/me'?401:200));await h.client.prepare({});await h.client.revalidate();assert.equal(h.events.length,0);
});
test('cancelling security preparation aborts its request without changing the pinned account',async()=>{
 let waiting=false;const h=harness(async(_path,options)=>waiting?new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(Object.assign(Error('cancelled'),{name:'AbortError'})))):response('A'));
 await h.client.prepare({});waiting=true;const controller=new AbortController();const pending=h.client.prepare({method:'POST',signal:controller.signal});controller.abort();
 await assert.rejects(pending,/cancelled/);assert.equal(h.events.length,0);assert.equal((await h.client.prepare({})).headers['X-CSRF-Token'],'A');
});
test('disabled consumer service preserves legacy client without fake enablement',async()=>{
 let calls=0;const {client}=harness(async()=>{calls++;return response('',503);});
 const options=await client.prepare({method:'POST'});assert.equal(client.enabled,false);assert.equal(options.headers,undefined);await client.prepare({});assert.equal(calls,1);
});
test('transient bootstrap failure remains retryable',async()=>{
 let calls=0;const {client}=harness(async()=>response('valid',++calls===1?500:200));
 await assert.rejects(client.prepare({}));await client.prepare({});assert.equal(client.enabled,true);
});
test('account tokens are removed from the address before any request or storage',()=>{
 let calls=0;const {replacements}=harness(async()=>{calls++;return response('x');},'#account_action=reset_password&token=synthetic-token');
 assert.equal(calls,0);assert.equal(replacements.length,1);assert.equal(replacements[0],'/#settings');
});
