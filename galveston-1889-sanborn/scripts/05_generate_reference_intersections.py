#!/usr/bin/env python3
"""05 -- Reference street-intersection coordinates (OpenStreetMap).

This feeds the SECONDARY product only: the modern-georeferenced derivative.
The historical reconstruction never consumes it, because forcing 1889 survey
geometry onto modern centrelines is exactly the distortion this project is
meant to avoid. Intersections are used to place the finished reconstruction in
the world, not to reshape it.

Only public reference data leaves the machine here -- a street-network query.
No map imagery is uploaded, which keeps the privacy requirement intact.

OPTIONAL. If the network is unavailable or OSMnx is not installed, this exits
cleanly with a warning: the historical master does not depend on it.

Outputs
    data/reference/intersections.geojson
    data/reference/intersections_meta.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sanborn.config import load_config, paths, setup_logging, utcnow, write_json


def normalise(name, rules):
    if not name:
        return ""
    s = str(name).upper()
    if rules.get("strip_punctuation", True):
        s = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in s)
    if rules.get("collapse_whitespace", True):
        s = " ".join(s.split())
    expand = rules.get("expand") or {}
    parts = [expand.get(tok, tok) for tok in s.split()]
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default="galveston1889")
    ap.add_argument("--place", default="Galveston, Texas, USA")
    args = ap.parse_args()

    cfg = load_config(args.profile)
    p = paths().ensure()
    log = setup_logging("05_generate_reference_intersections")

    if not (cfg.get("georeference") or {}).get("enabled", True):
        log.info("profile %r disables georeferencing -- skipping.", args.profile)
        return 0

    try:
        import osmnx as ox
    except ImportError:
        log.warning("osmnx is not installed. Skipping reference intersections.")
        log.warning("The historical master does not need them; only the "
                    "GEOREF derivative does. Install with: pip install osmnx")
        return 0

    import yaml
    alias_path = p.config / "street_aliases.yaml"
    rules = {}
    if alias_path.exists():
        rules = (yaml.safe_load(alias_path.read_text(encoding="utf-8")) or {}) \
            .get("normalisation", {})

    log.info("querying OpenStreetMap for %s ...", args.place)
    try:
        Gr = ox.graph_from_place(args.place, network_type="drive", simplify=True)
    except Exception as exc:
        log.warning("OSM query failed (%s: %s).", type(exc).__name__, exc)
        log.warning("If this is a network-policy denial, run this step from a "
                    "machine with ordinary internet access. The historical "
                    "master is unaffected.")
        return 0

    feats = []
    for node, data in Gr.nodes(data=True):
        names = set()
        for _, _, ed in list(Gr.in_edges(node, data=True)) + list(Gr.out_edges(node, data=True)):
            nm = ed.get("name")
            if isinstance(nm, (list, tuple)):
                names.update(nm)
            elif nm:
                names.add(nm)
        if len(names) < 2:
            continue                      # not an intersection of named streets
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(data["x"]), float(data["y"])]},
            "properties": {
                "osm_id": int(node),
                "streets": sorted(names),
                "streets_normalised": sorted({normalise(n, rules) for n in names}),
            },
        })

    write_json(p.reference / "intersections.geojson",
               {"type": "FeatureCollection", "crs_note": "EPSG:4326 lon/lat",
                "features": feats})
    write_json(p.reference / "intersections_meta.json",
               {"generated_utc": utcnow(), "place": args.place,
                "source": "OpenStreetMap via OSMnx",
                "licence": "ODbL 1.0 -- (c) OpenStreetMap contributors",
                "count": len(feats),
                "note": "Reference only. Used for the modern-georeferenced "
                        "derivative; never used to reshape the historical mosaic."})
    log.info("wrote %d named-street intersections", len(feats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
