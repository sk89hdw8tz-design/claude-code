/* ============================================================
   Model weights, regional packs, and repeatable tract-home plans.

   READ THIS BEFORE TRUSTING A NUMBER IN THIS FILE.

   Everything here falls into exactly one of three classes, and every
   record says which class it is in:

     code     A code or standard value (ASCE 7, IBC, IRC, NDS).
              Reproduced with its citation. Never invented.
     site     SITE-SPECIFIC and unknowable from a state name — ground
              snow, basic wind speed, exposure, seismic. What is
              carried here is a PLANNING DEFAULT for laying out a
              repeatable plan. Replace it with the ASCE 7 Hazard Tool
              / AHJ value before anything is stamped.
     market   A commercial preference weight — price, availability,
              labor, the cost of another SKU, dead-load takeoffs.
              No code standing at all. The firm's numbers. Placeholders.

   The safety invariant, enforced by test:

       No weight in this file can make a member pass.

   Feasibility is decided only by FM.engine.run() against the firm's
   DCR target. The weights choose among members that already passed.
   ============================================================ */

(function () {
  "use strict";

  /* ---------------- the weight vocabulary ----------------
     Every term is in dollars, so scores are comparable across regions
     and across candidate sets. A weight with no unit is one nobody can
     argue with, which is worse than one that is wrong. */

  var BASE = {
    id: "base",
    name: "Firm baseline",
    weights: {
      /* material */
      material:        1.00,   /* multiplier on lumber cost                                    [market] */
      baseBfUSD:       0.70,   /* $/board-foot fallback when a pack does not price a species   [market] */
      dropHandling:    0.15,   /* the offcut is already paid for in the stick — this prices
                                  sorting, stacking and disposing of it, net of salvage. It is
                                  NOT an estimating waste factor and must not be set to 1.10   [market] */

      /* labor — a lanai beam and a floor joist are not the same job */
      laborPerPiece:   3.50,   /* $/piece, fallback                                            [market] */
      laborPerPieceByRole: {
        joist: 3.50, rafter: 3.50, ceiling: 3.25,
        deck: 5.50,            /* treated, heavier, on hangers, outdoors                      [market] */
        header: 18.00,         /* two people, in a wall, with cripples and a king stud         [market] */
        beam: 45.00            /* exterior, elevated, often into a post cap                    [market] */
      },
      laborPerLb:      0.060,  /* $/lb handled. A 4x12x16 SYP is ~153 lb — a three-man lift    [market] */

      /* what structural depth costs downstream */
      depthPerInchSf:  0.020,  /* $/sf per inch, fallback                                      [market] */
      depthPerInchSfByRole: {
        joist:   0.100,        /* floor depth is building height: siding, brick, drywall       [market] */
        deck:    0.010,        /* a deck's depth costs a rim board and nothing else            [market] */
        rafter:  0.010,
        ceiling: 0.005,
        header:  0.000,        /* replaced by the hard maxDepthIn constraint — see MARKS       [market] */
        beam:    0.010
      },

      /* supply */
      stockPenaltySf:  1.00,   /* $/sf at zero availability, prorated. Sized to beat the
                                  material delta between adjacent rungs, so a stocked deeper
                                  member wins over an unstocked shallower one                  [market] */

      /* engineering risk */
      unsourcedCF:     5.00,   /* $/member when C_F is held at 1.00. Deliberately small: the
                                  catalog happens to cover 2"-thick non-Southern-Pine only, so
                                  a large value would tilt the answer toward Southern Pine as
                                  an artifact of catalog coverage rather than economics        [market] */

      /* right-sizing */
      slackPenalty:    3.00,   /* $ per unit of unused capacity fraction. Small on purpose —
                                  slack is insurance for the tile-roof option on lot 47        [market] */

      /* repeatability */
      skuPenalty:     40.00    /* $ PER HOUSE per distinct SKU carried on the plan. Decomposed:
                                  yard band-and-sort $15–40, extra jobsite stack $12–25,
                                  mis-pick remedy 1–3% x $40–150. An off-platform SKU costs an
                                  order of magnitude more and is priced through availability
                                  instead — see STOCK                                          [market] */
    },
    maxDCR: 0.90,
    minAvailability: 0.10,     /* HARD FLOOR — below this the member cannot be the pick at all.
                                  Set low on purpose. A floor of 0.35 measured against STOCK.dry
                                  silently excluded every dry 4x in every pack, which turned a
                                  placeholder market number into what looked like an engineering
                                  finding: the flagship plan reported "no solid-sawn solution" for
                                  a garage header that in fact passes at DCR 0.90. Refusing to
                                  answer is not the same as answering that it is a special order.
                                  Raise it deliberately if your firm wants the harder rule  [market] */
    specialOrderBelow: 0.35,   /* not a gate — a LABEL. A pick under this is flagged as a special
                                  order on the schedule, with its availability shown         [market] */
    gammaPcf: 35               /* calc-spec §1.3 — assumption, editable, not a sourced density */
  };

  /* ---------------- treated-species incising ----------------
     NDS Table 4.3.8 gives C_i = 0.80 on F_b, F_t, F_v and F_c for incised
     lumber, and engine.js now IMPLEMENTS it. Refractory species must be incised
     to take preservative, so a treated mark in one is checked WITH the factor —
     0.80 on F_b/F_t/F_v/F_c and 0.95 on E. This map is what tells the solver
     which species that applies to. It was once an exclusion gate; the gate keyed
     on moisture rather than treatment, which meant a price change could route
     around it, so the containment became the calculation. Southern Pine takes
     treatment without incising and is unaffected — which is why it is the
     porch-beam species of the entire Southeast. */
  var INCISED_WHEN_TREATED = {
    "Douglas Fir-Larch": true,
    "Douglas Fir-Larch (North)": true,
    "Douglas Fir-South": true,
    "Hem-Fir": true,
    "Hem-Fir (North)": true,
    "Spruce-Pine-Fir": true,
    "Spruce-Pine-Fir (South)": true
  };

  /* ---------------- load presets ----------------
     Assemblies a production builder repeats. psf on the horizontal projection
     (calc-spec §1.4). Dead-load takeoffs are [market] values, not code. */

  var ASSEMBLY = {
    roof_shingle: {
      psf: 15, label: "Asphalt shingle roof", cls: "market",
      makeup: "architectural shingle 2.5–3.0 psf, felt, 7/16 OSB, framing, R-38 blown, 1/2 in gypsum ceiling"
    },
    roof_tile: {
      psf: 22, label: "Concrete tile roof", cls: "market",
      makeup: "concrete tile 9–11 psf on battens, underlayment, 19/32 sheathing, framing, insulation, gypsum ceiling",
      note: "Tile is the largest gravity difference between a Florida plan and the same plan in Texas. " +
            "It moves a 12 ft lanai beam from a 4x10 to a 4x12 on its own."
    },
    roof_metal: {
      psf: 12, label: "Standing-seam / 5V metal roof", cls: "market",
      makeup: "26 ga metal 1.0–1.5 psf, underlayment, sheathing, framing, insulation, gypsum ceiling"
    },
    floor_res: {
      psf: 12, label: "Residential floor", cls: "market",
      makeup: "3/4 in sheathing, framing, 1/2 in gypsum below, light finish; no tile or mortar bed"
    },
    ceiling_attic: {
      psf: 10, label: "Gypsum ceiling, attic above", cls: "market",
      makeup: "1/2 in gypsum, ceiling framing, blown insulation"
    },
    roof_open: {
      psf: 10, label: "Open porch / lanai roof", cls: "market",
      makeup: "shingle or tile over sheathing and framing, exposed or vented soffit — no ceiling, no insulation",
      note: "A porch beam whose deflection row is 'no ceiling' cannot also be carrying a gypsum " +
            "ceiling and R-38 in its dead load. The enclosed-roof assembly is the wrong one here."
    },
    roof_open_tile: {
      psf: 17, label: "Open porch / lanai roof, concrete tile", cls: "market",
      makeup: "concrete tile 9-11 psf on battens over sheathing and framing — no ceiling, no insulation"
    },
    floor_wet: {
      psf: 22, label: "Residential floor, tiled wet area", cls: "market",
      makeup: "ceramic tile on backer with thinset (+10 psf) over 3/4 in sheathing, framing, gypsum below",
      note: "A bath or laundry bay carrying floor_res (which says 'no tile or mortar bed') is checked " +
            "31% light, and it is the bay a floor-depth unification decision is made on."
    },
    deck_pt: {
      psf: 10, label: "Pressure-treated deck", cls: "market",
      makeup: "5/4 or 2x PT decking on PT framing, no ceiling below"
    }
  };

  /* Live loads are code values and are reproduced as such. */
  var LIVE = {
    floor_residential: { psf: 40, cls: "code", cite: "IRC Table R301.5 / IBC Table 1607.1 — dwelling, rooms other than sleeping" },
    floor_sleeping:    { psf: 30, cls: "code", cite: "IRC Table R301.5 — sleeping rooms" },
    attic_no_storage:  { psf: 10, cls: "code", cite: "IRC Table R301.5 — uninhabitable attics without storage" },
    attic_storage:     { psf: 20, cls: "code", cite: "IRC Table R301.5 — uninhabitable attics with limited storage" },
    /* ---- the deck live load: 60, not 40 ----------------------------------
       This carried 40 psf, cited to IRC R507, and the review left it open as
       "answer it; do not carry it." Answered.

       The two codes do not agree, and the disagreement is real:

         IBC Table 1607.1 and ASCE 7-22 Table 4.3-1 both say a balcony or deck
         takes 1.5 × the live load of the occupancy served, not required to
         exceed 100 psf. A dwelling area is 40, so a residential deck is 60.

         IRC Table R301.5 lists decks at 40 and the R507 prescriptive span
         tables are built on 40 live + 10 dead.

       The defect was never that 40 is an indefensible number. It is that this
       engine is on the IBC/ASCE path in every other respect — ASCE 7-22 §2.4.1
       for the combinations, IBC Table 1604.3 for deflection — and was reaching
       across to the IRC for one load. Mixing code paths inside a single
       calculation is not a conservative choice or an unconservative one; it is
       an uncheckable one, because no single code produces the result.

       So the engine uses 60 and says which code it came from. The IRC number
       is kept below, unused, so a project actually permitted under the IRC's
       prescriptive deck provisions can see the number it would use and see
       that this engine did not use it.

       This is not free: at 60 psf the deck members that used to print clean go
       overstressed, so the search resizes them, and where it cannot it
       escalates. That is the honest consequence of the answer and it is
       supposed to show. */
    deck:              { psf: 60, cls: "code",
                         cite: "IBC Table 1607.1 / ASCE 7-22 Table 4.3-1 — balconies and decks, " +
                               "1.5 × the 40 psf of the dwelling area served",
                         note: "The IRC's prescriptive deck provisions (Table R301.5, R507) use " +
                               "40 psf. This engine is on the IBC/ASCE path throughout, so it uses " +
                               "60 psf; a project permitted under the IRC prescriptive path should " +
                               "be checked against that path in full, not by substituting one load." },
    deck_irc:          { psf: 40, cls: "code", used: false,
                         cite: "IRC Table R301.5 / R507 — exterior decks and balconies, prescriptive path",
                         note: "NOT USED by this engine. Carried so the difference from the IBC/ASCE " +
                               "value above is visible rather than buried in a choice nobody recorded." },
    roof_live:         { psf: 20, cls: "code", cite: "ASCE 7-22 §4.8.2 — minimum roof live load, unreduced (calc-spec §8.13 takes no reduction)" }
  };

  /* ---------------- stock reality ----------------
     Availability is a property of the SKU and of the treatment channel, not of
     the species. Dimensional 2x is racked everywhere. A DRY 4x header is a
     timber-yard special order in every one of these six markets. A TREATED 4x
     is the standard Southeast porch beam and is stocked.

     This distinction is the single thing that makes the output buyable, and it
     is why the same 4x10 is a normal purchase on a lanai and a special order in
     an interior wall. All [market], all estimates, all replaceable. */
  var STOCK = {
    dry: {
      "2x4": 1.00, "2x6": 1.00, "2x8": 1.00, "2x10": 1.00, "2x12": 0.95,
      "4x6": 0.45, "4x8": 0.30, "4x10": 0.18, "4x12": 0.15
    },
    wet: {
      "2x4": 0.90, "2x6": 0.95, "2x8": 0.95, "2x10": 0.95, "2x12": 0.85,
      "4x6": 0.90, "4x8": 0.85, "4x10": 0.85, "4x12": 0.80
    },
    note: "Dry 4x is a special order in all six markets; treated 4x is the standard porch beam. " +
          "The market's answer to an interior header is a 2-ply 2x, which calc-spec §8.6 puts out of scope."
  };

  /* ---------------- regional packs ---------------- */

  var PACKS = [

    {
      id: "tx-i35",
      name: "Texas · I-35 corridor",
      markets: "DFW · Austin · San Antonio",
      states: ["TX"],
      code: {
        family: "IRC", cls: "code",
        note: "Texas Local Government Code (HB 738, 2021) sets the 2012 IBC/IRC as the statewide municipal " +
              "floor; home-rule cities routinely adopt newer editions by ordinance, and unincorporated county " +
              "often has no adopted code at all. A Texas pack must be keyed to the CITY, not the state. " +
              "VERIFY the adopted edition for the jurisdiction.",
        deflectionTable: "IRC Table R301.7 governs one- and two-family dwellings. The engine's deflection rows " +
                         "are IBC Table 1604.3 rows and are a firm overlay where the IRC governs — the IRC has " +
                         "no total-load column for a rafter at all."
      },
      climate: {
        groundSnow:  { v: 5,   cls: "site", note: "Planning default. ASCE 7-22 remapped the South; any pre-2022 number is stale." },
        roofLive:    { v: 20,  cls: "code", note: LIVE.roof_live.cite },
        windMph:     { v: 115, cls: "site", note: "Risk Category II planning value. Look up the site." },
        exposure:    { v: "B", cls: "site", note: "A fetch determination per ASCE 7 §26.7, not a regional constant." },
        sdc:         { v: "A", cls: "site", note: "Seismic does not govern residential wood framing here." }
      },
      governs: "gravity",
      foundation: "slab-on-grade",
      exteriorWall: "wood",
      roofFraming: "truss",
      service: { wet: false, exteriorWet: false,
                 note: "Enclosed framing is dry service. Covered porch framing is treated for ground/masonry " +
                       "clearance per IRC R317 but is not sustained above 19% MC in this climate." },
      loads: {
        roofAssembly: "roof_shingle", floorAssembly: "floor_res", ceilingAssembly: "ceiling_attic",
        roofLoad: 20, roofType: "roof_live",
        roofLoadBasis: "Snow does not govern. Roof snow only overtakes the 20 psf roof live load once " +
                       "p_s exceeds 20 x 1.15/1.25 = 18.4 psf — about 26 psf ground snow — and Texas is " +
                       "nowhere near it. Lr = 20 psf, C_D = 1.25.",
        floorLive: LIVE.floor_residential.psf, ceilingLive: LIVE.attic_no_storage.psf,
        deckLive: LIVE.deck.psf
      },
      plateHeightIn: 109.125,      /* 9'-1-1/8" precut first floor  [market] */
      palette: [
        { species: "Southern Pine", grade: "No.2", bfUSD: 0.70, stockFactor: 1.00, cullRate: 0.03,
          note: "Regional staple. SPIB mills in freight range; takes treatment without incising." },
        { species: "Southern Pine", grade: "No.1", bfUSD: 0.86, stockFactor: 0.85, cullRate: 0.03,
          note: "Step up a grade before changing species." },
        { species: "Spruce-Pine-Fir", grade: "No. 1/No. 2", bfUSD: 0.74, stockFactor: 0.85, cullRate: 0.02,
          note: "Widely stocked in Texas. Canadian duty and the 2025 Section 232 tariff move this price — verify." },
        { species: "Douglas Fir-Larch", grade: "No. 2", bfUSD: 0.92, stockFactor: 0.50, cullRate: 0.015,
          note: "Long-haul from the PNW. Buys about 17 in of joist span over Southern Pine when it is worth the freight." }
      ],
      maxDCR: 0.90
    },

    {
      id: "tx-gulf",
      name: "Texas · Gulf Coast",
      markets: "Houston · Beaumont · Corpus Christi",
      states: ["TX"],
      code: { family: "IRC", cls: "code",
        note: "As tx-i35, plus windstorm requirements near the coast (TDI/TWIA certification). VERIFY the city's adopted edition." },
      climate: {
        groundSnow:  { v: 0,   cls: "site", note: "No snow load." },
        roofLive:    { v: 20,  cls: "code", note: LIVE.roof_live.cite },
        windMph:     { v: 140, cls: "site", note: "140–145 inland, 150–160+ at the coast, windborne-debris region. Look up the site." },
        exposure:    { v: "C", cls: "site", note: "D within roughly 600 ft of open shoreline." },
        sdc:         { v: "A", cls: "site" }
      },
      governs: "wind",
      governsNote: "On this coast the connections are governed by uplift, not by gravity, and the member often is too. " +
                   "This engine checks gravity only (calc-spec §8.11) and designs no connection of any kind (§8.17). " +
                   "A gravity-passing rafter here is not a finished design.",
      foundation: "slab-on-grade",
      exteriorWall: "wood",
      roofFraming: "truss",
      service: { wet: false, exteriorWet: true,
                 note: "Open porch and carport framing is treated as wet service. Sustained MC above 19% is realistic here." },
      loads: {
        roofAssembly: "roof_shingle", floorAssembly: "floor_res", ceilingAssembly: "ceiling_attic",
        roofLoad: 20, roofType: "roof_live",
        roofLoadBasis: "No snow load anywhere on this coast, so the D + S combination is not formed and C_D = 1.15 " +
                       "never appears. Lr = 20 psf unreduced, C_D = 1.25 per NDS Table 2.3.2 seven-day duration.",
        floorLive: LIVE.floor_residential.psf, ceilingLive: LIVE.attic_no_storage.psf,
        deckLive: LIVE.deck.psf
      },
      plateHeightIn: 109.125,
      palette: [
        { species: "Southern Pine", grade: "No.2", bfUSD: 0.66, stockFactor: 1.00, cullRate: 0.035,
          note: "Mills are close. The only species here that takes treatment without incising." },
        { species: "Southern Pine", grade: "No.1", bfUSD: 0.82, stockFactor: 0.85, cullRate: 0.035 },
        { species: "Spruce-Pine-Fir", grade: "No. 1/No. 2", bfUSD: 0.78, stockFactor: 0.60, cullRate: 0.02,
          note: "Checked with C_i = 0.80 on treated marks (NDS Table 4.3.8) — it must be incised to take preservative." }
      ],
      maxDCR: 0.90
    },

    {
      id: "nc-piedmont",
      name: "North Carolina · Piedmont",
      markets: "Charlotte · Raleigh · Greensboro",
      states: ["NC"],
      code: { family: "IRC", cls: "code",
        /* This note used to end at "delayed by statute to 1 July 2025", which
           was true when written and had been superseded twice by the time
           anyone read it. It said VERIFY, so it was not a lie — but a reader
           came away believing a 2021-IRC basis governs North Carolina, and the
           basis is 2015 IRC with ASCE 7-10. Two code generations back, on the
           reference this engine's own combinations are built against.

           A "VERIFY" on a stale sentence is not a disclaimer. It is a wrong
           answer with a footnote. */
        note: "North Carolina Residential Code, adopted statewide by the Building Code Council — local jurisdictions " +
              "do not write their own technical amendments. IN FORCE: the 2018 NCRC, on a 2015 IRC basis, which " +
              "references ASCE 7-10 — NOT 7-16 and NOT 7-22. The 2024 NCRC was delayed by S.L. 2024-57 to 1 July 2025, " +
              "then delayed again by S.L. 2025-2 until 12 months after the State Fire Marshal certifies both " +
              "publication and a fully constituted Residential Code Council; as of 15 Feb 2026 neither had happened " +
              "and the earliest possible effective date stated was 1 March 2027. VERIFY the effective edition and any " +
              "permit-date grandfathering with OSFM before this is used." },
      climate: {
        groundSnow:  { v: 15,  cls: "site", note: "Piedmont counties commonly 10–15 psf; the NCRC county table governs." },
        roofLive:    { v: 20,  cls: "code", note: LIVE.roof_live.cite },
        windMph:     { v: 115, cls: "site" },
        exposure:    { v: "B", cls: "site" },
        sdc:         { v: "B", cls: "site" }
      },
      governs: "gravity",
      foundation: "mixed slab / crawlspace",
      exteriorWall: "wood",
      roofFraming: "truss",
      service: { wet: false, exteriorWet: true,
                 note: "A vented or conditioned crawlspace stays under 19% MC, so crawlspace floor framing is DRY service. " +
                       "Only the sill plate and framing within the IRC R317 clearance need treatment." },
      loads: {
        roofAssembly: "roof_shingle", floorAssembly: "floor_res", ceilingAssembly: "ceiling_attic",
        roofLoad: 20, roofType: "roof_live",
        roofLoadBasis: "At 15 psf ground snow the flat-roof snow load is about 10.5 psf, well under the 20 psf roof " +
                       "live load, so Lr governs and C_D stays at 1.25. Declaring this pack as snow would be " +
                       "UNCONSERVATIVE by 8.7%: it would apply C_D = 1.15 to a smaller load. VERIFY p_g per county — " +
                       "snow takes over above roughly 26 psf ground snow.",
        floorLive: LIVE.floor_residential.psf, ceilingLive: LIVE.attic_no_storage.psf,
        deckLive: LIVE.deck.psf
      },
      plateHeightIn: 109.125,
      palette: [
        { species: "Southern Pine", grade: "No.2", bfUSD: 0.68, stockFactor: 1.00, cullRate: 0.03,
          note: "Home market for SPIB material." },
        { species: "Southern Pine", grade: "No.1", bfUSD: 0.84, stockFactor: 0.85, cullRate: 0.03 },
        { species: "Spruce-Pine-Fir", grade: "No. 1/No. 2", bfUSD: 0.80, stockFactor: 0.55, cullRate: 0.02 }
      ],
      maxDCR: 0.90
    },

    {
      id: "nc-mountain",
      name: "North Carolina · Mountains",
      markets: "Asheville · Boone · Brevard",
      states: ["NC"],
      code: { family: "IRC", cls: "code",
        note: "As nc-piedmont. Above roughly 3,000 ft the ASCE 7 ground snow map hands off to case-study (CS) zones " +
              "where NO mapped value exists and a site-specific study is required — a pack cannot supply that number." },
      climate: {
        groundSnow:  { v: 30,  cls: "site", note: "Planning default at valley elevation. Elevation-dependent and county-tabulated; " +
                                                  "CS zones above ~3,000 ft require a site study." },
        roofLive:    { v: 20,  cls: "code", note: LIVE.roof_live.cite },
        windMph:     { v: 115, cls: "site", note: "Topographic speed-up K_zt on ridges and escarpments, ASCE 7 §26.8 — not a regional constant." },
        exposure:    { v: "C", cls: "site" },
        sdc:         { v: "B", cls: "site" }
      },
      governs: "gravity",
      foundation: "crawlspace / walkout basement",
      exteriorWall: "wood",
      roofFraming: "truss",
      service: { wet: false, exteriorWet: true },
      loads: {
        roofAssembly: "roof_shingle", floorAssembly: "floor_res", ceilingAssembly: "ceiling_attic",
        roofLoad: 25, roofType: "snow",
        roofLoadBasis: "Snow governs here, and C_D drops from 1.25 to 1.15 — a real 8% capacity reduction on every " +
                       "bending check, not a bookkeeping change. The 25 psf carried is a PLANNING roof snow load: it " +
                       "is not a computed p_s and not a county value. Compute p_s = C_s x 0.7 x C_e x C_t x I_s x p_g " +
                       "per ASCE 7 Ch. 7 for the actual site. Unbalanced, drift, sliding and rain-on-snow are all " +
                       "excluded by calc-spec §8.14 — and in these mountains roof-step drift is often what governs.",
        floorLive: LIVE.floor_residential.psf, ceilingLive: LIVE.attic_no_storage.psf,
        deckLive: LIVE.deck.psf
      },
      plateHeightIn: 109.125,
      palette: [
        { species: "Southern Pine", grade: "No.2", bfUSD: 0.72, stockFactor: 0.95, cullRate: 0.03 },
        { species: "Southern Pine", grade: "No.1", bfUSD: 0.88, stockFactor: 0.80, cullRate: 0.03 },
        { species: "Spruce-Pine-Fir", grade: "No. 1/No. 2", bfUSD: 0.80, stockFactor: 0.70, cullRate: 0.02 },
        { species: "Douglas Fir-Larch", grade: "No. 2", bfUSD: 1.00, stockFactor: 0.40, cullRate: 0.015,
          note: "Worth the freight where snow makes the extra span matter — dry framing only." }
      ],
      maxDCR: 0.90
    },

    {
      id: "fl-central",
      name: "Florida · Central",
      markets: "Orlando · Tampa · Punta Gorda",
      states: ["FL"],
      code: { family: "IRC", cls: "code",
        note: "Florida Building Code, 8th Edition (2023), Residential — 2021 IRC basis, ASCE 7-22 referenced. " +
              "Statewide and supersedes local codes; local technical amendments are permitted only under " +
              "F.S. §553.73(4) and must be posted. The FBC AMENDS the deflection table (screen enclosures, " +
              "sunrooms, patio covers) — cite the FBC table, not the IBC/IRC one." },
      climate: {
        groundSnow:  { v: 0,   cls: "code", note: "Zero. Snow never governs anywhere in Florida." },
        roofLive:    { v: 20,  cls: "code", note: LIVE.roof_live.cite },
        windMph:     { v: 130, cls: "site", note: "130–139 Orlando, 140–150 coastal Tampa, 150–160 SW Florida coastal. Look up the site." },
        exposure:    { v: "C", cls: "site" },
        sdc:         { v: "A", cls: "site" }
      },
      governs: "wind",
      governsNote: "Uplift sets the connection schedule and frequently the member. This engine checks gravity only " +
                   "(calc-spec §8.11) and designs no connection (§8.17). Note also that uplift REVERSES the moment: " +
                   "the sheathed top edge that justifies C_L = 1.0 under gravity braces nothing when the load reverses.",
      foundation: "slab-on-grade",
      exteriorWall: "cmu",
      exteriorWallNote: "First-floor exterior walls are concrete block with a tie beam, so exterior openings are " +
                        "precast or cast-in-place concrete lintels, NOT wood headers. The wood members in a Central " +
                        "Florida production house are the roof trusses, the lanai beams, and second-floor framing " +
                        "where it exists.",
      roofFraming: "truss",
      service: { wet: false, exteriorWet: true,
                 note: "Lanai and covered-entry framing is treated and taken as wet service. FBC-R R318 termite " +
                       "protection and R317 ground/masonry clearance drive treatment. Note the engine applies C_M " +
                       "but not C_i — treated refractory species are therefore excluded from wet marks." },
      loads: {
        roofAssembly: "roof_shingle", floorAssembly: "floor_res", ceilingAssembly: "ceiling_attic",
        roofLoad: 20, roofType: "roof_live",
        roofLoadBasis: "No snow load in Florida, so the D + S combination is never formed and C_D = 1.15 must not " +
                       "appear on a Florida sheet. Lr = 20 psf unreduced, C_D = 1.25. The variable that actually " +
                       "moves a Florida plan is the roof covering dead load, not the live load.",
        floorLive: LIVE.floor_residential.psf, ceilingLive: LIVE.attic_no_storage.psf,
        deckLive: LIVE.deck.psf
      },
      plateHeightIn: 109.125,
      palette: [
        { species: "Southern Pine", grade: "No.2", bfUSD: 0.68, stockFactor: 1.00, cullRate: 0.04,
          note: "Cull rate runs higher in this humidity — SYP crook and twist on re-equilibration." },
        { species: "Southern Pine", grade: "No.1", bfUSD: 0.84, stockFactor: 0.85, cullRate: 0.04 },
        { species: "Spruce-Pine-Fir", grade: "No. 1/No. 2", bfUSD: 0.86, stockFactor: 0.35, cullRate: 0.02,
          note: "Not a Florida staple. Checked with C_i on treated marks." }
      ],
      maxDCR: 0.90
    },

    {
      id: "fl-hvhz",
      name: "Florida · High-Velocity Hurricane Zone",
      markets: "Miami-Dade · Broward",
      states: ["FL"],
      code: { family: "IRC", cls: "code",
        note: "FBC 8th Edition (2023) Residential, plus FBC-R Chapter 44 (High-Velocity Hurricane Zones). " +
              "VERIFY whether Chapter 44 permits the prescriptive/WFCM path or mandates engineered design — " +
              "this was not resolved and it changes what this output is for." },
      climate: {
        groundSnow:  { v: 0,   cls: "code" },
        roofLive:    { v: 20,  cls: "code", note: LIVE.roof_live.cite },
        windMph:     { v: 175, cls: "site", note: "Miami-Dade 175, Broward 170, Risk Category II — fixed by the FBC. Verify against FBC-R Figure R301.2(2)." },
        exposure:    { v: "C", cls: "site" },
        sdc:         { v: "A", cls: "site" }
      },
      governs: "wind",
      governsNote: "In the HVHZ, gravity sizing is not the design. Uplift, the continuous load path and product " +
                   "approval decide what gets built, and none of them is in this engine (calc-spec §8.11, §8.17). " +
                   "Nothing here has a Miami-Dade NOA and no strap, anchor or hold-down has been designed. " +
                   "Treat a result from this pack as a gravity floor on the member size and nothing more.",
      foundation: "slab-on-grade",
      exteriorWall: "cmu",
      exteriorWallNote: "HVHZ production housing is essentially all concrete block with concrete lintels. Wood " +
                        "exterior headers do not exist in this market.",
      roofFraming: "truss",
      service: { wet: false, exteriorWet: true },
      loads: {
        roofAssembly: "roof_tile", floorAssembly: "floor_res", ceilingAssembly: "ceiling_attic",
        roofLoad: 20, roofType: "roof_live",
        roofLoadBasis: "No snow. Lr = 20 psf, C_D = 1.25. What moves here is the DEAD load: concrete tile at " +
                       "22 psf total against 15 psf for shingle. That alone takes a 12 ft lanai beam from a 4x10 " +
                       "to a 4x12, so tile must be a plan VARIANT and not an afterthought.",
        floorLive: LIVE.floor_residential.psf, ceilingLive: LIVE.attic_no_storage.psf,
        deckLive: LIVE.deck.psf
      },
      plateHeightIn: 109.125,
      palette: [
        { species: "Southern Pine", grade: "No.2", bfUSD: 0.72, stockFactor: 1.00, cullRate: 0.04 },
        { species: "Southern Pine", grade: "No.1", bfUSD: 0.90, stockFactor: 0.85, cullRate: 0.04 },
        { species: "Southern Pine", grade: "Select Structural", bfUSD: 1.15, stockFactor: 0.55, cullRate: 0.04 }
      ],
      maxDCR: 0.85,
      maxDCRBasis: "Firm policy: leave gravity headroom where the same section will also be checked for uplift."
    }
  ];

  /* ---------------- unification bonus ----------------
     Collapsing a group to ONE size buys system effects that a per-SKU handling
     charge does not price: one rim depth, one hanger SKU, one subfloor
     elevation, no bay transitions, and no chance of a 2x10 landing in a 2x12
     bay. Estimators put a single floor depth at $150–400 per house on its own —
     far more than the $40 the generic SKU term carries. It is awarded only when
     a group actually collapses to a single SKU, because that is the only
     condition under which those effects exist. All [market], all estimates. */
  var UNIFY_BONUS = {
    floor:   220,   /* one joist depth for the whole floor                    [market] */
    header:  120,   /* a banded header schedule is the biggest SKU reduction
                       available in a production plan                          [market] */
    roof:     60,
    ceiling:  40,
    deck:     40,
    porch:     0    /* two porch beams of different spans are two members, and
                       nobody bundles them                                     [market] */
  };

  /* ---------------- ladders, spacings, roles ----------------
     Solid sawn only. Multi-ply built-up members and engineered lumber are
     outside the engine (calc-spec §8.6, §8.19), and nothing 14 in or wider is
     offered because the catalog carries no C_F for it (gap #1) and the engine
     refuses rather than hold C_F at 1.00. */
  var LADDERS = {
    rafter:  ["2x6", "2x8", "2x10", "2x12"],
    joist:   ["2x8", "2x10", "2x12"],
    ceiling: ["2x4", "2x6", "2x8", "2x10"],
    header:  ["4x6", "4x8", "4x10", "4x12"],
    beam:    ["4x6", "4x8", "4x10", "4x12"],
    deck:    ["2x8", "2x10", "2x12"]
  };

  /* 19.2 in o.c. is on the tape and saves 20% of the pieces, and sawn-lumber
     crews still mislay it. It is offered on engineered floors only, and this
     build has none — so floors are 16 in o.c. */
  var SPACINGS = {
    rafter:  [16, 24],
    joist:   [16],
    ceiling: [16, 24],
    deck:    [12, 16]
  };

  var REPETITIVE = { rafter: true, joist: true, ceiling: true, deck: true, header: false, beam: false };

  /* What a member CARRIES decides its loads, its duration factor and its
     deflection row. Deriving those from the member's ROLE STRING instead put a
     treated deck beam on roof dead load, roof live at C_D 1.25 and l/180 — and
     printed a 4x8 at 59% utilisation for a member that is overstressed at 1.05
     against the deck load it actually supports. A role is a name; `carries` is
     the structure. Every non-obvious mark must declare it. */
  var CARRIES_DEFAULT = {
    rafter: "roof", ceiling: "ceiling", joist: "floor", deck: "deck"
    /* header and beam are deliberately absent. A joist carries a floor by
       definition; a beam carries whatever the plan puts on it, and guessing
       "roof" is exactly the defect that printed a passing deck beam. They must
       declare `carries`. */
  };

  var DEFL_BY_CARRIES = {
    roof:         "roof_nonplaster",   /* gypsum ceiling below */
    "roof-open":  "roof_no_ceiling",   /* open porch soffit, nothing on the underside */
    ceiling:      "roof_nonplaster",
    floor:        "floor",
    deck:         "floor",
    "roof+floor": "floor"              /* the tighter of the two rows governs */
  };

  /* HDR-1's refusal, kept verbatim. It is the ruling SE-3 wrote in round four —
     "substituting 12.0 replaces one asserted tributary with another and closes
     the finding without answering it" — and it is specific to THAT mark. It used
     to be hard-coded inside applicability(), which meant the second
     underdetermined mark on any plan would have inherited HDR-1's story and
     reported a contradiction it does not have. Every underdetermined mark now
     carries its own `underdeterminedNote`; the generic fallback below is what a
     mark that forgets gets, and it says it forgot rather than borrowing a
     reason from somewhere else. */
  var UNDETERMINED_HDR1 =
    "NOT SIZED — the tributary is not derivable. This mark's roof tributary (19.0 ft, half the " +
    "first-floor depth) contradicts the sibling header in the same wall one storey up (12.0 ft), " +
    "and the plan declares no roof mark, no second-floor outline and no truss direction. Three " +
    "values are in play (12.0, 16.32, 19.0) and none follows from the plan. Substituting one for " +
    "another closes the finding without answering it. Declare the second-floor outline and the " +
    "truss direction, then derive both headers from it.";

  var UNDETERMINED_GENERIC =
    "NOT SIZED — this mark is declared underdetermined and its tributary is not derivable from " +
    "the plan's stated geometry. It carries no asserted number, because asserting one would " +
    "close the finding without answering it. The mark states no reason of its own; add " +
    "`underdeterminedNote` saying which quantity is missing and what must be declared to " +
    "recover it.";

  /* ---------------- repeatable tract-home plans ----------------
     Built around the marks that are REAL in these three states.

     A production roof in Texas, the Carolinas and Florida is a truss package
     at 24 in o.c., engineered by the truss supplier as a deferred sealed
     submittal. Rafter and ceiling-joist marks are fiction outside porch roofs,
     dormers and tray areas. Long openings are engineered headers. Both are
     carried here as marks with `component: true` or `escalate: true` so the
     schedule shows what it is NOT designing — a plan that silently omits the
     garage header reads as if the garage header were fine.

     Where this engine is genuinely the right tool: treated lanai and porch
     beams, North Carolina crawlspace floor joists and decks, and small-to-mid
     headers. Those are the marks it solves. */

  var PLANS = [
    {
      id: "sunbelt-ranch-1850",
      name: "Sunbelt Ranch 1850",
      summary: "1,860 sf single-story slab-on-grade, 50 ft × 46 ft, two-car garage, trusses at 24 in o.c.",
      lots: 100,
      note: "The entry-level production footprint in DFW, San Antonio, Orlando, Tampa, Charlotte and Raleigh. " +
            "The roof clear-spans on common trusses, which is the product feature — it is what makes the " +
            "partitions movable between elevations.",
      marks: [
        { id: "T-1",     label: "Common roof truss · 46 ft clear span", role: "rafter", span: 46, runFt: 50, count: 26, carries: "roof",
          component: true,
          componentNote: "Truss package, deferred sealed submittal by the truss supplier. Out of scope: this engine " +
                         "designs simple-span solid-sawn members only (calc-spec §8.6, §8.19)." },
        { id: "BM-LAN",  label: "Lanai beam", role: "beam", span: 12.0, trib: 7.0, count: 2,
          exposure: "exterior", braced: false, skuGroup: "porch", roofAssembly: "open", carries: "roof",
          note: "The best-fitting mark in the system: simple span, uniform load, treated Southern Pine, wet service." },
        { id: "BM-LAN-W", label: "Lanai beam · wide bay", role: "beam", span: 16.0, trib: 7.0, count: 1,
          exposure: "exterior", braced: false, skuGroup: "porch", roofAssembly: "open", carries: "roof" },
        { id: "HDR-W",   label: "Window header · typical", role: "header", span: 5.0, trib: 23.0, count: 14,
          carries: "roof", bearing: 3.0, skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor",
          note: "Tributary is half the truss span where the trusses bear on this wall. A 4 ft " +
                "tributary here would follow from neither the 46 ft clear span nor the gable end." },
        { id: "HDR-GAR-G", label: "Garage header · gable end over the door", role: "header", span: 16.67, trib: 2.0, count: 1,
          component: true,
          componentNote: "OUT OF SCOPE — NOT CHECKED. A gable-end header carries the gable wall " +
            "standing on it, and ASSEMBLY{} has no wall dead load of any kind, so the model cannot " +
            "express the dominant term. It is also a TRIANGULAR load, which calc-spec §8.3 excludes " +
            "outright. Checked as a 2 ft roof strip this mark printed 4x8 at DCR 0.896; across the " +
            "plausible envelope of pitch, gable width and wall weight the same member runs 1.10 to " +
            "1.78 — it fails in every case. Re-admit only once the plan declares roof pitch, gable " +
            "width and opening offset, with a stated moment-equivalent uniform.",
          carries: "roof", bearing: 3.0, skuGroup: "header", headHeightIn: 84, wallPosition: "exterior-first-floor",
          note: "Same opening as HDR-GAR-B. The truss direction is the entire design: 2 ft of tributary here, 11 ft there." },
        { id: "HDR-GAR-B", label: "Garage header · trusses bearing", role: "header", span: 16.67, trib: 11.0, count: 1,
          carries: "roof", bearing: 3.0, skuGroup: "header", headHeightIn: 84, wallPosition: "exterior-first-floor", escalateExpected: true,
          note: "Under a bearing truss line this is a 3-ply LVL or a girder truss in every one of these markets." },
        { id: "HDR-SLD", label: "Rear slider header · under clear-span truss", role: "header", span: 12.0, trib: 23.0, count: 1,
          carries: "roof", bearing: 3.0, skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor", escalateExpected: true,
          note: "Tributary is half the 46 ft truss span. This is why exterior openings in production single-stories " +
                "are almost always engineered." },
        { id: "PST-LAN", label: "Lanai beam posts · BM-LAN / BM-LAN-W", role: "post",
          count: 6, component: true, reactionFrom: ["BM-LAN", "BM-LAN-W"],
          componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10 specifies C_P, §8.20 " +
            "states no interaction equation is evaluated, and engine.js implements neither). The " +
            "design load is the end reaction of the beam above, printed live below for this region. " +
            "BM-LAN-W escalates, so no reaction is published for it and none is invented. Uplift, " +
            "the continuous load path and both the base and cap connections are out of scope " +
            "(§8.11, §8.17). Slenderness is not a formality: for a typical 8 ft 4x4, C_P runs 0.25 to " +
            "0.35, so a check that omits it overstates axial capacity roughly threefold." }
      ],
      geometry: {
        footprintFt: [50, 46],
        underRoofSf: 1860,
        trussSpanFt: 46,
        trussSpacingIn: 24,
        bearingLines: "the two 50 ft walls. The 46 ft clear span is the product feature — it is what " +
                      "makes the partitions movable between elevations.",
        lanaiDepthFt: 14,
        note: "Stated design geometry, not a weight. The 14 ft lanai depth is what HDR-W's 23.0 ft " +
              "and BM-LAN's 7.0 ft tributaries already imply — half the truss span and half the " +
              "lanai depth respectively. It is written down here so an elevation can move it."
      },
      elevations: [
        { id: "a", kind: "elevation", label: "Elevation A · gable, 14 ft lanai", base: true,
          takeRate: 0.40,
          note: "The stamped base case. What the marks above are." },
        { id: "b", kind: "elevation", label: "Elevation B · hip", takeRate: 0.35,
          movesNoMember: true,
          note: "The most-built elevation in most of these subdivisions and it moves no member this " +
                "engine sizes. The common trusses still clear-span 46 ft onto the same two 50 ft " +
                "walls, so every header tributary is unchanged. What a hip actually changes is the " +
                "TRUSS PACKAGE — hip girders, step-downs and jacks — which is the supplier's " +
                "deferred sealed submittal (T-1), and the girder-truss corner reactions, which land " +
                "on posts §8.20 does not check. Declared as no-move rather than asserted as " +
                "no-change: the members this engine sizes do not move, and the two things that do " +
                "are both already out of scope." },
        { id: "c", kind: "elevation", label: "Elevation C · extended covered patio", takeRate: 0.25,
          note: "The lanai goes from 14 ft to 18 ft deep. The posts do not move, so neither span " +
                "changes and both tributaries do — 18/2 = 9.0 ft against 14/2 = 7.0. This is the " +
                "cleanest demonstration in the book that an elevation is a structural document: one " +
                "dimension on a sales sheet, two members resized, and the revision is manufactured " +
                "after permit if nobody sized the envelope.",
          overrides: {
            "BM-LAN": { trib: 9.0,
              note: "Elevation C lanai is 18 ft deep; the beam takes half of it. Same 12 ft span — " +
                    "the post bays did not move." },
            "BM-LAN-W": { trib: 9.0,
              note: "Elevation C lanai is 18 ft deep; the beam takes half of it. Same 16 ft wide " +
                    "bay." },
            "PST-LAN": { componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10 specifies " +
              "C_P, §8.20 evaluates no interaction equation). Elevation C loads these posts harder " +
              "than Elevation A: both lanai beams carry 9.0 ft of tributary instead of 7.0, about " +
              "29% more reaction. Take the design load from the reactions this tool computes for " +
              "BM-LAN and BM-LAN-W in THIS variant — the Elevation A figures on the base mark are " +
              "not the envelope. Uplift, the continuous load path and both the base and cap " +
              "connections stay out of scope (§8.11, §8.17), and for a typical 8 ft 4x4 C_P runs " +
              "0.25 to 0.35." }
          } }
      ],
      options: [
        { id: "opt-tile", kind: "option", label: "Concrete tile roof", takeRate: 0.20,
          roofAssemblyKey: "roof_tile",
          note: "The pack note on fl-hvhz already says it: concrete tile at 22 psf against 15 for " +
                "shingle takes a 12 ft lanai beam from a 4x10 to a 4x12 on its own, so tile must be " +
                "a plan VARIANT and not an afterthought. This is that variant. It is a no-op in the " +
                "HVHZ pack, which already ships tile, and it is the single largest gravity change " +
                "available anywhere else. [market] take rate." },
        { id: "opt-8ft", kind: "option", label: "8 ft tall doors and windows, first floor",
          takeRate: 0.30,
          note: "An 8 ft head height in the 9'-1-1/8\" precut wall leaves 9.625 in for the header, " +
                "less a double top plate and a shim — so nothing deeper than a 4x10 fits. It changes " +
                "no load whatsoever and it is still a member change, because a header that does not " +
                "fit is not a cheaper header, it is a plate-height change and a revision. Take it " +
                "together with the tile option to see the case that produces one: tile drives the " +
                "member deeper at the same moment this option caps how deep it may be.",
          overrides: {
            "HDR-W": { headHeightIn: 96 },
            "HDR-SLD": { headHeightIn: 96 }
          } },
        { id: "opt-bed4", kind: "option", label: "4th bedroom in lieu of the study", takeRate: 0.50,
          movesNoMember: true,
          note: "Half the lots take it and it moves nothing. Under a 46 ft clear-span truss every " +
                "interior partition is non-bearing, which is exactly what the plan note claims — " +
                "this option is the claim being exercised rather than asserted. Declared rather than " +
                "omitted: an option missing from the master set reads as an option nobody checked." }
      ]
    },
    {
      id: "two-story-2450",
      name: "Two-Story 2450",
      summary: "2,450 sf two-story, 40 ft × 38 ft first floor (1,520 sf) plus 930 sf second floor, centre bearing line",
      lots: 60,
      note: "The second floor is the mark set that matters. In Texas and Florida this floor is increasingly an " +
            "open-web truss or an I-joist; sawn 2x is Carolina value product and some Texas builders.",
      marks: [
        { id: "FJ-1", label: "2nd floor joist · front bay", role: "joist", span: 13.5, runFt: 34, count: 26, skuGroup: "floor",
          note: "The DCR-policy mark: 2x10 SYP #2 reaches 13 ft 3 in at a 0.90 target and 14 ft 0 in at 1.00." },
        { id: "FJ-2", label: "2nd floor joist · rear bay", role: "joist", span: 15.0, runFt: 31, count: 24, skuGroup: "floor" },
        { id: "FJ-3", label: "2nd floor joist · bath and laundry", role: "joist", span: 9.5, runFt: 13, count: 10, skuGroup: "floor",
          floorAssembly: "floor_wet",
          note: "Solves shallow, and is the prime unification target — one floor depth is worth more than the lumber." },
        { id: "GB-1", label: "Centre floor girder", role: "beam", span: 12.0, trib: 14.25, count: 2, skuGroup: "girder",
          braced: true, escalateExpected: true, carries: "floor",
          note: "Multi-ply LVL or a steel W-shape in the market. The catalog carries 48 W-shapes; the calc-spec has " +
                "no steel method, so this engine cannot design either answer." },
        { id: "HDR-1", label: "1st-floor opening header", role: "header", span: 5.0, count: 10,
          carries: "roof+floor", tribRoof: 19.0, tribFloor: 6.75, underdetermined: true,
          underdeterminedNote: UNDETERMINED_HDR1,
          bearing: 3.0, skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor" },
        { id: "HDR-2", label: "2nd-floor window header", role: "header", span: 4.0, trib: 12.0, count: 12,
          carries: "roof", bearing: 1.5, skuGroup: "header", headHeightIn: 80,
          note: "Second floor, so it is a wood header even in a concrete-block market." },
        { id: "DK-1", label: "Deck joist · treated", role: "deck", span: 12.0, runFt: 20, count: 16, skuGroup: "deck",
          exposure: "exterior",
          note: "North Carolina production homes very often carry one. IRC R507, 40 psf live." },
        { id: "DK-2", label: "Deck beam · treated", role: "beam", span: 8.0, trib: 6.0, count: 2, skuGroup: "deckbeam",
          exposure: "exterior", braced: false, carries: "deck",
          note: "Carries the deck, not a roof. Checked as a roof beam it printed a 4x8 at 59% that is " +
                "overstressed at 1.05 against 40 psf of deck live load." },
        { id: "HDR-ST", label: "Stair opening header · 2nd floor", role: "header",
          span: 12.5, trib: 5.0, count: 1, carries: "floor",
          braced: true, bearing: 3.0, skuGroup: "header",
          note: "12'-6\" clear opening = 15 treads at 10 in, derived from this pack's own 109.125 in " +
                "plate (16R at 7.6 in per IRC R311.7.1). The opening runs ALONG the bearing line, so the " +
                "header takes the tail joists over the remaining 10.0 ft of the 13.5 ft bay, t = 5.0 ft. " +
                "NOT CHECKED HERE, and neither is anything else in this assembly: the two double TRIMMERS " +
                "carry this header's end reaction as a CONCENTRATED load (calc-spec §8.3 — uniform " +
                "full-span load only), the upper stringer lands on it as a second point load, and the " +
                "joist-to-header connection is a face-mount hanger (§8.17)." },
        { id: "HDR-GAR-2S", label: "Garage door header · bonus room over", role: "header",
          span: 16.67, count: 1, carries: "roof+floor", tribRoof: 11.0, tribFloor: 5.5,
          bearing: 4.5, skuGroup: "header", headHeightIn: 84, wallPosition: "exterior-first-floor",
          escalateExpected: true,
          note: "16'-0\" door. The roof spans the 22 ft garage depth onto this wall, t_roof = 11.0 — the " +
                "same derivation HDR-GAR-B uses. The BONUS-ROOM elevation (register D11) puts a floor " +
                "over the garage; 22 ft is beyond sawn range so it needs a mid girder, giving " +
                "t_floor = 11.0/2 = 5.5. This is the envelope mark D11 asks for: sizing the base " +
                "elevation and letting an option move the bearing is how a revision gets manufactured." },
        { id: "PST-DK", label: "Deck beam posts · DK-2", role: "post", count: 2, component: true,
          reactionFrom: ["DK-2"],
          componentNote: "AXIAL MEMBER — NOT CHECKED HERE. calc-spec §4.10 specifies C_P (NDS §3.7.1) " +
            "and §8.20 states no interaction equation is evaluated; engine.js implements neither. " +
            "The design load is DK-2's end reaction, which this tool does compute and prints live " +
            "below. Also out of scope on this member: uplift and the continuous " +
            "load path (§8.11, §8.17) and both the base and cap connections (§8.17). Slenderness is " +
            "not a formality — for a typical 8 ft 4x4, C_P runs 0.25 to 0.35, so a check that omits " +
            "it overstates axial capacity roughly threefold." }
      ],
      geometry: {
        footprintFt: [40, 38],
        firstFloorSf: 1520,
        secondFloorSf: 930,
        storeys: 2,
        bearingLines: "the exterior walls plus a centre bearing line on the first floor; the second " +
                      "floor splits into a 13.5 ft front bay and a 15.0 ft rear bay across it.",
        garageDepthFt: 22,
        deckFt: [20, 12],
        note: "Stated design geometry, not a weight. The 12 ft deck depth is what DK-1's 12.0 ft " +
              "joist span and DK-2's 6.0 ft tributary already imply; the 22 ft garage depth is what " +
              "HDR-GAR-2S derives its 11.0 ft roof tributary from."
      },
      elevations: [
        { id: "a", kind: "elevation", label: "Elevation A · as stamped", base: true, takeRate: 0.55,
          note: "The stamped base case. What the marks above are." },
        { id: "b", kind: "elevation", label: "Elevation B · covered front porch", takeRate: 0.45,
          geometry: { porchFt: [20, 8], posts: 3, eaveOverhangFt: 1.0,
                      note: "Geometry this elevation adds, from which its added marks derive." },
          note: "A covered porch across 20 ft of the 40 ft front face, 8 ft deep, on three posts. It " +
                "adds a member rather than resizing one — which is the case a master set is most " +
                "likely to lose, because a mark that does not exist on the base sheet has nobody " +
                "checking it.",
          add: [
            { id: "BM-POR", label: "Front porch beam · treated", role: "beam",
              span: 10.0, trib: 5.0, count: 2, carries: "roof",
              exposure: "exterior", braced: false, skuGroup: "porch", roofAssembly: "open",
              note: "Elevation B only. Porch is 20 ft wide by 8 ft deep on three posts, so the beam " +
                    "is two 10.0 ft bays, and the tributary is half the 8 ft depth plus the 1 ft " +
                    "eave overhang = 5.0 ft. Open roof: no ceiling, no insulation, no-ceiling " +
                    "deflection row." },
            { id: "PST-POR-B", label: "Front porch beam posts · BM-POR", role: "post",
              count: 3, component: true,
              componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10 specifies C_P, §8.20 " +
                "evaluates no interaction equation). Elevation B only. Take the design load from the " +
                "end reaction this tool computes for BM-POR in this variant; the CENTRE post takes " +
                "two bearings, so double it. Uplift, the continuous load path and both the base and " +
                "cap connections are out of scope (§8.11, §8.17). For a typical 9 ft 4x4, C_P runs " +
                "0.25 to 0.35." }
          ] }
      ],
      options: [
        { id: "opt-bonus", kind: "option", label: "Bonus room over the garage", takeRate: 0.35,
          movesNoMember: true,
          note: "This option moves no member, and the reason is the entire argument for master-set " +
                "sizing. HDR-GAR-2S was ALREADY sized to it: register D11 and §K.4 ruled that the " +
                "base sheet carries the bonus-room case (tribRoof 11.0 + tribFloor 5.5) rather than " +
                "the roof-only case, precisely so that taking the option does not manufacture a " +
                "revision after permit. The cost of that decision is visible on every lot that does " +
                "NOT take the bonus room and buys the header anyway; the cost of the other decision " +
                "is a stamped revision on 35% of them. Both are real, the firm chose, and the choice " +
                "is written down here instead of being invisible." },
        { id: "opt-deck-ext", kind: "option", label: "Extended rear deck · 26 ft × 14 ft",
          takeRate: 0.25,
          note: "The deck grows from 20 ft × 12 ft to 26 ft × 14 ft. The extra width buys a fourth " +
                "post, so the beam bays go from two at 8.0 ft to three at 8.67 ft — a longer span " +
                "AND a heavier tributary, both worse. That makes this the easy envelope case: one " +
                "variant dominates on every driver, so envelopeFor() names it and a member sized " +
                "for it covers every lot in the set. Compare the coastal duplex's Elevation B, " +
                "where the fourth post SHORTENS the span while deepening the porch and no single " +
                "variant governs.",
          overrides: {
            "DK-1": { span: 14.0, runFt: 26,
              note: "Extended deck is 14 ft deep, so the joists span 14.0 ft, over a 26 ft run. " +
                    "IRC R507, 40 psf live — and see register L10 on the 60 psf reading." },
            "DK-2": { span: 8.67, trib: 7.0, count: 3,
              note: "26 ft of beam on four posts = three 8.67 ft bays, and the tributary is half the " +
                    "14 ft deck depth = 7.0 ft. Shorter span, heavier load: it is the pair that " +
                    "makes the envelope a genuine question rather than a maximum." },
            "PST-DK": { count: 4, reactionFrom: ["DK-2"],
              componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10, " +
              "§8.20). The extended deck stands on FOUR posts, not two, and each carries 7.0 ft of " +
              "tributary instead of 6.0. The design load is DK-2's reaction IN THIS VARIANT, printed " +
              "live below — the base mark's reaction is the 20 ft deck and is a different number. Uplift " +
              "and both connections remain out of scope (§8.11, §8.17), and C_P is not evaluated." }
          } },
        { id: "opt-tile", kind: "option", label: "Concrete tile roof", takeRate: 0.15,
          roofAssemblyKey: "roof_tile",
          note: "22 psf against 15 reaches every roof-carrying mark on the plan at once — HDR-2 " +
                "here, and Elevation B's porch beam where that elevation is built. A no-op in the " +
                "HVHZ pack, which already ships tile. [market] take rate." }
      ]
    },
    {
      id: "coastal-duplex-1600",
      name: "Coastal Duplex 1600",
      summary: "1,600 sf per unit, two-story paired duplex, 26 ft × 32 ft per unit, party wall bearing",
      lots: 24,
      note: "Maps to the sample Punta Gorda project — Charlotte County, windborne-debris region, not HVHZ. " +
            "This is the archetype where the engine has the least to say: the design action that governs the " +
            "building is the continuous uplift load path, and it is excluded by calc-spec §8.11 and §8.17.",
      marks: [
        { id: "T-1",  label: "Common roof truss · 26 ft", role: "rafter", span: 26, count: 17, component: true, carries: "roof",
          componentNote: "Truss package, uplift-governed, deferred sealed submittal. Out of scope." },
        { id: "FJ-1", label: "2nd floor joist", role: "joist", span: 15.5, runFt: 32, count: 25, skuGroup: "floor",
          note: "Runs tight against the 2x12 limit — the mark that shows why a firm DCR target below 1.00 exists." },
        { id: "BM-POR", label: "Porch beam · treated", role: "beam", span: 10.0, trib: 6.0, count: 2,
          exposure: "exterior", braced: false, skuGroup: "porch", roofAssembly: "open", carries: "roof" },
        { id: "HDR-SLD", label: "1st-floor slider header · roof + floor", role: "header", span: 8.0, count: 2,
          carries: "roof+floor", tribRoof: 13.0, tribFloor: 7.75,
          bearing: 3.0, skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor" },
        { id: "BM-BRG", label: "Interior bearing line · great-room girder", role: "beam",
          span: 12.0, trib: 13.0, count: 1, carries: "floor", braced: true,
          skuGroup: "girder", escalateExpected: true,
          note: "The interior line FJ-1 already implies: FJ-1 spans 15.5 of the 26 ft width and " +
                "HDR-SLD declares tribFloor 7.75 = 15.5/2, so this line takes 15.5/2 + 10.5/2 = 13.0 ft. " +
                "It is the mark that gives this plan something to say in the two concrete-block markets, " +
                "where every other header is a lintel. NOT CHECKED: the 10.5 ft party-wall bay has no " +
                "joist mark of its own — FJ-1 covers the 15.5 ft bay only." },
        { id: "HDR-2F", label: "2nd-floor window header · bearing wall", role: "header",
          span: 5.0, trib: 13.0, count: 8, carries: "roof", bearing: 3.0,
          skuGroup: "header", headHeightIn: 80,
          note: "Tributary is half the 26 ft truss span — the same 13.0 ft HDR-SLD declares for " +
                "tribRoof. wallPosition is deliberately ABSENT: second-floor framing is wood even in " +
                "a concrete-block market, and declaring it would delete the mark. The gable-end variant " +
                "of the same window takes about 2 ft and is a separate mark." },
        { id: "DK-C1", label: "Deck joist · treated, under the covered porch", role: "deck",
          span: 12.0, runFt: 20, count: 16, carries: "deck",
          exposure: "exterior", skuGroup: "deck",
          note: "12 ft = the porch depth implied by BM-POR's 6.0 ft tributary; the 20 ft run is " +
                "BM-POR's two 10 ft bays. OPEN: IRC R507 gives 40 psf where ASCE 7-22 Table 4.3-1 " +
                "gives 60 psf for an exterior balcony, and at 60 this member is overstressed at 1.024." },
        { id: "DK-C2", label: "Deck beam · treated", role: "beam",
          span: 10.0, trib: 6.0, count: 2, carries: "deck",
          exposure: "exterior", braced: false, skuGroup: "deckbeam",
          note: "Shares posts with BM-POR — one post takes both this reaction and the porch-roof " +
                "beam's. A deck without its beam is the same silent omission this mark set exists " +
                "to remove." },
        { id: "PST-POR", label: "Porch and deck beam posts · BM-POR / DK-C2", role: "post",
          count: 4, component: true, reactionFrom: ["BM-POR", "DK-C2"],
          componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10, §8.20: C_P is specified " +
            "and no interaction equation is evaluated). The design loads are the end reactions of " +
            "the two beams above, printed live below for this region. In a " +
            "wind-governed market UPLIFT on this post and its base and cap connections (§8.11, " +
            "§8.17) govern, and none of that is checked here." }
      ],
      geometry: {
        footprintFt: [26, 32],
        storeys: 2,
        sfPerUnit: 1600,
        trussSpanFt: 26,
        bearingLines: "the party wall and the two end walls, plus one interior line on the second " +
                      "floor 15.5 ft off the exterior wall — FJ-1's bay — leaving a 10.5 ft " +
                      "party-wall bay that carries no joist mark.",
        porchFt: [20, 12],
        posts: 3,
        note: "Stated design geometry, not a weight. The 12 ft porch depth is what BM-POR's 6.0 ft " +
              "tributary and DK-C1's 12.0 ft joist span already imply, and the 20 ft porch width is " +
              "DK-C1's stated run — two 10 ft bays on three posts."
      },
      elevations: [
        { id: "a", kind: "elevation", label: "Elevation A · gable, 12 ft covered porch", base: true,
          takeRate: 0.60,
          note: "The stamped base case. What the marks above are." },
        { id: "b", kind: "elevation", label: "Elevation B · deep screened lanai", takeRate: 0.40,
          note: "The porch goes from 12 ft to 14 ft deep and the wider load buys a fourth post, so " +
                "the 20 ft run becomes three 6.67 ft bays instead of two 10.0 ft ones. Both porch " +
                "members therefore get MORE tributary and LESS span at the same time, and neither " +
                "variant dominates the other. This is the case the envelope logic exists for: there " +
                "is no single conservative demand, and the honest answer is to size both and take " +
                "the deeper pick, not to compose a maximum no lot is built to.",
          overrides: {
            "BM-POR": { span: 6.67, trib: 7.0, count: 3,
              note: "Elevation B: 20 ft of beam on four posts = three 6.67 ft bays; tributary is " +
                    "half the 14 ft porch depth = 7.0 ft." },
            "DK-C1": { span: 14.0,
              note: "Elevation B porch depth is 14 ft, so the deck joists span it. Run is still " +
                    "BM-POR's 20 ft. OPEN: IRC R507 gives 40 psf where ASCE 7-22 Table 4.3-1 gives " +
                    "60 psf for an exterior balcony (register L10) — at 14 ft that gap is wider, " +
                    "not narrower." },
            "DK-C2": { span: 6.67, trib: 7.0, count: 3,
              note: "Shares the same four posts as BM-POR in this elevation: three 6.67 ft bays, " +
                    "tributary half the 14 ft depth = 7.0 ft." },
            "PST-POR": { count: 5, componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec " +
              "§4.10, §8.20: C_P is specified and no interaction equation is evaluated). Elevation B " +
              "stands on FOUR posts per porch, not three, and each carries 7.0 ft of tributary " +
              "instead of 6.0 — and each still takes BOTH the porch-roof beam and the deck beam. " +
              "Take the design loads from the reactions this tool computes for BM-POR and DK-C2 in " +
              "THIS variant; the figures on the base mark are Elevation A. In a wind-governed market " +
              "UPLIFT on this post and its base and cap connections (§8.11, §8.17) govern, and none " +
              "of that is checked here." }
          } }
      ],
      options: [
        { id: "opt-tile", kind: "option", label: "Concrete tile roof", takeRate: 0.45,
          roofAssemblyKey: "roof_tile",
          note: "Nearly half the lots in this market, and it is a no-op in the HVHZ pack because " +
                "that pack already ships tile — which is worth showing, because it is the same " +
                "option costing nothing in one market and moving the porch beam in the other five. " +
                "[market] take rate." },
        { id: "opt-3bed-down", kind: "option", label: "3rd bedroom down in lieu of the study",
          takeRate: 0.35, movesNoMember: true,
          note: "Moves nothing. The trusses clear-span the 26 ft width party wall to party wall, so " +
                "no first-floor partition is bearing for the roof, and the second-floor bearing line " +
                "BM-BRG serves is set by FJ-1's 15.5 ft bay, which this option does not touch. " +
                "Declared rather than omitted: an option missing from the master set reads as an " +
                "option nobody checked." }
      ]
    },

    /* ---------------- the small end of the market ----------------
       The three plans above are 1,600–2,450 sf. The product that is actually
       repeated two hundred times in one subdivision is smaller than any of
       them, and it frames differently: a slab-on-grade starter has NO floor
       framing at all, and an attached unit's party walls carry everything so
       its street-facing walls carry almost nothing. Both facts change what this
       engine has to say, and both are stated on the marks rather than implied. */

    {
      id: "starter-1210",
      name: "Starter 1210",
      summary: "1,208 sf conditioned + 264 sf one-car garage, single-story slab-on-grade, 46 ft × 32 ft, simple gable, trusses at 24 in o.c.",
      lots: 220,
      geometry: {
        footprintFt: [46, 32],
        underRoofSf: 1472,
        conditionedSf: 1208,
        garage: { widthFt: 12, depthFt: 22, sf: 264, cars: 1 },
        roofForm: "simple gable, ridge parallel to the 46 ft street face",
        trussSpanFt: 32,
        trussSpacingIn: 24,
        bearingLines: "the two 46 ft walls, front and rear. The two 32 ft walls are gable ends and " +
                      "bear nothing. There is no third bearing line and no floor framing.",
        coveredEntryFt: [8, 6],
        eaveOverhangFt: 1.0,
        note: "Stated design geometry, not a weight. Every span, tributary and count on this plan " +
              "is derived from these seven numbers and the derivation is written on the mark."
      },
      note: "The genuinely small end of this market — the 3/2 entry product built two hundred times " +
            "in one subdivision. One decision sets the whole frame: the common trusses clear-span the " +
            "32 ft depth onto the two 46 ft walls, so those two walls are the only bearing lines in " +
            "the house, every interior partition is non-bearing, and every opening in a 46 ft wall " +
            "takes the same 16.0 ft. It is a slab, so there is no floor framing to size. The engine's " +
            "entire answer on this plan is four headers and one entry beam — and in the two " +
            "concrete-block Florida packs it is one entry beam, because first-floor exterior " +
            "openings there are concrete lintels. That is the truth about the product, not a gap " +
            "in the tool.",
      marks: [
        { id: "T-1", label: "Common roof truss · 32 ft clear span", role: "rafter",
          span: 32, runFt: 46, count: 24, carries: "roof", component: true,
          componentNote: "Truss package, deferred sealed submittal by the truss supplier. Out of " +
            "scope: this engine designs simple-span solid-sawn members only (calc-spec §8.6, §8.19). " +
            "Count is the 46 ft ridge run at 24 in o.c. plus one." },

        { id: "HDR-W", label: "Window header · typical, bearing wall", role: "header",
          span: 4.5, trib: 16.0, count: 8, carries: "roof", bearing: 3.0,
          skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor",
          note: "4'-0\" window: rough opening 4'-0-1/2\" plus 3 in of bearing at each end = 4.5 ft. " +
                "Tributary is half the 32 ft truss clear span, because both 46 ft walls are bearing " +
                "lines and they are the only ones on the plan. Two jacks." },

        { id: "HDR-ENT", label: "Front entry door header", role: "header",
          span: 3.67, trib: 16.0, count: 1, carries: "roof", bearing: 3.0,
          skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor",
          note: "3'-0\" door: rough opening 3'-2\" plus 3 in of bearing at each end = 3'-8\" = 3.67 ft. " +
                "Same 16.0 ft as HDR-W — it is in the same bearing wall, and that is the point of a " +
                "clear-span truss plan: the tributary is a property of the wall, not of the opening." },

        { id: "HDR-SLD", label: "Rear slider header", role: "header",
          span: 6.5, trib: 16.0, count: 1, carries: "roof", bearing: 3.0,
          skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor",
          note: "6'-0\" sliding glass door: rough opening 6'-1\" plus 3 in of bearing at each end " +
                "= 6.5 ft. Tributary is half the 32 ft truss span." },

        { id: "HDR-GAR", label: "One-car garage door header · trusses bearing", role: "header",
          span: 9.67, trib: 16.0, count: 1, carries: "roof", bearing: 4.5,
          skuGroup: "header", headHeightIn: 84, wallPosition: "exterior-first-floor",
          note: "9'-0\" single garage door: rough opening 9'-2\" plus 3 in of bearing at each end = " +
                "9'-8\" = 9.67 ft. The garage door is in the FRONT 46 ft wall, which is a truss " +
                "bearing line, so it takes the same 16.0 ft every other opening in that wall takes. " +
                "Three jacks: §K3 found five rows needing more than one and this is the largest " +
                "reaction on the plan. This is the mark that decides whether the smallest house in " +
                "the book needs an engineered header at all, and the answer is regional: it lands " +
                "on a 4x12 in the four gravity and wind markets and ESCALATES in nc-mountain on " +
                "bending, because snow takes C_D from 1.25 to 1.15 — an 8% capacity cut on the one " +
                "mark that had no margin for it. Same house, same door, different lumber package." },

        { id: "HDR-GBL", label: "Gable-end window header", role: "header",
          span: 4.5, count: 3, carries: "roof", bearing: 3.0,
          skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor",
          component: true,
          componentNote: "OUT OF SCOPE — NOT CHECKED, for the same reason HDR-GAR-G on the Sunbelt " +
            "Ranch is not: a header in a gable end carries the gable wall standing on it, ASSEMBLY{} " +
            "has no wall dead load of any kind (register §L6), and the load is TRIANGULAR, which " +
            "calc-spec §8.3 excludes outright. The 32 ft walls are not truss bearing lines, so there " +
            "is no roof strip to substitute either — the honest tributary here is a wall weight and " +
            "the model cannot express it. Re-admit only once the plan declares roof pitch, gable " +
            "width, wall weight and opening offset, with a stated moment-equivalent uniform." },

        { id: "BM-ENT", label: "Covered entry beam · treated", role: "beam",
          span: 8.0, trib: 4.0, count: 1, carries: "roof",
          exposure: "exterior", braced: false, skuGroup: "porch", roofAssembly: "open",
          note: "The entry stoop is 8 ft wide by 6 ft deep. The beam is at the outer edge on two " +
                "posts, so the span is the 8 ft width and the tributary is half the 6 ft depth plus " +
                "the 1 ft eave overhang = 4.0 ft. Open roof: no ceiling, no insulation, so it is on " +
                "the no-ceiling deflection row and the 10 psf open-roof assembly, not the 15 psf " +
                "enclosed one. This is the only mark on the plan that survives in a block market." },

        { id: "PST-ENT", label: "Covered entry beam posts · BM-ENT", role: "post",
          count: 2, component: true, reactionFrom: ["BM-ENT"],
          componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10 specifies C_P, §8.20 " +
            "states no interaction equation is evaluated, and engine.js implements neither). The " +
            "design load is BM-ENT's end reaction, printed live below for this region. " +
            "The numbers are small, and they are still not the design: " +
            "on a covered entry in a wind-governed market UPLIFT and the base and cap connections " +
            "govern, and all three are out of scope (§8.11, §8.17). For a typical 8 ft 4x4, C_P runs " +
            "0.25 to 0.35, so a check that omits it overstates axial capacity roughly threefold." }
      ],
      elevations: [
        { id: "a", kind: "elevation", label: "Elevation A · gable, one-car garage", base: true,
          takeRate: 0.45,
          note: "The stamped base case: simple gable, 12 ft x 22 ft one-car garage, 8 ft x 6 ft " +
                "covered entry. What the marks above are." },
        { id: "b", kind: "elevation", label: "Elevation B · gable, deeper covered entry",
          takeRate: 0.30,
          note: "The same roof and the same garage; the entry stoop grows to 12 ft wide by 8 ft " +
                "deep for a front-porch look. The beam span and tributary both move, so this is a " +
                "different member on the same stamped plan.",
          overrides: {
            "BM-ENT": { span: 12.0, trib: 5.0,
              note: "Elevation B stoop: 12 ft wide by 8 ft deep. Span is the 12 ft width on two " +
                    "posts; tributary is half the 8 ft depth plus the 1 ft eave = 5.0 ft." },
            "PST-ENT": { componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10, §8.20). " +
              "Elevation B loads this post harder than Elevation A: BM-ENT grows to a 12 ft span at " +
              "5.0 ft of tributary. Take the design load from the reaction this tool computes for " +
              "BM-ENT in THIS variant, not from the Elevation A figure. Uplift and both connections " +
              "remain out of scope (§8.11, §8.17), and C_P is not evaluated." }
          } },
        { id: "c", kind: "elevation", label: "Elevation C · carport in lieu of the garage",
          takeRate: 0.25,
          note: "The entry-level elevation in the value series and a real one in Texas and Florida: " +
                "the 12 ft x 22 ft garage becomes an open carport on posts. The garage door header " +
                "does not exist on these lots — the opening is the full 12 ft bay and it is spanned " +
                "by a treated beam, not a header in a wall. This is the variant that shows why an " +
                "elevation is not a finish selection: it deletes a member and adds a different one.",
          remove: ["HDR-GAR"],
          add: [
            { id: "BM-CAR", label: "Carport beam · treated", role: "beam",
              span: 12.0, trib: 11.0, count: 1, carries: "roof",
              exposure: "exterior", braced: false, skuGroup: "porch",
              note: "Elevation C only. The carport is the same 12 ft x 22 ft opening the garage " +
                    "occupied, and it sits under the main roof, so the beam spans the 12 ft width " +
                    "and carries half the 22 ft carport depth = 11.0 ft. It carries the ENCLOSED " +
                    "roof assembly and sits on the gypsum-ceiling deflection row, because the main " +
                    "roof runs over it — this is not an open porch soffit, which is why " +
                    "`roofAssembly: \"open\"` is deliberately absent." },
            { id: "PST-CAR", label: "Carport beam posts · BM-CAR", role: "post",
              count: 2, component: true,
              componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10 specifies C_P, §8.20 " +
                "evaluates no interaction equation). Elevation C only. Take the design load from the " +
                "end reaction this tool computes for BM-CAR in this variant. These are the tallest " +
                "and hardest-worked posts on the plan and they stand in the open: uplift, the " +
                "continuous load path and both the base and cap connections are out of scope " +
                "(§8.11, §8.17), and in a wind-governed market they are the design." }
          ] }
      ],
      options: [
        { id: "opt-tile", kind: "option", label: "Concrete tile roof", takeRate: 0.20,
          roofAssemblyKey: "roof_tile",
          note: "Sold as an elevation upgrade in Florida and Texas; standard in the HVHZ pack, where " +
                "taking it changes nothing because the pack already ships tile. Everywhere else it " +
                "is the largest gravity change available on this plan — 22 psf against 15 for the " +
                "enclosed roof, 17 against 10 for the open entry — and it moves every roof-carrying " +
                "mark at once. [market] take rate." },
        { id: "opt-8ft", kind: "option", label: "8 ft tall entry and slider", takeRate: 0.25,
          note: "An 8 ft head height in a 9'-1-1/8\" precut wall leaves 9.625 in of depth for the " +
                "header, less a double top plate and a shim. It changes no load at all and it can " +
                "still force a revision, because a member that does not fit is not a cheaper member. " +
                "Pair it with the tile option to see the case that actually produces one.",
          overrides: {
            "HDR-ENT": { headHeightIn: 96 },
            "HDR-SLD": { headHeightIn: 96 }
          } },
        { id: "opt-bed3-flex", kind: "option", label: "3rd bedroom in lieu of the flex room",
          takeRate: 0.55, movesNoMember: true,
          note: "The most-taken option in the series and it moves nothing structural, which is the " +
                "product feature: the trusses clear-span 32 ft onto the two 46 ft walls, so every " +
                "interior partition on this plan is non-bearing and a wall can be added, moved or " +
                "deleted without a member changing. Declared here rather than omitted, because an " +
                "option missing from the master set reads as an option nobody checked." }
      ]
    },

    {
      id: "townhome-1220",
      name: "Townhome 1220",
      summary: "1,220 sf conditioned + 220 sf one-car garage, two-story attached interior unit, 20 ft × 36 ft, party-wall bearing",
      lots: 96,
      geometry: {
        footprintFt: [20, 36],
        storeys: 2,
        grossSfPerFloor: 720,
        conditionedSf: 1220,
        garage: { widthFt: 11, depthFt: 20, sf: 220, cars: 1 },
        roofForm: "low gable, ridge front to back, common trusses party wall to party wall",
        trussSpanFt: 20,
        trussSpacingIn: 24,
        bearingLines: "the two party walls, plus one interior line running front to back 11.0 ft off " +
                      "the left party wall — it is the garage's inboard side wall, stacked, and it " +
                      "splits the 20 ft width into an 11.0 ft bay and a 9.0 ft bay.",
        coveredPatioFt: [20, 8],
        eaveOverhangFt: 1.0,
        note: "Stated design geometry, not a weight. This is an INTERIOR unit of an attached row: " +
              "both party walls are bearing and both are shared. An end unit is a different plan."
      },
      note: "Attached for-sale townhomes are a genuinely cookie-cutter product in DFW, Austin, " +
            "Charlotte, Raleigh, Orlando and Tampa, and this is the small front-load unit. The frame " +
            "follows from the attachment: both the roof trusses and the second-floor joists span the " +
            "20 ft width party wall to party wall, so the party walls carry the building and the " +
            "front and rear walls carry almost nothing. That is why the most conspicuous opening on " +
            "the elevation — the garage door — is the one mark on this plan the engine refuses. What " +
            "it carries is two storeys of wall, and this model has no wall dead load (register §L6). " +
            "Every other opening in the front and rear walls is the same wall-load-only condition; " +
            "the garage door is carried as the representative case rather than repeating the same " +
            "refusal eight times.",
      marks: [
        { id: "T-1", label: "Common roof truss · 20 ft clear span", role: "rafter",
          span: 20, runFt: 36, count: 19, carries: "roof", component: true,
          componentNote: "Truss package, deferred sealed submittal by the truss supplier. Out of " +
            "scope (calc-spec §8.6, §8.19). Count is the 36 ft depth at 24 in o.c. plus one. On an " +
            "attached unit the truss bears on the two party walls, which is what makes the front and " +
            "rear walls non-bearing." },

        { id: "FJ-1", label: "2nd floor joist · 11 ft bay, garage side", role: "joist",
          span: 11.0, runFt: 36, count: 28, skuGroup: "floor",
          note: "The interior bearing line sits 11.0 ft off the left party wall because that is the " +
                "garage's inboard side wall, stacked and continuous to the rear of the unit. The bay " +
                "runs the full 36 ft depth. Piece count follows the spacing the solver picks." },

        { id: "FJ-2", label: "2nd floor joist · 9 ft bay", role: "joist",
          span: 9.0, runFt: 26, count: 21, skuGroup: "floor",
          note: "20 ft unit width less the 11.0 ft bay = 9.0 ft. Run is the 36 ft depth less the " +
                "10 ft bath and laundry stretch carried by FJ-3. An 11 ft bay and a 9 ft bay is a " +
                "narrow enough spread that both land on the SAME depth in all six packs — so what " +
                "this plan actually poses is not a depth question but a species-band one, and the " +
                "unification pass prices it and declines: the extra lumber to put the whole floor " +
                "on one SKU costs more than the second SKU does. That is the answer being computed, " +
                "not the answer being assumed." },

        { id: "FJ-3", label: "2nd floor joist · bath and laundry", role: "joist",
          span: 9.0, runFt: 10, count: 9, skuGroup: "floor", floorAssembly: "floor_wet",
          note: "Same 9.0 ft bay as FJ-2, but tiled: ceramic on backer with thinset is +10 psf and a " +
                "bay carrying the plain residential assembly here is checked 31% light. It is also " +
                "the bay a single floor depth is decided on." },

        { id: "GB-1", label: "Flush girder · great-room opening in the bearing line", role: "beam",
          span: 12.0, trib: 10.0, count: 1, carries: "floor", braced: true,
          skuGroup: "girder", escalateExpected: true,
          note: "The interior bearing line is interrupted behind the garage for the great room. The " +
                "line takes half of each adjacent bay: 11.0/2 + 9.0/2 = 10.0 ft. 12.0 ft is the " +
                "opening. In the market this is a multi-ply LVL or a steel W-shape; the catalog " +
                "carries 48 W-shapes and calc-spec has no steel method, so this engine can design " +
                "neither answer and says so rather than printing a sawn member nobody would build." },

        { id: "HDR-ST", label: "Stair opening header · 2nd floor", role: "header",
          span: 12.5, trib: 2.75, count: 1, carries: "floor", braced: true, bearing: 3.0,
          skuGroup: "header",
          note: "12'-6\" clear opening = 15 treads at 10 in, derived from this pack's own 109.125 in " +
                "plate (16R at 7.6 in per IRC R311.7.1) — the same derivation the Two-Story 2450 " +
                "uses. The stair runs front to back against the left party wall, PERPENDICULAR to " +
                "the joists, so the header runs with the stair and catches the cut joists: the " +
                "opening is 3'-6\" wide, leaving tail joists spanning 9.0 - 3.5 = 5.5 ft to the " +
                "bearing line, t = 2.75 ft. NOT CHECKED HERE, and neither is anything else in this " +
                "assembly: the two double TRIMMERS take this header's end reaction as a " +
                "CONCENTRATED load (calc-spec §8.3 admits a uniform full-span load only), the upper " +
                "stringer lands on it as a second point load, and the joist-to-header connection is " +
                "a face-mount hanger (§8.17)." },

        { id: "HDR-GAR", label: "One-car garage door header · front wall", role: "header",
          span: 9.67, count: 1, bearing: 4.5,
          skuGroup: "header", headHeightIn: 84, wallPosition: "exterior-first-floor",
          underdetermined: true,
          underdeterminedNote:
            "NOT SIZED — what this header carries is a WALL, and this model has no wall dead load. " +
            "In an interior attached unit the roof trusses and the second-floor joists both span " +
            "party wall to party wall, so the front wall is a bearing line for NEITHER. This header " +
            "takes the second-floor rim joist, two storeys of wall standing on it, and the eave — " +
            "and ASSEMBLY{} has no wall entry of any kind (register §L6, still open). There is no " +
            "roof strip and no floor strip to substitute: a 16.0 ft tributary would be borrowed from " +
            "a detached plan, and a 0.7 ft one would be the rim alone with the wall silently " +
            "dropped. Both are inventions. Declare a wall dead load and the rim condition, then " +
            "derive it. Sizing it on a roof strip is precisely the defect §K5 refused on the garage " +
            "gable header, and the answer there was refusal too. `carries` is deliberately ABSENT " +
            "for the same reason the tributary is: what this member carries is a wall, and \"wall\" " +
            "is not a value this model has. Writing `carries: \"roof\"` to make the record look " +
            "complete would assert a load path the framing does not have, and it would put the mark " +
            "in the blast radius of the tile option, which reaches nothing here. `span` and " +
            "`bearing` are declared, because those two the plan does know." },

        { id: "BM-PAT", label: "Rear covered patio beam · treated", role: "beam",
          span: 10.0, trib: 5.0, count: 2, carries: "roof",
          exposure: "exterior", braced: false, skuGroup: "porch", roofAssembly: "open",
          note: "The rear covered patio is the full 20 ft unit width by 8 ft deep. The beam is at " +
                "the outer edge on three posts, so it is two 10.0 ft bays, and the tributary is half " +
                "the 8 ft depth plus the 1 ft eave overhang = 5.0 ft. Open roof: no ceiling, no " +
                "insulation, no-ceiling deflection row. Treated Southern Pine in all six markets — " +
                "this and the joists are what this engine is genuinely the right tool for here." },

        { id: "PST-PAT", label: "Rear patio beam posts · BM-PAT", role: "post",
          count: 3, component: true, reactionFrom: ["BM-PAT"],
          componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10 specifies C_P, §8.20 " +
            "states no interaction equation is evaluated, and engine.js implements neither). The " +
            "design load is BM-PAT's end reaction, printed live below for this region and this " +
            "variant. The CENTRE post takes two " +
            "bearings, so double it. Elevation B deepens the patio and raises all of these, and the " +
            "reaction printed below is the one for the variant on screen. Uplift, the continuous load path and both " +
            "the base and cap connections are out of scope (§8.11, §8.17). For a typical 9 ft 4x4, " +
            "C_P runs 0.25 to 0.35, so a check that omits it overstates axial capacity roughly " +
            "threefold." }
      ],
      elevations: [
        { id: "a", kind: "elevation", label: "Elevation A · interior unit, 8 ft covered patio",
          base: true, takeRate: 0.70,
          note: "The stamped base case and the great majority of the row: an interior unit with " +
                "both party walls shared." },
        { id: "b", kind: "elevation", label: "Elevation B · interior unit, 12 ft covered patio",
          takeRate: 0.30,
          note: "The rear patio grows from 8 ft to 12 ft deep on the lots that back to open space. " +
                "The beam run does not change, so the span does not either — only the tributary " +
                "moves. It is the cleanest single-driver variant in the book and the one to show " +
                "first: same member, same span, more roof on it.",
          overrides: {
            "BM-PAT": { trib: 7.0,
              note: "Elevation B patio: 20 ft wide by 12 ft deep, same three posts, so still two " +
                    "10.0 ft bays. Tributary is half the 12 ft depth plus the 1 ft eave = 7.0 ft." },
            "PST-PAT": { componentNote: "AXIAL MEMBER — NOT CHECKED HERE (calc-spec §4.10 specifies " +
              "C_P, §8.20 evaluates no interaction equation). Elevation B loads these posts 40% " +
              "harder than Elevation A: BM-PAT carries 7.0 ft of tributary instead of 5.0 over the " +
              "same 10 ft bays. Take the design load from the reaction this tool computes for BM-PAT " +
              "in THIS variant — the Elevation A figures on the base mark are not the envelope — and " +
              "double it at the CENTRE post, which takes two bearings. Uplift, the continuous load " +
              "path and both the base and cap connections remain out of scope (§8.11, §8.17)." }
          } }
      ],
      options: [
        { id: "opt-tile", kind: "option", label: "Concrete tile roof", takeRate: 0.15,
          roofAssemblyKey: "roof_tile",
          note: "Rare on attached product outside Florida and a no-op in the HVHZ pack, which " +
                "already ships tile. Carried because the tile decision is made once for the whole " +
                "row and it reaches the patio beam. [market] take rate." },
        { id: "opt-loft", kind: "option", label: "Loft in lieu of the 3rd bedroom", takeRate: 0.40,
          movesNoMember: true,
          note: "Deletes a partition on the second floor. The trusses clear-span 20 ft party wall to " +
                "party wall, so no second-floor partition on this plan is bearing and no member " +
                "moves. Declared rather than omitted: an option missing from the master set reads as " +
                "an option nobody checked." }
      ]
    }
  ];

  /* ============================================================
     MASTER SETS — one stamped plan, built many ways

     READ THIS BEFORE WIRING A UI TO IT.

     A production builder does not own a plan. He owns a MASTER SET: one plan,
     stamped once, built across ELEVATIONS (A/B/C — different roof forms and
     porch configurations over the same footprint) and structural OPTIONS
     (bonus room over the garage, extended covered patio, 4th bedroom, tile
     instead of shingle). Sizing the base case and letting an option move a
     bearing is how a revision gets manufactured after permit, and that is the
     most expensive line item in this model. So the variants are first-class
     data, not a note on a drawing.

     ---- what a plan declares ----

       plan.elevations : [Variant]   mutually exclusive. Exactly one is `base`.
                                     Their takeRates are a MIX and must sum to 1.
       plan.options    : [Variant]   independently selectable upgrades.
       plan.geometry   : the plan's own stated dimensions. NOT a weight and it
                         carries no class marker, for the same reason `span` and
                         `trib` do not: it is the design, not an estimate of the
                         world. Every span, tributary and count on the plan is
                         derived from it and the derivation is on the mark.

     A Variant is plain data:

       { id            "a" | "opt-tile"    unique across BOTH lists, no "+"
         kind          "elevation" | "option"
         label         what the builder calls it
         takeRate      [market] share of lots. Elevations: the mix, summing to
                       1.00. Options: the attach rate. A commercial estimate
                       with no code standing, like every other market number
                       in this file.
         base          elevations only — the stamped case the plan.marks ARE
         note          why it exists and what it does structurally
         movesNoMember true when the variant deliberately moves nothing this
                       engine sizes. REQUIRED when it touches no mark: a
                       variant that changes nothing and does not say so is
                       indistinguishable from one nobody checked, and the
                       helpers throw rather than let it pass.
         overrides     { "MARK-ID": { field: value, ... } }  patches on marks
                       that already exist. Absolute values, never deltas, so
                       applying twice is applying once.
         add           [ {full mark record} ]  marks only this variant builds
         remove        [ "MARK-ID" ]           marks this variant deletes
         roofAssemblyKey  an ASSEMBLY key replacing the pack's roof covering
                       for this variant. This is how tile is modelled: it
                       reaches every roof-carrying mark at once, including a
                       lanai beam, where it maps to the open-roof tile
                       assembly. Distinct from `mark.roofAssembly: "open"`,
                       which says there is no ceiling underneath — a different
                       question with a different answer.
         requiresElevation [ids]  options only — elevations that offer it
         excludes          [ids]  options only — mutually exclusive siblings

     Every one of those is validated. An override or a remove naming a mark the
     plan does not have, an added mark colliding with an existing id, an unknown
     assembly key, a duplicate variant id, an elevation mix that does not sum to
     1.00, an option that excludes itself — all throw. A typo in a master set is
     a member that is silently never checked, which is the exact failure class
     this file exists to make impossible.

     ---- what the UI consumes ----

       FM.weights.variantsFor(plan)
         { planId, elevations[], options[], combinations[], solvedFor, note }

         `elevations` and `options` are the declared set, normalised, each with
         an `overrides` map EXPANDED to every mark the variant moves — including
         marks it adds, marks it removes, and, for a roof-covering variant,
         every roof-carrying mark on the plan. That map is READ-ONLY reporting
         ("which marks move across this set"); the authored patch data is kept
         beside it under `declared`.

         `combinations` is the buildable list: every elevation on its own, every
         elevation with each option it offers, and — because that is where the
         revisions come from — every compatible PAIR of options that touches a
         common mark. Pass { combos: "all" } for the full power set, or
         { combos: "none" } for elevations only. Each entry:

           { id "c+opt-tile", planId, kind: "combination", label,
             elevationId, optionIds[], isBase, takeRate, lotsExpected,
             touches[], movesNoMember, roofAssemblyKey, notes[] }

         takeRate on a combination is the share of lots that include ALL of its
         parts — not the share configured exactly that way. Option rates are
         treated as independent and conditional on the elevation, which is a
         planning simplification and [market] like everything under it.

       FM.weights.planForVariant(plan, variantId)
         A plain plan object with the overrides applied, the removals gone and
         the additions in. Feed it straight to FM.solver.solvePlan(vp, pack) —
         the solver is untouched and does not know variants exist. It carries
         `variant` (the descriptor) and `ofPlan` (the base plan id).

       FM.weights.variantPlansFor(plan, opts)   the same, for every combination

       FM.weights.markFor(plan, markId, variantId)      resolved mark, or null
       FM.weights.demandFor(mark, plan, pack, variantId)  resolve, then size

       FM.weights.envelopeFor(plan, markId, pack, opts)
         The envelope report for ONE mark across the whole buildable set.

     ---- what the envelope does, and what it refuses to do ----

     The obvious implementation — take the worst span, the worst tributary and
     the heaviest assembly across the variants and size that — invents a member
     for a house nobody builds, and then quietly ships the extra depth on every
     lot. This one does not do that.

     envelopeFor() reports each variant's demand, and names a GOVERNING variant
     only when one of them dominates every other on every driver at once: span,
     tributary, dead, live, roof load and bearing all at least as large, depth
     budget no larger, and the same member regime (same `carries`, same
     deflection row, same duration factor, same service and bracing
     assumptions). Under those conditions a member that passes the governing
     variant passes all of them, because every load combination's demand is
     monotone in each driver and the capacity side is identical. That is a
     provable statement, and it is the only one this file is willing to make.

     When no variant dominates — Elevation B of the coastal duplex gets MORE
     tributary and LESS span than Elevation A, because a deeper porch buys a
     fourth post — it returns split: true and says so. The honest answer there
     is to size each variant and take the deepest pick:

         var vs = FM.weights.variantsFor(plan).combinations;
         var runs = vs.map(function (v) {
           return { v: v, r: FM.solver.solvePlan(
                             FM.weights.planForVariant(plan, v.id), pack) };
         });

     which is three lines, uses the solver unmodified, and gives a real answer
     per lot instead of a composite one for none of them.
     ============================================================ */

  function K(id) { return " " + id; }          /* author strings are never bare keys */
  function hasK(o, id) { return Object.prototype.hasOwnProperty.call(o, K(id)); }

  function shallowCopy(o) {
    var out = {}, k;
    for (k in o) if (Object.prototype.hasOwnProperty.call(o, k)) out[k] = o[k];
    return out;
  }

  function carriesOf(mark) {
    return mark.carries ||
      (Object.prototype.hasOwnProperty.call(CARRIES_DEFAULT, mark.role) ? CARRIES_DEFAULT[mark.role] : null);
  }
  /* which marks a change of roof COVERING reaches */
  function takesRoofCovering(mark) {
    var c = carriesOf(mark);
    return c === "roof" || c === "roof+floor";
  }

  var SYNTHETIC_BASE = {
    id: "base", kind: "elevation", base: true, takeRate: 1.0, synthetic: true,
    label: "As stamped",
    note: "This plan declares no elevations, so the stamped base case is the only variant."
  };

  /* built once per plan object, and it validates while it builds */
  var VCACHE = { keys: [], vals: [] };

  function variantIndex(plan) {
    var at = VCACHE.keys.indexOf(plan);
    if (at !== -1) return VCACHE.vals[at];
    var idx = buildVariantIndex(plan);
    VCACHE.keys.push(plan);
    VCACHE.vals.push(idx);
    return idx;
  }

  function buildVariantIndex(plan) {
    if (!plan || !plan.marks || !plan.marks.length) {
      throw new Error("the master-set helpers need a plan with marks");
    }
    var where = "plan " + (plan.id || "(no id)");
    var marksById = {};
    plan.marks.forEach(function (m) {
      if (hasK(marksById, m.id)) throw new Error(where + " declares two marks with id \"" + m.id + "\"");
      marksById[K(m.id)] = m;
    });

    var els = plan.elevations || [];
    var opts = plan.options || [];
    var ids = {};

    function checkCommon(v, kind) {
      if (!v || typeof v !== "object") throw new Error(where + " has a malformed " + kind);
      if (!v.id || typeof v.id !== "string") throw new Error(where + " has an " + kind + " with no id");
      if (v.id.indexOf("+") !== -1) {
        throw new Error(where + " " + kind + " id \"" + v.id + "\" contains '+', which is what " +
                        "composes a variant id — pick another");
      }
      if (hasK(ids, v.id)) {
        throw new Error(where + " declares two variants with id \"" + v.id + "\" — elevation and " +
                        "option ids share one namespace because a variant id names both");
      }
      ids[K(v.id)] = kind;
      if (!v.label) throw new Error(where + " " + kind + " \"" + v.id + "\" has no label");
      var tr = Number(v.takeRate);
      if (!isFinite(tr) || tr < 0 || tr > 1) {
        throw new Error(where + " " + kind + " \"" + v.id + "\" needs a takeRate in [0,1] — it is a " +
                        "[market] share of lots and the whole option model is priced off it");
      }
      if (v.roofAssemblyKey) {
        if (!Object.prototype.hasOwnProperty.call(ASSEMBLY, v.roofAssemblyKey)) {
          throw new Error(where + " " + kind + " \"" + v.id + "\" names unknown assembly \"" +
                          v.roofAssemblyKey + "\"");
        }
      }
      /* an added mark may be patched by the same variant that adds it */
      var localAdds = {};
      (v.add || []).forEach(function (m) {
        if (!m || !m.id) throw new Error(where + " " + kind + " \"" + v.id + "\" adds a mark with no id");
        if (hasK(marksById, m.id)) {
          throw new Error(where + " " + kind + " \"" + v.id + "\" adds mark \"" + m.id +
                          "\", which the base plan already has — patch it with `overrides` instead");
        }
        if (hasK(localAdds, m.id)) {
          throw new Error(where + " " + kind + " \"" + v.id + "\" adds mark \"" + m.id + "\" twice");
        }
        localAdds[K(m.id)] = true;
      });
      (v.remove || []).forEach(function (id) {
        if (!hasK(marksById, id)) {
          throw new Error(where + " " + kind + " \"" + v.id + "\" removes mark \"" + id +
                          "\", which is not on the plan");
        }
      });
      var ov = v.overrides || {};
      Object.keys(ov).forEach(function (id) {
        if (!hasK(marksById, id) && !hasK(localAdds, id)) {
          throw new Error(where + " " + kind + " \"" + v.id + "\" overrides mark \"" + id +
                          "\", which is not on the plan and is not added by this variant. A patch " +
                          "on a mark that does not exist is a member nobody checks.");
        }
        var p = ov[id];
        if (p && p.roofAssemblyKey &&
            !Object.prototype.hasOwnProperty.call(ASSEMBLY, p.roofAssemblyKey)) {
          throw new Error(where + " " + kind + " \"" + v.id + "\" sets unknown assembly \"" +
                          p.roofAssemblyKey + "\" on " + id);
        }
      });

      var touches = touchesOf(plan, v);
      if (!touches.length && !v.base && !v.movesNoMember) {
        throw new Error(where + " " + kind + " \"" + v.id + "\" moves no mark and does not declare " +
                        "`movesNoMember: true`. Say which it is — a variant that changes nothing " +
                        "and does not say so is indistinguishable from one nobody checked.");
      }
      if (touches.length && v.movesNoMember) {
        throw new Error(where + " " + kind + " \"" + v.id + "\" declares `movesNoMember: true` but " +
                        "moves " + touches.join(", "));
      }
    }

    var bases = 0, mix = 0;
    els.forEach(function (v) {
      checkCommon(v, "elevation");
      if (v.base) bases++;
      mix += Number(v.takeRate);
      if (v.requiresElevation || v.excludes) {
        throw new Error(where + " elevation \"" + v.id + "\" declares requiresElevation or excludes — " +
                        "elevations are already mutually exclusive");
      }
    });
    if (els.length) {
      if (bases !== 1) {
        throw new Error(where + " declares " + bases + " base elevations; exactly one must carry " +
                        "`base: true`, because the plan's own marks ARE that elevation");
      }
      if (Math.abs(mix - 1) > 0.001) {
        throw new Error(where + " elevation takeRates sum to " + mix.toFixed(3) +
                        ", not 1.000 — they are a mix of the lots, not independent attach rates");
      }
    }

    opts.forEach(function (v) {
      checkCommon(v, "option");
      if (v.base) throw new Error(where + " option \"" + v.id + "\" is marked base; only an elevation can be");
      (v.requiresElevation || []).forEach(function (e) {
        if (!els.some(function (x) { return x.id === e; })) {
          throw new Error(where + " option \"" + v.id + "\" requires elevation \"" + e + "\", which does not exist");
        }
      });
      (v.excludes || []).forEach(function (o) {
        if (o === v.id) throw new Error(where + " option \"" + v.id + "\" excludes itself");
        if (!opts.some(function (x) { return x.id === o; })) {
          throw new Error(where + " option \"" + v.id + "\" excludes \"" + o + "\", which does not exist");
        }
      });
    });

    return {
      plan: plan,
      marksById: marksById,
      elevations: els.length ? els : [SYNTHETIC_BASE],
      options: opts,
      syntheticBase: !els.length
    };
  }

  /* every mark this variant moves, including the ones a roof-covering change
     reaches without naming */
  function touchesOf(plan, v) {
    var seen = {}, out = [];
    function add(id) { if (!hasK(seen, id)) { seen[K(id)] = true; out.push(id); } }
    Object.keys(v.overrides || {}).forEach(add);
    (v.remove || []).forEach(add);
    (v.add || []).forEach(function (m) { add(m.id); });
    if (v.roofAssemblyKey) {
      plan.marks.forEach(function (m) { if (takesRoofCovering(m)) add(m.id); });
      (v.add || []).forEach(function (m) { if (takesRoofCovering(m)) add(m.id); });
    }
    return out;
  }

  /* the read-only reporting shape: `overrides` expanded to every mark that
     moves, with the authored data kept beside it */
  function publicVariant(plan, v) {
    var expanded = {};
    var removed = {}, added = {};
    (v.remove || []).forEach(function (id) { removed[K(id)] = true; });
    (v.add || []).forEach(function (m) { added[K(m.id)] = true; });
    touchesOf(plan, v).forEach(function (id) {
      var p = shallowCopy((v.overrides || {})[id] || {});
      if (hasK(removed, id)) p.removedByVariant = true;
      if (hasK(added, id)) p.addedByVariant = true;
      if (v.roofAssemblyKey && !p.roofAssemblyKey) p.roofAssemblyKey = v.roofAssemblyKey;
      expanded[id] = p;
    });
    return {
      id: v.id,
      kind: v.kind || (v.base || v.synthetic ? "elevation" : "option"),
      label: v.label,
      takeRate: Number(v.takeRate),
      takeRateCls: "market",
      base: !!v.base,
      note: v.note || "",
      movesNoMember: !!v.movesNoMember,
      roofAssemblyKey: v.roofAssemblyKey || null,
      requiresElevation: v.requiresElevation || null,
      excludes: v.excludes || null,
      touches: touchesOf(plan, v),
      /* READ-ONLY: which marks move. Not a patch source — use `declared`. */
      overrides: expanded,
      declared: { overrides: v.overrides || {}, add: v.add || [], remove: v.remove || [],
                  roofAssemblyKey: v.roofAssemblyKey || null }
    };
  }

  function elevationById(idx, id) {
    return idx.elevations.filter(function (e) { return e.id === id; })[0] || null;
  }
  function optionById(idx, id) {
    return idx.options.filter(function (o) { return o.id === id; })[0] || null;
  }
  function offeredOn(option, elevation) {
    return !option.requiresElevation || option.requiresElevation.indexOf(elevation.id) !== -1;
  }
  function compatible(a, b) {
    return (a.excludes || []).indexOf(b.id) === -1 && (b.excludes || []).indexOf(a.id) === -1;
  }

  /* "c+opt-tile" -> the elevation and the options, validated as a buildable
     combination. An empty/absent id is the base elevation with no options. */
  function partsOf(plan, variantId) {
    var idx = variantIndex(plan);
    var raw = (variantId === undefined || variantId === null) ? "" : String(variantId);
    var ids = raw.length ? raw.split("+") : [];
    var el;
    if (!ids.length) {
      el = idx.elevations.filter(function (e) { return e.base; })[0] || idx.elevations[0];
    } else {
      el = elevationById(idx, ids[0]);
      if (!el) {
        throw new Error("plan " + plan.id + " has no elevation \"" + ids[0] + "\" (variant \"" +
                        raw + "\"); a variant id is elevation first, then options");
      }
    }
    var seen = {}, options = [];
    ids.slice(1).forEach(function (oid) {
      var o = optionById(idx, oid);
      if (!o) throw new Error("plan " + plan.id + " has no option \"" + oid + "\" (variant \"" + raw + "\")");
      if (hasK(seen, oid)) throw new Error("variant \"" + raw + "\" names option \"" + oid + "\" twice");
      seen[K(oid)] = true;
      if (!offeredOn(o, el)) {
        throw new Error("option \"" + oid + "\" is not offered on elevation \"" + el.id + "\"");
      }
      options.forEach(function (p) {
        if (!compatible(p, o)) {
          throw new Error("options \"" + p.id + "\" and \"" + oid + "\" are mutually exclusive");
        }
      });
      options.push(o);
    });
    return { idx: idx, elevation: el, options: options, all: [el].concat(options) };
  }

  function descriptorFor(plan, elId, optIds) {
    var vid = [elId].concat(optIds || []).join("+");
    var p = partsOf(plan, vid);
    var take = Number(p.elevation.takeRate);
    p.options.forEach(function (o) { take *= Number(o.takeRate); });
    var touches = {}, order = [], roofKey = null, notes = [];
    p.all.forEach(function (v) {
      touchesOf(plan, v).forEach(function (id) {
        if (!hasK(touches, id)) { touches[K(id)] = true; order.push(id); }
      });
      if (v.roofAssemblyKey) roofKey = v.roofAssemblyKey;
      if (v.note) notes.push({ from: v.id, label: v.label, text: v.note });
    });
    return {
      id: vid,
      planId: plan.id,
      kind: "combination",
      label: p.all.map(function (v) { return v.label; }).join(" + "),
      elevationId: p.elevation.id,
      optionIds: p.options.map(function (o) { return o.id; }),
      isBase: !!p.elevation.base && !p.options.length,
      takeRate: take,
      takeRateCls: "market",
      takeRateBasis: "Elevation mix x option attach rates, treated as independent and conditional " +
                     "on the elevation. It is the share of lots that include ALL of these parts, " +
                     "not the share configured exactly this way. [market] — a commercial estimate " +
                     "with no code standing.",
      lotsExpected: isFinite(plan.lots) ? Math.round(plan.lots * take) : null,
      touches: order,
      movesNoMember: order.length === 0,
      roofAssemblyKey: roofKey,
      notes: notes
    };
  }

  function variantsFor(plan, opts) {
    opts = opts || {};
    var idx = variantIndex(plan);
    var mode = opts.combos || "single";
    var combos = [];

    idx.elevations.forEach(function (el) {
      combos.push(descriptorFor(plan, el.id, []));
      if (mode === "none") return;
      var offered = idx.options.filter(function (o) { return offeredOn(o, el); });
      offered.forEach(function (o) { combos.push(descriptorFor(plan, el.id, [o.id])); });

      if (mode === "all") {
        /* full power set, size >= 2, honouring excludes */
        var n = offered.length, mask, i, pick;
        for (mask = 0; mask < (1 << n); mask++) {
          pick = [];
          for (i = 0; i < n; i++) if (mask & (1 << i)) pick.push(offered[i]);
          if (pick.length < 2) continue;
          var ok = true;
          pick.forEach(function (a) {
            pick.forEach(function (b) { if (a !== b && !compatible(a, b)) ok = false; });
          });
          if (ok) combos.push(descriptorFor(plan, el.id, pick.map(function (o) { return o.id; })));
        }
      } else {
        /* Pairs are not decoration. A revision comes from two options landing on
           the SAME mark from opposite directions — tile driving a header deeper
           while an 8 ft head height caps how deep it may be. Emit exactly those. */
        for (var a = 0; a < offered.length; a++) {
          for (var b = a + 1; b < offered.length; b++) {
            if (!compatible(offered[a], offered[b])) continue;
            var ta = touchesOf(plan, offered[a]), tb = touchesOf(plan, offered[b]);
            var shares = ta.some(function (id) { return tb.indexOf(id) !== -1; });
            if (shares) combos.push(descriptorFor(plan, el.id, [offered[a].id, offered[b].id]));
          }
        }
      }
    });

    return {
      planId: plan.id,
      declaresVariants: !idx.syntheticBase || !!idx.options.length,
      elevations: idx.elevations.map(function (v) { return publicVariant(plan, v); }),
      options: idx.options.map(function (v) { return publicVariant(plan, v); }),
      combinations: combos,
      combos: mode,
      solvedFor: plan.variant ? (plan.variant.label || plan.variant.id) : undefined,
      lots: isFinite(plan.lots) ? plan.lots : null,
      note: "Elevations are mutually exclusive and their takeRates are the lot mix. Options are " +
            "independent attach rates. Both are [market] estimates and neither has code standing. " +
            "`combinations` is what the builder actually builds; feed each id to planForVariant() " +
            "and the result straight to FM.solver.solvePlan()."
    };
  }

  function applyTo(out, patch) {
    var k;
    for (k in patch) if (Object.prototype.hasOwnProperty.call(patch, k)) out[k] = patch[k];
    return out;
  }

  function resolveMark(plan, mark, parts, variantId) {
    var out = shallowCopy(mark);
    parts.all.forEach(function (v) {
      /* the variant's roof covering, unless the mark names its own */
      if (v.roofAssemblyKey && !out.roofAssemblyKey) out.roofAssemblyKey = v.roofAssemblyKey;
      var patch = (v.overrides || {})[mark.id];
      if (patch) applyTo(out, patch);
    });
    if (variantId) { out.variantId = variantId; out.baseMarkId = mark.id; }
    return out;
  }

  function markFor(plan, markId, variantId) {
    var parts = partsOf(plan, variantId);
    var removed = false, found = null;
    parts.all.forEach(function (v) {
      (v.remove || []).forEach(function (id) { if (id === markId) removed = true; });
      (v.add || []).forEach(function (m) { if (m.id === markId) found = m; });
    });
    if (removed) return null;
    if (!found) found = parts.idx.marksById[K(markId)] || null;
    if (!found) return null;
    return resolveMark(plan, found, parts, variantId);
  }

  function planForVariant(plan, variantId) {
    if (plan.ofPlan) {
      throw new Error("plan " + plan.id + " is already a variant of " + plan.ofPlan +
                      " — take variants of the master set, not of a variant");
    }
    var parts = partsOf(plan, variantId);
    var d = descriptorFor(plan, parts.elevation.id, parts.options.map(function (o) { return o.id; }));

    var removed = {}, adds = [], addSeen = {};
    parts.all.forEach(function (v) {
      (v.remove || []).forEach(function (id) { removed[K(id)] = v.id; });
      (v.add || []).forEach(function (m) {
        if (hasK(addSeen, m.id)) {
          throw new Error("variant \"" + d.id + "\" of plan " + plan.id + " adds mark \"" + m.id +
                          "\" from two parts at once");
        }
        addSeen[K(m.id)] = true;
        adds.push(m);
      });
    });

    var marks = [];
    plan.marks.forEach(function (mk) {
      if (hasK(removed, mk.id)) return;
      marks.push(resolveMark(plan, mk, parts, d.id));
    });
    adds.forEach(function (mk) {
      if (hasK(removed, mk.id)) return;
      marks.push(resolveMark(plan, mk, parts, d.id));
    });

    return merge(plan, {
      id: plan.id + "--" + d.id.replace(/[^a-zA-Z0-9._-]+/g, "-"),
      name: plan.name + " · " + d.label,
      summary: plan.summary + " — " + d.label,
      marks: marks,
      variant: d,
      ofPlan: plan.id,
      lots: d.lotsExpected === null ? plan.lots : d.lotsExpected
    });
  }

  function variantPlansFor(plan, opts) {
    return variantsFor(plan, opts).combinations.map(function (v) {
      return planForVariant(plan, v.id);
    });
  }

  /* the drivers a simple-span uniformly loaded member's demand is monotone in.
     Bigger is worse for all of them except maxDepthIn, where smaller is. */
  var ENVELOPE_DRIVERS = ["span", "trib", "dead", "live", "roofLoad"];

  /* two variants are only comparable by driver if they are the same KIND of
     member — the same deflection row, duration factor, service condition and
     bracing assumption. Otherwise the capacity side moves too and dominance on
     the load side proves nothing. */
  function regimeOf(d) {
    return [d.carries, d.memberUse, d.roofType, d.repetitive ? 1 : 0,
            d.wet ? 1 : 0, d.braced ? 1 : 0, d.treated ? 1 : 0].join("/");
  }

  function envelopeFor(plan, markId, pack, opts) {
    var vs = variantsFor(plan, opts).combinations;
    var rows = vs.map(function (v) {
      var row = { variantId: v.id, label: v.label, takeRate: v.takeRate,
                  lotsExpected: v.lotsExpected, present: true, sized: false };
      var mk = markFor(plan, markId, v.id);
      if (!mk) {
        row.present = false;
        row.note = "Not built in this variant.";
        return row;
      }
      row.mark = mk;
      var appl = applicability(mk, pack);
      if (!appl.applicable) {
        row.notSized = { reason: appl.reason, note: appl.note };
        return row;
      }
      var d = demandFor(mk, plan, pack);
      row.sized = true;
      row.demand = d;
      row.regime = regimeOf(d);
      row.drivers = {
        span: Number(d.span) || 0,
        trib: Number(d.trib) || 0,
        dead: Number(d.dead) || 0,
        live: Number(d.live) || 0,
        roofLoad: Number(d.roofLoad) || 0,
        bearing: Number(d.bearing) || 0,
        maxDepthIn: d.maxDepthIn === undefined || d.maxDepthIn === null ? Infinity : Number(d.maxDepthIn)
      };
      return row;
    });

    var sized = rows.filter(function (r) { return r.sized; });
    var out = {
      planId: plan.id, markId: markId, packId: pack.id,
      variants: rows,
      builtOn: rows.filter(function (r) { return r.present; }).length,
      absentOn: rows.filter(function (r) { return !r.present; }).map(function (r) { return r.variantId; }),
      sizedOn: sized.length
    };

    if (!sized.length) {
      out.split = false;
      out.governedBy = null;
      out.note = "This mark is not sized in any variant — see the per-variant reason. Nothing to " +
                 "envelope.";
      return out;
    }

    /* worst value of each driver, and who supplies it */
    var worst = {};
    ["span", "trib", "dead", "live", "roofLoad", "bearing", "maxDepthIn"].forEach(function (k) {
      var smallerIsWorse = (k === "maxDepthIn" || k === "bearing");
      var best = null;
      sized.forEach(function (r) {
        var v = r.drivers[k];
        if (best === null || (smallerIsWorse ? v < best : v > best)) best = v;
      });
      worst[k] = { value: best, smallerIsWorse: smallerIsWorse,
                   by: sized.filter(function (r) { return r.drivers[k] === best; })
                            .map(function (r) { return r.variantId; }) };
    });
    out.drivers = worst;

    var regimes = {};
    sized.forEach(function (r) { regimes[K(r.regime)] = true; });
    var oneRegime = Object.keys(regimes).length === 1;

    function dominates(a, b) {
      var ok = true;
      ENVELOPE_DRIVERS.forEach(function (k) { if (a.drivers[k] < b.drivers[k]) ok = false; });
      if (a.drivers.bearing > b.drivers.bearing) ok = false;      /* less bearing is worse */
      if (a.drivers.maxDepthIn > b.drivers.maxDepthIn) ok = false; /* less depth budget is worse */
      return ok;
    }

    var gov = oneRegime ? sized.filter(function (a) {
      return sized.every(function (b) { return a === b || dominates(a, b); });
    })[0] : null;

    if (gov) {
      out.split = false;
      out.governedBy = gov.variantId;
      out.governing = gov;
      out.note = "One variant governs: \"" + gov.label + "\" is at least as severe as every other " +
                 "buildable variant on span, tributary, dead, live and roof load, gives away no " +
                 "bearing and no depth budget, and is the same kind of member (" + gov.regime +
                 "). Demand is monotone in each of those and the capacity side is identical, so a " +
                 "member that passes this variant passes all " + sized.length + ". Size this one " +
                 "and the master set is covered.";
    } else {
      out.split = true;
      out.governedBy = null;
      out.note = "NO SINGLE VARIANT GOVERNS" +
        (oneRegime ? ". " : " — and the variants are not even the same kind of member (" +
                     Object.keys(regimes).length + " regimes), so the capacity side moves too. ") +
        "The drivers pull in different directions across the set, so there is no one demand that " +
        "covers it. This tool will NOT compose a maximum out of them: the worst span from one " +
        "elevation with the worst tributary from another is a member for a house nobody builds, " +
        "and it ships the extra depth on every lot. Size each variant — " +
        "FM.solver.solvePlan(FM.weights.planForVariant(plan, id), pack) — and take the deepest " +
        "pick. The per-variant demands are in `variants` and the worst value of each driver, with " +
        "the variant that supplies it, is in `drivers`.";
    }
    return out;
  }

  /* ---------------- assembly ---------------- */

  function merge() {
    var out = {}, i, k, src;
    for (i = 0; i < arguments.length; i++) {
      src = arguments[i];
      if (!src) continue;
      for (k in src) if (Object.prototype.hasOwnProperty.call(src, k)) out[k] = src[k];
    }
    return out;
  }

  function packById(id) { return PACKS.filter(function (p) { return p.id === id; })[0] || null; }
  function planById(id) { return PLANS.filter(function (p) { return p.id === id; })[0] || null; }

  function policyFor(pack, plan, role) {
    var weights = merge(BASE.weights, pack.weights, plan && plan.weights);
    function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k) ? o[k] : undefined; }
    var ladder = own(LADDERS, role) || LADDERS.rafter;
    var spacings = own(REPETITIVE, role) ? (own(SPACINGS, role) || [16, 24]) : [0];

    return {
      id: pack.id + (role ? ":" + role : ""),
      name: pack.name + (role ? " · " + role : ""),
      role: role || null,
      maxDCR: (plan && plan.maxDCR) || pack.maxDCR || BASE.maxDCR,
      minAvailability: pack.minAvailability === undefined ? BASE.minAvailability : pack.minAvailability,
      specialOrderBelow: pack.specialOrderBelow === undefined ? BASE.specialOrderBelow : pack.specialOrderBelow,
      gammaPcf: pack.gammaPcf || BASE.gammaPcf,
      palette: pack.palette,
      ladder: ladder,
      spacings: spacings,
      weights: weights,
      incisedWhenTreated: INCISED_WHEN_TREATED,
      unifyBonus: UNIFY_BONUS,
      priceOf: function (cand, demand) {
        var p = pack.palette.filter(function (x) {
          return x.species === cand.species && x.grade === cand.grade;
        })[0];
        /* the treated channel, not the wet-service one. A treated-but-dry porch
           beam is stocked as treated; keying this off moisture made the flagship
           Texas lanai beam a special order in the one market that racks it. */
        var channel = (demand && (demand.treated || demand.wet)) ? STOCK.wet : STOCK.dry;
        var sizeAvail = Object.prototype.hasOwnProperty.call(channel, cand.size)
          ? channel[cand.size] : 0.25;
        if (!isFinite(sizeAvail)) sizeAvail = 0.25;
        return {
          bfUSD: p && isFinite(p.bfUSD) ? p.bfUSD : weights.baseBfUSD,
          cullRate: p && isFinite(p.cullRate) ? p.cullRate : 0,
          availability: (p && isFinite(p.stockFactor) ? p.stockFactor : 0.5) * sizeAvail
        };
      }
    };
  }

  function demandFor(mark, plan, pack, variantId) {
    /* A master set is one plan built many ways. Passing `variantId` resolves the
       mark against that elevation/option set FIRST and then sizes what the
       builder will actually build on that lot. Omitting it sizes the stamped
       base case, which is what the solver does today — the fourth argument is
       additive and every existing three-argument call is unchanged. */
    if (variantId && plan) {
      var rv = markFor(plan, mark.id, variantId);
      if (!rv) {
        throw new Error("mark " + mark.id + " is not built in variant \"" + variantId +
                        "\" of plan " + plan.id + " — it is removed by that elevation or option, " +
                        "so it has no demand there");
      }
      mark = rv;
    }
    var role = mark.role;
    var L = pack.loads;
    function assembly(name) {
      /* a typo throws loudly; a prototype key used to return silently and
         launder into a dead load of zero. Both must fail the same way. */
      if (!Object.prototype.hasOwnProperty.call(ASSEMBLY, name)) {
        throw new Error("unknown assembly \"" + name + "\" in pack " + pack.id);
      }
      return ASSEMBLY[name].psf;
    }
    /* The roof covering is the one assembly a plan OPTION changes — tile over
       shingle is the single largest gravity difference in this product, and the
       fl-hvhz pack already says so. A mark (or the variant that resolved it)
       may therefore name its own roof assembly; absent that, the pack's. Note
       that `mark.roofAssembly === "open"` is a different field with a different
       job — it says there is no ceiling under this member, not which covering
       is on top of it. */
    var roofKey = mark.roofAssemblyKey || L.roofAssembly;
    var roofDead = assembly(roofKey);
    var floorDead = assembly(mark.floorAssembly || L.floorAssembly);
    var ceilingDead = assembly(L.ceilingAssembly);

    var d = {
      role: role,
      span: mark.span,
      trib: mark.trib || 0,
      repetitive: Object.prototype.hasOwnProperty.call(REPETITIVE, role) ? !!REPETITIVE[role] : false,
      wet: mark.exposure === "exterior" ? !!pack.service.exteriorWet : !!pack.service.wet,
      braced: mark.braced === undefined ? true : !!mark.braced,
      /* a header bears on jack studs — 1.5 in per jack, not the 3.5 in a beam
         gets on a post cap. Defaulting a header to 3.5 in was 2.33x optimistic
         on bearing, which is the governing check more often than it looks. */
      /* Bearing became a DESIGN INPUT the moment the header default moved to one
         jack stud: it governs 3 of 66 picks and produced 4 of 24 escalations, and
         no mark declared it. Same ruling as `carries` — a header must state its
         jack count rather than inherit one. */
      bearing: mark.bearing || (Object.prototype.hasOwnProperty.call(REPETITIVE, role) && REPETITIVE[role]
        ? 3.0 : (role === "header" ? null : 3.5)),
      roofType: L.roofType
    };

    if (mark.underdetermined) {
      throw new Error("mark " + mark.id + " is underdetermined and must not be sized: " +
                      (mark.underdeterminedNote || UNDETERMINED_GENERIC));
    }
    if (role === "header" && !mark.bearing) {
      throw new Error("header " + mark.id + " must declare `bearing` (jack studs x 1.5 in) — " +
                      "it governs the check and produced false escalations as a silent default");
    }
    var carries = mark.carries ||
      (Object.prototype.hasOwnProperty.call(CARRIES_DEFAULT, role) ? CARRIES_DEFAULT[role] : null);
    if (!carries) {
      throw new Error("mark " + mark.id + " is a " + role + " and must declare what it carries");
    }
    if (carries === "roof" && mark.roofAssembly === "open") carries = "roof-open";
    if (!Object.prototype.hasOwnProperty.call(DEFL_BY_CARRIES, carries)) {
      throw new Error("unknown carries \"" + carries + "\" on mark " + mark.id);
    }
    d.carries = carries;
    d.memberUse = mark.memberUse || DEFL_BY_CARRIES[carries] || "floor";

    /* Treatment, not moisture, is what forces incising — and it is what decides
       which stock channel the member comes out of. A treated-but-dry porch beam
       in the I-35 corridor is still treated. */
    d.treated = mark.treated !== undefined ? !!mark.treated : (mark.exposure === "exterior");

    /* a header's depth budget is set by the plate and the head height, less a
       double top plate and a shim. A member that does not fit is not a cheaper
       member — it is a plate-height change and a revision. */
    if (mark.maxDepthIn) d.maxDepthIn = mark.maxDepthIn;
    else if (mark.headHeightIn && pack.plateHeightIn) {
      d.maxDepthIn = pack.plateHeightIn - mark.headHeightIn - 3.0 - 0.5;
    }

    /* a porch or lanai beam carries an OPEN roof — no ceiling, no insulation.
       Which covering is on it still matters: tile over an open lanai is 17 psf
       against shingle's 10. Keyed off the EFFECTIVE roof assembly so a tile
       OPTION reaches the lanai beam, not just the pack that ships tile. */
    if (mark.roofAssembly === "open") {
      roofDead = assembly(roofKey === "roof_tile" ? "roof_open_tile" : "roof_open");
    }
    d.roofAssemblyKey = roofKey;

    if (carries === "roof" || carries === "roof-open") {
      d.dead = roofDead; d.live = 0; d.roofLoad = L.roofLoad;
    } else if (carries === "ceiling") {
      d.dead = ceilingDead; d.live = L.ceilingLive; d.roofLoad = 0; d.roofType = "snow";
    } else if (carries === "floor") {
      d.dead = floorDead; d.live = L.floorLive; d.roofLoad = 0; d.roofType = "snow";
    } else if (carries === "deck") {
      d.dead = ASSEMBLY.deck_pt.psf; d.live = L.deckLive; d.roofLoad = 0; d.roofType = "snow";
    } else if (carries === "roof+floor") {
      /* Two load paths with two different tributary widths cannot be expressed by
         one number: HDR-1 meant the floor tributary and HDR-SLD meant the sum, and
         the model applied both full load sets over whichever it was given. The
         engine takes one tributary, so convert exactly — total line load is
         q_roof*t_roof + q_floor*t_floor, expressed as psf over t = t_roof + t_floor. */
      var tR = Number(mark.tribRoof), tF = Number(mark.tribFloor);
      if (!(tR >= 0) || !(tF >= 0) || !(tR + tF > 0)) {
        throw new Error("mark " + mark.id + " carries roof+floor and must declare tribRoof and tribFloor");
      }
      var tT = tR + tF;
      d.trib = tT;
      d.roofLoadActual = L.roofLoad;   /* the advisory must see the real load, not the blend */
      d.tribRoof = tR; d.tribFloor = tF;
      d.dead = (roofDead * tR + floorDead * tF) / tT;
      d.live = (L.floorLive * tF) / tT;
      d.roofLoad = (L.roofLoad * tR) / tT;
    } else {
      d.dead = roofDead; d.live = 0; d.roofLoad = L.roofLoad;
    }
    return d;
  }

  /* a mark can be structurally irrelevant in a region — a wood exterior header
     in a concrete-block market is not a member anybody will build */
  function applicability(mark, pack, plan, variantId) {
    if (variantId && plan) {
      var rv = markFor(plan, mark.id, variantId);
      if (!rv) {
        return { applicable: false, reason: "not-in-variant", note:
          "NOT BUILT IN THIS VARIANT — the elevation or option set \"" + variantId + "\" removes " +
          "this mark. It is not a failure and not out of scope; those lots simply do not have this " +
          "member. It stays on the master set because other lots do." };
      }
      mark = rv;
    }
    if (mark.underdetermined) {
      return { applicable: false, reason: "underdetermined",
               note: mark.underdeterminedNote || UNDETERMINED_GENERIC };
    }
    if (mark.component && mark.role === "post") {
      return { applicable: false, reason: "out-of-scope", note: mark.componentNote };
    }
    if (mark.component) {
      return { applicable: false, reason: "component", note: mark.componentNote ||
               "Manufactured component — designed by its supplier as a deferred sealed submittal." };
    }
    /* Only a FIRST-FLOOR EXTERIOR opening is spanned by a concrete lintel. The
       rule used to fire on every header in a block market, which deleted the
       second-floor window headers and the interior roof+floor headers — the very
       members the pack's own note says ARE wood. A mark must opt in by declaring
       itself exterior and first-floor. */
    if (mark.role === "header" && pack.exteriorWall === "cmu" &&
        mark.wallPosition === "exterior-first-floor") {
      return { applicable: false, reason: "wall-system", note: pack.exteriorWallNote ||
               "First-floor exterior walls are concrete block in this market; this opening is spanned by a concrete lintel, not a wood header." };
    }
    return { applicable: true };
  }

  FM.weights = {
    BASE: BASE, PACKS: PACKS, PLANS: PLANS,
    ASSEMBLY: ASSEMBLY, LIVE: LIVE, STOCK: STOCK,
    LADDERS: LADDERS, SPACINGS: SPACINGS, REPETITIVE: REPETITIVE,
    CARRIES_DEFAULT: CARRIES_DEFAULT, DEFL_BY_CARRIES: DEFL_BY_CARRIES,
    UNIFY_BONUS: UNIFY_BONUS,
    INCISED_WHEN_TREATED: INCISED_WHEN_TREATED,
    policyFor: policyFor, demandFor: demandFor, applicability: applicability,
    packById: packById, planById: planById,

    /* master sets — see the contract block above variantsFor() */
    variantsFor: variantsFor,
    planForVariant: planForVariant,
    variantPlansFor: variantPlansFor,
    markFor: markFor,
    envelopeFor: envelopeFor
  };
})();
