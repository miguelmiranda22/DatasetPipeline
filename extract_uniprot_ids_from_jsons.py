import argparse
import glob
import json
import os
import sys
import time


def extract_targets_from_json_glob(active_glob, inactive_glob):
    files = sorted(glob.glob(active_glob)) + sorted(glob.glob(inactive_glob))
    print(f"    Found {len(files)} files ({active_glob} / {inactive_glob})")
    if not files:
        print("    WARNING: no files matched - check --dir and the glob patterns.")
        return set()

    targets = set()
    for fp in files:
        t_start = time.time()
        with open(fp, "r") as f:
            data = json.load(f)

        payload = data.get("raw_results", {}).get("internal_result_payload", {})
        targets_dict = (
            payload.get("active_genes_T01") or payload.get("inactive_genes_T01")
            or payload.get("active_genes_T0") or payload.get("inactive_genes_T0")
            or payload.get("active_genes") or payload.get("inactive_genes") or {}
        )

        before = len(targets)
        for mol_id, target_list in targets_dict.items():
            for t in target_list:
                t = str(t).strip()
                if t:
                    targets.add(t)

        del data, payload, targets_dict
        elapsed = time.time() - t_start
        print(f"      {os.path.basename(fp):<48} +{len(targets) - before:>7} new IDs  "
              f"(running total: {len(targets)})  [{elapsed:.1f}s]")

    return targets


def save_ids(ids, path, overwrite):
    if os.path.exists(path) and not overwrite:
        print(f"    REFUSING to overwrite existing {path} (pass --overwrite to replace it)")
        return False
    with open(path, "w") as f:
        for uid in sorted(ids):
            f.write(uid + "\n")
    print(f"    Saved {len(ids)} unique UniProt IDs to: {path}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="Folder holding the JSON shards (default: cwd)")
    ap.add_argument("--strict_out", default="uniprot_ids_strict_t0_json.txt")
    ap.add_argument("--nonstrict_out", default="uniprot_ids_nonstrict_t0_json.txt")
    ap.add_argument("--union_out", default="uniprot_ids_t0_json_union.txt")
    ap.add_argument("--skip_strict", action="store_true")
    ap.add_argument("--skip_nonstrict", action="store_true")
    ap.add_argument("--overwrite", action="store_true",
                    help="Replace output files that already exist")
    args = ap.parse_args()

    d = args.dir
    strict_active = os.path.join(d, "actives_t0_strict_years_dataset_*_results.json")
    strict_inactive = os.path.join(d, "inactives_t0_strict_years_dataset_*_results.json")
    nonstrict_active = os.path.join(d, "actives_t0_nonstrict_years_dataset_*_results.json")
    nonstrict_inactive = os.path.join(d, "inactives_t0_nonstrict_years_dataset_*_results.json")

    strict_ids, nonstrict_ids = set(), set()

    if not args.skip_strict:
        print("=" * 78)
        print(">>> [1/2] Extracting Target IDs from STRICT T0 CSANNO JSON output")
        print("=" * 78)
        strict_ids = extract_targets_from_json_glob(strict_active, strict_inactive)
        save_ids(strict_ids, args.strict_out, args.overwrite)

    if not args.skip_nonstrict:
        print("\n" + "=" * 78)
        print(">>> [2/2] Extracting Target IDs from NON-STRICT T0 CSANNO JSON output")
        print("=" * 78)
        nonstrict_ids = extract_targets_from_json_glob(nonstrict_active, nonstrict_inactive)
        save_ids(nonstrict_ids, args.nonstrict_out, args.overwrite)

    union = strict_ids | nonstrict_ids
    if union:
        print("\n" + "=" * 78)
        print(">>> UNION OF BOTH RULESETS")
        print("=" * 78)
        save_ids(union, args.union_out, args.overwrite)

    print("\n" + "=" * 78)
    print(">>> DONE")
    print("=" * 78)
    print(f"    strict T0 JSON collection      : {len(strict_ids)} unique IDs  -> {args.strict_out}")
    print(f"    non-strict T0 JSON collection  : {len(nonstrict_ids)} unique IDs  -> {args.nonstrict_out}")
    print(f"    union of the two               : {len(union)} unique IDs  -> {args.union_out}")

    if strict_ids and nonstrict_ids:
        print("\n" + "-" * 78)
        print(f"    in both rulesets               : {len(strict_ids & nonstrict_ids)}")
        print(f"    strict only                    : {len(strict_ids - nonstrict_ids)}")
        print(f"    non-strict only                : {len(nonstrict_ids - strict_ids)}")

    print("=" * 78)

    if not strict_ids and not nonstrict_ids:
        print("Nothing was extracted. Check --dir.")
        sys.exit(1)


if __name__ == "__main__":
    main()
