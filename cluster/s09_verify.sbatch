#!/bin/bash
#SBATCH --job-name=s09_verify
#SBATCH --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --mem=100G
#SBATCH --cpus-per-task=4

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s09_verify  start $(date)  host $(hostname)  cwd $(pwd)"

python -u verify_against_reference.py --new_dir "$WORK_DIR" --ref_dir "$REF_DIR"

echo ">>> s09_verify  done  $(date)"
