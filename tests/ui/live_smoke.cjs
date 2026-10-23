/* Verify an already-cached successful answer in the owner's local app.
   No upload/delete/feedback mutations or new test questions are allowed. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {chromium} = require(path.resolve('tests/ui/node_modules/playwright'));

async function main() {
  const evidence = JSON.parse(await fs.readFile('docs/ui/evidence/local-live-smoke.json','utf8'));
  assert.equal(evidence.status,'PASS','Complete the HTTP live smoke before checking its cached UI response');
  const browser = await chromium.launch({executablePath:process.env.UI_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto('http://127.0.0.1:8000');
    await page.locator('#categories .category-button').first().waitFor();
    assert(!(await page.locator('#runtime-notice').isVisible()));
    await page.locator('#scope-open').click();
    await page.locator(`#scope-documents [data-select="${evidence.doc_id}"]`).check();
    await page.keyboard.press('Escape');
    await page.locator('#reply-language').selectOption('vi');
    const responsePromise = page.waitForResponse(response=>response.url().endsWith('/api/query'));
    await page.locator('#question').fill('Stack thực hiện thao tác push và pop theo nguyên tắc nào?');
    await page.locator('#send').click();
    const response = await responsePromise;
    const answer = await response.json();
    assert(answer.cache_hit,'Live UI verification must reuse the previously checked answer');
    assert(!answer.answer.abstained && answer.answer.citations.length);
    await page.locator('.source-card').first().waitFor();
    await page.screenshot({path:'docs/ui/evidence/local-live-view.png'});
    await page.locator('[data-source-preview]').first().click();
    await page.locator('#preview-body iframe').waitFor();
    const preview = await page.locator('#preview-body iframe').getAttribute('src');
    assert(preview.endsWith(`#page=${evidence.citations[0].preview_page}`));
    assert((await page.locator('#preview-page').textContent()).includes('Đã tìm thấy đoạn trích'));
    assert.deepEqual(errors,[]);
    await fs.writeFile('docs/ui/evidence/local-live-browser.json',JSON.stringify({status:'PASS',cached:true,
      aiConfigured:true,language:'vi',citationCount:answer.answer.citations.length,previewPage:evidence.citations[0].preview_page,
      sourceMatched:true,browserErrors:errors,scope:'Actual local application; no user document deleted'},null,2));
    console.log('PASS actual local UI: configured AI, Vietnamese cached answer, verified PDF page, no script errors');
  } finally {await browser.close();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
