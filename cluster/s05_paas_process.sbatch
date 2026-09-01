#!/bin/bash
#SBATCH --job-name=s05_paas_process
#SBATCH --ntasks=1
#SBATCH --time=24:00:00
#SBATCH --mem=125G
#SBATCH --exclusive

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s05_paas_process  start $(date)  host $(hostname)  cwd $(pwd)"

cd PAAS-Toolkit
test -n "$(ls sp_structs/*.gz 2>/dev/null)" || { echo "no structures in sp_structs"; exit 1; }
python -u MakeAAVecs.py
python -u PAAS_Processor.py 4.0
echo "paas pickles: $(ls paas_4.0_pickles | wc -l)"

echo ">>> s05_paas_process  done  $(date)"
