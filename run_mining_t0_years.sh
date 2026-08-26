#!/bin/bash
#SBATCH --job-name=csanno_mining_t0_years
#SBATCH --output=/mnt/storage/admindi/home/mmiranda/Classification/csanno_mining_results/job_%A_task_%a_t0_years.txt
#SBATCH --error=/mnt/storage/admindi/home/mmiranda/Classification/csanno_mining_results/job_%A_task_%a_t0_years.err
#SBATCH --array=0-19
#SBATCH --time=24:00:00
#SBATCH --mem=32G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --partition=compute

# Re-mine T0 (exact match) data from scratch, for BOTH strict and non-strict
# activity rules, against the SAME seeds_part_*.txt input files already used
# by run_mining_t0_strict.sh - the same files confirmed (via
# diagnose_year_mapping_mismatch.py) to carry real ChEMBL molecule IDs
# (e.g. "CHEMBL1") as their first column, rather than the "SEED_N" seed
# placeholder IDs that seeds.sar/the older split files use.
#
# This is the root-cause fix for the year-mapping failure found in the
# non-strict prospective-validation datasets: since csanno.py's molecule_id
# in the output JSON is taken directly from the INPUT file's first column
# (see csanno.py::read_molecules), mining non-strict rules against these
# same already-correctly-ID'd files means BOTH strict and non-strict output
# will now resolve against chembl_year_mapping.csv - no merge-side patch
# needed.
#
# 20 array tasks = 10 seed-file chunks x 2 rulesets (file_idx = task_id % 10,
# ruleset_idx = task_id / 10):
#
#   Tasks  0-9  : seeds_part_0.txt .. seeds_part_9.txt, STRICT rules
#   Tasks 10-19 : seeds_part_0.txt .. seeds_part_9.txt, NON-STRICT (default) rules
#
# Output names are deliberately different from the existing
# actives_t0_strict_dataset_N_results.json / actives_t0_dataset_N_results.json
# (and their _report.md siblings), so nothing gets overwritten:
#
#   Strict     -> {actives,inactives}_t0_strict_years_dataset_{0-9}_results.json (+ _report.md)
#   Non-strict -> {actives,inactives}_t0_nonstrict_years_dataset_{0-9}_results.json (+ _report.md)
#
# Submit from wherever seeds_part_*.txt, csanno.py, csanno_strict_rules.yaml
# and csanno_default_rules.yaml actually live (per project convention:
# Classification/csanno_repo/):
#   sbatch run_mining_t0_years.sh

N_FILES=10

FILE_IDX=$((SLURM_ARRAY_TASK_ID % N_FILES))
RULESET_IDX=$((SLURM_ARRAY_TASK_ID / N_FILES))

FILES=(seeds_part_*.txt)
CURRENT_FILE=${FILES[$FILE_IDX]}

RULESET_FILES=(csanno_strict_rules.yaml csanno_default_rules.yaml)
RULESET_NAMES=(strict nonstrict)
CURRENT_RULES=${RULESET_FILES[$RULESET_IDX]}
CURRENT_NAME=${RULESET_NAMES[$RULESET_IDX]}

echo ">>> Booting Array Task $SLURM_ARRAY_TASK_ID (T0 EXACT MATCHES ONLY - ${CURRENT_NAME^^} RULES, file $CURRENT_FILE, chunk $FILE_IDX)"

# 1. Search strictly for INACTIVES (0s) FIRST
echo ">>> Mining INACTIVES (T0, $CURRENT_NAME)..."
python -u csanno.py -in $CURRENT_FILE -search N -rules $CURRENT_RULES -report AD -ofield U -out inactives_t0_${CURRENT_NAME}_years_dataset_${FILE_IDX}

# 2. Search strictly for ACTIVES (1s)
echo ">>> Mining ACTIVES (T0, $CURRENT_NAME)..."
python -u csanno.py -in $CURRENT_FILE -search A -rules $CURRENT_RULES -report AD -ofield U -out actives_t0_${CURRENT_NAME}_years_dataset_${FILE_IDX}

echo ">>> Task $SLURM_ARRAY_TASK_ID Complete ($CURRENT_NAME, chunk $FILE_IDX)."
