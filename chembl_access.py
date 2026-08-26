"""
ChEMBL LOCAL SQLITE data-access layer for CSANNO.
Overrides the REST API to use the local chembl_37.db for HPC execution.
Includes a High-Performance RAM cache for RDKit Similarity searches.
"""

import os
import sys
import sqlite3
import pandas as pd
import pickle
from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import AllChem
from rdkit import RDLogger
import multiprocessing as mp
RDLogger.DisableLog('rdApp.*')

# --- ABSOLUTE PATH CONFIGURATION ---
# Using raw string (r"") to prevent Windows backslash errors
DB_PATH = r"../chembl_37/chembl_37_sqlite/chembl_37.db"
DEFAULT_SERVER = "LOCAL_SQLITE"
GLOBAL_FPGEN = AllChem.GetMorganGenerator(radius=2)

# --- FAIL FAST INITIALIZATION CHECK ---
# This executes the millisecond this file is imported, preventing wasted time.
if not os.path.exists(DB_PATH):
    print("\n" + "="*60)
    print("🚨 CRITICAL ERROR: ChEMBL Database Not Found!")
    print(f"Expected Location: {DB_PATH}")
    print("Please check the path inside chembl_access.py and try again.")
    print("="*60 + "\n")
    sys.exit(1) # Instantly kills the script

# --- GLOBAL RAM CACHE FOR SIMILARITY ---
GLOBAL_CHEMBL_IDS = None
GLOBAL_FPS = None

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def warn(msg, silent=False):
    if not silent: print(f"WARNING: {msg}")

# Mocking HTTP warning systems from original file
REQUEST_FAILURES = []
def reset_request_failures(): pass
def get_request_failure_summary(*args, **kwargs): return {"count": 0}
def print_request_failure_summary(*args, **kwargs): pass
def normalise_server(server): return DEFAULT_SERVER
def normalise_chembl_server(server): return DEFAULT_SERVER

# --- CORE SQL QUERIES ---

def get_molecule_id(inchikey, server=DEFAULT_SERVER, silent=False):
    conn = get_db_connection()
    query = """
        SELECT m.chembl_id 
        FROM molecule_dictionary m 
        JOIN compound_structures s ON m.molregno = s.molregno 
        WHERE s.standard_inchi_key = ?
    """
    cur = conn.cursor()
    cur.execute(query, (inchikey,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else False

def get_activities(molecule_id, server=DEFAULT_SERVER, silent=False):
    if not molecule_id: return []
    
    conn = get_db_connection()
    query = """
        SELECT 
            ass.chembl_id AS assay_id,
            t.chembl_id AS target_id,
            act.standard_type AS assay_type,
            act.standard_units AS units,
            act.standard_value AS value,
            act.standard_relation AS rel,
            act.pchembl_value AS pvalue
        FROM activities act
        JOIN assays ass ON act.assay_id = ass.assay_id
        JOIN target_dictionary t ON t.tid = ass.tid
        JOIN molecule_dictionary m ON act.molregno = m.molregno
        WHERE m.chembl_id = ? AND act.standard_value IS NOT NULL
    """
    df = pd.read_sql_query(query, conn, params=(molecule_id,))
    conn.close()
    
    df = df.dropna(subset=['target_id'])
    return df.to_dict(orient='records')

def get_target_components(target_id, server=DEFAULT_SERVER, silent=False):
    if not target_id: return []
    
    conn = get_db_connection()
    query = """
        SELECT 
            t.organism,
            t.pref_name AS pname,
            cs.accession AS uniprot,
            tcs.component_synonym AS gene
        FROM target_dictionary t
        JOIN target_components tc ON t.tid = tc.tid
        JOIN component_sequences cs ON tc.component_id = cs.component_id
        LEFT JOIN component_synonyms tcs ON cs.component_id = tcs.component_id AND tcs.syn_type = 'GENE_SYMBOL'
        WHERE t.chembl_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(target_id,))
    conn.close()
    
    tcomps = []
    for _, row in df.iterrows():
        tcomps.append({
            "organism": row['organism'],
            "pname": row['pname'],
            "uniprot": row['uniprot'],
            "gene": row['gene'] if pd.notnull(row['gene']) else ""
        })
    return tcomps

# --- TIER 1: HIGH PERFORMANCE RAM SIMILARITY ---

def _init_similarity_cache():
    global GLOBAL_CHEMBL_IDS, GLOBAL_FPS
    if GLOBAL_FPS is not None: return
    
    cache_file = "chembl_37_fp_cache.pkl"
    if os.path.exists(cache_file):
        print("\n>>> Loading RDKit Bulk Similarity Cache from Disk (~30 seconds)...")
        with open(cache_file, 'rb') as f:
            GLOBAL_CHEMBL_IDS, GLOBAL_FPS = pickle.load(f)
        return
        
    print("\n>>> Building RDKit Similarity Cache (This takes ~15 mins but only happens ONCE)...")
    conn = get_db_connection()
    query = """
        SELECT m.chembl_id, s.canonical_smiles 
        FROM compound_structures s 
        JOIN molecule_dictionary m ON s.molregno = m.molregno 
        WHERE s.canonical_smiles IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    ids, fps = [], []
    fpgen = AllChem.GetMorganGenerator(radius=2)
    for _, row in df.iterrows():
        try:
            mol = Chem.MolFromSmiles(row['canonical_smiles'])
            if mol:
                fps.append(fpgen.GetFingerprint(mol))
                ids.append(row['chembl_id'])
        except:
            pass
            
    GLOBAL_CHEMBL_IDS = ids
    GLOBAL_FPS = fps
    with open(cache_file, 'wb') as f:
        pickle.dump((ids, fps), f)
    print(">>> Cache Built and Saved Successfully!\n")

def get_similar_molecules(smiles, sim_thr=0.9, server=DEFAULT_SERVER, silent=False):
    # Worker function for single molecules (Called by the multiprocessing pool)
    mol = Chem.MolFromSmiles(smiles)
    if not mol: return []
    
    fpgen = AllChem.GetMorganGenerator(radius=2)
    query_fp = fpgen.GetFingerprint(mol)
    
    sims = DataStructs.BulkTanimotoSimilarity(query_fp, GLOBAL_FPS)
    
    results = []
    for i, sim in enumerate(sims):
        if sim >= sim_thr:
            results.append(GLOBAL_CHEMBL_IDS[i])
    return results

# Top-level helper function required for Python Multiprocessing to serialize properly
def _worker_similarity(args):
    """Highly optimized single worker"""
    mid, smi, thres = args
    mol = Chem.MolFromSmiles(smi)
    if not mol: return mid, []
    
    query_fp = GLOBAL_FPGEN.GetFingerprint(mol)
    sims = DataStructs.BulkTanimotoSimilarity(query_fp, GLOBAL_FPS)
    
    results = [GLOBAL_CHEMBL_IDS[i] for i, sim in enumerate(sims) if sim >= thres]
    return mid, results

def get_all_similar_molecules(mols, thres, silent=False, server=DEFAULT_SERVER):
    _init_similarity_cache()
    
    sim_mols = []
    sim_mols_detail = {}
    
    tasks = [(mid, data[0], thres) for mid, data in mols.items()]
    num_cores = int(os.environ.get('SLURM_CPUS_PER_TASK', 1))
    
    if not silent: 
        print(f"\n>>> Launching MULTIPROCESSING on {num_cores} cores with Chunking...")
    
    with mp.Pool(processes=num_cores) as pool:
        # CRITICAL FIX: chunksize=1000 sends 1000 molecules to a CPU core at once, 
        # completely eliminating the IPC traffic jam.
        for i, (mid, sims) in enumerate(pool.imap_unordered(_worker_similarity, tasks, chunksize=1000)):
            sim_mols.extend(sims)
            sim_mols_detail[mid] = sims
            if (i + 1) % 5000 == 0 and not silent:
                print(f"\tProcessed {i + 1} similarities...")
                
    return set(sim_mols), sim_mols_detail
    
    # 2. Spawn the pool and blast through the seeds
    with mp.Pool(processes=num_cores) as pool:
        # imap_unordered is faster than map() because it yields results as soon as they finish
        for i, (mid, sims) in enumerate(pool.imap_unordered(_worker_similarity, tasks)):
            sim_mols.extend(sims)
            sim_mols_detail[mid] = sims
            if (i + 1) % 1000 == 0 and not silent:
                print(f"\tProcessed {i + 1} similarities (Parallel on {num_cores} cores)")
                
    return set(sim_mols), sim_mols_detail
# --- CSANNO MAIN LOOPS ---

def get_targets_info(mol_list, data_type="inchikeys", silent=False, server=DEFAULT_SERVER):
    mol_ids, mol_acts = {}, {}
    if not silent: print("Processing molecules...")

    if data_type == "inchikeys":
        for i, ick in enumerate(mol_list):
            mid = get_molecule_id(ick, silent=silent)
            if mid:
                mol_ids[ick] = mid
                mol_acts[mid] = get_activities(mid, silent=silent)
            if i % 1000 == 0 and not silent: print(f"\tProcessed {i} molecules")
    elif data_type == "chemblids":
        for i, mid in enumerate(mol_list):
            mol_acts[mid] = get_activities(mid, silent=silent)
            if i % 1000 == 0 and not silent: print(f"\tProcessed {i} molecules")

    ctargets = set()
    for mid, acts in mol_acts.items():
        for act in acts:
            if act.get("target_id"): ctargets.add(act["target_id"])

    if not silent: print("Getting the Chembl target data...")
    btargets = {}
    for i, target_id in enumerate(ctargets):
        btargs = get_target_components(target_id, silent=silent)
        btargets[target_id] = [(bt.get("organism", ""), bt.get("gene", ""), bt.get("uniprot", "")) for bt in btargs]
        if i % 1000 == 0 and not silent: print(f"\tProcessed {i} targets")

    return mol_ids, mol_acts, btargets

# Legacy caching overrides
def load_target_cache(*args, **kwargs): return {}
def save_target_cache(*args, **kwargs): pass

# Backward compatible wrappers
get_chembl_id = get_molecule_id
get_activities_chembl = get_activities
get_targets_chembl = get_target_components
get_targets_info_chembl = get_targets_info
get_sims = get_similar_molecules
get_all_sims = get_all_similar_molecules
