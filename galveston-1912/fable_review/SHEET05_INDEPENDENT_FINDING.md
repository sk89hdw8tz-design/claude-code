# Sheet 5 (Galveston 1912 Sanborn, wharf front) — Independent Finding

**Reviewer:** independent historical-cartography review (Fable review workspace)
**Source examined:** `/home/user/g1912/data-branch/galveston_1912_sources/sanborn08539_004_img009_archival.jp2` (6653 x 7795 px, read-only), plus key map `img004`, index `img001`, special plates `img002`/`img003`. All coordinates below are **full-resolution source pixels** of `img009` (x right, y down) measured from 1:1 crops with drawn pixel rulers; evidence crops in `evidence/sheet05/`.
**Plate scale:** "Scale 100 Ft. to One Inch"; measured 100 ft = ~309 px (scale bar 0-tick x=735 to 300-tick x=1660 at y=7265; crop 24).
**Page orientation:** the drafted text reads normally in the scan orientation — the plate is NOT rotated 90 deg in the scan. The *geography* is rotated: compass rose at (3990,5180) carries "E" at its top spoke and "S" at the lower-right needle end (crop 23), so **page-left = north (Galveston Bay), page-down = west (increasing street numbers), page-up = east**. This corrects the prior "plate drafted rotated 90 degrees within the scanned page" note: the *drawing content* is rotated relative to geographic north, but labels are upright in the scan.

## VERDICT: CONFIRMED MULTI-REGION (two panels)

Sheet 5 is one physical page carrying **two separately drafted panels of one continuous east-west wharf frontage**, laid side by side to fit the page. The panels are separated by a drafted heavy rule; the frontage continues from the bottom of the left (east) panel to the top of the right (west) panel, with **Pier 22 drawn twice** (once per panel) as the continuation overlap.

---

## Answers

### 1. Does Sheet 5 contain two or more geographically distinct or differently oriented map strips?
**Yes — exactly two strips (panels), same orientation, geographically consecutive (not overlapping except at Pier 22 / 22nd St).**
- **Panel A (page-left/east panel):** Piers 17-22 top-to-bottom, labels read at 1:1: PIER 17 (384,1016), 18 (744,2040), 19 (1120,3520), 20 (1304,5056), 21 (1656,6520), 22 (1900,7280) — crop 13 (montage). Landward column with 16th-22nd St stubs, "Ave. A or Water", "Galveston Wharf Company's Terminal Tracks & Yard".
- **Panel B (page-right/west panel):** Piers 22-28 top-to-bottom: PIER 22 (4560,360), 23 (4720,1624), 24 (4688,2544), 25 (4688,3696), 26 (4504,5064), 27 (4288,6160), 28 (4120,7200) — crop 13. Landward margin at far right with 22nd (y~230), 23rd/Tremont (~1400), 24th (~2530), 25th/Rosenberg (~3715), 26th (~5000), 27th (~6150), 28th (~7290) and its own "Ave. A or Water" label (crops 19-22).
- Both panels are drafted with the bay to page-left and land to page-right (duplicate "Galveston Bay" water texts and duplicate "Ave. A or Water" labels — one per panel). Each panel carries its own corner plate numeral "5": (5240,230) top of Panel B, (2860,7560) bottom of Panel A, besides the title "5" at (170,600) (crops 04, 25, 26).
- **Same orientation** for both panels (single compass rose serves both). The prior grid-concentration anomaly (0.454) is explained by the diagonal piers/slips/tracks, not by differently rotated panels.

### 2. Where is the drafted-content break?
A **heavy solid rule ~22 px wide, flanked by thin parallel lines** (triple-line panel border), running the full page height with a slight lean (~0.5 deg). Measured centerline (numpy dark-run scan at 500 px steps, crop 16/17/18):

| y | x (centerline) |
|------|------|
| 100 | 3790 |
| 1600 | 3813 |
| 3100 | 3833 |
| 4600 | 3848 |
| 6100 | 3861 |
| 7600 | ~3860-3866 |

Linear form: **x ≈ 3789 + 0.0099·y** (i.e., from (3789,0) to (3866,7795)). It is interrupted only where the compass rose arm crosses near y=5100. Full polyline in the GeoJSON feature `BREAK_RULE`.
- Left of the rule: Panel A's landward sliver (Ave A at x~3480-3650, outline block fronts to x~3770).
- Right of the rule: **blank paper**, then Panel B's bay tint and "Galveston Bay" lettering from x~4200 (crop 17). The blank gap narrows near the bottom, where Panel B's Pier 28 approaches the rule at x~3900 (crop 18).

### 3. Is the break a physical page boundary, a cartographic panel division, or merely a change in shoreline direction?
**A cartographic panel division.** It is a drafted ink rule mid-page (not a page edge — the physical page edges are at x~30/6600 with binding tape visible), and it is not a shoreline: water tint and drafted content stop on both sides with blank paper between; the same shoreline continues from Panel A bottom to Panel B top (Pier 22 duplicated, crops 14/15). It is precisely the left panel's landward border rule, doubling as the divider.

### 4. Which portion adjoins Sheet 9?
**Both panels adjoin Sheet 9 (21st-24th), because the panel break at 22nd St falls inside Sheet 9's range:**
- Panel A: boxed/large "9" at **(3290,6320)** in the landward column between 21st-or-Center St (y~6080) and 22nd St (y~7160) — crop 08. Pixel region: Panel A landward edge, approx x 2700-3789, y 5900-7300.
- Panel B: boxed "9" at **(6460,1560)** on the right margin beside "23rd or Tremont St." (y~1400) — crop 09. Pixel region: Panel B landward margin, approx x 6300-6653, y 200-2500 (22nd to 24th).

### 5. Which portion adjoins Sheet 11?
**Panel B only.** Boxed "11" at **(6440,4390)** on the right margin, beside the "Ave. A" / "Gulf Colorado [& Santa Fe]" lettering, between 24th (y~2530) and 26th (y~5000) — crop 10. Pixel region: Panel B landward margin, approx x 6300-6653, y 2530-5000 (24th-26th; Sheet 11 = 24th-27th).

### 6. Which portion adjoins Sheet 13?
**Panel B only**, on sheet 5's own edge evidence: "13" at **(6460,6830)** on the right margin between 27th (y~6150) and 28th (y~7290) — crop 11; and a second "13" at **(5990,7540)** on the bottom (west) edge — crop 12. Pixel region: Panel B, x 5800-6653, y 6150-7795. **Evidence gap:** Sheet 13 itself is not on disk, so the reciprocal edge cannot be checked; the claim rests on sheet 5's printed references plus the key map (img004), whose band layout (13 = 27th-30th on Water/Strand) is consistent. Also on the bottom edge: **"4" at (4830,7550)** — Sheet 4 (Piers 29-32 per the index) continues the wharf frontage west, and "6" at **(1740,220)** on the top edge — Sheet 6 (Piers 10-15) continues it east; "33" at **(2980,1420)** adjoins Panel A landward at 17th (Sheet 33 = Water/Strand blocks 16th-18th on the key map).

### 7. Can the physical scan be fitted as ONE similarity transform without violating historical topology?
**No — structurally impossible, regardless of residuals.** The two panels are parallel page-neighbours but geographic *successors*: Panel B's ground lies entirely WEST of Panel A's, continuing beyond Panel A's bottom edge. Concretely:
- **Pier 22 is drawn twice**: at (1900,7280) in Panel A and (4560,360) in Panel B — 7,414 px apart on paper. At the plate scale (309 px = 100 ft) a single similarity transform would place the two depictions of the *same pier* ~**2,400 ft apart** (about 6.5 city blocks), or equivalently force at least one depiction ~2,400 ft off its true position.
- **22nd St appears twice** (Panel A landward column y~7160; Panel B right margin y~230), as does "Ave. A or Water" and the "Galveston Bay" water body.
- A low-residual rigid fit could only be achieved by fitting *one* panel and letting the other panel's control points be discarded/ignored — i.e., low residuals would be an artifact of control selection, not evidence of validity. Any fit that treats the full page as one frame duplicates the harbourfront into two parallel offset copies, which is historically false topology.

### 8. If not, how many logical regions are required?
**Two** (Panel A, Panel B), each with its own similarity/affine transform. Within each panel the content is a single continuously drafted strip (no further internal rules, no pier-sequence jumps, single orientation), so two is sufficient as well as necessary. The two transforms should be near-identical in rotation/scale and differ essentially by translation (both panels share drafting orientation); the Pier 22 / 22nd St duplication provides the cross-panel consistency check.

### 9. What source-pixel ranges or polygons define those regions?
See `sheet05_candidate_regions.geojson`. Summary:
- **Region A** (confidence 0.9): polygon [(0,0), (3789,0), (3866,7795), (0,7795)] — everything left of the break-rule centerline. Piers 16/17-22, 16th-22nd St.
- **Region B** (confidence 0.9): polygon [(3789,0), (6653,0), (6653,7795), (3866,7795)] — everything right of the rule. Piers 22-28, 22nd-28th St.
- **BREAK_RULE** (confidence 0.95): measured polyline (3789,0)...(3866,7795), the shared boundary.
The only ambiguity is ownership of the ~22 px rule itself and the blank gap (bay-side of Panel B) — cartographically dead space, so the exact split line does not affect georeferencing. Confidence 0.9 rather than 1.0 only because the rule is interrupted at the compass crossing (y~5100) and the bottom 200 px where Pier 28 crowds the gap.

### 10. What independent controls could determine each region's transform?
Named drafted features verified at 1:1 on this plate (all usable against the landward sheets 7/9/11/13, the key map, or city plats — no water mains/hydrants):

**Region A:**
- Cross-street/Ave A intersections: 16th St (x~3120, y~240), 17th (y~1420), 18th (y~2560), 19th (y~3730), 20th (y~4860), **21st-or-Center St** (label at (3900,6080)), 22nd (y~7160) — each reaches Ave A or Water and appears on the landward neighbour sheets.
- Pier heads with numbers: Piers 17-22 (coordinates in answer 1) and the named slips between them.
- Named premises: "Wm Parr & Co" (~(1150,780)), "E. O. Flood & Co, Lessee" (~(1700,650)), "Galveston Wharf Company's Shed / Anderson & Co Lessee" (Pier 20/21 area), "Galveston Wharf Co's Shed / Gulf Fishery Co. Lessee" (Pier 22, (2100,7100)).
- Rail: "Galveston Wharf Company's Terminal Tracks & Yard" (vertical label x~2480) and the track fans converging at 21st-22nd.

**Region B:**
- Cross-street/Ave A intersections on the right margin: 22nd (y~230), **23rd or Tremont** (y~1400), 24th (y~2530), **25th or Rosenberg Av.** (y~3715), 26th (y~5000), 27th (y~6150), 28th (y~7290).
- Pier heads with numbers: Piers 22-28 (coordinates in answer 1); slips flanking Piers 22, 27-28.
- Named premises: "Galveston Wharf Company's Shed / **Mallory Steamship Co. Lessee** & owner of building" (large shed, Piers 23-26, x~4900-5400, y~2100-6000); "Galveston Wharf Company's Shed / **Sykes Bros** Lessee" (Pier 27, (4600,5600)).
- Rail: "**Gulf, Colorado & Santa Fe**" lettering along the margin (~(6320,3900)); "Galveston Wharf Company's Terminal Tracks & Yard" (right-of-centre, x~5900); track junctions at 25th-26th.
- Cross-panel consistency (not an absolute control): the duplicated Pier 22 shed outline and slip must land on the same ground coordinates under both transforms.

### 11. Is any part of Sheet 5 outside the target footprint (Piers 19-25 / 19th-25th St)?
**Yes, substantial parts of both panels:**
- **Region A, approx y < 3000** (GeoJSON `A_out_of_target`, confidence 0.6 on the exact cut): Piers 17 & 18, their slips and sheds, and the 16th-18th St landward strip (adjoins sheets 6 and 33). Pier 19 (label y=3520) and 19th St (landward y~3730) mark the start of the target.
- **Region B, approx y > 4450** (GeoJSON `B_out_of_target`, confidence 0.6): Piers 26, 27, 28, the Sykes Bros shed, and the 26th-28th St landward strip (adjoins 13 and 4). Pier 25 (label y=3696) / 25th-or-Rosenberg (y~3715) end the target.
- The target footprint itself spans the panel break: Piers 19-22 live in Region A, Piers 22-25 in Region B — **the mosaic target cannot be served by either panel alone.**

### 12. Do the congested-business-district plates (img002/img003) or any other special plate in hand cover any of this waterfront ground more authoritatively?
**No — checked both.**
- **img002** "Map of Congested District of Galveston, Tex., 1912, scale 200 ft to an inch": covers 15th-27th St from the bay to Ave J/Broadway, including a *generalized* wharf front (piers as outlines, no per-building detail) along its left edge. Half the scale of sheet 5 (200 vs 100 ft/inch), so **less** authoritative for detail — but it depicts sheet 5's entire frontage **continuously in a single drawing**, making it a valuable independent topology/geometry control for stitching Regions A and B (crop 29).
- **img003** "Cotton Compress & Warehouse District, also part of wharf front, 1912, 200 ft/inch": covers the wharf front and warehouse district **west of ~28th St** (sheets 3/4 territory, Piers 29+). No overlap with Piers 16-28 (crop 30).
- Key map img004 and index img001 corroborate but do not map the ground in detail.

---

## Evidence chain (crops in `evidence/sheet05/`)
1. `01` annotated overview: two-panel interpretation, break rule, all adjoining refs, Pier 22 duplication.
2. `02` key map: single continuous grey band "5" from Pier No. 16 to Pier No. 28; "6" ends at Pier 15 east, "4" begins at Pier 29 west; landward bands 33/34, 7, 9, 11, 13. `03` index PIERS table at 1:1: "Piers 16 to 28 inclusive — 5".
3. `04`-`12` every adjoining-sheet reference at 1:1 with coordinates (6, 33, 7, 9, 9, 11, 13, 13, 4).
4. `13` pier-number sequence montage at 1:1 (17-22 then 22-28). `14`/`15` the duplicated Pier 22.
5. `16`-`18` the break rule at 1:1, top/middle/bottom, showing blank paper both sides at mid-page and Panel B's bay text beginning right of it.
6. `19`-`22` Panel B's landward street stubs (22nd, 24th, 25th/Rosenberg, 28th). `23` compass. `24` scale bar. `25`/`26` per-panel "5" numerals. `27` Panel A top edge (no Pier 16 drawn). `28` Mallory shed. `29`/`30` special-plate checks.

## Contradictions / corrections to the project's working hypothesis
1. **Panel relationship is east/west, not north/south.** The hypothesis said the "left half belongs north of / above the right half". In fact both panels have north to page-left; the left (A) panel's ground lies **EAST** of the right (B) panel's, and B continues the frontage **westward** from A's bottom edge. In page terms the continuation is bottom-of-A → top-of-B (not left-above-right).
2. **The plate is not rotated 90 deg in the scan.** All lettering is upright in scan orientation; only geographic north is rotated (to page-left). Any pipeline step that pre-rotates sheet 5 by 90 deg based on the page-detector aspect ratio would be wrong.
3. **The break is NOT at the physical page midpoint** — confirmed as hypothesized: it is at x≈3789-3866 (~57-58% of page width), drafted as a rule.
4. **Prior reading "9, 11, 13 in sequence (with 7 expected)" on 'the landward edge' conflates two different edges.** 9/11/13 are on Panel B's right margin; 7 (and 33, and a second 9) are on Panel A's landward column mid-page. Sheet 9 adjoins BOTH panels; sheet 7 adjoins only Panel A.
5. The 1912 index's "Piers 16-28" is verified, but **Pier 16 itself is not drawn** on the plate — Panel A starts at the slip east of Pier 17 (Pier 16 sits on sheet 6's ground per the key map, despite the index attribution).

## Classification
**CONFIRMED MULTI-REGION** — two panels, boundary measured, continuation topology proven by the duplicated Pier 22, duplicated 22nd St, duplicated "Ave. A or Water"/"Galveston Bay" annotations, per-panel plate numerals, and the key map's single continuous band.
