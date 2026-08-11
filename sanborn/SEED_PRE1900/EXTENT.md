# The extent, the sheets, and where the scans are

## The extent — one frame, three editions

Match the delivered 1899 poster:

> **Avenue A (Water Street) → Avenue I (Sealy); 19th Street → 25th Street
> (Rosenberg Avenue); plus the wharf front and piers west of Avenue A
> (Piers 19–25 in 1899).**

In 1899 grid terms that was avenue slots 0–8, streets 19–25, with the west
edge taken at the real extent of drawn wharf content (crop
`[235, 6581, 11752, 14237]` of the padded canvas → 11517 × 7515 px master,
aspect **1.533**).

Each edition numbers and names its corridors differently, and the earlier
editions cover less ground. **Do not port 1899's slot indices.** Derive each
edition's grid, then select the sheets whose printed labels place them
inside the frame above. Where an edition simply does not map part of the
frame, that area is flat paper and the report states the measured coverage.

### Poster geometry

| | Sheet | Map area | dpi from an 11.5k-px master |
|---|---|---|---|
| Large | 40 × 27 in landscape | ~39.0 × 25.4 in | ~295 |
| Small | 36 × 24 in landscape | ~34.5 × 22.5 in | ~329 |

Both rendered from the full-resolution master; never upscale. Caption bar in
the reserved margin. If an edition's master is smaller (1877 and 1885 scans
differ in scale), recompute — do not assume these numbers.

---

## Scans

`origin/sanborn-data-1889:sources/1889/ALL_GALVESTON_LINKS.txt` holds direct
UT links for **every** Galveston edition; `EDITIONS.txt` beside it gives the
counts below. Prefer these to re-scraping. Verify JPEG magic bytes and sizes
against `SHA256SUMS` before trusting a file. Never attempt to defeat bot
defenses or proof-of-work challenges; if blocked, use an alternate source.

| Edition | Sheets | Location | Status |
|---|---|---|---|
| 1877 | 9 | UT `txu-sanborn-galveston-1877-NN.jpg`, NN = 02–10 | **fetch first** |
| 1885 | 19 | LoC masters per `config.EDITIONS["1885"]` (6450 × 7650 tif); UT also carries 19 | partially local — verify |
| 1889 | 62 | branch **`origin/sanborn-data-1889`**, `sources/1889/Galveston_1889_NN.jpg` | **already fetched** |
| 1899 | 102 | branch `origin/sanborn-data-1899`, `sources/1899/` | reference only — do not rebuild |

---

## Candidate sheet sets for the frame

Starting points. **Verify by reading the printed corridor and street labels
on every sheet** before building — that check caught two mis-slotted sheets
and a ~700 px anchor error in 1899.

### 1889 — 62 sheets in the atlas

The user's original selection, read directly off the 1889 key map:

**Sheets 1, 2, 7, 8, 9, 10, 27, 29**

- 1, 2 — wharf front
- 7, 8, 29 — 19th–22nd × Avenues A–I
- 9, 10, 27 — 22nd–25th × Avenues A–I

The key sheet is in the fetched set; confirm the mapping against it. This is
the edition whose key the whole project's extent was chosen from, so it
should cover the frame most cleanly of the three.

### 1885 — 19 sheets, LoC masters, pitch 1856 × 2170 at 6450 px

From `coverage_prior.COVERAGE["1885"]` (avenue letters, street range):

| Unit | Avenues | Streets | Note |
|---|---|---|---|
| 2 | A–D | 16–19 | north edge of the frame |
| 7 | A–D | 19–22 | |
| 9 | A–D | 22–25 | wash-dominated (Strand brick) — needs the cream tone filter |
| 3 | D–G | 18–20 | **lower panel only**; upper panel is off-scale (pitch ~606) and excluded |
| 6 | D–G | 20–23 | contains 22nd & Post Office |
| 10 | D–G | 23–26 | |
| 5 | G–J | 20–23 | |
| 11a | G–H | 23–25 | left leg of an L-shaped panel; 11b is the upper step, clipped disjoint |
| **8** | Avenue A wharf strip | | **previously excluded as "outside crop" — now IN scope**, this frame includes the piers |

Sheet 1 is the index/key — reference only, never in the art.

### 1877 — 9 sheets, UT scans, pitch 972 × 1135 at 3400 px

| Unit | Avenues | Streets | Note |
|---|---|---|---|
| 3 | A–D | 20–23 | |
| 4 | A–D | 23–26 | |
| 10 | D–G | 20–23 | physical tear through blocks 441–442 — **retain, it is authentic** |
| 9 | D–G | 23–26 | |
| 2 | A–D | 17–20 | previously "west of crop"; check whether it supplies the 19th–20th band |

Excluded previously and probably still: 5, 6 (outlying west), 7 (cotton
presses, disconnected), 8 (nine disconnected panels).

**Expect 1877 to cover the frame only partially** — nothing in the working
set reaches Avenues G–I, and the wharf may not be mapped at this date.
Measure the achievable coverage, build what exists, disclose the rest as
flat paper with the number. If the covered fraction is too small to make an
honest poster, say so plainly rather than padding the frame.

---

## Per-edition constants to derive

For each edition, before any compositing:

1. **Pitch**, by autocorrelation of whiteness profiles over all sheets —
   report the median and IQR (1899: 1006 [1003–1012] × 1169 [1166–1171] at
   3400 px native). `config.EDITIONS` already carries measured pitches for
   1877 and 1885; confirm them against the full sheet set.
2. **Corridor width**, measured as the gap between the two block frontage
   lines bounding a street (1899: 245 px, measured on sheet 13).
3. **Identity model** — how corridors are named vs. indexed. 1899 required a
   physical-slot model because naming changes by district; check whether the
   earlier editions need the same.
4. **Frame-open edge table** and **scan insets** per sheet side
   (`LESSONS.md` §2).
5. **Edge-knot overrides** from interior-pitch extrapolation
   (`LESSONS.md` §3).
6. **Waterline colour**, sampled from that edition's own printed shoreline
   edging (1899: BGR 208, 214, 199).
