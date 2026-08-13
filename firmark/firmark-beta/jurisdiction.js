/* ============================================================
   FM.juris — code adoption and site hazard parameters for
   TEXAS, FLORIDA and NORTH CAROLINA.

   READ THIS BEFORE TRUSTING ANYTHING BELOW.

   ------------------------------------------------------------
   1. WHAT THIS FILE IS

   A jurisdiction table. It answers "which code, which edition,
   which hazard parameters, which submittals" for the places
   cookie-cutter single-storey housing actually gets built in
   these three states. It answers those questions the way the
   rest of this product answers questions: with a provenance
   class and a citation on every value, and with an explicit,
   never-empty list of what the user must still confirm.

   Provenance classes are weights.js's, unchanged:

     code    A code, standard or statutory value, reproduced
             with its citation. Never invented.
     site    SITE-SPECIFIC and unknowable from a place name —
             basic wind speed, ground snow, exposure, seismic.
             What is carried is a PLANNING value with a band.
             The ASCE 7 Hazard Tool is the authority.
     market  A commercial preference weight. No code standing.
             (This module publishes none.)

   ------------------------------------------------------------
   2. WHAT `confirmed` MEANS, AND WHY NOTHING SAYS "primary"

   Every record also carries `confirmed`:

     primary     the primary document was retrieved and read
     secondary   a search-engine summary of an official page;
                 the page itself was NOT opened
     unverified  inference, or a commercial/secondary source
                 with no official page behind it

   NOTHING IN THIS FILE IS `primary`. The build environment
   blocks outbound page fetches at the egress proxy — every
   official source below (ncosfm.gov, tdi.texas.gov,
   floridabuilding.org, codes.iccsafe.org, the municipal code
   libraries) refused. Every fact here was therefore established
   from a search-engine summary of a page that could not be
   opened, and every one of them is in `mustVerify` for that
   reason. See FM.juris.RESEARCH.

   That is a real limitation and it is stated rather than
   papered over. A `secondary` adoption date is good enough to
   plan around and NOT good enough to permit against.

   ------------------------------------------------------------
   3. THE THREE STATES ARE THREE DIFFERENT MACHINES

   TEXAS has no statewide residential code ENFORCEMENT. Local
   Government Code §214.212 makes the IRC as it existed on
   1 May 2012 the municipal residential code, but the EDITION
   actually enforced is a city ordinance question and varies
   city by city — San Antonio is on the 2024 IRC while Austin is
   on the 2021. Unincorporated county land may have no adopted
   code, no permit and no inspection at all. And on the coast
   there is a SECOND, INDEPENDENT regime: TDI/TWIA windstorm
   certification (WPI-1 before construction, WPI-8 at
   completion), which since 1 April 2026 requires the 2024 IRC —
   a NEWER code than the city underneath it enforces. A coastal
   Texas set must satisfy both, and they are not the same code.

   FLORIDA is one statewide code. The HVHZ is its own regime and
   it is MIAMI-DADE AND BROWARD COUNTIES ONLY — not "South
   Florida", not Palm Beach, not Monroe. Product approval / NOA
   is a submittal requirement, not a design load. And the
   wind-borne debris region is drawn by WIND SPEED CONTOUR and
   distance from the coastal mean high water line, NOT by county
   line — so this file refuses to publish a county-wide
   windborne-debris answer anywhere the code does not fix one.

   NORTH CAROLINA is one statewide code with no local technical
   amendments — and the edition in force is NOT the one most
   people assume. See §4.

   ------------------------------------------------------------
   4. THE HEADLINE FINDING: NORTH CAROLINA IS STILL ON THE 2018
      CODE, WHICH IS A 2015 IRC / ASCE 7-10 BASIS.

   The 2024 NCRC (2021 IRC basis) has been adopted and its
   effective date has been pushed three times:

     S.L. 2024-57 §1F.3   -> 1 July 2025
     S.L. 2025-2          -> 12 months AFTER the State Fire
                             Marshal certifies (a) the fully
                             adopted 2024 Code is published and
                             distributed and (b) the Residential
                             Code Council is fully constituted

   As of the NC licensing board's 15 February 2026 update that
   certification had not happened, and the earliest possible
   effective date stated was 1 MARCH 2027. Until then the 2018
   NCRC governs.

   This matters to this engine specifically: an engineered
   design under 2018 NCRC R301.1.3 references ASCE 7-10, not
   ASCE 7-16 and not ASCE 7-22. A North Carolina wind number
   taken off an ASCE 7-16 or 7-22 map is off the wrong map.

   weights.js `nc-piedmont` carries "delayed by statute to
   1 July 2025", which is stale by two rounds of legislation.
   It does say VERIFY, so it is not a lie — but a reader would
   come away believing a 2021-IRC-basis code is in force. It is
   not. Flagged in the report; that file is not mine to edit.

   ------------------------------------------------------------
   5. THE SECOND HEADLINE: FLORIDA'S CODE EXPIRES THIS YEAR.

   FBC 8th Edition (2023) is in force. The 9th Edition (2026)
   is expected effective 31 DECEMBER 2026 — inside the planning
   horizon of any set being drawn today. Under F.S. §553.73(4)
   a local TECHNICAL amendment is rendered void when the code is
   updated (Community Rating System amendments excepted), so
   every local technical amendment in Florida dies at that date
   too. A Florida plan set drawn now against the 8th Edition
   will be reviewed against the 9th if the permit application
   lands after it takes effect.

   ------------------------------------------------------------
   6. WHAT THIS FILE WILL NOT DO

   It will not publish an exposure category. ASCE 7 §26.7
   exposure is a fetch determination made from the ground
   roughness upwind of the actual site; it is not a property of
   a city. `wind.exposure` is null everywhere, on purpose, with
   `exposureCommon` carried beside it as an advisory that is
   explicitly not a design value.

   It will not publish S_s or S_1. Those come from the USGS /
   ASCE 7 Hazard Tool by coordinate. They are null everywhere.

   It will not publish a county-wide windborne-debris answer
   except where the code itself fixes one (the HVHZ). Everywhere
   else `windborneDebris.inRegion` is null and the CRITERION is
   published instead, with `likely` beside it.

   It will not publish a frost depth it could not establish.
   `frostDepthIn.inches` is null in every jurisdiction whose
   Table R301.2(1) value could not be read, and the code-minimum
   footing depth (IRC/FBC-R R403.1.4, 12 in below undisturbed
   ground) is carried separately because that one IS knowable.

   An honest gap beats a confident error.
   ============================================================ */

(function () {
  "use strict";

  /* The date every adoption fact, wind band and hazard value in
     this file was checked. Bump it only when the facts are
     actually re-checked, never to make the table look fresh. */
  var CHECKED = "2026-08-13";

  function has(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

  function copyInto(dst, src) {
    var k;
    for (k in src) if (has(src, k)) dst[k] = src[k];
    return dst;
  }

  /* ------------------------------------------------------------
     Sources. Every `src` field below names one of these ids.
     `retrieved` records HOW it was obtained, because "I read the
     ordinance" and "a search engine summarised a page about the
     ordinance" are not the same evidence and must not print the
     same way.
     ------------------------------------------------------------ */

  var SOURCES = [
    { id: "tx-lgc-214",   what: "Tex. Loc. Gov't Code §214.212 — IRC as it existed 1 May 2012 is the municipal residential code",
      url: "https://statutes.capitol.texas.gov/Docs/LG/pdf/LG.214.pdf", retrieved: "search-summary" },
    { id: "tx-lgc-233",   what: "Tex. Loc. Gov't Code §§233.151–233.153 — residential building standards in unincorporated areas of certain counties",
      url: "https://law.justia.com/codes/texas/2022/local-government-code/title-7/subtitle-b/chapter-233/subchapter-f/section-233-153/", retrieved: "search-summary" },
    { id: "tdi-codes",    what: "TDI adopted windstorm building codes — 2024 IRC/IBC for WPI-1 applications from 1 April 2026; 2018 IRC/IBC for 1 Sep 2020 – 31 Mar 2026",
      url: "https://www.tdi.texas.gov/wind/adopted-codes.html", retrieved: "search-summary" },
    { id: "tdi-cat",      what: "TDI designated catastrophe areas — the 14 first-tier coastal counties plus parts of Harris County east of SH 146",
      url: "https://www.tdi.texas.gov/wind/maps/index.html", retrieved: "search-summary" },
    { id: "tdi-wpi8",     what: "TDI windstorm inspection process — WPI-1 before construction, TDI-appointed qualified inspector or TDI-appointed Texas PE, WPI-8 certificate of compliance",
      url: "https://www.tdi.texas.gov/tips/need-windstorm-inspection.html", retrieved: "search-summary" },
    { id: "tdi-rule",     what: "28 TAC §5.4008 / TWIA Division 6 building codes, amendment adopted 21 Nov 2025, effective 1 April 2026",
      url: "https://www.sos.state.tx.us/texreg/archive/February132026/Adopted%20Rules/28.INSURANCE.html", retrieved: "search-summary" },
    { id: "hou-ord",      what: "City of Houston Ordinance 2023-907 — 2021 I-Codes incl. IRC, effective 1 January 2024",
      url: "https://www.iccsafe.org/about/periodicals-and-newsroom/houstons-city-council-approves-adoption-of-the-2021-international-codes/", retrieved: "search-summary" },
    { id: "hou-amend",    what: "Houston Amendments to the 2021 International Residential Code — R301.2.1 requires an ASCE 7 Hazard Tool printout for the property address attached to the plans",
      url: "https://www.houstonpermittingcenter.org/media/7376/download?inline=", retrieved: "search-summary" },
    { id: "dal-code",     what: "Dallas City Code Chapter 57 — 2021 IRC with Dallas amendments; 2021 I-Codes effective 12 May 2023, Ordinance 33099 amendments effective 23 May 2025",
      url: "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/know_code.aspx", retrieved: "search-summary" },
    { id: "ftw-ord",      what: "Fort Worth Ordinance 25383-03-2022 / City Code §7-61 — 2021 IRC adopted with local amendments",
      url: "https://codelibrary.amlegal.com/codes/ftworth/latest/ftworth_tx/0-0-0-8128", retrieved: "search-summary" },
    { id: "sat-ord",      what: "San Antonio Chapter 10 Building-Related Codes — 2024 I-Codes incl. IRC, Ordinance 2025-01-30-0075, effective 1 May 2025",
      url: "https://docsonline.sanantonio.gov/DSDUploads/2024Ch10Building-RelatedCodesFinal.pdf", retrieved: "search-summary" },
    { id: "aus-code",     what: "Austin City Code Ch. 25-12 Article 11 (Residential Code) — 2021 IRC, effective 1 September 2021",
      url: "https://www.austintexas.gov/page/building-technical-codes", retrieved: "search-summary" },
    { id: "cc-ord",       what: "City of Corpus Christi Code Chapter 14 — 2021 I-Codes incl. IRC with local amendments, effective 1 August 2023",
      url: "https://www.corpuschristitx.gov/department-directory/development-services/construction-codes-and-ordinances/", retrieved: "search-summary" },
    { id: "galv-ord",     what: "City of Galveston Code Chapter 10 / Ordinance 23-012 — 2021 I-Codes incl. IRC with local amendments",
      url: "https://www.galvestontx.gov/219/Building-Codes-Permitting", retrieved: "search-summary" },
    { id: "fbc8",         what: "Florida Building Code, Residential, 8th Edition (2023) — 2021 IRC basis, ASCE 7-22 referenced, effective 31 December 2023",
      url: "https://codes.iccsafe.org/content/FLRC2023P1", retrieved: "search-summary" },
    { id: "fbc9",         what: "Florida Building Code 9th Edition (2026) — base 8th Edition FBC-R updated by the 2024 IRC, expected effective 31 December 2026",
      url: "https://www.floridabuilding.org/fbc/thecode/2026_Code_Development/Analysis_Code_Changes/Analysis_of_changes_9th_Edition-2026-FBC-Residential.pdf", retrieved: "search-summary" },
    { id: "fs-553-73",    what: "F.S. §553.73(4) — local technical amendments: more stringent only, once per 6 months, local-conditions finding, transmitted within 30 days, VOID when the code is updated (CRS amendments excepted)",
      url: "https://www.flsenate.gov/Laws/Statutes/2023/553.73", retrieved: "search-summary" },
    { id: "fl-hvhz",      what: "HVHZ is Broward and Miami-Dade counties only — FBC-B §1620 / FBC-R Chapter 44",
      url: "https://up.codes/s/high-velocity-hurricane-zones-wind-loads", retrieved: "search-summary" },
    { id: "fl-prod",      what: "Florida Product Approval, F.A.C. Rule 61G20-3 and the BCIS; Miami-Dade NOA is a local approval; a statewide approval must carry the HVHZ endorsement to be used in the HVHZ",
      url: "https://www.floridabuilding.org/fbc/commission/FBC_0615/Commission_Education_POC/588/588-1-MATERIAL.pdf", retrieved: "search-summary" },
    { id: "fl-wbdr",      what: "Florida Building Commission investigation of the wind-borne debris regions in ASCE 7-22",
      url: "https://www.floridabuilding.org/fbc/commission/FBC_0125/hrac/Interim_Report_WBDR.pdf", retrieved: "search-summary" },
    { id: "fl-asce722",   what: "Florida Building Commission fact sheet — wind load impacts from ASCE 7-22 in the 8th Edition",
      url: "http://www.floridabuilding.org/fbc/thecode/2023_Code_Development/2023_Code_Resources/ASCE-7-22_Wind_Loads_Fact_Sheet.pdf", retrieved: "search-summary" },
    { id: "nc-gs-143",    what: "N.C.G.S. §143-138 — the NC State Building Code is adopted by the Building Code Council / Residential Code Council; local rules require Council approval",
      url: "https://www.ncleg.gov/EnactedLegislation/Statutes/PDF/BySection/Chapter_143/GS_143-138.pdf", retrieved: "search-summary" },
    { id: "nc-osfm",      what: "NC OSFM — 2024 NC State Building Code implementation delayed; 2018 Code remains in effect until the delayed date",
      url: "https://www.ncosfm.gov/news/press-releases/2025/04/07/north-carolina-delays-implementation-2024-state-building-code", retrieved: "search-summary" },
    { id: "nc-lic-2026",  what: "NC licensing board code update, 15 February 2026 — effective date at least one year after the General Assembly approves the Residential Code Council nominees; earliest possible 1 March 2027; exams remain on the 2018 editions",
      url: "https://nclicensing.org/wp-content/uploads/2026/02/2026-02-15-Code-Update.pdf", retrieved: "search-summary" },
    { id: "ncrc2018",     what: "2018 NC State Building Code: Residential Code — 2015 IRC basis, adopted 13 June 2017, effective 1 January 2019",
      url: "https://codes.iccsafe.org/content/NCRC2018", retrieved: "search-summary" },
    { id: "ncrc-asce710", what: "OSFM formal interpretation — 2018 NCRC R301.1.3 engineered design references ASCE 7-10",
      url: "https://www.ncosfm.gov/formal-interpretations/20240229-residential-structures-2018-ncrc-r30113-engineered-design-and-asce-7-2010/open", retrieved: "search-summary" },
    { id: "ncrc-ch45",    what: "NCRC Chapter 45 High Wind Zones — North Carolina-specific chapter",
      url: "https://codes.iccsafe.org/content/NCRC2018P2/chapter-45-high-wind-zones", retrieved: "search-summary" },
    { id: "asce7",        what: "ASCE 7 Hazard Tool — the authority for basic wind speed, ground snow and seismic ground motion at a coordinate",
      url: "https://asce7hazardtool.online/", retrieved: "not-fetched" }
  ];

  /* What could NOT be established here, and why. This is published
     so a reader can tell the difference between "the module says
     nothing about X" and "the module could not find out about X". */
  var RESEARCH = {
    checked: CHECKED,
    method: "WebSearch only.",
    blocked: "Outbound page fetches are blocked at this environment's egress proxy. Every official " +
             "source in SOURCES refused, including ncosfm.gov, tdi.texas.gov, floridabuilding.org, " +
             "codes.iccsafe.org, up.codes, flsenate.gov, statutes.capitol.texas.gov and every " +
             "municipal code library. curl through the proxy returns 'CONNECT tunnel failed, 403'.",
    consequence: "No record in this file is `confirmed: \"primary\"`. Everything is a search-engine " +
                 "summary of a page that was never opened. That is enough to plan against and NOT " +
                 "enough to permit against.",
    couldNotEstablish: [
      "Any jurisdiction's completed IRC/FBC-R Table R301.2(1) — the climatic and geographic design " +
      "criteria table is filled in by the adopting jurisdiction and is not published in a form a " +
      "search could reach. Wind speed, ground snow, frost line depth, seismic design category, " +
      "termite and decay probability all live in that table and all of them are therefore banded " +
      "or null here rather than stated.",
      "S_s and S_1 for any jurisdiction. Null everywhere.",
      "County-level ground snow load for North Carolina. The NCRC tabulates p_g by county; the " +
      "table was not retrievable.",
      "Whether Tex. Loc. Gov't Code ch. 233 Subchapter F applies to Galveston County, and whether " +
      "Galveston County has adopted any residential building code for its unincorporated area.",
      "Whether the City of Austin has a 2024 IRC adoption in progress. Only the 2021 adoption " +
      "(effective 1 September 2021) could be confirmed, and a five-year-old adoption is exactly " +
      "the kind of fact that goes stale without anyone noticing.",
      "The exact wind-borne debris region boundary in any Florida or North Carolina county. It is " +
      "a contour, not a county line, and it cannot be tabulated by jurisdiction at all."
    ]
  };

  /* ------------------------------------------------------------
     Record builders. Every one stamps cls, cite, checked, src and
     confirmed. A value that cannot be stamped does not ship.
     ------------------------------------------------------------ */

  var WIND_SITE_NOTE =
    "MUST BE CONFIRMED FOR THE ACTUAL SITE. This is a planning value, not a lookup. The basic " +
    "design wind speed is read at the site's coordinates from the ASCE 7 edition the ADOPTED code " +
    "references, and from the code's own figure where it publishes one. Risk Category II.";

  function windOf(o) {
    return {
      vMph: has(o, "vMph") ? o.vMph : null,
      band: o.band || null,
      riskCategory: "II",
      asce: o.asce,                       /* the ASCE 7 edition the ADOPTED code references */
      codeFixed: !!o.codeFixed,           /* true only where the code itself fixes the number */
      exposure: null,                     /* never asserted — see file header §6 */
      exposureCommon: o.exposureCommon || null,
      exposureNote: "NOT A DESIGN VALUE. ASCE 7 §26.7 exposure is a fetch determination made from " +
                    "the ground roughness upwind of the actual site. `exposureCommon` is what this " +
                    "market usually turns out to be and it is an advisory only.",
      siteConfirmRequired: true,
      cls: "site",
      cite: o.cite,
      src: o.src,
      confirmed: o.confirmed || "unverified",
      basis: o.basis,
      checked: CHECKED,
      note: WIND_SITE_NOTE + (o.note ? " " + o.note : "")
    };
  }

  function snowOf(o) {
    return {
      pgPsf: has(o, "pgPsf") ? o.pgPsf : null,
      band: o.band || null,
      cls: o.cls || "site",
      cite: o.cite,
      src: o.src,
      confirmed: o.confirmed || "unverified",
      checked: CHECKED,
      note: o.note || "Ground snow load is a mapped site value. Confirm against the ASCE 7 Hazard " +
                      "Tool and the adopted code's county table."
    };
  }

  function seismicOf(o) {
    return {
      sdc: has(o, "sdc") ? o.sdc : null,
      ss: null,
      s1: null,
      cls: "site",
      cite: o.cite,
      src: o.src,
      confirmed: o.confirmed || "unverified",
      checked: CHECKED,
      note: "S_s and S_1 are NOT published here. They come from the USGS / ASCE 7 Hazard Tool by " +
            "coordinate and no jurisdiction-level value is defensible. The seismic design category " +
            "carried is a planning value. " + (o.note || "")
    };
  }

  function frostOf(o) {
    return {
      inches: has(o, "inches") ? o.inches : null,
      minFootingDepthIn: 12,
      cls: "code",
      cite: o.cite,
      src: o.src,
      confirmed: o.confirmed || "unverified",
      checked: CHECKED,
      note: "`inches` is the jurisdiction's published frost line depth from Table R301.2(1); null " +
            "means it could not be established here. `minFootingDepthIn` is the separate code " +
            "minimum — exterior footings not less than 12 in below undisturbed ground surface, " +
            "IRC/FBC-R R403.1.4 — which applies regardless of frost and IS knowable. " +
            (o.note || "")
    };
  }

  function levelOf(o) {
    return {
      level: has(o, "level") ? o.level : null,
      cls: "code",
      cite: o.cite,
      src: o.src,
      confirmed: o.confirmed || "unverified",
      checked: CHECKED,
      note: o.note || ""
    };
  }

  var WBD_CRITERION =
    "The wind-borne debris region is drawn by WIND SPEED CONTOUR and distance from the coastal mean " +
    "high water line, NOT by county line: within 1 mile of the coastal mean high water line where " +
    "the basic design wind speed is 130 mph or greater, or anywhere the basic design wind speed is " +
    "140 mph or greater (IRC / FBC-R R301.2.1.2). A single county routinely has land inside and " +
    "outside it. This module publishes `inRegion` only where the code itself fixes the answer.";

  function wbdOf(o) {
    return {
      inRegion: has(o, "inRegion") ? o.inRegion : null,
      likely: has(o, "likely") ? o.likely : null,
      determinedBy: o.determinedBy || "site",
      criterion: WBD_CRITERION,
      cls: o.cls || "code",
      cite: o.cite,
      src: o.src,
      confirmed: o.confirmed || "unverified",
      checked: CHECKED,
      note: o.note || ""
    };
  }

  function codeRec(o) {
    return {
      name: o.name,
      edition: o.edition,
      basis: o.basis,
      asce: o.asce || null,
      adopted: o.adopted,
      status: o.status || "in force",
      cls: "code",
      cite: o.cite,
      src: o.src,
      confirmed: o.confirmed || "secondary",
      checked: CHECKED,
      note: o.note || ""
    };
  }

  function amend(text, cite, src, extra) {
    var a = { text: text, cite: cite, src: src, cls: "code",
              confirmed: "secondary", checked: CHECKED };
    if (extra) copyInto(a, extra);
    return a;
  }

  function mv(o) {
    return {
      id: o.id,
      what: o.what,
      why: o.why,
      check: o.check,               /* what to check it AGAINST — never omitted */
      authority: o.authority,
      severity: o.severity || "major",
      checked: CHECKED
    };
  }

  /* ------------------------------------------------------------
     STATE-LEVEL RECORDS
     ------------------------------------------------------------ */

  var STATE_MV = {
    TX: [
      mv({ id: "tx-edition", severity: "blocking",
        what: "The IRC edition the municipality actually enforces today.",
        why: "Texas has no statewide residential code enforcement. §214.212 sets the 2012 IRC as the " +
             "floor and every home-rule city adopts newer editions by its own ordinance on its own " +
             "clock. San Antonio is on the 2024 IRC and Austin is on the 2021; two cities 80 miles " +
             "apart are on different codes and different ASCE 7 wind maps.",
        check: "The city's currently adopted construction-code ordinance and its effective date.",
        authority: "The adopting municipality's building official." }),
      mv({ id: "tx-annex", severity: "major",
        what: "Whether the site is inside city limits, in the ETJ, or in unincorporated county.",
        why: "The three have three different answers, and the third is often 'no adopted code, no " +
             "permit and no inspection'. §233.153 applies only to certain counties, defaults to the " +
             "IRC as published 1 May 2008 or the county seat's edition, and the county may not " +
             "charge a fee to enforce it — which is why in practice much of it is not enforced.",
        check: "Tex. Loc. Gov't Code §§233.151–233.153, the county, and the nearest city's ETJ map.",
        authority: "The county and the municipality whose ETJ may reach the site." })
    ],
    FL: [
      mv({ id: "fl-9th", severity: "blocking",
        what: "Whether the permit application will land before or after the FBC 9th Edition (2026) " +
              "effective date, expected 31 December 2026.",
        why: "The edition is set by the date the permit application is submitted and accepted. A set " +
             "drawn now against the 8th Edition is reviewed against the 9th if it is submitted after " +
             "that date. The 9th also expands the 160 mph impact-resistant envelope to new " +
             "construction within five miles of tidal water, which is an opening-protection change " +
             "reaching well inland of anything the 8th Edition required.",
        check: "floridabuilding.org for the adopted 9th Edition and its confirmed effective date.",
        authority: "Florida Building Commission." }),
      mv({ id: "fl-local", severity: "major",
        what: "Any local technical amendment in force in this jurisdiction.",
        why: "F.S. §553.73(4) permits more-stringent local technical amendments, and they are real — " +
             "but they are VOID when the code is updated (Community Rating System amendments " +
             "excepted). So the answer changes twice: once when a local amendment is adopted, and " +
             "again when the 9th Edition wipes it.",
        check: "The local government's adopted amendments as transmitted to the Commission, and " +
               "whether they survive the 9th Edition.",
        authority: "The local building department; Florida Building Commission." })
    ],
    NC: [
      mv({ id: "nc-edition", severity: "blocking",
        what: "Which edition of the NC Residential Code is effective on the permit date — the 2018 " +
              "NCRC (2015 IRC / ASCE 7-10) or the 2024 NCRC (2021 IRC).",
        why: "The 2024 NCRC has been adopted and delayed three times: S.L. 2024-57 §1F.3 to 1 July " +
             "2025, then S.L. 2025-2 to 12 months after the State Fire Marshal certifies both " +
             "publication/distribution of the 2024 Code AND that the Residential Code Council is " +
             "fully constituted. As of the 15 February 2026 licensing-board update that had not " +
             "happened and the earliest possible date stated was 1 March 2027. This module carries " +
             "the 2018 NCRC as in force because that is what the last confirmable statement said, " +
             "and that statement is six months old.",
        check: "NC OSFM's current codes page and the certification status of the Residential Code " +
               "Council. This is the single most perishable fact in this file.",
        authority: "NC Office of State Fire Marshal." }),
      mv({ id: "nc-asce", severity: "major",
        what: "Which ASCE 7 edition an engineered design must use.",
        why: "2018 NCRC R301.1.3 engineered design references ASCE 7-10. A wind speed taken off an " +
             "ASCE 7-16 or ASCE 7-22 map is off the wrong map for a North Carolina permit today, and " +
             "will be off the wrong map in the other direction the moment the 2024 NCRC takes effect.",
        check: "The referenced-standards chapter of the edition actually in force on the permit date.",
        authority: "NC Office of State Fire Marshal." })
    ]
  };

  var STATES_DATA = {

    TX: {
      code: "TX",
      name: "Texas",
      statewide: false,
      enforcement: "municipal",
      model: "IRC",
      authority: "The adopting municipality. No state agency reviews or inspects one- and two-family " +
                 "dwellings in Texas. On the coast, TDI runs a separate windstorm certification " +
                 "programme that is an insurance-eligibility regime, not a building department.",
      summary: "There is no statewide residential building code ENFORCEMENT in Texas. Statute makes " +
               "the IRC the municipal residential code, but the EDITION is a city-by-city ordinance " +
               "question, unincorporated county land may have no code at all, and the coast carries " +
               "a second and independent windstorm regime on its own code cycle.",
      statute: [
        codeRec({ name: "Municipal residential code floor", edition: "2012 IRC",
          basis: "The International Residential Code as it existed on 1 May 2012",
          adopted: "statutory", status: "statutory floor",
          cite: "Tex. Loc. Gov't Code §214.212 — the IRC as it existed on 1 May 2012 is adopted as the " +
                "municipal residential building code and applies to all construction, alteration, " +
                "remodeling, enlargement and repair of residential structures in a municipality. A " +
                "municipality may adopt local amendments after a public hearing, and may review and " +
                "consider ICC amendments made after 1 May 2012.",
          src: "tx-lgc-214",
          note: "This is a FLOOR, not the answer. It tells you the least a Texas city can be on. It " +
                "does not tell you what any particular city is on, and every jurisdiction in this " +
                "module is on something newer." }),
        codeRec({ name: "Unincorporated area residential standards", edition: "2008 IRC or the county seat's edition",
          basis: "The IRC as published 1 May 2008, or the IRC edition applicable in the county seat",
          adopted: "statutory", status: "applies only to certain counties",
          cite: "Tex. Loc. Gov't Code §§233.151–233.153 — new single-family or duplex construction in " +
                "the unincorporated area of a county to which Subchapter F applies must conform to the " +
                "IRC as published 1 May 2008 or the edition applicable in that county's county seat; " +
                "applies to construction begun after 1 September 2009; a municipality's ETJ building " +
                "code controls where one exists; and the county may not charge a fee to defray the " +
                "cost of enforcing the standards.",
          src: "tx-lgc-233",
          note: "The no-fee clause is why this is weakly enforced in practice. WHICH counties " +
                "Subchapter F reaches could not be established here — see RESEARCH." })
      ],
      windstormRegime: {
        name: "TDI / TWIA windstorm certification",
        appliesTo: "The designated catastrophe area — the 14 first-tier coastal counties plus parts " +
                   "of Harris County east of SH 146.",
        counties: ["Aransas", "Brazoria", "Calhoun", "Cameron", "Chambers", "Galveston", "Jefferson",
                   "Kenedy", "Kleberg", "Matagorda", "Nueces", "Refugio", "San Patricio", "Willacy"],
        partialCounties: [
          { county: "Harris", extent: "east of SH 146, and within the city limits of La Porte, " +
                                      "Morgan's Point, Pasadena, Seabrook and Shore Acres" }
        ],
        cls: "code",
        cite: "TDI designated catastrophe areas; Tex. Ins. Code §§2210.251–2210.252, 2210.258–2210.259.",
        src: "tdi-cat",
        confirmed: "secondary",
        checked: CHECKED,
        codeEditions: [
          codeRec({ name: "TDI windstorm building code", edition: "2024 IRC / 2024 IBC",
            basis: "2024 IRC", adopted: "2026-04-01", status: "in force",
            asce: "ASCE 7-22",
            cite: "28 TAC §5.4008 as amended, adopted 21 November 2025 — WPI-1 applications from " +
                  "1 April 2026 must be certified to the 2024 IRC or the 2024 IBC.",
            src: "tdi-rule" }),
          codeRec({ name: "TDI windstorm building code — prior", edition: "2018 IRC / 2018 IBC",
            basis: "2018 IRC", adopted: "2020-09-01", status: "superseded 1 April 2026",
            asce: "ASCE 7-16",
            cite: "28 TAC §5.4008 — construction in the designated catastrophe areas on and after " +
                  "1 September 2020 and before 1 April 2026 complies with the 2018 IRC/IBC.",
            src: "tdi-rule" })
        ],
        trap: "THE WINDSTORM CODE AND THE CITY CODE ARE NOT THE SAME CODE AND ARE NOT ON THE SAME " +
              "CYCLE. Since 1 April 2026 TDI requires the 2024 IRC for a WPI-8, while Corpus Christi " +
              "and Galveston are enforcing the 2021 IRC for the permit. A coastal Texas set must " +
              "satisfy BOTH, and where they differ the governing requirement is whichever is more " +
              "demanding for the item in question. A set that satisfies only the city passes plan " +
              "review and then fails windstorm certification, which is discovered after framing.",
        process: "WPI-1 application filed BEFORE construction begins; oversight by a TDI-appointed " +
                 "qualified inspector or a Texas-licensed professional engineer appointed by TDI; " +
                 "WPI-8 certificate of compliance issued by TDI at completion.",
        processCite: "TDI windstorm inspection programme.",
        processSrc: "tdi-wpi8"
      },
      localAmendments: {
        permitted: true,
        cls: "code",
        cite: "Tex. Loc. Gov't Code §214.212 — a municipality may establish procedures to adopt local " +
              "amendments that add, modify or remove requirements, after a public hearing.",
        src: "tx-lgc-214",
        confirmed: "secondary",
        checked: CHECKED,
        note: "Texas municipal amendments are unbounded in direction — they may REMOVE requirements, " +
              "not only add them. That is the opposite of Florida, where §553.73(4) permits only " +
              "more-stringent technical amendments. A Texas amendment set must be read, not assumed."
      },
      mustVerify: STATE_MV.TX
    },

    FL: {
      code: "FL",
      name: "Florida",
      statewide: true,
      enforcement: "statewide code, local administration",
      model: "IRC (as amended into the FBC)",
      authority: "Florida Building Commission adopts the code; the local building department " +
                 "administers and enforces it.",
      summary: "One statewide code. Local governments administer it and may adopt more-stringent " +
               "technical amendments under a narrow statutory test, which are then wiped by the next " +
               "code edition. The HVHZ is a separate regime covering exactly two counties. Product " +
               "approval is a submittal requirement, not a design load.",
      statute: [
        codeRec({ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
          basis: "2021 IRC", asce: "ASCE 7-22", adopted: "2023-12-31", status: "in force",
          cite: "Florida Building Code, Residential, 8th Edition (2023), effective 31 December 2023; " +
                "2021 IRC model basis with Florida amendments; references ASCE 7-22 (the change from " +
                "ASCE 7-16 reached 125 code sections).",
          src: "fbc8" }),
        codeRec({ name: "Florida Building Code, Residential", edition: "9th Edition (2026)",
          basis: "8th Edition (2023) FBC-R updated by the 2024 IRC", asce: "ASCE 7-22",
          adopted: "expected 2026-12-31", status: "PENDING — not yet in force as of " + CHECKED,
          cite: "Analysis of Changes for the 9th Edition (2026) Florida Building Code, Residential — " +
                "the 8th Edition FBC-R is the base code and the 2024 IRC is the model code used to " +
                "update it; not all 2024 IRC changes are included. Expected effective 31 December 2026.",
          src: "fbc9",
          note: "Structural consequence to watch: the 9th Edition expands the 160 mph impact-resistant " +
                "envelope to new construction within FIVE MILES of tidal water. That is an " +
                "opening-protection requirement reaching far inland of the 1-mile wind-borne debris " +
                "line, and it lands inside the planning horizon of anything drawn today." })
      ],
      hvhz: {
        counties: ["Miami-Dade", "Broward"],
        cls: "code",
        cite: "High-Velocity Hurricane Zone — Broward and Miami-Dade counties only. FBC-B §1620 " +
              "(HVHZ wind loads); FBC-R Chapter 44 (High-Velocity Hurricane Zones).",
        src: "fl-hvhz",
        confirmed: "secondary",
        checked: CHECKED,
        note: "TWO COUNTIES. Not 'South Florida'. Palm Beach is not in it. Monroe is not in it. " +
              "Collier is not in it. The HVHZ boundary is a county line and it is the one hazard " +
              "boundary in Florida that IS a county line — which is exactly why people extend it to " +
              "neighbours by analogy and get it wrong."
      },
      productApproval: {
        statewide: "Florida Product Approval — F.A.C. Rule 61G20-3, listed in the BCIS under an FL " +
                   "number. Required for products in the regulated categories (building envelope " +
                   "components and other elements in habitable spaces).",
        hvhz: "Inside the HVHZ a product must carry either a Miami-Dade NOA or a statewide Florida " +
              "Product Approval that bears the HVHZ endorsement. A statewide approval WITHOUT the " +
              "HVHZ endorsement cannot be installed in Miami-Dade or Broward and is rejected at " +
              "permit review. A Miami-Dade NOA is a local approval.",
        cls: "code",
        cite: "F.A.C. Rule 61G20-3, Florida Product Approval; Miami-Dade NOA programme.",
        src: "fl-prod",
        confirmed: "secondary",
        checked: CHECKED,
        note: "This is a SUBMITTAL requirement, not a design load. It does not change a member size. " +
              "It decides whether the package can be permitted at all, and nothing this engine sizes " +
              "carries an approval of any kind."
      },
      localAmendments: {
        permitted: true,
        direction: "more stringent only",
        cls: "code",
        cite: "F.S. §553.73(4) — a local government may adopt technical amendments applying solely " +
              "within its jurisdiction that are MORE STRINGENT than the FBC, not more than once every " +
              "6 months, on a governing-body finding based on a review of local conditions " +
              "demonstrating that local conditions justify them; transmitted to the Commission within " +
              "30 days. A technical amendment is rendered VOID when the code is updated, unless it " +
              "was adopted for the purpose of participating in the Community Rating System.",
        src: "fs-553-73",
        confirmed: "secondary",
        checked: CHECKED,
        note: "The void-on-update rule is the one to plan around: every local technical amendment in " +
              "Florida dies at the 9th Edition unless it is a CRS amendment."
      },
      mustVerify: STATE_MV.FL
    },

    NC: {
      code: "NC",
      name: "North Carolina",
      statewide: true,
      enforcement: "statewide code, local administration",
      model: "IRC (as amended into the NCRC)",
      authority: "NC Building Code Council and Residential Code Council adopt the code under " +
                 "G.S. §143-138; NC OSFM publishes it; local inspection departments enforce it.",
      summary: "One statewide Residential Code with state amendments and NO local technical " +
               "amendments — a local rule requires Council approval. The edition in force is the " +
               "2018 NCRC, a 2015 IRC basis on ASCE 7-10, because the 2024 NCRC has been delayed " +
               "three times and had still not taken effect at the last confirmable statement.",
      statute: [
        codeRec({ name: "NC State Building Code: Residential Code", edition: "2018 NCRC",
          basis: "2015 IRC", asce: "ASCE 7-10", adopted: "2019-01-01", status: "in force",
          cite: "2018 North Carolina State Building Code: Residential Code — 2015 IRC basis with NC " +
                "amendments, adopted by the Building Code Council 13 June 2017, effective 1 January " +
                "2019. Engineered design under 2018 NCRC R301.1.3 references ASCE 7-10 (OSFM formal " +
                "interpretation, 29 February 2024).",
          src: "ncrc2018",
          note: "ASCE 7-10, not 7-16 and not 7-22. This engine's load path and any wind number taken " +
                "for a North Carolina permit today must come off the ASCE 7-10 map." }),
        codeRec({ name: "NC State Building Code: Residential Code", edition: "2024 NCRC",
          basis: "2021 IRC", asce: "ASCE 7-16", adopted: "delayed — see status",
          status: "ADOPTED BUT NOT IN FORCE as of " + CHECKED,
          cite: "2024 NC Residential Code (2021 IRC basis). Effective date delayed by S.L. 2024-57 " +
                "§1F.3 to 1 July 2025, then by S.L. 2025-2 to 12 months after the State Fire Marshal " +
                "certifies both that the fully adopted 2024 Code is published and distributed and " +
                "that the Residential Code Council is fully constituted. As of the 15 February 2026 " +
                "NC licensing board code update that certification had not occurred and the earliest " +
                "possible effective date stated was 1 March 2027.",
          src: "nc-lic-2026",
          note: "This is the most perishable fact in this module and it is six months old. Re-check " +
                "before it is relied on. If it has taken effect, the base code changes to the 2021 " +
                "IRC and the referenced wind standard changes with it." })
      ],
      localAmendments: {
        permitted: false,
        cls: "code",
        cite: "N.C.G.S. §143-138 — the NC State Building Code is adopted by the Building Code Council " +
              "and the Residential Code Council. More stringent local provisions require Council " +
              "approval under §143-138(e); local governments do not write their own technical " +
              "amendments to the Residential Code.",
        src: "nc-gs-143",
        confirmed: "secondary",
        checked: CHECKED,
        note: "This is the cleanest of the three states for a repeatable plan: one code, statewide, " +
              "with no per-city technical overlay to diff. What varies across North Carolina is the " +
              "SITE data — wind, snow, seismic — not the code text."
      },
      highWindZone: {
        cls: "code",
        cite: "NCRC Chapter 45, High Wind Zones — a North Carolina-specific chapter with prescriptive " +
              "requirements keyed to the design wind speed zone (e.g. one tie at each end of each " +
              "rafter at 130 mph, two at 140 and 150 mph; continuous concrete footings under all " +
              "exterior walls in the 140 and 150 mph zones).",
        src: "ncrc-ch45",
        confirmed: "secondary",
        checked: CHECKED,
        note: "Chapter 45 is prescriptive and this engine is not on the prescriptive path — it sizes " +
              "individual bending members. Where Chapter 45 applies, its provisions are ADDITIONAL " +
              "requirements this engine does not check and does not satisfy, and its connection and " +
              "foundation requirements are squarely in calc-spec §8.17 territory."
      },
      mustVerify: STATE_MV.NC
    }
  };

  /* ------------------------------------------------------------
     JURISDICTIONS

     `packId` is the nearest existing weights.js region pack. It is
     an APPROXIMATION and `packFor()` reports where it is wrong
     rather than letting the pack stand in silently for the site.
     ------------------------------------------------------------ */

  var TX_ASCE_2021 = "ASCE 7-16";   /* what a 2021-IRC city references */
  var TX_ASCE_2024 = "ASCE 7-22";   /* what a 2024-IRC city references */

  var JURIS = [

    /* ---------------- TEXAS ---------------- */

    {
      id: "tx-houston", name: "Houston", county: "Harris", state: "TX", kind: "municipality",
      packId: "tx-gulf", packWhy: "Gulf Coast market, wind-governed, Southern Pine palette.",
      governs: "wind",
      codes: [codeRec({ name: "Houston Construction Code — Residential", edition: "2021 IRC",
        basis: "2021 IRC with Houston amendments", asce: TX_ASCE_2021,
        adopted: "2024-01-01",
        cite: "City of Houston Ordinance 2023-907, adopting the 2021 I-Codes including the IRC, " +
              "effective 1 January 2024.", src: "hou-ord" })],
      wind: windOf({ vMph: 140, band: [130, 145], asce: TX_ASCE_2021, exposureCommon: "C",
        confirmed: "unverified",
        basis: "Planning band for the Houston metro read off secondary ASCE 7-16 wind-map summaries. " +
               "NOT a code-table lookup and NOT a Hazard Tool result.",
        cite: "ASCE 7-16 Figure 26.5-1 / 2021 IRC Figure R301.2(2), Risk Category II.", src: "asce7",
        note: "Houston's own amendment settles this: the city REQUIRES the ASCE 7 Hazard Tool " +
              "printout for the property address to be attached to the plans. Use that, not this." }),
      snow: snowOf({ pgPsf: 0, cls: "site", confirmed: "secondary",
        cite: "No mapped ground snow load on the Texas Gulf Coast.", src: "asce7",
        note: "Zero. The D + S combination is never formed and C_D = 1.15 must not appear on a " +
              "Houston sheet." }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified",
        cite: "Planning value. Seismic does not govern residential wood framing on the Texas coast.",
        src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "unverified",
        cite: "No frost penetration on the upper Texas coast; footing depth governed by the 12 in " +
              "minimum of IRC R403.1.4.", src: "hou-ord" }),
      termite: levelOf({ level: "very heavy", confirmed: "unverified",
        cite: "IRC Figure R301.2(6) termite infestation probability — the Gulf Coast is in the very " +
              "heavy band. The value in force is whatever Houston entered in Table R301.2(1).",
        src: "hou-ord" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC Figure R301.2(7) decay probability. The value in force is whatever Houston entered " +
              "in Table R301.2(1).", src: "hou-ord" }),
      windborneDebris: wbdOf({ inRegion: null, likely: true, determinedBy: "site",
        confirmed: "secondary",
        cite: "Houston amendment to 2021 IRC R301.2.1.2 — exterior glazing in wind-borne debris " +
              "regions must be protected; the wood structural panel fastening schedule is based on " +
              "180 mph V_ult at 45 ft mean roof height.",
        src: "hou-amend",
        note: "Houston is large enough that the answer differs across the city. It is determined from " +
              "the site's mapped speed, which the city already makes you print out." }),
      amendments: [
        amend("R301.2.1 — the ultimate design wind speed is determined by entering the property's " +
              "physical address into the ASCE 7 Hazard Tool; the building is Risk Category II; and a " +
              "copy of the wind-speed printout must be attached to the plans for verification.",
              "Houston Amendments to the 2021 International Residential Code, §R301.2.1.", "hou-amend",
              { effect: "This is the strongest amendment in the module and it is worth copying as " +
                        "practice. Houston refuses to publish a city-wide wind speed and requires the " +
                        "site value on the drawing. It is the same discipline this file runs on, " +
                        "written into an ordinance." }),
        amend("R301.2.1.2 — glazed opening protection for wind-borne debris must meet the Large " +
              "Missile Test of ASTM E1886 and ASTM E1996 as modified by the Houston amendment; the " +
              "wood structural panel alternative is scheduled for 180 mph V_ult at 45 ft mean roof " +
              "height.",
              "Houston Amendments to the 2021 International Residential Code, §R301.2.1.2.", "hou-amend")
      ],
      mustVerify: [
        mv({ id: "tx-houston-2024", severity: "major",
          what: "Whether Houston has moved to the 2024 I-Codes since January 2024.",
          why: "Two-and-a-half years is long enough for a code-modernisation programme to produce " +
               "another adoption, and Houston runs one.",
          check: "The Houston Permitting Center construction-code page and the current ordinance.",
          authority: "City of Houston Department of Public Works, Building Code Enforcement." })
      ]
    },

    {
      id: "tx-dallas", name: "Dallas", county: "Dallas", state: "TX", kind: "municipality",
      packId: "tx-i35", packWhy: "I-35 corridor market, gravity-governed, DFW palette and pricing.",
      governs: "gravity",
      codes: [codeRec({ name: "Dallas Residential Code", edition: "2021 IRC",
        basis: "2021 IRC with Dallas amendments", asce: TX_ASCE_2021,
        adopted: "2023-05-12",
        cite: "Dallas City Code Chapter 57, the 2021 International Residential Code with Dallas " +
              "amendments; 2021 I-Codes effective 12 May 2023, with Ordinance 33099 construction-code " +
              "amendments effective 23 May 2025.", src: "dal-code" })],
      wind: windOf({ vMph: 115, band: [105, 120], asce: TX_ASCE_2021, exposureCommon: "B",
        confirmed: "unverified",
        basis: "Planning band for DFW from secondary ASCE 7-16 map summaries, which disagreed with " +
               "each other by up to 15 mph. The low end of the band is the ASCE 7-16 mapped value " +
               "over north Texas; the high end is what commercial summaries quote.",
        cite: "ASCE 7-16 Figure 26.5-1 / 2021 IRC Figure R301.2(2), Risk Category II.", src: "asce7",
        note: "The sources genuinely conflict here. Do not use the midpoint; look up the site." }),
      snow: snowOf({ pgPsf: 5, band: [0, 10], confirmed: "unverified",
        cite: "Planning value for north Texas. ASCE 7-22 remapped the South and any pre-2022 number " +
              "is stale.", src: "asce7",
        note: "Snow does not govern: roof snow only overtakes the 20 psf roof live load above roughly " +
              "26 psf ground snow." }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified",
        cite: "Planning value. Seismic does not govern residential wood framing in north Texas.",
        src: "asce7" }),
      frostDepthIn: frostOf({ confirmed: "unverified",
        cite: "Dallas's published frost line depth from Table R301.2(1) could not be established. " +
              "Secondary sources report a 12 in minimum footing depth, which is the IRC R403.1.4 " +
              "minimum rather than a frost value.", src: "dal-code" }),
      termite: levelOf({ level: "moderate to heavy", confirmed: "unverified",
        cite: "IRC Figure R301.2(6). The value in force is whatever Dallas entered in Table R301.2(1).",
        src: "dal-code" }),
      decay: levelOf({ level: "none to slight", confirmed: "unverified",
        cite: "IRC Figure R301.2(7). The value in force is whatever Dallas entered in Table R301.2(1).",
        src: "dal-code" }),
      windborneDebris: wbdOf({ inRegion: false, likely: false, determinedBy: "site",
        confirmed: "secondary",
        cite: "IRC R301.2.1.2. Dallas is roughly 250 miles from the coastal mean high water line and " +
              "the mapped speed is far below 140 mph, so neither limb of the criterion is reached.",
        src: "dal-code" }),
      amendments: [
        amend("Dallas maintains a substantial amendment set to the 2021 IRC in City Code Chapter 57, " +
              "revised by Ordinance 33099 effective 23 May 2025. The individual structural amendments " +
              "were NOT retrieved and are not reproduced here.",
              "Dallas City Code Chapter 57; Ordinance 33099.", "dal-code",
              { incomplete: true,
                effect: "Treat this module's Dallas amendment list as EMPTY OF CONTENT, not as " +
                        "evidence that there are no structural amendments. There are; they were not " +
                        "readable from here." })
      ],
      mustVerify: [
        mv({ id: "tx-dallas-amend", severity: "blocking",
          what: "The Dallas structural amendments to the 2021 IRC.",
          why: "Dallas amends heavily and the amendment text could not be retrieved. An unread " +
               "amendment set is the most likely single cause of a Dallas plan review comment.",
          check: "Dallas City Code Chapter 57 and the current amendment PDFs published by Building " +
                 "Inspection.",
          authority: "City of Dallas Building Inspection." })
      ]
    },

    {
      id: "tx-fortworth", name: "Fort Worth", county: "Tarrant", state: "TX", kind: "municipality",
      packId: "tx-i35", packWhy: "I-35 corridor market, gravity-governed, DFW palette and pricing.",
      governs: "gravity",
      codes: [codeRec({ name: "Fort Worth Residential Code", edition: "2021 IRC",
        basis: "2021 IRC with Fort Worth amendments", asce: TX_ASCE_2021,
        adopted: "2022-03",
        cite: "Fort Worth City Code §7-61, adopting the 2021 edition of the International Residential " +
              "Code; Ordinance 25383-03-2022, March 2022. Appendices AA, AB, AC, AG and AK adopted, " +
              "AK (sound insulation near airports) as a local amendment.", src: "ftw-ord" })],
      wind: windOf({ vMph: 115, band: [105, 120], asce: TX_ASCE_2021, exposureCommon: "B",
        confirmed: "unverified",
        basis: "Same DFW planning band as Dallas, from the same conflicting secondary summaries.",
        cite: "ASCE 7-16 Figure 26.5-1 / 2021 IRC Figure R301.2(2), Risk Category II.", src: "asce7" }),
      snow: snowOf({ pgPsf: 5, band: [0, 10], confirmed: "unverified",
        cite: "Planning value for north Texas.", src: "asce7" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified",
        cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ confirmed: "unverified",
        cite: "Fort Worth's published frost line depth from Table R301.2(1) could not be established.",
        src: "ftw-ord" }),
      termite: levelOf({ level: "moderate to heavy", confirmed: "unverified",
        cite: "IRC Figure R301.2(6).", src: "ftw-ord" }),
      decay: levelOf({ level: "none to slight", confirmed: "unverified",
        cite: "IRC Figure R301.2(7).", src: "ftw-ord" }),
      windborneDebris: wbdOf({ inRegion: false, likely: false, determinedBy: "site",
        confirmed: "secondary",
        cite: "IRC R301.2.1.2 — neither limb of the criterion is reached this far inland.",
        src: "ftw-ord" }),
      amendments: [
        amend("Fort Worth's 2021 IRC amendments are adopted by Ordinance 25383-03-2022. The " +
              "structural amendments were NOT retrieved and are not reproduced here.",
              "Fort Worth Ordinance 25383-03-2022; City Code §7-61.", "ftw-ord",
              { incomplete: true })
      ],
      mustVerify: [
        mv({ id: "tx-ftw-age", severity: "major",
          what: "Whether Fort Worth has adopted the 2024 I-Codes since March 2022.",
          why: "A four-year-old adoption in a fast-growing DFW city is exactly the fact that is wrong " +
               "by a cycle. Its neighbour San Antonio has already moved to the 2024 IRC.",
          check: "Fort Worth Development Services building-code amendment page and the current " +
                 "ordinance.",
          authority: "City of Fort Worth Development Services." })
      ]
    },

    {
      id: "tx-sanantonio", name: "San Antonio", county: "Bexar", state: "TX", kind: "municipality",
      packId: "tx-i35", packWhy: "I-35 corridor market, gravity-governed.",
      governs: "gravity",
      codes: [codeRec({ name: "San Antonio Residential Code", edition: "2024 IRC",
        basis: "2024 IRC with San Antonio amendments", asce: TX_ASCE_2024,
        adopted: "2025-05-01",
        cite: "San Antonio City Code Chapter 10, Building-Related Codes, effective 1 May 2025; " +
              "Ordinance 2025-01-30-0075 adopting the 2024 editions including the International " +
              "Residential Code for One- and Two-Family Dwellings. Supersedes the 2021 I-Codes that " +
              "were effective 1 February 2023 under Ordinance 2022-11-10-0875.", src: "sat-ord" })],
      wind: windOf({ vMph: 115, band: [105, 120], asce: TX_ASCE_2024, exposureCommon: "B",
        confirmed: "unverified",
        basis: "Planning band for south-central Texas from secondary map summaries.",
        cite: "ASCE 7-22 Figure 26.5-1 / 2024 IRC Figure R301.2(2), Risk Category II.", src: "asce7",
        note: "NOTE THE MAP. San Antonio is on the 2024 IRC and therefore ASCE 7-22, while Austin " +
              "80 miles away is on the 2021 IRC and ASCE 7-16. The same site read off the two maps " +
              "does not give the same number, and a repeatable plan sold in both markets is being " +
              "checked against two different standards." }),
      snow: snowOf({ pgPsf: 5, band: [0, 10], confirmed: "unverified",
        cite: "Planning value for south-central Texas.", src: "asce7" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ confirmed: "unverified",
        cite: "San Antonio's published frost line depth from Table R301.2(1) could not be established.",
        src: "sat-ord" }),
      termite: levelOf({ level: "moderate to heavy", confirmed: "unverified",
        cite: "IRC Figure R301.2(6).", src: "sat-ord" }),
      decay: levelOf({ level: "none to slight", confirmed: "unverified",
        cite: "IRC Figure R301.2(7).", src: "sat-ord" }),
      windborneDebris: wbdOf({ inRegion: false, likely: false, determinedBy: "site",
        confirmed: "secondary",
        cite: "IRC R301.2.1.2 — neither limb of the criterion is reached this far inland.",
        src: "sat-ord" }),
      amendments: [
        amend("San Antonio is the only jurisdiction in this module on the 2024 IRC. That changes the " +
              "referenced wind standard to ASCE 7-22 and changes the referenced-standards chapter " +
              "wholesale relative to every other Texas city here.",
              "San Antonio City Code Chapter 10; Ordinance 2025-01-30-0075.", "sat-ord",
              { effect: "A master set drawn to the 2021 IRC for Austin and DFW is NOT on San " +
                        "Antonio's code. This is the concrete case for keying a Texas pack to the " +
                        "city rather than the state." }),
        amend("San Antonio's local amendments to the 2024 IRC were NOT retrieved and are not " +
              "reproduced here.",
              "San Antonio City Code Chapter 10, Building-Related Codes.", "sat-ord",
              { incomplete: true })
      ],
      mustVerify: [
        mv({ id: "tx-sat-amend", severity: "major",
          what: "San Antonio's structural amendments to the 2024 IRC.",
          why: "Not retrieved. Chapter 10 carries the amendment set and it was not readable here.",
          check: "San Antonio City Code Chapter 10, Building-Related Codes, current edition.",
          authority: "City of San Antonio Development Services Department." })
      ]
    },

    {
      id: "tx-austin", name: "Austin", county: "Travis", state: "TX", kind: "municipality",
      packId: "tx-i35", packWhy: "I-35 corridor market, gravity-governed.",
      governs: "gravity",
      codes: [codeRec({ name: "Austin Residential Code", edition: "2021 IRC",
        basis: "2021 IRC with Austin amendments", asce: TX_ASCE_2021,
        adopted: "2021-09-01",
        cite: "Austin City Code Chapter 25-12, Article 11 (Residential Code), adopting the 2021 " +
              "International Residential Code; approved by Council 3 June 2021, effective " +
              "1 September 2021.", src: "aus-code" })],
      wind: windOf({ vMph: 115, band: [105, 120], asce: TX_ASCE_2021, exposureCommon: "B",
        confirmed: "unverified",
        basis: "Planning band for central Texas from secondary map summaries, which quoted 120–135 " +
               "for 'Austin / Central TX' — a range this module does not believe for Risk Category II " +
               "on the ASCE 7-16 map and has not adopted.",
        cite: "ASCE 7-16 Figure 26.5-1 / 2021 IRC Figure R301.2(2), Risk Category II.", src: "asce7",
        note: "The secondary sources for Austin were the worst in the module and disagreed by 30 mph. " +
              "This band is the conservative reading of the ASCE 7-16 map, not a quotation. Look it up." }),
      snow: snowOf({ pgPsf: 5, band: [0, 10], confirmed: "unverified",
        cite: "Planning value for central Texas.", src: "asce7" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ confirmed: "unverified",
        cite: "Austin's published frost line depth from Table R301.2(1) could not be established.",
        src: "aus-code" }),
      termite: levelOf({ level: "moderate to heavy", confirmed: "unverified",
        cite: "IRC Figure R301.2(6).", src: "aus-code" }),
      decay: levelOf({ level: "none to slight", confirmed: "unverified",
        cite: "IRC Figure R301.2(7).", src: "aus-code" }),
      windborneDebris: wbdOf({ inRegion: false, likely: false, determinedBy: "site",
        confirmed: "secondary",
        cite: "IRC R301.2.1.2 — neither limb of the criterion is reached this far inland.",
        src: "aus-code" }),
      amendments: [
        amend("Austin's local amendments to the 2021 IRC live in City Code Chapter 25-12 Article 11 " +
              "and were NOT retrieved. Austin also runs a separate Land Development Code that " +
              "constrains what may be built but not how it is framed.",
              "Austin City Code Chapter 25-12, Article 11.", "aus-code", { incomplete: true })
      ],
      mustVerify: [
        mv({ id: "tx-austin-age", severity: "blocking",
          what: "Whether Austin is still on the 2021 IRC.",
          why: "The only confirmable Austin adoption is five years old. Of every adoption date in " +
               "this module this is the one most likely to have moved, and nothing found here either " +
               "confirms or denies a 2024 adoption.",
          check: "Austin Development Services building technical codes page and City Code " +
                 "Chapter 25-12.",
          authority: "City of Austin Development Services Department." })
      ]
    },

    {
      id: "tx-corpuschristi", name: "Corpus Christi", county: "Nueces", state: "TX",
      kind: "municipality",
      packId: "tx-gulf", packWhy: "Gulf Coast market, wind-governed, Southern Pine palette.",
      governs: "wind",
      catastropheArea: true,
      codes: [
        codeRec({ name: "Corpus Christi Residential Code", edition: "2021 IRC",
          basis: "2021 IRC with local amendments", asce: TX_ASCE_2021,
          adopted: "2023-08-01",
          cite: "Corpus Christi Code Chapter 14, adopting the 2021 I-Codes including the " +
                "International Residential Code for One- and Two-Family Dwellings, with local " +
                "amendments effective 1 August 2023.", src: "cc-ord" }),
        codeRec({ name: "TDI windstorm building code", edition: "2024 IRC / 2024 IBC",
          basis: "2024 IRC", asce: TX_ASCE_2024, adopted: "2026-04-01",
          cite: "28 TAC §5.4008 — WPI-1 applications from 1 April 2026 must be certified to the 2024 " +
                "IRC or 2024 IBC. Nueces County is a designated catastrophe area.", src: "tdi-rule",
          note: "A SECOND CODE, NOT A SECOND OPINION. This is a newer edition than the city enforces " +
                "and it applies to the same house." })
      ],
      wind: windOf({ vMph: 150, band: [140, 160], asce: TX_ASCE_2021, exposureCommon: "C",
        confirmed: "unverified",
        basis: "First-tier coastal planning band. TDI describes the first tier as 140–150 mph V_ult " +
               "Risk Category II seaward of the intracoastal canal and 130–140 mph for the second " +
               "tier inland of it.",
        cite: "ASCE 7-16 Figure 26.5-1 / 2021 IRC Figure R301.2(2), Risk Category II; TDI seacoast " +
              "territory tiers.", src: "tdi-codes",
        note: "Exposure D applies within roughly 600 ft of open shoreline. The tier boundary runs " +
              "through this city — the seaward and inland halves are not the same design." }),
      snow: snowOf({ pgPsf: 0, cls: "site", confirmed: "secondary",
        cite: "No mapped ground snow load on the Texas coast.", src: "asce7" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "unverified",
        cite: "No frost penetration on the south Texas coast; footing depth governed by the 12 in " +
              "minimum of IRC R403.1.4.", src: "cc-ord" }),
      termite: levelOf({ level: "very heavy", confirmed: "unverified",
        cite: "IRC Figure R301.2(6) — the Gulf Coast is in the very heavy band.", src: "cc-ord" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC Figure R301.2(7).", src: "cc-ord" }),
      windborneDebris: wbdOf({ inRegion: true, likely: true, determinedBy: "code",
        confirmed: "secondary",
        cite: "TDI states that most of the designated catastrophe areas are now within the " +
              "wind-borne debris region, with protection requirements as specified in the 2024 IRC " +
              "and 2024 IBC.", src: "tdi-codes",
        note: "'Most of' is TDI's word, not 'all of'. The site's own position against the contour " +
              "still decides." }),
      amendments: [
        amend("Corpus Christi's local amendments to the 2021 I-Codes were NOT retrieved.",
              "Corpus Christi Code Chapter 14; 2021 Adopted Code Amendments.", "cc-ord",
              { incomplete: true }),
        amend("Windstorm certification is a separate submittal and inspection track: WPI-1 before " +
              "construction, oversight by a TDI-appointed qualified inspector or TDI-appointed Texas " +
              "PE, WPI-8 certificate of compliance at completion. Since 1 April 2026 the code for " +
              "that track is the 2024 IRC, while the city permit is on the 2021 IRC.",
              "Tex. Ins. Code §§2210.251–2210.252, 2210.258–2210.259; 28 TAC §5.4008.", "tdi-wpi8",
              { effect: "TWO CODES ON ONE HOUSE. Satisfying the city does not satisfy TDI, and " +
                        "failing TDI costs the owner windstorm insurance eligibility, which in " +
                        "practice costs them the mortgage." })
      ],
      mustVerify: [
        mv({ id: "tx-cc-dual", severity: "blocking",
          what: "Which requirement governs each item where the city's 2021 IRC and TDI's 2024 IRC " +
                "differ.",
          why: "They are different editions of the same model code applying to the same building at " +
               "the same time. This module does not diff them and cannot.",
          check: "The 2021 IRC as amended by Corpus Christi against the 2024 IRC as required by TDI, " +
                 "item by item, for everything on the windstorm path.",
          authority: "City of Corpus Christi Development Services and TDI Windstorm Inspections." })
      ]
    },

    {
      id: "tx-galveston-city", name: "Galveston", county: "Galveston", state: "TX",
      kind: "municipality",
      packId: "tx-gulf", packWhy: "Gulf Coast market, wind-governed, Southern Pine palette.",
      governs: "wind",
      catastropheArea: true,
      codes: [
        codeRec({ name: "City of Galveston Building Code — Residential", edition: "2021 IRC",
          basis: "2021 IRC with local amendments", asce: TX_ASCE_2021,
          adopted: "2023",
          cite: "City of Galveston Code Chapter 10 (Building Code); Ordinance 23-012 adopting the " +
                "2021 International Codes with local amendments.", src: "galv-ord",
          confirmed: "unverified",
          note: "The ordinance number and the 2021 edition are corroborated by secondary sources; " +
                "the effective date was not established." }),
        codeRec({ name: "TDI windstorm building code", edition: "2024 IRC / 2024 IBC",
          basis: "2024 IRC", asce: TX_ASCE_2024, adopted: "2026-04-01",
          cite: "28 TAC §5.4008 — WPI-1 applications from 1 April 2026 must be certified to the 2024 " +
                "IRC or 2024 IBC. Galveston County is a designated catastrophe area.", src: "tdi-rule" })
      ],
      wind: windOf({ vMph: 150, band: [140, 160], asce: TX_ASCE_2021, exposureCommon: "D",
        confirmed: "unverified",
        basis: "First-tier coastal planning band; the island is seaward of the intracoastal canal.",
        cite: "ASCE 7-16 Figure 26.5-1 / 2021 IRC Figure R301.2(2), Risk Category II; TDI seacoast " +
              "territory tiers.", src: "tdi-codes",
        note: "Exposure D over most of the island. This is the one jurisdiction in the module where " +
              "the advisory exposure is D rather than B or C, and it is still an advisory." }),
      snow: snowOf({ pgPsf: 0, cls: "site", confirmed: "secondary",
        cite: "No mapped ground snow load on the Texas coast.", src: "asce7" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "unverified",
        cite: "No frost penetration; footing depth governed by the 12 in minimum of IRC R403.1.4.",
        src: "galv-ord",
        note: "Foundation design on Galveston Island is dominated by FEMA flood elevation and " +
              "breakaway-wall requirements, not frost. Neither is in this engine." }),
      termite: levelOf({ level: "very heavy", confirmed: "unverified",
        cite: "IRC Figure R301.2(6) — the Gulf Coast is in the very heavy band.", src: "galv-ord" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC Figure R301.2(7).", src: "galv-ord" }),
      windborneDebris: wbdOf({ inRegion: true, likely: true, determinedBy: "code",
        confirmed: "secondary",
        cite: "TDI — most of the designated catastrophe areas are within the wind-borne debris " +
              "region; the island is within 1 mile of the coastal mean high water line throughout.",
        src: "tdi-codes" }),
      amendments: [
        amend("Galveston's local amendments to the 2021 I-Codes were NOT retrieved.",
              "City of Galveston Code Chapter 10; Ordinance 23-012.", "galv-ord", { incomplete: true }),
        amend("Windstorm certification applies: WPI-1 before construction, TDI-appointed inspector or " +
              "TDI-appointed Texas PE, WPI-8 at completion, on the 2024 IRC since 1 April 2026.",
              "Tex. Ins. Code ch. 2210; 28 TAC §5.4008.", "tdi-wpi8"),
        amend("Flood: much of the island is in a FEMA special flood hazard area with elevation, " +
              "breakaway-wall and free-of-obstruction requirements. NONE of it is modelled by this " +
              "product.",
              "FEMA NFIP; City of Galveston floodplain ordinance.", "galv-ord",
              { effect: "Named so it is visibly absent rather than silently missing." })
      ],
      mustVerify: [
        mv({ id: "tx-galv-eff", severity: "major",
          what: "The effective date of Galveston's 2021 code adoption, and whether a 2024 adoption " +
                "has followed.",
          why: "Only the ordinance number and edition could be corroborated; the date could not.",
          check: "City of Galveston Code Chapter 10 and the Building Division's adopted-codes page.",
          authority: "City of Galveston Building Division." })
      ]
    },

    {
      id: "tx-galveston-county-uninc", name: "Galveston County — unincorporated",
      county: "Galveston", state: "TX", kind: "county-unincorporated",
      packId: "tx-gulf", packWhy: "Gulf Coast market, wind-governed, Southern Pine palette.",
      governs: "wind",
      catastropheArea: true,
      codes: [
        codeRec({ name: "County residential building code", edition: "NOT ESTABLISHED",
          basis: "unknown", asce: null, adopted: "unknown", status: "UNKNOWN — see mustVerify",
          confirmed: "unverified",
          cite: "No adopted residential building code for the unincorporated area of Galveston County " +
                "could be established. Texas counties have no general building-code authority; a " +
                "survey cited in secondary sources found only 2 of 10 responding Texas counties had " +
                "adopted a building code for their unincorporated areas. Tex. Loc. Gov't Code " +
                "§§233.151–233.153 may or may not reach this county, and where it does it defaults to " +
                "the IRC as published 1 May 2008 or the county seat's edition, with no enforcement " +
                "fee permitted.",
          src: "tx-lgc-233",
          note: "THIS RECORD IS DELIBERATELY EMPTY. It is carried because unincorporated Galveston " +
                "County is real, tract housing is built in it, and a jurisdiction table that silently " +
                "omitted it would read as if every Texas site had a code behind it. What is known " +
                "here is that TDI's windstorm regime applies regardless of whether any building code " +
                "does." }),
        codeRec({ name: "TDI windstorm building code", edition: "2024 IRC / 2024 IBC",
          basis: "2024 IRC", asce: TX_ASCE_2024, adopted: "2026-04-01",
          cite: "28 TAC §5.4008 — WPI-1 applications from 1 April 2026 must be certified to the 2024 " +
                "IRC or 2024 IBC. Galveston County is a designated catastrophe area.", src: "tdi-rule",
          note: "In unincorporated coastal Texas this is frequently the ONLY code with a real " +
                "inspection behind it, and it is an insurance-eligibility programme rather than a " +
                "building department. That is the whole regulatory picture for these sites." })
      ],
      wind: windOf({ vMph: 150, band: [140, 160], asce: TX_ASCE_2024, exposureCommon: "C",
        confirmed: "unverified",
        basis: "First-tier coastal planning band. The ASCE edition shown is TDI's, because TDI's is " +
               "the only code confirmed to apply here.",
        cite: "ASCE 7-22 (2024 IRC, TDI) Figure 26.5-1, Risk Category II; TDI seacoast territory tiers.",
        src: "tdi-codes",
        note: "The county spans both TDI tiers and both sides of the intracoastal canal." }),
      snow: snowOf({ pgPsf: 0, cls: "site", confirmed: "secondary",
        cite: "No mapped ground snow load on the Texas coast.", src: "asce7" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "unverified",
        cite: "No frost penetration; the 12 in minimum footing depth of IRC R403.1.4 applies only if " +
              "an IRC edition is actually in force here, which is unestablished.", src: "tx-lgc-233" }),
      termite: levelOf({ level: "very heavy", confirmed: "unverified",
        cite: "IRC Figure R301.2(6) — the Gulf Coast is in the very heavy band.", src: "tx-lgc-233" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC Figure R301.2(7).", src: "tx-lgc-233" }),
      windborneDebris: wbdOf({ inRegion: null, likely: true, determinedBy: "site",
        confirmed: "unverified",
        cite: "IRC R301.2.1.2 as applied through TDI's 2024 IRC requirement. The county spans the " +
              "contour.", src: "tdi-codes" }),
      amendments: [
        amend("There may be no building permit and no building inspection for a site in " +
              "unincorporated Galveston County. Where a municipality's extraterritorial jurisdiction " +
              "reaches the site, that municipality's building code controls instead.",
              "Tex. Loc. Gov't Code §233.153.", "tx-lgc-233",
              { effect: "Establish which of the three regimes the site is in BEFORE the geometry " +
                        "gate, not at submittal. It changes the code basis, the submittal set and " +
                        "whether anyone inspects the work." })
      ],
      mustVerify: [
        mv({ id: "tx-galvco-code", severity: "blocking",
          what: "Whether ANY residential building code applies to this site, and which.",
          why: "Not established. The three candidates are (a) a municipality's ETJ code, (b) Tex. " +
               "Loc. Gov't Code ch. 233 Subchapter F if it reaches this county, (c) nothing. They " +
               "produce three different code bases.",
          check: "Galveston County, the ETJ maps of the nearby municipalities, and whether " +
                 "Subchapter F applies to Galveston County.",
          authority: "Galveston County; the adjacent municipalities." }),
        mv({ id: "tx-galvco-sub-f", severity: "major",
          what: "Whether Tex. Loc. Gov't Code ch. 233 Subchapter F applies to Galveston County.",
          why: "Subchapter F reaches only 'certain counties' and the list could not be established. " +
               "If it applies, the default basis is the IRC as published 1 May 2008 — sixteen years " +
               "older than what TDI requires for the same house.",
          check: "Tex. Loc. Gov't Code §233.151 applicability.",
          authority: "Galveston County; Texas Local Government Code." })
      ]
    },

    /* ---------------- FLORIDA ----------------
       Every Florida jurisdiction is on the same code. What varies is
       the site data, the HVHZ line (two counties), and whatever local
       technical amendment the jurisdiction has bought itself under
       §553.73(4) — all of which the 9th Edition voids. */

    {
      id: "fl-miamidade", name: "Miami-Dade County", county: "Miami-Dade", state: "FL",
      kind: "county",
      packId: "fl-hvhz", packWhy: "The pack is built for exactly this jurisdiction.",
      governs: "wind", hvhz: true,
      codes: [codeRec({ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
        basis: "2021 IRC", asce: "ASCE 7-22", adopted: "2023-12-31",
        cite: "FBC-R 8th Edition (2023), effective 31 December 2023, PLUS FBC-R Chapter 44, " +
              "High-Velocity Hurricane Zones.", src: "fbc8" })],
      wind: windOf({ vMph: 175, band: [175, 175], asce: "ASCE 7-22", exposureCommon: "C",
        codeFixed: true, confirmed: "secondary",
        basis: "The FBC fixes the HVHZ design wind speed by county rather than leaving it to the " +
               "ASCE contour; 175 mph Risk Category II for Miami-Dade.",
        cite: "FBC-R Figure R301.2(2) / FBC-B §1620, HVHZ wind loads, Risk Category II.",
        src: "fl-hvhz",
        note: "Even a code-fixed number is confirmed against the figure in the edition in force on " +
              "the permit date. The 9th Edition arrives 31 December 2026." }),
      snow: snowOf({ pgPsf: 0, cls: "code", confirmed: "secondary",
        cite: "Ground snow load is zero throughout Florida; FBC-R Table R301.2(1).", src: "fbc8",
        note: "Zero. The D + S combination is never formed and C_D = 1.15 must not appear on a " +
              "Florida sheet." }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified",
        cite: "Planning value. Seismic does not govern residential wood framing in south Florida.",
        src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "secondary",
        cite: "No frost line in Florida; footing depth governed by the 12 in minimum of FBC-R " +
              "R403.1.4.", src: "fbc8" }),
      termite: levelOf({ level: "very heavy", confirmed: "secondary",
        cite: "FBC-R R318 requires subterranean termite protection throughout Florida; the whole " +
              "state is in the very heavy band of the termite infestation probability map.",
        src: "fbc8" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC/FBC-R decay probability figure.", src: "fbc8" }),
      windborneDebris: wbdOf({ inRegion: true, likely: true, determinedBy: "code", cls: "code",
        confirmed: "secondary",
        cite: "The entire HVHZ is a wind-borne debris region; FBC-R Chapter 44.", src: "fl-hvhz",
        note: "This is one of only two jurisdictions in the module where the code fixes the answer " +
              "and the contour does not have to be consulted." }),
      amendments: [
        amend("FBC-R Chapter 44 (High-Velocity Hurricane Zones) applies in full and is a distinct " +
              "design and approval regime, not a set of stricter numbers.",
              "FBC-R Chapter 44; FBC-B §1620.", "fl-hvhz",
              { effect: "Whether Chapter 44 permits the prescriptive/WFCM path or mandates engineered " +
                        "design was NOT resolved — the same open question weights.js records on the " +
                        "fl-hvhz pack. It decides what this tool's output is for." }),
        amend("Every product in a regulated category needs a Miami-Dade NOA, or a statewide Florida " +
              "Product Approval bearing the HVHZ endorsement. A statewide approval without the HVHZ " +
              "endorsement is rejected at permit review.",
              "F.A.C. Rule 61G20-3; Miami-Dade NOA programme.", "fl-prod"),
        amend("First-floor exterior walls in this market are concrete block with a tie beam, so " +
              "exterior openings are spanned by precast or cast-in-place concrete lintels, not wood " +
              "headers.",
              "Market practice, recorded on the fl-hvhz pack in weights.js.", "fbc8",
              { cls: "market",
                effect: "weights.js applicability() already deletes first-floor exterior wood headers " +
                        "in a cmu market. It is repeated here so the jurisdiction record and the pack " +
                        "agree rather than each asserting it separately." })
      ],
      mustVerify: [
        mv({ id: "fl-md-ch44", severity: "blocking",
          what: "Whether FBC-R Chapter 44 permits a prescriptive path or mandates engineered design " +
                "for this building.",
          why: "Unresolved here and unresolved in weights.js. It decides whether a gravity member " +
               "schedule is an input to a design or a substitute for one.",
          check: "FBC-R Chapter 44 in the edition in force on the permit date.",
          authority: "Miami-Dade County Department of Regulatory and Economic Resources." })
      ]
    },

    {
      id: "fl-broward", name: "Broward County", county: "Broward", state: "FL", kind: "county",
      packId: "fl-hvhz", packWhy: "The other HVHZ county; the pack is built for both.",
      governs: "wind", hvhz: true,
      codes: [codeRec({ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
        basis: "2021 IRC", asce: "ASCE 7-22", adopted: "2023-12-31",
        cite: "FBC-R 8th Edition (2023), effective 31 December 2023, PLUS FBC-R Chapter 44, " +
              "High-Velocity Hurricane Zones.", src: "fbc8" })],
      wind: windOf({ vMph: 170, band: [170, 170], asce: "ASCE 7-22", exposureCommon: "C",
        codeFixed: true, confirmed: "secondary",
        basis: "The FBC fixes the HVHZ design wind speed by county; 170 mph Risk Category II for " +
               "Broward — five mph below Miami-Dade, on the same code, across a county line.",
        cite: "FBC-R Figure R301.2(2) / FBC-B §1620, HVHZ wind loads, Risk Category II.",
        src: "fl-hvhz" }),
      snow: snowOf({ pgPsf: 0, cls: "code", confirmed: "secondary",
        cite: "Ground snow load is zero throughout Florida; FBC-R Table R301.2(1).", src: "fbc8" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "secondary",
        cite: "No frost line in Florida; FBC-R R403.1.4 12 in minimum applies.", src: "fbc8" }),
      termite: levelOf({ level: "very heavy", confirmed: "secondary",
        cite: "FBC-R R318 requires termite protection throughout Florida.", src: "fbc8" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC/FBC-R decay probability figure.", src: "fbc8" }),
      windborneDebris: wbdOf({ inRegion: true, likely: true, determinedBy: "code", cls: "code",
        confirmed: "secondary",
        cite: "The entire HVHZ is a wind-borne debris region; FBC-R Chapter 44.", src: "fl-hvhz" }),
      amendments: [
        amend("FBC-R Chapter 44 (HVHZ) applies in full.", "FBC-R Chapter 44.", "fl-hvhz"),
        amend("Miami-Dade NOA or HVHZ-endorsed statewide Florida Product Approval required for every " +
              "product in a regulated category. A Miami-Dade NOA is accepted in Broward as satisfying " +
              "the HVHZ testing protocols, but the reverse — a Broward-only approval — does not exist; " +
              "verify the acceptance route with the county rather than assuming reciprocity.",
              "F.A.C. Rule 61G20-3; Miami-Dade NOA programme.", "fl-prod", { confirmed: "unverified" }),
        amend("Concrete block first-floor exterior walls with concrete lintels, as Miami-Dade.",
              "Market practice, recorded on the fl-hvhz pack in weights.js.", "fbc8", { cls: "market" })
      ],
      mustVerify: [
        mv({ id: "fl-bro-noa", severity: "major",
          what: "How Broward accepts product approvals — whether a Miami-Dade NOA is accepted " +
                "directly or an HVHZ-endorsed statewide approval is required.",
          why: "The NOA is by name a Miami-Dade instrument. Its acceptance in Broward is asserted by " +
               "secondary sources and was not confirmed against either county's rules.",
          check: "Broward County Board of Rules and Appeals product-approval policy.",
          authority: "Broward County Board of Rules and Appeals." })
      ]
    },

    {
      id: "fl-palmbeach", name: "Palm Beach County", county: "Palm Beach", state: "FL",
      kind: "county",
      packId: "fl-central",
      packWhy: "The only non-HVHZ Florida pack. It is a poor fit — see packFor() differences.",
      governs: "wind", hvhz: false,
      codes: [codeRec({ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
        basis: "2021 IRC", asce: "ASCE 7-22", adopted: "2023-12-31",
        cite: "FBC-R 8th Edition (2023), effective 31 December 2023.", src: "fbc8" })],
      wind: windOf({ vMph: 165, band: [150, 175], asce: "ASCE 7-22", exposureCommon: "C",
        confirmed: "unverified",
        basis: "Planning band from secondary ASCE 7-22 summaries. Palm Beach sits immediately north " +
               "of the HVHZ line with mapped speeds close to Broward's, and the county spans a wide " +
               "contour range from the barrier island to the western communities.",
        cite: "ASCE 7-22 Figure 26.5-1 / FBC-R Figure R301.2(2), Risk Category II.", src: "asce7",
        note: "PALM BEACH IS NOT IN THE HVHZ. It carries near-HVHZ wind speeds under the ordinary " +
              "statewide code, which is exactly the combination that gets it mistaken for HVHZ. The " +
              "wind number is nearly Broward's; the approval regime is not." }),
      snow: snowOf({ pgPsf: 0, cls: "code", confirmed: "secondary",
        cite: "Ground snow load is zero throughout Florida; FBC-R Table R301.2(1).", src: "fbc8" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "secondary",
        cite: "No frost line in Florida; FBC-R R403.1.4 12 in minimum applies.", src: "fbc8" }),
      termite: levelOf({ level: "very heavy", confirmed: "secondary",
        cite: "FBC-R R318 requires termite protection throughout Florida.", src: "fbc8" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC/FBC-R decay probability figure.", src: "fbc8" }),
      windborneDebris: wbdOf({ inRegion: null, likely: true, determinedBy: "site",
        confirmed: "unverified",
        cite: "FBC-R R301.2.1.2. At mapped speeds of 150 mph and above the 140 mph limb of the " +
              "criterion is reached county-wide, but the county spans the contour and the answer is " +
              "read at the site.", src: "fbc8" }),
      amendments: [
        amend("Palm Beach County administers the statewide code and maintains a product-approval " +
              "process for permit submittals. Any local technical amendment was NOT retrieved.",
              "F.S. §553.73(4); Palm Beach County Planning, Zoning and Building.", "fs-553-73",
              { incomplete: true })
      ],
      mustVerify: [
        mv({ id: "fl-pb-hvhz", severity: "major",
          what: "That the package is NOT being detailed to HVHZ requirements by analogy to its " +
                "neighbour.",
          why: "Palm Beach borders Broward and carries similar wind speeds under a different regime. " +
               "Detailing it as HVHZ buys unnecessary product cost; detailing Broward as Palm Beach " +
               "fails permit review. The wind number does not tell you which side of the line you " +
               "are on — the county name does.",
          check: "FBC-R Chapter 44 scope: Broward and Miami-Dade only.",
          authority: "Palm Beach County Planning, Zoning and Building." })
      ]
    },

    {
      id: "fl-orange", name: "Orlando / Orange County", county: "Orange", state: "FL",
      kind: "county",
      packId: "fl-central", packWhy: "The pack's named market. Closest fit in the product.",
      governs: "wind", hvhz: false,
      codes: [codeRec({ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
        basis: "2021 IRC", asce: "ASCE 7-22", adopted: "2023-12-31",
        cite: "FBC-R 8th Edition (2023), effective 31 December 2023.", src: "fbc8" })],
      wind: windOf({ vMph: 130, band: [125, 140], asce: "ASCE 7-22", exposureCommon: "C",
        confirmed: "unverified",
        basis: "Planning band for inland central Florida from secondary ASCE 7-22 summaries.",
        cite: "ASCE 7-22 Figure 26.5-1 / FBC-R Figure R301.2(2), Risk Category II.", src: "asce7" }),
      snow: snowOf({ pgPsf: 0, cls: "code", confirmed: "secondary",
        cite: "Ground snow load is zero throughout Florida; FBC-R Table R301.2(1).", src: "fbc8" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "secondary",
        cite: "No frost line in Florida; FBC-R R403.1.4 12 in minimum applies.", src: "fbc8" }),
      termite: levelOf({ level: "very heavy", confirmed: "secondary",
        cite: "FBC-R R318 requires termite protection throughout Florida.", src: "fbc8" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC/FBC-R decay probability figure.", src: "fbc8" }),
      windborneDebris: wbdOf({ inRegion: null, likely: false, determinedBy: "site",
        confirmed: "unverified",
        cite: "FBC-R R301.2.1.2. Orange County is inland — no part is within 1 mile of a coastal mean " +
              "high water line — so the region is reached only if the mapped speed at the site is " +
              "140 mph or greater, which is at the top of the planning band.",
        src: "fbc8",
        note: "THIS IS THE CASE THE COUNTY-LINE HABIT GETS WRONG IN BOTH DIRECTIONS. Orlando is not " +
              "coastal, so people assume no opening protection; but the 140 mph limb applies " +
              "anywhere, coast or not. And the 9th Edition's five-mile-from-tidal-water rule is a " +
              "third, different geometry again." }),
      amendments: [
        amend("Any local technical amendment adopted by Orange County or the City of Orlando was NOT " +
              "retrieved. Under F.S. §553.73(4) any that exist are void at the 9th Edition unless " +
              "adopted for Community Rating System purposes.",
              "F.S. §553.73(4).", "fs-553-73", { incomplete: true })
      ],
      mustVerify: []
    },

    {
      id: "fl-hillsborough", name: "Tampa / Hillsborough County", county: "Hillsborough",
      state: "FL", kind: "county",
      packId: "fl-central", packWhy: "The pack's named market.",
      governs: "wind", hvhz: false,
      codes: [codeRec({ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
        basis: "2021 IRC", asce: "ASCE 7-22", adopted: "2023-12-31",
        cite: "FBC-R 8th Edition (2023), effective 31 December 2023.", src: "fbc8" })],
      wind: windOf({ vMph: 140, band: [130, 150], asce: "ASCE 7-22", exposureCommon: "C",
        confirmed: "unverified",
        basis: "Planning band for the Tampa Bay area from secondary ASCE 7-22 summaries. The county " +
               "runs from open bay frontage to well inland and the contour crosses it.",
        cite: "ASCE 7-22 Figure 26.5-1 / FBC-R Figure R301.2(2), Risk Category II.", src: "asce7" }),
      snow: snowOf({ pgPsf: 0, cls: "code", confirmed: "secondary",
        cite: "Ground snow load is zero throughout Florida; FBC-R Table R301.2(1).", src: "fbc8" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "secondary",
        cite: "No frost line in Florida; FBC-R R403.1.4 12 in minimum applies.", src: "fbc8" }),
      termite: levelOf({ level: "very heavy", confirmed: "secondary",
        cite: "FBC-R R318 requires termite protection throughout Florida.", src: "fbc8" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC/FBC-R decay probability figure.", src: "fbc8" }),
      windborneDebris: wbdOf({ inRegion: null, likely: true, determinedBy: "site",
        confirmed: "unverified",
        cite: "FBC-R R301.2.1.2. Tampa Bay frontage puts land inside the 1-mile / 130 mph limb while " +
              "eastern Hillsborough may be outside both limbs. The county line is not the boundary.",
        src: "fbc8",
        note: "The clearest single illustration in the module of why a per-county windborne-debris " +
              "flag is wrong: two lots in the same county, same code, same builder, different " +
              "opening-protection requirement." }),
      amendments: [
        amend("Any local technical amendment adopted by Hillsborough County or the City of Tampa was " +
              "NOT retrieved.",
              "F.S. §553.73(4).", "fs-553-73", { incomplete: true })
      ],
      mustVerify: []
    },

    {
      id: "fl-lee", name: "Lee County", county: "Lee", state: "FL", kind: "county",
      packId: "fl-central",
      packWhy: "The only non-HVHZ Florida pack. Understates this county's wind badly — see packFor().",
      governs: "wind", hvhz: false,
      codes: [codeRec({ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
        basis: "2021 IRC", asce: "ASCE 7-22", adopted: "2023-12-31",
        cite: "FBC-R 8th Edition (2023), effective 31 December 2023.", src: "fbc8" })],
      wind: windOf({ vMph: 160, band: [150, 170], asce: "ASCE 7-22", exposureCommon: "C",
        confirmed: "unverified",
        basis: "Planning band for coastal south-west Florida from secondary ASCE 7-22 summaries.",
        cite: "ASCE 7-22 Figure 26.5-1 / FBC-R Figure R301.2(2), Risk Category II.", src: "asce7",
        note: "Lee County is not in the HVHZ and carries wind speeds within 10 mph of Broward's. " +
              "The design load is nearly HVHZ; the approval regime is the ordinary statewide one." }),
      snow: snowOf({ pgPsf: 0, cls: "code", confirmed: "secondary",
        cite: "Ground snow load is zero throughout Florida; FBC-R Table R301.2(1).", src: "fbc8" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "secondary",
        cite: "No frost line in Florida; FBC-R R403.1.4 12 in minimum applies.", src: "fbc8" }),
      termite: levelOf({ level: "very heavy", confirmed: "secondary",
        cite: "FBC-R R318 requires termite protection throughout Florida.", src: "fbc8" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC/FBC-R decay probability figure.", src: "fbc8" }),
      windborneDebris: wbdOf({ inRegion: null, likely: true, determinedBy: "site",
        confirmed: "unverified",
        cite: "FBC-R R301.2.1.2. At mapped speeds of 150 mph and above the 140 mph limb is reached " +
              "throughout, but the determination is still made at the site.", src: "fbc8" }),
      amendments: [
        amend("Any local technical amendment adopted by Lee County was NOT retrieved. Post-Ian " +
              "floodplain and substantial-improvement rules are administered here and are not " +
              "modelled by this product in any form.",
              "F.S. §553.73(4); FEMA NFIP; Lee County floodplain ordinance.", "fs-553-73",
              { incomplete: true })
      ],
      mustVerify: []
    },

    {
      id: "fl-duval", name: "Jacksonville / Duval County", county: "Duval", state: "FL",
      kind: "county",
      packId: "fl-central", packWhy: "Nearest Florida non-HVHZ pack; north Florida is not its market.",
      governs: "wind", hvhz: false,
      codes: [codeRec({ name: "Florida Building Code, Residential", edition: "8th Edition (2023)",
        basis: "2021 IRC", asce: "ASCE 7-22", adopted: "2023-12-31",
        cite: "FBC-R 8th Edition (2023), effective 31 December 2023.", src: "fbc8" })],
      wind: windOf({ vMph: 130, band: [120, 140], asce: "ASCE 7-22", exposureCommon: "C",
        confirmed: "unverified",
        basis: "Planning band for north-east Florida from secondary ASCE 7-22 summaries. This is the " +
               "lowest-wind jurisdiction in the Florida set.",
        cite: "ASCE 7-22 Figure 26.5-1 / FBC-R Figure R301.2(2), Risk Category II.", src: "asce7" }),
      snow: snowOf({ pgPsf: 0, cls: "code", confirmed: "secondary",
        cite: "Ground snow load is zero throughout Florida; FBC-R Table R301.2(1).", src: "fbc8" }),
      seismic: seismicOf({ sdc: "A", confirmed: "unverified", cite: "Planning value.", src: "asce7" }),
      frostDepthIn: frostOf({ inches: 0, confirmed: "secondary",
        cite: "No frost line in Florida; FBC-R R403.1.4 12 in minimum applies.", src: "fbc8" }),
      termite: levelOf({ level: "very heavy", confirmed: "secondary",
        cite: "FBC-R R318 requires termite protection throughout Florida.", src: "fbc8" }),
      decay: levelOf({ level: "moderate to severe", confirmed: "unverified",
        cite: "IRC/FBC-R decay probability figure.", src: "fbc8" }),
      windborneDebris: wbdOf({ inRegion: null, likely: true, determinedBy: "site",
        confirmed: "unverified",
        cite: "FBC-R R301.2.1.2. Duval has Atlantic frontage and the St Johns River through it; the " +
              "1-mile / 130 mph limb reaches part of the county and not all of it.", src: "fbc8" }),
      amendments: [
        amend("Any local technical amendment adopted by the City of Jacksonville was NOT retrieved.",
              "F.S. §553.73(4).", "fs-553-73", { incomplete: true })
      ],
      mustVerify: []
    }
  ];

  FM.juris = {};
  FM.juris.STATES = ["TX", "FL", "NC"];
  FM.juris.CHECKED = CHECKED;
  FM.juris.SOURCES = SOURCES;
  FM.juris.RESEARCH = RESEARCH;

  /* the builders are exported so a reviewer can see that every
     record in this file went through one, and so a later
     jurisdiction cannot be added by hand without the stamps */
  FM.juris._build = {
    wind: windOf, snow: snowOf, seismic: seismicOf, frost: frostOf,
    level: levelOf, wbd: wbdOf, code: codeRec, amendment: amend, mustVerify: mv
  };
})();
