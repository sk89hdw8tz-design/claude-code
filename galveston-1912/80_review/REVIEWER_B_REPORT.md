# REVIEWER B — CONTENT-FIRST HISTORICAL AUDIT
**Object:** `60_master/final/master_full.tif` (26206 x 14489 RGB) and `deliverables/Galveston_1912_Wharf_Downtown_print.jpg`
**Method:** fully independent — all structure derived from the 1912 archival scans only (street & specials index img001, key map img004, plates img009-img060). No material from 40_solve/, 50_seams/, 30_controls/, 70_qa/, fable_review/, 90_decisions/ was read.
**Reviewer:** B (adversarial, working separately). Date: 2026-08-17.
**Evidence:** `80_review/evidence_B/B01…B27` (all coordinates below are master_full.tif pixels, origin top-left).

---

## 1. Independently derived ground truth (from img001, the 1912 street & specials index)

Galveston address system (read off the index, confirmed on plates): avenue blocks carry
numbers x00–x29 only; avenue evens face north (canvas-left), odds south. Numbered-street
runs break at Avenue C (…224 | 300…), Avenue F (…525 | 600…), Avenue I (…825 | 900…).

| Ground | Sheet | Index evidence |
|---|---|---|
| Av A–C(even), 18th–21st | 7 | Av A/B 1800–2029; Av C even 1800–2028* |
| Av C(odd)–F(even), 18th–21st | 8 | Av C odd 1801–2027*; Av D/E 1800–2029; Av F even 1800–2028* |
| Av F(odd)–I(even), 18th–21st | 39 | Av F odd 1801–2027*; Av G/H; Av I even 1800–2028* |
| Av I(odd)–, 18th–21st | 40 | Av I odd 1801–2027* |
| same bands, 21st–24th | 9, 10, 43, 44 | 2100–2329 rows; 21st split 2-224*→7 / 1-223*→9 |
| same bands, 24th–27th | 11, 12, 49, 50 | 2400–2629 rows; 24th split 2-224*→9 / 1-223*→11 |
| Av A–C(even), 27th–30th | **13** | Av A/B 2700–2929 — **outside the 19th–25th window** |
| Piers 16–28 | **5** | index "Piers … 16 to 28 inclusive → 5" (B03) |

Row seams therefore lie ON 21st and ON 24th Street (each street's two frontages drawn on
different plate rows); column seams run along Avenues C, F, I (frontages split even/odd).
The plates' own printed margin cross-references (sheet 11 prints "9" north, "5" west, "12"
east, "13" south; sheet 49 prints "43/12/50/55"; sheet 5 prints "6/7/9" and "9/11/13")
independently confirm exactly the adjacency the mosaic implements.

Placement was re-derived by multi-patch NCC template matching (my own transforms, not the
manifest's): 12 grid sheets fit with RMS 0.2–1.4 px; wharf panels 5A/5B fit at scale
1.974 / 1.989, rot −1.23° / +0.13° (RANSAC, RMS ≈1–3 px). The wharf sheet is drafted at
100 ft/in vs the grid's 50 ft/in; the ~2x factors show the mosaic really did unify the scales.

## 2. Tests performed and results

**T1 — Address-run continuity, vertical seams (18 band crossings).** Avenue C bands
19/20/21/22/23/24 (B04, B05): even 1902–2028…2402–2428 vs odd 1901–2027…2401–2427 oppose
correctly; every numbered street crosses …223/224 | 301/302… . Avenue F (B06, B07): crossings
…519–524 | 601–614… at all six bands; Avenue I (B08, B09): …815–824 | 901/902… at all bands.
**No break anywhere; the 2028|2101-style sequences are exact.**

**T2 — Horizontal seams (21st, 24th).** Verified at the C/F/I corners in T1 plus mid-block
spots (B10: 21st at A–B, Anheuser-Busch Depot [sheet 7] facing Office/Bank [sheet 9];
B11: 24th at G–H, 710–724 | 709–723). Even/odd frontage parity matches the index split
(2-224→row above, 1-223→row below) at every point sampled. Pipe runs (6", 12") continue
across seams; street widths agree on both sides (70'/80'/120').

**T3 — Specials census.** 40+ index specials located; **every one appears exactly once and
on its indexed sheet's ground**, including: Rex Steam Laundry (8) at 1901 Mechanic "from
plans" — coherently cross-referenced by the Rex Laundry note on sheet 12 ("to be removed…
see Sheet No 8"); City Storage (7); City Hall & Market (8); Grand Opera House (8); Arlington
House (8); O.K. Laundry (8); Cotton Exchange (9); Galveston News (9); Security Building (9);
Royal/Washington Hotels (9); Mistrot Whol. Dry Goods (9) vs Mistrot Warehouses (10); Armour
& Swift Cold Storage (9); Galveston Dry Goods, Blum Notion, Blum Hardware, Miller Bros
Overalls, Gulf Fishery Ice Plant (9); Palmetto & Oxford Hotels, Bon Marche, Salvation Army,
Scottish Rite Cathedral, SW Tel&Tel, Fellman, Garbade-Eiband, Elks Home, Crystal-Majestic,
Galveston Tribune, Interurban Terminal, Model Laundry & Dye Works, Girardin House, Parsons
Overall Fact'y, Tremont Hotel (10); Clark & Courts, Texas Hotel, Panama Hotel (11); Jewish
Immigrant Information Bureau, Avenue Hotel, New City Hotel (12); Presbyterian Ch. 19th, St
Mary's Cathedral, Methodist Ch., County Court House, Supreme Court Bldg, Park Hotel, Ball
School Annex, Galveston Electric Co (39); Ball High, First Baptist, First Ch. of Christ,
Eaton Chapel, Trinity Episcopal, YMCA, Hebrew B'nai Israel, Rosenberg Library, 4th
Presbyterian (43); Atlanta Hotel, German Lutheran Ch. (49); Mallory Bldg, Merrow Shed, Gulf
Fishery Shed, Parr Warehouses (5, wharf). Specials indexed to in-scope sheets but **not** in
the mosaic all verifiably lie outside the declared window on the source plates: U.S. Post
Office & Custom House (49, block 385, **between 25th and 26th**, B26), Union Depot Steel
Train Shed + G.C.&S.F. depot + Pierce-Fordyce (11, south of 25th, B27), Orthodox Synagogue
(49, 26th–27th), and the sheet-40/44 specials east of Avenue I (St Joseph's, Reedy Chapel
etc.). No duplicated special; no phantom.

**T4 — Block-number lattice.** ~30 printed block numbers read across the mosaic form a
perfect two-dimensional arithmetic lattice: +1 per block southward, −60 per corridor
eastward — yard-A 739/740/741/742/743/744; A–B 679–684; B–C 619–624; C–D 559–564; D–E
499–504; E–F 439–444; F–G 379–384 (complete run along the F seam); G–H 319–324 (Court House
319, Central Park 320, Ball High 321); H–I 259–264 (B19, B20). Spot-verified against source
plates (684, 624, 384, 324 on img019/img059). Any row shift or column swap would break both
progressions simultaneously; nothing breaks. **No repeats, no skips, no mirrored placement.**

**T5 — Wharf.** (a) Pier census: PIER 19 through PIER 25 each appear exactly once (B12–B14),
finger piers 19–22 with slips, 23–25 as landing stages on the marginal Wharf Company's Shed
— matching sheet 5's own drawing. (b) Registration: mapping the wharf panels' printed shore
street labels through **my** fitted transforms lands 19TH→y≈234 (grid 19th ≈130–230),
20TH→2524 (2555), 21ST→4868 (≈4900), 22ND→7010 (7074), 24TH→11660 (11660 — exact),
26TH→16522 (correctly off-canvas). A one-street misplacement (~2400 px) is excluded by two
orders of magnitude. (c) Scale unification: panels fit at 1.974x/1.989x vs grid ≈1.00x ↔ the
100 ft/in vs 50 ft/in drafting scales stated on the plates; the five-street label
registration in (b) — agreement within 30–100 px over a ~14,300 px north–south baseline —
bounds any residual wharf-vs-grid scale error at ≈0.5%, i.e. the strips are drawn to one
unified scale (a raw-scale paste would err by ~7,000 px at 26th St). (d) Pier 22 (drawn on BOTH panels): panel
A's complete depiction (Gulf Fishery shed at root) renders once; panel B's edge-truncated
stub maps to canvas (5929, 6707), on the A-owned side of the cut → correctly suppressed
(B15–B17). No duplicate pier, no mid-pier jog, no gap. (e) Wharf/grid ownership boundary
(x≈7350–7550) checked at three latitudes (B18): marginal wharf line, slip bulkheads and the
long shed continue across with only tone/color steps (2x vs 1x depictions of the same
structures); B's dead-ending slip bulkhead is hidden inside the grid-owned strip as designed.

**T6 — Sheet 13 (img023) exclusion.** Template matching of sheet 13 content against the
whole mosaic at 1x and 2x: best NCC 0.32/0.30 = noise floor → its ground is nowhere in the
mosaic. Per the index its ground is Avenues A–C(even), addresses 2700–2929 = 27th–29th
Streets, entirely west of the 25th-Street window. **Absence verified and correct.**

**T7 — Print derivative vs master.** The print is exactly master's map_rect
[3556,0,26206,14489] at scale 0.52151 with 94 px margins (NCC 0.995 at offset (94,94));
nine-point grid diff shows JPEG-level differences only (mean |Δ| 0.2–2.8 gray levels). The
discarded strip x<3556 contains **no drawn ink** — only warped-in scan backing / plate paper
edge (dark bbox x 3315–3555). Westernmost true ink (wharf scale-bar tip + "100" label,
x≈3730) is retained with ~175 px of margin. Top edge retains 19th St with both frontages;
bottom retains 25th plus its south-frontage sliver; right retains Avenue I's odd frontage.
Caption text present and matches the manifest (B25).

## 3. Findings

**F1 — MINOR (factual error in the deliverable's caption) — confidence: high.**
The print caption states "Composited from **15 source regions** … sheets
5(A,B),7,8,9,10,11,12,39,40,43,44,49,50". The actual count of composited source regions is
**14**: 12 grid-sheet regions + wharf panels 5A and 5B. My independent template matching
accounts for the entire drawn canvas with exactly these 14 regions (and the mosaic's own
manifest lists 12 sheet regions + 2 wharf transforms). The likely cause is double-counting
sheet 5 (13 sheet labels + 2 panels). One-word fix in the caption (and in
`master_full_manifest.json` caption_lines) before further distribution. Evidence: B25.

**F2 — MINOR (misleading scale text carried into the unified mosaic) — confidence: high.**
The only verbal scale statement anywhere in the composition is the wharf sheet's retained
"Scale 100 Ft. to One Inch." (canvas ≈(3745–5100, 7250–7430)). After the 2x unification this
wording is false for the master (which is at the grid sheets' 50 ft/in drafting scale) and
for the print (~80 ft/in at 300 dpi). The graphic bar itself remains metrically TRUE (it was
resampled with the image; its "100 Ft" segment still spans 100 ft of ground), but a reader
pairing the words with the print will misjudge distances by 2x. The grid sheets' own "Scale
of Feet" bars are clipped at seams (e.g. sheet 39's at canvas ≈(24300,6660)). Recommend one
caption clause ("graphic bar valid; printed scale wording refers to original plates").
Evidence: B13, B24.

**F3 — MINOR (cosmetic, class: seam-clipped street lettering) — confidence: high.**
Where the row seams ride along 21st and 24th Streets, the plates' tall street-name letters
are partially cut: "24TH ST." at D–E survives only as letter bottoms (canvas ≈16400–17000,
y≈11650–11700); "21ST OR CENTER ST." is top-clipped (≈10600–11400, y≈4900). Addresses,
widths and geometry around them are intact — legibility blemish only. Evidence: B23, B10.

**F4 — NOTE (cosmetic, class: plate marginalia fragments at seams) — confidence: high.**
The hard-ownership, no-blending policy (declared in the caption as "plate disagreements
preserved") leaves authentic plate-margin artifacts at seams: interleaved giant sheet-number
digits at Avenue I ("4" of 40 over "9" of 39, canvas ≈(25600,1000–1600)); an orphaned giant
"4" (of sheet 10's "43" cross-ref) plus both plates' "AVE. F OR CHURCH" texts at F/22nd–23rd
(≈(19800,8250–8900)); solid digit fragments near 24th/C (≈(13840,11700)) and 24th/F
(≈(19890–20100,11720)); sheet 5's big "5"s near the wharf boundary; several compass roses
(one per plate). All authentic content, none positional errors. Evidence: B21, B22, B08.

**F5 — NOTE (cosmetic, west edge & water cut) — confidence: high.**
(a) Panel A's physical paper edge plus a scan-backing sliver are visible inside the map rect
at canvas x≈3556–3620 (y≈6900–8250, smaller bits above); in the print they appear as a faint
gray fringe in the left margin (print y≈3690–4400). (b) The A|B water cut between Piers 22
and 23 shows a tone step (panel A's lavender water apron vs panel B's paper white) with
stepped polygon edges in open water (≈(3400–7400, 7900–8700)); the wharf/grid boundary shows
similar tone steps and a small white notch at the shed north edge (≈(7480,9900)). No content
is missing or duplicated at any of these. Evidence: B24, B15, B18.

**F6 — NOTE (coverage boundaries).** The window slices flanking blocks honestly: an 18xx
south-frontage sliver above 19th, a 25xx north-frontage sliver below 25th, Avenue I's odd
frontage at the east edge. In-scope-sheet specials south of 25th (U.S. Post Office & Custom
House, Union Depot Train Shed, G.C.&S.F. depot, Pierce-Fordyce, Orthodox Synagogue) are
excluded by the declared 19th–25th window — consistent with the caption, but worth knowing
for anyone using the print as "downtown Galveston": the federal building is one block
outside the frame. Evidence: B26, B27.

## 4. What was NOT found (asserted after real effort)
- No address-run break at any of the 30+ seam crossings walked (T1, T2).
- No duplicated or missing establishment among 40+ specials censused (T3), and no duplicated
  pier or shed along the wharf, including the doubly-drafted Pier 22 (T5d).
- No block-number repeat, skip, or transposition in the two-way lattice (T4).
- No sheet misplacement, rotation, or scale error beyond ±0.5% paper-distortion terms
  (independent transform fits, T5b/T5c); no one-street wharf shift.
- No sheet-13 content, and its exclusion is index-correct (T6).
- No drawn content lost by the print crop, and no content difference print-vs-master beyond
  JPEG noise (T7).

## 5. Verdict
**PASS — no CRITICAL or MAJOR defects.** The mosaic is a historically faithful composite of
the 1912 plates: every seam I walked continues the 1912 address fabric exactly as the
volume's own index prescribes, and the wharf strip is correctly rescaled and registered to
its streets. The only outright error found is the caption's region count (**F1**: says 15,
is 14), plus one misleading retained scale text (**F2**) and documented cosmetic seam
artifacts (**F3–F5**) inherent to the declared hard-ownership compositing policy.
