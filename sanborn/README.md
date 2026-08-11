# Galveston Sanborn Map Composite Pipeline

Rebuilds seamless composites of the Sanborn Fire Insurance Maps of Galveston,
Texas (1885 from Library of Congress, 1877 from UT Perry-Castañeda), centered
on 22nd Street & Postoffice Street (Avenue E).

Implements the verified algorithms and hard-won fixes from
`CLAUDE_CODE_BUILD_SPEC.md` (uploaded spec from a completed manual run).

## Modules

| File | Phase | Contents |
|---|---|---|
| `config.py` | — | Verified constants: pitches, working sets, paper tones, gates |
| `acquire.py` | A | LoC JSON probe + master TIFF downloads; UT cookie-jar/retry recipe; sha256 manifest |
| `registration.py` | B | Whiteness street-grid isolation, fixed-period comb + phase search, center-of-mass refinement, off-scale panel detector, axis-aligned affine fit with ±1%/±2% validation gates |
| `composite.py` | C | Constrained frame detection, past-boundary clip shift (duplicate-label fix), interior-only paper-tone gains, single-pass Lanczos warp into ROI, row-chunk blending on uint8 canvas |
| `output.py` | E | Full JPEG, ~45 MP tile set + index map (iOS decode-ceiling fix), lossless img2pdf atlas, >450 MB split with SHA-256 |

## Run order

```
python3 acquire.py all          # needs egress to loc.gov / tile.loc.gov / maps.lib.utexas.edu
# Phase B/C are driven per-edition by run scripts written during the build,
# with an A2 coverage-verification step (sheet identities from printed labels
# + the 1885 index sheet) between detection and affine fitting.
```

QC (Phase D) runs three times in independent reviewer contexts, judging crops
extracted from the actual delivered files, per the spec §8 checklists.

## Non-negotiables

- No generative fill, inpainting, or invented content anywhere. Genuine gaps
  (1885 Ave G–H × 18th–20th) get flat paper tone, disclosed.
- The ALTCHA proof-of-work gate on texashistory.unt.edu is not circumvented.
- Foxing, stains, and the 1877 sheet-10 tear are retained — authentic condition.
- Off-scale panels (1885 sheet 3 upper, sheet 8/1877 disconnected panels) are
  excluded and disclosed, never warped into place.
