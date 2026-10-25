/* Read-only lab Web Vitals on the actual app; no query or document mutation. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const {chromium} = require(path.resolve('tests/ui/node_modules/playwright'));

async function main() {
  const output = process.env.UI_VITALS_OUTPUT || '.tmp/qa-web-vitals-20261025.json';
  await assert.rejects(fs.access(output), 'Preserve prior measurements');
  const bundle = await fs.readFile('tests/ui/node_modules/web-vitals/dist/web-vitals.iife.js','utf8');
  const browser = await chromium.launch({executablePath:process.env.UI_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const report = {scope:'Actual local app, Chrome lab sessions with viewport/touch emulation; not field or physical-mobile data',
    browser:browser.version(),library:'web-vitals6.2.3',librarySha256:crypto.createHash('sha256').update(bundle).digest('hex'),
    providerCalls:0,mutationsAllowed:false,documentMetadataDelayMs:200,status:'INCOMPLETE',sessions:[]};
  try {
    const viewports=process.env.UI_VITALS_WIDTH ? [{width:Number(process.env.UI_VITALS_WIDTH),height:900}]
      : [{width:1440,height:900},{width:768,height:1024},{width:390,height:844}];
    const runs=Number(process.env.UI_VITALS_RUNS || 3);
    for (const viewport of viewports) {
      for (let run=1;run<=runs;run++) {
        const touch = viewport.width<1280;
        const context = await browser.newContext({viewport,hasTouch:touch,isMobile:touch});
        const blocked = [], errors = [];
        await context.route('**/*',async route => {
          const request = route.request();
          if (request.method()!=='GET' || !request.url().startsWith('http://127.0.0.1:8000/')) {
            blocked.push({method:request.method(),url:request.url()}); return route.abort();
          }
          if (request.url()==='http://127.0.0.1:8000/api/documents')
            await new Promise(resolve=>setTimeout(resolve,report.documentMetadataDelayMs));
          return route.continue();
        });
        await context.addInitScript({content:bundle+`\nwindow.__vitals={};window.__trustedInteractions=0;window.__shifts=[];
          const collect=m=>window.__vitals[m.name]={value:m.value,rating:m.rating,navigationType:m.navigationType};
          webVitals.onLCP(collect,{reportAllChanges:true});
          webVitals.onCLS(collect,{reportAllChanges:true});
          webVitals.onINP(collect,{reportAllChanges:true,durationThreshold:16});
          new PerformanceObserver(list=>{for(const e of list.getEntries())if(!e.hadRecentInput)window.__shifts.push({value:e.value,
            sources:e.sources.map(s=>({id:s.node?.id,tag:s.node?.tagName,className:s.node?.className,
              previous:{x:s.previousRect.x,y:s.previousRect.y,width:s.previousRect.width,height:s.previousRect.height},
              current:{x:s.currentRect.x,y:s.currentRect.y,width:s.currentRect.width,height:s.currentRect.height}}))})})
            .observe({type:'layout-shift',buffered:true});
          for(const name of ['pointerdown','keydown'])addEventListener(name,e=>{if(e.isTrusted)window.__trustedInteractions++},true);`});
        const page = await context.newPage();
        page.on('pageerror',error=>errors.push(error.message));
        try {
          await page.goto('http://127.0.0.1:8000/',{waitUntil:'networkidle'});
          await page.locator('#categories .category-button').first().waitFor({state:'attached'});
          await page.evaluate(()=>document.fonts.ready);
          if (viewport.width<768) {
            for (let i=0;i<3;i++) {
              await page.locator('#menu-toggle').tap();
              await page.keyboard.press('Escape');
              await page.locator('#scope-open').tap();
              await page.keyboard.press('Escape');
            }
          } else {
            for (const tab of ['documents','collections','guide','assistant'])
              await page.locator(`.nav-item[href="#${tab}"]`).click();
            await page.locator('#scope-open').click();
            await page.keyboard.press('Escape');
          }
          await page.locator('#question').click();
          await page.keyboard.type('Local UI performance probe',{delay:35});
          await page.locator('#question').fill('');
          await page.waitForFunction(()=>['LCP','INP','CLS'].every(name=>Number.isFinite(window.__vitals[name]?.value)),{timeout:5000});
          const data = await page.evaluate(()=>({metrics:window.__vitals,trustedInteractions:window.__trustedInteractions,
            horizontalOverflow:document.documentElement.scrollWidth>innerWidth,layoutShifts:window.__shifts}));
          assert(data.trustedInteractions>0,'INP requires actual trusted browser input');
          assert(!data.horizontalOverflow,'Unexpected horizontal overflow');
          assert.deepEqual(errors,[]);assert.deepEqual(blocked,[]);
          const row={viewport,run,...data};
          row.passed=data.metrics.LCP.value<=2500 && data.metrics.INP.value<=200 && data.metrics.CLS.value<=.1;
          report.sessions.push(row);
          console.log(JSON.stringify({viewport,run,LCP:data.metrics.LCP.value,INP:data.metrics.INP.value,CLS:data.metrics.CLS.value,passed:row.passed}));
        } finally {await context.close();}
      }
    }
    report.status=report.sessions.length===viewports.length*runs && report.sessions.every(row=>row.passed)?'PASS':'FAIL';
  } finally {
    await browser.close();
    await fs.writeFile(output,JSON.stringify(report,null,2));
  }
  assert.equal(report.status,'PASS');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
