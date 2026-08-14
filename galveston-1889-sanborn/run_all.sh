#!/usr/bin/env bash
# One-command runner for the whole pipeline.
#   ./run_all.sh                 -> the real sheets (profile: galveston1889)
#   ./run_all.sh synthetic       -> the self-test fixture, end to end
#   ./run_all.sh galveston1889 --from 06   -> resume at a given step
#
# Every step is idempotent and writes to logs/. The run stops at the first
# failure rather than carrying a bad intermediate forward.
set -uo pipefail
cd "$(dirname "$0")"

PROFILE="${1:-galveston1889}"; shift || true
FROM="01"
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 64 ;;
  esac
done

PY="${PYTHON:-python3}"

STEPS=(
  "01_fetch_sources.py"
  "02_inventory_sources.py"
  "03_build_sheet1_mask.py"
  "04_build_topology.py"
  "05_generate_reference_intersections.py"
  "06_detect_or_define_gcps.py"
  "07_fit_and_evaluate_transforms.py"
  "08_build_masks.py"
  "09_warp_sources.py"
  "10_build_mosaic.py"
  "11_quality_control.py"
  "12_export_final.py"
)

if [ "$PROFILE" = "synthetic" ]; then
  echo "=== building the synthetic fixture first ==="
  "$PY" scripts/make_synthetic_fixture.py || exit 1
fi

for s in "${STEPS[@]}"; do
  n="${s%%_*}"
  if [ "$n" \< "$FROM" ]; then
    echo "--- skipping $s (before --from $FROM)"
    continue
  fi
  echo
  echo "=============================================================="
  echo "=== $s   (profile: $PROFILE)"
  echo "=============================================================="
  "$PY" "scripts/$s" --profile "$PROFILE"
  rc=$?
  if [ $rc -ne 0 ]; then
    echo
    echo "!!! $s exited $rc -- stopping. Read the message above and logs/." >&2
    exit $rc
  fi
done

echo
echo "=== complete. Deliverables in output/ ==="
ls -la output/ 2>/dev/null | sed 's/^/    /'
