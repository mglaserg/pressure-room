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
 await context.addInitScript(p=>{if(!localStorage.getItem('pressure-room-local-db')){localStorage.setItem('pressure-room-storage-mode','local');localStorage.setItem('pressure-room-local-db',JSON.stringify(p));}},fixture);
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:3137');await page.getByLabel('Scene screenplay',{exact:true}).waitFor();
 await page.screenshot({path:out+'/desktop.png',fullPage:true});
 await page.getByLabel('Scene screenplay',{exact:true}).fill('A fresh scene.\n\nMARA\nI will not leave.');
 await page.getByText('Saved in this browser',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Focus',exact:true}).click();
 assert.equal(await page.locator('.scene-rail').isVisible(),false);
 await page.screenshot({path:out+'/focus.png',fullPage:true});
 await page.getByRole('button',{name:'Exit focus',exact:true}).click();
 await page.getByRole('button',{name:'Room',exact:true}).click();
 await page.getByRole('dialog',{name:'Your room',exact:true}).waitFor();
 await page.screenshot({path:out+'/menu.png',fullPage:true});
 await page.keyboard.press('Escape');assert.equal(await page.getByRole('button',{name:'Room',exact:true}).evaluate(e=>e===document.activeElement),true);
 await page.getByRole('button',{name:'Room',exact:true}).click();await page.getByRole('button',{name:'Export & backup',exact:true}).click();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:/Full story backup/}).click();
 const d=await download;await d.saveAs(out+'/browser-backup.pressureroom');assert.ok(fs.statSync(out+'/browser-backup.pressureroom').size>100);
 await page.locator('input[type=file]').setInputFiles(out+'/browser-backup.pressureroom');
 await page.getByRole('dialog',{name:'Export & backup',exact:true}).waitFor({state:'hidden'});
 assert.equal(await page.locator('.context-select select').first().locator('option').count(),2);
 await page.reload();await page.getByLabel('Scene screenplay',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Scene screenplay',{exact:true}).inputValue(),'A fresh scene.\n\nMARA\nI will not leave.');

 // Simulate another tab changing this exact scene after the editor loaded it.
 const selectedEpisode=await page.locator('.context-select select').nth(1).inputValue();
 const selectedId=await page.evaluate(ep=>JSON.parse(localStorage.getItem('pressure-room-local-db')).scenes.filter(s=>s.episode_id===ep).sort((a,b)=>a.scene_no-b.scene_no)[0].id,selectedEpisode);
 await page.evaluate(id=>{const db=JSON.parse(localStorage.getItem('pressure-room-local-db'));const scene=db.scenes.find(s=>s.id===id);scene.screenplay_text='Another tab saved this';scene.version=(scene.version||1)+1;localStorage.setItem('pressure-room-local-db',JSON.stringify(db))},selectedId);
 await page.getByLabel('Scene screenplay',{exact:true}).fill('My conflicting draft');
 await page.getByText('Conflict · draft kept here',{exact:true}).waitFor();
 await page.getByLabel('Scene screenplay',{exact:true}).fill('More edits to my conflicting draft');
 await page.waitForTimeout(800);
 assert.equal(await page.evaluate(id=>JSON.parse(localStorage.getItem('pressure-room-local-db')).scenes.find(s=>s.id===id).screenplay_text,selectedId),'Another tab saved this');
 const recovery=page.waitForEvent('download');await page.getByRole('button',{name:'Download draft & load saved story',exact:true}).click();await recovery;
 await page.getByLabel('Scene screenplay',{exact:true}).waitFor();
 assert.equal(await page.getByLabel('Scene screenplay',{exact:true}).inputValue(),'Another tab saved this');
 await page.setViewportSize({width:390,height:844});assert.equal(await page.getByText('Saved in this browser',{exact:true}).isVisible(),true);await page.screenshot({path:out+'/mobile.png',fullPage:true});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile horizontal overflow');
 await page.getByRole('button',{name:'Room',exact:true}).click();await page.screenshot({path:out+'/mobile-menu.png',fullPage:true});
 assert.ok(await page.getByRole('dialog',{name:'Your room',exact:true}).evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0}),'dialog clipped');
 await page.keyboard.press('Escape');await page.getByRole('button',{name:/^Diagnose/}).click();await page.getByText('Your next revision',{exact:true}).waitFor();await page.screenshot({path:out+'/diagnose.png',fullPage:true});
 assert.equal(await page.getByRole('button',{name:'Explore the full diagnosis',exact:true}).isVisible(),true);
 assert.deepEqual(errors,[]);
 fs.writeFileSync(out+'/browser-results.json',JSON.stringify({passed:true,checks:['desktop editor','autosave persisted','focus mode','dialog Escape and focus return','browser ZIP export','copy import','reload preservation','390px layout without horizontal overflow','mobile dialog containment','progressive diagnosis','stale browser scene rejected','conflicting draft remains paused','draft download and load saved version'],pageErrors:errors},null,2));
 console.log('Browser checks passed');
 }finally{if(browser)await browser.close();for(const p of processes)p.kill();}})().catch(e=>{console.error(e);process.exitCode=1});
