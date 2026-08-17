# Seam structure of the 1912 edition — every seam abuts

## The rule, read from the 1912 street index

The index marks `*` against an address range meaning **"only one side of street shown"**.
Applying that across the numbered streets and lettered avenues in the target area gives a
completely regular rule:

- **Streets and avenues that fall on a sheet boundary are split**, one side to each plate.
- **Streets and avenues interior to a sheet are shown whole**, with no asterisk.

Evidence, straight from the index:

| Feature | Index entries | Reading |
|---|---|---|
| 22nd, 23rd St | `1–224→9`, `300–525→10`, `600–825→43`, `900–1125→44` — no asterisks | interior to a sheet row, shown whole |
| 25th, 26th St | `1–224→11`, `300–525→12`, `600–825→49`, `900–1125→50` — no asterisks | interior, whole |
| **21st (Center) St** | `600–824→*39` / `601–823→*43`; `900–1124→*40` / `901–1123→*44` | **split** across our horizontal seam pairs |
| **24th St** | `2–224→*9` / `1–223→*11`; `300–524→*10` / `301–523→*12`; `600–824→*43` / `601–823→*49`; `900–1124→*44` / `901–1123→*50` | **split**, exactly our four 24th-St pairs |
| **Ave. C (Mechanic)** | `1800–2028→*7` / `1801–2027→*8`; `2100–2328→*9` / `2101–2327→*10`; `2400–2628→*11` / `2401–2627→*12` | **split**, our three Mechanic pairs |
| **Ave. F (Church)** | `1800–2028→*8` / `1801–2027→*39`; `2100–2328→*10` / `2101–2327→*43`; `2400–2628→*12` / `2401–2627→*49` | **split** |
| **Ave. I (Sealy)** | `1800–2028→*39` / `1801–2027→*40`; `2100–2328→*43` / `2101–2327→*44`; `2400–2628→*49` / `2401–2627→*50` | **split** |

The split ranges name the exact sheet pairs already derived independently from the key map
and from the adjoining-sheet numbers printed on the plate edges. Three independent sources
agree on the same 17 internal pairs for the twelve-sheet block.

## What this means for the method

**1. No image correlation is valid at any seam.** There is no band of duplicated
cartography anywhere in this edition — not on the vertical seams, not on the horizontal
ones. NCC, SIFT, and panorama stitching would be matching blank street paper and the
repetitive drafted furniture inside it. Any alignment they produced would be an artefact.
This is the structural reason the brief's warning applies here, and it applies uniformly.

**2. The shared geometry is always perpendicular to the seam.** For a seam along an
avenue, the cross *streets* are drawn on both plates and constrain position along the
seam. For a seam along a street, the crossing *avenues* do the same. In both cases the
across-seam direction is constrained only by the plate's own drafted street-width
annotation — hence anisotropic uncertainty, tight along-seam and loose across-seam.

**3. The natural ownership cut is the street centreline.** Because each plate carries one
side of its boundary street, the two plates' content tiles rather than overlaps. Source
ownership follows from the cartography itself: each plate owns its own frontage, and the
pooled cut for a shared street runs down the middle of that street. This is the opposite
of a blending problem — there is nothing to blend, and blending would be inventing.

**4. Duplicated page furniture cannot be resolved by moving a cut onto a neighbour's
copy of the same ground**, because no neighbour holds the same ground. Where furniture
sits inside a plate's unique coverage, the brief's instruction stands: preserve it.

## Still to establish per pair

How much of each boundary street each plate actually draws (half, or the full width with
the neighbour drawing it again). The index proves which *frontage* belongs to which plate;
it does not say where the drafted street space ends. A first attempt at measuring this
failed degenerately and is recorded as F-003; it needs a neatline detector based on
continuous straight runs rather than profile maxima, validated by hand on two or three
plates before any number from it is used.
