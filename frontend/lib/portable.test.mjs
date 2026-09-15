import test from 'node:test';
import assert from 'node:assert/strict';
import {zipSync,strToU8} from 'fflate';
import {encodeProject,decodeProject,copyProject} from './portable.mjs';
const project=()=>({format:'pressure-room',format_version:2,project:{id:'p',title:'Story'},branches:[{id:'b',project_id:'p',name:'Main',is_main:1}],episodes:[{id:'e',project_id:'p',branch_id:'b',title:'Episode'}],scenes:[{id:'s',episode_id:'e',slugline:'INT. TEST',screenplay_text:''}],characters:[],bills:[],causal_links:[],story_notes:[],snapshots:[]});
test('portable backup round trip includes complete snapshot history',()=>{
 const p=project();p.snapshots=[{id:'snap',project_id:'p',label:'Before',payload:project()}];
 const restored=decodeProject(encodeProject(p));assert.equal(restored.snapshots[0].payload.scenes[0].screenplay_text,'');assert.equal(restored.project.title,'Story');
});
test('copy remaps all relationships, including historical project identity',()=>{
 const p=project();p.snapshots=[{id:'snap',project_id:'p',payload:project()}];let n=0;
 const copy=copyProject(p,()=>`new-${++n}`);assert.notEqual(copy.project.id,'p');assert.equal(copy.episodes[0].branch_id,copy.branches[0].id);assert.equal(copy.snapshots[0].payload.project.id,copy.project.id);
});
test('invalid references and duplicate IDs are rejected',()=>{
 const p=project();p.scenes[0].episode_id='missing';assert.throws(()=>encodeProject(p),/relationship/);
 const q=project();q.scenes[0].id='b';assert.throws(()=>encodeProject(q),/Duplicate/);
});
test('decompression limit checked before expanding compressed payload',()=>{
 const bytes=zipSync({'project.json':new Uint8Array(33*1024*1024)});assert.throws(()=>decodeProject(bytes),/oversized/);
});
test('prototype fields do not cross backup boundary',()=>{
 const p=project();p.project=JSON.parse('{"id":"p","title":"Story","__proto__":{"polluted":true}}');
 const data=decodeProject(encodeProject(p));assert.equal(Object.hasOwn(data.project,'__proto__'),false);assert.equal({}.polluted,undefined);
});
