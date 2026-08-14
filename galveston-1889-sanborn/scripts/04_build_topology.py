#!/usr/bin/env python3
"""04 -- Validate the sheet topology and emit config/sheet_topology.yaml.

The topology says which mapped region sits next to which, in what direction,
and along which shared street. It is DERIVED BY A HUMAN from the 1889 Key,
from continuation notes printed at sheet edges, and from streets that run
across a join -- and then checked here. This script does not infer adjacency
from imagery; it verifies that what a human recorded is internally consistent
and complete enough to build on.

Checks performed
    * every region named exists in the profile (catches typos and stale ids)
    * every adjacency is symmetric, with opposite directions on the two sides
    * no region claims two different neighbours in the same direction
    * the adjacency graph is connected -- a region with no path to the anchor
      cannot be placed by tie points at all
    * excluded regions (Sheet 1's detached section) appear in no adjacency

Refuses to emit a topology for a profile whose `verified` flag is false, so an
unchecked layout can never reach the mosaic.

Outputs
    config/sheet_topology.yaml
    output/qc/topology.md
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn.config import (all_regions, load_config, paths, regions_from_config,
                            setup_logging, utcnow, write_yaml)

OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east",
            "northeast": "southwest", "southwest": "northeast",
            "northwest": "southeast", "southeast": "northwest"}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--allow-unverified", action="store_true",
                    help="emit anyway (for inspecting a work-in-progress layout)")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("04_build_topology")

    verified = bool(cfg.get("verified", False))
    if not verified and not args.allow_unverified:
        log.error("profile %r is marked verified: false", args.profile)
        log.error("%s", (cfg.get("verification_note") or "").strip())
        log.error("Open the 1889 Key, fill in the sheets/topology entries, set "
                  "verified: true, then re-run. Nothing was written.")
        return 2

    kept = {r["region_id"] for r in regions_from_config(cfg)}
    excluded = {r["id"] for r in all_regions(cfg) if not r.get("keep", True)}
    known = kept | excluded
    entries = cfg.get("topology") or []
    if not entries:
        log.error("profile %r declares no topology. Derive it from the Key.",
                  args.profile)
        return 3

    problems, warnings = [], []
    pairs = {}
    by_dir = defaultdict(dict)
    adj = defaultdict(set)

    for i, e in enumerate(entries):
        a, b = e.get("region"), e.get("neighbour")
        d = str(e.get("direction", "")).lower().strip()
        where = f"topology[{i}] ({a} -> {b})"
        if a not in known:
            problems.append(f"{where}: unknown region {a!r}")
            continue
        if b not in known:
            problems.append(f"{where}: unknown neighbour {b!r}")
            continue
        if a in excluded or b in excluded:
            problems.append(
                f"{where}: references an EXCLUDED region -- a region that is not "
                f"kept must not participate in adjacency")
            continue
        if d and d not in OPPOSITE:
            problems.append(f"{where}: direction {d!r} is not one of {sorted(OPPOSITE)}")
        if not e.get("shared_street"):
            warnings.append(f"{where}: no shared_street recorded")
        if str(e.get("confidence", "")).lower() not in ("high", "medium", "low"):
            warnings.append(f"{where}: confidence should be high/medium/low")
        if not e.get("source"):
            warnings.append(f"{where}: no source recorded (Key? printed continuation note?)")

        if d:
            prev = by_dir[a].get(d)
            if prev and prev != b:
                problems.append(f"{where}: {a} already has neighbour {prev!r} to the {d}")
            by_dir[a][d] = b
        key = tuple(sorted([a, b]))
        if key in pairs and pairs[key]["direction"] != d:
            # Recorded from both sides: directions must be opposites.
            if OPPOSITE.get(pairs[key]["direction"]) != d:
                problems.append(
                    f"{where}: recorded from both sides with non-opposite "
                    f"directions ({pairs[key]['direction']} vs {d})")
        pairs.setdefault(key, {"direction": d, "entry": e})
        adj[a].add(b)
        adj[b].add(a)

    # connectivity from the anchor
    anchor = (cfg.get("geometry") or {}).get("anchor_region") or ""
    if anchor and anchor not in kept:
        problems.append(f"geometry.anchor_region {anchor!r} is not a kept region")
        anchor = ""
    if not anchor:
        warnings.append("geometry.anchor_region is not set; the adjustment will "
                        "hold the first region fixed, which may not be central")
        anchor = sorted(kept)[0] if kept else ""
    if anchor:
        seen, stack = {anchor}, [anchor]
        while stack:
            cur = stack.pop()
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        orphans = sorted(kept - seen)
        if orphans:
            problems.append(
                f"regions with no adjacency path to anchor {anchor!r}: {orphans} "
                f"-- these cannot be positioned")

    isolated = sorted(r for r in kept if not adj[r])
    for r in isolated:
        problems.append(f"region {r!r} has no recorded neighbour")

    for w in warnings:
        log.warning("%s", w)
    for e in problems:
        log.error("%s", e)
    if problems:
        log.error("topology is INCONSISTENT -- %d problem(s). Nothing written.",
                  len(problems))
        return 4

    log.info("topology OK: %d region(s), %d adjacency pair(s), anchor=%s",
             len(kept), len(pairs), anchor)
    for (a, b), v in sorted(pairs.items()):
        log.info("   %-14s <-> %-14s %-10s %s", a, b, v["direction"],
                 v["entry"].get("shared_street", ""))

    doc = {
        "generated_utc": utcnow(),
        "profile": args.profile,
        "verified": verified,
        "anchor_region": anchor,
        "regions": [
            {"region": r["region_id"], "sheet": r["sheet"],
             "keep": True, "neighbours": sorted(adj[r["region_id"]]),
             "mask": r["mask"], "note": r["note"]}
            for r in regions_from_config(cfg)
        ] + [
            {"region": rid, "sheet": next(x["sheet"] for x in all_regions(cfg)
                                          if x["id"] == rid),
             "keep": False, "neighbours": [],
             "note": "excluded from the mosaic; retained here for the record"}
            for rid in sorted(excluded)
        ],
        "adjacency": [
            {"region": a, "neighbour": b,
             "direction": v["direction"],
             "shared_street": v["entry"].get("shared_street", ""),
             "confidence": v["entry"].get("confidence", ""),
             "source": v["entry"].get("source", ""),
             "note": v["entry"].get("note", "")}
            for (a, b), v in sorted(pairs.items())
        ],
        "warnings": warnings,
    }
    out = write_yaml(p.config / "sheet_topology.yaml", doc, header=(
        "Verified sheet topology -- generated by 04_build_topology.py.\n"
        "Derived from the 1889 Key and printed continuation notes, then checked\n"
        "for symmetry, direction conflicts and connectivity. Do not hand-edit;\n"
        "edit the profile and re-run so the checks are applied."))
    log.info("wrote %s", out)

    md = ["# Sheet topology", "", f"Profile `{args.profile}` -- {doc['generated_utc']}",
          "", f"Anchor region: `{anchor}`", "",
          "| region | neighbour | direction | shared street | confidence | source |",
          "|---|---|---|---|---|---|"]
    for a in doc["adjacency"]:
        md.append(f"| {a['region']} | {a['neighbour']} | {a['direction']} | "
                  f"{a['shared_street']} | {a['confidence']} | {a['source']} |")
    if excluded:
        md += ["", "## Excluded regions", ""]
        for rid in sorted(excluded):
            md.append(f"- `{rid}` -- excluded by mask; not part of any adjacency")
    if warnings:
        md += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    (p.qc / "topology.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log.info("wrote %s", p.qc / "topology.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
