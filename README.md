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

**6.5** `PAASTrimmer.py <n>` - drops the n lowest-information (most frequent) labels -> `all_prots_fps_selected.pickle`

## 7. Merge

`merge_all_prots_datasets_uniform.py <task 0-3>` - 2 dictionaries x 2 rulesets.

Morgan encoding of the SMILES (radius 4, 2048 bits), PAAS lookup on the target, Zeros-Win conflict resolution (a pair is Active only if every measurement was Active), Year attached from the mapping.

| | strict | non-strict |
|---|---|---|
| AllProts | `final_ml_dataset_T0_strict_zeros_win_all_prots_uniform.pkl` | `..._nonstrict_..._all_prots_uniform.pkl` |
| AllProtsSelected | `..._strict_..._all_prots_selected_uniform.pkl` | `..._nonstrict_..._all_prots_selected_uniform.pkl` |

Blind (90/10 by protein) and prospective (Year <= 2022 / >= 2023) splits are made downstream, in the training scripts.
