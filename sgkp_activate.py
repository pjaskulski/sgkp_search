"""Switch the active SGKP index pair to a previously imported version."""

import argparse
import json
from pathlib import Path

from sgkp_core import file_hash, source_files
from sgkp_services import Meili, ROOT


def activate(runtime: Path, suffix: str) -> dict:
    if not suffix.replace("_", "").isalnum():
        raise ValueError("Nieprawidłowy sufiks indeksu")
    source = runtime / f"manifest_{suffix}.json"
    manifest = json.loads(source.read_text())
    for path in source_files(Path(manifest["source_dir"])):
        if file_hash(path) != manifest["sha256"][path.name]:
            raise ValueError(f"Źródło nie odpowiada wersji {suffix}: {path.name}")
    meili = Meili(write=True)
    for kind in ("entries", "passages"):
        actual = meili.stats(manifest[f"{kind}_index"])["numberOfDocuments"]
        if actual != manifest["counts"][kind]:
            raise ValueError(f"Indeks {kind} ma {actual} dokumentów zamiast {manifest['counts'][kind]}")
    temporary = runtime / "active_manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(runtime / "active_manifest.json")
    return {"active_entries_index": manifest["entries_index"], "active_passages_index": manifest["passages_index"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=ROOT / "runtime")
    parser.add_argument("--suffix", required=True)
    args = parser.parse_args()
    print(json.dumps(activate(args.runtime, args.suffix), ensure_ascii=False))
