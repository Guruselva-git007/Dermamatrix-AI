const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../consumer.js'),'utf8');
function harness(fetch,hash=''){
 const replacements=[];const context={window:{addEventListener(){}},location:{hash,pathname:'/',search:''},history:{replaceState:(_state,_title,url)=>replacements.push(url)},URLSearchParams,document:{readyState:'loading',addEventListener(){}},fetch,console};
 vm.createContext(context);vm.runInContext(source,context);return{client:context.window.ConsumerClient,replacements};
}
const response=(token,status=200)=>({status,ok:status===200,json:async()=>({csrf_token:token})});
test('parallel readers share security bootstrap; unsafe requests refresh the current token',async()=>{
 let calls=0;let release;const pending=new Promise(resolve=>release=resolve);
 const {client}=harness(async()=>{calls++;if(calls===1)await pending;return response('token-'+calls);});
 const readers=[client.prepare({}),client.prepare({}),client.prepare({})];release();await Promise.all(readers);assert.equal(calls,1);
 const options=await client.prepare({method:'POST',headers:{'Idempotency-Key':'original-key'},body:'actual input'});
 assert.equal(calls,2);assert.equal(options.headers['X-CSRF-Token'],'token-2');assert.equal(options.headers['Idempotency-Key'],'original-key');assert.equal(options.body,'actual input');
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
