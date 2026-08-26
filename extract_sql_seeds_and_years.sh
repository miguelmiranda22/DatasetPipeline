#!/bin/bash
#SBATCH --job-name=phase0_sql
#SBATCH --output=/mnt/storage/admindi/home/mmiranda/Classification/phase0_sql.txt
#SBATCH --error=/mnt/storage/admindi/home/mmiranda/Classification/phase0_sql.err
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --partition=compute

echo ">>> Starting Phase 0: SQL Seed & Year Extraction"
python -u extract_sql_seeds_and_years.py
echo ">>> Extraction Complete!"
