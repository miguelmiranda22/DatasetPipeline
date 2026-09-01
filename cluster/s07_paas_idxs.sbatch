#!/bin/bash
#SBATCH --job-name=s07_paas_idxs
#SBATCH --ntasks=1
#SBATCH --time=08:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s07_paas_idxs  start $(date)  host $(hostname)  cwd $(pwd)"

cd PAAS-Toolkit
python -u ProcessPAASidxs.py paas_4.0_pickles
cp AllProtPaas.pickle "$WORK_DIR/all_prots_fps.pickle"

python -u PAASTrimmer.py "${PRUNING_SIZE:-5000}" all_prots_fps_selected.pickle
cp all_prots_fps_selected.pickle "$WORK_DIR/all_prots_fps_selected.pickle"

ls -l "$WORK_DIR/all_prots_fps.pickle" "$WORK_DIR/all_prots_fps_selected.pickle"

echo ">>> s07_paas_idxs  done  $(date)"
