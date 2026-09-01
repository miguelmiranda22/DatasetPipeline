import argparse
import os
import sys

import numpy as np
import pandas as pd

NAMES = [
    "final_ml_dataset_T0_strict_zeros_win_all_prots_uniform.pkl",
    "final_ml_dataset_T0_nonstrict_zeros_win_all_prots_uniform.pkl",
    "final_ml_dataset_T0_strict_zeros_win_all_prots_selected_uniform.pkl",
    "final_ml_dataset_T0_nonstrict_zeros_win_all_prots_selected_uniform.pkl",
]


def fp_key(v):
    if v is None:
        return None
    a = np.asarray(v)
    return a.tobytes()


def compare(new_path, ref_path):
    new = pd.read_pickle(new_path)
    ref = pd.read_pickle(ref_path)

    print("  rows            new %-12d ref %-12d %s" % (
        len(new), len(ref), "MATCH" if len(new) == len(ref) else "DIFFER"))
    print("  unique proteins new %-12d ref %-12d %s" % (
        new.Target.nunique(), ref.Target.nunique(),
        "MATCH" if new.Target.nunique() == ref.Target.nunique() else "DIFFER"))

    for col in ("Activity", "Year"):
        if col in new and col in ref:
            a, b = new[col].value_counts().to_dict(), ref[col].value_counts().to_dict()
            if col == "Activity":
                print("  activity        new %-12s ref %-12s %s" % (
                    a, b, "MATCH" if a == b else "DIFFER"))
            else:
                print("  year resolved   new %-12d ref %-12d" % (
                    new[col].notna().sum(), ref[col].notna().sum()))

    kn = set(zip(new.SMILES, new.Target))
    kr = set(zip(ref.SMILES, ref.Target))
    print("  pairs           shared %d | only new %d | only ref %d" % (
        len(kn & kr), len(kn - kr), len(kr - kn)))

    shared = kn & kr
    if shared:
        n = new.set_index(["SMILES", "Target"]).loc[list(shared)]
        r = ref.set_index(["SMILES", "Target"]).loc[list(shared)]
        lab = int((n.Activity.values != r.Activity.values).sum())
        print("  label conflicts on shared pairs: %d" % lab)

        idx = list(shared)[:2000]
        n2 = new.set_index(["SMILES", "Target"]).loc[idx]
        r2 = ref.set_index(["SMILES", "Target"]).loc[idx]
        for col in ("Morgan_FP", "PAAS_FP"):
            if col in n2 and col in r2:
                bad = sum(1 for x, y in zip(n2[col], r2[col]) if fp_key(x) != fp_key(y))
                print("  %-9s mismatches on 2000 sampled pairs: %d" % (col, bad))
    return len(kn - kr) == 0 and len(kr - kn) == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new_dir", required=True)
    ap.add_argument("--ref_dir", required=True)
    args = ap.parse_args()

    identical = True
    for name in NAMES:
        new_path = os.path.join(args.new_dir, name)
        ref_path = os.path.join(args.ref_dir, name)
        print("=" * 70)
        print(name)
        print("=" * 70)
        if not os.path.exists(new_path):
            print("  new file missing: %s" % new_path)
            identical = False
            continue
        if not os.path.exists(ref_path):
            print("  no reference to compare against: %s" % ref_path)
            continue
        identical &= compare(new_path, ref_path)
        print()

    print("=" * 70)
    print("REPRODUCED EXACTLY" if identical else "DIFFERENCES FOUND - see above")
    print("=" * 70)


if __name__ == "__main__":
    main()
