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

   The page is reloaded before every single control, AND localStorage is
   cleared on every load. It is slower and it is the only way one
   control's effect cannot be another's. A Reset button halfway down a
   view must not decide what the buttons after it appear to do.

   The storage clear is not belt-and-braces: without it the reload does
   almost nothing, because localStorage survives one. That gap made the
   audit report cad's "Delete" as dead when Delete is not rendered at all
   unless something is selected — a selection had leaked in from an
   earlier click, several controls back.

   The drawing surface is SVG, not canvas. Both are fingerprinted: an
   earlier version measured only canvas and so could not see "Fit to
   content" or "Reload source" do their work, and called both dead.
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
   words a half-built button uses.

   Deliberately NARROW. "Nothing to export yet." is an honest empty-state
   message, not an unbuilt feature, and an earlier draft of this pattern
   matched it on the bare words "not yet" — which would have condemned a
   correct control. Only unambiguous admissions belong here. */
const EXCUSE = /(not wired|isn'?t wired|not implemented|not built|coming soon|\btodo\b|\bno-?op\b)/i;

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

  /* A control guarded by window.confirm() must be tested THROUGH its
     confirm, not around it. Playwright auto-dismisses dialogs, which
     answers the prompt "no" — so cad's "Reload source" was clicked,
     correctly did nothing because the user had declined, and got
     reported as a dead button. Accepting is what a user who meant to
     press it does. */
  page.on('dialog', async d => { try { await d.accept(); } catch (e) {} });

  /* Re-find a control after a reload, by zone and index. Enumeration is
     deterministic for a given view and run state, so the index is
     stable — and the label is carried into every result, so an index
     that drifts shows up as a renamed control rather than passing
     unnoticed. Installed as an init script so it survives every reload. */
  await page.addInitScript(() => {
    /* ISOLATION, for real this time.

       The header above claims that reloading before every control means
       one control's effect cannot be mistaken for another's. That was
       not true: localStorage SURVIVES a reload, so a control that saved
       a model, made a selection or approved a stage carried into every
       control audited after it.

       It showed up as a phantom: the audit reported cad's "Delete" as a
       dead button, and Delete is not even rendered unless something is
       selected — the selection had leaked in from an earlier click. An
       audit whose whole premise is isolation has to actually have it. */
    try { localStorage.clear(); } catch (e) {}

    window.__fmNodeAt = function (zone, i) {
      const roots = zone === 'chrome'
        ? [document.querySelector('.topbar'), document.querySelector('.rail')].filter(Boolean)
        : [document.querySelector('.view.active')].filter(Boolean);
      const nodes = [];
      roots.forEach(r => [].slice.call(r.querySelectorAll('button, select, a[href]'))
        .forEach(n => nodes.push(n)));
      return nodes[i];
    };
  });

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

  /* `skip` is [zone, index] of the control being operated. Setting a
     <select> necessarily changes its own value, so counting that as an
     effect would mark EVERY select alive — including the broken picker
     this whole file exists because of. The control under test is
     excluded from the value signature; everything it moves is not. */
  const FINGERPRINT = (skip) => {
    const active = document.querySelector('.view.active');
    const self = skip ? window.__fmNodeAt(skip[0], skip[1]) : null;
    /* The open class in this app is `on`, not `open`. Getting this wrong
       is not a detail: the first run of this audit checked for `show` on
       the toast, so it never detected a single toast, and reported a
       whole column of working buttons as dead. The record panel and the
       palette both use `on` too (`.palette-scrim.on { display: block }`),
       and the toast is ALWAYS display-visible with only its opacity
       animated — so for the toast the class is the only usable signal. */
    const openScrims = ['paletteScrim', 'recordScrim', 'gate']
      .filter(id => {
        const n = document.getElementById(id);
        if (!n) return false;
        if (n.hasAttribute('hidden')) return false;
        return n.classList.contains('on') || getComputedStyle(n).display !== 'none';
      });
    const toast = document.getElementById('toast');
    const store = {};
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      store[k] = localStorage.getItem(k);
    }
    /* The chrome is state too. Without this, the sidebar toggle and the
       theme toggle change nothing the fingerprint can see and would be
       reported as dead controls — a false accusation is as bad as a
       missed one. */
    const rail = document.getElementById('railToggle');
    const shell = document.getElementById('shell');
    const chrome = [
      document.documentElement.getAttribute('data-theme') || '',
      document.body.className || '',
      shell ? shell.className : '',
      rail ? rail.getAttribute('aria-expanded') : ''
    ].join('|');
    /* Three things a text-and-route fingerprint cannot see, each of which
       produced a FALSE ACCUSATION of a dead control on the first run:

         · a form control's value. A <textarea> filled by "Export into the
           box" changes no innerText anywhere.
         · which tab or tool is currently pressed. A segmented control
           whose job is to switch modes changes a class, not prose.
         · the canvas. "Fit to content" repaints pixels and touches
           nothing else in the DOM at all.

       Accusing a working button of being dead is exactly as damaging as
       missing a dead one, so all three are measured. */
    const scope = active || document.body;
    const values = [].slice.call(scope.querySelectorAll('input, select, textarea'))
      .filter(n => n !== self)
      .map(n => (n.type === 'checkbox' || n.type === 'radio') ? (n.checked ? '1' : '0') : n.value)
      .join('');
    const pressed = [].slice.call(
      scope.querySelectorAll('[aria-pressed], [aria-selected], [aria-current], .active, .is-active, .on, .sel'))
      .map(n => (n.className || '') + '#' +
                (n.getAttribute('aria-pressed') || '') +
                (n.getAttribute('aria-selected') || '') +
                (n.getAttribute('aria-current') || ''))
      .join('|');
    const canvases = [].slice.call(scope.querySelectorAll('canvas'))
      .map(c => {
        try { return c.width + 'x' + c.height + ':' + c.toDataURL().length; }
        catch (e) { return 'unreadable'; }
      }).join(',');
    /* The CAD view draws in SVG, and there is no <canvas> in this app at
       all. Measuring only canvas is why "Fit to content" and "Reload
       source" were both reported dead: zooming changes the drawing's
       markup length 24,235 -> 18,910 and Fit puts it back exactly, and
       none of that is text, a route, storage or a toast. */
    const svgs = [].slice.call(scope.querySelectorAll('svg'))
      .map(s => (s.getAttribute('viewBox') || '') + ':' +
                s.childElementCount + ':' + s.outerHTML.length).join(',');

    return {
      view: active ? active.id : null,
      hash: location.hash,
      scrims: openScrims.join(','),
      chrome,
      toast: (toast && toast.classList.contains('on')) ? (toast.textContent || '') : '',
      store: JSON.stringify(store),
      values, pressed, canvases, svgs,
      text: active ? (active.innerText || '') : '',
      controls: active ? active.querySelectorAll('button,select,a[href],input,textarea').length : 0
    };
  };

  /* ---------------- enumerate, stably ---------------- */

  /* Two zones. The view is what changes as you navigate; the chrome is
     the topbar and the nav rail, which every page carries and which an
     audit scoped to `.view.active` never touches at all — the theme
     toggle, the sidebar toggle, the search button and every rail link
     would go unexamined. */
  const ENUMERATE = (zone) => {
    const roots = zone === 'chrome'
      ? [document.querySelector('.topbar'), document.querySelector('.rail')].filter(Boolean)
      : [document.querySelector('.view.active')].filter(Boolean);
    const nodes = [];
    roots.forEach(r => [].slice.call(r.querySelectorAll('button, select, a[href]'))
      .forEach(n => nodes.push(n)));
    return nodes.map((n, i) => {
      const tag = n.tagName.toLowerCase();
      let label = (n.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60);
      if (!label) label = n.getAttribute('aria-label') || n.getAttribute('title') || n.id || '';
      /* Is this control ALREADY the chosen one? Clicking the tab you are
         on correctly does nothing, and calling that a dead button is a
         false accusation — it was 9 of the 31 the first clean run
         raised. Verified the honest way before trusting it: for each
         such pair the SIBLING was clicked and did change the view
         (Grid/Table, Schedule/Region pack, Section properties/Sawn
         design values, S0.0/S1.0). The pairs work; the flag was mine. */
      const cls = ' ' + (n.className || '') + ' ';
      const selected = n.getAttribute('aria-pressed') === 'true' ||
                       n.getAttribute('aria-selected') === 'true' ||
                       !!n.getAttribute('aria-current') ||
                       / (active|is-active|on|sel|current) /.test(cls);
      return {
        idx: i,
        tag,
        label,
        id: n.id || '',
        href: tag === 'a' ? (n.getAttribute('href') || '') : '',
        disabled: !!n.disabled,
        selected,
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
    if (before.chrome !== after.chrome) return 'chrome';
    if (before.store !== after.store) return 'stored';
    if (before.pressed !== after.pressed) return 'toggled';
    if (before.values !== after.values) return 'filled';
    if (before.canvases !== after.canvases || before.svgs !== after.svgs) return 'drew';
    if (after.toast && after.toast !== before.toast) return 'toast';
    /* A repaint of the same view with the same text and the same control
       count is not an effect. This is the case that used to read as a
       pass. */
    if (before.text !== after.text || before.controls !== after.controls) return 'redrew';
    return 'none';
  }

  /* ---------------- the walk ---------------- */

  const results = [];

  async function auditControl(view, warm, zone, idx) {
    pageErrors = [];
    await open(view, warm);

    const list = await page.evaluate(ENUMERATE, zone);
    const c = list[idx];
    if (!c) return null;

    if (c.disabled) {
      return { view, warm, zone, ...c, effect: 'disabled', errs: [] };
    }

    const before = await page.evaluate(FINGERPRINT, [zone, idx]);

    if (c.tag === 'select') {
      /* Clicking a select does nothing. The picker bug lived exactly
         here: the control existed, looked right, and changing it moved
         no state. Every option is chosen and each must move something. */
      const moved = [];
      for (const v of c.options) {
        await page.evaluate(([zone, i, val]) => {
          const n = window.__fmNodeAt(zone, i);
          n.value = val;
          n.dispatchEvent(new Event('change', { bubbles: true }));
        }, [zone, idx, v]);
        await page.waitForTimeout(200);
        const after = await page.evaluate(FINGERPRINT, [zone, idx]);
        moved.push({ value: v, effect: classify(before, after) });
        /* re-open so each option is judged from the same start */
        await open(view, warm);
      }
      const dead = moved.filter(m => m.effect === 'none' || m.effect === 'redrew');
      return {
        view, warm, zone, ...c,
        effect: dead.length === moved.length && moved.length ? 'none' : 'stored',
        detail: moved.map(m => m.value + '=' + m.effect).join(' '),
        errs: pageErrors.slice()
      };
    }

    await page.evaluate(([zone, i]) => {
      window.__fmNodeAt(zone, i).click();
    }, [zone, idx]);
    await page.waitForTimeout(260);

    const after = await page.evaluate(FINGERPRINT, [zone, idx]);
    const effect = classify(before, after);
    return { view, warm, zone, ...c, effect, toast: after.toast, errs: pageErrors.slice() };
  }

  for (const warm of [false, true]) {
    /* The chrome is the same on every page, so it is walked once per
       pass rather than eighteen times. */
    await open('dashboard', warm);
    const chromeList = await page.evaluate(ENUMERATE, 'chrome');
    for (let i = 0; i < chromeList.length; i++) {
      const r = await auditControl('dashboard', warm, 'chrome', i);
      if (r) results.push(r);
    }

    for (const view of views) {
      await open(view, warm);
      const list = await page.evaluate(ENUMERATE, 'view');
      if (!list.length) {
        results.push({ view, warm, zone: 'view', tag: '-', label: '(no controls)',
                       effect: 'empty', errs: [] });
        continue;
      }
      for (let i = 0; i < list.length; i++) {
        const r = await auditControl(view, warm, 'view', i);
        if (r) results.push(r);
      }
    }
  }

  await browser.close();

  /* ---------------- the verdict ---------------- */

  /* A control that is dead COLD but alive WARM is not dead — it is inert
     until the run gives it something to act on. The sheet's six selects
     are the clear case: with no plan chosen they move nothing, and with
     a run behind them every one recomputes. Worth knowing, not a defect;
     the fix there is to disable them with a reason, not to wire them. */
  const aliveWarm = {};
  results.filter(r => r.warm && r.effect !== 'none' && r.effect !== 'disabled')
    .forEach(r => { aliveWarm[(r.zone === 'chrome' ? 'chrome' : r.view) + ' ' + r.label] = true; });

  /* window.print() opens the browser's own print path and is not
     observable from the page in headless Chromium. Verified working
     separately by hooking window.print and watching it fire. Exempt by
     name and by reason, never by silence. */
  const UNOBSERVABLE = { 'planset Print / PDF': 'calls window.print(), which headless Chromium does not surface' };

  /* Idempotent when the view is ALREADY in the target state. Exempt by
     name and with the evidence, never by silence — and the evidence is a
     measurement, not an opinion: a wheel-zoom moves the CAD drawing's
     markup from 24,235 to 18,910 characters and "Fit to content"
     restores it to 24,235 exactly. The view renders already fitted, so
     clicking Fit on a fresh view is a correct no-op. Send the wheel
     event before the click if you ever want to see it work. */
  const IDEMPOTENT = {
    'cad Fit to content': 'the view renders already fitted; zoom first (24,235 -> 18,910 chars) ' +
                          'and Fit restores it exactly'
  };

  const bad = [], noted = [];
  for (const r of results) {
    const key = (r.zone === 'chrome' ? 'chrome' : r.view) + ' ' + r.label;
    const where = `${r.zone === 'chrome' ? 'chrome' : r.view}` +
                  `${r.warm ? ' (warm)' : ' (cold)'} · <${r.tag}> "${r.label}"`;
    if (r.effect === 'none' && r.selected) {
      noted.push(`already-active  ${where} — it is the current selection, so clicking it ` +
                 `correctly does nothing`);
    } else if (r.effect === 'none' && UNOBSERVABLE[key]) {
      noted.push(`unobservable    ${where} — ${UNOBSERVABLE[key]}`);
    } else if (r.effect === 'none' && IDEMPOTENT[key]) {
      noted.push(`idempotent      ${where} — ${IDEMPOTENT[key]}`);
    } else if (r.effect === 'none' && !r.warm && aliveWarm[key]) {
      noted.push(`needs a run     ${where} — inert with nothing loaded, works once the run ` +
                 `has content; consider disabling it with that reason`);
    } else if (r.effect === 'none') {
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
      r.warm ? 'warm' : 'cold', r.zone === 'chrome' ? 'chrome' : r.view, r.tag, r.effect,
      JSON.stringify(r.label), r.detail || '', (r.errs || []).join(' | ')
    ].join('\t')).join('\n') + '\n');
  console.log('\n   full record: ' + report);

  if (noted.length) {
    console.log('\n' + noted.length + ' NOT DEFECTS, listed so the number is not mistaken ' +
                'for silence\n');
    noted.forEach(n => console.log('  - ' + n));
  }

  if (bad.length) {
    console.log('\n' + bad.length + ' PROBLEMS\n');
    bad.forEach(b => console.log('  - ' + b));
    console.log('');
    process.exit(1);
  }
  console.log('\nEvery control does something real.\n');
})().catch(e => { console.error(e); process.exit(1); });
