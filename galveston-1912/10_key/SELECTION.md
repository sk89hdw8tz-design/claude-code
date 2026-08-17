# 1912 Galveston sheet selection — downtown / wharf

**Volume:** LOC `sanborn08539_004`, *Sanborn Fire Insurance Map from Galveston,
Galveston County, Texas*, **1912**, 111 sheets, 110 scanned images. Public domain.

## Target ground

Taken from the supplied 1899 print's own caption (the benchmark defines the area to
match; **no** 1912 geometry, sheet numbering, or topology is inferred from it):

> Avenue A (Water) to Avenue I (Sealy) · 19th Street to 25th Street (Rosenberg Avenue) · Piers 19–25

## Volume structure (from LOC page identifiers, not assumed)

Each image URL embeds a page id (`…g085391912:08539_1912-0039`), giving an exact
image-index ↔ sheet-number map with no offset guessing. This matters: the volume
interleaves **six skeleton sheets** (`0007s`–`0012s`) which would otherwise shift
every index after sheet 7.

| id | meaning |
|---|---|
| `titl` | title page (image 0) |
| `ind1` | street & specials index (image 1) |
| `cbd1`, `cbd2` | congested business district (images 2–3) |
| `0000` | key map to edition (image 4) |
| `0001`–`0099` | sheets 1–99 |
| `0007s`–`0012s` | 6 skeleton maps |

## Sheet grid (read from the key map at archival resolution)

Each regular sheet covers **3 avenue-strips × 3 street-blocks**:

| Column | Avenues | 18th–21st | 21st–24th | 24th–27th |
|---|---|---|---|---|
| 1 | A Water, B Strand | **7** | **9** | **11** |
| 2 | C Mechanic, D Market, E Post Office | **8** | **10** | **12** |
| 3 | F Church, G Winnie, H Ball | **39** | **43** | **49** |
| 4 | I Sealy, J Broadway, K | **40** | **44** | **50** |

## Independent confirmation — the 1912 street index

The index lists address ranges against sheet numbers. Galveston avenue addresses run
by cross-street, so `1800–2029` = 18th→21st, `2100–2329` = 21st→24th, `2400–2629` =
24th→27th. Read directly off the index:

| Avenue | 18th–21st | 21st–24th | 24th–27th |
|---|---|---|---|
| A | 7 | 9 | 11 |
| B Strand | 7 | 9 | 11 |
| C Mechanic | *7 / *8 | *9 / *10 | *11 / *12 |
| D Market | 8 | 10 | 12 |
| E Post Office | 8 | 10 | 12 |
| F Church | *8 / *39 | *10 / *43 | *12 / *49 |
| G Winnie | 39 | 43 | 49 |
| H Ball | 39 | 43 | 49 |
| I Sealy | *39 / *40 | *43 / *44 | *49 / *50 |
| J Broadway | 40 | 44 | 50 |

(`*` = index's own mark for "only one side of street shown".)

This agrees with the key-map reading on every cell. Two consequences:

- **Avenue C, F and I are split between adjacent sheets** (one side each), so the
  columns either side of them are both required — the seam network will have to
  carry these shared avenues rather than cutting along them arbitrarily.
- **Avenue I (Sealy) — the southern limit of the target — is itself split**, so
  column 4 (40/44/50) is required to complete Sealy's odd side. Column 4 is not
  optional padding.

## Wharf

The index's `PIERS.` block assigns pier ranges to sheets directly:

| Piers | Sheet |
|---|---|
| …to 15 inclusive | 6 |
| **16 to 28 inclusive** | **5** |
| …to 32 | 4 |
| …to 38 inclusive | 3 |
| …to 41 | 2 |

Piers 19–25 fall wholly inside **sheet 5**; sheets 6 and 4 are therefore *not*
needed. Pier numbers correspond to the street they foot (Pier 21 at 21st St), which
is consistent with sheet 5 sitting alongside the 17th–27th street range on the key.

## Selected set — 13 sheets

`5, 7, 8, 9, 10, 11, 12, 39, 40, 43, 44, 49, 50`

| Sheet | LOC image index | Role |
|---|---|---|
| 5 | 9 | wharf front, Piers 16–28 |
| 7 | 11 | Ave A–B, 18th–21st |
| 8 | 13 | Ave C–E, 18th–21st |
| 39 | 49 | Ave F–H, 18th–21st |
| 40 | 50 | Ave I–K, 18th–21st |
| 9 | 15 | Ave A–B, 21st–24th |
| 10 | 17 | Ave C–E, 21st–24th |
| 43 | 53 | Ave F–H, 21st–24th |
| 44 | 54 | Ave I–K, 21st–24th |
| 11 | 19 | Ave A–B, 24th–27th |
| 12 | 21 | Ave C–E, 24th–27th |
| 49 | 59 | Ave F–H, 24th–27th |
| 50 | 60 | Ave I–K, 24th–27th |

Not selected, with reasons: sheets **6** and **4** (wharf outside Piers 19–25);
sheets **17/21/27/33** (north of 18th St); **13/14/55/56** (south of 27th St);
**26/45/46/47** (east of Avenue K). The 6 skeleton maps (`0007s`–`0012s`) happen to
cover this same downtown ground and are available as corroborating evidence if a
disputed control needs a second witness, but they are not mosaic sources.

## Resolution

Archival JP2 derivative, **6653 × 7795 px** (~51.9 MP) per sheet — LOC's largest
JPEG derivative is only 1663 px wide, so JP2 is used and decoded locally. This
comfortably exceeds what the 1899 benchmark print required (11817 × 7965 total at
300 DPI from 13 sheets).
