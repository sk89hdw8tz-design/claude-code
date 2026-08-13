#!/usr/bin/env bash
# Download the second Galveston 1899 set and render both print versions.
# Usage: ./run_all.sh [output-dir]
set -euo pipefail

cd "$(dirname "$0")"
OUT="${1:-out}"
MAPS="$OUT/maps"
mkdir -p "$OUT"

echo "==> 1/4  Listing groups on the index page"
python3 fetch_maps.py --list

echo
echo "==> 2/4  Downloading group 2 (13 sheets + Key) and zipping"
python3 fetch_maps.py --group 2 --out "$MAPS" \
    --zip "$OUT/galveston-1899-selection.zip"

echo
echo "==> 3/4  Plate montage (each sheet whole, nothing cropped)"
python3 make_print.py --src "$MAPS" \
    --out "$OUT/galveston-1899-27x40-montage.tif" \
    --trim --labels \
    --proof "$OUT/proof-montage.jpg" \
    --pdf "$OUT/galveston-1899-27x40-montage.pdf"

echo
echo "==> 4/4  Geographic mosaic (edge-to-edge, PROVISIONAL layout)"
echo "    layout-provisional.json is inferred from the requested sheet order,"
echo "    not from the Key sheet. Check proof-mosaic.jpg against the Key."
python3 make_print.py --src "$MAPS" \
    --mode mosaic --trim \
    --layout layout-provisional.json \
    --out "$OUT/galveston-1899-27x40-mosaic.tif" \
    --proof "$OUT/proof-mosaic.jpg"

echo
echo "Done. Compare $OUT/proof-montage.jpg and $OUT/proof-mosaic.jpg."
ls -lh "$OUT"
