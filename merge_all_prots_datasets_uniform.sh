#!/bin/bash
#SBATCH --job-name=merge_all_prots_uniform
#SBATCH --output=merge_all_prots_uniform_%A_task_%a.txt
#SBATCH --error=merge_all_prots_uniform_%A_task_%a.err
#SBATCH --array=0-3
#SBATCH --time=12:00:00
#SBATCH --mem=80G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --partition=compute

# CPU-only, no GPU needed - same per-task workload/allocation as
# merge_all_prots_datasets_years.sh.
#
# Builds 4 datasets from the NEW, uniformly-ID'd mining output
# (run_mining_t0_years.sh), each carrying both Morgan_FP/PAAS_FP (for the
# protein-blind test) AND Year (for the prospective/temporal test) - see the
# script docstring for why one file can now serve both purposes:
#
#   Task 0: all_prots_fps.pickle          + strict     -> final_ml_dataset_T0_strict_zeros_win_all_prots_uniform.pkl
#   Task 1: all_prots_fps.pickle          + non-strict  -> final_ml_dataset_T0_nonstrict_zeros_win_all_prots_uniform.pkl
#   Task 2: all_prots_fps_selected.pickle + strict     -> final_ml_dataset_T0_strict_zeros_win_all_prots_selected_uniform.pkl
#   Task 3: all_prots_fps_selected.pickle + non-strict  -> final_ml_dataset_T0_nonstrict_zeros_win_all_prots_selected_uniform.pkl
#
# Requires alongside it: all_prots_fps.pickle, all_prots_fps_selected.pickle,
# chembl_year_mapping.csv, and the actives/inactives_t0_{strict,nonstrict}_years_dataset_*_results.json
# shards produced by run_mining_t0_years.sh.
#
# Submit from wherever these files actually live (per project convention:
# Classification/csanno_repo/):
#   sbatch merge_all_prots_datasets_uniform.sh

python -u merge_all_prots_datasets_uniform.py $SLURM_ARRAY_TASK_ID
