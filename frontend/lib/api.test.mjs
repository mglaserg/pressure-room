import test from 'node:test';
import assert from 'node:assert/strict';
import {localApi,setStorageMode} from './api.js';

function browserStorage() {
  const values=new Map();
  return {
    getItem:key=>values.has(key)?values.get(key):null,
    setItem:(key,value)=>values.set(key,String(value)),
    removeItem:key=>values.delete(key),
  };
}

test('browser-local branch deletion protects Main and descendants',async()=>{
  const previous=globalThis.window;
  globalThis.window={localStorage:browserStorage(),crypto:globalThis.crypto};
  try{
    setStorageMode('local');
    const {id:projectId}=await localApi('/projects',{method:'POST',body:JSON.stringify({data:{title:'Local safety'}})});
    let workspace=await localApi(`/projects/${projectId}`);
    const main=workspace.branches[0];
    await assert.rejects(
      localApi(`/projects/${projectId}/branches/${main.id}`,{method:'DELETE',body:JSON.stringify({confirm_name:main.name})}),
      /Main cannot be deleted/,
    );
    const {id:parent}=await localApi(`/projects/${projectId}/branches/${main.id}/clone`,{method:'POST',body:JSON.stringify({name:'Parent'})});
    const {id:child}=await localApi(`/projects/${projectId}/branches/${parent}/clone`,{method:'POST',body:JSON.stringify({name:'Child'})});
    await localApi(`/projects/${projectId}/branches/${parent}/promote`,{method:'POST'});
    workspace=await localApi(`/projects/${projectId}`);
    assert.equal(workspace.branches.find(branch=>branch.is_main).id,parent);
    await localApi(`/projects/${projectId}/branches/${main.id}/promote`,{method:'POST'});
    await assert.rejects(
      localApi(`/projects/${projectId}/branches/${parent}`,{method:'DELETE',body:JSON.stringify({confirm_name:'Parent'})}),
      /descendants/,
    );
    await localApi(`/projects/${projectId}/branches/${child}`,{method:'DELETE',body:JSON.stringify({confirm_name:'Child'})});
    await localApi(`/projects/${projectId}/branches/${parent}`,{method:'DELETE',body:JSON.stringify({confirm_name:'Parent'})});
    workspace=await localApi(`/projects/${projectId}`);
    assert.deepEqual(workspace.branches.map(branch=>branch.id),[main.id]);
  }finally{
    if(previous===undefined)delete globalThis.window;else globalThis.window=previous;
  }
});
