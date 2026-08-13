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
echo "==> 2/4  Downloading group 2 (13 sheets + Key + Index) and zipping"
# Key and Index go in the zip. Neither is printed: the Key was dropped from the
# print by request, and the index map is the alignment reference, not a tile.
python3 fetch_maps.py --group 2 --out "$MAPS" \
    --zip "$OUT/galveston-1899-selection.zip"

# The layout must come off the index map. Until that has been read, fall back
# to the provisional one and say so loudly.
LAYOUT=layout-index.json
if [ ! -f "$LAYOUT" ]; then
    LAYOUT=layout-provisional.json
    echo
    echo "    !! layout-index.json not found -- falling back to $LAYOUT, which is"
    echo "       inferred from the requested sheet order, NOT read off the index"
    echo "       map. The mosaic will not be geographically correct until the"
    echo "       index map has been transcribed into layout-index.json."
fi

echo
echo "==> 3/4  Plate montage (each sheet whole, nothing cropped)"
python3 make_print.py --src "$MAPS" \
    --exclude key,index \
    --out "$OUT/galveston-1899-27x40-montage.tif" \
    --trim --labels \
    --proof "$OUT/proof-montage.jpg" \
    --pdf "$OUT/galveston-1899-27x40-montage.pdf"

echo
echo "==> 4/4  Geographic mosaic (edge-to-edge, aligned per $LAYOUT)"
python3 make_print.py --src "$MAPS" \
    --mode mosaic --trim --neatline \
    --exclude key,index \
    --layout "$LAYOUT" \
    --out "$OUT/galveston-1899-27x40-mosaic.tif" \
    --proof "$OUT/proof-mosaic.jpg" \
    --pdf "$OUT/galveston-1899-27x40-mosaic.pdf"

echo
echo "Done. Compare $OUT/proof-montage.jpg and $OUT/proof-mosaic.jpg."
ls -lh "$OUT"
