# Final acceptance — Galveston 1912 Historical Master

## Verdict: ACCEPTED (revision 2), 2026-08-17

Master: `deliverables/Galveston_1912_SelectedArea_HISTORICAL_MASTER.tif`
sha256 `6541150275d6c098f673c356c286423c5ef53c1ac3d898632f2384c93ab4bba5`
Print: `deliverables/Galveston_1912_Wharf_Downtown_print.pdf`
sha256 `e0844b9406b5943fc5361b67ddaba092348baf54cd641c13d7d8b56a32e268e4`
(40.00 x 26.09 in, exactly 300.0 DPI, single baseline JPEG q92.)

## The adversarial process worked, and the record shows it

Reviewer B (content audit): PASS — address-run continuity at every seam crossing per the
1912 index, flawless block-number lattice, 40+ specials exactly once, wharf registered at
correctly unified 2x scale. Found the caption's region count wrong (15 -> 14) and the
retained wharf scale text misleading. Both fixed in revision 2.

Reviewer A (geometry + blind layout derivation): confirmed sheet identity, arrangement,
scale and rotation sound — and found a CRITICAL defect the entire QA chain had missed:
the Mallory Steamship shed (Piers 23-25) ~90% overwritten by blank block-sheet margin,
plus the Merrow shed's east wedge (MAJOR). Root cause: the wharf compositor's block-
priority rule used page extent instead of drawn-content extent — the 1889 blank-margin
failure recurring through a newly written rule, in the one band the census had not been
re-run on after compositing. Re-tested numerically (ink fraction 0.9% vs source 7.4%),
fixed by per-row content-frontier ownership (sustained-density test, short-spike removal),
verified restored (ink 9.0%, all annotations legible), Merrow wedge likewise (7.5%).

## Adjudication of remaining REVIEW items (all cosmetic, none blocking)

- Split mid-street ornaments/labels at cuts (incl. the 24TH ST name at D-E) and the
  Sealy-corridor composite numerals ("4|9" chimera): authentic furniture from both
  plates meeting at hard ownership cuts. ACCEPTED-AS-DOCUMENTED; revision path exists
  (manual cut deviations, precedent: the 21st St scale-bar deviation).
- Faint trimmed paper edge of bay-side sheets at the wharf/grid boundary: authentic
  physical-page evidence, 1-3 px. ACCEPTED.
- Wharf attachment steps (10-90 px at Ave A): recorded plate drafting disagreements,
  preserved per the brief. ACCEPTED.

## Acceptance criteria walk

Seams resolved 17/17 + 5 wharf attachments; QA gates: tiling exact, ownership exact,
provenance byte-verified, census 0 hidden-content fails (block) + wharf band re-verified
after the F1/F2 fix; junctions pass; no holes; originals unchanged (SHA-256 re-verified);
one-resample provenance in manifests; adversarial reviews reconciled with fixes or
documented adjudications; sheet-5 two-panel topology honoured with Pier 22 rendered once.
