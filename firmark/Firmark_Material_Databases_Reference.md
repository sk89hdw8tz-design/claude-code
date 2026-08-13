# Firmark Material Databases — Repository Reference Guide

> Source repository: <https://github.com/Firmark/material-databases>
> Snapshot: commit 7093386 2026-08-11 · Reference generated 2026-08-12
>
> **9 databases · 102 seed snapshots · 123 schema migrations** — every value tied to a cited official source revision.

## 1. Overview

Firmark Material Databases is a public repository of source-traceable material catalogs for structural and architectural engineering: the data layer behind [Firmark](https://tryfirmark.com)'s calculation and automation tooling.

**Why it is public.** Firmark is built around one principle: maximum transparency, no black box. Engineers are right not to trust tools they can't inspect; a licensed PE has to put their seal on whatever the tooling produces. So the data the tooling stands on is published to be checked. If any value disagrees with the source revision it cites, that is exactly the report the project wants (GitHub issue forms exist for value discrepancies and coverage gaps).

**What it is not:**

- **Not the engine.** The import, resolution, and calculation code that consumes these catalogs is part of Firmark's closed platform and is not published.
- **Not a design authority.** These are transcriptions with provenance. For actual engineering use, values must be taken from the governing documents; the cited source always controls.

## 2. The Nine Databases

| Database | Seeds | Migrations | Coverage |
|---|---:|---:|---|
| `member_db` | 35 | 25 | Sawn lumber, glulam, SCL, CLT, I-joists, posts/piles, decking: section properties and reference design values |
| `ceiling_wall_db` | 35 | 41 | Ceiling and wall product catalogs (suspension systems, panels, trims, accessories) |
| `steel_db` | 11 | 12 | Hot-rolled shapes and cold-formed steel: SFIA wall heights, axial/lateral tables, web crippling |
| `connector_db` | 7 | 28 | Connectors, fasteners, hold-downs, truss plates, shear-wall systems: evaluated-report and catalog identities kept distinct |
| `panel_db` | 6 | 4 | Wood structural panel assemblies, generic and manufacturer-specific |
| `masonry_db` | 4 | 5 | Masonry materials, units, and capacity tables |
| `roof_material_db` | 2 | 4 | Roofing material assemblies |
| `aluminum_db` | 1 | 2 | Extruded aluminum mechanical properties |
| `concrete_db` | 1 | 2 | Concrete material catalog |

Each database directory under `data/` carries its SQL schema migrations; the seed snapshots (JSON) sit at the `data/` root. `data/material_catalog_integrity_manifest_v1.json` pins every seed and migration by byte count and SHA-256.

## 3. Data Discipline

- **Source-exact values.** Manufacturer names, family identifiers, and unit strings are preserved exactly as printed in the source. Canonical identifiers are a separate join layer and never rewrite seed values.
- **Explicit provenance.** Every seed declares its dataset revision and the official source revision it was transcribed from (catalog editions, ICC-ES report reissue dates, standard years).
- **Null with reason.** Where a source does not publish a value, the omission is recorded explicitly. Values are never invented, interpolated, or decoded from model names.
- **Evaluated vs. catalog identity.** Evaluated performance (e.g. ICC-ES reports) is never silently merged with purchasable catalog identity; the two remain separately queryable, cross-referenced where the sources cross-reference them.

## 4. Repository Layout and Verification

- `data/*.json` — the canonical seed snapshots; canonical set declared by `material_catalog_integrity_manifest_v1.json` (byte count + SHA-256 pins).
- `data/<database>/migrations/*.sql` — the schema each database is built from, in order.
- `data/<database>/*.py` (where present) — byte-idempotent builder scripts that produced seeds from their pinned sources.
- `docs/SOURCE_REGISTER.md` — generated seed-by-seed provenance index (basis of Section 7 below).
- `tools/verify_integrity.py`, `tools/build_source_register.py` — standard-library-only verification tooling.
- `.github/` — issue forms (value discrepancy, coverage gap) and the CI workflow running both verifiers on every push.

*Line endings: every file is pinned byte-exact; the repository-level `.gitattributes` disables all conversion. Do not reformat.*

Verify locally:

```
python tools/verify_integrity.py
python tools/build_source_register.py --check
```

The first recomputes every pinned SHA-256 and byte count, checks the declared database/seed/migration counts, parses every seed, and confirms each declared dataset revision; any mutation of any pinned file fails it. The second confirms the source register matches the seeds. Both run in CI on every push.

## 5. License (Source-Available)

**Firmark Material Databases — Source-Available License. Copyright © 2026 Firmark LLC. All rights reserved.**

Published "source-available" for transparency and review. Permission is granted, free of charge, to view and clone the repository and run its verification tooling, solely to review, evaluate, and verify the data and its provenance, and to report findings back to the project. No other rights are granted. Without Firmark's prior written permission, the contents may not be:

1. used in products, services, or engineering deliverables;
2. redistributed, republished, or mirrored;
3. used to build derivative datasets, databases, or models.

The underlying factual values originate in the cited official sources; nothing in the license restricts use of those sources themselves. Contents provided "as is", without warranty. Not engineering advice — for design use, values must be taken from the governing official documents.

## 6. Contributing and Reporting Issues

The repository publishes governed data; the most valuable contribution is **review**. Data pull requests are closed by design: every seed is pinned in the integrity manifest, which is produced by Firmark's governed import pipeline, so a hand edit to a pinned seed fails integrity CI on purpose. Corrections ship back through the pipeline with provenance intact. PRs against documentation and `tools/` are welcome.

A value-discrepancy report the project can act on fastest names:

1. the seed path and where in it the value sits,
2. the source document and revision the seed cites,
3. the page/table in that source and the value you read there.

Coverage gaps (a member, product family, or value the catalogs should carry but don't) have their own issue form — name the authoritative source that publishes it.

## 7. Seed-by-Seed Catalog

Every canonical seed, its pinned dataset revision, declared record count, file size, and the official source documents it declares. Condensed from `docs/SOURCE_REGISTER.md` as of the snapshot commit; if this document disagrees with a seed, the seed controls. SHA-256 pins are recorded in the repository's integrity manifest and source register and are omitted here for readability.

### 7.1 `member_db`

Sawn lumber, glulam, SCL, CLT, I-joists, posts/piles, decking: section properties and reference design values. 35 seeds, 25 schema migrations.

#### `wood_clt_reference_design_values_esr3631_oklaminators.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 35
- **File size:** 94 KB
- **Content:** CLT Reference Design Values - OK Laminators CLT (ICC-ES ESR-3631)
- **Provenance note:** Values from ICC-ES ESR-3631 Tables 1-3 (OK Laminators CLT), developed per 2017 ANSI/APA PRG 320; dry service only. Out-of-plane bending (Table 2) AND in-plane shear (Table 3) are both tabulated. ESR-3631 publishes no lamination specified...

#### `wood_clt_reference_design_values_esr4733_smartlam.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 59
- **File size:** 156 KB
- **Content:** CLT Reference Design Values - SmartLam CLT (ICC-ES ESR-4733)
- **Provenance note:** Values from ICC-ES ESR-4733 Tables 1-5 (SmartLam CLT); PRG-320 cited only for cross-reference. ESR-4733 tabulates no in-plane shear (Fv/Gt) and no Fc-perp/G for the laminations - those fields are null with omission notes; nothing invented.

#### `wood_clt_reference_design_values_esr4875_nordic.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 15
- **File size:** 32 KB
- **Content:** CLT Reference Design Values - Nordic X-Lam (ICC-ES ESR-4875)
- **Provenance note:** Values from ICC-ES ESR-4875 Tables 1-4; PRG-320 standard used only for cross-reference (its PDF is encrypted).

#### `wood_clt_reference_design_values_esr5053_sterling.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 9
- **File size:** 27 KB
- **Content:** CLT Reference Design Values - Sterling TerraLam CLT (ICC-ES ESR-5053)
- **Provenance note:** Values from ICC-ES ESR-5053 Tables 1-3 (Sterling TerraLam CLT), developed per ANSI/APA PRG 320-2019; dry service only. Table 3 gives out-of-plane bending effective ASD values; ESR-5053 tabulates NO in-plane shear (Fv/Gt) table and NO bal...

#### `wood_clt_reference_design_values_esr5363_arboreal.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 120
- **File size:** 400 KB
- **Content:** CLT Reference Design Values - Arboreal CLT (ICC-ES ESR-5363)
- **Provenance note:** Values from ICC-ES ESR-5363 Tables 1-3 (Arboreal SA CLT), developed per ANSI/APA PRG 320-2019; dry service only. Table 3 gives out-of-plane bending effective ASD values keyed by (layup, laminations strength class); each (layup, class) is...

#### `wood_clt_reference_design_values_esr5517_theurl.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 25
- **File size:** 75 KB
- **Content:** CLT Reference Design Values - Theurl CLTplus (ICC-ES ESR-5517)
- **Provenance note:** Values from ICC-ES ESR-5517 Tables 1-4 (Theurl CLTplus), developed per ANSI/APA PRG 320 (the report's Evaluation Scope cites both PRG 320-2019 and PRG 320-2025); dry service only. Table 3 gives out-of-plane bending effective ASD values; ...

#### `wood_glulam_axial_reference_design_values_nds2024_table_5b.json`

- **Dataset revision:** `1.1.0`
- **Declared records:** 30
- **File size:** 68 KB
- **Content:** NDS 2024 Supplement Table 5B - Reference Design Values for Structural Glued Laminated Softwood Timber Combinations (members stressed primarily in axial tension or compression)
- **Governing reference:** AWC NDS Supplement Chapter 5, Table 5B.
- **Provenance note:** 30 glulam axial combinations (DF/HF/SW/AC/POC/SP) keyed (number, species, grade). 14 design values incl. E_axial(+0.95, +min), Fc by lam count (4+/2-3), Fby by lam count (4+/3/2), single Fbx, Fc-perp, Ft, Fvx, Fvy, G. E in psi. Table 5B ...

#### `wood_glulam_bending_combination_reference_design_values_nds2024_table_5a_expanded.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 56
- **File size:** 122 KB
- **Content:** NDS 2024 Supplement Table 5A Expanded - Reference Design Values for Structural Glued Laminated Softwood Timber Combinations (members stressed primarily in bending)
- **Governing reference:** AWC NDS Supplement Chapter 5, Table 5A Expanded.
- **Provenance note:** 56 softwood glulam bending COMBINATIONS keyed (combination_symbol, species) - the same symbol recurs across species blocks (DF/DF, DF/HF, HF/HF, SP/SP, AC/AC, POC/POC, ES/ES, SPF/SPF). 18 design values incl. dual-face Fc_perp_x (tension-...

#### `wood_glulam_current_official_public_2026_03_28.json`

- **Dataset revision:** `2026.07.14.04`
- **Declared records:** 529
- **File size:** 4.8 MB
- **Provenance:** declared per record inside the seed

#### `wood_glulam_hardwood_axial_reference_design_values_nds2024_table_5d.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 37
- **File size:** 84 KB
- **Content:** NDS 2024 Supplement Table 5D - Reference Design Values for Structural Glued Laminated Hardwood Timber (members stressed primarily in axial tension or compression)
- **Governing reference:** AWC NDS Supplement Chapter 5, Table 5D.
- **Provenance note:** 37 hardwood-axial glulam combinations H1-H37 (16 visually graded + 21 E-rated; species by group A-D). 13 design values: E + E,min (no 0.95*E), Fc by lam count (4+/2-3), Fby by lam count (4+/3/2), single Fbx, Fc-perp, Ft, Fvx, Fvy, G. E i...

#### `wood_glulam_reference_design_values_nds2024_table_5a.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 7
- **File size:** 14 KB
- **Content:** NDS 2024 Supplement Table 5A - Reference Design Values for Structural Glued Laminated Softwood Timber (stress classes, members stressed primarily in bending)
- **Governing reference:** AWC NDS Supplement Chapter 5, Table 5A (stress-class form).
- **Provenance note:** 7 glulam softwood bending stress classes x 16 design values (bi-axial: Fbx+/Fbx-, Fc_perp_x, Fvx, Ex true/app/min; Fby, Fc_perp_y, Fvy, Ey true/app/min; axial Ft, Fc; fastener G). E values in psi. Adjustment factors (volume Cv, flat-use,...

#### `wood_glulam_reference_design_values_nds2024_table_5c.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 21
- **File size:** 48 KB
- **Content:** NDS 2024 Supplement Table 5C - Reference Design Values for Structural Glued Laminated Hardwood Timber (members stressed primarily in bending)
- **Governing reference:** AWC NDS Supplement Chapter 5, Table 5C.
- **Provenance note:** 21 hardwood glulam bending combinations (12 visually graded + 9 E-rated incl. Yellow Poplar/Red Maple/Red Oak) in the shared glulam_reference_design_value catalog under source_table '5C'. 14 bending design values; Ex/Ey stored as apparen...

#### `wood_i_joist_performance_grades_esr1405.json`

- **Dataset revision:** `2025-12`
- **File size:** 762 KB
- **Content:** APA PRI-400 generic I-joist performance grades and detailing
- **Declared source documents:**
  - [APA PRI-400 generic I-joist performance grades and detailing](https://icc-es.org/wp-content/uploads/report-directory/ESR-1405.pdf)

#### `wood_i_joists_current_official_public_2026_03_28.json`

- **Dataset revision:** `2026-07-15`
- **Declared records:** 97
- **File size:** 923 KB
- **Content:** wood_i_joists_current_official_public
- **Provenance:** declared per record inside the seed

#### `wood_mass_plywood_esr4760.json`

- **Dataset revision:** `2025-11`
- **File size:** 99 KB
- **Content:** Freres Mass Ply Panel and Mass Ply Lam material catalog
- **Declared source documents:**
  - [Freres Mass Ply Panel and Mass Ply Lam material catalog](https://icc-es.org/wp-content/uploads/report-directory/ESR-4760.pdf)

#### `wood_posts_piles_resolved_current_official_public_2026_03_29.json`

- **Dataset revision:** `2026-03-29`
- **Declared records:** 2691
- **File size:** 6.2 MB
- **Content:** wood_posts_piles_resolved_current_official_public
- **Provenance:** declared per record inside the seed

#### `wood_sawn_decking_nds2024_table_4e.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 74
- **File size:** 132 KB
- **Content:** NDS 2024 Supplement Table 4E - Reference Design Values for Visually Graded Decking
- **Governing reference:** AWC NDS Supplement Chapter 4, Table 4E - visually graded decking (flatwise; Fb single + (Fb)(Cr) repetitive, Fc_perp, E, Emin, G).
- **Provenance note:** Decking is loaded flatwise: Table 4E publishes single-member Fb, repetitive-member (Fb)(Cr), Fc_perp, E, Emin, G; Ft/Fv/Fc-parallel are not tabulated. Dash cells -> null + exact_omission_notes. The 2"/3"-thick size factor (CF) is an adju...

#### `wood_sawn_mechanical_grade_species_properties_nds2024_table_4c_fn2.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 43
- **File size:** 64 KB
- **Content:** NDS 2024 Supplement Table 4C Footnote 2 — Specific Gravity / Fv / Fc-perp for MSR & MEL Lumber by Species + E
- **Governing reference:** AWC NDS Supplement Chapter 4, Table 4C footnote 2.
- **Declared source documents:**
  - [https://awc.org/resources/2024-nds-supplement/](https://awc.org/resources/2024-nds-supplement/)
  - [https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf](https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf)
  - [https://web-media.awc.org/wp-content/uploads/2025/03/27192445/2024-NDSSuppAddendum3.27.25.pdf](https://web-media.awc.org/wp-content/uploads/2025/03/27192445/2024-NDSSuppAddendum3.27.25.pdf)

#### `wood_sawn_mechanical_grades_nds2024_table_4c.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 85
- **File size:** 159 KB
- **Content:** NDS 2024 Supplement Table 4C — Reference Design Values, Mechanically Graded (MSR/MEL) Dimension Lumber
- **Governing reference:** AWC NDS Supplement Chapter 4, Table 4C — machine stress rated (MSR) + machine evaluated lumber (MEL).
- **Declared source documents:**
  - [https://awc.org/resources/2024-nds-supplement/](https://awc.org/resources/2024-nds-supplement/)
  - [https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf](https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf)

#### `wood_sawn_member_database_phase1_nds2024_v1_2_wet_pressure_treated.json`

- **Dataset revision:** `1.2.0`
- **Declared records:** 275
- **File size:** 862 KB
- **Content:** Phase 1 Wood Sawn Member Database - Wet Service Pressure-Treated Extension
- **Declared source documents:**
  - [AWC 2024 NDS Supplement resource page](https://awc.org/resources/2024-nds-supplement/)
  - [AWC February 2024 Addendum to the 2024 NDS Supplement](https://awc.org/wp-content/uploads/2024/02/2024NDS-Supplement-Updates-Errata_20240212.pdf)
  - [AWC March 2025 Addendum to the 2024 NDS Supplement](https://web-media.awc.org/wp-content/uploads/2025/03/27192445/2024-NDSSuppAddendum3.27.25.pdf)
  - [AWC 2018 NDS Supplement Chapter 4 (official AWC PDF)](https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf)
  - [2018 NDS Supplement full view-only PDF (licensed mirror)](https://www.fp-supply.com/cmss_files/attachmentlibrary/AWC-NDS2018-Supplement-ViewOnly-171027.pdf)
  - [AWC 2015 Manual for Engineered Wood Construction](https://awc.org/wp-content/uploads/2021/12/AWC-2015-Manual-1603.pdf)
  - [AWC Prescriptive Residential Wood Deck Construction Guide](https://awc.org/wp-content/uploads/2022/02/AWC-DCA62012-DeckGuide-1405.pdf)
  - [Pressure-Treated Southern Pine](https://www.southernpine.com/why-southern-pine/pressure-treated/)
  - [SPC Use Guide 2013](https://www.southernpine.com/wp-content/uploads/2023/09/SP_USEguide_METRIC_10-18L.pdf)
  - [2005 Errata to 2001 ASD / April 2003 Errata to NDS 2001](https://web-media.awc.org/wp-content/uploads/2021/12/17210637/AWC-ASD2001-Errata-0506.pdf)

#### `wood_sawn_reference_design_values_nds2024_table_4a.json`

- **Dataset revision:** `1.3.0`
- **Declared records:** 237
- **File size:** 431 KB
- **Content:** NDS 2024 Supplement Table 4A — Reference Design Values, Visually Graded Dimension Lumber (complete, incl. addenda)
- **Governing reference:** AWC NDS Supplement Chapter 4, Table 4A — visually graded dimension lumber (2"-4" thick), all species except Southern Pine.
- **Declared source documents:**
  - [https://awc.org/resources/2024-nds-supplement/](https://awc.org/resources/2024-nds-supplement/)
  - [https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf](https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf)
  - [https://awc.org/wp-content/uploads/2024/02/2024NDS-Supplement-Updates-Errata_20240212.pdf](https://awc.org/wp-content/uploads/2024/02/2024NDS-Supplement-Updates-Errata_20240212.pdf)
  - [https://web-media.awc.org/wp-content/uploads/2025/03/27192445/2024-NDSSuppAddendum3.27.25.pdf](https://web-media.awc.org/wp-content/uploads/2025/03/27192445/2024-NDSSuppAddendum3.27.25.pdf)

#### `wood_sawn_reference_design_values_nds2024_table_4b.json`

- **Dataset revision:** `1.2.0`
- **Declared records:** 105
- **File size:** 244 KB
- **Content:** NDS 2024 Supplement Table 4B — Reference Design Values, Visually Graded Southern Pine Dimension Lumber
- **Governing reference:** AWC NDS Supplement Chapter 4, Table 4B — visually graded Southern Pine dimension lumber (2"-4" thick), width-specific.
- **Declared source documents:**
  - [https://awc.org/resources/2024-nds-supplement/](https://awc.org/resources/2024-nds-supplement/)
  - [https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf](https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf)

#### `wood_sawn_reference_design_values_nds2024_table_4f.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 144
- **File size:** 270 KB
- **Content:** NDS 2024 Supplement Table 4F - Reference Design Values for Non-North American Visually Graded Dimension Lumber (2"-4" thick)
- **Governing reference:** AWC NDS Supplement Chapter 4, Table 4F - non-North-American visually graded dimension lumber.
- **Provenance note:** 18 imported species-groups x 8 grades (SS/No.1/No.2/No.3/Stud at 2" & wider; Construction/Standard/Utility at 2"-4" wide). Same 7-value column set as Table 4A; stored in the shared sawn_reference_design_value catalog under source_table '...

#### `wood_sawn_section_properties_nds2024_table_1b.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 86
- **File size:** 129 KB
- **Content:** NDS 2024 Supplement Table 1B — Sawn-Lumber Section Properties (S4S)
- **Governing reference:** AWC NDS Supplement (2024) Chapter 3: Table 1A (dressed sizes), Table 1B (section properties); geometry edition-stable across 2015/2018/2024.
- **Declared source documents:**
  - [NDS Supplement Table 1A — Nominal and Minimum Dressed Sizes of Sawn Lumber](https://awc.org/resources/2024-nds-supplement/)
  - [NDS Supplement Table 1B — Section Properties of Standard Dressed (S4S) Sawn Lumber (Boards / Dimension Lumber / Posts and Timbers)](https://awc.org/resources/2024-nds-supplement/)
  - [NDS Supplement Table 1B (Cont.) — Section Properties of Standard Dressed (S4S) Sawn Lumber (Beams and Stringers)](https://awc.org/resources/2024-nds-supplement/)
  - [NDS Supplement Section 3.1 — Section Properties of Sawn Lumber (symbols/formulas)](https://awc.org/resources/2024-nds-supplement/)
  - [Voluntary Product Standard PS 20, American Softwood Lumber Standard — Nominal and Minimum-Dressed Sizes (governing root standard for dressed sizes)](https://www.alsc.org/greenbook%20collection/ps20.pdf)
  - [AWC 2018 NDS Supplement Chapter 3 — Section Properties (downloadable, edition-stable corroboration)](https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter03.pdf)

#### `wood_sawn_timbers_nds2024_table_4d.json`

- **Dataset revision:** `1.1.0`
- **Declared records:** 239
- **File size:** 430 KB
- **Content:** NDS 2024 Supplement Table 4D — Reference Design Values, Visually Graded Timbers (5x5 and larger)
- **Governing reference:** AWC NDS Supplement Chapter 4, Table 4D — visually graded timbers, Beams & Stringers and Posts & Timbers.
- **Declared source documents:**
  - [https://awc.org/resources/2024-nds-supplement/](https://awc.org/resources/2024-nds-supplement/)
  - [https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf](https://awc.org/wp-content/uploads/2021/10/AWC_NDS2018-Supplement_20200827_AWCWebsite_Chapter4.pdf)

#### `wood_scl_members_current_official_public_2026_03_28.json`

- **Dataset revision:** `2026.03.28`
- **Declared records:** 197
- **File size:** 415 KB
- **Provenance:** declared per record inside the seed

#### `wood_scl_reference_design_values_esr1040_boise_versalam.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 38
- **File size:** 137 KB
- **Content:** ICC-ES ESR-1040 (Boise Cascade VERSA-LAM LVL) - SCL Reference Design Values
- **Governing reference:** ICC-ES ESR-1040 (Reissued September 2025), Table 1.
- **Provenance note:** Boise Cascade VERSA-LAM LVL from ICC-ES ESR-1040 Table 1 (p.5), 38 grades. Tier-1 ESR. e = E_apparent (E_true + E_apparent both preserved in reference_values_conditional; PE to confirm which the engine consumes). ESR-1040 tabulates CoV_E...

#### `wood_scl_reference_design_values_esr1053_westfraser_durastrand.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 6
- **File size:** 31 KB
- **Content:** ICC-ES ESR-1053 (West Fraser Durastrand LSL + OSL) - SCL Reference Design Values
- **Governing reference:** ICC-ES ESR-1053 (Reissued September 2025), Table 1.
- **Provenance note:** West Fraser (formerly Norbord) Durastrand LSL (3 grades) + OSL (3 grades, FIRST OSL records) from ICC-ES ESR-1053 Table 1, rev 'Reissued September 2025'. Tier-1 ESR. Single shear-free (TRUE) MOE column -> e=E_true, emin=null, cov_e=null ...

#### `wood_scl_reference_design_values_esr1210_roseburg_rigidlam.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 6
- **File size:** 50 KB
- **Content:** ICC-ES ESR-1210 (Roseburg RigidLam LVL) - SCL Reference Design Values
- **Governing reference:** ICC-ES ESR-1210 (Reissued September 2024; Revised September 2025), Table 1.
- **Provenance note:** Roseburg Forest Products RigidLam LVL (6 grades 1.4E-2.4E, true-E labels) from ICC-ES ESR-1210 Table 1, rev 'Reissued Sept 2024; Revised Sept 2025'. Tier-1 ESR. e=E_apparent where published (e_true + e_apparent in reference_values_condit...

#### `wood_scl_reference_design_values_esr1387_weyerhaeuser.json`

- **Dataset revision:** `1.1.0`
- **Declared records:** 47
- **File size:** 106 KB
- **Content:** ICC-ES ESR-1387 (Weyerhaeuser) - SCL Reference Design Values (Microllam LVL, Parallam PSL, TimberStrand LSL)
- **Governing reference:** ICC-ES ESR-1387 (Reissued February 2025; Revised June 2025), Table 1.
- **Provenance note:** Weyerhaeuser/Trus Joist SCL from ICC-ES ESR-1387 Table 1. Tier-1 ESR source (the existing wood_scl_members_current_*.json is separate Tier-2 manufacturer-guide data). Fb at 12-in ref depth + depth exponent; dual Fc-perp (edge/wide-face);...

#### `wood_scl_reference_design_values_esr1898_global_lvl.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 4
- **File size:** 40 KB
- **Content:** ICC-ES ESR-1898 (Global LVL) - SCL Reference Design Values
- **Governing reference:** ICC-ES ESR-1898 (Reissued June 2026), Table 1.
- **Provenance note:** Global LVL, Inc. Global LVL (4 grades: 2800Fb-1.7E, 2850Fb-1.9E [Aspen]; 3025Fb-1.9E, 3300Fb-2.0E [Birch/Aspen]) from ICC-ES ESR-1898 Table 1, rev 'Reissued June 2026'. Tier-1 ESR. Single shear-free (true) MOE -> e=E_true (=grade label)....

#### `wood_scl_reference_design_values_esr2909_pacificwoodtech.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 10
- **File size:** 63 KB
- **Content:** ICC-ES ESR-2909 (Pacific Woodtech PWT LVL + Treated LVL) - SCL Reference Design Values
- **Governing reference:** ICC-ES ESR-2909 (Reissued September 2025; Revised November 2025), Table 1.
- **Provenance note:** Pacific Woodtech PWT LVL (8 grades) + PWT Treated LVL (dry + wet-use, own design values) from ICC-ES ESR-2909 Table 1A/1B, rev 'Reissued Sept 2025; Revised Nov 2025'. Tier-1 ESR. Single shear-free (TRUE) MOE -> e=E_true, emin=null, cov_e...

#### `wood_scl_reference_design_values_esr2993_redbuilt_redlam.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 11
- **File size:** 122 KB
- **Content:** ICC-ES ESR-2993 (RedBuilt RedLam LVL) - SCL Reference Design Values
- **Governing reference:** ICC-ES ESR-2993 (Reissued January 2025; Revised May 2026), Table 1.
- **Provenance note:** RedBuilt LLC RedLam LVL (11 grades 1.4E-2.6E incl. 2.0E vs 2.0E-2900Fb) from ICC-ES ESR-2993 Table 1, rev 'Reissued Jan 2025; Revised May 2026' (additional listee Boise Cascade). Tier-1 ESR. FIRST catalog ESR with a tabulated Emin (fn11)...

#### `wood_scl_reference_design_values_esr3633_metsa_kerto.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 1
- **File size:** 21 KB
- **Content:** ICC-ES ESR-3633 (Metsa Wood Kerto LVL S-beam / Master Plank LVL) - SCL Reference Design Values
- **Governing reference:** ICC-ES ESR-3633 (Reissued July 2025), Table 1.
- **Provenance note:** Metsa Wood (Metsaliitto Cooperative, Finland; distributed by Metsa Wood USA) Kerto LVL S-beam, also known as Master Plank LVL, from ICC-ES ESR-3633 Table 1, rev 'Reissued July 2025'. Tier-1 ESR. SINGLE un-labeled structural grade (no E-g...

#### `wood_scl_reference_design_values_esr4618_pollmeier_spruce.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 3
- **File size:** 46 KB
- **Content:** ICC-ES ESR-4618 (Pollmeier Spruce LVL) - SCL Reference Design Values
- **Governing reference:** ICC-ES ESR-4618 (Reissued April 2026), Tables 1 & 3.
- **Provenance note:** Pollmeier Spruce LVL (spruce veneers -- NOT BauBuche beech, per the ESR evaluation subject) from ICC-ES ESR-4618, rev 'Reissued April 2026'. Tier-1 ESR. 3 records across two thickness classes keyed (grade+thickness): 1-3/4in billet 2.1E ...

### 7.2 `ceiling_wall_db`

Ceiling and wall product catalogs (suspension systems, panels, trims, accessories). 35 seeds, 41 schema migrations.

#### `ceiling_and_wall_products_current_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12`
- **Declared records:** 41
- **File size:** 128 KB
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_armstrong_accessory_master_2026.json`

- **Dataset revision:** `2026-07-13`
- **File size:** 5.5 MB
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_armstrong_axiom_building_perimeter_2026.json`

- **Dataset revision:** `armstrong_axiom_building_perimeter_current_official_2026_07_13_v1`
- **File size:** 535 KB
- **Content:** current official AXIOM Building Perimeter product/accessory state plus visually audited data-sheet and installation-guide schedules, rules, aliases, and conflicts
- **Declared source documents:**
  - [axiom-building-perimeters-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-building-perimeters.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-building-perimeter-system-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-building-perimeter-system-data-sheet.pdf)
  - [axiom-building-perimeter-system-installation-guide.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-building-perimeter-system-installation-guide.pdf)

#### `ceiling_wall_armstrong_axiom_classic_2026.json`

- **Dataset revision:** `2026.07.12`
- **File size:** 2.7 MB
- **Content:** Complete current official AXIOM Classic family: 99 product items, exact live finish configurations, source-union finish palette, accessory union, straight/curved/full-carton/corner schedules, installation rules, and conflicts.
- **Declared source documents:**
  - [axiom-classic-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-classic-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-classic-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-classic-data-sheet.pdf)
  - [axiom-classic-curved-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-classic-curved-data-sheet.pdf)
  - [axiom-classic-installation-guide.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-classic-installation-guide.pdf)

#### `ceiling_wall_armstrong_axiom_design_trough_2026.json`

- **Dataset revision:** `armstrong_axiom_design_trough_current_document_union_2026_07_13_v1`
- **File size:** 134 KB
- **Declared source documents:**
  - [axiom-design-trough-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-design-trough.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-design-trough-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-design-troughs-data-sheet.pdf)
  - [axiom-design-trough-installation.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-design-troughs-installation.pdf)

#### `ceiling_wall_armstrong_axiom_direct_light_cove_2026.json`

- **Dataset revision:** `armstrong_axiom_direct_light_cove_current_document_union_2026_07_13_v1`
- **File size:** 252 KB
- **Declared source documents:**
  - [axiom-direct-light-coves-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-direct-light-coves-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-direct-light-coves-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-direct-light-coves-data-sheet.pdf)
  - [axiom-direct-light-coves-installation-guide.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-direct-light-coves-installation-guide.pdf)

#### `ceiling_wall_armstrong_axiom_direct_light_cove_specialty_2026.json`

- **Dataset revision:** `armstrong_axiom_direct_light_cove_specialty_current_document_union_2026_07_13_v1`
- **File size:** 191 KB
- **Declared source documents:**
  - [axiom-direct-light-coves-specialty-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-direct-field-light-coves-specialty-ceilings-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-direct-light-coves-specialty-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-direct-light-coves-specialty-ceilings-data-sheet.pdf)
  - [axiom-direct-light-coves-installation-guide.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-direct-light-coves-installation-guide.pdf)

#### `ceiling_wall_armstrong_axiom_drywall_trim_2026.json`

- **Dataset revision:** `2026-07-13`
- **File size:** 457 KB
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_armstrong_axiom_glazing_channel_2026.json`

- **Dataset revision:** `2026-07-13`
- **File size:** 188 KB
- **Content:** Complete current/document-union AXIOM Glazing Channel profile, component, geometry, installer-material, rule, and conflict catalog.
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_armstrong_axiom_indirect_field_light_cove_2026.json`

- **Dataset revision:** `armstrong_axiom_indirect_field_light_cove_current_document_union_2026_07_13_v1`
- **File size:** 300 KB
- **Declared source documents:**
  - [axiom-indirect-field-light-coves-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-indirect-field-light-coves-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-indirect-field-light-coves-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-indirect-field-light-coves-data-sheet.pdf)
  - [axiom-indirect-field-light-coves-installation-guide.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-indirect-field-light-coves-installation-guide.pdf)

#### `ceiling_wall_armstrong_axiom_indirect_field_light_cove_specialty_2026.json`

- **Dataset revision:** `2026-07-13`
- **File size:** 280 KB
- **Content:** Complete current/document-union AXIOM Indirect Field Light Coves for Specialty Ceilings profile, component, geometry, installer-material, rule, and conflict catalog.
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_armstrong_axiom_indirect_light_cove_2026.json`

- **Dataset revision:** `armstrong_axiom_indirect_light_cove_current_document_union_2026_07_13_v1`
- **File size:** 419 KB
- **Declared source documents:**
  - [axiom-indirect-light-coves-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-indirect-light-coves-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-indirect-light-coves-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-indirect-light-coves-data-sheet.pdf)
  - [axiom-indirect-light-coves-installation-guide.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-indirect-light-coves-installation-guide.pdf)

#### `ceiling_wall_armstrong_axiom_indirect_light_ledge_2026.json`

- **Dataset revision:** `2026-07-13`
- **File size:** 217 KB
- **Content:** complete_current_visible_document_union
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_armstrong_axiom_interlude_2026.json`

- **Dataset revision:** `armstrong_axiom_interlude_current_document_union_2026_07_13_v1`
- **File size:** 146 KB
- **Content:** Complete current/document-union Armstrong AXIOM for INTERLUDE catalog
- **Declared source documents:**
  - [axiom-interlude-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-interlude-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-for-interlude-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-for-interlude-data-sheet.pdf)

#### `ceiling_wall_armstrong_axiom_knife_edge_2026.json`

- **Dataset revision:** `armstrong_axiom_knife_edge_current_document_union_2026_07_13_v1`
- **File size:** 456 KB
- **Content:** Complete current/document-union Armstrong AXIOM KNIFE EDGE catalog
- **Declared source documents:**
  - [axiom-knife-edge-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-knife-edge-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-knife-edge-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-knife-edge-data-sheet.pdf)
  - [axiom-knife-edge-installation.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-knife-edge-installation.pdf)
  - [axiom-trims-brochure.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/brochures/axiom-trims-brochure.pdf)

#### `ceiling_wall_armstrong_axiom_lutron_shade_pockets_2026.json`

- **Dataset revision:** `armstrong_axiom_lutron_shade_pockets_current_document_union_2026_07_13_v1`
- **File size:** 372 KB
- **Content:** Complete current Lutron-family items and exact configurations, exact current and document-only components, cross-family overlaps, all selected data-sheet schedules, all visually audited installation identities, material/BOM rules, and conflicts.
- **Declared source documents:**
  - [axiom-lutron-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-building-perimeters-lutron-compatible.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-lutron-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-building-perimeter-pockets-for-lutron-shades-data-sheet.pdf)
  - [axiom-lutron-installation-guide.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-lutron-compatible-shade-pockets-installation-guide.pdf)

#### `ceiling_wall_armstrong_axiom_moldings_column_rings_2026.json`

- **Dataset revision:** `armstrong_axiom_moldings_column_rings_current_document_union_2026_07_13_v1`
- **File size:** 319 KB
- **Content:** Complete current/document-union Armstrong AXIOM Moldings & Column Rings catalog
- **Declared source documents:**
  - [axiom-moldings-column-rings-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-molding-column-rings-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-moldings-column-rings-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-moldings-column-rings-data-sheet.pdf)

#### `ceiling_wall_armstrong_axiom_paired_2026.json`

- **Dataset revision:** `armstrong_axiom_paired_current_document_union_2026_07_13_v1`
- **File size:** 1.4 MB
- **Content:** Complete current/document-union Armstrong AXIOM Paired catalog
- **Declared source documents:**
  - [axiom-paired-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-paired-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-paired-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-paired-data-sheet.pdf)
  - [axiom-trims-brochure.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/brochures/axiom-trims-brochure.pdf)

#### `ceiling_wall_armstrong_axiom_transitions_2026.json`

- **Dataset revision:** `armstrong_axiom_transitions_current_document_union_2026_07_13_v1`
- **File size:** 437 KB
- **Content:** Complete current/document-union Armstrong AXIOM Transitions catalog
- **Declared source documents:**
  - [axiom-transitions-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-transitions-trim.html)
  - [axiom-perimeter-category-page1.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json)
  - [axiom-perimeter-category-page2.json](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim/_jcr_content.browseresults.json?page=2)
  - [axiom-transitions-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-transitions-data-sheet.pdf)
  - [axiom-transitions-installation-instructions.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-transitions-installation-instructions.pdf)

#### `ceiling_wall_armstrong_axiom_vector_2026.json`

- **Dataset revision:** `2026.07.12`
- **File size:** 2.5 MB
- **Content:** Complete current official AXIOM Vector family: 98 product items, exact live finish configurations, source-union finish palette, accessory union, straight/curved/vertical schedules, corners, installation rules, and conflicts.
- **Declared source documents:**
  - [axiom-vector-family.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/axiom-vector-trim.html)
  - [axiom-perimeter-category.html](https://www.armstrongceilings.com/commercial/en/suspension-systems/trims-and-transitions/axiom-perimeter-trim.html)
  - [axiom-vector-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-vector-data-sheet.pdf)
  - [axiom-vector-curved-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/axiom-vector-curved-data-sheet.pdf)
  - [axiom-vector-installation.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/installation-and-maintenance/axiom-vector-installation.pdf)
  - [360-painted-grid-data-sheet.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/data-sheets/360-painted-grid-data-sheet.pdf)
  - [axiom-trims-brochure.pdf](https://www.armstrongceilings.com/content/dam/armstrongceilings/commercial/north-america/brochures/axiom-trims-brochure.pdf)

#### `ceiling_wall_armstrong_feltworks_acoustical_wall_panels_2026.json`

- **Dataset revision:** `2026.07.12`
- **File size:** 86 KB
- **Content:** Complete current official FELTWORKS acoustical wall panels, exact finishes, mounting acoustics, accessories, adhesives, application rules, and source conflicts.
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_armstrong_soundscapes_wall_panels_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 142 KB
- **Provenance note:** Complete current official Shapes and Blades wall-panel schedules for painted and wood-look variants, including standard finish expansion. Custom colors/panels are retained as availability rules because their exact SKUs are not enumerable...

#### `ceiling_wall_armstrong_suspension_master_2026.json`

- **Dataset revision:** `2026-07-13`
- **File size:** 10.1 MB
- **Content:** Complete current commercial suspension-system category, line, base-item, line-scoped specification, and exact configured-material surface.
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_armstrong_tectum_create_wall_panels_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 70 KB
- **Provenance note:** Complete current official TECTUM Create! catalog: every standard design, design-by-size configuration, exact panel identifier/material ID, mounting/NRC fact, custom artwork specification and claim, order/application rule, and explicit ac...

#### `ceiling_wall_armstrong_tectum_designart_lines_wall_panels_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 1.2 MB
- **Provenance note:** Complete current official Direct-Attach, High NRC, and Finale PB routed Lines wall schedules: every panel base, pattern, family finish, exact finished item, mounting/acoustic fact, live accessory finish variant, family accessory occurren...

#### `ceiling_wall_armstrong_tectum_designart_shapes_wall_panels_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 598 KB
- **Provenance note:** Complete current official DesignArt Shapes Direct-Attach wall catalog: every panel base, exact finished item, mounting/acoustic fact, live accessory variant, Pattern Gallery hue/color occurrence, and visually audited example-layout BOM l...

#### `ceiling_wall_armstrong_tectum_direct_attach_wall_panels_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 319 KB
- **Provenance note:** Complete current official standard Direct-Attach and High NRC wall schedules: all base items, standard finish expansions, acoustics, mounting constructions, accessories, touch-up-paint expansions, packaging facts and explicit omissions, ...

#### `ceiling_wall_armstrong_tectum_finale_pb_wall_panels_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 105 KB
- **Provenance note:** Complete current official Finale PB wall schedule: every base and finished item, shared TECTUM finish occurrence, product construction, official-source conflicts, acoustics, mounting methods, accessories, touch-up paint, layout constrain...

#### `ceiling_wall_armstrong_woodworks_grille_forte_wall_panels_2026.json`

- **Dataset revision:** `2026.07.12`
- **File size:** 721 KB
- **Content:** Complete current official WOODWORKS Grille - Forté solid wall panels, finishes, accessories, source conflicts, custom options, and installation rules.
- **Provenance:** declared per record inside the seed

#### `ceiling_wall_clarkdietrich_lath_accessory_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12`
- **Declared records:** 194
- **File size:** 505 KB
- **Content:** All printed product schedule rows on catalog pages 4-19; one row per printed size/weight variant.
- **Declared source documents:**
  - [official source](https://www.clarkdietrich.com/sites/default/files/media/documents/CD_Metal_Lath_Access_Catalog.pdf)

#### `ceiling_wall_usg_acoustical_panel_packaging_2026.json`

- **Dataset revision:** `2026-07-12`
- **Declared records:** 390
- **File size:** 301 KB
- **Declared source documents:**
  - [official source](https://www.usg.com/content/dam/USG_Marketing_Communications/united_states/product_promotional_materials/finished_assets/usg-ceiling-solutions-catalog-pro-edition-wl294911.pdf)

#### `ceiling_wall_usg_acoustical_panel_performance_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 707 KB
- **Declared source documents:**
  - [official source](https://www.usg.com/content/dam/USG_Marketing_Communications/united_states/product_promotional_materials/finished_assets/usg-ceiling-solutions-catalog-pro-edition-wl294911.pdf)

#### `ceiling_wall_usg_interior_finishing_j1424.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 650 KB
- **Content:** USG Interior Finishing Products commodity catalog
- **Declared source documents:**
  - [USG Interior Finishing Products commodity catalog](https://www.usg.com/content/dam/USG_Marketing_Communications/united_states/product_promotional_materials/finished_assets/usg-interior-finishings-catalog-en-J1424.pdf)

#### `ceiling_wall_usg_renditions_specialty_panels_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 56 KB
- **Declared source documents:**
  - [official source](https://www.usg.com/content/dam/USG_Marketing_Communications/united_states/product_promotional_materials/finished_assets/usg-ceiling-solutions-catalog-pro-edition-wl294911.pdf)

#### `ceiling_wall_usg_suspension_accessory_packaging_2026.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 289 KB
- **Declared source documents:**
  - [official source](https://www.usg.com/content/dam/USG_Marketing_Communications/united_states/product_promotional_materials/finished_assets/usg-ceiling-solutions-catalog-pro-edition-wl294911.pdf)

### 7.3 `steel_db`

Hot-rolled shapes and cold-formed steel: SFIA wall heights, axial/lateral tables, web crippling. 11 seeds, 12 schema migrations.

#### `steel_cold_formed_channel_ceiling_spans_sfia_v2025_1.json`

- **Dataset revision:** `2026-01`
- **Declared records:** 1020
- **File size:** 1.6 MB
- **Content:** SFIA cold-formed U-channel and hat-furring allowable ceiling spans
- **Declared source documents:**
  - [SFIA cold-formed U-channel and hat-furring allowable ceiling spans](https://sfia.memberclicks.net/assets/Library/TechnicalCatalog/SFIA-technical-product-guide_FINAL_20260107.pdf)

#### `steel_cold_formed_combined_axial_lateral_sfia_v2025_1.json`

- **Dataset revision:** `2026-01`
- **Declared records:** 11664
- **File size:** 23.9 MB
- **Content:** SFIA combined axial and lateral allowable load matrices
- **Declared source documents:**
  - [SFIA combined axial and lateral allowable load matrices](https://sfia.memberclicks.net/assets/Library/TechnicalCatalog/SFIA-technical-product-guide_FINAL_20260107.pdf)

#### `steel_cold_formed_fastener_capacities_sfia_v2025_1.json`

- **Dataset revision:** `2026-01`
- **File size:** 112 KB
- **Content:** SFIA cold-formed steel screw and weld allowable capacities
- **Declared source documents:**
  - [SFIA cold-formed steel screw and weld allowable capacities](https://sfia.memberclicks.net/assets/Library/TechnicalCatalog/SFIA-technical-product-guide_FINAL_20260107.pdf)

#### `steel_cold_formed_header_uniform_loads_sfia_v2025_1.json`

- **Dataset revision:** `2026-01`
- **Declared records:** 833
- **File size:** 1.3 MB
- **Content:** SFIA cold-formed steel header allowable uniform loads
- **Declared source documents:**
  - [SFIA cold-formed steel header allowable uniform loads](https://sfia.memberclicks.net/assets/Library/TechnicalCatalog/SFIA-technical-product-guide_FINAL_20260107.pdf)

#### `steel_cold_formed_joist_uniform_loads_sfia_v2025_1.json`

- **Dataset revision:** `2026-01`
- **Declared records:** 2958
- **File size:** 5.5 MB
- **Content:** SFIA floor and roof joist allowable uniform loads
- **Declared source documents:**
  - [SFIA floor and roof joist allowable uniform loads](https://sfia.memberclicks.net/assets/Library/TechnicalCatalog/SFIA-technical-product-guide_FINAL_20260107.pdf)

#### `steel_cold_formed_sections_current_official_public_2026_07_11.json`

- **Dataset revision:** `2026-07-11`
- **Declared records:** 571
- **File size:** 982 KB
- **Content:** Cold-formed steel framing section properties (studs/tracks/U-channels/hat-furring) - SFIA Technical Guide v2025.1
- **Provenance:** declared per record inside the seed

#### `steel_cold_formed_ultra_span_truss_sections_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12`
- **Declared records:** 44
- **File size:** 296 KB
- **Content:** Aegis/MiTek Ultra-Span cold-formed steel truss sections
- **Provenance note:** Current Tier-1 ICC-ES report; no inferred member capacities.

#### `steel_cold_formed_wall_heights_sfia_v2025_1.json`

- **Dataset revision:** `2026-01`
- **Declared records:** 11862
- **File size:** 24.0 MB
- **Content:** SFIA cold-formed steel limiting wall heights
- **Declared source documents:**
  - [SFIA cold-formed steel limiting wall heights](https://sfia.memberclicks.net/assets/Library/TechnicalCatalog/SFIA-technical-product-guide_FINAL_20260107.pdf)

#### `steel_cold_formed_web_crippling_sfia_v2025_1.json`

- **Dataset revision:** `2026-01`
- **Declared records:** 2944
- **File size:** 6.4 MB
- **Content:** SFIA cold-formed steel allowable web-crippling capacities
- **Declared source documents:**
  - [SFIA cold-formed steel allowable web-crippling capacities](https://sfia.memberclicks.net/assets/Library/TechnicalCatalog/SFIA-technical-product-guide_FINAL_20260107.pdf)

#### `steel_material_grades_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026-07-19`
- **Declared records:** 6
- **File size:** 12 KB
- **Content:** Structural steel material grades (Fy/Fu) - AISC 16th-ed and AISC 303-22 shop-standard materials plus the ASTM A36 alternative
- **Provenance:** declared per record inside the seed

#### `steel_shapes_current_official_public_2026_07_11.json`

- **Dataset revision:** `2026-07-11`
- **Declared records:** 2299
- **File size:** 4.6 MB
- **Content:** AISC Shapes Database v16.0 - hot-rolled structural steel shapes (US-customary)
- **Provenance:** declared per record inside the seed

### 7.4 `connector_db`

Connectors, fasteners, hold-downs, truss plates, shear-wall systems: evaluated-report and catalog identities kept distinct. 7 seeds, 28 schema migrations.

#### `connector_allowable_installations_current_official_public_2026_07_11.json`

- **Dataset revision:** `2026-07-19`
- **Declared records:** 3131
- **File size:** 29.3 MB
- **Content:** Structural connector allowable installations — allowable loads by fastener x species x direction
- **Provenance note:** Founder-expanded connector build: full Simpson + MiTek line, full-line TIER-TAGGED. Simpson joist hangers from ICC-ES ESR-2552 (Reissued April 2026): P3a single-nail face-mount (LUS T6/MUS T7/HUS T8/HHUS T9/HGUS T10) + P3b LU T1 & U T3 (...

#### `connector_fasteners_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026.07.19-bostitch-current`
- **File size:** 52.9 MB
- **Content:** Structural fastener products and reference design values
- **Provenance note:** Source-backed evaluated structural fasteners plus manufacturer catalog physical products, package SKUs, accessories, and compatibility. Catalog rows do not imply unpublished strengths; report and catalog identities remain separate and li...

#### `connector_hold_down_design_components_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 419 KB
- **Content:** ESR-3105 hold-down threaded-rod and wood-compression design components
- **Declared source documents:**
  - [ESR-3105 hold-down threaded-rod and wood-compression design components](https://icc-es.org/wp-content/uploads/report-directory/ESR-3105.pdf)

#### `connector_metal_webs_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12.1`
- **File size:** 435 KB
- **Content:** MiTek POSI-STRUT metal web governed catalog
- **Declared source documents:**
  - [MiTek POSI-STRUT metal web governed catalog](https://icc-es.org/wp-content/uploads/report-directory/ESR-4722.pdf)

#### `connector_seed_all_products_current_catalog_2026_03_29.json`

- **Dataset revision:** `2026-03-29`
- **Declared records:** 4243
- **File size:** 25.9 MB
- **Content:** simpson_mitek_all_current_catalog_products_seed
- **Provenance:** declared per record inside the seed

#### `connector_shear_wall_systems_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12.1`
- **File size:** 2.6 MB
- **Content:** MiTek Hardy Frame shear wall panel components governed catalog
- **Declared source documents:**
  - [MiTek Hardy Frame shear wall panel components governed catalog](https://icc-es.org/wp-content/uploads/report-directory/ESR-2089.pdf)

#### `connector_truss_plates_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12`
- **File size:** 257 KB
- **Content:** MiTek metal truss connector plates and hinge plate connectors
- **Provenance note:** Preserves plate design values only. Complete truss design, fabrication, quality assurance, special inspection, and diaphragm design remain outside the governed data slice.

### 7.5 `panel_db`

Wood structural panel assemblies, generic and manufacturer-specific. 6 seeds, 4 schema migrations.

#### `wood_panel_assemblies_current_official_public_2026_03_29.json`

- **Dataset revision:** `2026-03-29`
- **Declared records:** 10
- **File size:** 36 KB
- **Provenance:** declared per record inside the seed

#### `wood_panel_assemblies_manufacturer_specific_current_official_public_2026_03_29.json`

- **Dataset revision:** `2026-03-29`
- **Declared records:** 9
- **File size:** 22 KB
- **Provenance:** declared per record inside the seed

#### `wood_panel_engineering_rules_current_official_public_2026_03_30.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 19
- **File size:** 30 KB
- **Provenance:** declared per record inside the seed

#### `wood_panel_engineering_tables_current_official_public_2026_03_30.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 16
- **File size:** 293 KB
- **Provenance:** declared per record inside the seed

#### `wood_structural_panels_current_official_public_2026_03_29.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 11
- **File size:** 36 KB
- **Provenance:** declared per record inside the seed

#### `wood_structural_panels_manufacturer_specific_current_official_public_2026_03_29.json`

- **Dataset revision:** `2026-07-02`
- **Declared records:** 74
- **File size:** 215 KB
- **Provenance:** declared per record inside the seed

### 7.6 `masonry_db`

Masonry materials, units, and capacity tables. 4 seeds, 5 schema migrations.

#### `masonry_cmu_section_properties_cmha_cmu_tec_002_23.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 36
- **File size:** 64 KB
- **Content:** CMHA CMU-TEC-002-23 concrete masonry assembly section properties
- **Provenance:** declared per record inside the seed

#### `masonry_fm_unit_strength_current_official_public_2026_07_11.json`

- **Dataset revision:** `2026-07-11`
- **Declared records:** 21
- **File size:** 26 KB
- **Content:** Masonry specified compressive strength f'm - unit-strength method (concrete + clay)
- **Provenance:** declared per record inside the seed

#### `masonry_materials_and_units_current_official_public_2026_03_29.json`

- **Dataset revision:** `2026-03-29`
- **Declared records:** 77
- **File size:** 165 KB
- **Provenance:** declared per record inside the seed

#### `masonry_published_capacities_cmha_asd_v1.json`

- **Dataset revision:** `2026-07-19.v3`
- **Declared records:** 529
- **File size:** 1.1 MB
- **Content:** Published masonry calculator capacity and verification rows
- **Provenance:** declared per record inside the seed

### 7.7 `roof_material_db`

Roofing material assemblies. 2 seeds, 4 schema migrations.

#### `roof_material_assemblies_current_official_public_2026_04_01.json`

- **Dataset revision:** `1.0`
- **Declared records:** 2
- **File size:** 3 KB
- **Provenance:** declared per record inside the seed

#### `roofing_products_icc_approved_current_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12`
- **Declared records:** 39
- **File size:** 178 KB
- **Provenance:** declared per record inside the seed

### 7.8 `aluminum_db`

Extruded aluminum mechanical properties. 1 seed, 2 schema migrations.

#### `aluminum_extruded_mechanical_properties_current_official_public_2026_07_12.json`

- **Dataset revision:** `1.0.0`
- **Declared records:** 447
- **File size:** 1019 KB
- **Content:** Aluminum Association 2009 selected extruded-product mechanical property limits
- **Provenance note:** Complete free Tables 11.1 and 12.1, not an abbreviated common-alloy subset. ADM-only compression, shear, modulus, and standard-shape design data remain explicit source-gated nulls.

### 7.9 `concrete_db`

Concrete material catalog. 1 seed, 2 schema migrations.

#### `concrete_reinforcement_and_post_tension_seed_current_official_public_2026_07_12.json`

- **Dataset revision:** `2026-07-12`
- **Declared records:** 83
- **File size:** 304 KB
- **Content:** concrete_reinforcement_and_post_tension_seed_current_official_public
- **Provenance:** declared per record inside the seed

## Appendix A. Schema Migrations

The SQL migrations defining each database schema, applied in order; all pinned in the integrity manifest.

### `member_db` (25)

- `0001_runtime_bootstrap.sql`
- `0002_phase1_sawn_catalog.sql`
- `0003_phase1_sawn_v1_1_extensions.sql`
- `0004_i_joist_catalog.sql`
- `0005_engineered_wood_catalog.sql`
- `0006_panel_split_cleanup.sql`
- `0007_posts_piles_catalog.sql`
- `0008_phase1_sawn_v1_2_wet_service.sql`
- `0009_sawn_section_property_catalog.sql`
- `0010_sawn_reference_design_value_catalog.sql`
- `0011_sawn_rdv_service_condition.sql`
- `0012_sawn_mechanical_grade_catalog.sql`
- `0013_sawn_mechanical_grade_species_property.sql`
- `0014_sawn_decking_catalog.sql`
- `0015_glulam_reference_design_value_catalog.sql`
- `0016_glulam_axial_reference_design_value_catalog.sql`
- `0017_glulam_hardwood_axial_reference_design_value_catalog.sql`
- `0018_glulam_bending_combination_reference_design_value_catalog.sql`
- `0019_scl_reference_design_value_catalog.sql`
- `0020_clt_reference_design_value_catalog.sql`
- `0021_i_joist_performance_grade_catalog.sql`
- `0022_mass_plywood_esr4760_catalog.sql`
- `0023_glulam_axial_design_adjustment_rules.sql`
- `0024_i_joist_property_source_provenance.sql`
- `0025_i_joist_depth_qualification_aliases.sql`

### `ceiling_wall_db` (41)

- `0001_runtime_bootstrap.sql`
- `0002_ceiling_wall_catalog.sql`
- `0003_usg_interior_finishing_catalog.sql`
- `0004_lap_siding_installed_coverage.sql`
- `0005_clarkdietrich_lath_accessory_catalog.sql`
- `0006_ceiling_wall_source_audit_metadata.sql`
- `0007_usg_acoustical_panel_packaging_catalog.sql`
- `0008_usg_suspension_accessory_packaging_catalog.sql`
- `0009_usg_acoustical_panel_performance_catalog.sql`
- `0010_usg_acoustical_panel_selection_fields.sql`
- `0011_usg_renditions_specialty_panel_catalog.sql`
- `0012_usg_renditions_option_collection_scope.sql`
- `0013_armstrong_soundscapes_wall_panel_catalog.sql`
- `0014_armstrong_soundscapes_source_conflicts.sql`
- `0015_armstrong_tectum_direct_attach_wall_catalog.sql`
- `0016_armstrong_tectum_finale_pb_wall_catalog.sql`
- `0017_armstrong_tectum_designart_lines_wall_catalog.sql`
- `0018_armstrong_tectum_designart_shapes_wall_catalog.sql`
- `0019_armstrong_tectum_create_wall_catalog.sql`
- `0020_armstrong_woodworks_grille_forte_wall_catalog.sql`
- `0021_armstrong_feltworks_acoustical_wall_catalog.sql`
- `0022_armstrong_axiom_vector_catalog.sql`
- `0023_armstrong_axiom_classic_catalog.sql`
- `0024_armstrong_axiom_building_perimeter_catalog.sql`
- `0025_armstrong_axiom_paired_catalog.sql`
- `0026_armstrong_axiom_transitions_catalog.sql`
- `0027_armstrong_axiom_knife_edge_catalog.sql`
- `0028_armstrong_axiom_interlude_catalog.sql`
- `0029_armstrong_axiom_moldings_column_rings_catalog.sql`
- `0030_armstrong_axiom_lutron_shade_pocket_catalog.sql`
- `0031_armstrong_axiom_design_trough_catalog.sql`
- `0032_armstrong_axiom_direct_light_cove_catalog.sql`
- `0033_armstrong_axiom_direct_light_cove_specialty_catalog.sql`
- `0034_armstrong_axiom_indirect_light_cove_catalog.sql`
- `0035_armstrong_axiom_indirect_field_light_cove_catalog.sql`
- `0036_armstrong_axiom_indirect_light_ledge_catalog.sql`
- `0037_armstrong_axiom_glazing_channel_catalog.sql`
- `0038_armstrong_axiom_indirect_field_light_cove_specialty_catalog.sql`
- `0039_armstrong_axiom_drywall_trim_catalog.sql`
- `0040_armstrong_accessory_master_catalog.sql`
- `0041_armstrong_suspension_master_catalog.sql`

### `steel_db` (12)

- `0001_runtime_bootstrap.sql`
- `0002_steel_shape_catalog.sql`
- `0003_steel_material_grade_catalog.sql`
- `0004_cold_formed_steel_section_catalog.sql`
- `0005_cold_formed_steel_truss_section_catalog.sql`
- `0006_cold_formed_fastener_capacity_catalog.sql`
- `0007_cold_formed_channel_ceiling_span_catalog.sql`
- `0008_cold_formed_wall_height_catalog.sql`
- `0009_cold_formed_combined_axial_lateral_catalog.sql`
- `0010_cold_formed_joist_uniform_load_catalog.sql`
- `0011_cold_formed_header_uniform_load_catalog.sql`
- `0012_cold_formed_web_crippling_capacity_catalog.sql`

### `connector_db` (28)

- `0001_runtime_bootstrap.sql`
- `0002_connector_catalog.sql`
- `0003_connector_allowable_installation.sql`
- `0004_connector_allowable_capacity_condition.sql`
- `0005_connector_fastener_catalog.sql`
- `0006_connector_allowable_load_condition.sql`
- `0007_connector_hold_down_design_catalog.sql`
- `0008_connector_wood_capacity_and_material_spec.sql`
- `0009_connector_wood_capacity_f2_and_brick_tie.sql`
- `0010_connector_wood_capacity_esr3448_directions.sql`
- `0011_connector_wood_capacity_esr3455_directions.sql`
- `0012_connector_prescriptive_bridging_and_bracing.sql`
- `0013_truss_plate_connector_catalog.sql`
- `0014_shear_wall_system_catalog.sql`
- `0015_metal_web_truss_catalog.sql`
- `0016_system_fastener_application_catalog.sql`
- `0017_fastener_catalog_packaging_and_exact_geometry.sql`
- `0018_fastener_report_design_axes.sql`
- `0019_generic_fastener_catalog.sql`
- `0020_fastener_catalog_accessories.sql`
- `0021_evaluated_fastener_source_fidelity.sql`
- `0022_connector_lookup_enrichment.sql`
- `0023_evaluated_fastener_head_height.sql`
- `0024_fastener_approximate_package_count.sql`
- `0025_fastener_steel_capacity.sql`
- `0026_fastener_package_hierarchy.sql`
- `0027_fastener_assembly_capacities.sql`
- `0028_fastener_evaluated_profiles.sql`

### `panel_db` (4)

- `0001_runtime_bootstrap.sql`
- `0002_panel_catalog.sql`
- `0003_panel_manufacturer_extensions.sql`
- `0004_panel_engineering_catalog.sql`

### `masonry_db` (5)

- `0001_runtime_bootstrap.sql`
- `0002_masonry_catalog.sql`
- `0003_masonry_fm_unit_strength_catalog.sql`
- `0004_cmu_section_property_catalog.sql`
- `0005_published_capacity_catalog.sql`

### `roof_material_db` (4)

- `001_initial_schema.sql`
- `002_roof_product_catalog.sql`
- `003_esr3267_product_variant_catalog.sql`
- `004_seed_registry_normalization.sql`

### `aluminum_db` (2)

- `0001_runtime_bootstrap.sql`
- `0002_extruded_mechanical_property_catalog.sql`

### `concrete_db` (2)

- `0001_runtime_bootstrap.sql`
- `0002_material_catalog.sql`

## Appendix B. Builder Scripts

Byte-idempotent builder scripts (where present) that produced seeds from their pinned sources.

### `ceiling_wall_db` (34)

- `build_armstrong_accessory_master_seed.py`
- `build_armstrong_axiom_building_perimeter_seed.py`
- `build_armstrong_axiom_classic_seed.py`
- `build_armstrong_axiom_design_trough_seed.py`
- `build_armstrong_axiom_direct_light_cove_seed.py`
- `build_armstrong_axiom_direct_light_cove_specialty_seed.py`
- `build_armstrong_axiom_drywall_trim_seed.py`
- `build_armstrong_axiom_glazing_channel_seed.py`
- `build_armstrong_axiom_indirect_field_light_cove_seed.py`
- `build_armstrong_axiom_indirect_field_light_cove_specialty_seed.py`
- `build_armstrong_axiom_indirect_light_cove_seed.py`
- `build_armstrong_axiom_indirect_light_ledge_seed.py`
- `build_armstrong_axiom_interlude_seed.py`
- `build_armstrong_axiom_knife_edge_seed.py`
- `build_armstrong_axiom_lutron_shade_pockets_seed.py`
- `build_armstrong_axiom_moldings_column_rings_seed.py`
- `build_armstrong_axiom_paired_seed.py`
- `build_armstrong_axiom_transitions_seed.py`
- `build_armstrong_axiom_vector_seed.py`
- `build_armstrong_feltworks_acoustical_wall_seed.py`
- `build_armstrong_soundscapes_wall_seed.py`
- `build_armstrong_suspension_master_seed.py`
- `build_armstrong_tectum_create_wall_seed.py`
- `build_armstrong_tectum_designart_lines_wall_seed.py`
- `build_armstrong_tectum_designart_shapes_wall_seed.py`
- `build_armstrong_tectum_direct_attach_wall_seed.py`
- `build_armstrong_tectum_finale_pb_wall_seed.py`
- `build_armstrong_woodworks_grille_forte_wall_seed.py`
- `build_clarkdietrich_lath_accessory_seed.py`
- `build_usg_acoustical_panel_packaging_seed.py`
- `build_usg_acoustical_panel_performance_seed.py`
- `build_usg_renditions_specialty_panel_seed.py`
- `build_usg_suspension_catalog_seed.py`
- `update_generic_official_sources.py`

