#!/usr/bin/env node
/* ============================================================
   UI smoke test.  Run:  node test/ui-tests.js
   Requires Playwright and a Chromium at PLAYWRIGHT_BROWSERS_PATH.

   core.js, sheet.js and sizing.js have no other coverage — the node
   suite loads only the DOM-free layers. That gap is how a fix to the
   seed bounds shipped while silently breaking the very card that
   displays them, and how the species dropdown came to substitute a
   grade that errors every sheet.

   This renders the real built bundle across every pack x plan, opens
   every mark's detail, and fails on any numeric slot that came out
   NaN, undefined, Infinity or an empty em-dash.
   ============================================================ */

var pwPath;
try { pwPath = require.resolve('playwright'); }
catch (e) { pwPath = '/opt/node22/lib/node_modules/playwright'; }
const { chromium } = require(pwPath);
const path = require('path');
const APP = 'file://' + path.join(__dirname, '..', 'firmark-app.html');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1440, height: 1200 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(APP);
  let bad = [];
  const packs = await p.evaluate(() => FM.weights.PACKS.map(x=>x.id));
  const plans = await p.evaluate(() => FM.weights.PLANS.map(x=>x.id));
  await p.evaluate(() => FM.go('sizing'));
  for (const pk of packs) for (const pl of plans) {
    await p.evaluate(([a,b2]) => { FM.state.sizing.packId=a; FM.state.sizing.planId=b2; FM.state.sizing.open=null; FM.go('sizing'); }, [pk,pl]);
    await p.waitForTimeout(120);
    // open every solvable mark's detail
    const n = await p.evaluate(() => document.querySelectorAll('#view-sizing tbody tr').length);
    for (let i=0;i<n;i++) {
      await p.evaluate(j => { const r=document.querySelectorAll('#view-sizing tbody tr'); if(r[j]) r[j].click(); }, i);
      await p.waitForTimeout(60);
      const t = await p.evaluate(() => document.getElementById('view-sizing').innerText);
      if (/NaN|undefined|≥ —|Infinity/.test(t)) bad.push(`${pk}/${pl}/row${i}: ` + (t.match(/.{0,50}(NaN|undefined|≥ —|Infinity).{0,30}/)||[])[0]);
    }
    for (const tab of ['region','matrix','schedule']) {
      await p.evaluate(t2 => { const x=document.querySelector('#view-sizing [data-tab="'+t2+'"]'); if(x) x.click(); }, tab);
      await p.waitForTimeout(tab==='matrix'?900:150);
      const t = await p.evaluate(() => document.getElementById('view-sizing').innerText);
      if (/NaN|undefined|Infinity/.test(t)) bad.push(`${pk}/${pl}/${tab}: ` + (t.match(/.{0,50}(NaN|undefined|Infinity).{0,30}/)||[])[0]);
    }
  }
  await p.evaluate(() => FM.go('sheet', { sheetId: 'R-12' }));
  await p.waitForTimeout(200);
  const sheetProblem = await p.evaluate(() => {
    var sel = document.querySelector('#view-sheet select');
    if (!sel) return 'no species select on the sheet';
    sel.value = 'Southern Pine';
    sel.dispatchEvent(new Event('change'));
    return /Not evaluated/i.test(document.getElementById('view-sheet').innerText)
      ? 'sheet errored after switching species to Southern Pine' : null;
  });
  if (sheetProblem) bad.push('sheet: ' + sheetProblem);

  const uniq = [...new Set(bad)];
  console.log(uniq.length
    ? 'FAIL\n  ' + uniq.slice(0, 12).join('\n  ')
    : '\u2713 clean across ' + (packs.length * plans.length) +
      ' pack/plan combinations, every mark detail, all three tabs, and the sheet species switch');
  if (errs.length) console.log('page errors:', [...new Set(errs)].slice(0, 5));
  await b.close();
  process.exit(uniq.length || errs.length ? 1 : 0);
})();
