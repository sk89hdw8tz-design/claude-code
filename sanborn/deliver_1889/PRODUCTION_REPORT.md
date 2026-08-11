# Galveston 1889 — Wharf Front and Downtown

Sanborn Map Co., 1889 edition. Composited from the University of Texas
(Dolph Briscoe Center) scans.

**Extent** — Avenue A (Water) to Avenue I (Sealy); 19th Street to 25th
(Bath Avenue); Galveston Bay and the wharf front. The same frame as the
delivered 1899 poster.

**Sheets used (8)** — 2, 1 (wharf front); 7, 8, 29 (19th–22nd);
9, 10, 27 (22nd–25th). These are the sheets indexed to this ground on the
1889 edition's own key map — the same eight originally selected from it.

## Sheet identification

Every sheet's coverage was established by reading its printed avenue and
street labels, not inferred from position:

| Unit | Coverage |
|---|---|
| 7 | Av. A (Water E.) – D (Market E.) × 19th–22nd |
| 8 | Av. D – G (Winnie E.) × 19th–22nd |
| 29 | Av. G – J (E. Broadway) × 19th–22nd |
| 9 | Av. A – D × 22nd–25th (Bath Av.) |
| 10 | Av. D – G × 22nd–25th |
| 27 | Av. G – J × 22nd–25th |
| 2 | Bay/wharf → Av. A × 19th–22nd |
| 1 | Bay/wharf → Av. A × 22nd–25th (**right panel only**) |

Two traps this caught. Sheet 2's apparent panel divider is a bundle of
railroad switch tracks, not a rule — it is one continuous panel. Sheet 1
carries **two** panels split by a real rule at native x = 1598; its left
panel is the Texas Standard Oil Mill district at **43rd–45th**, twenty
blocks west, and is excluded. Taken at face value it would have been
composited into the middle of downtown.

Also recorded: "north points page-left" is the normal orientation on these
sheets, so none needs rotation — unlike the 1885 edition's wharf sheet,
which really does print Avenue A horizontally.

## Registration

1889 shares 1899's physical grid. Autocorrelation over the six downtown
sheets gives an avenue pitch of 1007 px (982/1005/996/1011/1009/1012) and a
street pitch of 1161 px (1160/1161/1135/1162/1176/1174), against 1899's
1006 × 1169 on the same 3400 px UT scan width — same city, same map scale.
The 1899 corridor-slot model therefore applies unchanged. The wharf sheets
return noise at low correlation confidence, exactly as 1899's do: few grid
lines, mostly piers and water.

### Corrections applied, and why

1. **Edge-line overrides (14 knots, 6 units).** The whiteness comb latches
   the block frontage wherever a corridor is cut by the sheet's own paper
   edge. Measured by fixing the pitch at the edition nominal and anchoring
   the phase on each unit's interior lines: edge spacings ran **5–9 % short**
   while interior spacings sat within ±1 %. Verified visually on sheet 7's
   Avenue D line — the detected position lay on the frontage with the
   address numerals printed along it, the predicted position in the open
   corridor.

2. **Frame-open edges.** No 1889 sheet prints a frame line on any
   seam-facing edge: the longest dark run in the 260 px edge band is
   77–402 px, and the few larger hits are still under 35 % of a sheet
   dimension (rail lines and frontage rules, not neat lines). Left
   uncorrected, the bogus frame estimate clamped the vertical seam cuts to
   **+6…+61 px** past the corridor line, so both sheets' copies of the
   avenue name rendered.

3. **Clip insets at the corridor far kerb.** Three earlier criteria were
   tried and rejected against the picture: the paper bound let sheet 7's
   torn margin render as a blank strip down Avenue D; "last ink" counted
   the printed SEE SHEET marginalia as content and put sheet 8's margin
   note into the Avenue G corridor; "last long line" would have clipped at
   the kerb, leaving the roadway drawn by neither sheet. Final rule:
   centreline ± 110 px, half the drawn corridor measured on the interior
   avenues (204–213 px kerb to kerb).

4. **Wharf ownership.** The wharf sheets take deliberately large right-side
   insets (740 / 601 px) so the downtown sheets own everything east of the
   Avenue A corridor — the wharf sheets only trace those blocks in outline
   while the downtown sheets survey them. Everything west of Avenue A —
   blocks 739–744, Morgan and Brick Wharves, the Central Line warehouses,
   the Navigation Slip and the basins — is drawn only by the wharf sheets
   and is kept in full.

5. **Landmark-solved placement.** See Verification.

## Verification — the anti-circular gate

Fit residuals cannot establish alignment: a uniform per-sheet error is
absorbed by the translation term. The gate instead measures **35
ground-truth landmarks** — one physical object located on both sheets of a
pair, in each sheet's native pixels — mapped through the build's own
transforms.

Weighted by measurement quality: least-squares line crossings 1.5, block
corners 1.0, hydrant **discs** 0.5. The discs are hand-placed symbols, not
survey points — the same disc sits 43 px above the water main on one sheet
and 67 px above it on the other, so they carry ~±25 px of irreducible
drafting slop.

**Result, before → after the landmark solve:**

| | before | after |
|---|---|---|
| median landmark step | 119.2 px | **13.7 px** |
| max | 543.4 px | 106.3 px |
| wharf pair 02\|07 mean dx | −515 px | **−1.6 px** |
| wharf pair 01\|09 mean dx | −382 px | **−3.5 px** |
| 07\|08 mean | (+173, −76) | **(0.0, 0.0)** |

Every unit had registered "ok" with clean residuals while the wharf sheets
sat half an avenue out of place. Each wharf sheet carries a single avenue
line, so nothing in the fit could see it. This is the circularity lesson
made concrete for a second edition.

Per-pair means after the solve: 01|09 (−3.5, −17.4), 02|07 (−1.6, +1.5),
07|08 (0.0, 0.0), 07|09 (+0.5, −5.0), 08|10 (+2.8, +7.3), 29|27 (−0.5,
+8.8).

## Colour

Each scan's illumination field is flattened to the edition's aged-cream
tone before compositing, then the printed washes render as scanned (no
per-sheet white balance). Measured uniformity in the delivered composite:
sheet columns agree within **4 levels**, street bands within **2**, and
wharf-to-downtown within **6**.

Galveston Bay and the slips are filled flat at the atlas's own printed
waterline tone (BGR 188, 202, 198, the median of the shoreline edging
strips), with ink blended back through a smoothstep so lettering keeps
clean edges. This is the single deliberate stylization; the originals print
open water as blank paper.

## Disclosures

- Source coverage of the delivered frame is **92.06 %**. The shortfall is
  almost entirely the **south-west bay quadrant**: sheet 2 (19th–22nd) draws
  far more of Galveston Bay than sheet 1 (22nd–25th) does, so that water is
  not mapped at this frame width. It is left as flat paper and is **not**
  tinted — presenting unmapped ground as surveyed water would be a
  fabrication. Uncovered canvas is repainted to the composite's own paper
  median so it reads as blank paper rather than as a grey block; no content
  is added.
- **"AV. D OR MARKET E." renders twice** at the 7|8 seam, and similarly at
  the other avenue seams. Unlike 1899, these sheets *abut* rather than
  overlap: each draws its own half of the corridor and letters it. No cut
  drops one copy without opening a gap in the roadway, so both authentic
  copies render — the same class as the duplicated compass roses.
- Stray sheet-reference numerals ("7", "8") print inside the map body on the
  originals and render where the original prints them.
- **Residual scatter is rotational.** Pair spreads run 5–99 px and vary
  *smoothly and monotonically* along each shared corridor — relative
  rotation and ~1–1.5 % scale, not bad correspondences. The separable
  piecewise warp cannot express rotation; this is the one genuine rebuild
  item, unchanged from 1899.
- Sheet 1's top-edge 22nd Street pipework is drawn 60–90 px out of place
  against block corners **on its own sheet** — decoration, not survey. That
  landmark is weighted zero and flagged.
- No map content anywhere is generated, inferred, or cloned.

## Output

| File | Size |
|---|---|
| `galveston_1889_downtown_wharf.png` | 10985 × 7370 px master |
| `Galveston_1889_Wharf_Downtown_40x27.pdf` | map 36.62 × 24.57 in at 300 dpi |
| `Galveston_1889_Wharf_Downtown_36x24.pdf` | map 32.49 × 21.80 in at 338 dpi |

Guard metrics: coverage 92.06 %, pure-white 3 px, pure-black 0.0018 %.
