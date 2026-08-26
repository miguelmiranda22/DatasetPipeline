"""
Build 4 datasets from the new, uniformly-ID'd mining output
(run_mining_t0_years.sh: actives/inactives_t0_{strict,nonstrict}_years_dataset_*_results.json),
each carrying BOTH the Morgan_FP/PAAS_FP columns needed for the protein-blind
test (run_blind_protein_all_prots.py) AND the Year column needed for the
temporal/prospective test (run_prospective_validation_all_prots.py).

Why one file can serve both purposes: run_blind_protein_all_prots.py never
reads a 'Year' column at all, so an extra column present but unused there is
harmless. That means, now that BOTH strict and non-strict mining runs carry
real ChEMBL molecule_ids (the whole point of run_mining_t0_years.sh), there is
no need to maintain two separate dataset families ("blind" vs "years") any
more - a single build per (dictionary, ruleset) combo, always with Year
attached, covers both evaluations and guarantees they are trained on
byte-identical rows.

Whether this reproduces the EXACT same bioactivity content as the original
(pre-uniform) blind datasets depends on whether the new seeds_part_*.txt
files reference the identical molecule pool as the original seeds.sar-derived
split, and on whether ChEMBL itself changed between the two mining runs -
both plausible but NOT verified here. Recommend diffing the new
"_uniform" output against the existing final_ml_dataset_T0_*_all_prots*.pkl
files (e.g. with a compare_final_datasets_consistency.py-style row/label
check) before treating them as drop-in replacements.

Run as a SLURM array of 4 tasks (task_id 0-3), one dataset per task:

  Task 0: all_prots_fps.pickle          + strict     -> final_ml_dataset_T0_strict_zeros_win_all_prots_uniform.pkl
  Task 1: all_prots_fps.pickle          + non-strict  -> final_ml_dataset_T0_nonstrict_zeros_win_all_prots_uniform.pkl
  Task 2: all_prots_fps_selected.pickle + strict     -> final_ml_dataset_T0_strict_zeros_win_all_prots_selected_uniform.pkl
  Task 3: all_prots_fps_selected.pickle + non-strict  -> final_ml_dataset_T0_nonstrict_zeros_win_all_prots_selected_uniform.pkl

Usage:
    python merge_all_prots_datasets_uniform.py <task_id 0-3>
"""
import sys
import os
import glob
import json
import pickle
import gc

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger
from rdkit import DataStructs

RDLogger.DisableLog('rdApp.*')

MORGAN_RADIUS = 4
MORGAN_BITS = 2048
YEAR_MAPPING_PATH = "chembl_year_mapping.csv"

# Points at the NEW, uniformly-ID'd mining output from run_mining_t0_years.sh
RULESET_GLOBS = {
    "strict": ("actives_t0_strict_years_dataset_*_results.json", "inactives_t0_strict_years_dataset_*_results.json"),
    "nonstrict": ("actives_t0_nonstrict_years_dataset_*_results.json", "inactives_t0_nonstrict_years_dataset_*_results.json"),
}

JOBS = [
    ("all_prots_fps.pickle", "strict", "final_ml_dataset_T0_strict_zeros_win_all_prots_uniform.pkl"),
    ("all_prots_fps.pickle", "nonstrict", "final_ml_dataset_T0_nonstrict_zeros_win_all_prots_uniform.pkl"),
    ("all_prots_fps_selected.pickle", "strict", "final_ml_dataset_T0_strict_zeros_win_all_prots_selected_uniform.pkl"),
    ("all_prots_fps_selected.pickle", "nonstrict", "final_ml_dataset_T0_nonstrict_zeros_win_all_prots_selected_uniform.pkl"),
]


def extract_records_with_id(filepath, activity_label):
    with open(filepath, "r") as f:
        data = json.load(f)

    mol_to_smiles = {}
    for m in data.get("raw_results", {}).get("molecules", []):
        mid = m.get("molecule_id")
        smi = m.get("smiles")
        if mid and smi:
            mol_to_smiles[mid] = smi

    payload = data.get("raw_results", {}).get("internal_result_payload", {})
    targets_dict = (
        payload.get("active_genes_T01") or payload.get("inactive_genes_T01")
        or payload.get("active_genes_T0") or payload.get("inactive_genes_T0")
        or payload.get("active_genes") or payload.get("inactive_genes") or {}
    )

    records = []
    for mol_id, target_list in targets_dict.items():
        smi = mol_to_smiles.get(mol_id)
        if smi:
            for t in target_list:
                if str(t).strip():
                    records.append({
                        "molecule_id": mol_id,
                        "SMILES": smi,
                        "Target": t,
                        "Activity": activity_label,
                    })
    return records


def attach_years(df_final, year_mapping_path):
    print("\n" + "=" * 70)
    print(">>> Phase 2: Attaching Publication Year via SQL Mapping")
    print("=" * 70)
    if not os.path.exists(year_mapping_path):
        print(f"WARNING: {year_mapping_path} not found. Year will be NaN.")
        df_final["Year"] = np.nan
        return df_final

    year_df = pd.read_csv(year_mapping_path)
    print(">>> Building Year lookup dictionaries...")

    mol_year_fallback = year_df.groupby("molecule_id")["Year"].min().to_dict()

    precision_dict = {}
    for _, row in year_df.iterrows():
        m_id = row["molecule_id"]
        y = row["Year"]
        if pd.notna(row["target_accession"]):
            precision_dict[(m_id, row["target_accession"])] = y
        if pd.notna(row["target_chembl_id"]):
            precision_dict[(m_id, row["target_chembl_id"])] = y
        if pd.notna(row["target_pref_name"]):
            precision_dict[(m_id, row["target_pref_name"])] = y

    def get_year(row):
        exact = precision_dict.get((row["molecule_id"], row["Target"]))
        if exact is not None:
            return exact
        return mol_year_fallback.get(row["molecule_id"], np.nan)

    df_final["Year"] = df_final.apply(get_year, axis=1)

    missing_years = df_final["Year"].isna().sum()
    print(f">>> Year Mapping Complete. Found publication years for {len(df_final) - missing_years} / {len(df_final)} rows.")
    return df_final


def main():
    try:
        task_id = int(sys.argv[1])
    except (IndexError, ValueError):
        print("ERROR: Please provide a valid SLURM array task ID (0-3).")
        sys.exit(1)

    if task_id >= len(JOBS):
        print(f"Task ID {task_id} exceeds available jobs ({len(JOBS)}). Exiting cleanly.")
        sys.exit(0)

    dict_path, ruleset, output_name = JOBS[task_id]
    active_glob, inactive_glob = RULESET_GLOBS[ruleset]

    print("=" * 70)
    print(f"--- Merge (Uniform) Task {task_id} Booted ---")
    print(f"Dictionary:  {dict_path}")
    print(f"Ruleset:     {ruleset}")
    print(f"Output:      {output_name}")
    print("=" * 70)

    print("\n>>> Phase 1: Loading T0 Data (Zeros-Win resolution)")
    active_files = sorted(glob.glob(active_glob))
    inactive_files = sorted(glob.glob(inactive_glob))
    print(f"Found {len(active_files)} Active files and {len(inactive_files)} Inactive files "
          f"({active_glob} / {inactive_glob})")

    if not active_files and not inactive_files:
        print("CRITICAL ERROR: No files matched - check run_mining_t0_years.sh has completed "
              "and produced actives/inactives_t0_{strict,nonstrict}_years_dataset_*_results.json")
        sys.exit(1)

    records = []
    for fp in active_files:
        records.extend(extract_records_with_id(fp, 1))
    for fp in inactive_files:
        records.extend(extract_records_with_id(fp, 0))

    df_final = pd.DataFrame(records)
    if df_final.empty:
        print("CRITICAL ERROR: No T0 records found. Check your JSON files/glob patterns.")
        sys.exit(1)
    df_final["Tier"] = "T0"
    print(f"Extracted {len(df_final)} absolute T0 interactions.")

    print("\n>>> RESOLVING CONFLICTS: 0 overrides 1 (Zeros-Win). Only pure 1s are kept as Active.")
    df_final = df_final.sort_values(by=["Activity"], ascending=[True]).drop_duplicates(subset=["SMILES", "Target"], keep="first")
    print(f">>> Total Valid Interactions: {len(df_final)}")
    print(f">>> Final Activity Balance:\n{df_final['Activity'].value_counts()}")

    df_final = attach_years(df_final, YEAR_MAPPING_PATH)

    # Drop molecule_id now that Year has been resolved - not needed for ML
    df_final = df_final.drop(columns=["molecule_id"])

    print("\n" + "=" * 70)
    print(">>> Phase 3: Morgan Encoding")
    print("=" * 70)
    fpgen = AllChem.GetMorganGenerator(radius=MORGAN_RADIUS, fpSize=MORGAN_BITS)

    def get_morgan(smi):
        try:
            mol = Chem.MolFromSmiles(smi)
            if mol:
                arr = np.zeros((MORGAN_BITS,), dtype=np.int8)
                DataStructs.ConvertToNumpyArray(fpgen.GetFingerprint(mol), arr)
                return arr
        except Exception:
            pass
        return None

    print("Encoding SMILES strings...")
    df_final["Morgan_FP"] = df_final["SMILES"].apply(get_morgan)
    df_final = df_final.dropna(subset=["Morgan_FP"])

    print("\n" + "=" * 70)
    print(f">>> Phase 4: Protein Encoding ({dict_path}) & Exporting")
    print("=" * 70)
    if not os.path.exists(dict_path):
        print(f"ERROR: Dictionary {dict_path} not found. Aborting.")
        sys.exit(1)

    with open(dict_path, "rb") as f:
        paas_dict = pickle.load(f)
    print(f"Loaded dictionary with {len(paas_dict)} protein keys.")

    df_final["PAAS_FP"] = df_final["Target"].map(paas_dict)
    ready_df = df_final.dropna(subset=["PAAS_FP"])

    ready_df.to_pickle(output_name)

    print(f"\n>>> PROCESS COMPLETE. Saved {len(ready_df)} rows to: {output_name}")
    print(f">>> Unique proteins in final dataset: {ready_df['Target'].nunique()} / {len(paas_dict)} dictionary keys")
    valid_years = ready_df["Year"].notna().sum()
    print(f">>> Rows with a resolved Year: {valid_years} / {len(ready_df)} ({100 * valid_years / len(ready_df):.2f}%)")

    del df_final, ready_df, paas_dict
    gc.collect()


if __name__ == "__main__":
    main()
