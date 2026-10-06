"""Retrieve assay, molecule and document provenance for the preserved MIC cohort."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from urllib.parse import urlencode
import pandas as pd
from abwm.acquire import get
from abwm.data import dump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = pd.read_csv(args.data_root / "curated/mic_measurements.csv", dtype=str)
    specs = [("assay", "assay", "assays"), ("molecule", "molecule_id", "molecules"), ("document", "study", "documents")]

    def acquire(spec):
        endpoint, column, plural = spec
        ids = sorted(data[column].dropna().unique())
        rows = []
        for i in range(0, len(ids), 75):
            query = urlencode({endpoint + "_chembl_id__in": ",".join(ids[i:i + 75]), "limit": 1000})
            path = get("https://www.ebi.ac.uk/chembl/api/data/" + endpoint + ".json?" + query,
                       f"{endpoint}_{i // 75:03d}.json", "chembl_joined", "ChEMBL 37", "CC BY-SA 3.0",
                       data_root=args.data_root)
            if path:
                rows.extend(json.loads(path.read_text())[plural])
        dump(args.data_root / f"curated/chembl_{plural}.json", rows)
        found = {r[endpoint + "_chembl_id"] for r in rows}
        result = dict(endpoint=endpoint, requested=len(ids), obtained=len(found), missing=sorted(set(ids) - found))
        if endpoint == "assay":
            result["explicit_taxon_conflicts"] = [r["assay_chembl_id"] for r in rows
                                                 if r.get("assay_tax_id") and str(r["assay_tax_id"]) != "470"]
        return result

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(acquire, specs))
    dump(args.output, dict(tables=results,
                           label_source="Activity original mass-concentration fields; metadata does not replace experimental labels.",
                           form_mw="Molecule properties retained for provenance; no molar conversion without verified tested form."))


if __name__ == "__main__":
    main()
