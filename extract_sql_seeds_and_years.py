import sqlite3
import pandas as pd
import os
import math

# Requested Database Path
DB_PATH = r"../chembl_37/chembl_37_sqlite/chembl_37.db"

print("==================================================")
print(">>> PHASE 0: SQL EXTRACTION (SEEDS & YEAR MAPPING)")
print("==================================================")

if not os.path.exists(DB_PATH):
    print(f"🚨 CRITICAL ERROR: Database not found at {DB_PATH}")
    exit(1)

print(">>> Connecting to local SQLite ChEMBL DB...")
conn = sqlite3.connect(DB_PATH)

# We extract the molecules and their earliest publication year for each target combination
query = """
SELECT md.chembl_id AS molecule_id,
       cs.canonical_smiles AS SMILES,
       td.chembl_id AS target_chembl_id,
       td.pref_name AS target_pref_name,
       csn.accession AS target_accession,
       MIN(d.year) AS Year
FROM activities a
JOIN assays ass ON a.assay_id = ass.assay_id
JOIN target_dictionary td ON ass.tid = td.tid
LEFT JOIN target_components tc ON td.tid = tc.tid
LEFT JOIN component_sequences csn ON tc.component_id = csn.component_id
JOIN molecule_dictionary md ON a.molregno = md.molregno
JOIN compound_structures cs ON md.molregno = cs.molregno
JOIN docs d ON ass.doc_id = d.doc_id
WHERE d.year IS NOT NULL
  AND a.standard_type IN ('Ki', 'IC50', 'Kd', 'EC50', 'AC50', 'Potency', 'INH', 'Inhibition', 'pKi', 'pIC50', 'Activity')
GROUP BY md.chembl_id, cs.canonical_smiles, td.chembl_id, td.pref_name, csn.accession
"""

print(">>> Executing SQL Query (This may take a few minutes)...")
df = pd.read_sql_query(query, conn)
conn.close()

print(f">>> Extracted {len(df)} unique interaction records with Publication Year.")

# Save mapping for the merge step later
mapping_file = "chembl_year_mapping.csv"
df.to_csv(mapping_file, index=False)
print(f">>> Saved metadata mapping to {mapping_file}")

# Generate CSANNO seed chunks properly (ID \t Activity \t SMILES)
unique_mols_df = df[['molecule_id', 'SMILES']].drop_duplicates().dropna(subset=['molecule_id', 'SMILES'])
unique_mols = unique_mols_df.to_dict('records')

num_chunks = 10
chunk_size = math.ceil(len(unique_mols) / num_chunks)

print(f"\n>>> Splitting {len(unique_mols)} unique molecules into {num_chunks} chunks for CSANNO...")
for i in range(num_chunks):
    chunk = unique_mols[i*chunk_size : (i+1)*chunk_size]
    filename = f"seeds_part_{i}.txt"
    with open(filename, 'w') as f:
        for row in chunk:
            mol_id = row['molecule_id']
            smi = row['SMILES']
            # CSANNO requires exactly 3 tab-separated fields.
            # We pass 'NA' as a dummy activity placeholder.
            f.write(f"{mol_id}\tNA\t{smi}\n")
    print(f"  -> Created {filename} ({len(chunk)} seeds, 3-column format)")

print("\n==================================================")
print(">>> Phase 0 Complete! You can now run your CSANNO SLURM array.")
print("==================================================")
