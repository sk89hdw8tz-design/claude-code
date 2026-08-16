# STATUS — Galveston 1912 Sanborn Map Acquisition

**Result: ACQUISITION NOT POSSIBLE FROM THIS SESSION — ALL SOURCE HOSTS BLOCKED BY NETWORK EGRESS POLICY.**

No map files were downloaded. This directory contains only this status file.

## Egress probe results

Probes run at **2026-08-16T23:08:46Z – 2026-08-16T23:08:47Z UTC** via `curl` through the
session's mandatory HTTPS agent proxy:

| URL | Result |
|---|---|
| https://maps.lib.utexas.edu/maps/sanborn/g.html | `curl: (56) CONNECT tunnel failed, response 403` (HTTP 000, 0.35s) |
| https://www.loc.gov/item/sanborn08539_006/ | `curl: (56) CONNECT tunnel failed, response 403` (HTTP 000, 0.31s) |
| https://tile.loc.gov/ | `curl: (56) CONNECT tunnel failed, response 403` (HTTP 000, 1.28s) |
| https://web.archive.org/ | `curl: (56) CONNECT tunnel failed, response 403` (HTTP 000, 0.28s) |

## Confirmation the block is policy, not transient

The agent proxy status endpoint (`$HTTPS_PROXY/__agentproxy/status`, checked
2026-08-16T23:08:47Z UTC) logged all four attempts as:

```
kind: connect_rejected
detail: gateway answered 403 to CONNECT (policy denial or upstream failure)
hosts: maps.lib.utexas.edu:443, www.loc.gov:443, tile.loc.gov:443, web.archive.org:443
```

The proxy runs in non-selective mode (`"selective": false`) with an allowlist limited to
package registries (npm, PyPI, crates.io, proxy.golang.org, jsr.io) and Anthropic domains.
General web hosts are denied at the CONNECT stage, so no HTTPS request ever reaches the
target servers.

An out-of-band check via the WebFetch tool (server-side fetch path) at approximately
2026-08-16T23:10Z UTC also failed for `https://www.loc.gov/item/sanborn08539_006/?fo=json`
with `EGRESS_BLOCKED: Access to www.loc.gov is blocked by the network egress proxy`.
(Even if WebFetch had succeeded, it returns processed text only and cannot deliver
unmodified binary image files, so it could not have substituted for direct downloads.)

## Conclusion and guidance for the consuming session

- **UT Austin PCL (maps.lib.utexas.edu): BLOCKED**
- **Library of Congress (www.loc.gov, tile.loc.gov): BLOCKED**
- **Internet Archive (web.archive.org): BLOCKED**

Per the task instructions ("If ALL hosts are blocked, say so in STATUS.md, push, and
stop"), acquisition was aborted after the probe step. Steps 2–5 (index download, sheet
selection, sheet download, inventory) were not attempted.

To complete the acquisition, re-run this task in a session whose environment network
policy permits egress to `maps.lib.utexas.edu`, `www.loc.gov`, and `tile.loc.gov`
(e.g. an environment configured with an unrestricted or appropriately allowlisted
network policy in Claude Code on the web environment settings). The intended sources
remain:

- UT Austin: https://maps.lib.utexas.edu/maps/sanborn/g.html (Galveston 1912 entry; web-resolution JPGs)
- Library of Congress (preferred, higher resolution): volume `sanborn08539`, 1912 Galveston,
  77 sheets — item pages `https://www.loc.gov/item/sanborn08539_00N/` (check _005/_006/_007
  for the 1912 volume); per-image download URLs listed in the item JSON (`?fo=json`) on
  `tile.loc.gov`.
