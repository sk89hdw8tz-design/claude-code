# QA plan — Galveston 1912 candidate master

Binding scope for the QA harness and reviewers. QA is adversarial: the tools themselves
are validated before their verdicts are believed, and no score substitutes for looking.

## Stages (all must produce artifacts under 70_qa/)

1. **Seam matrix** — per seam: solve residual RMS, cut provenance, mask tiling status
   (no gap/overlap along the cut), content-extent encroachment, panel verdict. One table.
2. **Native-resolution seam panels** — per seam: A-only / B-only / merged, all three cut
   from ONE precomputed integer rectangle in the mosaic frame (the rectangle is computed
   once and stored; the three images must be pixel-registered — guard against the
   documented float-truncation and crop-clamping failures). Each panel stamped with the
   master's content hash. Reviewed visually, verdict recorded per seam.
3. **Junction panels** — all six interior 4-sheet junctions, the two Sealy junctions
   first, plus the block's outer corners. Checks: coverage, ownership, blank-margin
   intrusion, building clipping, roadway continuity, holes.
4. **Sheet-5 cross-panel review** — after panel integration: the duplicated Pier 22 /
   22nd St ground as rendered (which panel owns it, is the seam honest, is the ~55 ft
   pier drafting disagreement preserved rather than hidden).
5. **Paper-edge / scanner-surround review** — no dark backdrop or page edge may appear
   in the master; no mask may quietly include scanner surround as "content".
6. **Whole-footprint hidden-content census** — the real question, per contributing
   source region: does the ORIGINAL plate draw meaningful cartography, near ground
   covered by the master, that the master does not show? Method: warp each source's
   drawn-content map (page-isolated ink, F-001-aware) into the mosaic; subtract the
   master's ownership of that sheet; connected components of the difference above a
   size threshold are listed and EVERY significant component is visually inspected
   against the original (not scored away by whiteness/alpha/ink-fraction proxies).
   Verdicts: OWNED-BY-NEIGHBOUR-CORRECTLY / FURNITURE-BY-DESIGN / **HIDDEN-CONTENT-FAIL**.
7. **Source-ownership audit** — every master pixel maps to exactly one source region;
   the ownership raster's provenance hashes match the render manifest; cuts follow the
   pooled per-street definitions.
8. **Independent adversarial full-mosaic review** — two reviewers (separately spawned,
   no authorship of geometry/masks, not given expected answers or PASS statistics),
   instructed: "Assume this reconstruction contains a subtle but serious error. Find
   it." They derive the layout independently from the 1912 key/margins/blocks/streets/
   piers. Every significant finding is re-tested numerically against the current master
   and the original scans before any change is made.

## Tool-validation gates (before any QA verdict is accepted)

- Panel generator self-test: render a synthetic checker mosaic, verify A/B/merged
  pixel-registration byte-exactly, and verify the stored rectangle matches the images.
- Census self-test: hide a known 200-px square of synthetic "cartography" under a mask;
  the census must find it. Run once per census code change.
- Stale-artifact guard: every QA artifact embeds the master's SHA-256; the QA report
  refuses to aggregate artifacts carrying a different hash.
- Revert rule: any revert regenerates affected derived state and re-verifies the
  reverted feature is gone (a revert is an operation, not an assumption).

## Cross-year comparison (after acceptance of the 1912 geometry)

Compare with the accepted 1889 mosaic as sanity only; classify differences as genuine
urban change / drafting disagreement / atlas-layout difference / reconstruction error.
1912 geometry is never adjusted toward 1889.
