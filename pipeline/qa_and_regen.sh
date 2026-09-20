#!/usr/bin/env bash
# Audit all cells; delete/regenerate unsatisfactory ones (empty, truncated, too short).
# Usage:
#   bash qa_and_regen.sh           # audit + regen bad for E1..E4
#   bash qa_and_regen.sh E1 E3     # only those epochs

set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
export TOKENIZERS_PARALLELISM=false
unset PYTORCH_ENABLE_MPS_FALLBACK || true

EPOCHS=("$@")
if [[ ${#EPOCHS[@]} -eq 0 ]]; then
  EPOCHS=(E1 E2 E3 E4)
fi

echo "=== QA report (before) ==="
"$PYTHON" pipeline.py --qa-only --outdir outputs || true

echo
echo "=== Regenerating unsatisfactory cells for: ${EPOCHS[*]} ==="
for epoch in "${EPOCHS[@]}"; do
  echo
  echo "######## QA regen $epoch ########"
  if [[ "$epoch" == "E3" || "$epoch" == "E4" ]]; then
    # one process per cell for large models
    for sid in s01 s02 s03 s04 s05 s06 s07 s08 s09 s10 s11 s12; do
      for cond in baseline pipeline; do
        out="outputs/${sid}__${epoch}__${cond}.json"
        # Decide via a tiny python check
        need=$("$PYTHON" - <<PY
import json, sys
from pipeline import response_quality_issues
path = "$out"
epoch = "$epoch"
try:
    row = json.load(open(path))
    issues = response_quality_issues(row.get("response", ""), epoch_id=row.get("epoch_id", epoch))
except Exception:
    issues = ["missing"]
print("yes" if issues else "no")
if issues:
    print(path, issues, file=sys.stderr)
PY
)
        if [[ "$need" != "yes" ]]; then
          echo "[qa-ok keep] $out"
          continue
        fi
        rm -f "$out"
        echo "########## regen $sid / $epoch / $cond ##########"
        "$PYTHON" pipeline.py \
          --epoch "$epoch" \
          --stimulus "$sid" \
          --condition "$cond" \
          --outdir outputs \
          --no-skip-existing \
          --pause 1
        sleep 2
      done
    done
  else
    # small models: one process with --regen-bad is fine
    "$PYTHON" pipeline.py --epoch "$epoch" --regen-bad --outdir outputs --pause 1
  fi
done

echo
echo "=== QA report (after) ==="
"$PYTHON" pipeline.py --qa-only --outdir outputs
"$PYTHON" pipeline.py --merge-only --outdir outputs
echo "Done."
