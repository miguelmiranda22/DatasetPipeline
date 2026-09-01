#!/bin/bash
#SBATCH --job-name=s03_ids
#SBATCH --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --mem=24G
#SBATCH --cpus-per-task=4

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s03_ids  start $(date)  host $(hostname)  cwd $(pwd)"

python -u extract_uniprot_ids_from_jsons.py --overwrite
wc -l uniprot_ids_*.txt

echo ">>> s03_ids  done  $(date)"
