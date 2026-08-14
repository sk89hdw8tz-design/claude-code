"""Project configuration, paths, and logging.

Everything the pipeline does that a human decided -- which sheets, which
regions are kept, where a mask polygon sits, which transform family is allowed
-- lives in `config/` as YAML, never in code.  That is what makes a hand
correction reproducible: you fix the file, re-run, and get the same answer
every time.

Profiles let one pipeline serve two jobs: `galveston1889` (the real sheets) and
`synthetic` (the self-test fixture), so the code that ships is the code that
was tested.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def config(self): return self.root / "config"
    @property
    def original(self): return self.root / "data" / "original"
    @property
    def reference(self): return self.root / "data" / "reference"
    @property
    def proxies(self): return self.root / "data" / "proxies"
    @property
    def masks(self): return self.root / "masks"
    @property
    def gcps(self): return self.root / "gcps"
    @property
    def working(self): return self.root / "working"
    @property
    def warped(self): return self.root / "working" / "warped"
    @property
    def georeferenced(self): return self.root / "georeferenced"
    @property
    def output(self): return self.root / "output"
    @property
    def qc(self): return self.root / "output" / "qc"
    @property
    def seams(self): return self.root / "output" / "qc" / "seam_report"
    @property
    def logs(self): return self.root / "logs"

    def ensure(self):
        for p in (self.config, self.original, self.reference, self.proxies,
                  self.masks, self.gcps, self.working, self.warped,
                  self.georeferenced, self.output, self.qc, self.seams, self.logs):
            p.mkdir(parents=True, exist_ok=True)
        return self


def paths(root=None) -> Paths:
    return Paths(Path(root) if root else ROOT)


class Config(dict):
    """Loaded project configuration with profile overlay."""

    @property
    def profile(self):
        return self.get("_profile", "")

    def require(self, dotted, why=""):
        cur = self
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                raise KeyError(
                    f"config key {dotted!r} is missing" + (f" ({why})" if why else ""))
            cur = cur[part]
        return cur


def load_config(profile="galveston1889", root=None) -> Config:
    p = paths(root)
    base = _read_yaml(p.config / "project.yaml")
    prof_path = p.config / "profiles" / f"{profile}.yaml"
    if not prof_path.exists():
        avail = sorted(x.stem for x in (p.config / "profiles").glob("*.yaml"))
        raise FileNotFoundError(
            f"no profile {profile!r} in {p.config / 'profiles'} (available: {avail})")
    prof = _read_yaml(prof_path)
    merged = _deep_merge(base, prof)
    merged["_profile"] = profile
    merged["_root"] = str(p.root)
    return Config(merged)


def _read_yaml(path):
    path = Path(path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def write_yaml(path, obj, header=""):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=100)
    if header:
        text = "".join(f"# {line}\n" for line in header.strip().splitlines()) + text
    path.write_text(text, encoding="utf-8")
    return path


def _deep_merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=_jsonable) + "\n", encoding="utf-8")
    return path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class ProfileMismatch(RuntimeError):
    pass


def require_profile(doc, profile, path, log=None):
    """Refuse to consume an intermediate produced under a different profile.

    All steps write to fixed paths, so without this check a run of one profile
    would happily pick up another's transforms, grid or control points and
    produce a mosaic labelled `galveston1889` built from synthetic pixels. That
    failure is silent and the output looks plausible, which makes it exactly
    the kind of error this project cannot afford.
    """
    got = (doc or {}).get("profile")
    if got is None:
        msg = (f"{path}: no profile recorded. It predates this check -- delete it "
               f"and re-run the step that produces it.")
    elif got != profile:
        msg = (f"{path}: produced under profile {got!r}, but this run is "
               f"{profile!r}. Refusing to mix profiles. Delete working/, gcps/ "
               f"and output/ (or re-run from step 06) before switching profile.")
    else:
        return
    if log:
        log.error("%s", msg)
    raise ProfileMismatch(msg)


def _jsonable(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    return str(o)


def setup_logging(name, root=None, level=logging.INFO):
    p = paths(root)
    p.logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logfile = p.logs / f"{stamp}__{name}.log"
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%H:%M:%S")
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.info("log file: %s", logfile)
    return logger


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path, chunk=1 << 20):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def regions_from_config(cfg):
    """Flatten config sheets -> the list of mapped regions actually kept.

    A sheet may carry more than one mapped region (Sheet 1 does), so regions,
    not sheets, are the unit everything downstream works with.
    """
    out = []
    for sheet in cfg.get("sheets", []):
        for reg in sheet.get("regions", []):
            if not reg.get("keep", True):
                continue
            out.append({
                "region_id": reg["id"],
                "sheet": str(sheet["id"]),
                "sheet_file": sheet.get("file", ""),
                "priority": reg.get("priority", sheet.get("priority", 100)),
                "mask": reg.get("mask", ""),
                "note": reg.get("note", ""),
            })
    return out


def all_regions(cfg):
    """Every declared region, including excluded ones (for reporting)."""
    out = []
    for sheet in cfg.get("sheets", []):
        for reg in sheet.get("regions", []):
            out.append({**reg, "sheet": str(sheet["id"]),
                        "sheet_file": sheet.get("file", "")})
    return out
