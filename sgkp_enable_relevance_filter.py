"""Enable per-entry passage filtering on the currently active index."""
import json
import os
from pathlib import Path
from urllib.parse import quote

from sgkp_services import Meili, ROOT


def main():
    runtime = Path(os.getenv("SGKP_RUNTIME_DIR", str(ROOT / "runtime")))
    config = json.loads((runtime / "active_manifest.json").read_text())
    index = config["passages_index"]
    meili = Meili(write=True)
    current = meili.request("GET", f"/indexes/{quote(index, safe='')}/settings/filterable-attributes")
    if "entry_id" not in current:
        meili.settings(index, {"filterableAttributes": current + ["entry_id"]})
    print(f"Indeks {index}: filtrowanie po entry_id jest dostępne.")


if __name__ == "__main__":
    main()
