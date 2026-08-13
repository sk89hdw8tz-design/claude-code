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

  /* ---- routing: Back and Reload must not be a cliff ----
     The app had no URL at all, so the browser's own controls threw the
     demo out of the product. These exercise the real browser history,
     not FM.go — the point is that the buttons on the chrome work. */
  await p.goto(APP);
  await p.waitForTimeout(150);
  const h0 = await p.evaluate(() => location.hash);
  if (!/^#\/dashboard/.test(h0)) bad.push(`routing: boot did not write a hash (got ${JSON.stringify(h0)})`);

  await p.evaluate(() => FM.go('materials'));
  await p.waitForTimeout(120);
  const h1 = await p.evaluate(() => location.hash);
  if (!/^#\/materials/.test(h1)) bad.push(`routing: navigating did not update the hash (got ${JSON.stringify(h1)})`);

  await p.goBack();
  await p.waitForTimeout(200);
  const back = await p.evaluate(() => ({ hash: location.hash, route: FM.state.route }));
  if (back.route !== 'dashboard') bad.push(`routing: Back left the app on ${back.route}, not dashboard`);

  await p.goForward();
  await p.waitForTimeout(200);
  const fwd = await p.evaluate(() => FM.state.route);
  if (fwd !== 'materials') bad.push(`routing: Forward landed on ${fwd}, not materials`);

  /* a deep link, cold, in a fresh page load — the shareable case */
  await p.goto(APP + '#/sizing/two-story-2450/fl-hvhz');
  await p.waitForTimeout(400);
  const deep = await p.evaluate(() => ({
    route: FM.state.route,
    plan: FM.state.sizing && FM.state.sizing.planId,
    pack: FM.state.sizing && FM.state.sizing.packId,
    text: document.getElementById('view-sizing').innerText.slice(0, 400)
  }));
  if (deep.route !== 'sizing') bad.push(`routing: deep link did not open sizing (got ${deep.route})`);
  if (deep.plan !== 'two-story-2450' || deep.pack !== 'fl-hvhz')
    bad.push(`routing: deep link lost its arguments (plan=${deep.plan} pack=${deep.pack})`);
  if (/NaN|undefined/.test(deep.text)) bad.push('routing: deep-linked view rendered NaN/undefined');

  /* reload must land on the same thing, which is the whole point */
  await p.reload();
  await p.waitForTimeout(400);
  const again = await p.evaluate(() => ({
    route: FM.state.route, plan: FM.state.sizing && FM.state.sizing.planId }));
  if (again.route !== 'sizing' || again.plan !== 'two-story-2450')
    bad.push(`routing: reload dropped the view (route=${again.route} plan=${again.plan})`);

  /* a stale or mistyped link must degrade, not throw */
  await p.goto(APP + '#/no-such-view/whatever');
  await p.waitForTimeout(250);
  const junk = await p.evaluate(() => FM.state.route);
  if (junk !== 'dashboard') bad.push(`routing: an unknown route landed on ${junk} instead of falling back`);

  const uniq = [...new Set(bad)];
  console.log(uniq.length
    ? 'FAIL\n  ' + uniq.slice(0, 12).join('\n  ')
    : '\u2713 clean across ' + (packs.length * plans.length) +
      ' pack/plan combinations, every mark detail, all three tabs, the sheet species\n' +
      '  switch, and routing \u2014 boot, Back, Forward, deep link, reload, unknown route');
  if (errs.length) console.log('page errors:', [...new Set(errs)].slice(0, 5));
  await b.close();
  process.exit(uniq.length || errs.length ? 1 : 0);
})();
