# QC Pass 3 — Delivery (re-verification run 2)

Target: `/tmp/claude-0/-home-user-claude-code/2bd63ebc-a879-5d86-b98a-dc1ab929f20f/scratchpad/sanborn/deliver/1885/`
Method: programmatic only (python3 + tifffile/PIL/pikepdf/hashlib, `OPENCV_IO_MAX_IMAGE_PIXELS=2**40`).
Run 1 of this pass (FAIL) archived as `qc_pass_3_run1.md`.

**OVERALL VERDICT: PASS** — all six items pass; two cosmetic advisories, no blockers.

---

## Item 1 — File sizes / split present, monolith gone — PASS

Delivered tree (24 files, 8 top-level + 16 in `tiles/`):

| file | bytes | MB |
|---|---|---|
| galveston_1885_composite.tif.part-aa | 272,629,760 | 272.6 |
| galveston_1885_composite.tif.part-ab | 272,629,760 | 272.6 |
| galveston_1885_composite.tif.part-ac | 3,700,838 | 3.7 |
| galveston_1885_composite.tif.sha256 | 95 | — |
| galveston_1885_atlas.pdf | 107,112,574 | 107.1 |
| galveston_1885_full.jpg | 57,830,222 | 57.8 |
| largest tile (r3c2) | 10,628,537 | 10.6 |

- Largest delivered file = 272.6 MB < 450 MB. PASS.
- No `galveston_1885_composite.tif` monolith anywhere under `deliver/1885/` — only the three `.part-*` files. (The 551,895,046-byte working copy remains in `build/1885/`, which is not the delivery tree.) PASS.
- Exactly three `.part-*` files plus one `.sha256`. PASS.

## Item 2 — Reassembly, checksum, geometry, resolution tags — PASS

Reassembled in a clean temp dir with `cat part-aa part-ab part-ac`; the delivered `.sha256` copied in unmodified.

- Reassembled size 548,960,358 bytes (= sum of the three parts exactly).
- `.sha256` contents: `fdddee08…98b7  galveston_1885_composite.tif` — **bare filename, no absolute path** (run-1 warning fixed).
- `sha256sum -c galveston_1885_composite.tif.sha256` from inside that directory → `galveston_1885_composite.tif: OK`, exit 0. PASS.

tifffile on the reassembled file:

| tag | value |
|---|---|
| ImageWidth × ImageLength | **17632 × 26968** |
| shape / dtype | (26968, 17632, 3) uint8 |
| PhotometricInterpretation | 2 (RGB) |
| SamplesPerPixel / BitsPerSample | 3 / (8,8,8), PlanarConfiguration 1 |
| Compression / Predictor | 5 (LZW) / 2 (horizontal) |
| RowsPerStrip | **128** (211 strips) |
| XResolution / YResolution | **(300,1) / (300,1)** |
| ResolutionUnit | 2 (inch) → **300 ppi** |

All expectations met, including the run-1 missing-resolution-tag warning. Single page, no ICC (untagged sRGB, as the report states).

## Item 3 — JPEG density, decode, chroma, pixel spot-check — PASS

All 17 JPEGs (full + index + 15 tiles) opened and fully decoded with PIL without error or truncation warning.

- **JFIF density: 300 × 300, unit = 1 (dots/inch) on every one of the 17 files.** Run-1 warning fixed.
- Tile dimensions all 6144 × 5714; full JPEG 17632 × 26968; index 1600 × 2447.
- Chroma sampling read from the SOF marker: all 15 tiles `1x1,1x1,1x1` = **4:4:4**. Full JPEG `2x2,1x1,1x1` = **4:2:0** (now disclosed — see item 6). Index map is also 4:2:0 (advisory below).
- No ICC profile and no EXIF on any JPEG, consistent with the report's untagged-sRGB statement.

Spot-checks against the reassembled TIFF (mean absolute difference, RGB, 768×768 windows unless noted):

| tile | origin in canvas | MAD |
|---|---|---|
| r1c1 | (0, 0) | 0.40 (mostly paper margin) |
| r3c2 | (5744, 10628) | 1.33 |
| r5c3 | (11488, 21254) | 1.20 |
| full JPEG | region (8000, 10000) | 1.97 |

Tile MADs land in the expected q93 JPEG-noise band (~1–2); the 4:2:0 full JPEG is slightly higher as expected. Content registration confirmed (a 1 px origin error would push MAD far above this band).

## Item 4 — Atlas PDF — PASS

pikepdf: **16 pages**, each with exactly one XObject, `/DCTDecode`, `/DeviceRGB`.

- SHA-256 of every page's **raw** (undecoded) stream matches the corresponding delivered file byte-for-byte: page 1 = `tiles/galveston_1885_index.jpg`, pages 2–16 = `r1c1 … r5c3` in row-major order. 16/16 exact, no re-encode.
- Page geometry: index page 384.00 × 587.28 pt, all tile pages 1474.56 × 1371.36 pt — exactly `px × 72/300` in both axes (6144/300×72 = 1474.56; 5714/300×72 = 1371.36). **300 dpi confirmed on all 16 pages.**

## Item 5 — MANIFEST.txt — PASS

- **23 entries**; every hash and size recomputed from disk: **23/23 exact, zero mismatches.**
- Coverage: 24 files on disk; the 23 non-MANIFEST files are all listed, MANIFEST.txt correctly excludes itself. `PRODUCTION_REPORT.md` **is** listed (`ddd4d24a…`, 10,459 B).
- No listed-but-absent entries, no unlisted files (including nothing stray in `tiles/`).

## Item 6 — PRODUCTION_REPORT.md deliverables section — PASS

Every load-bearing claim recomputed:

| claim | verified |
|---|---|
| tiles "35.1 MP each" | 6144 × 5714 = 35,106,816 px = **35.1 MP** ✓ (run-1 overstatement fixed) |
| TIFF "549 MB total" | 548,960,358 B = **549.0 MB** decimal ✓ (523.5 MiB — units now used consistently as decimal MB throughout) |
| parts "under 273 MB" | 272.63 MB ✓ |
| full JPEG "4:2:0 chroma subsampling — the tiles and TIFF are the color-accurate carriers" | matches SOF `2x2,1x1,1x1` ✓ (run-1 undisclosed-4:2:0 warning fixed) |
| "300 ppi resolution tags, 128-row strips" | ✓ per item 2 |
| "All JPEGs carry 300 dpi JFIF density; the TIFF carries 300 ppi resolution tags; no ICC profile (untagged sRGB)" | ✓ all 17 JPEGs + TIFF, no ICC anywhere |
| reassembly: `cat …part-* > …tif` then `sha256sum -c …sha256` | ✓ glob expands aa,ab,ac in lexical = correct order; bare-filename checksum works from the delivery dir; reproduced exactly in item 2 |
| tiles "400 px overlap … 100.0% canvas coverage" | col origins 0/5744/11488 (+6144 = 17632), row origins 0…21254 (+5714 = 26968) — full canvas, ≥400 px seam overlap ✓ |
| "under the ~100 MP iOS decode ceiling" | 35.1 MP ✓ |
| atlas "16 pages, losslessly at 300 dpi" | ✓ per item 4 |
| canvas "475 MP", "58.8 × 89.9 in at 300 ppi", index factor "≈0.09" | 475.5 MP; 58.77 × 89.89 in; 1600/17632 = 0.0907 ✓ |
| QC section's pass-3 note (first run failed on packaging, all fixed) | matches this run's findings ✓ |

### Advisories (non-blocking, no action required)

1. **Report's embedded MANIFEST self-entry is stale.** The copy of the manifest pasted at the end of `PRODUCTION_REPORT.md` lists its own hash/size as `e42cfb92… / 9896`, whereas the delivered file is `ddd4d24a… / 10459`. The other 22 embedded lines are byte-identical to `MANIFEST.txt`. A self-referential hash cannot be made correct in-place; the authoritative `MANIFEST.txt` is exact (item 5), so this is cosmetic. Optional fix: replace the self-line with `(self — see MANIFEST.txt)`.
2. **Index map chroma not stated.** `tiles/galveston_1885_index.jpg` is 4:2:0. The report's "4:4:4 no chroma subsampling" parenthetical scopes to the 15 tiles and the index is named separately, so this is not a misstatement — but the index is a 0.09× navigation aid and could say so explicitly.

---

### Verdict

**PASS.** All five run-1 warnings and the single run-1 FAIL are confirmed fixed: monolith removed, split verified end-to-end from the delivered checksum, resolution tags present on TIFF and all JPEGs, tile MP figure corrected, MB usage consistent, 4:2:0 disclosed. Manifest is exact and complete; the PDF embeds the delivered bytes unaltered at 300 dpi. Delivery is ready to ship.
