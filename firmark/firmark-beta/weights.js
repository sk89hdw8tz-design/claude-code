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
     lumber. calc-spec §4.8 specifies it; engine.js does NOT implement it.
     Refractory species must be incised to take preservative, so checking a
     treated one without C_i overstates bending and shear by 20%. The solver
     therefore excludes these species from any wet-service demand rather than
     checking them optimistically. Southern Pine takes treatment without
     incising, which is why it survives the gate — and why it is the porch-beam
     species of the entire Southeast. */
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
    deck:              { psf: 40, cls: "code", cite: "IRC Table R301.5 / R507 — exterior decks and balconies" },
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
          note: "Dry framing only — excluded from treated marks because the engine does not apply C_i." }
      ],
      maxDCR: 0.90
    },

    {
      id: "nc-piedmont",
      name: "North Carolina · Piedmont",
      markets: "Charlotte · Raleigh · Greensboro",
      states: ["NC"],
      code: { family: "IRC", cls: "code",
        note: "North Carolina Residential Code, adopted statewide by the Building Code Council — local jurisdictions " +
              "do not write their own technical amendments. The 2024 NCRC (2021 IRC basis) was delayed by statute to " +
              "1 July 2025. VERIFY the currently effective edition and any permit-date grandfathering with OSFM." },
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
          note: "Not a Florida staple, and excluded from treated marks." }
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
          carries: "roof", skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor",
          note: "Tributary is half the truss span where the trusses bear on this wall. A 4 ft " +
                "tributary here would follow from neither the 46 ft clear span nor the gable end." },
        { id: "HDR-GAR-G", label: "Garage header · gable end over the door", role: "header", span: 16.67, trib: 2.0, count: 1,
          carries: "roof", skuGroup: "header", headHeightIn: 84, wallPosition: "exterior-first-floor",
          note: "Same opening as HDR-GAR-B. The truss direction is the entire design: 2 ft of tributary here, 11 ft there." },
        { id: "HDR-GAR-B", label: "Garage header · trusses bearing", role: "header", span: 16.67, trib: 11.0, count: 1,
          carries: "roof", skuGroup: "header", headHeightIn: 84, wallPosition: "exterior-first-floor", escalateExpected: true,
          note: "Under a bearing truss line this is a 3-ply LVL or a girder truss in every one of these markets." },
        { id: "HDR-SLD", label: "Rear slider header · under clear-span truss", role: "header", span: 12.0, trib: 23.0, count: 1,
          carries: "roof", skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor", escalateExpected: true,
          note: "Tributary is half the 46 ft truss span. This is why exterior openings in production single-stories " +
                "are almost always engineered." }
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
          note: "Solves shallow, and is the prime unification target — one floor depth is worth more than the lumber." },
        { id: "GB-1", label: "Centre floor girder", role: "beam", span: 12.0, trib: 14.25, count: 2, skuGroup: "girder",
          braced: true, escalateExpected: true, carries: "floor",
          note: "Multi-ply LVL or a steel W-shape in the market. The catalog carries 48 W-shapes; the calc-spec has " +
                "no steel method, so this engine cannot design either answer." },
        { id: "HDR-1", label: "1st-floor opening header", role: "header", span: 5.0, count: 10,
          carries: "roof+floor", tribRoof: 19.0, tribFloor: 6.75,
          skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor" },
        { id: "HDR-2", label: "2nd-floor window header", role: "header", span: 4.0, trib: 12.0, count: 12,
          carries: "roof", skuGroup: "header", headHeightIn: 80,
          note: "Second floor, so it is a wood header even in a concrete-block market." },
        { id: "DK-1", label: "Deck joist · treated", role: "deck", span: 12.0, runFt: 20, count: 16, skuGroup: "deck",
          exposure: "exterior",
          note: "North Carolina production homes very often carry one. IRC R507, 40 psf live." },
        { id: "DK-2", label: "Deck beam · treated", role: "beam", span: 8.0, trib: 6.0, count: 2, skuGroup: "deckbeam",
          exposure: "exterior", braced: false, carries: "deck",
          note: "Carries the deck, not a roof. Checked as a roof beam it printed a 4x8 at 59% that is " +
                "overstressed at 1.05 against 40 psf of deck live load." }
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
          skuGroup: "header", headHeightIn: 80, wallPosition: "exterior-first-floor",
          escalateExpected: true }
      ]
    }
  ];

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

  function demandFor(mark, plan, pack) {
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
    var roofDead = assembly(L.roofAssembly);
    var floorDead = assembly(L.floorAssembly);
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
      bearing: mark.bearing ||
        (Object.prototype.hasOwnProperty.call(REPETITIVE, role) && REPETITIVE[role] ? 3.0
          : (role === "header" ? 1.5 : 3.5)),
      roofType: L.roofType
    };

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

    /* a porch or lanai beam carries an OPEN roof — no ceiling, no insulation */
    if (mark.roofAssembly === "open") {
      roofDead = assembly(L.roofAssembly === "roof_tile" ? "roof_open_tile" : "roof_open");
    }

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
  function applicability(mark, pack) {
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
    packById: packById, planById: planById
  };
})();
