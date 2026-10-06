"""Enable archeo searches on the active entries index without regenerating vectors."""
import json
import os
from pathlib import Path
from urllib.parse import quote

from sgkp_services import Meili, ROOT


def main():
    runtime = Path(os.getenv("SGKP_RUNTIME_DIR", str(ROOT / "runtime")))
    config = json.loads((runtime / "active_manifest.json").read_text())
    index = config["entries_index"]
    meili = Meili(write=True)
    current = meili.request("GET", f"/indexes/{quote(index, safe='')}/settings/searchable-attributes")
    if "*" not in current and "archeo" not in current:
        meili.settings(index, {"searchableAttributes": current + ["archeo"]})
    print(f"Indeks {index}: wyszukiwanie w archeo jest dostępne.")


if __name__ == "__main__":
    main()
