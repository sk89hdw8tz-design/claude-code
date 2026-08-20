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

## D-015 — Flat water treatment for the print deliverable (2026-08-18)

**Owner request:** make Galveston Bay the same colour as the 1899 companion print, and fix a
large white rectangle in the bay.

**Measured first, because the obvious reading was wrong twice.**

*The 1899 bay is a flat colour fill, not scanned tint.* 84.7% of its bay region carries exactly
`RGB(199,214,209)`; p5 = p95 = median on every patch sampled. (That sheet's own caption claims
"no fill, no generated content anywhere". Inaccurate for its water — noted so this project's
caption does not inherit the claim.)

*The 1912 plates do tint the bay.* Sheet 5's water reads 30-43 levels cooler than the same
sheet's bare paper (`B-(R+G)/2`: bay -9 to -23, bare paper -52). It composites to warm grey
`(180,175,165)` because the paper is strongly yellowed and the LOC scan dim — the tint is real
but swamped. The 1912 page is globally ~55 levels darker than the 1899 (paper 177,166,132 vs
233,213,165).

*Colour cannot select water.* Bay measures -12.5 on `B-(R+G)/2`; a blank downtown street
measures -11.5. A colour key would recolour streets. A geometric mask is required.

*The white rectangle is uncovered canvas, not a plate defect:* canvas x 3324-4956, y 8148-14489.
Sheet 5 panel A ends at y 8148 and panel B does not reach as far west, so no sheet in the set
draws it. Filling it is generated content, disclosed in the caption and here. Because the fill
is flat, it and the scanned bay land on the identical value and the rectangle vanishes into the
bay with no seam — the two reported defects resolve together.

**Method.** A presentation stage between master and PDF (`60_master/tools/water_treatment.py`),
applied in memory. Shape comes from an ink-constrained flood fill seeded inside `seed_*` and
capped by `bound` (`50_seams/water_regions.geojson`), so the fill snaps to the drafted shoreline
and reaches every slip open to the bay — "all water" hydrographically — without hand-tracing a
pier face. Ink is alpha-composited rather than thresholded, so lettering, compass roses, the
scale bar, soundings, pier outlines and bulkheads keep full darkness with clean edges; a hard
threshold would leave a warm halo round every mark on flat blue. 360,704 ink px inside the mask
are preserved this way.

**Two detector faults found and fixed during the work, both mine, both silent:**

1. *Flat-fielding fooled by uncovered canvas.* The 121 px background blur read the exact-255
   uncovered region as very bright paper, so genuine bay tint within ~60 px of it scored
   rel ~0.75 and was classified as ink. That left a hairline of unfilled water tracing the panel
   coverage edges, which I first read as a page edge in the scan — the pixel values proved it was
   ordinary water tone. Fixed by neutralising uncovered canvas to the median tone of covered
   water before estimating ink; it cannot affect output, since those pixels are filled regardless.
   Removed a 399,870 px residue and dropped the water from 125 fragments to 28.
2. *An idempotence check that was the wrong test.* Compositing ink with a partial coverage alpha
   is by construction not self-idempotent — re-running on the OUTPUT blends the same ink toward
   the fill a second time. Replaced with determinism (same input twice → byte-identical output,
   verified 0 px), which is what reproducibility actually requires.

**Verification** (`60_master/tools/water_qa.py`, all assertions): determinism 0 px; frozen-artefact
verifier still passes with only D-014's compositor and its output changed; zero water outside
`bound` and zero east of canvas x=9000, recoloured bbox stops at x 8123; ink preserved
360,704 → 360,354; open-water median exactly `(199,214,209)`; zero pure-255 left anywhere in the
printed bay; PDF 1 page, 40.00 x 25.84 in, one baseline JPEG at exactly 300.0 DPI both axes.
Native crops rendered back out of the finished PDF confirm the D-014 Pier 22 repair intact.

Recoloured 60,008,046 px — 40,024,006 from scanned tint, 19,984,040 from uncovered canvas.

**Applied to the print only.** `master_full.tif` is unchanged (sha256 `a22da6ad…` identical
across the build) and remains the as-scanned historical composite; the archival scans are never
opened for writing. Page geometry is deliberately measured from the untreated master, so the
printed extent is identical to the previous build.

**Known remaining, not fixed:** 143 pure-255 px survive elsewhere in the printed rect as six 1 px
slivers where abutting block sheets fail to meet. They are present in `candidate_master.tif`, so
they pre-date the wharf composite and this stage, and are unrelated to water. Sub-pixel after the
0.516x downsample. Recorded rather than silently tolerated.

## D-016 — Tone and colour match of the print to the 1899 sheet (2026-08-18)

**Owner request:** make the remaining 1912 colours match the 1899 companion; do not touch the
1899; orange structures unchanged except brightening; no loss of type legibility.

**Diagnosis: both brightness and saturation, not hue.** Matched-feature measurement (same
blocks, Central Park on both sheets): 1912 paper (183,179,168) vs 1899 (238,228,202) — 1.24x
dimmer; fills ~2x less saturated at the same hues; black ink already matched (27,21,17 vs
36,27,12). Because the black point matches, brightening lifts paper while ink barely moves, so
type contrast RISES — the opposite of the feared risk.

**Orange, corrected mid-work.** An early hue-bucket measure suggested both sheets had orange.
Connected components >= 2000 px show the 1899 has TWO pale-tan blobs (0.080% of page, one
building) vs NINETEEN genuinely orange on the 1912 (0.448%): the earlier "1899 orange" was
scattered blend pixels between yellow and pink fills. There is NO 1899 orange to match, so
orange takes the brightness lift and holds its own saturation.

**Transform** (`60_master/tools/tone_match.py`, constants + provenance in
`50_seams/tone_anchors.json`), applied in memory before the water fill:
1. Per-channel affine levels, fitted PRINT-TO-PRINT (ink->ink, paper->paper). Master-to-print
   fitting was measured and rejected: the master's pre-JPEG blacks (9.8,6.8,6.6) are deeper than
   any print black, and fitting across that mismatch would lift blacks and wash out type.
   Per-channel, not 3x3, per the least-complex-model rule (3x3 improved anchor RMS only
   12.9 -> 9.6 while allowing hue-shifting channel mixing).
2. Soft highlight shoulder, knee 210: a hard stretch to the 1899 paper level clips 15.3% of map
   content to 255; with the shoulder, 0.000%.
3. Chroma x1.30 about Rec.601 luma (fitted optimum; sweep 1.00->err 9.0, 1.30->6.6, 1.75->10.3),
   with the orange band (H 18-42 deg, S>0.30, feathered) holding saturation per pixel — the
   levels step alone saturates warm colours (+12% measured with a naive gain-1.0 carve-out,
   because the red gain 1.327 exceeds the blue 1.244), so inside the band chroma is rescaled to
   keep S ~ c/Y constant.
4. THEN the D-015 water fill — order matters, or the bay is dragged off (199,214,209) to
   (255,255,249). The water mask is built on the ORIGINAL master (its uncovered-canvas logic
   keys on exact-255, which the shoulder maps to ~251) and the fill applied to the toned image;
   water stats reproduced byte-for-byte (60,008,046 px, same bbox).

**One QA-tool bug found during the work:** the content window kept 0.5% of page width at the
right edge, but the page's white margin is 0.78% wide, so ~16 columns of blank MARGIN were
counted as clipped map content (0.268% "clipping" that did not exist). Crop corrected to 0.985.

**Verification** (`tone_qa.py`, all assertions; `water_qa.py` still passes): type contrast UP in
all six lettering regions spread across the sheet (+1.4% to +24.8%); land ink p1 50.5 (dark);
0.000% of map content at 255; paper within 6 levels of the 1899; yellow saturation ratio 1.02,
pink 1.01 vs the 1899; orange S 0.431->0.427 (held) with V 159->188 (brightened); hue shifts
0.0 deg; open water still exactly (199,214,209); determinism byte-identical; frozen-artefact
verifier passes; PDF 40.00 x 25.84 in at exactly 300.0 DPI.

**Applied to the print only.** `master_full.tif` byte-identical; archival scans never opened for
writing; page geometry measured from the untreated master and unchanged.

**Known remaining, accepted by decision:** sheet-to-sheet paper steps are amplified by the
~1.3x gain and stay visible — plate character preserved, consistent with the project rule and
the 1899's own no-per-sheet-white-balance approach.

## D-017 — Per-plate illumination correction so streets read one tone (2026-08-18)

**Owner report:** not all streets on the 1912 sheet match the one at Ave. G (Winnie) x 22nd St;
make them all that colour.

**Diagnosis: per-plate vignetting, not a per-sheet offset.** Each LOC plate was photographed
with its centre brightest and its edges falling off, so the same street reads bright mid-sheet
and dark near a seam, and dark bands run along every join. Measured on blank paper in master
space: **18.9 levels between plates but 26.0 levels WITHIN a plate** (p10-p90). Intra-sheet
variation exceeds between-sheet variation, so a per-sheet constant gain cannot fix it -- the
correction has to vary inside each plate. A field map with the sheet footprints overlaid shows
the radial falloff directly.

The reference the owner chose sits in region **s43_r0**, whose own median is 12 levels darker
than that intersection -- i.e. the reference is a bright spot on a mid-toned plate, which is
exactly why a per-sheet scheme would have failed.

**Fix** (`60_master/tools/paper_flatfield.py`, spec `50_seams/paper_flatfield.json`): estimate
the blank-paper level as a smooth field INSIDE each source region separately (normalized
convolution, so the field is never smeared across a seam), then scale every pixel by
target/field. Multiplicative, so black maps to black and hue is preserved: ink stays ink and
type legibility cannot fall. Runs on the master ahead of the D-016 tone match.

Target = (192.5, 187.6, 177.6), the Ave. G x 22nd street tone. It equals the page-wide paper
mode to within 1.5 levels, so overall page brightness is preserved and the D-016 anchors stay
valid -- confirmed by QA, which now reports paper within **3** levels of the 1899 (was 6) and
yellow/pink saturation ratios of exactly 1.00 (were 1.02/1.01).

**One estimator fault found and fixed.** The first field used a per-cell MEDIAN of paper
candidates. Where that candidate set is polluted by grey fills or shading the median reads low,
the gain runs high, and those cells over-brighten -- street p95 landed 18 levels ABOVE target
and the spread only fell 34.6 -> 21.7. Switching to the mean of the brightest 30% of each cell's
candidates keys the field to true blank paper. The target had to be re-measured with the same
estimator (191,186,176 median vs 192.5,187.6,177.6 bright-tail); leaving the median target in
place would have under-brightened the whole sheet.

**Result:** wide-open street paper spread **34.6 -> 15.5 levels (55% better)**, sd 10.8 -> 4.8,
median 186.5 against a target of 187.9. Gains ran 0.944-1.308, median 1.044. **Zero genuine map
content clipped** -- all 5.6M clipped pixels were already white or water in the source and are
flat-filled downstream anyway.

**Applied to the print only.** `master_full.tif` byte-identical; archival scans never opened for
writing; page geometry unchanged. Ordering: flat-field -> tone match -> water fill, with the
water mask still measured on the ORIGINAL master (its uncovered-canvas test keys on exact 255,
which the gain would otherwise move).

**Supersedes** the "preserve sheet-to-sheet paper differences" choice recorded under D-016, at
the owner's request.

## D-018 — Duplicated street labels at pooled cuts (2026-08-18)

**Owner report:** a fragment showing "4" and mangled "F. OR CHURCH" lettering.

**Diagnosis.** The pooled per-street cut runs down the CENTRE of the shared street, and BOTH
flanking plates letter that street -- each with its own cross-reference numeral naming the
adjoining sheet. Both label bands straddle the midline, so the composite showed half of each,
180 deg apart, as an illegible tangle. Confirmed by warping each plate separately and measuring
ink-cluster extents at 1:1; e.g. on Ave. F the sheet-10 band is canvas x 19782-19949 and the
sheet-43 band 19860-19933, with the cut at 19893 splitting both.

**Survey.** Five occurrences, found by laying every avenue corridor out end-to-end and reading
them: Ave. F x2 (s10|s43, s08|s39), Ave. C x1 (s07|s08), Ave. I x2 (s39|s40, s43|s44). The
other six avenues are clean.

**Fix.** Five entries in `50_seams/manual_deviations.json` -- the mechanism the project already
built for this. Each moves the cut 76-123 px sideways over the label's along-street range (with
200 px ramps) so BOTH bands fall on one side and a single plate supplies one complete label.
Ownership only: the duplicate is suppressed by whose ground it is, never erased. Every deviation
was placed from measured clearances (25-93 px to the losing plate's nearest drawn content, and
clear of both plates' page edges), and `build_cuts` reports 0 flagged spans with `build_masks`
confirming "no seam gaps: every page reaches past every bounding cut".

**Result.** All five now read as one clean label. The winning plate's own cross-reference numeral
("10", "8", "39", "43") remains inside its label on four of them -- that is authentic plate
drafting within that sheet's own coverage, legible and not obscuring the name, so it is preserved
per the brief. Ave. C came out with no numeral at all.

**Two faults of my own, both recorded rather than buried:**
1. *A collision detector that produced confident nonsense.* An automated scan meant to find every
   collision reported 41 "collision windows" that were actually segment boundaries and page
   edges, and it had west/east reversed. This is the FIFTH detector in this project to emit
   well-formed meaningless output (cf. F-001..F-003, F-005). Abandoned for the prescribed
   workflow -- generate panels, read the plates -- which found the real five immediately.
2. *`street_match` matched nothing.* The first pass used street IDs ("ave_f_or_church"), but the
   loader tests against the human-readable `street_name` ("Ave. F or Church"). cuts.json rebuilt
   byte-identical, which is the only reason it was caught. Corrected to the readable names.

**Downstream.** Cuts, masks, block master, master_full and the print were all regenerated
(block render 107 s). The D-014 Pier 22 repair was re-verified after the block master changed --
tracks 5/7, the T.H. tank house, the 6" main and the whole fan render exactly as before. All
transforms, controls, adjacency, inventory and archival scans stayed byte-identical. Both QA
suites pass; the pre-existing 1 px inter-sheet white slivers fell from 143 to 33 as a side effect.

**Checkpoint re-baselined** as `1912_POST_D018_FROZEN`, now recording component -> PATH -> sha256.
The original Pier 22 checkpoint stored hashes without paths, which is what let a parser bug read
as "0 artefacts checked ... OK"; `verify_checkpoint.py` resolves nothing by search.

## D-019 — Pixel-accurate flat-field + remaining label/numeral repairs (2026-08-20) [PENDING OWNER APPROVAL]

**Owner review request:** red-circled areas on four crops of the print — wharf-yard tone
patchwork, Ave. C labels, Ave. F corridor, Ave. I labels — with instruction to show results
before finalizing. Before/after evidence delivered as review sheets 1-4; this entry records
what was changed and why. Commit made to preserve state; the owner has not yet approved.

**1. Wharf-yard patchwork (owner image 1) — my own artifact, root-caused and fixed.** The pale
rectangles, the grey band around the Elevator conveyor, and the beige steps near the bay
lettering were all one defect: D-017's flat-field rasterized its region map in 128 px CELLS, so
gain steps landed NEAR but not ON the ownership seams — misaligned tone rectangles wherever
ownership is fine-grained (the content-frontier staircase, every panel/block border). Fix:
`composite_wharf.py` now writes `ownership_map.tif` (uint8 region id per pixel, 0=uncovered,
1..12 = masks.json order, 13/14 = panels A/B), and `paper_flatfield.py` estimates each region's
field as before but applies gain PER PIXEL by that map, each region's grid extrapolated over the
whole cell lattice so bilinear sampling never mixes neighbouring regions. Tone transitions now
sit exactly on source seams, where matching both sides to the common target makes them
invisible. Side benefit: the panel-B/sheet-9 tone band at Pier 22 (D-014 "known remaining")
is gone.

**2. Ave. C s09|s10 doubled label (owner image 2, left circle).** Sheets 9 and 10 both letter
the avenue at canvas y 7595-8741 and both bands straddled the cut — printed as a tangle with a
ghost copy. Deviation moves the cut 85 px EAST (to ~13933) so sheet 9 supplies one complete
label. Moving west was rejected: it would delete sheet 9's drawn block face. Clearances 20/20/41
px, recorded in manual_deviations.json.

**3. Chopped page numerals at the 24th St junctions (found during the sweep).** Sheets 12 and
49 print their own page numbers ('12', '49', with 'GALVESTON, TEXAS.') into the Ave C x 24th
and Ave F x 24th intersections; every neighbour maps that ground as blank street; the cuts
showed floating fragments. Two 24th-St deviations (offsets +100 / +80 px south over the numeral
spans) hand the fragment pockets to the blank northern plates — numerals suppressed whole by
ownership, consistent with D-013 and with every other plate's page number, none of which appears
mid-print. At the F junction this also completes sheet 43's half-clipped 70-ft width figure.

**4. NOT changed, deliberately: the sideways cross-reference numerals** inside street names
('AVE. F 10 OR CHURCH', 'AVE. I 39 OR SEALY'). Authentic Sanborn typography — the numeral names
the adjacent sheet and is printed upright on the plate, hence sideways along the street. Cannot
be removed by ownership: every flanking plate's label embeds one. Removal would mean erasing
ink, which the project rules forbid.

**Verification.** Both QA suites pass every content check (contrast up in all six lettering
regions, 0.000% clipping, paper within 3 levels of the 1899, yellow/pink saturation 1.00,
orange held, water exact, determinism byte-identical, PDF 40.00 x 25.84 in at 300.0 DPI). The
frozen-artefact verifier reports exactly the six files this change legitimately touches (cuts,
masks, deviations, block master, master_full, compositor) and nothing else. Pier 22 re-verified
intact after the block re-render. Checkpoint re-baseline deferred until owner approval.

---

## D-020 — Northern wharf yard: smooth ownership cut (two variants, PENDING OWNER APPROVAL)

**Owner report.** Two circled areas in the wharf yard: the compass rose / shed edge, and the
cotton-seed oil tanks. Shown a three-way comparison of the yard (block plates only / sheet-5
panel A only / current composite) the owner said *"I think sheet five panel a looks the best"*,
then asked for both variants below to be built in full.

**Diagnosis — one cause, not two.** The panel/block content frontier over canvas rows 0-6399 is
a STAIRCASE, not a line. Measured: it lands ON drawn ink in **1816 of 6400 rows (28.4%)**, and
its largest row-to-row jump is **883 px**. Every large jump that falls on drawn content slices
it. The compass rose printed cut in half (the step at y~5750 swings the frontier 8512 -> 7605,
so panel A's blank apron supplies the top of the ornament and sheet 9 the bottom); the dashed
track work beside the oil tanks was interrupted by rectangular panels of blank apron. This is a
source-ownership fault, not registration: both plates draw this ground.

**Rejected first — the "ink envelope" frontier (v2/v3).** Measured: it locks onto the block
plates' own PAGE-EDGE LINE at canvas x 7445-7468 for every row from y 4000 to 9000, dragging a
page margin into the print and rendering the slip corner twice at two scales. Reverted; the
compositor was restored byte-identical before this work began. Recorded as F-007.

**Method.** Min-cost path over rows 0-6399, cost `1000 * (cut lands on drawn ink on either
plate) + 60 * (ink fraction within +-40 px)`. Anchored so row 6399 = canvas x 8161, the D-014
polyline's first breakpoint, so the approved Pier 22 repair is met with **no ownership step** and
rows 6400-8999 are byte-unchanged. The cut may never run west of the block plates' page-edge line
(coverage edge + dark edge run + 8 px). Stated as a 200-breakpoint polyline in
`50_seams/yard_cut.json`; max deviation from the solved path 2 px. Ownership only — no pixel is
painted, cloned, blended or interpolated.

**Why the second cost term exists.** A pure on-ink objective scored 0.4% and still looked wrong:
it threaded the cut BETWEEN the compass rose's spokes, printing a sliver of star with the body
gone. The metric was satisfied; the picture was not. The proximity term keeps the boundary
mid-lane and repels it from ornament and lettering. Recorded as F-008 — the sixth automated
detector on this project to return a confident wrong answer, and the reason every candidate here
was rendered and looked at before being believed.

| | rows on ink | max row jump |
|---|---|---|
| v1 frontier (delivered) | 1816 / 6400 (28.38%) | 883 px |
| **A — compass kept** | **144 / 6400 (2.25%)** | **2 px** |
| **B — compass dropped** | **172 / 6400 (2.69%)** | **3 px** |

**Variant A — compass rose kept.** The cut is held west of the ornament so the block plate
supplies it whole. Keeps every feature the block plates carry there: the compass rose, the
rail-track numbering, the full `COTTON SEED OIL TANK` lettering, the `Fish Commis. Off.` label
and the `740` block number.

**Variant B — compass rose dropped.** The cut is held east of the ornament so sheet-5 panel A
supplies that ground and the compass is suppressed by ownership, as Sanborn page furniture,
following the D-013 precedent for page numerals. A first attempt constrained only to x 8460 left
the ornament's long solid pointer (which reaches canvas x 8729) printing as an orphan dark
sliver; the constraint now covers rows 5450-5899 out to x 8790. Suppressing it whole obliges
panel A to supply a wider band of the yard through those rows, which also costs the rail-track
numbering, the `SEED` in the tank labels and the Fish Commission label.

**Plate resolution, measured.** Sheet 5 is a half-scale overview plate (solved scale 1.98761 vs
the block sheets' 0.993-1.005), so panel A carries about one source pixel per 2x2 canvas pixels.
Measured on features both plates draw: the block plates resolve line pairs down to ~9-10 canvas
px separation, panel A needs ~12-13; above 0.15 cycles/px the block carries 5-30x more spectral
energy. Both survive the 0.458x print downsample, so the plate, not the print, is the limit.
(Measured by a subagent whose challengers were killed before they could re-verify; stated here
with that provenance.)

**Recommendation: A.** What made panel A look best in the three-way was the absence of seams,
not the drawing; smoothing the boundary delivers that without giving up the cartography.

**Verification.** Both variants built end to end. Every content check passes in both QA suites:
contrast up in all six lettering regions (+2.3% to +21.4%), 0.000% of map content clipped, paper
within 3 levels of the 1899, yellow and pink saturation ratio 1.00, orange saturation held and
luminance up, hue shift 0-2 deg, open water exactly (199,214,209), determinism byte-identical,
PDF 40.00 x 25.84 in at exactly 300.0 DPI. The frozen-artefact verifier reports 35 of 41
artefacts byte-identical and exactly six changed — four from D-019 (cuts, masks, deviations,
block master, still pending approval) and two from this decision (master_full, compositor). The
archival scans, every transform, the inventory, the freeze manifest and the controls are
untouched. Checkpoint re-baseline deferred until owner approval.

**Deliverables.** `deliverables/variants/Galveston_1912_VARIANT_A_compass_kept.pdf` and
`..._VARIANT_B_compass_dropped.pdf`, with their print_composition and master_full manifests.
`50_seams/yard_cut.json` carries both polylines and an `active` selector; it is currently `A`,
and the canonical deliverable is built from A.

---

## D-021 — Pink-wash saturation match to the 1899 (PENDING OWNER APPROVAL)

**Owner request.** The selected print (print(4), verified byte-identical in image content to the
D-020 variant A build) will be framed side by side with the 1899; the owner asked for a check
that the red-ish buildings match, colour changes only, nothing applied without approval.

**Measured (print-to-print, 150 dpi, red/pink class by brightness subclass).** Mid tones and
deep reds already match the 1899 within 3 levels. The only gap: the LIGHT PINK WASH — 86% of the
class — at median S 0.286 vs the 1899's 0.302 (ratio 0.947).

**Change.** `pink_wash_boost` in `50_seams/tone_anchors.json`, applied by `tone_match.py` inside
the D-016 stage: extra chroma gain x1.055 about the same Rec.601 luma axis, confined to the pink
band (hue 330-20 deg wrapped, S > 0.15, feathered 4 deg / 0.05 like the orange carve-out),
ramped by HSV value (zero below V 190, full above 215) so the mid and deep tones do not move,
and gated by (1 - orange weight) so the D-016 orange hold is never double-treated. Luma is
preserved by construction, so type legibility cannot change.

**Caught during implementation (units mismatch).** The first version ramped on Rec.601 luma; the
wash's luma is ~187, below the ramp start, so the boost never engaged — pixels changed 0.14%,
class median x1.000. The slab test caught it before anything shipped; the ramp now uses the max
channel (HSV V), the same statistic the subclasses were measured with.

**Result (rebuilt print vs the 1899).** Pink wash S 0.302 vs 0.302 — exact; mid (184,133,126)
vs (185,136,131); deep red (117,81,75) vs (116,80,73); hue and luma unchanged; orange and
yellow untouched (x1.000). Both QA suites: every content check passes (pink saturation ratio
now 1.01 page-wide, 0.000% clipping, water exact, determinism byte-identical, 300.0 DPI). The
frozen-artefact verifier reports exactly seven intentional changes: six from D-019/D-020 plus
`tone_anchors.json` from this decision. Checkpoint re-baseline still deferred until approval.
