# Independent audit of the semi-manual control protocol

Auditor: Fable review track. Scope: `30_controls/VERIFICATION_PROTOCOL.md` together with
`CONTROL_STRATEGY.md` and `SEAM_STRUCTURE.md`, as they stand on the canonical branch.
Nothing canonical was edited; all recommendations are for the controller to reconcile.

## Overall verdict

**Sound in architecture, incomplete in schema.** The protocol's core decisions are right
for this material: crossing-feature observables rather than image correlation at abutting
seams; both flanking faces recorded so the drafted street width acts as a per-control
sanity check; navigation panels barred from supplying final coordinates; pipe/hydrant
symbols excluded from precision use; anisotropic sigma with the across-seam component
deferred to a constructed quantity. Field-by-field, however, several records the audit
checklist requires are missing or only implicit, and two defaults are unsafe.

## Field-by-field assessment

| Required record | Status in protocol | Note |
|---|---|---|
| Named historical anchor | PRESENT (`anchor`) | — |
| Semantic feature identity | PRESENT (`anchor_evidence`) | free text; adequate |
| Both flanking face lines | PRESENT (`north_face_y` / `south_face_y`) | naming does not generalise to horizontal seams — use `face_1`/`face_2` + explicit axis |
| Source pixel coordinates | **PARTIAL** | one along-seam coordinate per face plus `measured_at_x`; a line reading should record the measured segment (both endpoints, or position + extent). As written, two readers could measure different spans of a jogging face and both satisfy the schema |
| Measurement location along frontage | PRESENT (`measured_at_x`) | rule "corresponding corners adjacent to the seam street" is stated — good |
| Address-run / block-number evidence | PRESENT (in `anchor_evidence`) | — |
| Why not one block off | **MISSING as a dedicated field** | currently inferable from evidence text; the protocol should force an explicit disambiguation sentence per control (the failure it guards against is the project's documented number-one risk) |
| Uncertainty | PARTIAL | see unsafe defaults below |
| Sigma along seam | PRESENT | — |
| Sigma across seam | **UNDERSPECIFIED** | recorded as the string "constructed from drafted street width at solve time", but the protocol never defines the construction: which width annotation, read where, converted at what scale, with what tolerance. Define it once, in the protocol, not per-solve ad hoc |
| Observed vs constructed | PARTIAL | template hardcodes `"class": "observed"`; the verified store has no CONSTRUCTED / CONTEXT-ONLY / REJECTED lifecycle |
| Independently remeasured | **MISSING** | no field records a second reading, by whom, or its delta. Add `remeasured_by`, `remeasure_delta_px`; controls disagreeing beyond tolerance escalate rather than average |

## Unsafe assumptions found

1. **Fixed default `sigma_along_px: 8.0`.** Line readability varies plate-to-plate and
   corner-to-corner (clean single rule vs. building outline overlapping the face vs.
   stained paper). A constant default invites copy-through. Require the reader to set a
   per-reading sigma from stated criteria (e.g. clean rule ≈ half line width; obstructed
   or doubled rule ≥ 2×), and flag any file where every sigma is identical.
2. **Rejected controls are not retained.** Only accepted controls reach the verified
   store; rejects exist nowhere (harvest candidates are proposals, not adjudications).
   For auditability the store needs rejected entries with reasons — otherwise a future
   session cannot tell "considered and rejected" from "never examined".
3. **No axis/sign convention stated.** All coordinates are raster pixels, y increasing
   downward, origin at scan top-left — true, but nowhere written. One session working in
   flipped convention would corrupt the network silently. State it once in the protocol.
4. **Control records are not tied to source checksums.** `INVENTORY.json` holds SHA-256
   per scan; control records should carry the source file's hash (or inventory reference)
   so a re-scan or file substitution invalidates measurements loudly.
5. **The street-width sanity check has no recorded basis.** The check "separation must
   agree with the drafted street width" is only as good as the width evidence; require
   each control to cite the width annotation used (value + where it is printed), or mark
   the check inapplicable.

## Two structural observations (no action required, but the controller should be aware)

- The protocol's coverage target (~29 controls) counts interior crossing features only.
  For **corner sheets of the block (7, 40, 11, 50)** this leaves their outermost corners
  governed by no control at all; the determinability review (separate note) examines
  whether the network still pins their rotation/scale adequately.
- The protocol is silent on **junction points** (4-sheet corners, e.g. 21st×Mechanic
  where 7/8/9/10 meet). They need not be controls, but the protocol should say explicitly
  that junction QA panels are the place where the four solved plates are checked against
  each other, so the omission is a decision rather than a gap.

## Classification

**READY FOR OPUS RECONCILIATION** — adopt the missing fields and the two default fixes
before the first verified control is recorded; nothing here blocks measurement work from
starting under the amended schema.
