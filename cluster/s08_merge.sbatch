#!/bin/bash
#SBATCH --job-name=s08_merge
#SBATCH --ntasks=1
#SBATCH --array=0-3
#SBATCH --time=12:00:00
#SBATCH --mem=100G
#SBATCH --cpus-per-task=16

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s08_merge  start $(date)  host $(hostname)  cwd $(pwd)"

python -u merge_all_prots_datasets_uniform.py $SLURM_ARRAY_TASK_ID

echo ">>> s08_merge  done  $(date)"
