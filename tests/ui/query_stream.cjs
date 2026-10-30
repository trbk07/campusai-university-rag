/* Unit contracts for the actual browser transport; no network/provider calls. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.resolve(__dirname,'../../src/campusai/ui/scripts/api.js'),'utf8');
const api = import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const encoder = new TextEncoder();
const record = value => JSON.stringify(value)+'\n';

test('local AI contention is distinct from exhausted provider quota',async()=>{
  const {errorText}=await api;
  const text=errorText({code:'provider_busy'});
  assert.match(text,/đang được xử lý/);
  assert.doesNotMatch(text,/429|hạn mức|quota/);
  assert.match(errorText({code:'provider_rate_limited'}),/429/);
});
test('configured browser deadline is passed to JSON and streaming without automatic resend',async t=>{
  const calls=[];
  const nativeSet=global.setTimeout, nativeClear=global.clearTimeout;
  global.setTimeout=(_fn,ms)=>{calls.push(ms);return 1;};global.clearTimeout=()=>{};
  t.after(()=>{global.setTimeout=nativeSet;global.clearTimeout=nativeClear;});
  mockFetch(t,async()=>new Response(JSON.stringify(answer),{headers:{'Content-Type':'application/json'}}));
  await (await api).post('/api/query',{question:'q'},195000);
  await (await api).postQuery({question:'q'},null,195000);
  assert.deepEqual(calls,[195000,195000]);
});
const answer = {ok:true, answer:{answer:'Nội dung đã kiểm chứng 🌿',citations:[],abstained:false}};
function response(text, {status=200,fragment=3,type='application/x-ndjson'}={}) {
  const bytes=encoder.encode(text);
  return new Response(new ReadableStream({start(controller) {
    for(let i=0;i<bytes.length;i+=fragment) controller.enqueue(bytes.slice(i,i+fragment));
    controller.close();
  }}),{status,headers:{'Content-Type':type,'X-Request-ID':'request-fixture'}});
}
function mockFetch(t, fn) {
  const original=global.fetch;
  global.fetch=fn;
  t.after(()=>{global.fetch=original;});
}

test('fragmented UTF-8 progress never becomes an unverified answer',async t=>{
  const events=[];let posts=0;
  mockFetch(t,async(path,options)=>{
    posts++;assert.equal(path,'/api/query');assert.equal(options.headers.Accept,'application/x-ndjson');
    assert.deepEqual(JSON.parse(options.body),{question:'Môn nào?',history:[]});
    return response(record({type:'progress',phase:'generating'})+
      record({type:'progress',phase:'verifying'})+record({type:'result',status:200,value:answer}));
  });
  const result=await (await api).postQuery({question:'Môn nào?',history:[]},phase=>events.push(phase));
  assert.deepEqual(events,['generating','verifying']);assert.equal(posts,1);
  assert.equal(result.answer.answer,answer.answer.answer);assert.equal(result.responseId,'request-fixture');
});

test('a provider error after progress retains retry metadata without retrying',async t=>{
  let posts=0;
  mockFetch(t,async()=>{posts++;return response(record({type:'progress',phase:'generating'})+
    record({type:'result',status:503,value:{ok:false,error_code:'provider_overloaded',retry_after_seconds:60}}));});
  await assert.rejects((await api).postQuery({question:'q'}),error=>error.code==='provider_overloaded'&&error.retryAfterSeconds===60);
  assert.equal(posts,1);
});

test('cached/local JSON and early HTTP errors retain the existing API contract',async t=>{
  const module=await api;let posts=0;
  mockFetch(t,async()=>{posts++;return response(JSON.stringify(answer),{type:'application/json'});});
  assert.equal((await module.postQuery({question:'q'},()=>assert.fail('cache is not streaming'))).answer.answer,answer.answer.answer);
  global.fetch=async()=>{posts++;return response(JSON.stringify({ok:false,error_code:'query_busy',retry_after_seconds:2}),{type:'application/json',status:429});};
  await assert.rejects(module.postQuery({question:'q'}),error=>error.code==='query_busy'&&error.retryAfterSeconds===2);
  assert.equal(posts,2);
});

for(const text of [record({type:'delta',text:'unverified'}),record({type:'progress',phase:'unknown'}),
  '{not-json}\n',record({type:'progress',phase:'generating'}),
  JSON.stringify({type:'result',status:200,value:answer})]) {
  test('malformed or truncated progress never returns an answer: '+text.slice(0,45),async t=>{
    let posts=0;mockFetch(t,async()=>{posts++;return response(text);});
    await assert.rejects((await api).postQuery({question:'q'}));assert.equal(posts,1);
  });
}

test('oversized response is rejected and its reader cancelled',async t=>{
  let cancelled=false;
  mockFetch(t,async()=>new Response(new ReadableStream({start(controller){
    controller.enqueue(new Uint8Array(4*1024*1024+1));
  },cancel(){cancelled=true;}}),{headers:{'Content-Type':'application/x-ndjson'}}));
  await assert.rejects((await api).postQuery({question:'q'}));assert.equal(cancelled,true);
});
