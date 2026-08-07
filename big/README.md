# Galveston 1885 Sanborn composite — large deliverables

Files over chat-transfer limits, chunked under GitHub's 100 MB cap.

Reassemble (macOS/Linux Terminal, or use any file-joiner):
    cat galveston_1885_composite.tif.gh-* > galveston_1885_composite.tif
    shasum -a 256 -c galveston_1885_composite.tif.sha256
    cat galveston_1885_atlas.pdf.gh-* > galveston_1885_atlas.pdf
    shasum -a 256 -c galveston_1885_atlas.pdf.sha256

galveston_1885_full.jpg needs no reassembly.

## Navigation overlay add-on (repo root)

Two small files at the root of this branch, outside the QC'd delivery manifest:

- `galveston_1885_nav_overlay.svg` — traced street-grid navigation layer,
  same 17632x26968 coordinate space as the composite. DERIVED layer; not
  part of the archival raster and not listed in MANIFEST.txt.
- `galveston_1885_nav_viewer.html` — self-contained browser viewer
  (embedded preview JPEG + toggleable overlay).
