const {spawn,spawnSync}=require('node:child_process');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PRESSURE_ROOM_PLAYWRIGHT_MODULE||'playwright');
const root=process.cwd(),out=root+'/qa';
fs.mkdirSync(out,{recursive:true});
const seeded=spawnSync(root+'/backend/.venv/bin/python',['-c',`import sys,json
from pathlib import Path
sys.path.insert(0,'backend')
from app import db
db.init_db()
p=db.project_payload(db.get_projects()[0]['id']);p['projects']=[p.pop('project')];p['snapshots']=[]
Path('qa/fixture.json').write_text(json.dumps(p))`],{cwd:root,env:{...process.env,PRESSURE_ROOM_DB:out+'/fixture.db'},encoding:'utf8'});
if(seeded.status!==0)throw Error(seeded.stderr);
const processes=[];
function start(cmd,args,cwd,env){const p=spawn(cmd,args,{cwd,env:{...process.env,...env},stdio:['ignore','pipe','pipe']});processes.push(p);p.stderr.on('data',d=>fs.appendFileSync(out+'/servers.log',d));return p;}
async function ready(url){for(let i=0;i<100;i++){try{if((await fetch(url)).ok)return}catch{}await new Promise(r=>setTimeout(r,200));}throw Error('Server unavailable: '+url)}
(async()=>{let browser;const errors=[];try{
 start(root+'/backend/.venv/bin/python',['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8137'],root+'/backend',{PRESSURE_ROOM_DB:out+'/qa-server.db'});
 start(process.execPath,['node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','3137'],root+'/frontend',{PRESSURE_ROOM_API_URL:'http://127.0.0.1:8137'});
 await Promise.all([ready('http://127.0.0.1:3137'),ready('http://127.0.0.1:8137/api/health')]);
 browser=await chromium.launch({executablePath:process.env.PRESSURE_ROOM_CHROMIUM,headless:true,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});

 const fixture=JSON.parse(fs.readFileSync(out+'/fixture.json','utf8'));
 fixture.branches.push({id:'empty-path',project_id:fixture.projects[0].id,name:'Empty path',is_main:0});
 await context.addInitScript(p=>{localStorage.setItem('pressure-room-storage-mode','local');localStorage.setItem('pressure-room-local-db',JSON.stringify(p));},fixture);
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:3137');await page.getByLabel('Scene screenplay',{exact:true}).waitFor();
 const originalEpisode=await page.getByLabel('Episode',{exact:true}).inputValue();
 await page.getByLabel('Scene screenplay',{exact:true}).fill('Draft preserved before adding an episode.');
 async function addExisting(){
   const picker=page.getByLabel('Episode',{exact:true});const before=await picker.inputValue();
   const count=await page.evaluate(()=>JSON.parse(localStorage.getItem('pressure-room-local-db')).episodes.length);
   await picker.selectOption('__new_episode__');
   await page.waitForFunction(old=>{const s=document.querySelector('select[aria-label="Episode"]');return s&&!s.disabled&&s.value!==old&&s.value!=='__new_episode__'},before);
   assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('pressure-room-local-db')).episodes.length),count+1);
   return picker.inputValue();
 }
 const second=await addExisting();
 const firstCheck=await page.evaluate(id=>{const db=JSON.parse(localStorage.getItem('pressure-room-local-db'));return {scene:db.scenes.find(s=>s.episode_id===id),episodes:db.episodes}},originalEpisode);
 assert.equal(firstCheck.scene.screenplay_text,'Draft preserved before adding an episode.');
 const added=firstCheck.episodes.find(e=>e.id===second);assert.equal(added.branch_id,fixture.branches[0].id);
 assert.equal(added.number,Math.max(...fixture.episodes.map(e=>e.number))+1);
 await page.setViewportSize({width:390,height:844});await addExisting();
 await page.getByRole('button',{name:'Room',exact:true}).click();await page.getByRole('dialog',{name:'Your room',exact:true}).locator('select').first().selectOption('empty-path');await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'+ Episode',exact:true}).click();await page.getByLabel('Episode',{exact:true}).waitFor();
 const emptyFirst=await page.getByLabel('Episode',{exact:true}).inputValue();
 assert.equal(await page.evaluate(id=>JSON.parse(localStorage.getItem('pressure-room-local-db')).episodes.find(e=>e.id===id).branch_id,emptyFirst),'empty-path');
 await addExisting();
 assert.deepEqual(errors,[]);
 fs.writeFileSync(out+'/episode-results.json',JSON.stringify({passed:true,checks:['add episode to existing story on desktop','pending draft saved before creation','correct branch and next episode number','new episode selected','add episode on mobile','first episode on empty path','second episode on previously empty path'],pageErrors:errors},null,2));
 console.log('Episode regression checks passed');
 }finally{if(browser)await browser.close();for(const p of processes)p.kill();}})().catch(e=>{console.error(e);process.exitCode=1});
