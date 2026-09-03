#!/usr/bin/env python3
"""journalq.py -- persist a subagent Workflow's journal into a durable QC record.

Round-5 census, the periphery review and the interior review were run as
Workflow subagent teams. Their only record is journal.jsonl inside each
workflow's directory under
`/root/.claude/projects/<project>/subagents/workflows/<workflow-id>/`
(one `{"type": "result", ...}` line per agent turn; an agent that was
re-prompted appears more than once, and only its LAST result should count).
Nothing under `outputs/1912/qc/` captured that record before this tool, so a
re-run of the same workflow (or a container recycle) would have lost the
census/review scores permanently.

This tool reads journal.jsonl, keeps only `type == "result"` lines, keeps the
LAST result per agentId, and merges the survivors into one JSON document keyed
by seam or window, split by --kind:

  census      result["seams"] (list of {"seam": ..., "score": ...})
              keyed by seam, merged with adjudication-diagnosis results
              (identifiable by an "agree" key) collected into a "diagnoses"
              list per seam.
  periphery   result["windows"] (list of {"window": ..., ...})
              keyed by window, merged with confirm results (identifiable by
              a "confirmed" key) collected into a "confirms" list per window.
  interior    result objects that themselves carry a "clean" key, keyed by
              window, merged with confirm results (identifiable by a
              "confirmed" key) collected into a "checks" list per window.

Every entry records which workflow and agentId produced it. The output also
carries a "summary" block (counts and, for census, a score histogram) so the
numbers can be sanity-checked against the source journal without re-deriving
them by hand.

Usage:
    python3 tools/journalq.py --workflow-dir <dir> --out <file.json> --kind census
    python3 tools/journalq.py --workflow-dir <dir> --out <file.json> --kind periphery
    python3 tools/journalq.py --workflow-dir <dir> --out <file.json> --kind interior

This tool only reads the journal and writes the QC record; it never touches
the recipe, units.json, or anything under inputs/.
"""

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict


def load_last_results(workflow_dir):
    """Read journal.jsonl, keep type=='result' lines, last one per agentId.

    Returns a list of result lines (dicts with at least "agentId" and
    "result") in first-seen-agent order, each value being the LAST result
    seen for that agentId.
    """
    path = os.path.join(workflow_dir, "journal.jsonl")
    last_by_agent = OrderedDict()
    with open(path, "r") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"warning: {path}:{lineno}: skipping malformed JSON ({exc})",
                      file=sys.stderr)
                continue
            if rec.get("type") != "result":
                continue
            agent_id = rec.get("agentId")
            if agent_id is None:
                continue
            # Overwrite so the LAST result for this agentId wins; order of
            # first appearance is preserved via OrderedDict re-insertion
            # semantics (Python moves nothing on plain assignment, which is
            # what we want -- position is irrelevant, only "last write wins"
            # matters).
            last_by_agent[agent_id] = rec
    return list(last_by_agent.values())


def workflow_id_from_dir(workflow_dir):
    return os.path.basename(os.path.normpath(workflow_dir))


def build_census(results, workflow_dir):
    wf_id = workflow_id_from_dir(workflow_dir)
    seams = OrderedDict()

    for rec in results:
        agent_id = rec.get("agentId")
        result = rec.get("result") or {}
        if "seams" in result and isinstance(result["seams"], list):
            for s in result["seams"]:
                seam_key = s.get("seam")
                if seam_key is None:
                    continue
                entry = dict(s)
                entry["workflow"] = wf_id
                entry["agentId"] = agent_id
                entry["diagnoses"] = []
                seams[seam_key] = entry
        elif "agree" in result:
            seam_key = result.get("seam")
            if seam_key is None:
                continue
            diag = dict(result)
            diag["agentId"] = agent_id
            if seam_key not in seams:
                # Diagnosis arrived without (or before) its base grading
                # entry -- keep it, but flag that the base row is missing.
                seams[seam_key] = {
                    "seam": seam_key,
                    "workflow": wf_id,
                    "agentId": None,
                    "score": None,
                    "diagnoses": [],
                    "note": "no base grading result found for this seam",
                }
            seams[seam_key]["diagnoses"].append(diag)

    hist = Counter(s["score"] for s in seams.values() if s.get("score") is not None)
    summary = {
        "workflow": wf_id,
        "total_results": len(results),
        "total_seams": len(seams),
        "score_histogram": {str(k): v for k, v in sorted(hist.items(), reverse=True)},
        "seams_with_diagnoses": sum(1 for s in seams.values() if s["diagnoses"]),
    }
    return {
        "workflow": wf_id,
        "kind": "census",
        "seams": seams,
        "summary": summary,
    }


def build_periphery(results, workflow_dir):
    wf_id = workflow_id_from_dir(workflow_dir)
    windows = OrderedDict()

    for rec in results:
        agent_id = rec.get("agentId")
        result = rec.get("result") or {}
        if "windows" in result and isinstance(result["windows"], list):
            for w in result["windows"]:
                win_key = w.get("window")
                if win_key is None:
                    continue
                entry = dict(w)
                entry["workflow"] = wf_id
                entry["agentId"] = agent_id
                entry["confirms"] = []
                windows[win_key] = entry
        elif "confirmed" in result:
            win_key = result.get("window")
            if win_key is None:
                continue
            confirm = dict(result)
            confirm["agentId"] = agent_id
            if win_key not in windows:
                windows[win_key] = {
                    "window": win_key,
                    "workflow": wf_id,
                    "agentId": None,
                    "confirms": [],
                    "note": "no base finding result found for this window",
                }
            windows[win_key]["confirms"].append(confirm)

    total_confirms = sum(len(w["confirms"]) for w in windows.values())
    confirmed_true = sum(
        1 for w in windows.values() for c in w["confirms"] if c.get("confirmed") is True
    )
    summary = {
        "workflow": wf_id,
        "total_results": len(results),
        "total_windows": len(windows),
        "total_confirms": total_confirms,
        "confirms_confirmed_true": confirmed_true,
    }
    return {
        "workflow": wf_id,
        "kind": "periphery",
        "windows": windows,
        "summary": summary,
    }


def build_interior(results, workflow_dir):
    wf_id = workflow_id_from_dir(workflow_dir)
    windows = OrderedDict()

    for rec in results:
        agent_id = rec.get("agentId")
        result = rec.get("result") or {}
        if "clean" in result:
            win_key = result.get("window")
            if win_key is None:
                continue
            entry = dict(result)
            entry["workflow"] = wf_id
            entry["agentId"] = agent_id
            entry["checks"] = []
            windows[win_key] = entry
        elif "confirmed" in result:
            win_key = result.get("window")
            if win_key is None:
                continue
            check = dict(result)
            check["agentId"] = agent_id
            if win_key not in windows:
                windows[win_key] = {
                    "window": win_key,
                    "workflow": wf_id,
                    "agentId": None,
                    "checks": [],
                    "note": "no base window result found for this window",
                }
            windows[win_key]["checks"].append(check)

    total_checks = sum(len(w["checks"]) for w in windows.values())
    checks_confirmed_true = sum(
        1 for w in windows.values() for c in w["checks"] if c.get("confirmed") is True
    )
    clean_true = sum(1 for w in windows.values() if w.get("clean") is True)
    summary = {
        "workflow": wf_id,
        "total_results": len(results),
        "total_windows": len(windows),
        "windows_clean_true": clean_true,
        "total_checks": total_checks,
        "checks_confirmed_true": checks_confirmed_true,
    }
    return {
        "workflow": wf_id,
        "kind": "interior",
        "windows": windows,
        "summary": summary,
    }


BUILDERS = {
    "census": build_census,
    "periphery": build_periphery,
    "interior": build_interior,
}


def main():
    ap = argparse.ArgumentParser(
        description="Extract a durable QC record from a Workflow subagent journal.jsonl."
    )
    ap.add_argument("--workflow-dir", required=True,
                     help="Directory containing journal.jsonl for the workflow run.")
    ap.add_argument("--out", required=True, help="Path to write the merged JSON record.")
    ap.add_argument("--kind", required=True, choices=sorted(BUILDERS.keys()),
                     help="Which merge shape to build: census, periphery, or interior.")
    args = ap.parse_args()

    results = load_last_results(args.workflow_dir)
    if not results:
        print(f"error: no type==result lines found in {args.workflow_dir}/journal.jsonl",
              file=sys.stderr)
        sys.exit(1)

    doc = BUILDERS[args.kind](results, args.workflow_dir)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(doc, fh, indent=2, sort_keys=False)
        fh.write("\n")

    print(f"wrote {args.out}")
    print(json.dumps(doc["summary"], indent=2))


if __name__ == "__main__":
    main()
