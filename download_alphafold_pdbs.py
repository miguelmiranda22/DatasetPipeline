import gzip
import os
import shutil

os.system("python -m pip install requests tqdm")

import requests
from tqdm import tqdm

if __name__ == "__main__":
    input_file = "unified_uniprot_ids_union.txt"
    pdb_folder = "alphafold_pdbs"

    if not os.path.exists(input_file):
        print(f"Error: '{input_file}' not found.")
        exit(1)

    with open(input_file, 'r') as f:
        unique_proteins = [line.strip() for line in f if line.strip()]

    if not os.path.exists(pdb_folder):
        os.makedirs(pdb_folder)
        print(f"Folder '{pdb_folder}' created.")
    else:
        print(f"Folder '{pdb_folder}' already exists.")

    print(f"Found {len(unique_proteins)} unique proteins to download.")

    not_found_list = []

    for up_id in tqdm(unique_proteins, desc="Downloading PDBs"):

        file_path = os.path.join(pdb_folder, f"{up_id}.pdb")

        if os.path.exists(file_path) or os.path.exists(file_path + ".gz"):
            continue

        url_v6 = f"https://alphafold.ebi.ac.uk/files/AF-{up_id}-F1-model_v6.pdb"
        url_v4 = f"https://alphafold.ebi.ac.uk/files/AF-{up_id}-F1-model_v4.pdb"

        try:
            response = requests.get(url_v6, stream=True)

            if response.status_code != 200:
                response = requests.get(url_v4, stream=True)

            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                not_found_list.append(up_id)

        except Exception as e:
            print(f"\nError downloading {up_id}: {e}")
            not_found_list.append(up_id)

    print("\n>>> Downloads completed!")

    pdb_files = [f for f in os.listdir(pdb_folder) if f.endswith(".pdb")]
    if pdb_files:
        print(f"Compressing {len(pdb_files)} PDB files...")
        for name in tqdm(pdb_files, desc="Gzipping"):
            src = os.path.join(pdb_folder, name)
            with open(src, 'rb') as f_in, gzip.open(src + ".gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            os.remove(src)
        print(f"Saved {len(pdb_files)} .pdb.gz files in '{pdb_folder}'.")

    if len(not_found_list) > 0:
        print(f"{len(not_found_list)} proteins could not be downloaded.")
        with open("alphafold_not_found.txt", "w") as f:
            for prot in not_found_list:
                f.write(f"{prot}\n")
        print("Saved missing IDs to 'alphafold_not_found.txt'.")
    else:
        print("All proteins successfully downloaded!")
