#!/bin/bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"

FROM="${1:-}"
if [ -z "$FROM" ]; then
    echo "usage: bash cluster/resume_pipeline.sh <first stage to run, 1-9>"
    exit 1
fi

if [ ! -d "$WORK_DIR" ]; then
    echo "no work dir at $WORK_DIR - use run_pipeline.sh for a fresh run"
    exit 1
fi

sed -i 's|name=key.split("-")\[1\]|name=key.split("-")[1] if "-" in key else key|' \
    "$WORK_DIR/PAAS-Toolkit/MakePAASCentroids.py"

cp "$HERE/verify_against_reference.py" "$WORK_DIR/"
mkdir -p "$LOG_DIR"
export PIPE_CONFIG="$HERE/config.sh"

STAGES=(s01_sql s02_mining s03_ids s04_structures s05_paas_process \
        s06_paas_centroids s07_paas_idxs s08_merge s09_verify)

echo "=== resuming from stage $FROM in $WORK_DIR"
echo

PREV=""
for i in $(seq "$FROM" 9); do
    name="${STAGES[$((i-1))]}"
    args=(--parsable --partition="$PARTITION"
          --export=ALL,PIPE_CONFIG="$PIPE_CONFIG"
          --output="$LOG_DIR/%x_%A_%a.out" --error="$LOG_DIR/%x_%A_%a.err")
    [ -n "$PREV" ] && args+=(--dependency=afterok:"$PREV")
    JID=$(sbatch "${args[@]}" "$HERE/$name.sbatch")
    printf '  %-20s %s\n' "$name" "$JID"
    PREV="$JID"
done

echo
echo "watch:  squeue -u \$USER"
echo "logs :  $LOG_DIR"
