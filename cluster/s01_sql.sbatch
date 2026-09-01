#!/bin/bash
#SBATCH --job-name=s01_sql
#SBATCH --ntasks=1
#SBATCH --time=12:00:00
#SBATCH --mem=96G
#SBATCH --cpus-per-task=8

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s01_sql  start $(date)  host $(hostname)  cwd $(pwd)"

python -u extract_sql_seeds_and_years.py
ls -l chembl_year_mapping.csv
ls seeds_part_*.txt | wc -l

echo ">>> s01_sql  done  $(date)"
