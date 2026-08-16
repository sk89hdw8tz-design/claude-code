# Galveston 1912 Sanborn Mosaic — Decision Log

Chronological record of project decisions, their rationale, and evidence.

## D-001 — Source acquisition route (2026-08-16)

**Problem.** Both Claude Code environments ("Test", "Default") enforce a strict egress
allowlist (package registries + GitHub only). All archival hosts — maps.lib.utexas.edu,
www.loc.gov, tile.loc.gov, web.archive.org — are denied at the gateway (verified by direct
probes in this session and by a dedicated probe session on the Default environment; see
`galveston_1912_sources/STATUS.md` on branch `claude/galveston-1912-source-data`).

**Decision.** With the user's explicit approval, acquisition runs in GitHub Actions on the
user's fork (runners have ordinary internet egress): workflow
`.github/workflows/fetch-1912-sources.yml` on branch `claude/galveston-1912-source-data`
downloads the complete Galveston 1912 set (key, index, all sheets) from the UT Austin PCL
index page `https://maps.lib.utexas.edu/maps/sanborn/g.html`, verifies JPEG magic bytes,
records SHA-256 + exact source URL per file in `inventory.json`, and commits the unmodified
files back to the same data branch, which the session then pulls (GitHub is allowlisted).

**Alternatives considered.**
- Environment network-policy change to allow loc.gov: cleaner, and LOC serves higher
  resolution (volume `sanborn08539`, 77 sheets), but requires user settings change + fresh
  session. Kept as an upgrade path.
- Direct upload by user: declined by user.
- No other GitHub-reachable mirror of the rasters exists (searched).

**Precedent.** The accepted 1889 and 1899 mosaics (branches
`claude/galveston-1889-sanborn-mosaic-1h5aoc`, `claude/galveston-1899-sanborn-maps-g5pfqc`)
were built from the same UT PCL web JPGs (~3400×4100 px, 300 dpi, ~2.6 MB) — demonstrating
that this source meets the accepted print standard (the 1899 benchmark print is 11817×7965 px
@ 300 dpi from 13 such sheets).

## D-002 — Print target (2026-08-16)

The supplied 1899 benchmark PDF measures: single page, 39.39×26.55 in, one embedded baseline
JPEG 11817×7965 px, 8-bit DeviceRGB, exactly 300.0 DPI. The 1912 master targets the same
standard: ~300 DPI large-format, extent determined by the solved 1912 geography (not copied
from 1899).

## D-003 — Prior-edition independence (2026-08-16)

Prior-project branches contain 1889/1899 controls, seams, and tooling. Per the brief and the
user's "build fresh" instruction: 1912 sheet identity, topology, controls, and geometry are
solved independently from the 1912 Key and plates. Prior branches are used only as (a) process
precedent and (b) presentation benchmark. No geometric data is transferred between editions.
