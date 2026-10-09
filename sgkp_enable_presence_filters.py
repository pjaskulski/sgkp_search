"""Add presence flags and the Catholic parish filter without replacing text or vectors."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from urllib.parse import quote, urlencode

from sgkp_core import PRESENCE_FIELDS, file_hash, iter_entries, source_files
from sgkp_services import Meili, ROOT


def stage_documents(meili, config, flags, database, batch_size):
    """Read and validate all existing document IDs before making any changes."""
    counts = {}
    for kind, primary in (("entries", "ID"), ("passages", "passage_id")):
        index = config[f"{kind}_index"]
        offset = 0
        while True:
            params = urlencode({"offset": offset, "limit": batch_size,
                                "fields": primary + (",entry_id" if kind == "passages" else "")})
            page = meili.request("GET", f"/indexes/{quote(index, safe='')}/documents?{params}")
            documents = page["results"]
            if not documents:
                break
            for document in documents:
                identifier = document[primary]
                entry_id = document["entry_id"] if kind == "passages" else identifier
                if entry_id not in flags:
                    raise ValueError(f"Dokument indeksu nie ma odpowiednika w źródłach: {identifier}")
                patch = {primary: identifier, **flags[entry_id]}
                database.execute("INSERT INTO patches VALUES (?, ?, ?)",
                                 (kind, identifier, json.dumps(patch, ensure_ascii=False)))
            offset += len(documents)
            print(f"Sprawdzono {kind}: {offset}", flush=True)
        expected = config["counts"][kind]
        if offset != expected:
            raise ValueError(f"Niezgodna liczba dokumentów {kind}: {offset}, oczekiwano {expected}")
        counts[kind] = offset
    database.commit()
    return counts


def update_indexes(meili, config, database, batch_size, timeout, extra_fields=()):
    for kind in ("entries", "passages"):
        index = config[f"{kind}_index"]
        path = f"/indexes/{quote(index, safe='')}"
        cursor = database.execute("SELECT payload FROM patches WHERE kind=? ORDER BY identifier", (kind,))
        done = 0
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            # PUT partially updates documents. Omitting _vectors preserves stored embeddings.
            task = meili.request("PUT", path + "/documents",
                                 body=[json.loads(row[0]) for row in batch], timeout=120)
            meili.wait_task(task, timeout=timeout)
            done += len(batch)
            print(f"Uzupełniono {kind}: {done}", flush=True)
        current = meili.request("GET", path + "/settings/filterable-attributes")
        additions = [flag for flag in (*PRESENCE_FIELDS, *extra_fields) if flag not in current]
        if additions:
            task = meili.request("PATCH", path + "/settings",
                                 body={"filterableAttributes": current + additions})
            meili.wait_task(task, timeout=timeout)
        if meili.stats(index)["numberOfDocuments"] != config["counts"][kind]:
            raise ValueError(f"Liczba dokumentów zmieniła się podczas aktualizacji: {index}")
        sample = database.execute("SELECT identifier, payload FROM patches WHERE kind=? LIMIT 1",
                                  (kind,)).fetchone()
        if sample:
            document = meili.request("GET", path + "/documents/" + quote(sample[0], safe=""))
            expected = json.loads(sample[1])
            if any(document.get(flag) is not expected[flag] for flag in PRESENCE_FIELDS):
                raise ValueError(f"Weryfikacja zapisanych pól nie powiodła się: {index}")
            if any(document.get(field) != expected[field] for field in extra_fields):
                raise ValueError(f"Weryfikacja dodatkowych pól nie powiodła się: {index}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    runtime = Path(os.getenv("SGKP_RUNTIME_DIR", str(ROOT / "runtime")))
    parser.add_argument("--manifest", type=Path, default=runtime / "active_manifest.json")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--task-timeout", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true", help="Sprawdź źródła i indeksy bez zapisu")
    args = parser.parse_args()
    if args.batch_size < 1 or args.task_timeout < 1:
        parser.error("Rozmiar partii i timeout muszą być dodatnie")
    original = args.manifest.read_bytes()
    config = json.loads(original)
    source_dir = Path(config["source_dir"])
    for path in source_files(source_dir):
        if file_hash(path) != config["sha256"][path.name]:
            raise ValueError(f"Źródło różni się od danych aktywnego indeksu: {path.name}")
    flags = {entry["ID"]: {**{flag: entry[flag] for flag in PRESENCE_FIELDS},
                           "parafia_katolicka": entry.get("parafia_katolicka")}
             for entry in iter_entries(source_dir)}
    meili = Meili(write=True)
    if not meili.key:
        raise ValueError("Brak klucza administracyjnego Meilisearch")
    with tempfile.TemporaryDirectory(prefix="presence-filters-") as temporary:
        with sqlite3.connect(str(Path(temporary) / "patches.sqlite")) as database:
            database.execute("CREATE TABLE patches (kind TEXT, identifier TEXT, payload TEXT, "
                             "PRIMARY KEY (kind, identifier))")
            counts = stage_documents(meili, config, flags, database, args.batch_size)
            print(f"Zweryfikowano dokumenty: {counts}", flush=True)
            if args.dry_run:
                print("Tryb kontrolny: nie zmieniono indeksów ani manifestu.")
                return
            update_indexes(meili, config, database, args.batch_size, args.task_timeout,
                           extra_fields=("parafia_katolicka",))
    for path in source_files(source_dir):
        if file_hash(path) != config["sha256"][path.name]:
            raise ValueError(f"Źródło zmieniło się podczas aktualizacji: {path.name}")
    if args.manifest.read_bytes() != original:
        raise ValueError("Manifest zmienił się podczas aktualizacji; nie nadpisuję go")
    config["presence_filters_version"] = 1
    config["catholic_parish_filter_version"] = 1
    temporary = args.manifest.with_suffix(".presence.tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(args.manifest)
    print("Filtry obecności informacji i parafii katolickiej są gotowe w obu indeksach.")


if __name__ == "__main__":
    main()
