# Galveston Sanborn Map Composite — Claude Code Build Spec

Rebuild, from scratch, seamless high-resolution composites of the Sanborn Fire
Insurance Maps of Galveston, Texas (1885 and 1877), centered on the intersection
of **22nd Street and Postoffice Street**.

This spec encodes findings from a completed manual run. **Everything in
"Established Facts" was verified against the actual scans — trust it, but
re-verify anything marked `[VERIFY]`.** Sections marked **HARD-WON** are
mistakes already paid for; do not repeat them.

---

## 0. Success Criteria

The build is done when all of the following are true:

1. A single stitched composite exists per year, at native source resolution,
   with no invented content.
2. Street and block lines connect across every sheet seam; no duplicated street
   labels; no sheet margin material (title cartouches, scale bars, "See Sheet
   No. x" *margin* notes) inside the artwork.
3. Deliverables open and zoom sharply **on the target device** (see §9 — ask the
   user what device before choosing formats).
4. Three independent QC passes have run and signed off (§8).
5. A production report documents sources, sheets used, sheets excluded with
   reasons, gaps, and confirmation that no generative fill was used.

---

## 1. Agent Topology

Run as an orchestrator plus specialist subagents. Suggested model assignment:

| Agent | Role | Model | Why |
|---|---|---|---|
| **Orchestrator** | Plans, sequences, adjudicates QC disputes, owns the report | Opus 5, high reasoning effort | Judgment and cross-checking |
| **A1 Acquisition** | Source discovery, API probing, downloads, checksums | Haiku 4.5 or Sonnet 5 | Mechanical, I/O-bound |
| **A2 Cartography** | Sheet identification, coverage tables, street naming, panel analysis | Opus 5, high effort | Needs visual reading + reasoning |
| **A3 Registration** | Grid detection, control points, affine fits | Fable 5 (highest effort available) | Dense numerical code |
| **A4 Compositing** | Warping, clipping, blending, memory-tiled canvas | Fable 5 (highest effort available) | Performance-critical code |
| **A5 Output** | Format conversion, packaging, metadata | Sonnet 5 | Straightforward |
| **A6 Reviewer** | Independent QC, runs 3× (§8) | Opus 5, high effort | Must be adversarial |

**A6 must not be the same context as A3/A4.** A reviewer that wrote the code
will rationalize its own output. Give A6 only the artifacts and the criteria.

Parallelize A1 downloads. Serialize A2 → A3 → A4. Run A6 after A4 and again
after A5.

---

## 2. Established Facts — Sources

### 2.1 Source ranking (VERIFIED)

| Source | Resolution/sheet | Editions | Access | Verdict |
|---|---|---|---|---|
| **Library of Congress** | **6450 × 7650** (~307 dpi of original) | 1885, 1889, 1899, 1912, 1948, 1950 | Open, no login | **PRIMARY for 1885** |
| UT Perry-Castañeda | 3400 × 4124 (~162 dpi) | 1877, 1885, 1889, 1899, 1912, 1918, 1923, 1947 | Open, flaky TLS | **ONLY source for 1877** |
| Portal to Texas History | unknown | many | **ALTCHA proof-of-work gate** | **DO NOT circumvent** |

**LoC has no 1877 Galveston edition.** 1877 must come from UT at 3400 px. This
is a hard ceiling — do not promise 300-ppi output above ~15 × 22.5 in for 1877.

### 2.2 LoC access patterns (VERIFIED WORKING)

```
# REQUIRED: browser User-Agent, or the API returns non-JSON and json.load fails
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

# Item metadata (1885 Galveston = sanborn08539_001)
https://www.loc.gov/item/sanborn08539_001/?fo=json
  -> d['resources'][0]['files'] = list of sheets, each a list of variants
     with .mimetype / .width / .height / .url

# Master TIFF (142 MB each, uncompressed, 6450x7650)
https://tile.loc.gov/storage-services/master/gmd/gmd403m/g4034m/g4034gm/
  g4034gm_g085391885/08539_1885-NNNN.tif        # NNNN = 0002, 0006, 0014...

# IIIF region tiles (for deep-zoom viewers; returns 200 + valid JPEG)
https://tile.loc.gov/image-services/iiif/service:gmd:gmd403m:g4034m:g4034gm:
  g4034gm_g085391885:08539_1885-NNNN/{x},{y},{w},{h}/{outw},/0/default.jpg
```

**LoC file numbers map 1:1 to printed sheet numbers** — `08539_1885-0006.tif`
is printed Sheet 6. `[VERIFY]` visually on one sheet before trusting for all.

### 2.3 UT access patterns (VERIFIED WORKING)

```
Index:    https://maps.lib.utexas.edu/maps/sanborn/g.html
Sheets:   https://maps.lib.utexas.edu/maps/sanborn/g-i/txu-sanborn-galveston-YYYY-NN.jpg
```

**HARD-WON:** UT returns intermittent HTTP 503 from an F5 BIG-IP bot defense
(`TSPD_101_R0` cookies, 307 redirects). Fix: use a cookie jar (`curl -c/-b`),
send a `Referer` of the g.html page, and retry up to 10× with 5 s sleeps.
It succeeds — often on try 2–6. Plain HTTP 200 on first try is not guaranteed.

### 2.4 Ethics constraint (NON-NEGOTIABLE)

Do **not** solve the ALTCHA proof-of-work on texashistory.unt.edu. Honoring
cookies and following redirects is normal HTTP client behavior and is fine;
computing a PoW solution to defeat an anti-automation gate is not. If a source
is gated, report it and use an alternative.

---

## 3. Established Facts — Galveston Cartography

### 3.1 Street naming (VERIFIED from the sheets themselves)

Avenues run one direction, numbered streets cross them. Index them A=0 … J=9.

| Ave | Also called | | Street | Also called |
|---|---|---|---|---|
| A | Water | | 21st | **Centre** (1877 only) |
| B | Strand | | 23rd | Tremont |
| C | Mechanic | | 25th | Bath Ave |
| D | Market | | | |
| **E** | **Postoffice** ← target | | | |
| F | Church | | | |
| G | Winnie / Menard | | | |
| H | Williams | | | |
| I | McKinney | | | |
| J | Broadway | | | |

- **25th Street is the East/West address divide.** Labels switch from
  "Market E." to "Market W." there. Useful for validating sheet identity.
- Target intersection = **Avenue E × 22nd Street**.

### 3.2 Block pitch (VERIFIED)

| Scale | Avenue pitch | Street pitch |
|---|---|---|
| 3400 px detection scale (UT native) | **972 px** | **1135 px** |
| 6450 px LoC master scale | **1856 px** | **2170 px** |

Pitch is a **constant of the edition**, because all sheets are the same physical
size scanned to the same width. Fixing it and solving only for phase is far more
stable than fitting pitch and phase together (§5.2).

### 3.3 1885 sheet coverage (VERIFIED — 19 sheets total)

Sheet 1 is the **index/key sheet** with a full key map *and a street index that
lists which sheet each street appears on*. Use it as reference; never in art.

| Sheet | Avenues | Streets | Note |
|---|---|---|---|
| 2 | A–D | 16–19 | |
| 3 **lower panel** | D–G | 18–20 | two-panel sheet |
| 3 **upper panel** | G–J | 19–20 | **EXCLUDE — different scale** |
| 4 **left panel** | G–H | 25–28 | right panel is east of Broadway |
| 5 | G–J | 20–23 | City Park, Ball High School |
| 6 | D–G | 20–23 | **contains 22nd & Postoffice** |
| 7 | A–D | 19–22 | |
| 8 | A (wharf strip) | 20–25 | usually outside crop |
| 9 | A–D | 22–25 | |
| 10 | D–G | 23–26 | |
| 11 **upper-left panel** | G–I | 23–25 | stepped, multi-panel |
| 14 | A–D | 25–28 | |
| 12,13,15–19 | — | — | outside downtown crop |

**Ten-sheet working set: 2, 3, 4, 5, 6, 7, 9, 10, 11, 14.**

### 3.4 1877 sheet coverage (VERIFIED — 9 sheets, no index sheet)

| Sheet | Avenues | Streets | Note |
|---|---|---|---|
| 2 | A–D | 17–20 | |
| 3 | A–D | 20–23 | |
| 4 | A–D | 23–26 | |
| 5 | B–E West | 26–29 | outlying |
| 6 | C–F West | 29–32 | outlying |
| 7 | scattered | — | cotton presses, disconnected |
| 8 | **9 disconnected panels** | — | **EXCLUDE** (see §3.5) |
| 9 | D–G | 23–26 | |
| 10 | D–G | 20–23 | **contains 22nd & Postoffice** |

**Four-sheet working set: 3, 4, 9, 10** — yields a fully covered region with
essentially no gaps. 1877 sheet 10 has a **physical tear** through blocks
441–442 near Church East between 21st and 22nd. **Retain it.** It is authentic
condition, not damage to repair.

### 3.5 Irregular panels — THE key trap

Early Sanborn sheets are **not** rectangular grids. Verified cases:

- **1885 Sheet 3** — two panels. Lower panel is at edition scale (street pitch
  1135). **Upper panel is at a different scale** (measured street pitch ~606).
  Warping it to fit would stretch its buildings. Exclude it.
- **1885 Sheet 4** — two panels split at Broadway; left panel is a *single block
  column* (Ave G–H).
- **1885 Sheet 11** — stepped boundary; only the upper-left panel is on grid.
- **1877 Sheet 8** — nine geographically disconnected panels.

**Detection:** run a free-period comb fit per candidate panel region. If a
panel's measured pitch deviates >5% from the edition pitch, it is off-scale —
exclude and disclose. Do not warp it into place.

### 3.6 Known genuine gap

**1885, Avenue G–H × 18th–20th (top-right of a downtown crop).** The 1885
edition does not map 18th Street east of Avenue G at all — the Sheet 1 index
lists "Eighteenth St." only on sheets 2 and 3 (numbers 1–66, 67–130). The
19th–20th portion exists only on sheet 3's excluded upper panel. Fill with flat
paper tone and disclose. **Never generate content to hide it.**

---

## 4. Phase A — Acquisition (Agent A1)

1. Probe LoC item JSON with a browser UA. Enumerate all sheets and record
   `width`/`height` per variant.
2. Download master TIFFs for the working set. Verify each is >100 MB and
   decodes to 6450 × 7650. Retry ×3.
3. Download UT 1877 sheets with the cookie-jar/retry recipe (§2.3).
4. `sha256sum` everything into `sources/manifest.txt`.
5. Preserve originals unmodified in `sources/{year}/`. Never edit in place.
6. Write `source_urls.txt` with exact URLs.

**Disk/RAM:** LoC masters are ~142 MB each; ten sheets ≈ 1.4 GB. Budget ≥ 12 GB
free disk. Assume ~3 GB RAM (see §7).

---

## 5. Phase B — Registration (Agents A2, A3)

### 5.1 Sheet identification (A2)

Do **not** assume sheet numbers. Establish coverage two independent ways:

1. **Index sheet** (1885 only): read the street index. Entries look like
   `Twenty-second, 151-280 → 6` and `Avenue E, East, 101-230 → 6`. The
   intersection of the two sheet-sets identifies the target sheet.
2. **Each sheet's own printed labels and margin notes** ("SEE SHEET Nº 7" on
   the left edge, etc.). Cross-check against method 1.

For 1877 (no index) use method 2 alone, reading every sheet.

Produce `coverage.json`: for each sheet, its avenue range, street range, panel
regions, and whether it is on-grid.

### 5.2 Grid detection (A3) — VERIFIED ALGORITHM

Do **not** use feature matching. Sanborn sheets **abut along street centerlines
with zero image overlap**; there are no shared features. This is why SIFT/ORB
mosaic pipelines fail here.

```python
def whiteness(a):                       # a = float RGB in [0,1]
    mx = a.max(axis=2); mn = a.min(axis=2)
    return np.clip(a.mean(axis=2) - 2.2*(mx-mn), 0, 1)
```
Streets are unprinted paper (bright, unsaturated); buildings are strongly
colored. This isolates the street grid cleanly even through heavy foxing.

Then, per sheet:

1. Project `whiteness` to row and column signals over the map interior
   (inset ~7.5% to avoid bright margins).
2. **Fix the period** (§3.2) and grid-search only the phase. *Fitting period and
   phase together is unstable* — bright outer margins bias it, producing
   nonsense like avenue pitch 1056 on one sheet and 920 on another.
3. Extend the comb ±3 periods past the fitted range so edge lines are not
   clipped, then keep those inside the image.
4. **Refine each line by local center-of-mass** in a ±80 px window. Real block
   spacing is not perfectly uniform (measured 1101 / 1170 / 1133 for three
   consecutive street gaps); the comb gets you close, refinement lands it.
5. Assign identities from the labels established in §5.1.

**Detection at reduced scale is fine and much faster:** downsample LoC masters
to 3400 px wide, detect, then multiply coordinates by `6450/3400`. Same relative
precision.

### 5.3 Affine fit (A3)

Global grid: `X = avenue_index * P_AV`, `Y = (street_number - 16) * P_ST`.

Fit an **axis-aligned affine per sheet** (independent x/y scale + translation)
by least squares. Rotation is unnecessary — these scans are square.

**VALIDATION GATE:** every fitted scale must land within **±1% of 1.000**.
Verified results: 1877 0.988–1.003; 1885 0.965–1.001 (the 0.965 outlier is
sheet 4, fitted from only two avenue control points — acceptable, but flag any
sheet with <3 control points per axis). **A scale outside ±2% means a
misidentified grid line — stop and re-derive, don't proceed.**

---

## 6. Phase C — Compositing (Agent A4)

### 6.1 Clip windows — the duplicate-label fix (HARD-WON)

Naive clipping at the boundary street centerline makes **both** adjacent sheets
contribute the boundary street, so its printed name appears twice, offset by the
registration residual. It looks broken.

**Fix:** shift each sheet's clip window **past** its boundary street by ~half a
street width, so each street *and its label* belongs to exactly one sheet:

```
clip_lo = first_grid_line + SHIFT
clip_hi = last_grid_line  + SHIFT     # SHIFT ≈ 90 px at 3400 scale, 170 at 6450
```
Extend outward by `EXT` on edges that sit on the rim of the whole composite.
Blend with a narrow feather only (~24 px at 3400 scale, ~46 at 6450).

### 6.2 Border clipping — margin exclusion (HARD-WON)

Sheet margins hold title cartouches, scale bars and "See Sheet Nº x" notes that
must not enter the artwork. Detect the **printed black map frame** and intersect
it with the clip window.

**Critical detail:** search for the frame **only outside the outermost grid
lines**. An unconstrained search finds dense interior blocks instead of the thin
border line and clips *into* the map (observed: coverage dropped from 94% to
85%, and sheet 6 lost its entire Avenue G column).

Bonus: this same constrained detector automatically confines 1885 sheet 3 to its
lower panel and sheet 11 to its upper-left panel, because the panel dividers are
strong dark lines.

### 6.3 What stays in

Sanborn cross-reference notes printed **inside** the map border, and repository
stamps, are original printed content. Removing them means painting over the
source. **Leave them and disclose.** Only remove on explicit user instruction.

### 6.4 Tonal balance

Per-sheet **per-channel gain only** — no curves, no saturation change:

1. Measure paper tone as the median of bright, low-saturation pixels **on the
   map interior only** (crop to central ~56%). **HARD-WON:** including the white
   scanner margin makes some sheets report paper as `[229,232,235]` and others
   `[177,203,217]`, producing wildly inconsistent gains.
2. Equalize to the edition's mean paper tone. Clamp gains to ~0.93–1.08.
3. **Retarget per edition.** 1885 paper ≈ `[176,202,216]` BGR; 1877 is browner
   ≈ `[153,179,194]`. Using the 1885 target on 1877 pins every gain at the
   clamp.

Foxing, staining and age must survive. If the output looks "cleaned up," it is
wrong.

### 6.5 Single-pass resampling (HARD-WON — biggest quality win)

**Never warp to a native canvas and then resize to output.** Two Lanczos passes
over 4-pixel-tall lettering visibly softens it. Either:

- Compose the sheet→grid affine with the output scale and warp **once**, or
- Build at native and deliver at native (no resize at all).

Prefer delivering at native and letting the user crop.

---

## 7. Memory & Format Engineering (HARD-WON)

Assume ~3 GB RAM. The 1885 LoC canvas is 17,824 × 27,160 (1.45 GB as uint8).

| Trap | Fix |
|---|---|
| `PIL.Image.DecompressionBombError` | `Image.MAX_IMAGE_PIXELS = None` |
| PIL save of 484 MP → **OOM kill** | Use `cv2.imwrite` / `tifffile` instead |
| Float32 accumulator canvas (5.8 GB) | uint8 canvas; blend per-sheet in row chunks |
| Full-canvas CLAHE/levels → OOM | Process in ~1500-row bands with ~384 px overlap |
| Percentile levels over full array | Sample `img[::16,::16]`, apply via 256-entry LUT |
| tifffile LZW fails | `pip install imagecodecs --break-system-packages` |
| Warping full canvas per sheet | Warp only into that sheet's destination ROI |
| Huge intermediate re-reads | `tifffile.memmap` for the flat working copy |

Also: build a **coarse alpha mask** (e.g. 1/8 scale) and warp it with a scaled
matrix rather than materializing a full-size float mask.

---

## 8. Phase D — Review (Agent A6, run 3×)

Each pass produces `qc_pass_N.md` with explicit PASS/FAIL per item. **A6 must
extract crops from the actual delivered files** — never judge from a preview.

### Pass 1 — Geometry (after compositing, before output)
- [ ] All fitted scales within ±1% (list them)
- [ ] 200% crops at **every** sheet-boundary seam: streets and block lines
      connect; no black/transparent wedges; no white seam lines
- [ ] Grid-detection overlay per sheet: every detected line sits on the
      correctly *named* street
- [ ] No duplicated street labels at any seam
- [ ] No title cartouche, scale bar, or margin note inside the artwork
- [ ] Coverage mask computed numerically; every unfilled region is a single
      known, disclosed gap — not scattered holes
- [ ] Target intersection present and located as intended

### Pass 2 — Fidelity (after finishing)
- [ ] 100% crops confirm smallest lettering legible. Name specific targets and
      report failures: block numbers, address numerals, `Vac. S.`, `D.G.`,
      `Dwg`, and known landmarks (Harmony Hall, H. Rosenberg Bank, Ball High
      School, Cotton Exchange, The News Bld'g)
- [ ] No sharpening halos along block outlines or lettering
- [ ] Foxing/staining/tears **retained**, not cleaned
- [ ] Colors match the source (hand-coloring intact; check for BGR/RGB channel
      swaps by comparing a known pink/blue feature against the raw sheet)
- [ ] Diff a region decoded from two different deliverables — mean abs diff
      should be ≈1–2 gray levels (JPEG noise), proving they carry the same pixels

### Pass 3 — Delivery (after packaging)
- [ ] Every file opens cleanly; dimensions, DPI, compression, ICC verified
      programmatically, not assumed
- [ ] **Files actually arrive.** Verify each delivered file's byte size on the
      receiving side. Anything over ~450 MB may be silently dropped — split with
      `split -b 260m` and publish a SHA-256 so the user can verify reassembly.
- [ ] Portrait/landscape orientation is correct in the written file
- [ ] Formats match the user's actual device (§9)
- [ ] Production report complete and accurate

Orchestrator adjudicates. **Any FAIL sends work back to the owning agent and
re-runs that pass.** Do not ship on a partial pass.

---

## 9. Phase E — Delivery (Agent A5)

**ASK THE USER WHAT DEVICE THEY WILL VIEW THIS ON — BEFORE CHOOSING FORMATS.**
This was the single largest source of wasted effort in the prior run.

### The iPhone decode ceiling (HARD-WON, root cause of much confusion)
iOS will not fully decode images beyond roughly 100 MP. Past that, Photos
silently renders a small proxy, and zooming magnifies the *proxy*. The file is
fine; the renderer is not. Symptoms look exactly like a bad stitch.

This is also **why library websites look sharp on phones** — they stream small
full-resolution tiles of just the visible area, never the whole map.

### Format matrix

| Deliverable | Use | Notes |
|---|---|---|
| **Native TIFF** (LZW, sRGB, 300 ppi) | archival master, print shop | split if >450 MB |
| **Full JPEG** (q90) | one-file archive | JPEG compresses map linework far better than TIFF |
| **Tile set** (~45 MP each, 400 px overlap, q93, no chroma subsampling) + index map | phone viewing, cropping | *the* fix for mobile zoom |
| **Multi-page PDF atlas** (index page + tiles, `img2pdf` at 300 dpi, with bookmarks) | one document that zooms sharp on phone | PDF readers decode per page, staying under the ceiling |
| **OpenSeadragon + LoC IIIF viewer** (single HTML) | library-style infinite zoom | requires internet; tiles stream from tile.loc.gov |

`img2pdf` embeds existing JPEGs **losslessly** — no recompression. Use
`get_fixed_dpi_layout_fun((300,300))` so page size equals true print size.

---

## 10. Production Report (Orchestrator)

Must state: exact source URLs; sheets used per year; **candidate sheets reviewed
but excluded, with reasons**; original pixel dimensions per scan; composite and
crop dimensions; resampling factor for every output; restoration operations
performed; alignment method; gaps/damage/uncertainties; and explicit
confirmation that **no AI generation, generative fill, or synthetic inpainting**
was used anywhere.

State resampling factors **honestly**. If an output exceeds native resolution,
say so and give the number.

---

## 11. Behavioral Rules (learned the hard way)

1. **Narrate progress.** Do not go many tool calls without reporting.
2. **Never judge quality from a preview.** Extract crops from the real file.
3. **Verify delivery, not just creation.** A file written is not a file received.
4. **Ask about the target device early.**
5. **Report constraints as findings, not failures** — gated source, resolution
   ceiling, missing edition. State them plainly with the number attached.
6. **Do not fabricate detail to meet a requested size.** If the source can't
   support 40 × 60 at 300 ppi, say so and offer the size it does support.
7. **Prefer honest empty paper to invented map content**, always.
