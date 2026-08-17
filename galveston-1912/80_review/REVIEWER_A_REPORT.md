# Reviewer A — Independent Adversarial Review
**Object:** `60_master/final/master_full.tif` (26206x14489 RGB) and `deliverables/Galveston_1912_Wharf_Downtown_print.jpg` (12000x7828)
**Date:** 2026-08-17
**Ground truth used:** archival 1912 scans only (`/home/user/g1912/data-branch/galveston_1912_sources/`): key map (img004), plates img009/011/013/015/017/019/021/049/050/053/054/059/060 (= sheets 5, 7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50). No solver/QA/control/decision files were read; the render manifests next to the master were also deliberately not read. All expected-layout claims below were derived from the key map, the plates' own margin "reference to adjoining sheet" numerals, block numbers, street names, address runs, and pier numbers.
**Evidence crops:** `80_review/evidence_A/` (ev0-ev9). Coordinates below are master_full.tif pixels (x right, y down) unless marked "orig".

---

## Derived expected layout (independent)

From key map img004 (sheet numerals on shaded block groups) and confirmed by each plate's margin references:

| Streets \ Avenues | wharf strip | wharf blks + A(Water)-C(Mechanic) | C(Mechanic)-F(Church) | F(Church)-I(Sealy) | I(Sealy)-L |
|---|---|---|---|---|---|
| 18th-21st (Center) | sheet 5 | **7** (738-740/678-680/618-620) | **8** (558-560/498-500/438-440) | **39** (378-380/318-320/258-260) | **40** (198-200/138-140/78-80) |
| 21st-24th | sheet 5 | **9** (741-743/681-683/621-623) | **10** (561-563/501-503/441-443) | **43** (381-383/321-323/261-263) | **44** |
| 24th-27th | sheet 5 | **11** (744-746/684-686/624-626) | **12** (564-566/504-506/444-446) | **49** (384-386/324-326/264-266) | **50** |

Sheet 5 (100 ft/in) is the wharf/pier strip in two panels: A = piers 17-22 (16th-22nd), B = piers 22-28 (22nd-28th). Margin references verified on the plates themselves (e.g., 39 prints 35/43/40 at its 18th/21st/Sealy margins; 40 prints 36/44/39/41). The mosaic's arrangement **matches this derivation everywhere**; landmark content confirms every cell (Court House in 319, Central Park 320, St Mary Cathedral 380, Ball High School 321, Rosenberg Library 263 at 2310 Sealy, Grand Opera House 500, City Hall & Market at 20th, Union Depot property, Panama Hotel "being built" in 624, etc.). Mosaic extent: 19th St (top) to ~1/3 block past 25th/Rosenberg (bottom); wharf to a sliver past Sealy (blocks 9xx of sheets 40/44/50).

---

## FINDINGS

### F1 — CRITICAL: Eastern two-thirds of the Mallory Steamship terminal shed (Piers 23-25) erased and patched with matching fills
- **Mosaic:** kept west band x≈7220-7520; **erased zone x≈7600-8300, y≈9750-14390** (≈110 ft x 740 ft of ground). Above the 24th-St seam (y 9756-11710) the erased zone is filled with **flat shed-yellow**; below it (y 11710-14390) with **flat paper-cream**. Track yard resumes correctly at x≈8280 (sheets 9/11).
- **Original:** sheet 5 (img009), right panel, x≈4994-5540, y≈1560-3900: the Galveston Wharf Company's Shed runs *continuously* from Pier 23 past Pier 25 with three interior text lines, partitions, hydrants and an office.
- **Content lost:** the building's identity line "**MALLORY STEAMSHIP CO. LESSEE & OWNER OF BUILDING**", the watchman note "REPORT TO A.D.T. 7 STATIONS, HOURLY ROUNDS - & PAILS DISTRIBUTED", "OFFICE 2", HYD. 50' 2 1/2" HOSE symbols, interior partition/fire-division lines, the Pier-23 end wall. For a fire-insurance map this is the substance of the wharf front's principal terminal.
- **Measured:** ink fraction mosaic vs original over the same ground - 23rd-24th: **0.66% vs 5.97%**; 24th-25.5th: **1.13% vs 10.82%** (kept west band: 2.14% vs 1.96% and 8.06% vs 8.85% - parity). Control (track yard 23-24): 8.0% vs 16.2%, explained by sheets 9/11's legitimately sparser yard rendering (verified real content present).
- **Visible symptom:** at the 24th seam (y=11710) the shed's drawn width jumps discontinuously from 1055 px to 295 px; the original shows a continuous, gently tapering building through Pier 24.
- **Evidence:** ev1, ev2. **Confidence: very high** (side-by-side + ink statistics + exact ground mapping via x2 anchors: shed west edge 7220↔orig 4994, Pier 24 label 11670↔orig 2540, Pier 25 14000↔3730).

### F2 — MAJOR: East wedge of the J. Merrow & Co (Galveston Wharf Co) shed amputated by a straight clip at the 5|9 junction
- **Mosaic:** the wharf strip is clipped along a razor-straight vertical line **x≈7473, y≈4700-6700** (21st-22nd). East of the line the mosaic shows sheet 9's *empty plate margin* (compass rose, archival stain wedge). The shed's big text line now dead-ends: "...WHARF **COMPANY'S**" — the final word "**SHED**" and the shed's slanted east wall, the adjoining "PLATFORM"-dash strip, and up to ≈95 ft of shed width at the 22nd-St end are gone.
- **Original:** sheet 5 (img009), left panel, x≈1850-2600, y≈5650-6750: shed east edge slants to x≈2580 (maps to mosaic ≈8050); text ends "...COMPANY'S SHED"; "IRON CLAD" south wall spans the full ≈190 ft width (mosaic keeps ≈90 ft).
- Sheet 9 never draws this ground (it is beyond its coverage), so this is a deletion of **sole-source content**, not a plate-disagreement adjudication. Above 21st the same clip is harmless because plate 7's own west margin drawing (Fish Comm's Off., track fans) covers the ground.
- **Evidence:** ev3, ev9. **Confidence: high.**

### F3 — MINOR: Fabricated adjoining-sheet numerals in the Sealy corridor (seam-composited digits)
- At **(x≈25910-26075, y≈1330-1480)** the Sealy corridor between blocks 259|199 (19th-20th) displays a large outline "**49**". The originals print "**40**" there (sheet 39's right-margin reference) and "**39**" (sheet 40's left-margin reference). The seam slices between the digit pairs "4|0" and "3|9", keeping 39's "4" and 40's "9" — manufacturing a reference to sheet 49, which in the real 1912 edition lies two street-bands south. The duplicated "AVE. I OR"/"AVE." text fragments at the same spot betray the seam. A reader using the Sanborn convention (key legend: outline numeral = reference to adjoining sheet) is sent to the wrong plate.
- Same mechanism at **(x≈25900-26075, y≈8150-8350)**: composite of "4|4"+"4|3" reads "43" beside plate 43's own ground (self-referential nonsense; the sheet across Sealy is 44).
- Ground content across both seams is correct (address runs 1902-1928/1901-1927 and 2206-2224/2205-2223 continue perfectly), so this is documentary, not geometric.
- **Evidence:** ev4, ev5. **Confidence: very high.**

### F4 — MINOR: "24TH ST." name labels obliterated mosaic-wide by the horizontal seam routed through the label line
- The 9/10/43 | 11/12/49 seam (y≈11710) runs through the corridor text. Surviving fragments are illegible ghosts at Water (x≈10650) and Market (x≈16450); nothing at Winnie/Ball (x 20300-23300). 24th Street itself is geometrically intact with perfect address continuity (evens 402-424 / odds 401-423 at Market, etc.), but its name is effectively unreadable anywhere on the 26k-px-wide sheet. The 21st/Center corridor by contrast retains legible labels.
- **Evidence:** ev6. **Confidence: high.**

### F5 — NOTE: Cosmetic patchwork at the wharf strip
- Differential toning across the 24th seam: the strip above is brightened (shed fill mean RGB ≈ 179/168/135) while below it retains dark archival toning (≈163/151/92) — a visible tone step on the same building, and a contradiction of the print caption's "original colors retained".
- A stained tan wedge from sheet 5's right-panel margin is pasted with straight clip edges at (x≈7450-7935, y≈4960-5940), partially underlapping sheet 9's compass rose; featureless lavender filler west of the shed (x≈5800-7440, y≈7790-11800) where the original quay/water area is white/blue.
- **Evidence:** ev9, ev2. Confidence: high.

### F6 — NOTE: Print deliverable
- The print JPG is a faithful crop+resample of the master: declared window (3556,0)-(26206,14489) at scale 0.52151 verified (alignment 0.995; mean |gray diff| 1.66 over 25 windows = JPEG-level). Caption sheet list matches my derivation. It therefore **inherits F1-F5**; caption claims "original colors retained; plate disagreements preserved" are contradicted by F5 and by F1/F2 (sole-source wharf content deleted, not preserved).

---

## Tested and found sound (near-misses and non-findings)

- **Sheet identity/arrangement:** all 13 sheets in their derived cells; no swap, no one-block-off placement. Landmarks verified per cell against the plates.
- **Street continuity and address runs at every interior seam:** Mechanic (7|8, 9|10, 11|12), Church (8|39, 10|43, 12|49), Sealy (39|40, 43|44, 49|50), 21st/Center (7|9, 8|10, 39|43), 24th (9|11, 10|12, 43|49) — names AND hundred-blocks continue correctly (19xx/20xx/21xx/22xx/23xx/24xx bands; 100/200/.../800/900 cross-street blocks; opposite parity on opposite frontages everywhere checked at native resolution).
- **Block-number sequences across seams:** columns 73x-74x/67x-68x/61x-62x/55x-56x/49x-50x/43x-44x/37x-38x/31x-32x/25x-26x/19x-20x all increment correctly across the 21st and 24th seams.
- **Geometric registration:** strip cross-correlation across every seam shows offsets ≤ ~10 px except two pockets: Mechanic seam at y 7244-11873 (-15 to -24 px ≈ 4 ft) and the Sealy sliver y 4929-14188 (-23 to -31 px). No rotation trend. MINOR wobble, below reporting threshold on its own.
- **Scale consistency:** sheet 5 strip upscaled x1.98-2.00 (mosaic scale bar 0-300 ft = 1820 px = 6.07 px/ft vs original 918 px; downtown block pitch ≈ 6.1 px/ft). Same drafted block widths match across seams.
- **Wharf coherence:** piers 19-25 strictly sequential, each near its street foot (Pier 22 label y≈7340 vs 22nd ≈7000; Pier 24 ≈11670 vs 24th ≈11550; Pier 25 ≈14000 vs 25th ≈13700); no duplicated Pier 22 despite both sheet-5 panels drawing it (right panel's label correctly clipped); slip topology at the panel switch intact; track numbering rows (evens above/odds below 24th) are the originals' own alternating label rows, correctly joined.
- **Blank-region sweep (whole mosaic):** all other low-ink regions correspond to genuinely open ground on the originals (Ball High School yard 321, Court House lawn 319, Central Park 320, Union Depot "to be built" property, bay water). A uniform-color-patch sweep found **only** the F1 fills (plus the F5 stain wedge).
- **No mirrored/rotated plates; no duplicated or missing streets** (19th-25th all present once; avenues Water-Sealy all present once, plus the Sealy-L sliver).

## Verdict

The reconstruction's plate identification, arrangement, registration and scaling are sound — but the wharf front, the deliverable's title feature, fails integrity review. The map content of the Galveston Wharf Company's Mallory Steamship terminal (Piers 23-25) has been ~90% erased over a ~110 ft x 740 ft swath and silently patched with shed-colored and paper-colored fills (F1), with a smaller sole-source deletion at the J. Merrow shed (F2). These are not preserved "plate disagreements"; they delete the only 1912 source's testimony while leaving a plausible-looking building footprint — the most dangerous kind of error for a historical document. Additionally, seam-composited marginal numerals fabricate a false adjoining-sheet reference "49" (F3), and 24th Street's name is unreadable mosaic-wide (F4).

**Recommendation: do not release.** Re-composite the wharf strip between 23rd St and the south edge from sheet 5 panel B with the full shed complex (orig x 4994-5540, y 1560-3900), move the 5|9 clip line east of the J. Merrow shed's true east wall (orig x≤2600), re-blend the Sealy corridor to keep exactly one plate's marginal numerals, and restore a legible "24TH ST." label.
