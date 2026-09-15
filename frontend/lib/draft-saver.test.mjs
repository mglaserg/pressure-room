import test from 'node:test';
import assert from 'node:assert/strict';
import {createDraftSaver} from './draft-saver.mjs';

function storage() {
  const data = new Map();
  return {getItem:k=>data.get(k)??null, setItem:(k,v)=>data.set(k,v), removeItem:k=>data.delete(k)};
}

test('navigation flush saves every field, including an intentionally empty screenplay', async () => {
  const store=storage(), sent=[];
  const saver=createDraftSaver({key:'scene1',storage:store,send:async p=>sent.push(p)});
  saver.update({screenplay_text:'',scene_want:'Escape',slugline:'EXT. ROAD'});
  assert.equal(saver.recover().screenplay_text,'');
  await saver.flush();
  assert.deepEqual(sent,[{screenplay_text:'',scene_want:'Escape',slugline:'EXT. ROAD'}]);
  assert.equal(store.getItem('scene1'),null);
});

test('in-flight save does not erase newer recovery data and sends remain ordered', async () => {
  const store=storage(), sent=[]; let release;
  const gate=new Promise(resolve=>release=resolve);
  const saver=createDraftSaver({key:'scene2',storage:store,send:async p=>{sent.push(p.text);if(p.text==='old')await gate;}});
  saver.update({text:'old'}); const first=saver.flush();
  await Promise.resolve();
  saver.update({text:'new'});
  release(); await first;
  assert.deepEqual(saver.recover(),{text:'new'});
  await saver.flush();
  assert.deepEqual(sent,['old','new']);
});

test('failed saves retain recovery data and can be retried', async () => {
  const store=storage(), states=[];let fail=true;
  const saver=createDraftSaver({key:'scene3',storage:store,onState:s=>states.push(s),send:async()=>{if(fail)throw Error('offline')}});
  saver.update({notes:'important'});await saver.flush();
  assert.equal(states.at(-1),'offline');assert.equal(saver.recover().notes,'important');
  fail=false;await saver.flush();assert.equal(states.at(-1),'saved');assert.equal(saver.recover(),null);
});

test('unavailable browser storage is reported, but remote save is still attempted', async () => {
  let sent=false;const states=[];
  const saver=createDraftSaver({key:'scene4',storage:{getItem:()=>null,setItem:()=>{throw Error('quota')},removeItem:()=>{}},send:async()=>{sent=true},onState:s=>states.push(s)});
  saver.update({notes:'x'});assert.equal(states.at(-1),'uncached');await saver.flush();assert.ok(sent);assert.equal(states.at(-1),'saved');
});
<<<<<<< HEAD


test('conflicting recovery stays cached and never auto-overwrites saved text', async()=>{
  let sends=0;const saver=createDraftSaver({key:'blocked',storage:storage(),send:async()=>{sends++}});
  saver.pause();saver.update({text:'recovered'});await saver.flush();
  saver.update({text:'still editing'});await saver.flush();
  assert.equal(sends,0);assert.equal(saver.recover().text,'still editing');assert.ok(saver.isPending());
  saver.discard();await saver.release();
});

test('a stale revision pauses later writes until recovery is explicitly discarded',async()=>{
  let sends=0;const saver=createDraftSaver({key:'stale',storage:storage(),send:async()=>{sends++;throw Object.assign(Error('stale'),{status:409})}});
  saver.update({text:'first'});await saver.flush();saver.update({text:'second'});await saver.flush();
  assert.equal(sends,1);assert.equal(saver.recover().text,'second');saver.discard();await saver.release();
});
=======
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
