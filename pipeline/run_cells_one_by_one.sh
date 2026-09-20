#!/usr/bin/env bash
# Run ONE cell per Python process.
# Usage:
#   bash run_cells_one_by_one.sh E3
#   bash run_cells_one_by_one.sh E4
#   bash run_cells_one_by_one.sh E3 s01          # only one stimulus
#   bash run_cells_one_by_one.sh E3 s01 baseline # one cell only

set -euo pipefail
cd "$(dirname "$0")"

EPOCH="${1:?epoch required, e.g. E3}"
ONLY_STIM="${2:-}"
ONLY_COND="${3:-}"

PYTHON="${PYTHON:-python3}"
export TOKENIZERS_PARALLELISM=false
unset PYTORCH_ENABLE_MPS_FALLBACK || true

STIMS=(s01 s02 s03 s04 s05 s06 s07 s08 s09 s10 s11 s12)
CONDS=(baseline pipeline)

if [[ -n "$ONLY_STIM" ]]; then
  STIMS=("$ONLY_STIM")
fi
if [[ -n "$ONLY_COND" ]]; then
  CONDS=("$ONLY_COND")
fi

echo "=== One-by-one run for $EPOCH ==="
echo "Python: $PYTHON"
echo

for sid in "${STIMS[@]}"; do
  for cond in "${CONDS[@]}"; do
    out="outputs/${sid}__${EPOCH}__${cond}.json"
    if [[ -f "$out" ]]; then
      echo "[skip exists] $out"
      continue
    fi
    echo
    echo "########## $sid / $EPOCH / $cond ##########"
    "$PYTHON" pipeline.py \
      --epoch "$EPOCH" \
      --stimulus "$sid" \
      --condition "$cond" \
      --outdir outputs \
      --pause 1
    sleep 3
  done
done

echo
echo "=== Merging results ==="
"$PYTHON" pipeline.py --merge-only --outdir outputs
echo "Done."
