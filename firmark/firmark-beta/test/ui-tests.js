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

  /* ---- numeric correctness in the DOM (register §L11 / J8) ----
     Everything above this line is a smoke test: it fails on NaN, undefined
     and Infinity, which means a wrong-but-finite number renders clean and
     passes. That is the gap the register has carried as open, and it is the
     one that matters — a DCR of 0.62 where the engine computed 1.62 looks
     exactly like a working product.

     So: recompute independently, in the page, and require the rendered text
     to carry the engine's own answer. Compared as text rather than by
     scraping cells, so a front-end rewrite cannot quietly disable it. */
  for (const pk of packs) for (const pl of plans) {
    const wrong = await p.evaluate(([a, b2]) => {
      FM.state.sizing.packId = a; FM.state.sizing.planId = b2; FM.state.sizing.open = null;
      FM.go('sizing');
      const res = FM.solver.solvePlan(FM.weights.planById(b2), FM.weights.packById(a));
      const txt = document.getElementById('view-sizing').innerText;
      const miss = [];
      res.marks.forEach(m => {
        const row = m.unifiedTo || (m.solution && m.solution.pick);
        if (!row) return;
        /* the DCR the engine computed, at the precision the view prints */
        const d3 = row.dcr.toFixed(3), d2 = row.dcr.toFixed(2);
        if (txt.indexOf(d3) === -1 && txt.indexOf(d2) === -1) {
          miss.push(`${m.mark.id}: DCR ${d3} is not on screen`);
        }
        /* and the member it actually selected */
        if (txt.indexOf(row.cand.size) === -1) {
          miss.push(`${m.mark.id}: selected ${row.cand.size} is not on screen`);
        }
      });
      return miss;
    }, [pk, pl]);
    wrong.forEach(w => bad.push(`numbers ${pk}/${pl}: ${w}`));
  }

  /* the sheet view, same treatment — against the engine, not against itself */
  const sheetIds = await p.evaluate(() => FM.SHEETS.map(s => s.id));
  for (const id of sheetIds) {
    const wrong = await p.evaluate(sid => {
      FM.go('sheet', { sheetId: sid });
      const s = FM.SHEETS.filter(x => x.id === sid)[0];
      const r = FM.engine.run(FM.inputsFor(s));
      const txt = document.getElementById('view-sheet').innerText;
      if (r.error) return /Not evaluated|not evaluated/.test(txt)
        ? [] : [`${sid}: engine refused (${r.message}) but the sheet does not say so`];
      const miss = [];
      const d3 = r.governing.dcr.toFixed(3), d2 = r.governing.dcr.toFixed(2);
      if (txt.indexOf(d3) === -1 && txt.indexOf(d2) === -1)
        miss.push(`${sid}: governing DCR ${d3} is not on screen`);
      if (txt.indexOf(r.governing.name) === -1)
        miss.push(`${sid}: governing check "${r.governing.name}" is not on screen`);
      /* every individual check's DCR, not just the governing one */
      r.checks.forEach(c => {
        const c3 = c.dcr.toFixed(3), c2 = c.dcr.toFixed(2);
        if (isFinite(c.dcr) && txt.indexOf(c3) === -1 && txt.indexOf(c2) === -1)
          miss.push(`${sid}: ${c.name} DCR ${c3} is not on screen`);
      });
      return miss;
    }, id);
    wrong.forEach(w => bad.push(`numbers ${w}`));
  }

  /* ---- the sheet is not the optimistic path (register §L8) ----
     It used to take C_F as a typed number defaulting to 1.00, bypassing
     sizeFactor(), and had no way to declare a member incised — so the tool a
     PE reaches for to CHECK the solver was more permissive than the solver. */
  const sheetGaps = await p.evaluate(() => {
    FM.go('sheet', { sheetId: 'R-12' });
    const pane = document.getElementById('view-sheet');
    const txt = pane.innerText;
    const gaps = [];
    if (!/Incised/i.test(txt)) gaps.push('no incising control on the sheet');
    if (!/C_F/.test(txt)) gaps.push('no C_F control on the sheet');
    if (!/Catalog|auto/i.test(txt)) gaps.push('C_F does not show it is on the catalog path');

    /* switching to a refractory species with wet service must warn */
    const boxes = [].slice.call(pane.querySelectorAll('input[type=checkbox]'));
    const wet = boxes.filter(b => /Wet service/i.test(b.parentNode.textContent))[0];
    const inc = boxes.filter(b => /Incised/i.test(b.parentNode.textContent))[0];
    if (!wet) gaps.push('no wet-service checkbox');
    if (!inc) gaps.push('no incised checkbox');
    if (wet && inc) {
      if (inc.checked) gaps.push('incised defaults to checked');
      wet.checked = true; wet.dispatchEvent(new Event('change'));
      const after = document.getElementById('view-sheet').innerText;
      if (!/normally incised/i.test(after))
        gaps.push('wet DF-L with incising off does not warn that it reads high');
    }
    return gaps;
  });
  sheetGaps.forEach(g => bad.push(`sheet L8: ${g}`));

  /* and the refusal the sheet used to let through */
  const wide = await p.evaluate(() => {
    const r = FM.engine.run({
      species: 'Douglas Fir-Larch', grade: 'No. 2', size: '2x14', span: 14, spacing: 16,
      dead: 15, live: 40, roofLoad: 0, roofType: 'snow', repetitive: true, wet: false,
      braced: true, bearing: 3.0, memberUse: 'floor', CF: 'auto'
    });
    return r.error ? null : 'a 2x14 evaluated on the catalog C_F path instead of being refused';
  });
  if (wide) bad.push(`sheet L8: ${wide}`);

  /* ---- the repeat matrix must not lose its Mark column (B1) ----
     Six regions is 1807px of table. It was rendering in a 996px container with
     no scroll affordance and `sticky top` but no `sticky left`, so at a laptop
     width only two of six regions were reachable and scrolling right lost the
     Mark column — you could see six member sizes with no way to tell which
     mark they belonged to. Checked at the widths a demo actually runs at. */
  for (const w of [1440, 1280, 1100]) {
    await p.setViewportSize({ width: w, height: 800 });
    const matrix = await p.evaluate(() => {
      FM.go('sizing');
      const tab = document.querySelector('#view-sizing [data-tab="matrix"]');
      if (!tab) return ['no matrix tab'];
      tab.click();
      const gaps = [];
      const table = document.querySelector('#view-sizing table');
      if (!table) return ['matrix has no table'];
      /* the scroll container is whichever ancestor actually clips */
      let tw = table.parentNode;
      while (tw && tw !== document.body && getComputedStyle(tw).overflowX === 'visible') tw = tw.parentNode;
      if (!tw || tw === document.body) return ['matrix table has no scroll container'];

      if (tw.scrollWidth > tw.clientWidth + 1) {
        /* the mark cells, not the first td — the body also carries group-header
           rows whose first cell is a spanning label and has no mark in it */
        const marks = [].slice.call(table.querySelectorAll('tbody tr td.k'));
        if (!marks.length) return ['matrix has no mark cells'];
        const loose = marks.filter(td => {
          const cs = getComputedStyle(td);
          return cs.position !== 'sticky' || cs.left !== '0px';
        });
        if (loose.length)
          gaps.push(`overflows but ${loose.length}/${marks.length} Mark cells are not sticky-left`);
        const th = table.querySelector('thead th');
        const hcs = th ? getComputedStyle(th) : null;
        if (!hcs || hcs.position !== 'sticky' || hcs.left !== '0px')
          gaps.push('the Mark header is not sticky-left, so it detaches from its column');
        const ox = getComputedStyle(tw).overflowX;
        if (ox !== 'auto' && ox !== 'scroll')
          gaps.push('overflows but its container does not scroll horizontally');
        /* the container must be reachable by keyboard, not mouse-drag only */
        if (!tw.hasAttribute('tabindex')) gaps.push('scroll container is not keyboard-focusable');
      }
      /* and the page itself must never scroll sideways at any width */
      if (document.documentElement.scrollWidth > window.innerWidth + 1)
        gaps.push(`page scrolls horizontally (${document.documentElement.scrollWidth} > ${window.innerWidth})`);
      return gaps;
    });
    matrix.forEach(g => bad.push(`matrix B1 @${w}px: ${g}`));
  }
  await p.setViewportSize({ width: 1440, height: 1200 });

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

  /* a stale or mistyped link must degrade, not throw — AND SAY SO.
     An unknown view toasted; an unknown plan, region, variant, sheet or
     project did not. That is the dangerous half: you send a colleague a link,
     the plan id changed, and they open a schedule that renders perfectly and
     is not the one you sent — a wrong answer wearing the shape of a right one. */
  const staleCases = [
    { hash: '#/no-such-view/whatever',                           what: 'unknown view' },
    { hash: '#/sizing/gone-plan/nc-piedmont/schedule',           what: 'unknown plan' },
    { hash: '#/sizing/two-story-2450/gone-pack/schedule',        what: 'unknown region' },
    { hash: '#/sizing/two-story-2450/nc-piedmont/schedule/gone', what: 'unknown variant' },
    { hash: '#/sheet/S-999',                                     what: 'unknown sheet' },
    { hash: '#/project/nope',                                    what: 'unknown project' }
  ];
  for (const c of staleCases) {
    await p.goto(APP + c.hash);
    await p.waitForTimeout(350);
    const r = await p.evaluate(() => ({
      route: FM.state.route,
      hash: location.hash,
      toast: document.body.innerText.indexOf('which this build does not have') !== -1 ||
             document.body.innerText.indexOf('No such view') !== -1
    }));
    if (!r.toast) bad.push(`routing: ${c.what} (${c.hash}) fell back SILENTLY — no notice on screen`);
    /* the address bar must not keep naming something that is not on screen */
    if (r.hash === c.hash) bad.push(`routing: ${c.what} left the stale hash in the address bar`);
  }
  await p.goto(APP + '#/no-such-view/whatever');
  await p.waitForTimeout(250);
  const junk = await p.evaluate(() => FM.state.route);
  if (junk !== 'dashboard') bad.push(`routing: an unknown route landed on ${junk} instead of falling back`);

  /* Back must undo a step the user would call a step.
     Every sub-state change used to `replace`, so switching Texas -> Florida
     and pressing Back landed on the dashboard: the two regions had never been
     two entries. Region, plan and variant are steps; the tab is a lens. */
  await p.goto(APP);
  await p.waitForTimeout(300);
  const nav = await p.evaluate(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    FM.go('sizing'); await wait(150);
    const s = FM.state.sizing;
    const startPack = s.packId;
    const sel = document.querySelectorAll('#view-sizing select');
    const packSel = sel[0];
    const other = [].slice.call(packSel.options).filter(o => o.value !== startPack)[0];
    if (!other) return { skip: 'only one region' };
    packSel.value = other.value; packSel.dispatchEvent(new Event('change'));
    await wait(200);
    return { startPack: startPack, movedTo: FM.state.sizing.packId, hash: location.hash };
  });
  if (!nav.skip) {
    if (nav.movedTo === nav.startPack) bad.push('routing: region change did not take');
    await p.goBack();
    await p.waitForTimeout(300);
    const backTo = await p.evaluate(() => ({ route: FM.state.route, pack: FM.state.sizing.packId }));
    if (backTo.route !== 'sizing')
      bad.push(`routing: Back after a region change left Sizing entirely (landed on ${backTo.route})`);
    if (backTo.pack !== nav.startPack)
      bad.push(`routing: Back after a region change did not restore ${nav.startPack} (got ${backTo.pack})`);
  }

  /* a tab change is NOT a step — it must not stack history */
  await p.goto(APP + '#/sizing/two-story-2450/nc-piedmont/schedule');
  await p.waitForTimeout(300);
  const tabStack = await p.evaluate(async () => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const before = history.length;
    for (const t of ['region', 'matrix', 'schedule']) {
      const b = document.querySelector('#view-sizing [data-tab="' + t + '"]');
      if (b) { b.click(); await wait(120); }
    }
    return { before: before, after: history.length, hash: location.hash };
  });
  if (tabStack.after > tabStack.before)
    bad.push(`routing: three tab clicks added ${tabStack.after - tabStack.before} history entries — tabs should replace`);

  const uniq = [...new Set(bad)];
  console.log(uniq.length
    ? 'FAIL\n  ' + uniq.slice(0, 12).join('\n  ')
    : '\u2713 clean across ' + (packs.length * plans.length) +
      ' pack/plan combinations, every mark detail, all three tabs, the sheet species\n' +
      '  switch, routing (boot, Back, Forward, deep link, reload, unknown route), and\n' +
      '  every rendered DCR checked against an independent engine run');
  if (errs.length) console.log('page errors:', [...new Set(errs)].slice(0, 5));
  await b.close();
  process.exit(uniq.length || errs.length ? 1 : 0);
})();
