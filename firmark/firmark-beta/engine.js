/* ============================================================
   NDS 2024 ASD wood member check — simply-supported, uniformly
   loaded sawn bending member.

   Reference design values and section properties are read from
   MATDATA, extracted verbatim from the public material catalogs.
   Adjustment factors follow NDS Table 4.3.1 applicability, with
   each factor's clause printed on the sheet.

   Deliberate boundary: C_F (size factor) is NOT published in the
   material catalog, so it is a typed input flagged as unsourced.
   ============================================================ */

(function () {
  "use strict";

  /* ---- load duration, NDS Table 2.3.2 ---- */
  var CD = {
    dead:      { v: 0.90, label: "Permanent (D)" },
    live:      { v: 1.00, label: "Ten years (L)" },
    snow:      { v: 1.15, label: "Two months (S)" },
    roof_live: { v: 1.25, label: "Seven days (Lr)" }
  };

  /* ---- wet service multipliers, NDS Table 4A (dimension lumber) ---- */
  var CM_WET = { Fb: 0.85, Fv: 0.97, Fc_perp: 0.67, Fc: 0.80, E: 0.90, Emin: 0.90 };

  /* ---- incising factor, NDS Table 4.3.8 ----
     Refractory species must be incised to take preservative. This was previously
     handled by excluding those species from treated marks, which is a containment
     rather than a fix — and a containment keyed on a proxy eventually keys on the
     wrong one. C_i is the same class of constant as C_D, C_M and C_t, all of
     which are hard-coded here already. */
  var CI = { Fb: 0.80, Ft: 0.80, Fv: 0.80, Fc: 0.80, E: 0.95, Emin: 0.95, Fc_perp: 1.00 };

  /* ---- deflection limits, IBC Table 1604.3 ----

     READ THIS BEFORE "FIXING" THE NUMBERS BELOW. The comment that used to sit
     here recited a two-column table and claimed the no-ceiling roof row was
     L/180 in BOTH columns. That was wrong, and it was wrong directly above
     correct code — a maintainer reconciling the comment to the code would have
     broken the engine. The table as printed has THREE load columns:

         Construction                        L        S or W     D + L
         Roof, plaster/stucco ceiling        ℓ/360    ℓ/360      ℓ/240
         Roof, nonplaster ceiling            ℓ/240    ℓ/240      ℓ/180
         Roof, not supporting a ceiling      ℓ/180    ℓ/180      ℓ/120
         Floor members                       ℓ/360    —          ℓ/240

     `live` below is the variable-load column (L, or S or W — they are numerically
     identical on every roof row, so one field carries both). `total` is the D + L
     column. The two are NOT equal on any row; a table that shows them equal has
     collapsed the first two columns and reprinted them under the third heading.

     DELIBERATE DEVIATION — roof_no_ceiling.total is 180 where IBC allows 120.
     That is a firm overlay, tighter than code, not a transcription of the table.
     It is not a bug and it must not be "corrected" to 120 without a decision from
     the firm. Everything else is the table as printed. See calc-spec §5.5.

     Scope note: the IRC governs one- and two-family dwellings, and every region
     pack in weights.js declares the IRC. IRC Table R301.7 has NO D + L column at
     all — so the `total` row here is a firm overlay for IRC work in its entirety,
     not an IRC requirement. Under the IBC it is a real code limit. */
  var DEFL = {
    floor:            { live: 360, total: 240, cite: "IBC T1604.3 · floor members" },
    roof_plaster:     { live: 360, total: 240, cite: "IBC T1604.3 · roof, plaster ceiling" },
    roof_nonplaster:  { live: 240, total: 180, cite: "IBC T1604.3 · roof, non-plaster ceiling" },
    /* totalCite is set only where the total-load limit is NOT the printed IBC value,
       so the sheet cannot cite a code section that does not contain the number. */
    roof_no_ceiling:  { live: 180, total: 180, cite: "IBC T1604.3 · roof, no ceiling",
                        totalCite: "FIRM OVERLAY · L/180 where IBC T1604.3 allows L/120 — tighter than code by policy, not a code limit" }
  };

  var LIMITS = [
    "Simply-supported single span, uniformly loaded",
    "Sawn dimension lumber only — timbers, glulam, SCL, CLT and I-joists are out of scope",
    "Gravity combinations only — no wind, seismic, uplift or lateral",
    "A snow load and a roof live load are carried separately; when both are supplied " +
      "all six ASCE 7 §2.4.1 gravity combinations are enumerated, so D + Lr and D + S are " +
      "both evaluated in the same run and may be governed by different limit states",
    "No cantilevers, continuous spans, notches, holes or camber",
    "No fire design, vibration, ponding or connection design",
    "ASD only — LRFD not implemented",
    "Creep (K_cr, NDS §3.5.2) not applied to long-term deflection",
    "C_b = 1.0 — bearings are at member ends, so NDS §3.10.4 does not apply",
    "C_F is a typed input; it is not carried in the material catalog",
    "C_i (incising, Table 4.3.8) applied when the member is declared incised",
    "Spans are HORIZONTAL PROJECTIONS and every psf is on the horizontal projection — " +
      "converting a sloped-roof assembly to the horizontal is the user's responsibility (§1.4)",
    "No wall dead load is carried anywhere — a header under a gable end or an upper storey " +
      "must have that load added by hand"
  ];

  /* ---------- lookups ---------- */

  function findSection(nominal) {
    if (!window.MATDATA) return null;
    /* Dimension lumber only. Table 4A values do not apply to timbers or
       beams & stringers, and the catalog carries no Table 4D. */
    return MATDATA.sections.filter(function (s) {
      return s.nominal === nominal && s.size_class === "Dimension lumber";
    })[0] || null;
  }

  /* Nominal width → dressed depth, read from the Table 1B payload itself rather
     than computed. The S4S dry allowance is not a single constant: nominal widths
     through 6" dress to (n − 1/2), 8" and wider to (n − 3/4).

     Only the dimension-lumber and board rows may seed this map. Timbers dress to
     (n − 1/2) at every width — 8x8 is 7.5 deep where 2x8 is 7.25 — so letting the
     timber rows in would shift the map by 1/4 in and silently hide the Table 4B
     rows keyed '8" wide' / '10" wide' / '12" wide'. Table 4A and 4B size classes
     describe dimension lumber, so dimension lumber is what the map is built from. */
  var DRESSED = null;
  function dressedDepth(nominalWidth) {
    if (!DRESSED) {
      DRESSED = {};
      ((window.MATDATA && MATDATA.sections) || []).forEach(function (s) {
        if (s.size_class !== "Dimension lumber" && s.size_class !== "Boards") return;
        var m = /^(\d+)x(\d+)$/.exec(s.nominal || "");
        if (m) DRESSED[m[2]] = s.d_in;      /* 1x10, 2x10, 3x10, 4x10 all dress to 9.25 */
      });
    }
    var v = DRESSED[String(nominalWidth)];
    if (v !== undefined) return v;
    /* outside the catalog: PS 20 dry-dressed allowance */
    return nominalWidth < 8 ? nominalWidth - 0.5 : nominalWidth - 0.75;
  }

  /* Size-class strings in Table 4A/4B are things like:
     '2" & wider', '2" - 4" wide', '2"-4" thick', '5" - 6" wide', '12" wide' …
     They are written in NOMINAL widths; `d` arrives dressed, so every comparison
     goes through dressedDepth(). Getting this wrong silently hides whole rows —
     Table 4B's Southern Pine 2x4 and 2x6 columns are the ones that disappear. */
  /* "2-1/2" in a size class is two and a half inches, not two minus a half */
  function nominalNum(txt) {
    var m = /^(\d+)(?:-(\d+)\/(\d+))?$/.exec(String(txt).trim());
    if (!m) return Number(txt);
    return Number(m[1]) + (m[2] ? Number(m[2]) / Number(m[3]) : 0);
  }
  function dressedFrom(nominal) {
    return nominal < 8 ? nominal - 0.5 : nominal - 0.75;
  }

  function classCoversDepth(sizeClass, d, b) {
    if (!sizeClass) return false;
    var s = sizeClass.toLowerCase();
    var EPS = 0.01;

    var wider = s.match(/(\d+)\s*["”]?\s*&\s*wider/);
    if (wider) return d >= dressedDepth(Number(wider[1])) - EPS;

    var range = s.match(/(\d+)\s*["”]?\s*-\s*(\d+)\s*["”]?\s*wide/);
    if (range) {
      var lo = dressedDepth(Number(range[1])), hi = dressedDepth(Number(range[2]));
      return d >= lo - EPS && d <= hi + EPS;
    }

    var exact = s.match(/^(\d+)\s*["”]?\s*wide/);
    if (exact) return Math.abs(d - dressedDepth(Number(exact[1]))) < EPS;

    /* Thickness descriptors do not constrain DEPTH — but they do constrain
       BREADTH, and treating them as a blanket match let a 1.5"-thick 2x10 read
       its values off Table 4B's '2-1/2" - 4" thick' row. When the caller tells
       us the breadth, honour it. */
    var thick = s.match(/(\d+(?:-\d+\/\d+)?)\s*["”]?\s*(?:-\s*(\d+(?:-\d+\/\d+)?)\s*["”]?\s*)?(?:&\s*thicker\s*)?thick/);
    if (thick) {
      if (b === undefined || b === null) return true;
      var lo = dressedFrom(nominalNum(thick[1]));
      if (b < lo - EPS) return false;
      if (thick[2]) {
        var hi = dressedFrom(nominalNum(thick[2]));
        if (b > hi + EPS) return false;
      }
      return true;
    }
    return false;
  }

  function findValues(species, grade, depth, breadth) {
    if (!window.MATDATA) return null;
    var sp = MATDATA.southern_pine.records || [];
    var isSP = sp.some(function (r) { return r.species === species; });
    var pool = isSP ? sp : MATDATA.species_grades;

    /* NDS-S Table 4A: over 6 in wide, Stud grade takes No. 3 tabulated VALUES and
       No. 3 size factors. The catalog tabulates Stud as '2" & wider' with no width
       limit, so a Stud 2x10 was reading Stud's own F_b — 700 psi where No. 3 gives
       525, a 33% overstatement that flips a floor joist from 0.79 to 1.05. The two
       C_F rows are numerically identical, so the whole error is in the values and
       none of it is in C_F. */
    if (!isSP && grade === "Stud" && depth !== undefined && depth > 6.0 - 0.5 + 0.01) {
      var no3 = pool.filter(function (r) { return r.species === species && r.grade === "No. 3"; });
      if (no3.length) grade = "No. 3";
    }

    var exact = pool.filter(function (r) { return r.species === species && r.grade === grade; });
    if (!exact.length) return null;

    if (depth === undefined) return exact[0];

    /* pick the record whose size class actually covers this depth —
       never silently fall back to a narrower class */
    var fit = exact.filter(function (r) { return classCoversDepth(r.size_class, depth, breadth); });
    if (!fit.length) return null;

    /* prefer the most specific (narrowest) descriptor */
    fit.sort(function (a, b) {
      var aw = /wider/i.test(a.size_class) ? 1 : 0, bw = /wider/i.test(b.size_class) ? 1 : 0;
      return aw - bw;
    });
    return fit[0];
  }

  function isSouthernPine(species) {
    if (!window.MATDATA) return false;
    return (MATDATA.southern_pine.records || []).some(function (r) { return r.species === species; });
  }

  function speciesList() {
    if (!window.MATDATA) return [];
    var seen = {}, out = [];
    function add(species, grade) {
      if (!seen[species]) { seen[species] = []; out.push(species); }
      if (seen[species].indexOf(grade) === -1) seen[species].push(grade);
    }
    MATDATA.species_grades.forEach(function (r) {
      /* Table 4A tabulates one row per grade across all widths; the '2" & wider'
         descriptor is that row. Filtering to it dedupes the list. */
      if (!/wider/i.test(r.size_class || "")) return;
      add(r.species, r.grade);
    });
    /* Table 4B is tabulated per nominal width instead, so there is no single
       '& wider' row to filter on — collect Southern Pine across every width.
       Leaving it out made the species that frames most of the Southeast
       unselectable even though the engine knew how to design it. */
    ((MATDATA.southern_pine && MATDATA.southern_pine.records) || []).forEach(function (r) {
      add(r.species, r.grade);
    });
    out.sort();
    return out.map(function (sp) { seen[sp].sort(); return { species: sp, grades: seen[sp] }; });
  }

  function sizeList() {
    if (!window.MATDATA) return [];
    return MATDATA.sections
      .filter(function (s) { return s.size_class === "Dimension lumber"; })
      .map(function (s) { return s.nominal; });
  }

  /* ---------- C_F, size factor ----------
     The catalog carries no published Table 4A size-factor table; what it does
     carry is the per-record helper the wet/PT seed uses to test the C_M
     thresholds, which the seed itself flags as threshold-only. sizeFactor()
     resolves a C_F for a candidate section and says exactly where the number
     came from, so nothing silently passes as sourced.

     Three outcomes:
       table_4b     Southern Pine — C_F is already inside the tabulated value.
       repo_partial the repo's threshold helper covers this cell.
       held         nothing covers it; C_F is held at 1.00 and flagged.
     plus `refuse`, for the one case where holding at 1.00 cannot be shown to be
     conservative: nominal widths of 14 in and wider, where Table 4A publishes a
     size factor below 1.00 that the catalog does not carry (gap register #1). */

  var CF_ROW = {
    "Select Structural": "SS / No.1 / No.2 / No.3",
    "No. 1 & Btr": "SS / No.1 / No.2 / No.3",
    "No. 1/No. 2": "SS / No.1 / No.2 / No.3",
    "No. 1": "SS / No.1 / No.2 / No.3",
    "No. 2": "SS / No.1 / No.2 / No.3",
    "No. 3": "SS / No.1 / No.2 / No.3",
    "Stud": "Stud"
  };

  function sizeFactor(species, grade, nominal) {
    var sec = findSection(nominal);
    var m = /^(\d+)x(\d+)$/.exec(nominal || "");
    var width = m ? Number(m[2]) : null;

    /* The 14 in refusal comes FIRST. It used to sit behind the Southern Pine
       branch, so it fired for every species where holding C_F at 1.00 is
       conservative and was bypassed for the one family where the catalog says
       the size factor was never applied. */
    if (width !== null && width >= 14) {
      return { CF: 1, basis: "held", sourced: false, refuse: true,
               note: "Table 4A publishes a size factor below 1.00 at 14\" and wider and the catalog does not carry it — holding C_F at 1.00 would be unconservative (gap #1)" };
    }

    /* calc-spec §4.5: "The app must key off that flag, not off a species-name
       string match." Six Southern Pine Dense Structural records carry
       size_factor_applied: false, and a species-pool test called them sourced. */
    var rec = sec ? findValues(species, grade, sec.d_in, sec.b_in) : null;
    if (rec && rec.size_factor_applied === true) {
      return { CF: 1, basis: "table_4b", sourced: true, refuse: false,
               note: "size_factor_applied is true on this record — the size factor is already in the value" };
    }
    if (isSouthernPine(species) && !rec) {
      return { CF: 1, basis: "table_4b", sourced: true, refuse: false,
               note: "Table 4B is tabulated per width — the size factor is already in the value" };
    }
    var tbl = (window.MATDATA && MATDATA.size_factors_CF && MATDATA.size_factors_CF.partial_from_repo) || null;
    var row = tbl && tbl.by_grade_category && tbl.by_grade_category[CF_ROW[grade]];
    var cell = row && sec && row[nominal];

    /* the repo helper is the 2"-thick column only */
    if (cell && sec && Math.abs(sec.b_in - 1.5) < 0.01 && isFinite(cell.Fb)) {
      return { CF: cell.Fb, basis: "repo_partial", sourced: false, refuse: false,
               note: "repo threshold helper · " + (tbl.source_field || "") +
                     " · declared " + (tbl.declared_purpose || "threshold use only") };
    }
    return { CF: 1, basis: "held", sourced: false, refuse: false,
             note: sec && Math.abs(sec.b_in - 1.5) > 0.01
               ? "catalog covers the 2\"-thick column only — C_F held at 1.00, conservative for thicker stock"
               : "grade not covered by the catalog helper — C_F held at 1.00" };
  }

  /* ---------- beam stability, NDS §3.3.3 ---------- */

  function beamStability(lu_in, d, b, FbStar, EminPrime) {
    if (!lu_in || lu_in <= 0) {
      return { CL: 1, note: "Compression edge continuously braced — C_L = 1.0", RB: null };
    }
    var ratio = lu_in / d, le;
    if (ratio < 7) le = 2.06 * lu_in;
    else if (ratio <= 14.3) le = 1.63 * lu_in + 3 * d;
    else le = 1.84 * lu_in;

    var RB = Math.sqrt(le * d / (b * b));
    if (RB > 50) {
      return { CL: 0, RB: RB, invalid: true, note: "R_B = " + RB.toFixed(1) + " exceeds 50 — not permitted (§3.3.3.7)" };
    }
    var FbE = 1.20 * EminPrime / (RB * RB);
    var r = FbE / FbStar;
    var a = (1 + r) / 1.9;
    var CL = a - Math.sqrt(a * a - r / 0.95);
    return { CL: CL, RB: RB, FbE: FbE, le: le, ratio: ratio, note: null };
  }

  /* §2.3, the rule implementers get wrong: C_D for a combination is the factor
     of the SHORTEST-duration load PRESENT IN NONZERO MAGNITUDE, applied to the
     whole combination. A zero term must not set it — testing membership instead
     of magnitude gives the dead-only case C_D = 1.00 and an 11% overstatement.
     max() is correct because C_D rises monotonically as duration shortens.

     This lives at module scope and is EXPORTED because the sizing solver needs
     the same envelope to compute its seed bounds. It used to be duplicated
     there, guarded by a test that compared the two — and the moment this file
     went from four combinations to six, that test caught the drift. One
     implementation cannot drift from itself, which is better than catching it. */
  function comboCD(terms) {
    var pick = null;
    terms.forEach(function (t) {
      if (!(Math.abs(t.psf) > 0)) return;          /* zero magnitude → not present */
      if (!pick || t.cd.v > pick.v) pick = t.cd;
    });
    return pick || CD.dead;   /* every term zero: permanent, the longest duration */
  }
  function mkCombo(id, label, terms) {
    var psf = 0, live = 0;
    terms.forEach(function (t) { psf += t.psf; if (t.cd !== CD.dead) live += t.psf; });
    return { id: id, label: label, psf: psf, cd: comboCD(terms), live: live };
  }
  /* ASCE 7-22 §2.4.1, the six gravity-relevant basic ASD combinations. */
  function buildCombos(D, L, qLr, qS) {
    var tD = { psf: D, cd: CD.dead };
    return [
      mkCombo("D",            "D",                   [tD]),
      mkCombo("D+L",          "D + L",               [tD, { psf: L,  cd: CD.live }]),
      mkCombo("D+Lr",         "D + Lr",              [tD, { psf: qLr, cd: CD.roof_live }]),
      mkCombo("D+S",          "D + S",               [tD, { psf: qS,  cd: CD.snow }]),
      mkCombo("D+.75L+.75Lr", "D + 0.75L + 0.75Lr",  [tD, { psf: 0.75 * L,   cd: CD.live },
                                                           { psf: 0.75 * qLr, cd: CD.roof_live }]),
      mkCombo("D+.75L+.75S",  "D + 0.75L + 0.75S",   [tD, { psf: 0.75 * L,   cd: CD.live },
                                                           { psf: 0.75 * qS,  cd: CD.snow }])
    ];
  }

  /* ---------- the check ---------- */

  function run(inp) {
    var warnings = [];

    /* ---- input validation: never compute on garbage ---- */
    var span = Number(inp.span), spacing = Number(inp.spacing);
    var D = Number(inp.dead), L = Number(inp.live);
    if (!isFinite(D)) D = 0;
    if (!isFinite(L)) L = 0;

    function bad(msg) {
      return { error: true, message: msg, checks: [], warnings: warnings,
               governing: { name: "—", dcr: NaN, combo: "—" }, basis: "—" };
    }
    function given(x) { return x !== undefined && x !== null; }

    /* ---- roof loads: q_Lr and q_S are SEPARATE inputs (calc-spec §2.1) ----
       Snow and roof live are different durations (C_D 1.15 vs 1.25) and are NOT
       alternatives to be picked between up front: between roughly 17 and 20 psf
       roof snow, snow governs bending while roof live governs deflection, and
       collapsing them to one number cannot produce both. Both are carried and
       all six §2.1 combinations are enumerated.

       Backward compatibility: the legacy `roofLoad` + `roofType` pair is the
       single-load form of exactly this input. When neither new field is supplied
       it is routed into its typed bucket and the run is identical to before.

       Naming: `qLr` / `qS`, not `Lr` / `S`. Bare `S` in this function is the
       SECTION MODULUS (S = sec.Sx_in3, below) — a snow load called `S` shadows it
       and silently adds 21.39 psf to every snow combination on a 2x10. */
    var splitGiven = given(inp.roofLive) || given(inp.snow);
    var legacyType = inp.roofType === "roof_live" ? "roof_live" : "snow";
    var qLr, qS;
    if (splitGiven) {
      qLr = Number(inp.roofLive); qS = Number(inp.snow);
      if (!isFinite(qLr)) qLr = 0;
      if (!isFinite(qS)) qS = 0;
      /* A legacy roofLoad alongside the new fields is not dropped — dropping a
         supplied load silently is the one failure this file exists to prevent.
         It is added to its typed bucket and the doubling is announced. */
      var legacyPsf = Number(inp.roofLoad);
      if (isFinite(legacyPsf) && legacyPsf > 0) {
        if (legacyType === "roof_live") qLr += legacyPsf; else qS += legacyPsf;
        warnings.push("Both roofLoad (" + legacyPsf + " psf, " + legacyType +
          ") and the separate roofLive/snow inputs were supplied — roofLoad was ADDED to the " +
          (legacyType === "roof_live" ? "roof-live" : "snow") + " total, not ignored. " +
          "Supply one form or the other.");
      }
    } else {
      var one = Number(inp.roofLoad);
      if (!isFinite(one)) one = 0;
      qLr = legacyType === "roof_live" ? one : 0;
      qS  = legacyType === "roof_live" ? 0 : one;
    }

    if (!isFinite(span) || span <= 0) return bad("Span must be greater than zero.");
    if (!isFinite(spacing) || spacing <= 0) return bad("Spacing must be greater than zero.");
    if (D < 0 || L < 0 || qLr < 0 || qS < 0) return bad("Loads cannot be negative.");
    /* a load that arrived as NaN was coerced to 0 above — designing for no load
       is the one failure mode worse than refusing to design */
    if (!isFinite(Number(inp.dead)) && given(inp.dead))
      return bad("Dead load is not a number.");
    if (!isFinite(Number(inp.live)) && given(inp.live))
      return bad("Floor live load is not a number.");
    if (!isFinite(Number(inp.roofLoad)) && given(inp.roofLoad))
      return bad("Roof load is not a number.");
    if (!isFinite(Number(inp.roofLive)) && given(inp.roofLive))
      return bad("Roof live load is not a number.");
    if (!isFinite(Number(inp.snow)) && given(inp.snow))
      return bad("Snow load is not a number.");
    if (!DEFL[inp.memberUse] && inp.memberUse !== undefined)
      warnings.push("Unknown deflection row \"" + inp.memberUse + "\" — IBC floor limits assumed.");

    var sec = findSection(inp.size);
    if (!sec) return bad("No dimension-lumber section properties for " + inp.size + ". Timbers and beams & stringers are out of scope.");

    var d = sec.d_in, b = sec.b_in, A = sec.A_in2, S = sec.Sx_in3, I = sec.Ix_in4;

    var mat = findValues(inp.species, inp.grade, d, b);
    if (!mat) {
      return bad("No reference design values for " + inp.species + " " + inp.grade +
                 " at " + d.toFixed(2) + " in depth. That grade is not tabulated for this size class.");
    }
    var v = mat.values_psi;

    /* ---- C_F ----
       "auto" resolves C_F from the catalog for THIS depth. Anything that walks
       the depth ladder — the sizing solver, or a user stepping sizes on the
       sheet — must use it: a C_F typed for a 2x10 is simply wrong on a 2x6. */
    var CF, cfSrc = null;
    if (inp.CF === "auto") {
      cfSrc = sizeFactor(inp.species, inp.grade, inp.size);
      if (cfSrc.refuse) {
        return bad("C_F cannot be resolved for " + inp.size + " — " + cfSrc.note +
                   ". Enter C_F from NDS-S Table 4A to check this size.");
      }
      CF = cfSrc.CF;
      if (cfSrc.basis === "held") warnings.push("C_F held at 1.00 — " + cfSrc.note + ".");
    } else {
      CF = (inp.CF === undefined || inp.CF === null) ? 1 : Number(inp.CF);
      if (!isFinite(CF) || CF <= 0) { CF = 1; warnings.push("C_F was not a positive number — reset to 1.00."); }
    }

    var spFlag = isSouthernPine(inp.species);
    if (spFlag && CF !== 1) {
      CF = 1;
      warnings.push("Southern Pine (Table 4B) already incorporates the size factor — C_F forced to 1.00.");
    }

    /* ---- C_r, NDS §4.3.9: dimension lumber, 3+ members, ≤24 in o.c. ---- */
    var Cr = 1;
    if (inp.repetitive) {
      if (spacing > 24) warnings.push("Repetitive-member factor not applied: spacing exceeds 24 in o.c. (§4.3.9).");
      else if (b > 4) warnings.push("Repetitive-member factor not applied: member thicker than 4 in (§4.3.9).");
      else Cr = 1.15;
    }

    /* ---- C_M, with the Table 4A threshold exception ---- */
    var wet = !!inp.wet;
    var CM = {
      /* The threshold is tested on the LARGEST C_F the cell could take whenever
         C_F is held, because 1.00 is not the conservative choice here — a bigger
         C_F pushes the product over 1150 and costs the exception. */
      Fb: wet ? (v.Fb * (cfSrc && cfSrc.basis === "held" ? 1.5 : CF) <= 1150 ? 1.00 : CM_WET.Fb) : 1,
      Fv: wet ? CM_WET.Fv : 1,
      Fc_perp: wet ? CM_WET.Fc_perp : 1,
      E: wet ? CM_WET.E : 1,
      Emin: wet ? CM_WET.Emin : 1
    };
    var CMnote = wet
      ? (v.Fb * CF <= 1150 ? "MC > 19% · (F_b)(C_F) ≤ 1150 → C_M = 1.0" : "MC > 19% · Table 4A")
      : "dry service";

    var incised = !!inp.incised;
    var Ci = incised ? CI : { Fb: 1, Ft: 1, Fv: 1, Fc: 1, E: 1, Emin: 1, Fc_perp: 1 };
    var CiNote = incised ? "incised · Table 4.3.8" : "not incised";

    var Ct = 1;                                   /* NDS Table 2.3.3, normal temperature */
    var Cb = 1;                                   /* end bearing — §3.10.4 does not apply */

    var Eprime = v.E * CM.E * Ct * Ci.E;
    var EminPrime = v.Emin * CM.Emin * Ct * Ci.Emin;

    /* ---- load combinations, ASCE 7-22 §2.4.1 (calc-spec §2.1) ----
       All SIX gravity combinations are enumerated unconditionally. A combination
       that reduces to a duplicate (D + L when q_L = 0 is numerically D alone) is
       still evaluated: §2.3 gives it the right C_D and the envelope in §6 discards
       it on its merits, not by a special case. Suppressing it instead is how
       D + Lr and D + S stopped being evaluatable in the same run. */

    var combos = buildCombos(D, L, qLr, qS);

    var checks = [];
    var strength = { name: "—", dcr: -Infinity, combo: "—" };
    var service  = { name: "—", dcr: -Infinity, combo: "—" };

    function consider(name, dcr, combo, lines, detail, kind) {
      checks.push({ name: name, dcr: dcr, combo: combo, lines: lines, detail: detail || null, kind: kind });
      /* A non-finite STRENGTH ratio is a failure, not an absence. Skipping it
         here let a member with zero bending capacity report PASS on deflection. */
      if (!isFinite(dcr)) {
        if (kind !== "service") {
          var t0 = strength;
          if (!isFinite(t0.dcr) || t0.dcr < Infinity) { t0.name = name; t0.dcr = Infinity; t0.combo = combo; }
        }
        return;
      }
      var tgt = kind === "service" ? service : strength;
      if (dcr > tgt.dcr) {
        tgt.name = name; tgt.dcr = dcr; tgt.combo = combo;
      }
    }

    /* ---------- bending ---------- */
    var best = null, invalidStability = null;
    combos.forEach(function (c) {
      var w = c.psf * spacing / 12;
      var M = w * span * span / 8;
      var fb = M * 12 / S;
      var FbStar = v.Fb * c.cd.v * CM.Fb * Ct * Ci.Fb * CF * Cr;
      var stab = beamStability(inp.braced ? 0 : span * 12, d, b, FbStar, EminPrime);
      var Fbp = FbStar * stab.CL;
      var dcr = Fbp > 0 ? fb / Fbp : Infinity;
      if (stab.invalid) invalidStability = stab;
      if (!best || dcr > best.dcr) best = { dcr: dcr, combo: c.label, w: w, M: M, fb: fb, Fbp: Fbp, cd: c.cd, stab: stab };
    });

    /* NDS §3.3.3.7 — R_B may not exceed 50. That is a prohibition, not a low
       capacity: the member is not permitted and the app must say so rather than
       return an infinite DCR that the governing-case selection then drops. */
    if (invalidStability) {
      return bad("Not permitted — " + invalidStability.note +
                 ". Reduce the unbraced length, or increase the breadth.");
    }

    consider("Bending", best.dcr, best.combo, [
      "w = " + f(best.w, 1) + " plf",
      "M = wL²/8 = " + f(best.M, 0) + " lb-ft = " + f(best.M * 12, 0) + " lb-in",
      "f_b = M/S = " + f(best.M * 12, 0) + " / " + f(S, 2) + " = " + f(best.fb, 0) + " psi",
      "F_b′ = " + f(v.Fb, 0) + " × C_D " + f(best.cd.v, 2) + " × C_M " + f(CM.Fb, 2) +
        " × C_t " + f(Ct, 2) + " × C_i " + f(Ci.Fb, 2) + " × C_L " + f(best.stab.CL, 3) + " × C_F " + f(CF, 2) +
        " × C_r " + f(Cr, 2) + " = " + f(best.Fbp, 0) + " psi",
      "DCR = " + f(best.fb, 0) + " / " + f(best.Fbp, 0) + " = " + f(best.dcr, 3)
    ], {
      factors: [
        { k: "F_b (reference)", v: comma(v.Fb) + " psi", cite: mat.size_class, src: true },
        { k: "× C_D · load duration", v: f(best.cd.v, 2), cite: "Table 2.3.2 · " + best.cd.label },
        { k: "× C_M · wet service", v: f(CM.Fb, 2), cite: CMnote },
        { k: "× C_t · temperature", v: f(Ct, 2), cite: "Table 2.3.3 · normal" },
        { k: "× C_i · incising", v: f(Ci.Fb, 2), cite: CiNote },
        { k: "× C_L · beam stability", v: f(best.stab.CL, 3), cite: best.stab.note || ("§3.3.3 · R_B " + f(best.stab.RB, 1)) },
        { k: "× C_F · size factor", v: f(CF, 2),
          cite: spFlag ? "built into Table 4B" : (cfSrc ? cfSrc.note : "typed — not in catalog"),
          typed: !spFlag && (!cfSrc || cfSrc.basis === "held"),
          src: spFlag || (cfSrc && cfSrc.basis === "repo_partial") },
        { k: "× C_r · repetitive", v: f(Cr, 2), cite: Cr > 1 ? "§4.3.9" : "not applied" },
        { k: "F_b′ (adjusted)", v: comma(best.Fbp) + " psi", total: true },
        { k: "f_b (applied)", v: comma(best.fb) + " psi" }
      ]
    }, "strength");

    /* ---------- shear ---------- */
    var sh = null;
    combos.forEach(function (c) {
      var w = c.psf * spacing / 12;
      var V = w * span / 2;
      var fv = 1.5 * V / A;
      var Fvp = v.Fv * c.cd.v * CM.Fv * Ct * Ci.Fv;
      var dcr = fv / Fvp;
      if (!sh || dcr > sh.dcr) sh = { dcr: dcr, combo: c.label, V: V, fv: fv, Fvp: Fvp, cd: c.cd };
    });

    consider("Shear", sh.dcr, sh.combo, [
      "V = wL/2 = " + f(sh.V, 0) + " lb  (taken at the support; no §3.4.3.1 reduction to d)",
      "f_v = 1.5V/A = " + f(sh.fv, 1) + " psi",
      "F_v′ = " + f(v.Fv, 0) + " × C_D " + f(sh.cd.v, 2) + " × C_M " + f(CM.Fv, 2) + " × C_i " + f(Ci.Fv, 2) + " = " + f(sh.Fvp, 0) + " psi",
      "DCR = " + f(sh.dcr, 3)
    ], {
      factors: [
        { k: "F_v (reference)", v: comma(v.Fv) + " psi", cite: "Table 4A", src: true },
        { k: "× C_D", v: f(sh.cd.v, 2), cite: "Table 2.3.2" },
        { k: "× C_M", v: f(CM.Fv, 2), cite: wet ? "MC > 19%" : "dry service" },
        { k: "× C_i", v: f(Ci.Fv, 2), cite: CiNote },
        { k: "F_v′", v: comma(sh.Fvp) + " psi", total: true },
        { k: "f_v (applied)", v: f(sh.fv, 1) + " psi" }
      ]
    }, "strength");

    /* ---------- deflection (serviceability) ----------
       calc-spec §5.5 load sets. The variable-load column takes the ROOF SLOT as
       max(q_Lr, q_S), never the sum: snow and roof live are alternative occupancies
       of the same roof, so adding them designs for a load that cannot occur. Floor
       live is a different tributary and DOES coexist with a roof load, so q_L adds
       — that is the mixed roof+floor header (weights.js `carries: "roof+floor"`),
       which §5.5's floor/roof branch does not name. On a pure floor member
       (q_Lr = q_S = 0) and a pure roof member (q_L = 0) this is §5.5 exactly.

       No C_D here: deflection uses E′, and C_D never touches E (§2.2). */
    var use = DEFL[inp.memberUse] || DEFL.floor;
    var L_in = span * 12;
    var qRoof = Math.max(qLr, qS);
    var qVar = L + qRoof;                              /* psf — variable column */
    var wLive = qVar * spacing / 12 / 12;              /* lb/in */
    var wTot = (D + qVar) * spacing / 12 / 12;

    /* name the load set that actually drives the check, per §6.3's per-limit-state
       table ("Deflection (S) | S alone"), rather than the generic word "variable" */
    var varNames = [];
    if (L > 0) varNames.push("L");
    if (qRoof > 0) varNames.push(qLr >= qS ? "Lr" : "S");
    var varLabel = varNames.length ? varNames.join(" + ") + " alone" : "variable load";
    var totLabel = varNames.length ? "D + " + varNames.join(" + ") : "D + variable";
    var dL = 5 * wLive * Math.pow(L_in, 4) / (384 * Eprime * I);
    var dT = 5 * wTot * Math.pow(L_in, 4) / (384 * Eprime * I);
    var aL = L_in / use.live, aT = L_in / use.total;

    consider("Deflection (live)", dL / aL, varLabel, [
      "Δ_L = 5wL⁴/(384 E′I) = " + f(dL, 3) + " in",
      "allowable = L/" + use.live + " = " + f(aL, 3) + " in",
      "actual = L/" + f(L_in / dL, 0),
      "DCR = " + f(dL / aL, 3)
    ], {
      factors: [
        { k: "E (reference)", v: comma(v.E) + " psi", cite: "Table 4A", src: true },
        { k: "× C_M", v: f(CM.E, 2), cite: wet ? "MC > 19%" : "dry service" },
        { k: "E′", v: comma(Eprime) + " psi", total: true },
        { k: "I", v: f(I, 2) + " in⁴", cite: "Table 1B", src: true },
        { k: "Allowable L/" + use.live, v: f(aL, 3) + " in", cite: use.cite }
      ]
    }, "service");

    consider("Deflection (total)", dT / aT, totLabel, [
      "Δ_TL = " + f(dT, 3) + " in",
      "allowable = L/" + use.total + " = " + f(aT, 3) + " in",
      "DCR = " + f(dT / aT, 3)
    ], {
      factors: [
        { k: "Δ_TL", v: f(dT, 3) + " in" },
        { k: "Allowable L/" + use.total, v: f(aT, 3) + " in", cite: use.totalCite || use.cite },
        { k: "Creep K_cr", v: "not applied", cite: "§3.5.2 — see scope" }
      ]
    }, "service");

    /* ---------- bearing ---------- */
    var lb = Number(inp.bearing);
    if (!isFinite(lb) || lb <= 0) { lb = 1.5; warnings.push("Bearing length was not a positive number — assumed 1.50 in."); }
    var R = 0, Rc = "—";
    combos.forEach(function (c) {
      var r = (c.psf * spacing / 12) * span / 2;
      if (r > R) { R = r; Rc = c.label; }
    });
    var fcp = R / (b * lb);
    var Fcpp = v.Fc_perp * CM.Fc_perp * Ct * Ci.Fc_perp * Cb;

    consider("Bearing (Fc⊥)", fcp / Fcpp, Rc, [
      "R = " + f(R, 0) + " lb on " + f(lb, 2) + " in of bearing",
      "f_c⊥ = R/(b·l_b) = " + f(R, 0) + " / (" + f(b, 3) + " × " + f(lb, 2) + ") = " + f(fcp, 0) + " psi",
      "F_c⊥′ = " + f(v.Fc_perp, 0) + " × C_M " + f(CM.Fc_perp, 2) + " × C_b " + f(Cb, 2) + " = " + f(Fcpp, 0) + " psi",
      "DCR = " + f(fcp / Fcpp, 3)
    ], {
      factors: [
        { k: "F_c⊥ (reference)", v: comma(v.Fc_perp) + " psi", cite: "Table 4A", src: true },
        { k: "× C_M", v: f(CM.Fc_perp, 2), cite: wet ? "MC > 19%" : "dry service" },
        { k: "× C_b · bearing length", v: f(Cb, 2), cite: "§3.10.4 does not apply at a member end" },
        { k: "C_D", v: "not applicable", cite: "Table 4.3.1" },
        { k: "F_c⊥′", v: comma(Fcpp) + " psi", total: true }
      ]
    }, "strength");

    /* ---------- governing ---------- */
    var anyFinite = checks.some(function (c) { return isFinite(c.dcr); });
    if (!anyFinite) return bad("The check could not be evaluated with these inputs.");

    var governing = (service.dcr > strength.dcr)
      ? { name: service.name, dcr: service.dcr, combo: service.combo, kind: "service" }
      : { name: strength.name, dcr: strength.dcr, combo: strength.combo, kind: "strength" };

    return {
      error: false,
      section: sec, material: mat, checks: checks, warnings: warnings,
      governing: governing,
      strength: strength, service: service,
      basis: "NDS 2024 ASD · ASCE 7 §2.4 · " + use.cite,
      combos: combos.map(function (c) { return { label: c.label, cd: c.cd.v, cdLabel: c.cd.label, psf: c.psf }; }),
      Eprime: Eprime, EminPrime: EminPrime
    };
  }

  function f(n, d) {
    if (n === null || n === undefined || !isFinite(n)) return "—";
    return Number(n).toFixed(d === undefined ? 2 : d);
  }
  function comma(n) {
    if (n === null || n === undefined || !isFinite(n)) return "—";
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  FM.engine = {
    run: run, LIMITS: LIMITS, DEFL: DEFL,
    speciesList: speciesList, sizeList: sizeList,
    findSection: findSection, findValues: findValues,
    isSouthernPine: isSouthernPine, sizeFactor: sizeFactor, CD: CD,
    buildCombos: buildCombos
  };
})();
