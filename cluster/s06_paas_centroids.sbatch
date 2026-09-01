#!/bin/bash
#SBATCH --job-name=s06_paas_centroids
#SBATCH --ntasks=1
#SBATCH --time=24:00:00
#SBATCH --mem=125G
#SBATCH --cpus-per-task=32

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s06_paas_centroids  start $(date)  host $(hostname)  cwd $(pwd)"

cd PAAS-Toolkit
test -n "$(ls paas_4.0_pickles/*.pickle 2>/dev/null)" || { echo "no paas pickles"; exit 1; }
python -u MakePAASCentroids.py paas_4.0_pickles
ls -l PAAS_Clusters.pickle

echo ">>> s06_paas_centroids  done  $(date)"
