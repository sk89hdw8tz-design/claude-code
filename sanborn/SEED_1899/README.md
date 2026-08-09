# SEED_1899 — start the rebuild at the frontier

Everything a fresh session needs to rebuild the Galveston 1899 wharf-front
and downtown composite **and beat the existing one on measured numbers**,
without re-deriving work that is already verified.

## Use it

1. Open a new session with this directory available.
2. Paste `PROMPT.md` as the opening message.
3. Rendition 1 calibrates and measures. Rendition 2 is the deliverable.

## What's here

```
PROMPT.md              the rebuild prompt — paste this
constants.json         verified pitches, corridor width, slot model, sources
coverage_1899.json     90 registration units, ground extents, panel regions
survey/                verbatim labels + edge refs, all 94 sheets
pair_context.json      each sheet pair's shared line, per sheet, in native px
landmarks.json         GROUND TRUTH: the same physical object located in two
                       sheets' native frames, double-measured
baseline_metrics.json  the prior build's guard metrics
KNOWN_DEFECTS.md       every remaining defect, measured, with method
tools/landmark_check.py  the anti-circular registration gate
tools/build_metrics.py   guard-metric suite
tools/sanborn-fetch-1899.yml  acquisition via CI proxy
```

## The two tools are the point

**`landmark_check.py`** is the gate that the prior build lacked. Give it
`landmarks.json` and your build's per-sheet transforms; it maps each landmark
through both sheets' transforms and reports the disagreement. That
disagreement *is* the registration error at that point.

It cannot be fooled the way fit residuals can. In the prior build residuals
stayed under 15 px while a sheet's content sat **114 px** out of place,
because a uniform per-sheet bias is absorbed by the translation term. Every
automated gate passed. A human noticed the same fire hydrant drawn twice.

```
python3 tools/landmark_check.py landmarks.json <build>/registration.json --max 8
```

It also groups by pair and reports mean dx/dy with spread — a consistent
offset across a pair's landmarks means a rigid misregistration, which is the
easily fixable kind. Scattered values mean local distortion, which usually
means a non-uniform warp is hiding something.

**`build_metrics.py`** is the regression guard. Run it before and after every
change; reject anything that regresses a guard metric.

```
python3 tools/build_metrics.py composite.png coverage_mask.png \
        --crop x0,y0,x1,y1 baseline_metrics.json
```

Pass `--crop` when the composite is a crop of a larger canvas — otherwise
coverage compares mismatched regions and reports nonsense (34.7% instead of
99.0%, which happened while building this).

## How landmarks.json was produced

One agent per boundary located physical objects drawn on **both** sheets of
each pair — hydrant dots, building corners, rail crossings, pier corners —
and reported each object's coordinate in each sheet's own native pixel frame.
A **second, independent agent** then re-located every object from its written
description alone, without seeing the first agent's coordinates. Features
carry both measurements plus an agreement figure, so you can weight or
discard the shaky ones.

Deliberately excluded: long featureless lines (a point on a line is ambiguous
along it), text, and anything drawn only once.

## What is already true, and shouldn't be re-litigated

- Avenue pitch **1006 px**, street pitch **1169 px** (autocorrelation, 62
  sheets). Street corridor width **245 px**.
- Corridor identities verified by label reading across 90 units, ~340 checks.
- The `s`-suffix sheets are July-1899 skeleton house-numbering sheets, not
  revisions — use the coloured base sheets.
- Adjacent sheets **overlap**: ~230 px on the wharf, 50–70 px inland. Both
  sheets draw the shared street and both facing frontages.
- Sheet numbers differ between editions. The target extent corresponds to
  sheets 1, 2, 7, 8, 9, 10, 27, 29 on the **1889** key.
