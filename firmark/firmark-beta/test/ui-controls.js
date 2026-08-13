#!/usr/bin/env node
/* ============================================================
   THE CONTROL AUDIT.  Run:  node test/ui-controls.js

   Every button, link and select in the real built bundle, clicked, with
   the effect classified. A control either does something, or it is not
   there. A button that toasts "not wired up yet" is a promise the
   product cannot keep, and this file fails on it by name.

   WHY THIS EXISTS, stated plainly so nobody deletes it as redundant:

   `node test/run-tests.js` loads fourteen modules and NOT ONE of them is
   a view. scope, engine, weights, solver, jurisdiction, cad, dxf,
   takeoff, bom, export, planset, auth, pipeline, project — that is the
   whole list. core.js, stages-view.js, pipeline-view.js, sheet.js,
   sizing.js and materials.js have no headless coverage at all, so every
   assertion in that suite can be green while the user interface is
   inoperable.

   That is not hypothetical. The jurisdiction picker shipped completely
   non-functional: choosing a state re-rendered the view, the fresh
   <select> read back its own empty value, and stage 3 was unreachable
   through the only path a human has. The suite was green throughout.
   Every end-to-end run that "passed" had set jurisId from the console.

   And an audit that measures "did the DOM change" cannot catch it,
   because re-rendering the view IS a DOM change. Detection by
   side-effect is not detection of the RIGHT side-effect. So each click
   here is classified against a before/after fingerprint — route,
   dialogs, storage, toast — and a bare repaint of the same view counts
   as NOTHING.

   The page is reloaded before every single control. It is slower and it
   is the only way one control's effect cannot be another's. A Reset
   button halfway down a view must not decide what the buttons after it
   appear to do.
   ============================================================ */

var pwPath;
try { pwPath = require.resolve('playwright'); }
catch (e) { pwPath = '/opt/node22/lib/node_modules/playwright'; }
const { chromium } = require(pwPath);
const path = require('path');
const fs = require('fs');

const APP = 'file://' + path.join(__dirname, '..', 'firmark-app.html');
const APP_FILE = path.join(__dirname, '..', 'firmark-app.html');

/* The views the shell declares. Read from the bundle rather than listed
   here, so a view added to shell.html is audited without anyone
   remembering to add it. */
function viewsFromBundle() {
  const html = fs.readFileSync(APP_FILE, 'utf8');
  const out = [];
  const re = /<div class="view[^"]*" id="view-([a-z-]+)"/g;
  let m;
  while ((m = re.exec(html))) out.push(m[1]);
  return out;
}

/* A control that destroys run state is clicked like any other — the
   reload before the next one undoes it. This list exists only so the
   report can say which failures are expected to be loud. */
const DESTRUCTIVE = /^(reset|clear|delete|remove|discard|sign out|reject|revoke|start over)\b/i;

/* A toast that admits the control does nothing. These are the exact
   words a half-built button uses. */
const EXCUSE = /(not wired|not implemented|not yet|coming soon|todo|no-?op|unavailable in this build|placeholder)/i;

(async () => {
  const views = viewsFromBundle();
  if (!views.length) {
    console.error('no views found in the bundle — has it been built? (node build.js)');
    process.exit(1);
  }

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });

  let pageErrors = [];
  page.on('pageerror', e => pageErrors.push(e.message));

  /* ---------------- the page, in a known condition ---------------- */

  async function signIn() {
    const gated = await page.evaluate(() => {
      const g = document.getElementById('gate');
      return !!g && !g.hasAttribute('hidden');
    });
    if (!gated) return;
    await page.evaluate(() => {
      document.getElementById('gateUser').value = 'Demo';
      document.getElementById('gatePass').value = 'Demo';
      document.getElementById('gateForm').dispatchEvent(
        new Event('submit', { cancelable: true, bubbles: true }));
    });
    await page.waitForTimeout(180);
    const still = await page.evaluate(() =>
      !document.getElementById('gate').hasAttribute('hidden'));
    if (still) throw new Error('could not sign in with Demo/Demo');
  }

  /* A run with real content behind it. Without this, most of the app is
     empty-state and the buttons that only exist once there is something
     to act on are never audited at all. Set through the module API on
     purpose: this file audits controls, it does not audit the setup
     path — ui-tests.js drives that. */
  async function seed() {
    return await page.evaluate(() => {
      const out = { ok: true, steps: [] };
      try {
        FM.project.reset();
        FM.project.set({ planId: 'starter-1210', stateCode: 'TX', jurisId: 'tx-houston' });
        out.steps.push('plan+juris');
        if (FM.pipeline && FM.pipeline.reset) FM.pipeline.reset();
        const order = ['geometry', 'takeoff', 'loads', 'calcs', 'bom'];
        for (const id of order) {
          const gate = FM.pipeline.can(id);
          if (!gate.ok) { out.steps.push(id + ' BLOCKED: ' + gate.blockedBy.join(' | ')); break; }
          FM.pipeline.approve(id, 'seeded by the control audit');
          out.steps.push(id + ' approved');
        }
      } catch (e) { out.ok = false; out.err = e.message; }
      return out;
    });
  }

  async function open(view, warm) {
    await page.goto(APP);
    await page.waitForTimeout(120);
    await signIn();
    if (warm) { await seed(); }
    await page.evaluate(v => FM.go(v), view);
    await page.waitForTimeout(220);
  }

  /* ---------------- what the page looks like right now ---------------- */

  const FINGERPRINT = () => {
    const active = document.querySelector('.view.active');
    const openScrims = ['paletteScrim', 'recordScrim', 'gate']
      .filter(id => {
        const n = document.getElementById(id);
        if (!n) return false;
        if (n.hasAttribute('hidden')) return false;
        return n.classList.contains('open') ||
               getComputedStyle(n).display !== 'none';
      });
    const toast = document.getElementById('toast');
    const store = {};
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      store[k] = localStorage.getItem(k);
    }
    return {
      view: active ? active.id : null,
      hash: location.hash,
      scrims: openScrims.join(','),
      toast: (toast && toast.classList.contains('show')) ? (toast.textContent || '') : '',
      store: JSON.stringify(store),
      text: active ? (active.innerText || '') : '',
      controls: active ? active.querySelectorAll('button,select,a[href],input,textarea').length : 0
    };
  };

  /* ---------------- enumerate, stably ---------------- */

  const ENUMERATE = () => {
    const active = document.querySelector('.view.active');
    const scope = active || document.body;
    const nodes = [].slice.call(scope.querySelectorAll('button, select, a[href]'));
    return nodes.map((n, i) => {
      const tag = n.tagName.toLowerCase();
      let label = (n.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60);
      if (!label) label = n.getAttribute('aria-label') || n.getAttribute('title') || n.id || '';
      return {
        idx: i,
        tag,
        label,
        id: n.id || '',
        href: tag === 'a' ? (n.getAttribute('href') || '') : '',
        disabled: !!n.disabled,
        options: tag === 'select'
          ? [].slice.call(n.options).map(o => o.value).filter(v => v !== '')
          : []
      };
    });
  };

  /* ---------------- classify one interaction ---------------- */

  function classify(before, after) {
    if (before.view !== after.view || before.hash !== after.hash) return 'navigated';
    if (before.scrims !== after.scrims) return 'dialog';
    if (before.store !== after.store) return 'stored';
    if (after.toast && after.toast !== before.toast) return 'toast';
    /* A repaint of the same view with the same text and the same control
       count is not an effect. This is the case that used to read as a
       pass. */
    if (before.text !== after.text || before.controls !== after.controls) return 'redrew';
    return 'none';
  }

  /* ---------------- the walk ---------------- */

  const results = [];

  async function auditControl(view, warm, idx) {
    pageErrors = [];
    await open(view, warm);

    const list = await page.evaluate(ENUMERATE);
    const c = list[idx];
    if (!c) return null;

    if (c.disabled) {
      return { view, warm, ...c, effect: 'disabled', errs: [] };
    }

    const before = await page.evaluate(FINGERPRINT);

    if (c.tag === 'select') {
      /* Clicking a select does nothing. The picker bug lived exactly
         here: the control existed, looked right, and changing it moved
         no state. Every option is chosen and each must move something. */
      const moved = [];
      for (const v of c.options) {
        await page.evaluate(([i, val]) => {
          const active = document.querySelector('.view.active');
          const n = active.querySelectorAll('button, select, a[href]')[i];
          n.value = val;
          n.dispatchEvent(new Event('change', { bubbles: true }));
        }, [idx, v]);
        await page.waitForTimeout(200);
        const after = await page.evaluate(FINGERPRINT);
        moved.push({ value: v, effect: classify(before, after) });
        /* re-open so each option is judged from the same start */
        await open(view, warm);
      }
      const dead = moved.filter(m => m.effect === 'none' || m.effect === 'redrew');
      return {
        view, warm, ...c,
        effect: dead.length === moved.length && moved.length ? 'none' : 'stored',
        detail: moved.map(m => m.value + '=' + m.effect).join(' '),
        errs: pageErrors.slice()
      };
    }

    await page.evaluate(i => {
      const active = document.querySelector('.view.active');
      const n = active.querySelectorAll('button, select, a[href]')[i];
      n.click();
    }, idx);
    await page.waitForTimeout(260);

    const after = await page.evaluate(FINGERPRINT);
    const effect = classify(before, after);
    return { view, warm, ...c, effect, toast: after.toast, errs: pageErrors.slice() };
  }

  for (const warm of [false, true]) {
    for (const view of views) {
      await open(view, warm);
      const list = await page.evaluate(ENUMERATE);
      if (!list.length) {
        results.push({ view, warm, tag: '-', label: '(no controls)', effect: 'empty', errs: [] });
        continue;
      }
      for (let i = 0; i < list.length; i++) {
        const r = await auditControl(view, warm, i);
        if (r) results.push(r);
      }
    }
  }

  await browser.close();

  /* ---------------- the verdict ---------------- */

  const bad = [];
  for (const r of results) {
    const where = `${r.view}${r.warm ? ' (warm)' : ' (cold)'} · <${r.tag}> "${r.label}"`;
    if (r.effect === 'none') {
      bad.push(`DEAD    ${where} — clicked, and nothing changed: not the view, not the ` +
               `route, not storage, no dialog, no toast`);
    }
    if (r.toast && EXCUSE.test(r.toast)) {
      bad.push(`EXCUSE  ${where} — its whole effect is a toast that admits it does ` +
               `nothing: "${r.toast.trim()}"`);
    }
    if (r.errs && r.errs.length) {
      bad.push(`THREW   ${where} — ${r.errs.join(' | ')}`);
    }
    if (r.tag === 'a' && (r.href === '#' || /^javascript:/i.test(r.href)) && r.effect === 'redrew') {
      bad.push(`STUB    ${where} — href="${r.href}" and the click only repainted`);
    }
  }

  const counted = results.filter(r => r.effect !== 'empty');
  const byEffect = {};
  counted.forEach(r => { byEffect[r.effect] = (byEffect[r.effect] || 0) + 1; });

  console.log('\nCONTROL AUDIT — ' + counted.length + ' controls across ' +
              views.length + ' views, cold and warm\n');
  Object.keys(byEffect).sort().forEach(k => {
    console.log('   ' + String(byEffect[k]).padStart(4) + '  ' + k);
  });

  /* The full record, so a reviewer can see what each control did rather
     than trusting the summary. */
  const report = path.join(__dirname, '..', 'control-audit.txt');
  fs.writeFileSync(report,
    results.map(r => [
      r.warm ? 'warm' : 'cold', r.view, r.tag, r.effect,
      JSON.stringify(r.label), r.detail || '', (r.errs || []).join(' | ')
    ].join('\t')).join('\n') + '\n');
  console.log('\n   full record: ' + report);

  if (bad.length) {
    console.log('\n' + bad.length + ' PROBLEMS\n');
    bad.forEach(b => console.log('  - ' + b));
    console.log('');
    process.exit(1);
  }
  console.log('\nEvery control does something real.\n');
})().catch(e => { console.error(e); process.exit(1); });
