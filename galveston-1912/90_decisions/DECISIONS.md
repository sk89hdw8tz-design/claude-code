# Galveston 1912 Sanborn Mosaic — Decision Log

Chronological record of project decisions, their rationale, and evidence.

## D-001 — Source acquisition route (2026-08-16)

**Problem.** Both Claude Code environments ("Test", "Default") enforce a strict egress
allowlist (package registries + GitHub only). All archival hosts — maps.lib.utexas.edu,
www.loc.gov, tile.loc.gov, web.archive.org — are denied at the gateway (verified by direct
probes in this session and by a dedicated probe session on the Default environment; see
`galveston_1912_sources/STATUS.md` on branch `claude/galveston-1912-source-data`).

**Decision.** With the user's explicit approval, acquisition runs in GitHub Actions on the
user's fork (runners have ordinary internet egress): workflow
`.github/workflows/fetch-1912-sources.yml` on branch `claude/galveston-1912-source-data`
downloads the complete Galveston 1912 set (key, index, all sheets) from the UT Austin PCL
index page `https://maps.lib.utexas.edu/maps/sanborn/g.html`, verifies JPEG magic bytes,
records SHA-256 + exact source URL per file in `inventory.json`, and commits the unmodified
files back to the same data branch, which the session then pulls (GitHub is allowlisted).

**Alternatives considered.**
- Environment network-policy change to allow loc.gov: cleaner, and LOC serves higher
  resolution (volume `sanborn08539`, 77 sheets), but requires user settings change + fresh
  session. Kept as an upgrade path.
- Direct upload by user: declined by user.
- No other GitHub-reachable mirror of the rasters exists (searched).

**Precedent.** The accepted 1889 and 1899 mosaics (branches
`claude/galveston-1889-sanborn-mosaic-1h5aoc`, `claude/galveston-1899-sanborn-maps-g5pfqc`)
were built from the same UT PCL web JPGs (~3400×4100 px, 300 dpi, ~2.6 MB) — demonstrating
that this source meets the accepted print standard (the 1899 benchmark print is 11817×7965 px
@ 300 dpi from 13 such sheets).

## D-004 — utlibraries/histmap-autogeoref-tools evaluated, not adopted (2026-08-17)

Proposed by the project owner. Repository inspected directly (public clone).

**What it actually does.** Georeferences Sanborn sheets *individually* onto modern
coordinates: a TF2 object-detection model finds street intersections and their street
labels on the scan, those are matched to OpenStreetMap intersection coordinates for the
city, `gdal.GCP` pairs are built, and `gdal.Translate`/`gdal.Warp` emit a georeferenced
GeoTIFF/COG in EPSG:3857 when at least 3 GCPs match. Dependencies: `tensorflow`,
`object_detection`, `osmnx`, `osgeo/gdal`, `pytesseract`, `geopandas`, `rasterio`.

**Why it is not adopted for the current stage.**

1. *It is the problem we deliberately deferred.* The brief separates historical sheet
   reconstruction from modern georeferencing and says not to force the plates onto a
   modern basemap prematurely. This tool is precisely that forcing.
2. *It solves no part of our actual problem.* It has no notion of sheet-to-sheet relative
   geometry, adjacency, seams, source ownership, or mosaicking. Our task is the relative
   placement of twelve plates and the seam network between them.
3. *OSM as control would import modern geometry into a 1912 reconstruction.* Galveston's
   waterfront and street frontage changed profoundly after 1912 — the grade raising, the
   seawall's extensions, and repeated rebuilding of the wharf front. Fitting 1912 drafting
   to present-day intersection coordinates would distort historical geometry toward modern
   truth, which is exactly what the brief forbids and what "preserve historical
   disagreement" exists to prevent.
4. *Its fitting standard is weaker than ours.* Three GCPs is the bare minimum and admits
   weakly-determined solutions; the script reports GCP counts but no covariance or
   determinability diagnostics, so a poorly constrained sheet with low residuals would
   pass. `gdal.Warp` on GCPs also tends toward polynomial/TPS fitting — precisely the
   higher-order distortion the brief says not to escalate to without independent evidence.

**Blocked in practice regardless.** The trained detection model is not in the repository;
it lives behind a Texas Data Repository DOI. OSMnx needs live OpenStreetMap queries. This
session's egress permits only PyPI and GitHub, so both of the things that make the tool
work are unreachable here.

**What is worth borrowing.** Its core idea is well matched to our control problem: detect
street intersections *together with their street labels*. That pairing is exactly the
disambiguating semantic anchor our control schema requires, and it is the property that
defeats one-block-off matching. We can pursue the same idea without their model or OSM —
`pytesseract` (installable from PyPI) can read street labels off the plates to attach
anchors to candidate controls, which are then **verified manually** and used only in the
historical plane. Controls proposed, never auto-solved.

Its quality-assessment script's habit of classifying outcomes into georeferenced-well /
georeferenced-with-unacceptable-distortion / failed is also a sane precedent for our own
diagnostics.

**Revisit when.** After the historical master is built and its transforms frozen, if
modern geographic registration is wanted as the separate final phase the brief allows. At
that point OSM matching would be applied to the finished master as a registration step —
never as control for the historical geometry itself.

## D-006 — Fable review reconciled: sheet 5 multi-region adopted (2026-08-17)

The independent Fable review (two subagents + coordinator verification; package under
`fable_review/`) is reconciled into the canonical record with owner authorization.

**Sheet 5:** CONFIRMED MULTI-REGION adopted — two east/west panels of one continuous
wharf frontage split by a drafted rule; Pier 22 drawn on both panels (controller-verified
against the scan); two transforms required; sheet 9 adjoins both panels. The earlier
stacked-strips hypothesis is superseded and retained for the record in
`WHARF_PLACEHOLDER.md`. Deferral and re-entry criteria stand, amended for two regions.

**Accepted with it:** the 17-seam triage (HIGH = the three column-4 attachments), the 12
independent controls as a reconciliation reference set, the alley-trap warning on 7-9,
and the Broadway drafted-vs-annotated width finding.

## D-007 — Protocol amendments and solve requirements adopted (2026-08-17)

The ten protocol amendments from `fable_review/FABLE_PROTOCOL_AUDIT.md` are binding
before any verified control is recorded (see the amendment block in
`VERIFICATION_PROTOCOL.md`): stated axis convention; required why-not-one-block-off and
remeasurement fields; per-reading sigmas (no defaults); defined sigma_across construction
with a ±12 px floor from measured (not annotated) street widths; retained rejects;
source-checksum binding; segment-endpoint reads; explicit junction statement.

Determinability requirements adopted as `40_solve/SOLVE_REQUIREMENTS.md`: covariance
flags on (θ, s) with expected first-solve flags on sheets 40, 50, 7; through-street
collinearity diagnostics across Sealy; junction closure QA order; the prohibition on
blanket-averaging independent measurement sets.

## D-002 — Print target (2026-08-16)

The supplied 1899 benchmark PDF measures: single page, 39.39×26.55 in, one embedded baseline
JPEG 11817×7965 px, 8-bit DeviceRGB, exactly 300.0 DPI. The 1912 master targets the same
standard: ~300 DPI large-format, extent determined by the solved 1912 geography (not copied
from 1899).

## D-003 — Prior-edition independence (2026-08-16)

Prior-project branches contain 1889/1899 controls, seams, and tooling. Per the brief and the
user's "build fresh" instruction: 1912 sheet identity, topology, controls, and geometry are
solved independently from the 1912 Key and plates. Prior branches are used only as (a) process
precedent and (b) presentation benchmark. No geometric data is transferred between editions.

## D-008 — Sheet-5 attachment measurements adopted; canon updates (2026-08-17)

ctrl-S5's attachment set accepted (9 ACCEPTED anchors, 2 CONTEXT_ONLY, 6 cross-panel
point pairs, 42 evidence crops). Canon updates it established:

1. **Sheet 13 is outside the target footprint** (mapped ground starts at 27th St, two
   blocks west of the Rosenberg limit). It remains context-only; the 5-13 topology
   check is closed. RESOLVED: the last REQUIRES SOURCE RECHECK item.
2. **The 5-7 attachment has genuine two-sided overlap** — sheet 7 duplicates the
   bay-side strip (Texas Star Flour Mills area). This is the second known exception to
   "no duplicated ground" (after sheet 5's own cross-panel Pier 22), and applies to a
   wharf attachment, not to any of the 17 ordinary block seams. Source-ownership for
   that strip will be decided at mask time (block plate is 2x finer scale).
3. **Scale structure:** block plates are drafted at 50 ft/in, sheet 5 at 100 ft/in —
   per-sheet free scale in the solver is mandatory, as designed.
4. **Cross-panel consistency:** 22nd-St street-corner pairs agree to 5-10 px; the
   duplicated pier ground itself disagrees ~55 ft between panels (drawn at different
   angle/offset relative to 22nd St). The street corners are the primary cross-panel
   constraint; the pier disagreement is preserved as original drafting disagreement.
5. **Orientation:** all plates in these attachments (5, 7, 9, 11, 13) are drafted
   bay-page-left (rotated from north-up); along-frontage is page-y everywhere here.

## D-009 — First diagnostic solve; determinability response (2026-08-17)

First full-network solve (34 anchors, 99 observations): along-seam RMS 6.7 px, kappa
6.01 px/ft, collinearity clean on most streets — but rotation std 4-7 mrad on all free
sheets against the 1.5 mrad standard, and LOSO shows sheet 11 swinging ~2,600 px without
seam 11-12. Robust variance factor s0^2 ≈ 3.6-4.3: drafting scatter dominates reading
noise, as the reconciliation record predicted. The Huber downweights cluster exactly on
documented plate disagreements (9-10 gallery depth, Rosenberg corners) — absorbing real
drafting scatter, not measurement error. The 20th-St collinearity outlier is the City
Storage esplanade (real geometry, not error).

Adopted responses (both pre-planned in FABLE_DETERMINABILITY_NOTES recommendations):
1. Rotation priors from the measured drafted-grid deviations (< 1.26 mrad on every
   plate): b_i ~ 0 ± 2 mrad, CLI-controlled, off for synthetic tests.
2. Long-baseline boundary anchors (18th/27th St) appended to the six row-1/row-3
   vertical seams — protocol amendment: boundary crossings are admitted as long-baseline
   rotation controls where legible (larger honest sigma), superseding the interior-only
   coverage rule.
3. Straight-street collinearity promoted from diagnostic to constraint (per-face lines,
   free direction parameters, only straightness assumed — the streets are platted
   straight and each plate drafts them straight individually).
