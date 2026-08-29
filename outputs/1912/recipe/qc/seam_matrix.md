# Seam matrix — QA stage 1

Master: `60_master/final/candidate_master.tif`  sha256 `3c35c429cca0d4b8c823604cdcac8eaaad55fdc83da296275207b1557c1d4cb9`

All frozen-input hash checks passed: **True**

Encroachment source: frozen-cuts rerun `70_qa/run1/content_extent_report_frozen.json` (the 60_master copy predates the freeze).

| seam | street | along RMS px (worst) | across RMS px (worst) | cut provenance | tiling (ovl px2, bad, gap px, drift px) | encroach interior A/B px (halfw) | panel verdict |
|---|---|---|---|---|---|---|---|
| 7-9 | 21st_or_center_st | 4.8 (7.1) | 34.5 (44.4) | pooled TLS +dev | PASS (1.1, 0/84, 0.001, 5.47) | 216 / 214 (216) | PASS — all rail track groups continuous across cut; frontages stagger correctly; 21st scale-bar manual deviation verified working (bar ground owned by s9 blank street as designed) |
| 8-10 | 21st_or_center_st | 3.0 (4.0) | 10.3 (10.5) | pooled TLS | PASS (0.0, 0/80, 0.0, 2.66) | 215 / 216 (216) | REVIEW — cosmetic: mid-intersection ornament (fountain/lamp) drawn by s10 loses its top at the cut, s8 half blank (canvas ~17800-18000, 4835); geometry aligned, no cartography lost |
| 39-43 | 21st_or_center_st | 3.2 (4.4) | 20.1 (23.9) | pooled TLS | PASS (0.0, 0/80, 0.0, 2.65) | 215 / 215 (216) | REVIEW — cosmetic: s43 compass/ornament and arrow tops amputated at cut + s39's own version leaves stray tip fragments (canvas ~21730-22760, 4850); geometry aligned |
| 40-44 | 21st_or_center_st | 3.4 (5.6) | 5.2 (6.7) | pooled TLS | PASS (1.9, 0/84, 0.001, 5.44) | 214 / 215 (216) | PASS — sliver seam clean; NOTE shared with 39-43 zone: s39 'Scale of Feet.' caption floats at canvas ~24700-25080,4805 (its ruler bar lies south of cut under s43 blank; census s39_c116) |
| 9-11 | 24th_st | 0.8 (0.9) | 7.6 (7.6) | pooled TLS | PASS (0.0, 0/84, 0.0, 4.98) | 216 / 168 (219) | PASS — dense rail-yard trackage crosses with no visible jog (best seam, rms 0.85) |
| 10-12 | 24th_st | 7.5 (11.2) | 7.8 (8.6) | pooled TLS | PASS (0.0, 0/80, 0.0, 2.43) | 216 / 178 (219) | REVIEW — cosmetic: s12 large '24TH ST.' label top-amputated at cut, only glyph bottoms show (canvas ~16590-17100, 11690-11740); geometry aligned; candidate for a future manual deviation |
| 43-49 | 24th_st | 4.0 (5.9) | 20.4 (24.8) | pooled TLS | PASS (0.0, 0/80, 0.0, 2.42) | 218 / 174 (219) | PASS — frontages + both pipe runs continuous; one small amputated glyph fragment mid-street (~23790,11730); s43 diagonal line is a crease in the archival scan |
| 44-50 | 24th_st | 2.8 (4.2) | 23.9 (26.7) | pooled TLS | PASS (2.2, 0/84, 0.001, 4.99) | 217 / 172 (219) | PASS — corridor continuous, stagger correct, per-plate width labels by design |
| 7-8 | ave_c_or_mechanic | 6.2 (12.8) | 17.1 (22.7) | pooled TLS | PASS (0.0, 0/96, 0.0, 2.55) | 70 / 203 (205) | PASS — street edges align (~10px); s7 'AVE. C.' name label nicked at cut (canvas x~13790, y 1490-1990); pipe annotations at plate-specific in-street offsets (drafting) |
| 9-10 | ave_c_or_mechanic | 20.6 (34.8) | 28.5 (37.7) | pooled TLS | PASS (0.0, 0/92, 0.0, 0.83) | 5 / 198 (205) | PASS — cross-street mouth jog 20-35px at 22nd/23rd = the plates' own drafting disagreement (matches along-residual 34.8 worst, huber-downweighted); s9 page edge safely outside master; no doubling |
| 11-12 | ave_c_or_mechanic | 9.3 (16.5) | 62.1 (87.6) | pooled TLS | PASS (0.3, 0/98, 0.0, 2.56) | 78 / 204 (205) | PASS — s11 mid-street annotation column preserved complete; opposite frontages stagger normally; 12-inch pipe continuous; tone step = scan exposure (by design) |
| 8-39 | ave_f_or_church | 4.5 (7.7) | 15.0 (22.5) | pooled TLS | PASS (0.0, 0/96, 0.0, 1.73) | 67 / 144 (235) | PASS — 10-inch pipe continuous; s8 'AVE. F' vertical name label split at cut (x~19905); frontages stagger correctly |
| 10-43 | ave_f_or_church | 11.0 (20.1) | 27.0 (36.0) | pooled TLS | PASS (0.0, 0/92, 0.0, 0.56) | 4 / 66 (235) | PASS — pipe line continuous (~10px jog); both plates' 'CHURCH' label halves sit side-by-side at cut (honest duplication); mouth jog ~30px within drafting scatter |
| 12-49 | ave_f_or_church | 4.7 (8.0) | 108.7 (110.8) | pooled TLS | PASS (2.2, 0/98, 0.001, 1.74) | 36 / 125 (235) | PASS — the 110px worst ACROSS residual manifests only as the plates' differing drafted street width; corridor blank, frontages complete, no doubling |
| 39-40 | ave_i_or_sealy | 5.0 (7.5) | 8.4 (14.0) | pooled TLS | PASS (1.3, 0/96, 0.0, 0.93) | 101 / 82 (231) | REVIEW — cosmetic: two plates' 'AVE. I' labels misaligned ~35px = ghost-doubled text at cut; margin cross-refs compose to a '4|9' chimera (s39 '40' + s40 '39'); geometry aligned |
| 43-44 | ave_i_or_sealy | 4.0 (6.9) | 3.7 (4.4) | pooled TLS | PASS (0.0, 0/92, 0.0, 0.3) | 195 / 77 (231) | PASS — composite 'AVE. I OR SEALY' street text reads cleanly (halves from both plates align within ~5px); s44 margin cross-ref '43' correctly owned |
| 49-50 | ave_i_or_sealy | 3.6 (6.2) | 10.3 (12.1) | pooled TLS | PASS (2.7, 0/98, 0.001, 0.94) | 134 / 55 (231) | PASS — clean corridor; 12-inch pipe and 120-ft avenue labels continue |

along = anchor coincidence projected on the seam direction (true misregistration). across = constructed frontage separation vs default width x kappa: absorbs drafted-width disagreement between plates (sigma floor 12 px), kappa is prior-dominated — NOT a misregistration metric. drift = distance between the mask cut (rebuilt from 3-dp-rounded line_fit by build_masks) and cuts.json polyline_mosaic; both sheets share the same rounded cut, so tiling is unaffected.

Tiling check: shapely re-derivation, overlap area of the two owned regions (px^2), boundary gap/side sampling every ~40 px at +/-0.5 px, shared boundary length. Manual deviations in span:

- 7-9: offset -18.0 px over t=[-8232.0, -6580.0] — Sheet 7's 'Scale of Feet' bar occupies 21st St street space at the cut; default midline clips its label edge. Deviating the cut north gives 
