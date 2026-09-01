#!/bin/bash
#SBATCH --job-name=s02_mining
#SBATCH --ntasks=1
#SBATCH --array=0-19
#SBATCH --time=24:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=16

set -euo pipefail
source "${PIPE_CONFIG:?PIPE_CONFIG not set - submit via run_pipeline.sh}"
cd "$WORK_DIR"
echo ">>> s02_mining  start $(date)  host $(hostname)  cwd $(pwd)"

N_FILES=10
FILE_IDX=$((SLURM_ARRAY_TASK_ID % N_FILES))
RULESET_IDX=$((SLURM_ARRAY_TASK_ID / N_FILES))
FILES=(seeds_part_*.txt)
CURRENT_FILE=${FILES[$FILE_IDX]}
RULESET_FILES=(csanno_strict_rules.yaml csanno_default_rules.yaml)
RULESET_NAMES=(strict nonstrict)
CURRENT_RULES=${RULESET_FILES[$RULESET_IDX]}
CURRENT_NAME=${RULESET_NAMES[$RULESET_IDX]}

python -u csanno.py -in $CURRENT_FILE -search N -rules $CURRENT_RULES -report AD -ofield U \
    -out inactives_t0_${CURRENT_NAME}_years_dataset_${FILE_IDX}
python -u csanno.py -in $CURRENT_FILE -search A -rules $CURRENT_RULES -report AD -ofield U \
    -out actives_t0_${CURRENT_NAME}_years_dataset_${FILE_IDX}

echo ">>> s02_mining  done  $(date)"
