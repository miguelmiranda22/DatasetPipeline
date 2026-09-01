#!/bin/bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/config.sh"

bash "$HERE/preflight.sh" || exit 1

mkdir -p "$WORK_DIR" "$LOG_DIR"
ln -sfn "$(dirname "$(dirname "$CHEMBL_DB")")" "$BASE_DIR/chembl_37"

for f in extract_sql_seeds_and_years.py csanno.py csanno_reports.py chembl_access.py \
         csanno_strict_rules.yaml csanno_default_rules.yaml \
         extract_uniprot_ids_from_jsons.py download_alphafold_pdbs.py \
         merge_all_prots_datasets_uniform.py; do
    cp "$PIPE_DIR/$f" "$WORK_DIR/"
done
rm -rf "$WORK_DIR/PAAS-Toolkit"
cp -r "$PIPE_DIR/PAAS-Toolkit" "$WORK_DIR/"
rm -rf "$WORK_DIR/PAAS-Toolkit/__pycache__"
sed -i 's|name=key.split("-")\[1\]|name=key.split("-")[1] if "-" in key else key|' "$WORK_DIR/PAAS-Toolkit/MakePAASCentroids.py"
cp "$HERE/verify_against_reference.py" "$WORK_DIR/"

export PIPE_CONFIG="$HERE/config.sh"

echo "=== work dir: $WORK_DIR"
echo "=== logs    : $LOG_DIR"
echo

sb() {
    local name="$1"; shift
    sbatch --parsable --partition="$PARTITION" \
           --export=ALL,PIPE_CONFIG="$PIPE_CONFIG" \
           --output="$LOG_DIR/%x_%A_%a.out" --error="$LOG_DIR/%x_%A_%a.err" \
           "$@" "$HERE/$name"
}

J1=$(sb s01_sql.sbatch)
J2=$(sb s02_mining.sbatch          --dependency=afterok:$J1)
J3=$(sb s03_ids.sbatch             --dependency=afterok:$J2)
J4=$(sb s04_structures.sbatch      --dependency=afterok:$J3)
J5=$(sb s05_paas_process.sbatch    --dependency=afterok:$J4)
J6=$(sb s06_paas_centroids.sbatch  --dependency=afterok:$J5)
J7=$(sb s07_paas_idxs.sbatch       --dependency=afterok:$J6)
J8=$(sb s08_merge.sbatch           --dependency=afterok:$J7)
J9=$(sb s09_verify.sbatch          --dependency=afterok:$J8)

cat <<EOF
submitted:
  01 sql              $J1
  02 mining (0-19)    $J2
  03 protein ids      $J3
  04 structures       $J4
  05 paas process     $J5
  06 paas centroids   $J6
  07 paas idxs        $J7
  08 merge (0-1)      $J8
  09 verify           $J9

cancel everything:
  scancel $J1 $J2 $J3 $J4 $J5 $J6 $J7 $J8 $J9

watch:  squeue -u \$USER
logs :  $LOG_DIR
EOF
