# Galveston Sanborn Full-City Build — Claude Code Prompt

Two parts. **Part A** is the five-minute setup you do once. **Part B** is the prompt you paste into Claude Code, from the marked line to the end of the file.

---

## Part A — Setup (do this before pasting)

1. **Make the project folder and drop the masters in.**
   ```bash
   mkdir galveston-sanborn && cd galveston-sanborn && git init
   mkdir -p inputs/masters
   cp ~/Downloads/Galveston_1899_Wharf_Downtown_27x40_Master_8-27-26.pdf inputs/masters/
   cp ~/Downloads/Galveston_1912_Wharf_Downtown_27x40_Master_8-27-26.pdf inputs/masters/
   ```

2. **Install the two native libraries the pipeline needs** (everything else is pip-installable).
   ```bash
   # macOS
   brew install libvips gdal
   # Ubuntu / WSL
   sudo apt install libvips-dev libvips-tools gdal-bin libgdal-dev
   ```

3. **Create `.claude/settings.json`** so the run doesn't stall on permission prompts every few minutes, and so agent timing gets logged for the dashboard:
   ```json
   {
     "permissions": {
       "allow": [
         "Bash(python *)", "Bash(python3 *)", "Bash(uv *)", "Bash(pip *)",
         "Bash(vips *)", "Bash(gdal*)", "Bash(rio *)", "Bash(git *)",
         "Bash(make *)", "Bash(curl *)", "Bash(ls *)", "Bash(mkdir *)",
         "Read", "Write", "Edit", "WebFetch"
       ],
       "deny": [
         "Bash(rm -rf *)",
         "Write(inputs/**)", "Edit(inputs/**)"
       ]
     },
     "env": {
       "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "0",
       "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "12"
     },
     "hooks": {
       "SubagentStart": [{ "hooks": [{ "type": "command", "command": "python tools/ledger.py event start" }] }],
       "SubagentStop":  [{ "hooks": [{ "type": "command", "command": "python tools/ledger.py event stop" }] }]
     }
   }
   ```
   The `deny` on `inputs/**` is a hard backstop: no agent can touch your 27×40 masters or the downloaded scans, no matter what it decides.

4. **Start Claude Code on Fable at high effort.**
   ```bash
   claude --model claude-fable-5
   /effort high
   ```

5. **Paste Part B.** Then open `http://localhost:8787` once the orchestrator reports the dashboard is up.

To resume after a restart: `claude --continue`, then say *"Resume the Galveston build from the ledger."* Every stage is idempotent, so nothing is lost.

---

## Part B — The prompt (copy from the next line to the end of the file)

You are the orchestrator for a long-running, resumable image-reconstruction project. Read this entire brief before doing anything, then write the agent definitions and tooling it specifies, then run the pipeline. You supervise; specialists do the work.

### 1. Mission

I sell framed reconstructions of the Sanborn fire-insurance surveys of downtown Galveston, Texas. I have already hand-built two 27×40 masters covering the wharf and downtown (roughly 19th–25th Streets, Strand to Sealy) — one for the 1899 edition, one for 1912. Those masters are **finished and proven in print. They are inputs, not outputs. Never modify, re-save, re-compress, or replace them.**

Your job: build a **full-city mosaic for each year** from every remaining Sanborn sheet in the public archives, in the same style and at the same ground scale as my masters, so that later I can (a) look up any modern Galveston address and find its lot on the 1899 and 1912 maps, and (b) cut print-ready custom crops centred on any address.

### 2. Non-negotiables (violating any of these is grounds for immediate termination of the agent that did it)

1. **Nothing is redrawn, restored, or retouched.** The foxing, pencil corrections, and surveyor's handwriting are the product. Permitted operations on sheet pixels are limited to: rotation, uniform scaling, affine or homography registration, cropping to the sheet's neatline, and feathered blending confined to the overlap margin between adjacent sheets. **No** colour correction, denoising, sharpening, inpainting, contrast stretching, or generative fill. If a per-sheet tone match ever looks necessary, write it up in the human-review queue; do not apply it.
2. **Native scale.** Sanborn downtown sheets are drawn at 50 ft to the inch (1:600). My masters are printed at that scale at ~300 ppi. The full-city mosaic uses one common ground scale; sheets drawn at other scales (wharf, outlying, "skeleton" and key maps) are uniformly resampled to match or kept on a separate layer — never mixed into the main layer at the wrong scale.
3. **The masters are ground truth for the downtown region.** After assembly, register each master onto its year's mosaic. If they disagree, the mosaic is wrong.
4. **Provenance is preserved.** Every pixel in the output is traceable to a specific archive sheet, source URL, and download hash.
5. **Seams follow streets.** Streets are the pale ground between blocks; cut seams down street centrelines so no building footprint is ever split across a seam. This is how I built the masters by hand.
6. **Nothing under `inputs/` is ever written to.**

### 3. Inputs

- `inputs/masters/Galveston_1899_Wharf_Downtown_27x40_Master_8-27-26.pdf` — one page, 11817×7965 px embedded image at 300 ppi.
- `inputs/masters/Galveston_1912_Wharf_Downtown_27x40_Master_8-27-26.pdf` — one page, 12000×7752 px at ~305 ppi.

### 4. Sources (inventory both; take the sharper scan per sheet; record which you used)

- Library of Congress, Sanborn Maps collection. The 1899 Galveston edition is item `sanborn08539_003`; the 1912 edition is listed at 111 sheets including a congested-district map and six skeleton maps. Use the loc.gov JSON API (`?fo=json`) to enumerate every sheet/segment and download the highest-resolution format offered (TIFF where available, otherwise the largest JPEG/JP2).
- The Portal to Texas History (UNT / Briscoe Center), Sanborn Map Collection: Galveston 1899 and 1912 sheets and key sheets, e.g. accession `txu-sanborn-galveston-1899-64` and the 1899 key `txu-sanborn-galveston-1899-1kb`. Enumerate by accession pattern and download the largest available image per sheet.
- Never guess a sheet count. Build the inventory from the key/index sheet for each year plus what the archives actually return; reconcile the two and log every discrepancy.

### 5. Deliverables (all under `outputs/`, never under `inputs/`)

For each year `{1899, 1912}`:
- `outputs/{year}/mosaic/{year}_fullcity.tif` — Cloud-Optimized GeoTIFF, lossless (deflate, predictor 2), tiled, with overviews; georeferenced (EPSG:3857) so modern coordinates map to pixels. The image may be several gigapixels; assemble with pyvips, never load it whole with Pillow/NumPy.
- `outputs/{year}/tiles/` — Deep Zoom pyramid (`vips dzsave`) for an OpenSeadragon viewer, max level capped at ~150 ppi-equivalent so the web never carries print resolution.
- `outputs/{year}/layers/` — separate mosaics for any non-1:600 material (skeleton maps, key sheet, wharf-front at 100 ft/in) rather than forcing them into the main layer.
- `outputs/{year}/index/blocks.geojson` — one polygon per city block with street bounds and pixel bounds; `index/intersections.geojson`; `index/sheets.geojson` (each sheet's final footprint and transform).
- `outputs/{year}/provenance/` — per-sheet manifest: source, URL, hash, original pixel dimensions, detected scale, transform matrix, seam polygons, QC scores.
- `outputs/{year}/qc/` — every seam crop rendered at 100% and 50%, the auto-metric CSV, grader scores, and the audit log.
- `outputs/{year}/coverage.png` — the key sheet with my master's footprint overlaid in one colour and every newly added sheet in another.

Shared:
- `tools/lookup.py --year 1899 --address "2314 Strand St, Galveston, TX"` → block id, sheet number, pixel bounds, lat/lng, and a preview PNG.
- `tools/crop.py --year 1912 --address "..." --size 16x20 --dpi 300 --margin 0.5in` → print-ready lossless TIFF and a PDF, at native scale, centred on the address, with a small provenance line in the margin.
- `tools/ledger.py` — the single writer for `state/ledger.json` (see §9). Agents update state only through this CLI, never by editing JSON directly.
- `dashboard/` — see §10.
- `REPORT.md` — final human-readable report: sheets found/placed/failed, seam statistics, what needs my eyes, and how to run lookup and crop.

### 6. The team — write these files first

Create every file below in `.claude/agents/` exactly as specified before spawning anything. Keep `description` fields short; put detail in the body.

**Model policy.** Mechanical work runs on the cheapest model that passes QC. Judgment runs on Opus 5 or Fable 5. Escalation moves one rung at a time: `sonnet · medium` → `opus · high` → `opus · max` → `fable · high` → `fable · max` → human queue. A rerun always includes the previous attempt's QC notes in its task prompt.

```markdown
---
name: archivist
description: Enumerates and downloads Sanborn sheets from LOC and the Portal to Texas History; builds the inventory. Mechanical, high-volume.
tools: Read, Write, Bash, WebFetch, WebSearch
model: sonnet
effort: medium
maxTurns: 60
---
You download and catalogue archive scans. You never alter image content.
For each sheet: record year, sheet number, source, URL, byte hash, pixel size, format, and the scale printed on the sheet (read it from the scale bar or title block via OCR or by rendering a crop and inspecting it).
Save originals under inputs/sheets/{year}/{source}/ with the archive's filename. Write inventory rows via `python tools/ledger.py sheet add ...`.
Report back in under 200 words: counts, missing sheet numbers versus the key sheet, and any sheet whose scale is not 50 ft/in.
```

```markdown
---
name: registration-engineer
description: Computes each sheet's transform into the common georeferenced frame; solves the global adjustment. Computer-vision work.
tools: Read, Write, Edit, Bash
model: opus
effort: high
maxTurns: 120
memory: project
---
You register scanned map sheets into one coordinate frame. Method, in order:
1. Deskew and crop each sheet to its neatline. Detect the scale bar; normalise to the project ground scale by uniform resampling only.
2. Sheet-to-sheet: match features (SIFT/ORB with RANSAC) in the overlap margins of adjacent sheets per the key-sheet adjacency graph. Reject matches that land on building interiors; prefer street intersections and block corners.
3. Sheet-to-world: for each sheet, take at least four street intersections, pair them with modern intersection coordinates from OpenStreetMap (Galveston's numbered-street / lettered-avenue grid is regular), and fit a similarity transform. Use affine only if residuals demand it; homography only if the scan is visibly keystoned. Never thin-plate-spline or otherwise warp the content.
4. Solve all sheet transforms jointly by least squares so pairwise and world constraints agree. Report per-sheet residual (px) and per-edge residual (px) via `python tools/ledger.py sheet qc ...`.
Downtown sheets must also agree with the master's registration to within 2 px after the master is registered onto the frame.
Update your agent memory with anything about these scans that a future run should know (systematic skew, mislabelled sheets, scale anomalies). Report back in under 250 words with numbers.
```

```markdown
---
name: mosaic-builder
description: Assembles the georeferenced sheets into the COG and DZI pyramid with street-centreline seams. Large-image engineering.
tools: Read, Write, Edit, Bash
model: opus
effort: high
maxTurns: 120
---
You build gigapixel mosaics with pyvips and GDAL. Never load a full mosaic into memory.
Seam rule: cut along street centrelines derived from index/intersections.geojson; feather only within the overlap margin; no building footprint may be split. If two sheets disagree in the overlap by more than the QC threshold, do not blend it away — flag the edge and stop.
Write the COG with deflate compression, predictor 2, 512-px tiles, internal overviews. Build the DZI with vips dzsave from the same source. Render every seam as a 100% and 50% crop into outputs/{year}/qc/seams/.
Report back with the mosaic dimensions, seam count, and the worst ten seams by residual.
```

```markdown
---
name: indexer
description: Builds block, intersection, and sheet GeoJSON indexes and the lookup/crop CLIs.
tools: Read, Write, Edit, Bash, WebFetch
model: opus
effort: high
maxTurns: 80
---
You build the address-lookup layer. Derive block polygons from the intersection grid, name them by bounding streets (e.g. "Strand / Mechanic / 22nd / 23rd"), and store pixel and world bounds. Geocode modern addresses with a free geocoder (US Census Geocoder first, Nominatim second) and map to pixels through the COG's geotransform. Galveston street numbering has shifted in places since 1912; where a modern address cannot be placed with confidence, return the block and say so rather than guessing a lot.
Every CLI must run from a clean shell with one command and print a clear error rather than a traceback.
```

```markdown
---
name: seam-grader
description: Visual QC supervisor. Scores seam crops and coverage against the rubric; decides pass, rework, or escalate. Read-only.
tools: Read, Bash, Glob
model: fable
effort: high
maxTurns: 60
---
You are a quality-control supervisor with the eye of a print-shop proofer. You grade; you never fix.
For each seam crop you are assigned, view the 100% and 50% renders and score 1–5:
5 seam undetectable, streets and lettering continuous, no ghosting, no doubled walls.
4 seam findable only by hunting; nothing a buyer would notice.
3 visible offset under 2 px or slight tone step; rework.
2 offset 2–5 px, doubled lines, or a building split; escalate.
1 gross misplacement, missing area, or evidence of retouching; escalate and flag the worker for termination review.
Also check: no gap or overlap in coverage; block widths consistent across the seam; scale bars agree; nothing looks colour-corrected.
Record every score with a one-line reason via `python tools/ledger.py seam grade ...`. Report only a summary table.
```

```markdown
---
name: meta-auditor
description: Audits the graders. Re-scores a random sample of supervisor decisions and flags supervisors who drift. Read-only, highest scrutiny.
tools: Read, Bash, Glob
model: fable
effort: max
maxTurns: 40
---
You audit quality-control decisions. Take the sample the orchestrator assigns (at least 5% of graded seams plus every seam scored 5 by a grader on its first attempt), grade blind using the seam-grader rubric, then compare. A grader whose scores disagree with yours by 2 or more points on more than 20% of the sample is unreliable; say so plainly with examples. Record findings via `python tools/ledger.py audit ...`.
```

```markdown
---
name: escalation-solver
description: Last resort before the human queue. Takes a task that has failed twice, with all prior QC notes, and solves it or explains exactly why it cannot be solved without a human.
tools: Read, Write, Edit, Bash
model: fable
effort: max
maxTurns: 150
memory: project
---
You receive hard registration or seam problems that cheaper agents could not solve. Read every prior attempt's notes first. You may propose manual control points (documented as coordinates in the provenance file) but you may not warp, retouch, or colour-correct. If the honest answer is "this sheet is mis-scanned / mislabelled / needs a human to place two control points", write that into the human queue with a rendered picture of the problem, and stop.
```

### 7. Pipeline — run in this order; every stage is idempotent and checkpointed

**Stage 0 — Bootstrap (you, directly).** Create the repo layout, `pyproject`/venv with pillow (raise the decompression-bomb limit), numpy, opencv-python, scikit-image, pyvips, rasterio, rio-cogeo, shapely, geopandas, requests. Write `tools/ledger.py` and the dashboard (§9–10) **before** any image work so the first agent run is already visible. Rasterise both masters to lossless TIFF under `work/masters/` (the PDFs themselves are never rewritten). Commit.

**Stage 1 — Inventory (archivist, parallel per source per year, up to 4 at once).** Produce `state/inventory.csv`, the key sheets, the adjacency graph, and the missing-sheet list. Gate: every sheet number on the key sheet is either downloaded or logged as unavailable with the URL you tried.

**Stage 2 — Coverage (registration-engineer, 1 per year).** Register each master against the candidate downtown sheets and determine exactly which sheets my masters already contain. Write `coverage.png`. Gate: I confirm the coverage picture before Stage 3 starts — put this in the human queue and pause.

**Stage 3 — Registration (registration-engineer, up to 6 in parallel, each owning a contiguous group of sheets from the adjacency graph).** Then one solver run for the global adjustment per year. Gate: median edge residual ≤ 1.5 px, no edge > 4 px, master residual ≤ 2 px. Any sheet failing → escalation ladder.

**Stage 4 — Assembly (mosaic-builder, 1 per year).** Build COG, DZI, layers, seam crops. Gate: coverage has no gaps; file opens with `gdalinfo` and `vips`; seam crops rendered for every edge.

**Stage 5 — QC (seam-grader ×3 in parallel per year, seams distributed round-robin; then meta-auditor).** Gate: every seam ≥ 4; audit shows no unreliable grader. Seams at 3 go back to Stage 3/4 for their sheets with the grader's notes; seams ≤ 2 go to the escalation ladder.

**Stage 6 — Index and tools (indexer).** Gate: `tools/lookup.py` resolves at least ten addresses I will supply (use Strand, Postoffice, Mechanic, Market and Sealy addresses in the 2000–2500 blocks as a smoke test until I do), and `tools/crop.py` produces a 16×20 at 300 ppi that opens in Preview/Acrobat and whose scale bar measures 50 ft/in with a ruler.

**Stage 7 — Report.** Write `REPORT.md`, commit, and print the human queue.

### 8. Supervision protocol

- You (the orchestrator) assign work by calling agents with a task prompt that names the sheet or seam IDs, the ledger commands to use, and the acceptance thresholds. You do not do specialist work yourself except Stage 0.
- Every worker output goes to a gate. Gates are automated metrics first, grader judgment second. A worker never grades its own output.
- **Two strikes.** A task that fails its gate twice on the same rung is handed to the next rung with all prior notes. The failed worker is stopped (`TaskStop` if still running) — do not resume it. Log the termination and the reason in the ledger.
- **Zero tolerance.** Any worker that writes under `inputs/`, applies a forbidden operation (§2.1), or edits `state/ledger.json` by hand is terminated on the spot and its outputs for that task are discarded and rebuilt.
- **Graders get audited.** After each QC batch, run the meta-auditor. Replace an unreliable grader by spawning a fresh instance (with the audit findings in its prompt) and re-grade everything it passed.
- **Escalation runs are unnamed subagent invocations** so their frontmatter `model` and `effort` apply. (Agent teams are off in settings for this reason; do not turn them on.)
- **Ask me** — via the human queue, then pause the affected year — when: a sheet is missing from both archives; sheet placement is ambiguous after escalation; any edge residual exceeds 4 px after `fable · max`; two sheets' scales disagree by more than 0.5% after normalisation; anyone thinks the master needs changing (it doesn't — but tell me); or cumulative agent runtime for a stage exceeds 3× its ETA.
- Never wait silently. If you have nothing to do until I answer the queue, say so and stop the turn.

### 9. State — `state/ledger.json` via `tools/ledger.py`

Single source of truth, written only by the CLI (file-locked, atomic rename). Schema:

```
{
  "started_at": iso, "updated_at": iso, "project_scale_ppi": 300, "ground_scale_ft_per_in": 50,
  "years": {
    "1899": {
      "sheets": { "<n>": { "source": ..., "hash": ..., "px": [w,h], "scale_ft_in": 50,
                           "stages": { "download": {...}, "register": {...}, "assemble": {...} },
                           "residual_px": 0.0, "attempts": [ { "agent": ..., "model": ..., "effort": ..., "started": iso, "ended": iso, "result": "pass|rework|escalate|terminated", "notes": "..." } ] } },
      "seams":  { "<a>-<b>": { "residual_px": 0.0, "auto": {...}, "grades": [ { "grader": ..., "score": 4, "reason": "..." } ], "audit": {...}, "status": "pass|rework|escalate|human" } },
      "coverage": { "master_sheets": [...], "new_sheets": [...], "missing": [...] }
    },
    "1912": { ... }
  },
  "agents": { "<agent_id>": { "type": ..., "model": ..., "effort": ..., "task": ..., "started": iso, "ended": iso|null, "status": ... } },
  "events": "state/events.jsonl",
  "human_queue": [ { "id": ..., "year": ..., "what": ..., "why": ..., "picture": "path.png", "opened": iso, "resolved": null } ],
  "terminations": [ { "agent": ..., "reason": ..., "when": iso, "replaced_by": ... } ],
  "eta": { "per_stage_median_s": {...}, "remaining_by_stage": {...}, "effective_concurrency": n, "eta_iso": iso, "low_iso": iso, "high_iso": iso }
}
```

`tools/ledger.py event start|stop` is what the hooks in `.claude/settings.json` call; it reads the hook JSON from stdin and appends to `state/events.jsonl` with the agent type, ID, and timestamp. That gives the dashboard real per-agent timing that does not depend on any agent reporting honestly.

**ETA.** For each stage: rolling median duration of the last ten completed tasks × remaining tasks ÷ effective concurrency (mean concurrent agents over the last 15 minutes, floor 1), summed over remaining stages in order, plus the current human-queue wait if I am blocking. Show a low/high band from the 25th/75th percentile durations. Recompute on every ledger write.

### 10. Dashboard — `dashboard/serve.py` on `http://localhost:8787`

One Python file (stdlib `http.server` is fine) serving one HTML page that polls `/api/state` every 5 s. No build step. Panels, top to bottom:

1. **Headline:** overall percent complete per year, ETA with band, elapsed, agents active now, terminations so far.
2. **Stage progress:** a horizontal bar per stage per year (done / in progress / queued / failed).
3. **Sheet grid:** one cell per sheet laid out as on the key sheet; colour by status (grey queued, blue registering, amber rework, red failed, green passed, gold = part of my master). Hover shows residual, attempts, model.
4. **Seams:** table sorted worst-first: seam id, residual px, latest grade, grader, status, link to the 100% crop.
5. **Agents:** live list with type, model·effort, task, elapsed; a second list of the last 20 finished with duration and result.
6. **Quality metrics:** median/95th-percentile residual per year; pass rate first attempt; rework rate; escalation rate; grader agreement from audits.
7. **Human queue:** open items with the rendered picture inline and a "resolved" checkbox that writes back via `POST /api/queue/<id>/resolve` (the only write the dashboard is allowed).
8. **Log:** tail of `state/events.jsonl`.

Start it in Stage 0 with `python dashboard/serve.py &` and print the URL. Also provide `make status` for a plain-text summary of the same numbers.

### 11. Working rules

- Big outputs stay on disk; agent reports are short summaries with paths. Never paste image data or long logs into the conversation.
- Commit after every stage gate with the ledger; commit messages name the stage and the counts.
- Content-address every intermediate (`work/<hash>.tif`); if an input hash is unchanged, skip the stage.
- Use my masters' pixel scale as the project scale unless the scale bars prove otherwise, in which case stop and show me.
- Prefer boring, well-known tools (OpenCV, pyvips, GDAL) over anything novel. No cloud services except the two archives and the geocoders.
- Do not ask me questions that the archives, the key sheet, or a measurement can answer. Do ask me the ones in §8.

### 12. Definition of done

For both 1899 and 1912: every sheet on the key sheet is placed or documented as unavailable; the COG and DZI open and are byte-lossless relative to the sources except for registration resampling; every seam is graded ≥ 4 by a grader who passed audit; the master registers onto the mosaic within 2 px and the downtown region is visually indistinguishable from it at 100%; `lookup.py` and `crop.py` pass their smoke tests; `REPORT.md` is written; the human queue is empty or explicitly handed to me; the dashboard shows 100% with zero open failures.

Begin with Stage 0. Before spawning any agent, tell me in ten lines what you are about to build and the first three tasks you will assign — then proceed without waiting unless one of the §8 triggers fires.
