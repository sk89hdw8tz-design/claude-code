# Sheet-5 status note — QA stage 4

Master: `60_master/final/candidate_master.tif`
sha256 `3c35c429cca0d4b8c823604cdcac8eaaad55fdc83da296275207b1557c1d4cb9`

## Finding

The two sheet-5 wharf panels (05A / 05B) are **FITTED but not composited** into
this master. Their transforms are frozen (`40_solve/output_sheet5/
transforms_sheet5.json`, hash in FREEZE_MANIFEST: `fdeeedcc2f3e...`), and the
canvas reserves a blank bay-side band for them.

## Independent verification (this QA run, not the render's own flag)

* Reserved band = canvas columns 0..7460 (full height 14489): scanned every
  pixel of the final master — **0 non-white elements; minimum value
  255** (pure 255 white). The band is truly blank.
* Gap between the band's east edge and the nearest owned content: 1.2 px
  (no sheet leaks into the band; consistent with ownership_audit).
* The render manifest lists exactly the 12 block sheets
  [7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50] — no sheet-5 source was warped.

## Deferral

QA_PLAN stage 4 ("Sheet-5 cross-panel review": which panel owns the duplicated
Pier 22 / 22nd St ground, is the seam honest, is the ~55 ft pier drafting
disagreement preserved) applies **after panel integration**. That integration
belongs to the wharf phase (see `50_seams/WHARF_PLACEHOLDER.md`); the verified
cross-panel controls are already in
`30_controls/verified/cross_panel_05.json` + `pair_05*.json` (hashes frozen).
Nothing to review against this master beyond the blank-band verification
above; the cross-panel QA is **deferred to the wharf phase**, not waived.
