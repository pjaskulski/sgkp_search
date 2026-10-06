"""Validate SGKP sources and publish a new pair of Meilisearch indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from sgkp_core import FILTER_FIELDS, file_hash, normalize, passages, read_volume, source_files, validate
from sgkp_qa import check as check_index
from sgkp_services import Embeddings, Meili, ROOT, ServiceError


RULE_VERSION = "2026-09-25-v1"
SEARCHABLE = ["ID", "nazwa", "warianty_nazw_text", "typ", "opis_lokalizacji", "powiat_ujednolicony", "gmina", "gubernia_ujednolicona", "obiekty_sakralne", "przemysłowe", "młyny", "text"]


class EmbeddingCache:
    def __init__(self, path: Path, model: str):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, vector TEXT NOT NULL)")
        self.model = model

    def key(self, text: str) -> str:
        return hashlib.sha256((self.model + "\0" + RULE_VERSION + "\0" + text).encode()).hexdigest()

    def embed(self, texts: list[str], service: Embeddings, batch_size: int = 128) -> list[list[float]]:
        keys = [self.key(text) for text in texts]
        known = {}
        for key in set(keys):
            row = self.db.execute("SELECT vector FROM vectors WHERE key = ?", (key,)).fetchone()
            if row:
                known[key] = json.loads(row[0])
        missing = {}
        for key, text in zip(keys, texts):
            if key not in known:
                missing[key] = text
        items = list(missing.items())

        def fetch(part):
            worker_service = Embeddings()
            worker_service.url, worker_service.model = service.url, service.model
            worker_service.key, worker_service.dimensions = service.key, service.dimensions
            for attempt in range(4):
                try:
                    return worker_service.embed([text for _, text in part])
                except ServiceError as exc:
                    if attempt == 3 or exc.status not in (None, 429, 500, 502, 503, 504):
                        raise
                    time.sleep(2 ** attempt)

        batches = [items[start:start + batch_size] for start in range(0, len(items), batch_size)]
        workers = max(1, min(8, int(os.getenv("EMBEDDING_WORKERS", "4"))))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(fetch, part): part for part in batches}
            for future in as_completed(futures):
                part = futures[future]
                for (key, _), vector in zip(part, future.result()):
                    known[key] = vector
                    self.db.execute("INSERT OR REPLACE INTO vectors VALUES (?, ?)", (key, json.dumps(vector, separators=(",", ":"))))
                self.db.commit()
        return [known[key] for key in keys]


def lookup_db(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE entries (id TEXT PRIMARY KEY, source_file TEXT NOT NULL, record_index INTEGER NOT NULL, element_index INTEGER)")
    return db


def settings(primary: str, with_vectors: bool, dimensions: int) -> dict:
    result = {
        "searchableAttributes": SEARCHABLE if primary == "ID" else ["nazwa", "text"],
        "filterableAttributes": list(FILTER_FIELDS) + (["entry_id"] if primary == "passage_id" else []),
        "faceting": {"maxValuesPerFacet": 2000},
        "pagination": {"maxTotalHits": 10000},
    }
    if with_vectors:
        result["embedders"] = {"jina": {"source": "userProvided", "dimensions": dimensions}}
    return result


def ingest(input_dir: Path, output_dir: Path, suffix: str, with_vectors: bool, entry_batch_size: int, passage_batch_size: int) -> dict:
    report = validate(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"validation_{suffix}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if report["errors"]:
        raise ValueError(f"Walidacja źródeł wykazała {len(report['errors'])} błędów: {report_path}")
    meili = Meili(write=True)
    if not meili.key:
        raise ValueError("Brak MEILI_API_KEY lub API_MEILISEARCH_ADMIN; raport walidacji jest gotowy, import nie został rozpoczęty")
    embedding = Embeddings() if with_vectors else None
    if with_vectors and not embedding.configured:
        raise ValueError("Brak AI_TEST_KEY i API_JINA_KEY")
    cache = EmbeddingCache(output_dir / "embeddings.sqlite", embedding.model) if embedding else None
    entries_index = f"sgkp_entries_{suffix}"
    passages_index = f"sgkp_passages_{suffix}"
    lookup_path = output_dir / f"lookup_{suffix}.sqlite"
    if lookup_path.exists():
        raise FileExistsError(lookup_path)
    meili.create_index(entries_index, "ID")
    meili.create_index(passages_index, "passage_id")
    meili.settings(entries_index, settings("ID", with_vectors, embedding.dimensions if embedding else 0))
    meili.settings(passages_index, settings("passage_id", with_vectors, embedding.dimensions if embedding else 0))
    lookup = lookup_db(lookup_path)
    entry_batch: list[dict] = []
    passage_batch: list[dict] = []
    passage_count = 0
    entry_count = 0

    def flush():
        nonlocal entry_batch, passage_batch
        if not entry_batch:
            return
        if embedding:
            vectors = cache.embed([passage["text"] for passage in passage_batch], embedding)
            grouped: dict[str, list] = {}
            for passage, vector in zip(passage_batch, vectors):
                passage["_vectors"] = {"jina": vector}
                grouped.setdefault(passage["entry_id"], []).append(vector)
            for entry in entry_batch:
                entry["_vectors"] = {"jina": grouped[entry["ID"]]}
        meili.add_documents(entries_index, entry_batch)
        for start in range(0, len(passage_batch), passage_batch_size):
            meili.add_documents(passages_index, passage_batch[start:start + passage_batch_size])
        entry_batch, passage_batch = [], []

    for path in source_files(input_dir):
        for record_index, row in enumerate(read_volume(path)):
            lookup.execute("INSERT INTO entries VALUES (?, ?, ?, NULL)", (row["ID"], path.name, record_index))
            if row["rodzaj"] == "indywidualne":
                atoms = [(None, row)]
            else:
                atoms = list(enumerate(row["elementy"]))
            for element_index, element in atoms:
                entry = normalize(row, path.name, record_index, element if element_index is not None else None, element_index)
                if element_index is not None:
                    lookup.execute("INSERT INTO entries VALUES (?, ?, ?, ?)", (entry["ID"], path.name, record_index, element_index))
                chunks = passages(entry)
                entry_batch.append(entry)
                passage_batch.extend(chunks)
                entry_count += 1
                passage_count += len(chunks)
                if len(entry_batch) >= entry_batch_size or len(passage_batch) >= passage_batch_size:
                    flush()
        lookup.commit()
        print(f"{path.name}: {entry_count} haseł, {passage_count} fragmentów", flush=True)
    flush()
    lookup.commit()
    lookup.close()
    actual_entries = meili.stats(entries_index)["numberOfDocuments"]
    actual_passages = meili.stats(passages_index)["numberOfDocuments"]
    if actual_entries != entry_count or actual_passages != passage_count or entry_count != report["counts"]["atomic"]:
        raise ValueError(f"Niezgodne liczności indeksów: {actual_entries}/{entry_count}, {actual_passages}/{passage_count}")
    for path in source_files(input_dir):
        if file_hash(path) != report["sha256"][path.name]:
            raise ValueError(f"Plik źródłowy zmienił się w trakcie importu: {path}")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(), "rule_version": RULE_VERSION,
        "source_dir": str(input_dir.resolve()), "sha256": report["sha256"],
        "source_stat": {path.name: {"size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns} for path in source_files(input_dir)},
        "entries_index": entries_index, "passages_index": passages_index,
        "lookup_db": str(lookup_path.resolve()), "counts": {"entries": entry_count, "passages": passage_count},
        "vectors": with_vectors, "embedding_model": embedding.model if embedding else None,
    }
    versioned_path = output_dir / f"manifest_{suffix}.json"
    versioned_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    qa_report = check_index(versioned_path, sample_size=16)
    (output_dir / f"qa_{suffix}.json").write_text(json.dumps(qa_report, ensure_ascii=False, indent=2) + "\n")
    active_temp = output_dir / "active_manifest.json.tmp"
    active_temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    active_temp.replace(output_dir / "active_manifest.json")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runtime")
    parser.add_argument("--suffix", default=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--with-vectors", action="store_true")
    parser.add_argument("--entry-batch-size", type=int, default=200)
    parser.add_argument("--passage-batch-size", type=int, default=500)
    args = parser.parse_args(argv)
    if not args.suffix.replace("_", "").isalnum():
        parser.error("Nieprawidłowy sufiks indeksu")
    if args.entry_batch_size < 1 or args.passage_batch_size < 1:
        parser.error("Wielkość partii musi być dodatnia")
    if args.check_only:
        report = validate(args.input_dir)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / f"validation_{args.suffix}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"report": str(path), "counts": report["counts"], "errors": len(report["errors"]), "warnings": len(report["warnings"])}, ensure_ascii=False))
        return 1 if report["errors"] else 0
    try:
        print(json.dumps(ingest(args.input_dir, args.output_dir, args.suffix, args.with_vectors, args.entry_batch_size, args.passage_batch_size), ensure_ascii=False))
        return 0
    except (ValueError, FileExistsError, ServiceError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
