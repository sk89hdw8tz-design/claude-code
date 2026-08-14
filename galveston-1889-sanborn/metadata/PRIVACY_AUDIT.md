# Privacy audit of the git remote

Performed on request, before any further work.

## Remote

```
origin  https://github.com/sk89hdw8tz-design/claude-code  (fetch and push)
```

This is the repository this session was scoped to from the start; it is a fork
of the upstream `anthropics/claude-code`.

## What was committed — VERIFIED, not assumed

Searched the **entire git history, all branches**, for any image file ever added:

```
git log --all --pretty=format: --name-only --diff-filter=A \
  | grep -iE '\.(tif|tiff|jpg|jpeg|png|jp2|sid|bmp|gif|webp)$' | sort -u
```

Result: exactly one file, `demo.gif` — a pre-existing asset of the upstream
claude-code repository, present before this project began and unrelated to it.

Scoped to the project directory specifically: **zero image files in any commit,
on any branch, at any point in history.**

| category | committed? |
|---|---|
| UT source scans (the eight sheets, Key, Index) | **NO** |
| Mosaics / MASTER.tif / GEOREF.tif | **NO** |
| Previews, seam crops, mask previews, overlays | **NO** |
| Any derived historical imagery | **NO** |

What *is* tracked under `galveston-1889-sanborn/`: 30 `.py`, 29 `.geojson`
(mask polygons and control points, coordinates only), 11 `.md`, 10 `.csv`,
7 `.yaml`, 6 `.json`, plus the runner scripts and `.gitignore`. All text.

This is enforced by `.gitignore`, which excludes `data/original/`, `working/`,
`georeferenced/`, `tests/fixture/`, all of `output/**` except the text QC
reports, and every image extension wherever it appears. The exclusion was
verified with `git check-ignore` when it was written and is confirmed again here
against the actual commit history.

## Repository visibility — I could NOT determine this from inside the session

This is a real limitation and I will not paper over it.

* `api.github.com` is intercepted by this environment's egress proxy, which
  returned `403 GitHub access is not enabled for this session` rather than the
  repository metadata. I cannot read the `private` flag.
* `raw.githubusercontent.com` returns **200** for a file on our branch — but the
  proxy injects credentials into GitHub requests (`GITHUB_TOKEN=proxy-injected`,
  `gitConfigInjection: true`), so a 200 is equally consistent with a private
  repository my token can read. It does **not** demonstrate public access.
  Controls confirm the probe works: a known-public file returned 200 and a
  nonexistent repository returned 404.
* GitHub repository search for `user:sk89hdw8tz-design` returned
  `total_count: 0`. Repository search indexes public repositories, so this is
  *suggestive* of a non-public account — but it is indirect evidence, not proof.

**Conclusion: visibility unconfirmed; please check the repository settings
directly.** The material point is unaffected either way — no source scan and no
derived map imagery has ever been committed, so nothing of the reconstruction's
imagery is exposed regardless of the setting.

## Action taken

No history rewrite was performed, because the condition that would require one
(public remote *containing* map imagery) is not met: the remote contains no map
imagery at all. No local work was deleted.

If you confirm the remote is public and you would rather the *code and control
coordinates* not be there either, the clean fix is to add a private remote and
push the branch there; the imagery has never left this machine and the archival
scans in `data/original/` remain untracked and unmodified.
