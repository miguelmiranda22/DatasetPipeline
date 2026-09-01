# Dataset pipeline

Builds the 4 final datasets from ChEMBL + AlphaFold.

`pip install -r requirements.txt`. The last two entries (scikit-bio, biopython) are only needed for step 6.

The PAAS toolkit (step 6) is a git submodule, so clone with:

```
git clone --recurse-submodules <this repo>
```

If you already cloned without it: `git submodule update --init`.

## 1. Chembl DB download

Go to https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/ , download chembl_37_sqlite.tar.gz and extract.

## 2. SQL extraction

`extract_sql_seeds_and_years.py` (via `extract_sql_seeds_and_years.sh`)

One query over the dump, restricted to the activity types the rulesets use, grouped to the earliest publication year per molecule/target.

- `seeds_part_0..9.txt` - 10 chunks, 3 tab-separated columns: ChEMBL id, `NA`, SMILES
- `chembl_year_mapping.csv` - molecule, target (accession / chembl id / pref name), year

## 3. CSANNO mining

`run_mining_t0_years.sh` - SLURM array 0-19 = 10 seed chunks x 2 rulesets.

Calls `csanno.py -search N|A -rules csanno_{strict,default}_rules.yaml -report AD -ofield U`. `-ofield U` makes the target field a UniProt accession. Actives and inactives are mined separately; the label comes from the ruleset, not from the seed file.

- `{actives,inactives}_t0_strict_years_dataset_0..9_results.json`
- `{actives,inactives}_t0_nonstrict_years_dataset_0..9_results.json`

## 4. Protein IDs

`extract_uniprot_ids_from_jsons.py` - every target accession appearing in the mining output.

- `uniprot_ids_strict_t0_json.txt`, `uniprot_ids_nonstrict_t0_json.txt`, `uniprot_ids_t0_json_union.txt`

## 5. Structures

`download_alphafold_pdbs.py` - AlphaFold PDB per accession, v6 with v4 fallback, gzipped at the end.

- `alphafold_pdbs/*.pdb.gz`, `alphafold_not_found.txt`

## 6. PAAS encoding

`PAAS-Toolkit/` (https://github.com/aofalcao/PAAS-Toolkit). Reads the structures from `sp_structs/*.gz`, so point it at the folder from step 5.

**6.1** `MakeAAVecs.py` - amino-acid coordinates from `aas.txt` + `blosum62.txt` -> `AAVecs.pickle`

**6.2** `PAAS_Processor.py 4.0` - amino acids within 4.0 A of each atom, per structure -> `paas_4.0_pickles/`

**6.3** `MakePAASCentroids.py` - two-stage KMeans, 144 x 144 = 20736 -> `PAAS_Clusters.pickle`

**6.4** `ProcessPAASidxs.py` - one index set per protein -> `AllProtPaas.pickle`, renamed `all_prots_fps.pickle`

**6.5** `PAASTrimmer.py 5000` - drops the 5000 lowest-information (most frequent) labels, leaving 144x144-5000 = 15736 -> `all_prots_fps_selected.pickle`

## 7. Merge

`merge_all_prots_datasets_uniform.py <task 0-3>` - 2 dictionaries x 2 rulesets.

Morgan encoding of the SMILES (radius 4, 2048 bits), PAAS lookup on the target, Zeros-Win conflict resolution (a pair is Active only if every measurement was Active), Year attached from the mapping.

| | strict | non-strict |
|---|---|---|
| AllProts | `final_ml_dataset_T0_strict_zeros_win_all_prots_uniform.pkl` | `..._nonstrict_..._all_prots_uniform.pkl` |
| AllProtsSelected | `..._strict_..._all_prots_selected_uniform.pkl` | `..._nonstrict_..._all_prots_selected_uniform.pkl` |

Blind (90/10 by protein) and prospective (Year <= 2022 / >= 2023) splits are made downstream, in the training scripts.

## Running the whole thing on the cluster

`cluster/` submits every stage as its own SLURM job, chained with `--dependency=afterok`.

```
BASE_DIR=$HOME/paas_rerun PIPE_DIR=$HOME/DatasetPipeline \
CHEMBL_DB=$HOME/chembl_37/chembl_37_sqlite/chembl_37.db \
  cluster/run_pipeline.sh
```

`cluster/preflight.sh` runs first and refuses to submit if a script, the database or a dependency is
missing. Everything runs in a fresh `$BASE_DIR/run`, so the existing datasets are never touched.
Stage 09 diffs the result against them.

All four datasets are built (merge tasks 0-3): AllProts and AllProtsSelected, strict and non-strict.
The trimming size is 5000, set by `PRUNING_SIZE` in `cluster/config.sh`.

| stage | resources |
|---|---|
| 01 sql | 96G, 8 cpu, 12h |
| 02 mining (array 0-19) | 32G, 16 cpu, 24h |
| 03 protein ids | 24G, 4 cpu, 4h |
| 04 structures | 8G, 2 cpu, 12h |
| 05 paas process | 125G, exclusive node, 24h |
| 06 paas centroids | 125G, 32 cpu, 24h |
| 07 paas idxs | 64G, 8 cpu, 8h |
| 08 merge (array 0-3) | 100G, 16 cpu, 12h |
| 09 verify | 100G, 4 cpu, 4h |

Stage 05 takes a whole node because `PAAS_Processor.py` sizes its pool from `mp.cpu_count()`, which
reports the node's cores rather than the SLURM allocation.
