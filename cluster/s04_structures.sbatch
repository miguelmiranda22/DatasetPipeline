#!/bin/bash
#SBATCH --job-name=s04_structures
#SBATCH --ntasks=1
#SBATCH --time=12:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=2

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s04_structures  start $(date)  host $(hostname)  cwd $(pwd)"

cp uniprot_ids_t0_json_union.txt unified_uniprot_ids_union.txt
python -u download_alphafold_pdbs.py

mkdir -p PAAS-Toolkit/sp_structs
mv alphafold_pdbs/*.pdb.gz PAAS-Toolkit/sp_structs/
echo "structures: $(ls PAAS-Toolkit/sp_structs | wc -l)"

echo ">>> s04_structures  done  $(date)"
