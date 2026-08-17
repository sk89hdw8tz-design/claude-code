# FABLE REVIEW HANDOFF — Galveston 1912 reconstruction

Independent review track (Fable). Two subagents used, as budgeted: a Sheet 5 / wharf
topology specialist and a high-risk seam-control specialist; coordinator performed the
protocol audit, determinability review, and adversarial verification of both specialists'
pivotal claims directly against the archival scans. Nothing canonical was modified;
nothing was pushed; all imagery stayed local.

## 1. Sheet 5 verdict — CONFIRMED MULTI-REGION (two panels) · READY FOR OPUS RECONCILIATION

Sheet 5 carries **two separately drafted panels of one continuous east-west wharf
frontage**, divided by a drafted full-height triple rule at x ≈ 3789 + 0.0099·y.
Panel A (page-left) = **Piers 17-22**, 16th-22nd St landward refs (6, 33, 7, 9);
Panel B (page-right) = **Piers 22-28**, 22nd-28th St refs (9, 11, 13, 4). North is
page-left (compass at 3990,5180); lettering is upright — the plate is NOT rotated in
the scan. **Pier 22 is drawn on both panels** (verified by coordinator at (1900,7280)
and (4560,360)) — a single rigid transform would displace the same pier ~2,400 ft, so
**two logical regions / two transforms are required**; the duplicated Pier 22 / 22nd St
ground is the cross-panel consistency check and the ONLY duplicated cartography found
anywhere in this edition.

Corrections to the prior working hypothesis: panels are east/west (not stacked
north/south); continuation runs bottom-of-A → top-of-B; **sheet 9 adjoins BOTH panels**
(break at 22nd falls inside 9's 21st-24th range); Pier 16 is not actually drawn despite
the index's "16-28"; the Piers 19-25 target spans the break, and regions outside target
(Piers 17-18; Piers 26-28) are polygon-flagged. Evidence gap: sheet 13 not on disk; the
5-13 relation rests on sheet 5's printed refs + key map.

Files: `SHEET05_INDEPENDENT_FINDING.md`, `sheet05_candidate_regions.geojson`,
`evidence/sheet05/` (30 crops).

## 2. Protocol findings — READY FOR OPUS RECONCILIATION

Architecture sound; schema incomplete. Add before first verified control: explicit
why-not-one-block-off field; remeasurement fields; a defined construction (and floor)
for sigma_across; per-reading sigma instead of the 8.0 default; retention of REJECTED
entries; explicit axis convention; source-checksum reference; recorded width-annotation
evidence. Details: `FABLE_PROTOCOL_AUDIT.md`.

## 3. Seam triage — 17/17 triaged

LOW 7, MEDIUM 7, HIGH 3 — the three HIGH seams are exactly the column-4 attachments
(39-40, 40-44, 44-50), agreeing independently with the determinability analysis.
Full table: `FABLE_SEAM_TRIAGE.csv`.

## 4. Independently measured seams (six, chosen for risk not ease)

39-40, 40-44, 44-50, 49-50 (weak column-4 quadrant), 7-9 (rail-yard seam), 11-12
(empty-outline blocks). 12 controls, 2 anchors per seam, both flanking faces on both
plates, all DIRECTLY OBSERVED, every record carrying printed address-run evidence.
Coordinator spot-verified control #1 (39-40, 19th St) against the source: both claimed
faces land exactly on the drafted lines with the cited addresses in view.

## 5. Accepted controls

8 high-confidence + 4 downgraded-to-medium = **12 accepted** (see
`FABLE_INDEPENDENT_CONTROLS.csv`, `evidence/seams/` — 24 annotated 1:1 crops).
Cross-checks passed: drafted street widths reproduce on facing plates; block pitches
agree within 0.4%; scale ~6.07 px/ft consistent.

## 6. Rejected controls and downgrades

0 rejected outright. 4 downgraded with reasons (bold power-house wall stroke; dashed
corner sheds forcing off-corner reads; rail-track clutter ×2 on 7-9). Three first-pass
reads were self-caught and corrected before recording (digit contamination 18 px; two
misidentified faces) — evidence that the adversarial pass is doing real work, and that
single-read coordinates should not be trusted network-wide.

## 7. Determinability risks

Along-seam geometry and scale: strong. Rotation: pinned by junction closure, weak on the
column-4 chain (40, 44, 50) and sheet 7. Across-seam placement: rests entirely on
constructed street widths — floor sigma_across at ~±12 px; use per-seam drafted-width
measurements from both plates, not annotations (Broadway's drafted separation is ~100 ft
where annotations say 150'). Recommendations 1-6 in `FABLE_DETERMINABILITY_NOTES.md`,
including the through-street collinearity diagnostic that catches a column-4 rotation.

## 8. Disagreements with current project assumptions

1. WHARF_PLACEHOLDER's stacked-strips reading → panels are east/west; sheet 9 meets both.
2. "No duplicated cartography anywhere" → true for the 17 block seams, with one exception
   now known: sheet 5's own cross-panel Pier 22 duplication (an asset, not a problem).
3. Annotated street widths as across-seam basis → unsafe as sole basis (Broadway 100 vs
   150); measure drafted widths per seam.
4. Coverage plan's "~29 controls" is safe, but panel-gap-keyed harvesting on 7-9 will hit
   the **20-ft alley trap** at x≈5400 (alley carries the 10" pipe; true Strand crossing
   ~700 px west). The alley/avenue distinction must be address-run-verified on that seam.

## 9. Files created (all under `fable_review/`)

- `FABLE_HANDOFF.md` (this file)
- `SHEET05_INDEPENDENT_FINDING.md` · `sheet05_candidate_regions.geojson` · `evidence/sheet05/` (30 crops)
- `FABLE_PROTOCOL_AUDIT.md`
- `FABLE_SEAM_TRIAGE.csv`
- `FABLE_INDEPENDENT_CONTROLS.csv` · `evidence/seams/` (24 crops)
- `FABLE_DETERMINABILITY_NOTES.md`

## 10. Recommendations to Opus

1. Reconcile the sheet-5 record: adopt two regions per the GeoJSON, correct the
   stacked-panels hypothesis in WHARF_PLACEHOLDER.md (keep deferral and re-entry
   criteria; note sheet 9 adjoins both panels).
2. Amend the protocol schema per the audit BEFORE recording verified controls.
3. Treat the 12 Fable controls as an independent measurement set: measure your own
   controls without reading these first where the protocol requires independence, then
   reconcile. Where measurements differ: diagnose; average only if neither shows an
   identified bias; supersede on demonstrated bias; otherwise carry the disagreement as
   uncertainty. Do not blanket-average.
4. On seams 7-9 and 39-40/40-44/44-50, use the Fable evidence crops as the reference for
   anchor identity (alley trap; power-house stroke) even where you re-measure positions.
5. Run the first diagnostic solve with sigma_across ≥ 12 px and the covariance flags from
   the determinability notes; expect flags on 40, 50, 7 and treat their absence as a
   tooling question, not reassurance.

**Overall: READY FOR OPUS RECONCILIATION.** No BLOCKING AMBIGUITY anywhere; one
REQUIRES SOURCE RECHECK item — the 5-13 attachment, pending sheet 13's acquisition in a
push-permitted session.
