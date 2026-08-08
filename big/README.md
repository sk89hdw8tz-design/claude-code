# Galveston 1885 Sanborn composite — v4.4 archival deliverables

Files over GitHub's 100 MB limit are split into `.gh-*` chunks.

## Reassemble the archival TIFF (555 MB)
    cat galveston_1885_composite.tif.gh-* > galveston_1885_composite.tif
    shasum -a 256 -c galveston_1885_composite.tif.sha256

## Reassemble the 16-page atlas PDF (107 MB)
    cat galveston_1885_atlas.pdf.gh-* > galveston_1885_atlas.pdf
    shasum -a 256 -c galveston_1885_atlas.pdf.sha256

## Single files
- `galveston_1885_onepage.pdf` — the whole map on one 300-dpi page
  (60.6 x 91.7 in) at archival JPEG quality 92 (4:4:4), with the traced
  navigation grid as a toggleable PDF layer (default off).
- `galveston_1885_full.jpg` — whole map, single JPEG q90.
- `PRODUCTION_REPORT.md` / `MANIFEST.txt` — method, QC record, 17
  disclosures; SHA-256 for every delivered file.

## Navigation overlay (repo root)
- `galveston_1885_nav_overlay.svg` — derived traced grid, same
  coordinate space as the composite. Never part of the archival raster.
- `galveston_1885_nav_viewer.html` — self-contained browser viewer.
