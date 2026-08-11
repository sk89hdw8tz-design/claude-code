# SEED_PRE1900 — seed package for the 1877 / 1885 / 1889 Galveston posters

**Start with `PROMPT.md`.** Paste it as the opening message of a new session.

The 1899 poster is finished and is not to be rebuilt; it is the benchmark
and the worked example throughout this package.

| File | What it is |
|---|---|
| **`PROMPT.md`** | the master prompt — mission, sources, playbook, team, gates |
| `LESSONS.md` | every 1899 lesson in detail, with pointers into `sanborn/*.py` |
| `EXTENT.md` | the frame in grid terms, candidate sheet sets per edition, scan locations, constants to derive |
| `landmarks.json` | 1899's 77 ground-truth features — the schema and a worked set |
| `constants.json` | 1899 grid constants, anchors, seam inventory |
| `KNOWN_DEFECTS.md` | the complete measured history, including retractions |
| `REFERENCE_REPORT_1899.md` | the production-report format and the benchmark numbers |
| `repaired_metrics.json` | 1899's final guard metrics |
| `tools/landmark_check.py` | the anti-circular alignment gate |
| `tools/build_metrics.py` | coverage / pure-white / pure-black guards |
| `tools/tint_bay.py` | water region detection + flat waterline fill |

Scans: 1889 is already fetched on branch `sanborn-data-1889` (62 sheets +
`SHA256SUMS`); 1899 on `sanborn-data-1899`; 1877 and 1885 links are in
`sources/1889/ALL_GALVESTON_LINKS.txt` on the 1889 branch.

Non-negotiable across every build in this project: **no generated,
inferred, or cloned map content, ever.** Gaps are flat paper, measured and
disclosed.
