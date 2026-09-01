#!/bin/bash
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/config.sh"

fail=0
say() { printf '  %-8s %s\n' "$1" "$2"; }

echo "=== preflight"

[ -d "$PIPE_DIR" ] && say "OK" "pipeline: $PIPE_DIR" || { say "MISSING" "pipeline: $PIPE_DIR"; fail=1; }

for f in extract_sql_seeds_and_years.py csanno.py chembl_access.py csanno_strict_rules.yaml \
         csanno_default_rules.yaml extract_uniprot_ids_from_jsons.py download_alphafold_pdbs.py \
         merge_all_prots_datasets_uniform.py requirements.txt; do
    [ -f "$PIPE_DIR/$f" ] && say "OK" "$f" || { say "MISSING" "$f"; fail=1; }
done

for f in MakeAAVecs.py PAAS_Processor.py MakePAASCentroids.py ProcessPAASidxs.py aas.txt blosum62.txt; do
    [ -f "$PIPE_DIR/PAAS-Toolkit/$f" ] && say "OK" "PAAS-Toolkit/$f" \
        || { say "MISSING" "PAAS-Toolkit/$f"; fail=1; }
done

[ -f "$PIPE_DIR/cluster/verify_against_reference.py" ] && say "OK" "cluster/verify_against_reference.py" \
    || { say "MISSING" "cluster/verify_against_reference.py"; fail=1; }

[ -f "$CHEMBL_DB" ] && say "OK" "chembl db: $CHEMBL_DB" || { say "MISSING" "chembl db: $CHEMBL_DB"; fail=1; }

python -c "import rdkit, pandas, numpy, scipy, sklearn, yaml, requests, tqdm" 2>/dev/null \
    && say "OK" "core python deps" || { say "MISSING" "core python deps"; fail=1; }
python -c "import skbio" 2>/dev/null \
    && say "OK" "scikit-bio" || { say "MISSING" "scikit-bio (needed by stage 06)"; fail=1; }

if [ -d "$REF_DIR" ]; then
    n=$(ls "$REF_DIR"/final_ml_dataset_T0_*_all_prots_uniform.pkl 2>/dev/null | wc -l)
    say "OK" "reference datasets found: $n"
else
    say "WARN" "no reference dir - stage 09 will be skipped"
fi

echo
if [ "$fail" -ne 0 ]; then
    echo "preflight FAILED - fix the above before submitting"
    exit 1
fi
echo "preflight passed"
