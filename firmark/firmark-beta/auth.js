/* ============================================================
   auth.js — the closed gate.

   This product is closed: nothing renders until someone is signed
   in, because every artefact it produces is attributable. An
   approval with no name on it is not an approval, and a calculation
   package whose approval trail says "someone" is not reviewable.

   WHAT THIS IS NOT
   ----------------
   This is a DEMO GATE, not security. Credentials are Demo/Demo, they
   are compared in this file, and the session lives in localStorage.
   Anyone who opens the bundle in a text editor can read them. That is
   fine for what this is and is stated on the login screen itself, so
   nobody mistakes it for an access control.

   A real deployment replaces this whole file with a server session.
   The rest of the product only ever asks FM.auth for a user object,
   so that swap touches nothing else.
   ============================================================ */

(function () {
  "use strict";

  var KEY = "fm-session";

  /* Roles exist because the approval gates need them. A drafter may
     approve that the geometry is right; only a PE may accept the
     package for sealing. The pipeline enforces this — see pipeline.js. */
  var ROLES = {
    drafter:   { id: "drafter",   label: "Drafter",            rank: 1 },
    estimator: { id: "estimator", label: "Estimator",          rank: 2 },
    engineer:  { id: "engineer",  label: "Design engineer",    rank: 3 },
    pe:        { id: "pe",        label: "Licensed PE",        rank: 4 }
  };

  /* The demo account carries every role, because one person is driving.
     A real deployment has one role per account and the gates bite. */
  var ACCOUNTS = [
    {
      user: "Demo", pass: "Demo",
      profile: {
        id: "demo", name: "Demo User", initials: "DU",
        roles: ["drafter", "estimator", "engineer", "pe"],
        licence: null,
        note: "Demo account. Holds every role so one person can walk the whole " +
              "pipeline. It carries NO professional licence — the PE gate records " +
              "that the seal block was left for a licensed engineer."
      }
    }
  ];

  var session = null;

  function now() { return new Date().toISOString(); }

  function load() {
    if (session) return session;
    try {
      var raw = localStorage.getItem(KEY);
      if (raw) session = JSON.parse(raw);
    } catch (e) { session = null; }
    return session;
  }

  function save() {
    try {
      if (session) localStorage.setItem(KEY, JSON.stringify(session));
      else localStorage.removeItem(KEY);
    } catch (e) {}
  }

  function state() {
    var s = load();
    return { user: s ? s.user : null, at: s ? s.at : null };
  }

  function require_() { return !!(load() && load().user); }

  function login(u, p) {
    var hit = null;
    for (var i = 0; i < ACCOUNTS.length; i++) {
      if (ACCOUNTS[i].user === String(u) && ACCOUNTS[i].pass === String(p)) { hit = ACCOUNTS[i]; break; }
    }
    if (!hit) {
      /* One message for both failures. Saying "no such user" tells an
         attacker which half to keep trying — a habit worth keeping even
         in a demo gate, because demo gates get copied. */
      return { ok: false, why: "That username and password do not match an account." };
    }
    session = { user: hit.profile, at: now() };
    save();
    return { ok: true, user: hit.profile };
  }

  function logout() { session = null; save(); }

  function has(roleId) {
    var s = load();
    if (!s || !s.user) return false;
    for (var i = 0; i < s.user.roles.length; i++) if (s.user.roles[i] === roleId) return true;
    return false;
  }

  FM.auth = {
    ROLES: ROLES,
    state: state,
    login: login,
    logout: logout,
    require: require_,
    has: has,
    /* the demo credentials are printed on the login screen; keeping them
       here means the screen and the check cannot drift apart */
    DEMO: { user: "Demo", pass: "Demo" }
  };
})();
