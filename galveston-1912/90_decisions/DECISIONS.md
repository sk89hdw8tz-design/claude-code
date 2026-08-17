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

## D-010 — Transform freeze (2026-08-17)

Geometry frozen per FREEZE_MANIFEST.json (SHA-256 over sources, controls, transforms,
cuts, masks, scripts). Acceptance rationale: rotation determinability is source-limited
at 1.3-3.1 mrad (plate drafting scatter, not observation design); composited previews
show no frontage doubling; the Ave I kink is 1.1-1.6 px on the long-baseline lines.
Presentation changes (crop, composition, ownership patches) may proceed; geometry refits
require QA proof the geometry is wrong. The 21st St cut carries one owner-verified manual
deviation giving the sheet-7 scale-bar area to sheet 9's authentic blank street (the
brief-preferred furniture removal by source ownership; nothing altered in any scan).
Rosenberg x Ave C composites as a preserved plate disagreement (54-ft drafted frontage
separation), documented rather than reconciled.

## D-011 — Sheet-5 panel misfit found by the owner; joint re-fit (2026-08-17)

**Owner report:** the two wharf panels do not align at the railroad tracks or at the
building by Pier 22; the join should read as one continuous frontage.

**Diagnosis (controller).** Confirmed and root-caused. `fit_sheet5.py` solves each panel
INDEPENDENTLY against the frozen block; nothing couples panel A to panel B. Each panel's
rotation was therefore set only by its own land-side attachments -- few, noisy (s0^2 ~
6.5), short lever arm. Result: theta_A = -1.243 deg, theta_B = +0.087 deg, a **1.33 deg
relative rotation between two panels drafted on one page by one hand at one scale**.
Propagated along the frontage that is ~350 px (~57 ft) of divergence.

**This supersedes an earlier finding of mine.** The ~55 ft discrepancy in the duplicated
Pier 22 ground was recorded (D-008, and in the accepted report) as *preserved original
drafting disagreement*. It is not: it is my fit error. Two panels of one continuous
frontage on one sheet must agree to drafting precision, and the sheet proves it by
drawing the Pier 22 / 22nd St ground twice. The earlier compositor decision to route the
A|B cut through open water "so the pier disagreement never appears as a mid-pier jog" was
therefore treating a symptom.

**Fix.** `fit_sheet5_joint.py`: joint 8-parameter solve of both panels, coupling them
with direct observations of the duplicated drafted ground (shed corners, track frogs,
slip/bulkhead corners) as T_A(pA) - T_B(pB) = 0 rows, alongside the existing block
attachments. The correspondences fix the panels RELATIVE to each other; the attachments
fix the pair against the land. Robust IRLS, full 8x8 covariance, and the relative
rotation reported as a first-class quantity -- the thing the independent fit could not
constrain at all.

## D-012 — Joint panel fit adopted; shared-orientation model (2026-08-17)

Seven cross-panel correspondences measured on the duplicated ground (shed and pier-deck
corners, pipe/street intersection, two building corners; sigma 3-6 px, 14 evidence crops,
one bad pairing caught and re-measured). Two models fitted and compared:

| model | relative rotation | duplicated-ground disagreement | block RMS |
|---|---|---|---|
| independent (superseded) | +1.330 deg | 283 px (49 ft) | -- |
| joint, free rotation | +0.373 +- 0.27 deg | 22.7 px (3.9 ft) | 60.8 px |
| **joint, shared orientation (ADOPTED)** | 0 by construction | 32.5 px (5.6 ft) | 59.2 px |

**Shared orientation adopted.** The free model's +0.373 deg is 1.4 sigma from zero -- not
demonstrated. The correspondence set is strongly elongated (1610 px across the frontage,
only 245 px along it), so relative rotation and scale are ill-conditioned from these
points alone: the measurer's own subset fits swung scale 0.98-1.02 and rotation -0.55 to
+1.0 deg. Per the brief's least-complex-model rule, the extra DOF is not adopted merely
because it lowers residuals. The physical argument is independent and strong: both panels
are on one page, at one drafted scale ("Scale 100 Ft. to One Inch"), laid out as parallel
bands with streets horizontal. Shared orientation also fits the land attachments slightly
BETTER (59.2 vs 60.8 px).

Residual ~5.6 ft disagreement is smaller than the ~10-11 ft the two hand drafts disagree
by on slip/yard width -- i.e. now within the source's own inconsistency. THAT remains a
genuine preserved drafting disagreement; the 49 ft was not.

Verified: anaglyph of both panels warped into the mosaic shows shed outlines coincident
and shared track lines printing neutral (agreement); remaining single-colour tracks are
genuine draft differences (the panels draw different yard track counts). Native-resolution
inspection at the cut shows continuous tracks and the Pier 22 shed rendered once, whole.

## D-013 — A|B cut routed as a polyline to preserve the slip bulkhead (2026-08-17)

**Owner report:** the slip between Piers 22 and 23 still did not align.

**Diagnosis.** Confirmed at native resolution: the straight A|B cut crossed the slip's
long east bulkhead obliquely, so the two drafts' residual ~30 px disagreement (genuine,
D-012) showed as a ~40 px step in that single continuous line. Coverage analysis at the
bulkhead column: panel A spans canvas y 0-8300, panel B spans 6620-14480, while the
bulkhead runs ~6460-8600 -- neither panel alone covers all of it, so no straight cut can
avoid splitting it.

**Fix.** The A|B boundary is now a POLYLINE that rises to meet panel B's own top edge at
the slip's chamfer corner (~canvas 8140, 6610): B draws the ENTIRE bulkhead, and the
transition happens in open slip water where nothing is drafted. West of the slip the cut
stays south of the Gulf Fishery shed so panel A keeps it whole. Verified at 1:1: the
bulkhead is now one unbroken line; piers 20-25, sheds and tracks read continuously.

**Known remaining, not fixed:** both panels label the slip, and the two labels sit ~900 px
apart within the same water body, so one "Slip" appears twice. Suppressing the second
would require extending panel A's ownership to ~canvas 8280, within 45 px of A's page
edge -- risking exactly the blank-margin intrusion that F1/1889 warn about. Left as
documented furniture duplication, the same class already adjudicated at the block seams.
Paper-tone steps at the panel boundary are authentic and preserved (no exposure matching).

## D-014 — Pier 22 rail fan: local source-ownership repair (2026-08-17)

**Owner report:** at the red-circled Pier 22 splice the railroad tracks jump, terminate,
change vertical position, or fail to meet their corresponding continuation.

**First finding: the disagreeing pair is not the one reported.** The report attributed the
defect to the two sheet-5 panels. An empirical ownership map (every master pixel matched
against every candidate source; 0.00% unmatched) shows the boundary through the circled
convergence is **sheet 5 panel B vs SHEET 9**, not A|B. Provenance from `50_seams/masks.json`:
region `s09_r0` covers 96.6% of the window. Panel A owns only a wedge 7.8% of it, ending at
canvas y 8184, north of the circle. Both plates draw this ground: sheet 9 is a 50 ft/in block
plate, sheet 5 the 100 ft/in wharf plate upscaled ~2x.

**Case determination — Case C (seam through a locally disagreeing duplicate), not A or B.**
Not Case A: flat-fielded ink correlation over the shared fan puts the two plates' relative
offset at **-2 px in x** (well determined by the near-vertical tracks; y is a 44-49 px plateau,
undetermined, as expected from vertical line work). The plates are registered. Not Case B:
both draw the same fan in the same place. What differs is *content* — sheet 9 alone carries
track numbers 5-24, "T.H." and its tank house, block number 742, the 6" water main and the
80' dimensions — and the seam ran straight through it.

**Root cause, quantified.** The panel/block content frontier ran a mean **151 px east** (max
324 px) of where sheet 9's drawn content actually begins. This is an artefact of the frontier's
own spike filter: `maximum_filter1d(size=281)` takes the easternmost frontier within +-140
rows, and the fan's west envelope moves west as y increases, so the filter walks the boundary
off sheet 9's cartography. Panel B then supplied blank wharf apron over ground where sheet 9
draws the yard. Same family as the Mallory shed defect (F1/F2) and the 1889 lesson, but with
the roles reversed: there blank *block* margin erased sole-source *wharf* content; here blank
*wharf* apron erased *block* content. The frontier heuristic is one-sided by construction.

**Both ownership directions were built and read at native resolution.**
*Candidate P — panel B owns the convergence:* rejected. It deletes every track number (5-24),
block number 742, the 6" water main and both 80' dimensions, floods the area with panel B's
markedly dimmer paper, duplicates the ICE RUN / ICE RUNWAY label, and opens a **new** hard
break at its east edge where panel B's coarser fan fails to meet sheet 9's. It repairs the
visible break by deleting different genuine cartography — the brief's explicit reject test.
*Candidate S — sheet 9 owns the convergence:* adopted.

**Fix.** Inside ONE bounded canvas rectangle (rows 6400..9000) the frontier is replaced by a
stated polyline running ~20 px east of sheet 9's own slip bulkhead (measured east edge
`8126 + 0.0525*(y-6600)`) and west of sheet 9's westernmost yard ink — i.e. through the wharf
apron that BOTH plates leave blank. Its first and last breakpoints equal the frozen frontier
at those rows, so the boundaries meet with no step (change tapers 55 -> 30 -> 6 -> 0 px across
y 8900..9000). Ownership only: no pixel painted, cloned, inpainted, blended or interpolated.

**Measured against the frozen boundary.** Crosses sheet-9 ink in 381 rows vs 500; panel-B ink
in 512 vs 615. Suppressed sheet-9 drawn ink falls 14.1% -> 10.9%, restoring 8,526 px of the
plate's own line work. Restored: tracks 5 and 7, the T.H. tank house and track-8 label, the
west end of the 6" water main, and continuity of every track that crossed the old staircase.

**Transforms: none changed.** Both sheet-5 panel transforms and all block transforms are
byte-identical (`verify_pier22_frozen.py`: 36 of 38 frozen artefacts byte-identical; the two
that changed are the compositor carrying this override and its output).

**Regression.** The frontier can only affect rows 6400..9000 and the panels can only write
within canvas x 2661..10571, so a before/after diff over x2600-10600 x y6200-9200 is a proof
rather than a sample: **517,949 px changed, bbox x8130..8471 y6402..8998, 100% inside the
authorised band, 0.1364% of the canvas.** Piers 20-21, Pier 22 and its shed, Piers 23-28, the
bay shoreline, both slips and their labels, and the Ave. A / Water St frontage all lie outside
that rectangle and are bit-identical.

**QA-tool bug found and fixed during this work.** The first frozen-input verifier reported
"0 hashed artefacts checked ... OK" — a false pass, because the checkpoint stores
component->sha256 with no paths and the parser silently matched nothing. Rewritten to resolve
paths by hashing the tree and looking the frozen hashes up in that index, so a component that
cannot be located fails loudly. Fourth instance in this project of a checker emitting
confident, well-formed, meaningless output (cf. F-001, F-003, F-005).

**Known remaining, not fixed:** panel B's paper is materially dimmer than sheet 9's (the
sheet-5 scan falls off toward its right side; bright page detected only to x=4447 of 6653), so
the ownership boundary is visible as a tone step in the blank apron. Authentic and preserved —
no exposure matching, per the brief. The duplicated "Slip" label (D-013) is likewise unchanged.
