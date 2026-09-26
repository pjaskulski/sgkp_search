"""Read-only comparison of the published SGKP indexes with source JSON."""

import argparse
import json
import random
import sqlite3
from pathlib import Path
from urllib.parse import quote

from sgkp_core import file_hash, normalize, passages, read_volume, source_files
from sgkp_services import Meili, ROOT


def check(manifest_path: Path, sample_size: int = 64) -> dict:
    manifest = json.loads(manifest_path.read_text())
    input_dir = Path(manifest["source_dir"])
    meili = Meili(write=True)
    actual = {
        "entries": meili.stats(manifest["entries_index"])["numberOfDocuments"],
        "passages": meili.stats(manifest["passages_index"])["numberOfDocuments"],
    }
    if actual != manifest["counts"]:
        raise ValueError(f"Liczność indeksów nie zgadza się z manifestem: {actual}")
    for path in source_files(input_dir):
        if file_hash(path) != manifest["sha256"][path.name]:
            raise ValueError(f"Źródło zmieniło się po imporcie: {path.name}")
    with sqlite3.connect(manifest["lookup_db"]) as db:
        rows = db.execute("SELECT id, source_file, record_index, element_index FROM entries").fetchall()
    randomizer = random.Random(20260925)
    chosen = randomizer.sample(rows, min(sample_size, len(rows)))
    chosen += [row for row in rows if row[0] == "08-05076" and row not in chosen]
    checked, skipped, checked_passages = 0, 0, 0
    volumes = {}
    for identifier, filename, record_index, element_index in chosen:
        if filename not in volumes:
            volumes[filename] = read_volume(input_dir / filename)
        parent = volumes[filename][record_index]
        if element_index is None and parent["rodzaj"] == "zbiorcze":
            skipped += 1
            continue
        element = parent["elementy"][element_index] if element_index is not None else None
        expected = normalize(parent, filename, record_index, element, element_index)
        indexed = meili.request("GET", f"/indexes/{quote(manifest['entries_index'])}/documents/{quote(identifier)}")
        for key, value in expected.items():
            if indexed.get(key) != value:
                raise ValueError(f"Różnica w {identifier}.{key}")
        source_passages = passages(expected)
        to_check = source_passages if identifier == "08-05076" else source_passages[:1]
        for expected_passage in to_check:
            indexed_passage = meili.request("GET", f"/indexes/{quote(manifest['passages_index'])}/documents/{quote(expected_passage['passage_id'])}")
            for key, value in expected_passage.items():
                if indexed_passage.get(key) != value:
                    raise ValueError(f"Różnica we fragmencie {expected_passage['passage_id']}.{key}")
            checked_passages += 1
        checked += 1
    return {"counts": actual, "sample_checked": checked, "passages_checked": checked_passages,
        "containers_skipped": skipped, "sha256_checked": 16}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "runtime" / "active_manifest.json")
    parser.add_argument("--sample-size", type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(check(args.manifest, args.sample_size), ensure_ascii=False))
