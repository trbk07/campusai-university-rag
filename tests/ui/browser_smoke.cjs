/* Run against tests/ui/serve_fixture.py. All network mocks below are test-only. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const moduleRoot = process.env.UI_NODE_MODULES || path.resolve('tests/ui/node_modules');
const {chromium} = require(path.join(moduleRoot, 'playwright'));
const {default:AxeBuilder} = require(path.join(moduleRoot, '@axe-core/playwright'));
const baseUrl = (process.env.UI_BASE_URL || 'http://127.0.0.1:8012').replace(/\/$/, '');

async function main() {
  const output = path.resolve(process.env.UI_EVIDENCE_DIR || 'docs/ui/evidence');
  await fs.mkdir(output,{recursive:true});
  const browser = await chromium.launch({executablePath:process.env.UI_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless:true});
  const context = await browser.newContext({viewport:{width:1440,height:900}, reducedMotion:'reduce'});
  const page = await context.newPage();
  const errors = [], checks = [], viewports = [];
  page.on('pageerror',error => errors.push(error.message));
  const check = (name, details={}) => { checks.push({name,passed:true,...details}); console.log('PASS '+name); };
  const audit = async name => {
    const result = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
    assert.equal(result.violations.length,0,JSON.stringify(result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))));
    check(`axe ${name}`);
  };
  try {
    const existing = await (await context.request.get(`${baseUrl}/api/documents`)).json();
    const fixtureNames = new Set(['Enrollment.pdf',...Array.from({length:9},(_,i)=>`Enrollment-${i+2}.pdf`),'mixed.pdf']);
    for (const doc of existing.documents) {
      assert(fixtureNames.has(doc.name),`Refusing to clean non-fixture document ${doc.name}`);
      assert.equal((await context.request.delete(`${baseUrl}/api/documents/${doc.doc_id}`)).status(),200);
    }
    await page.goto(baseUrl);
    await page.getByText('Bạn chưa có tài liệu nào.',{exact:true}).count();
    await page.locator('#categories .category-button').first().waitFor();
    assert(await page.locator('#send').isDisabled()); check('empty composer cannot submit');
    for (const [width,height] of [[1440,900],[1280,800],[1024,768],[768,1024],[390,844],[360,800]]) {
      await page.setViewportSize({width,height});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      const composer = await page.locator('#query-form').boundingBox();
      assert(composer.x >= 0 && composer.x+composer.width <= width+1 && composer.y+composer.height <= height);
      await page.screenshot({path:path.join(output,`welcome-${width}x${height}.png`)});
      const accessibility = await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
      assert.equal(accessibility.violations.length,0,JSON.stringify(accessibility.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),null,2));
      viewports.push({width,height,overflow:false,composerVisible:true,axeViolations:0});
      check(`responsive and axe ${width}x${height}`);
    }
    // Mobile drawer traps focus, closes with Escape, and restores focus.
    await page.locator('#menu-toggle').click();
    assert(await page.locator('#sidebar').isVisible());
    await page.keyboard.press('Shift+Tab');
    assert(await page.evaluate(() => !!document.activeElement.closest('#sidebar')));
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'),'false');
    check('mobile drawer keyboard focus and Escape');
    await page.setViewportSize({width:1440,height:900});
    for (const tab of ['documents','collections','guide','assistant']) {
      await page.locator(`.nav-item[href="#${tab}"]`).click();
      await page.locator(`#view-${tab}`).waitFor({state:'visible'});
    }
    check('all four navigation routes');
    await page.locator('.upload-main').click();
    await audit('upload dialog');
    const fixtureDir = path.resolve(process.env.UI_FIXTURE_DIR || '.tmp/ui-browser');
    const fixtureFiles = ['Enrollment.pdf','Enrollment-2.pdf','Enrollment-3.pdf','Enrollment-4.pdf','Enrollment-5.pdf'].map(name => path.join(fixtureDir,name));
    await page.locator('#file-input').setInputFiles([...fixtureFiles,fixtureFiles[0]]);
    assert(await page.locator('#upload-status').textContent().then(text => text.includes('tối đa 5')));
    assert(await page.locator('#upload-submit').isDisabled());
    await page.locator('#file-input').setInputFiles(fixtureFiles);
    assert.equal(await page.locator('#upload-selection .upload-file-card').count(),5);
    await page.locator('#upload-submit').click();
    await page.waitForFunction(() => {
      const documents = [...document.querySelectorAll('#document-list .document-card')];
      return documents.length === 5 && documents.every(card => card.textContent.includes('Sẵn sàng'));
    }, undefined, {timeout:30000});
    const listing = await page.evaluate(async () => await (await fetch('/api/documents', {cache:'no-store'})).json());
    const uploaded = listing.documents.find(document => document.name === 'Enrollment.pdf');
    assert(uploaded, `Expected Enrollment.pdf in document listing: ${JSON.stringify(listing.documents.map(document => ({name:document.name,ready:document.ready})))}`);
    const docId = uploaded.doc_id;
    assert(listing.documents.length === 5 && listing.documents.every(document => document.ready));
    check('five real PDFs upload concurrently and become ready');
    await page.locator('#document-search').fill('not-a-document');
    assert(await page.getByText('Không tìm thấy tài liệu phù hợp',{exact:true}).isVisible());
    await page.locator('#clear-filters').click();
    await page.locator(`#document-list input[data-select="${docId}"]`).check();
    await audit('document library');
    await page.locator('#ask-selected').click();
    await page.locator('#scope-open').click();
    await audit('scope dialog');
    const scopeCheckbox = page.locator(`#scope-documents input[data-select="${docId}"]`);
    await scopeCheckbox.uncheck(); assert(await page.locator('#send').isDisabled());
    await scopeCheckbox.check();
    assert(await page.evaluate(() => document.activeElement.matches('#scope-documents input')));
    await page.keyboard.press('Escape'); check('search filter selection and scope keyboard');
    await page.locator('#question').fill('alo'); await page.locator('#send').click();
    await page.getByText('Chào bạn! Bạn muốn tìm hiểu phần nào trong tài liệu đã chọn?',{exact:true}).waitFor();
    assert.equal(await page.locator('.citation-marker').count(),0);
    check('natural greeting answers locally without fake citations');
    // Adding another batch keeps the current conversation and all first-batch PDFs.
    await page.locator('.upload-main').click();
    assert((await page.locator('#upload-limits').textContent()).includes('mỗi lượt'));
    await page.locator('#file-input').setInputFiles(Array.from({length:5},(_,i)=>path.join(fixtureDir,`Enrollment-${i+6}.pdf`)));
    await page.locator('#upload-submit').click();
    await page.waitForFunction(() => {
      const cards = [...document.querySelectorAll('#document-list .document-card')];
      return cards.length === 10 && cards.every(card => card.textContent.includes('Sẵn sàng'));
    }, undefined, {timeout:30000});
    listing.documents = (await (await context.request.get(`${baseUrl}/api/documents`)).json()).documents;
    await page.locator('#ask-selected').click();
    // The click updates the hash; the view becomes visible in hashchange.
    // Check preserved conversation after that transition, not mid-navigation.
    await page.locator('#view-assistant').waitFor({state:'visible'});
    assert(await page.getByText('Chào bạn! Bạn muốn tìm hiểu phần nào trong tài liệu đã chọn?',{exact:true}).isVisible());
    await page.locator('#scope-open').click();
    for (const checkbox of await page.locator('#scope-documents input[data-select]').all()) await checkbox.check();
    assert.equal(await page.locator('#scope-documents input:checked').count(),10);
    await page.keyboard.press('Escape');
    const multiQuery = page.waitForRequest('**/api/query');
    await page.locator('#question').fill('Tổng số trang của tất cả tài liệu đã chọn?');
    await page.locator('#send').click();
    assert.equal((await multiQuery).postDataJSON().doc_ids.length,10);
    await page.waitForFunction(() => document.querySelector('.answer-body:last-child')?.textContent.includes('Tổng cộng: 10 trang.')
      || [...document.querySelectorAll('.answer-body')].some(body=>body.textContent.includes('Tổng cộng: 10 trang.')));
    await page.locator('#scope-open').click();
    for (const checkbox of await page.locator(`#scope-documents input:not([data-select="${docId}"])`).all()) await checkbox.uncheck();
    await page.keyboard.press('Escape');
    check('second batch of five preserves chat and all ten PDFs can be queried together');
    await page.locator('#question').fill('tài liệu có mấy trang'); await page.locator('#send').click();
    await page.locator('.document-info-card').waitFor();
    assert.equal((await page.locator('.answer-body').last().textContent()).trim(),'Enrollment.pdf: 1 trang.');
    assert.equal(await page.locator('.source-card').count(),0);
    await page.locator('[data-info-preview]').click();
    assert((await page.locator('#preview-body iframe').getAttribute('src')).endsWith(`/api/documents/${docId}/file#page=1`));
    await page.keyboard.press('Escape');
    check('page count answers the current turn from PDF metadata and opens original PDF');
    await page.locator('#new-chat').click();
    await page.locator('#reply-language').selectOption('en');
    await page.locator('#question').fill('What approval is required for enrollment?');
    let submits = 0;
    page.on('request',r => { if (r.url().endsWith('/api/query')) submits++; });
    const queryRequest = page.waitForRequest('**/api/query');
    await page.locator('#send').dblclick();
    assert.equal((await queryRequest).postDataJSON().language,'en'); check('answer language is sent to the actual API');
    if (process.env.UI_STREAM_PROBE === '1') {
      await page.getByText('AI đang tạo câu trả lời. Nội dung sẽ hiển thị sau khi kiểm chứng nguồn.',{exact:true}).waitFor();
      assert.equal(await page.locator('.answer-body').count(),0);
      assert.equal(await page.locator('.citation-marker').count(),0);
      assert(await page.locator('#send').isDisabled());
      check('controlled streaming progress exposes no unverified answer or citation');
    }
    await page.locator('.answer-body').waitFor({timeout:10000});
    assert.equal(submits,1); assert(await page.locator('.citation-marker').count());
    const quote = await page.locator('.source-card blockquote').first().textContent();
    assert.equal(quote,'Enrollment requires approval from the academic advisor.');
    await page.screenshot({path:path.join(output,'answer-1440x900.png')});
    await audit('grounded answer and source panel');
    check('real grounded answer citation and single submit');
    await page.locator('.citation-marker').first().click();
    await page.locator('[data-source-preview]').first().click();
    assert((await page.locator('#preview-body iframe').getAttribute('src')).endsWith(`/api/documents/${docId}/file#page=1`));
    assert.equal((await context.request.get(`${baseUrl}/api/documents/${docId}/file`)).status(),200);
    await page.keyboard.press('Escape'); check('citation opens exact physical PDF page');
    await page.locator('[data-feedback="helpful"]').first().click();
    await page.locator('[data-feedback="helpful"][aria-pressed="true"]').waitFor();
    check('feedback persisted through actual API');
    await page.setViewportSize({width:390,height:844});
    await page.locator('.citation-marker').first().click();
    assert(await page.locator('#sources').isVisible());
    await page.keyboard.press('Escape');
    await page.screenshot({path:path.join(output,'answer-390x844.png')});
    check('mobile citation drawer and focus return');
    await page.setViewportSize({width:1440,height:900});
    const excerptQuestion = 'Show enrollment source while Gemini is unavailable';
    const excerptQuote = 'Enrollment requires approval from the academic advisor.';
    const fallbackValue = {ok:true,answer:{answer:'AI temporarily unavailable.',abstained:true,
      abstention_reason:'provider_abstention',citations:[],claims:[]},
      provider_status:{error_code:'provider_overloaded',retry_after_seconds:60},
      fallback:{kind:'source_excerpts',citations:[{chunk_id:'fixture',doc_id:docId,page:1,
        page_range:[1,1],source_name:'Enrollment.pdf',quote:excerptQuote}]}};
    const excerptHistories = [];
    await page.route('**/api/query',route => {
      excerptHistories.push(route.request().postDataJSON().history);
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fallbackValue)});
    });
    await page.locator('#question').fill(excerptQuestion); await page.locator('#send').click();
    await page.getByText('AI tạm thời không thể tổng hợp câu trả lời. Dưới đây là trích đoạn nguyên văn được tìm thấy trong tài liệu. Bạn vẫn có thể tiếp tục tra cứu và mở PDF để đối chiếu.',{exact:true}).last().waitFor();
    assert.equal(await page.locator('.source-card blockquote').first().textContent(),excerptQuote);
    await page.locator('#question').fill('Another source lookup during cooldown');
    assert(await page.locator('#send').isEnabled());
    await page.locator('#send').click();
    await page.locator('#query-form[aria-busy="false"]').waitFor();
    assert.equal(excerptHistories.length,2);
    assert(!excerptHistories[1].some(message => message.content === excerptQuestion || message.content === 'AI temporarily unavailable.'));
    check('provider outage keeps source lookup usable and omits degraded turns from history');
    await page.locator('.citation-marker').last().click();
    assert(await page.getByText('Trích đoạn được tìm thấy trong tài liệu · Trang vật lý trong PDF',{exact:true}).isVisible());
    await page.locator('[data-source-preview]').first().click();
    assert((await page.locator('#preview-body iframe').getAttribute('src')).endsWith(`/api/documents/${docId}/file#page=1`));
    await page.keyboard.press('Escape');
    check('degraded excerpt opens its original PDF without AI claim labels');
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path:path.join(output,'source-excerpts-390x844.png')});
    await audit('source excerpt mode');
    await page.setViewportSize({width:1440,height:900});
    await page.unroute('**/api/query');
    await page.locator('#question').fill('What approval is required for enrollment?'); await page.locator('#send').click();
    await page.locator('.assistant-message').last().locator('.claim-sources').waitFor();
    check('subsequent user query returns to the normal grounded answer view');
    // Public-schema test responses exercise edge rendering without a paid API.
    await page.route('**/api/query',route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,answer:{answer:'<img src=x onerror="window.XSS=1"> Chưa đủ bằng chứng.',abstained:true,abstention_reason:'insufficient_evidence',citations:[{doc_id:docId,page:1,quote:'stale'}],claims:[]}})}));
    await page.locator('#question').fill('No evidence question'); await page.locator('#send').click();
    await page.getByText('Chưa đủ bằng chứng trong tài liệu đã chọn.',{exact:true}).waitFor();
    assert.equal(await page.locator('.source-card').count(),0);
    assert.equal(await page.locator('.answer-body img').count(),0);
    assert.equal(await page.evaluate(() => window.XSS),undefined);
    check('abstention clears stale sources and escapes unsafe HTML');
    await page.unroute('**/api/query');
    await page.route('**/api/query',route => route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({ok:false,error_code:'retrieval_not_ready'})}));
    await page.locator('#question').fill('What approval is required for enrollment?'); await page.locator('#send').click();
    await page.locator('[data-retry]').waitFor(); assert.equal(await page.locator('#query-form').getAttribute('aria-busy'),'false');
    await page.unroute('**/api/query');
    await page.locator('[data-retry]').click(); await page.locator('.source-card').first().waitFor();
    check('503 finishes loading and explicit retry succeeds');
    await page.route('**/api/query',route => route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({ok:true,answer:{answer:'Dịch vụ chưa thể trả lời.',abstained:true,abstention_reason:'provider_abstention',citations:[],claims:[]}})}));
    await page.locator('#question').fill('What approval is required for enrollment?'); await page.locator('#send').click();
    await page.getByText('Dịch vụ AI chưa sẵn sàng hoặc đang quá tải. Vui lòng thử lại sau.',{exact:true}).waitFor();
    assert.equal(await page.locator('.source-card').count(),0); check('provider overload differs from missing evidence');
    await page.unroute('**/api/query');
    await page.clock.install();
    const failedQuestion = 'Which approval is required for enrollment, please?';
    let outageRequests = 0;
    await page.route('**/api/query',route => { outageRequests++; return route.fulfill({status:503,contentType:'application/json',
      headers:{'Retry-After':'60'},body:JSON.stringify({ok:false,error_code:'provider_overloaded',retry_after_seconds:60})}); });
    await page.locator('#question').fill(failedQuestion); await page.locator('#send').click();
    await page.getByText('Dịch vụ Gemini đang quá tải (503). Chờ khoảng 60 giây trước khi gửi lại. App không tự gửi lại câu hỏi.',{exact:true}).waitFor();
    assert(await page.locator('[data-retry]').last().isDisabled());
    await page.locator('#question').fill('Another question'); assert(await page.locator('#send').isEnabled());
    await page.clock.fastForward(60001);
    assert.equal(outageRequests,1); assert(await page.locator('[data-retry]').last().isEnabled());
    check('provider cooldown counts down without automatic API retry');
    await page.unroute('**/api/query');
    let recoveredHistory;
    await page.route('**/api/query',route => { recoveredHistory=route.request().postDataJSON().history; return route.continue(); });
    await page.locator('[data-retry]').last().click(); await page.locator('.source-card').first().waitFor();
    assert(!recoveredHistory.some(message => message.content === failedQuestion));
    check('manual provider recovery omits failed turn from history');
    await page.unroute('**/api/query');
    await page.route('**/api/query',route => route.fulfill({status:429,contentType:'application/json',
      body:JSON.stringify({ok:false,error_code:'query_busy',retry_after_seconds:1})}));
    await page.locator('#question').fill(failedQuestion); await page.locator('#send').click();
    await page.getByText('Máy chủ đang xử lý một câu hỏi khác. Hãy chờ yêu cầu đó hoàn tất. Chờ khoảng 1 giây trước khi gửi lại. App không tự gửi lại câu hỏi.',{exact:true}).waitFor();
    assert(await page.locator('[data-retry]').last().isDisabled());
    await page.clock.fastForward(1001); assert(await page.locator('[data-retry]').last().isEnabled());
    await page.unroute('**/api/query'); check('busy request retry unlocks after short wait');
    let dailyRequests = 0;
    await page.route('**/api/query',route => { dailyRequests++; return route.fulfill({status:429,contentType:'application/json',
      body:JSON.stringify({ok:false,error_code:'provider_rate_limited',retry_after_seconds:90000})}); });
    await page.locator('#question').fill(failedQuestion); await page.locator('#send').click();
    await page.locator('[data-retry]').last().waitFor();
    await page.getByText(/Gemini đang giới hạn.*90000 giây/).waitFor();
    assert(await page.locator('[data-retry]').last().isDisabled());
    await page.clock.fastForward(1001); assert.equal(dailyRequests,1);
    await page.unroute('**/api/query');
    let localRequests = 0;
    await page.route('**/api/query',route => { localRequests++; return route.continue(); });
    await page.locator('#question').fill('What approval is required for enrollment?');
    assert(await page.locator('#send').isEnabled()); await page.locator('#send').click();
    await page.locator('.source-card').first().waitFor();
    assert.equal(localRequests,1); assert.equal(dailyRequests,1);
    assert(await page.locator('[data-retry]').last().isDisabled());
    await page.clock.fastForward(90001*1000);
    assert.equal(localRequests,1); assert(await page.locator('[data-retry]').last().isEnabled());
    await page.unroute('**/api/query');
    check('daily quota permits manual local lookup while failed-turn retry waits; no automatic resend');
    let heldRoute;
    await page.route('**/api/query',route => { heldRoute = route; });
    const timeoutRequest = page.waitForRequest('**/api/query');
    await page.locator('#question').fill('What approval is required for enrollment?'); await page.locator('#send').click();
    await timeoutRequest;
    await page.clock.fastForward(45001);
    await page.getByText('Yêu cầu mất quá nhiều thời gian. Bạn có thể thử lại. Việc dừng chờ không hủy xử lý trên máy chủ.',{exact:true}).waitFor();
    assert.equal(await page.locator('#query-form').getAttribute('aria-busy'),'false');
    if (heldRoute) await heldRoute.abort().catch(()=>{});
    await page.unroute('**/api/query'); await page.clock.resume(); check('45-second client timeout completes without claiming server cancellation');
    await page.locator('.nav-item[href="#guide"]').click();
    await page.locator('#view-guide').waitFor({state:'visible'}); await audit('guide');
    await page.locator('details summary').first().click(); assert(await page.locator('details').first().getAttribute('open') !== null);
    await page.locator('.nav-item[href="#collections"]').click(); await page.locator('#view-collections').waitFor({state:'visible'}); await audit('collections'); await page.locator('.collection-card').first().click();
    await page.locator('#view-documents').waitFor({state:'visible'}); check('collections filter and guide FAQ');
    await page.locator(`[data-delete="${docId}"]`).click();
    await page.locator('#delete-dialog .dialog-close').first().click();
    assert.equal((await context.request.get(`${baseUrl}/api/documents/${docId}`)).status(),200);
    for (const extra of listing.documents.filter(document => document.doc_id !== docId)) {
      await page.locator(`[data-delete="${extra.doc_id}"]`).click();
      await page.locator('#delete-confirm').click();
      await page.locator(`[data-delete="${extra.doc_id}"]`).waitFor({state:'detached'});
    }
    await page.locator(`[data-delete="${docId}"]`).click(); await page.locator('#delete-confirm').click();
    await page.getByText('Bạn chưa có tài liệu nào.',{exact:true}).waitFor();
    assert.equal((await context.request.get(`${baseUrl}/api/documents/${docId}/file`)).status(),404);
    assert.equal(await page.locator('.source-card').count(),0); check('delete confirmation and no stale source access');
    const invalidUpload = await context.request.post(`${baseUrl}/api/documents/upload`,{
      headers:{'Content-Type':'application/pdf','X-Filename':'invalid.pdf'},data:Buffer.from('%PDF-broken')});
    assert.equal(invalidUpload.status(),400);
    await page.reload();
    const orphanDelete = page.locator('#document-jobs [data-delete]');
    await orphanDelete.waitFor();
    assert.equal(await page.locator('#document-list .document-card').count(),0);
    await orphanDelete.click();
    assert.equal(await page.locator('#delete-name').textContent(),'invalid.pdf');
    await page.locator('#delete-confirm').click();
    await orphanDelete.waitFor({state:'detached'});
    assert.equal((await (await context.request.get(`${baseUrl}/api/documents`)).json()).jobs.length,0);
    check('failed upload without a registry document can be deleted from its job card');
    await page.locator('#clear-filters').click();
    await page.locator('.upload-main').click();
    await page.locator('#file-input').setInputFiles(path.join(fixtureDir,'mixed.pdf'));
    await page.locator('#upload-submit').click();
    await page.waitForFunction(() => [...document.querySelectorAll('#document-list .document-card')]
      .some(card => card.textContent.includes('mixed.pdf') && card.textContent.includes('Cần kiểm tra')));
    const scanned = (await (await context.request.get(`${baseUrl}/api/documents`)).json()).documents.find(doc => doc.name === 'mixed.pdf');
    assert(scanned.ocr_available && !scanned.ready);
    await page.locator(`#document-list [data-detail="${scanned.doc_id}"]`).click();
    await page.locator('#detail-content [data-ocr]').waitFor();
    assert((await page.locator('#detail-content').textContent()).includes('trang 2'));
    await audit('OCR review dialog');
    await page.route('**/api/documents/*/ocr',route => route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({ok:false,error_code:'job_store_unavailable'})}));
    await page.locator('[data-ocr]').click();
    await page.locator('#ocr-status').getByText(/Chưa lưu được/).waitFor();
    assert(await page.locator('[data-ocr]').isEnabled());
    await page.unroute('**/api/documents/*/ocr');
    await page.locator('[data-ocr]').click();
    await page.waitForFunction(() => [...document.querySelectorAll('#document-list .document-card')]
      .some(card => card.textContent.includes('mixed.pdf') && card.textContent.includes('Sẵn sàng')),
      undefined,{timeout:30000});
    const recognized = (await (await context.request.get(`${baseUrl}/api/documents/${scanned.doc_id}`)).json()).document;
    assert(recognized.ready && !recognized.ocr_available && recognized.page_count === 3);
    check('mixed PDF manual local OCR recovers after admission error and becomes ready without reupload');
    await page.locator(`[data-delete="${scanned.doc_id}"]`).click(); await page.locator('#delete-confirm').click();
    await page.getByText('Bạn chưa có tài liệu nào.',{exact:true}).waitFor();
    assert.deepEqual(errors,[]); check('no browser script errors');
    await fs.writeFile(path.join(output,'browser-results.json'),JSON.stringify({status:'PASS',browser:browser.version(),provider:'local test fixture; no live LLM calls',viewports,checks,browserErrors:errors},null,2));
  } finally { await context.close(); await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
