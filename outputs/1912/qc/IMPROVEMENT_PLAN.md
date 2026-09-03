# 1912 Galveston mosaic — improvement plan and team execution

## Context

The 1912 city mosaic is finished to the acceptance gate (HQ-29, REPORT.md): 106
units, one piece, 249 seams censused (203×5, 38×4, 5×3, 3×2, 0×1), 63 boundary
and 33 interior 1:1 windows reviewed, deliverables rendered and verified. The
owner has asked for a plan of what would still improve the map, executed by a
team of subagents — Opus 5 for judgement and evidence, Sonnet 5 for volume — so
Fable's remaining budget goes to direction and gate checks only.

Scope chosen by the owner: **must-do + should-do** (P1 + P2 below), Opus 5 on
every registration/evidence call. Three cheap extras ride along (P3-1..3).

Standing rules every task obeys: registration is frozen unless the plates
themselves prove a placement wrong (printed names, address runs, block faces,
adjoining-sheet numerals); no blending, inpainting, redrawing or tone
correction; one authentic plate owns each pixel; the accepted 27×40 master
(`inputs/masters/*1912*.pdf`) is the visual reference and it KEEPS compass
roses, adjoining numerals and scale legends where no neighbour maps the ground.
Recipe-first: every output is re-rendered from the recipe
(streetcut → fillgaps → tiling → publish/printmaster). One commit and one
HUMAN_QUEUE.md entry per landed change, including "no change, evidence
insufficient" outcomes.

Reconnaissance facts that shape the work:
- Round-5 census, the 63-window periphery review and the 33-window interior
  review exist ONLY in workflow journals under
  `/root/.claude/projects/-home-user-claude-code/667180c2-8c6a-5c7c-8f63-764f5714e1d7/subagents/workflows/`
  (`wf_dfa33c97-301` census, `wf_4cb95f43-0f4` periphery, `wf_fc88500c-4ca`
  interior; one `{"type":"result",...}` line per agent in `journal.jsonl`).
  Nothing under `outputs/1912/qc/` records them.
- `outputs/1912/recipe/provenance.json` is stale (2026-08-29, commit 79b58a2)
  and no tool writes it.
- `tools/streetcut.py:dp_cut` picks a side candidate by LEAST visible ink
  (`sides.sort(key=lambda c: c[2])`), so a band where one plate is blank
  paper beyond its rule and the other draws the street in detail is given to
  the blank plate (seen at 94|95 and 13|14). `DP_HALF=320` caps wander, so a
  band-edge candidate must be added, not just re-sorted.
- `reciplib.footprint_native()` is the single chokepoint for extent /
  exclude / region / furniture (`cut:false` honoured); `furncover.py`
  (COVER=0.98) already implements the master's keep rule. Only 6 units carry
  `edge numeral/glyph` boxes today; plate 89 has no scale-bar box; 3/5a/5b no
  title box.
- `tools/interiorwins.py` OVERWRITES `qc/interior/win_NN.jpg` and
  `windows.json` in place.

## Tasks

### P1 — must do

**P1-1 Persist the review record** (sonnet, 1 agent). New `tools/journalq.py`:
read a workflow dir, take the last result per agentId, merge `result.seams` /
`result.windows` / `result.reports` + confirms into one JSON keyed by seam or
window, recording agentId and workflow id. Outputs
`outputs/1912/qc/seams/census_round5.json`,
`outputs/1912/qc/periphery/review_round2.json`,
`outputs/1912/qc/interior/review_round1.json`. Verify: histogram reproduces
203/38/5/3/0; 63 windows / 18 confirmed; 33 windows / 21 clean / 16 confirmed.
Also copy `qc/interior/*` to `qc/interior/round1/` BEFORE anything re-runs
`interiorwins.py`.

**P1-2 Blank-band ownership rule** (opus, 1 dev + 1 reviewer; sonnet graders
for the regression set). In `dp_cut` after `raw[u]`/`raw[v]` are masked to
the band: `ink_u`, `ink_v` sums; if `min < BLANK_RATIO(0.20) * max`, add a
fourth candidate pinned at the blank plate's band edge (extend `DP_HALF` for
that case) and select it, bypassing the visible-ink sort; write
`"blank_band": {"winner", "ink_ratio"}` on the seam row of
`seams/ownership_city.json`. Evidence: the blank strip must be beyond that
plate's own coverage, confirmed on the native scans of 94|95 and 13|14. Verify
by DIFF, not by re-grading everything: dump each pair's cut line before/after,
list every seam whose path moved > 50 px, re-grade that set plus adjacent
round-5 fives; no seam may drop below its round-5 grade.

**P1-3 Inset-frame notch coverage** (opus, 2 agents: 20b/24/25 family and
25b/54b/32/47 family). Coverage only, no registration. Per side of plates
24/25/32/47, sample the strip between `extent` and `extent_scan` on the
native scan and relax `extent` only where it holds map ink and no border rule
(neatline chain from `tools/neatline.py`). For panels 20b/25b/54b, test
extending `region_native` to the parent's `exclude_native` boundary minus the
frame rule's width. Record each accepted change with its ink profile. Verify:
`qc/tiling_audit.json` unclaimed drops, the 54k px² 9th St/Ave L hole and the
47k px² hole at [43809,24982] shrink or close, overlap stays ~1,026 px², a 1:1
crop at each notch shows no frame rule and no second neatline.

**P1-4 Re-verify the four post-census fixes on the final build** (opus for
adjudication, sonnet for crops; ~14 agents). After the re-render: re-grade
`14_49 15_67 20_20b 20_23 63_70 63_71 64_71 64_72` under
`qc/seams/GRADER_BRIEF_R5.md` on fresh crops; re-review the 18 confirmed
periphery findings on fresh `tools/perirender.py` renders. Grader writes its
own score first, then sees the round-5 text and states agree/disagree.
Output `census_round6.json`, `periphery/review_round3.json`. Pass: every seam
≥ 4 or a written cause; each periphery finding resolved or reclassified into
the three accepted classes (master-kept furniture / neatline end of map /
the wharf–Strand source gap).

**P1-5 Generated provenance** (sonnet, 1 agent, last). New
`tools/provenance.py --year 1912 --apply`: HEAD commit + subject, tool list
with sha256, gate block read live from `qc/tiling_audit.json` and
`tools/bandresid.py`, QC record paths from P1-1, sha256 of every shipped
file in `mosaic/ tiles/ print/ preview/`, disclosed source gaps and unplaced
sources; keep the existing freeze-manifest verification block verbatim.
Verify: re-run on an unchanged tree is a no-op except the timestamp; hashes
match `sha256sum`.

### P2 — should do

**P2-1 Adjoining-sheet numerals and compass roses as furniture** (sonnet
detector + 3 opus adjudicators). New `tools/edgeglyph.py` on the
`tools/scalebar.py` pattern: template-match one clean rose and per-digit
templates; group digit hits into runs; fit each box to ink, clip to the
template footprint + 30 px, validate darkness (darkest row 0.7–0.95). Gates:
glyph height ≥ 60 native px, box centre within 400 px of the neatline
(`extent` vs `extent_scan`), box in a roadway (no block-face rule crossing).
Every proposed box is shown to an opus adjudicator as a native crop who must
name it ("adjoining numeral 74", "compass rose") before it is written; zero
false positives, false negatives accepted. Then ONE `furncover.py --apply`
after P1-3 and P2-1 both land. Expect most boxes `cut:false` — correct, the
master keeps them.

**P2-2 Finish the control-residual audit** (opus, 7 agents + 1
consolidator). `pair_26_42 pair_30_36 pair_54_60 pair_30_31 pair_31_32
pair_38_42 pair_38_41`, same protocol as the two already audited (both came
back "net tension, values sound"): read faces from `plates/lattice.json` and
native scans, confirm identity from printed names / address runs, decide
value-wrong vs net-tension, dry-run `tools/localsolve.py` (never `--apply`
from a reviewer). Any re-read records the previous value and reason in the
control file. Verify with `tools/bandresid.py --min-ft 6` before/after: no
control newly > 6 ft, median ≤ 1.7 ft.

**P2-3 The 17|18|19 seawall steps** (opus ×2 independent + 1 adjudicator).
Registration-evidence task on periphery windows edge_00/edge_01 (20–28 ft
steps at the far west). Read the seawall line and block faces natively;
propose a tie per `qc/seams/REGISTRATION_BRIEF.md`; dry-run
`localsolve.py --units 17 18 19` (`--similarity` if the step grows along the
seam). Apply only if both reviewers name the same corridor and face pair; a
split verdict = no change + HQ note. Likeliest honest outcome: documented
drawing difference, no change.

**P2-4 Denser 1:1 interior review** (~25 sonnet graders + 4 opus confirmers).
After P1-1's archive copy: `tools/interiorwins.py --cols 12 --rows 16`
(~100 windows), grade with `qc/interior/INTERIOR_BRIEF.md`, adversarial
confirm on every non-cosmetic finding. Output `review_round2.json`. Any real
recipe-changing finding re-opens the evidence wave; nothing is patched after
the render.

**P2-5 Tiled print output** (sonnet, 1 agent). `tools/printmaster.py
--tiles 2x2`: reuse `work/city/1912_wall_4.tif` (no re-render), crop with
pyvips into panels ≤ 36×44 in at 300 ppi with a 1 in (300 px) overlap,
registration marks and panel label in the overlap/bleed margin ONLY (never
over map pixels), TIFF (deflate/predictor 2, BigTIFF) + PDF per panel, and
`print/tiles/manifest.json` with each panel's mosaic rect. Verify: overlaps
match pixel-for-pixel; every panel opens in `gdalinfo` and `vipsheader`.

### P3 — riding along (cheap)

- **P3-1 DeepZoom viewer** (sonnet): `outputs/1912/tiles/index.html`,
  OpenSeadragon from a CDN, `tileSources: "1912.dzi"`, caption with source,
  ground scale (5.7966 px/ft) and the disclosed gaps.
- **P3-2 Plate 89's scale bar; 3/5a/5b titles** (opus, 1 agent): confirm on the
  native scan whether each sits outside the trimmed extent (record) or was
  missed by `scalebar.py`'s 0.52 threshold (re-run lower, validate, apply).
- **P3-3 Regenerate stale seam crops** (sonnet): after the re-cut,
  `tools/seamcrops.py --only <changed pairs>` so shipped QC evidence matches
  the shipped build; reconcile REPORT.md / DASHBOARD.html gate numbers.

### Deliberately not done
- Placing plate 32's inset or wharf sheet 2 (placement would come from a
  neighbour, not the plate; the inset duplicates 54b's ground).
- Filling the wharf/Strand 660 ft gap or the cemetery block (both plates
  print adjoining numeral "0"; there is no source).
- Any tone work on the 38 tone-only score-4 seams.

## Execution order and gates

```
WAVE 0  (parallel, no recipe change)   P1-1 journal extraction + interior archive copy
WAVE 1  (parallel; NO worker runs --apply)
        P2-2 ×7 control audits · P2-3 seawall ×2+1 · P1-3 notches ×2
        P2-1 edgeglyph detect + adjudicate · P3-2 plate 89 · P1-2 dp_cut rule (DP_DEBUG on 94|95, 13|14)
=== GATE A (orchestrator, opus): every transform/control change has a named corridor,
    face pair on each plate, identity argument. Split verdicts → no change + HQ note.
    Apply in order: controls/*.json → localsolve --apply (P2-3 only if it survived)
    → units.json extents/regions (P1-3) → furniture boxes (P2-1, P3-2)
    → furncover.py --apply ONCE. Check bandresid: median ≤ 1.7 ft, none newly > 6.
WAVE 2  (serial, one opus agent) snapshot ownership → streetcut --apply → fillgaps --apply
        → tiling; diff cut lines → CHANGED-SEAM SET.
=== GATE B: 1 piece; overlap ≤ ~1,100 px²; unclaimed ≤ 0.455% with no new hole > 50k px²
    without a named source cause. Fail → back to Wave 1, do not render.
WAVE 3  (serial, sonnet) publish.py → printmaster.py → printmaster --tiles 2x2
        → seamcrops --only <changed> → perirender → interiorwins 12×16
WAVE 4  (parallel) P1-4 re-verify · P1-2 regression grading · P2-4 interior sweep · P3-1 viewer
=== GATE C: every graded seam ≥ 4 or a written accepted cause; no seam below its round-5
    grade. A real new defect re-opens Wave 1 — never patched after the render.
WAVE 5  (serial, sonnet) P1-5 provenance → REPORT/DASHBOARD/HQ-30..3n reconciled → commits
```

Mechanics: each wave is one `Workflow` run (the owner asked for a subagent
team, which is the explicit opt-in). Wave 1 ≈ 17 agents, Wave 4 ≈ 45,
total ≈ 75 agent-runs. Fable's role is limited to launching each wave,
reading the gate summary, and deciding pass/fail; Opus agents do the
judgement inside the waves; the orchestrator agent at Gate A is Opus. All
work on branch `claude/galveston-setup-part-a-mk5z1l`; first action of Wave
0 commits the pending `state/events.jsonl`.

## Do not do
1. No blending, feathering, inpainting, tone matching, sharpening.
2. No plate moves without plate evidence; no city-wide re-solve; `localsolve --apply` only by the Gate A orchestrator.
3. No reviewer runs `--apply` on localsolve, streetcut, furncover, scalebar, fillgaps.
4. Keep `furncover.py` COVER=0.98; boundary furniture stays (master precedent).
5. Do not fill any source gap; do not place plate 32's inset or sheet 2.
6. Nothing written under `inputs/`; masters untouched.
7. No two plates owning one pixel beyond the ~1,026 px² already disclosed.
8. No registration marks over map pixels in the tiled print.
9. Do not run `interiorwins.py` before the round-1 archive copy.
10. No per-seam tuning of `BLANK_RATIO`.
11. Never hand-edit `provenance.json`, `state/ledger.json`, `ownership_city.json`.
12. Every change (including "no change") gets an HQ entry and a commit.

## Critical files
- `tools/streetcut.py` (`dp_cut`, main) · `tools/reciplib.py` (`footprint_native`, `ownership_shapes`)
- `outputs/1912/recipe/units.json` · `outputs/1912/recipe/controls/pair_*.json` · `transforms_city.json`
- `tools/furncover.py`, `tools/scalebar.py` (pattern for `tools/edgeglyph.py`)
- `tools/printmaster.py`, `tools/publish.py`, `tools/perirender.py`, `tools/interiorwins.py`, `tools/seamcrops.py`
- new: `tools/journalq.py`, `tools/provenance.py`, `tools/edgeglyph.py`, `outputs/1912/tiles/index.html`

## Verification (end to end)
- Gate numbers before/after from `qc/tiling_audit.json` and `tools/bandresid.py`.
- `census_round6.json` and `review_round3.json` show every reworked seam/window ≥ 4 or an accepted cause; no regressions vs `census_round5.json`.
- `python3 tools/publish.py --year 1912` and `tools/printmaster.py --year 1912 --tiles 2x2` complete; every output opens in `gdalinfo`/`vipsheader`; PDF page sizes correct.
- `tools/provenance.py` re-run is a no-op; hashes match disk.
- Fresh full-city preview and three 1:1 spot crops (downtown, wharf, south beach) sent to the owner with the four-part report.
