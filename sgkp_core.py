"""Source normalization and passage offsets for the SGKP search indexes."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


VOLUMES = tuple(f"{number:02d}" for number in range(1, 17))
PRESENCE_FIELDS = {
    f"has_{field}": field for field in (
        "obiekty_sakralne", "szkoły", "młyny", "przemysłowe", "zabytki",
        "archeo", "opieka_zdrowotna", "biblioteki", "uzdrowiska", "celne",
        "budownictwo_palacowe", "poczta", "stacje_drogi_zelaznej", "handel", "rzemioslo",
        "urzędy", "architektura_krajobrazu", "hodowla", "nekropolie", "dobroczynnosc",
        "sądy", "wojsko", "żegluga", "kolekcjonerstwo", "drukarnie", "muzealnictwo",
        "księgarnie", "bursa", "l_mk_statystyka", "l_dm_statystyka",
        "ludność_wyznanie", "własność_ziemska",
    )
}
PRESENCE_FIELD_VERSIONS = {flag: 1 for flag in PRESENCE_FIELDS}
PRESENCE_FIELD_VERSIONS.update(has_celne=2, has_budownictwo_palacowe=3, has_poczta=3,
                              has_stacje_drogi_zelaznej=3, has_handel=3, has_rzemioslo=3)
PRESENCE_FIELD_VERSIONS.update({flag: 4 for flag, field in PRESENCE_FIELDS.items()
                              if field in (
                                  "urzędy", "architektura_krajobrazu", "hodowla", "nekropolie",
                                  "dobroczynnosc", "sądy", "wojsko", "żegluga", "kolekcjonerstwo",
                                  "drukarnie", "muzealnictwo", "księgarnie", "bursa")})
STATISTICAL_FIELDS = ("l_mk_statystyka", "l_dm_statystyka", "ludność_wyznanie", "własność_ziemska")
PRESENCE_FIELD_VERSIONS.update({f"has_{field}": 5 for field in STATISTICAL_FIELDS})
PRESENCE_FILTER_VERSION = max(PRESENCE_FIELD_VERSIONS.values())
BOOLEAN_FILTER_FIELDS = ("jest_miejscowoscia", "królestwo_polskie", *PRESENCE_FIELDS)
FILTER_FIELDS = (
    "tom", "rodzaj", "jest_miejscowoscia", "typ_punktu_osadniczego", "typ",
    "powiat_ujednolicony", "gmina", "parafia_katolicka", "gubernia_ujednolicona", "królestwo_polskie",
    *PRESENCE_FIELDS,
)
COPY_FIELDS = (
    "typ", "typ_punktu_osadniczego", "powiat_ocr", "powiat_ujednolicony",
    "gmina", "gubernia_ujednolicona", "królestwo_polskie", "opis_lokalizacji",
    "parafia_katolicka", "obiekty_sakralne", "przemysłowe", "młyny", "archeo",
)


def source_files(input_dir: Path) -> list[Path]:
    paths = [input_dir / f"sgkp_{vol}.json" for vol in VOLUMES]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Brak plików źródłowych: " + ", ".join(missing))
    return paths


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_volume(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path}: oczekiwano tablicy rekordów")
    return data


def validate(input_dir: Path) -> dict:
    """Return a complete report; errors stop indexing, numbering warnings do not."""
    errors: list[dict] = []
    warnings: list[dict] = []
    seen: dict[str, str] = {}
    counts = {"records": 0, "individual": 0, "collective": 0, "elements": 0}
    hashes = {}
    for path in source_files(input_dir):
        vol = path.stem[-2:]
        hashes[path.name] = file_hash(path)
        for record_index, row in enumerate(read_volume(path)):
            counts["records"] += 1
            where = f"{path.name}[{record_index}]"
            if not isinstance(row, dict):
                errors.append({"location": where, "issue": "invalid_record_type"})
                continue
            identifier = row.get("ID")
            kind = row.get("rodzaj")
            if not isinstance(identifier, str) or not identifier.startswith(f"{vol}-"):
                errors.append({"location": where, "issue": "invalid_id", "value": identifier})
            elif identifier in seen:
                errors.append({"location": where, "issue": "duplicate_id", "value": identifier, "first": seen[identifier]})
            else:
                seen[identifier] = where
            if kind not in ("indywidualne", "zbiorcze"):
                errors.append({"location": where, "issue": "invalid_rodzaj", "value": kind})
            else:
                counts["individual" if kind == "indywidualne" else "collective"] += 1
            if not isinstance(row.get("nazwa"), str) or not row["nazwa"].strip():
                errors.append({"location": where, "issue": "invalid_nazwa"})
            if row.get("tom") != vol or type(row.get("strona")) is not int or row["strona"] < 1:
                errors.append({"location": where, "issue": "invalid_tom_strona"})
            if not isinstance(row.get("text"), str) or not row["text"]:
                errors.append({"location": where, "issue": "missing_text"})
            children = row.get("elementy", [])
            if not isinstance(children, list) or (kind == "zbiorcze" and not children):
                errors.append({"location": where, "issue": "invalid_elementy"})
                continue
            if kind == "indywidualne" and children:
                errors.append({"location": where, "issue": "individual_has_elements"})
            for element_index, element in enumerate(children):
                counts["elements"] += 1
                child_where = f"{where}.elementy[{element_index}]"
                if not isinstance(element, dict):
                    errors.append({"location": child_where, "issue": "invalid_element_type"})
                    continue
                child_id = element.get("ID")
                if not isinstance(child_id, str) or not isinstance(identifier, str) or not child_id.startswith(identifier + "-"):
                    errors.append({"location": child_where, "issue": "invalid_parent_id", "value": child_id})
                elif child_id in seen:
                    errors.append({"location": child_where, "issue": "duplicate_id", "value": child_id, "first": seen[child_id]})
                else:
                    seen[child_id] = child_where
                nr = element.get("nr")
                if not isinstance(nr, str) or not nr.isdigit():
                    errors.append({"location": child_where, "issue": "invalid_nr", "value": nr})
                elif isinstance(child_id, str):
                    suffix = child_id.rsplit("-", 1)[-1]
                    if suffix.isdigit() and int(suffix) != int(nr):
                        warnings.append({"location": child_where, "issue": "id_nr_mismatch", "id": child_id, "nr": nr})
                if element.get("rodzaj") != "element":
                    errors.append({"location": child_where, "issue": "invalid_rodzaj", "value": element.get("rodzaj")})
                if not isinstance(element.get("nazwa"), str) or not element["nazwa"].strip():
                    errors.append({"location": child_where, "issue": "invalid_nazwa"})
                if not isinstance(element.get("text"), str) or not element["text"]:
                    errors.append({"location": child_where, "issue": "missing_text"})
    counts["atomic"] = counts["individual"] + counts["elements"]
    return {"counts": counts, "sha256": hashes, "errors": errors, "warnings": warnings}


def has_information(value) -> bool:
    """Ignore absent annotations, empty containers and whitespace-only values."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(has_information(item) for item in value)
    if isinstance(value, dict):
        return any(has_information(item) for item in value.values())
    return value is not None


def has_statistical_information(field: str, value) -> bool:
    """Require actual data, not a scope title or a date alone; zero is valid."""
    if isinstance(value, list):
        return any(has_statistical_information(field, item) for item in value)
    if not isinstance(value, dict):
        return has_information(value)
    if field in ("l_mk_statystyka", "l_dm_statystyka"):
        return has_statistical_information(field, value.get("liczba"))
    if field == "ludność_wyznanie":
        details = value.get("struktura_wyznaniowa")
        return isinstance(details, list) and any(isinstance(item, dict) and
            any(has_information(item.get(key)) for key in ("wyznanie_ocr", "wyznanie", "liczba"))
            for item in details)
    details = value.get("land")
    return isinstance(details, list) and any(isinstance(item, dict) and
        has_information(item.get("area_of_ground")) for item in details)


def presence_flags(source: dict) -> dict:
    return {flag: (has_statistical_information(field, source.get(field))
                   if field in STATISTICAL_FIELDS else has_information(source.get(field)))
            for flag, field in PRESENCE_FIELDS.items()}


def normalize(row: dict, source_file: str, record_index: int, element: dict | None = None, element_index: int | None = None) -> dict:
    source = element if element is not None else row
    document = {
        "ID": source["ID"], "nazwa": source["nazwa"], "text": source["text"],
        "rodzaj": "element" if element is not None else "indywidualne",
        "tom": row["tom"], "strona": row["strona"],
        "source_file": source_file, "record_index": record_index,
    }
    if element is not None:
        document.update(parent_id=row["ID"], parent_nazwa=row["nazwa"], nr=element["nr"], element_index=element_index)
    for key in COPY_FIELDS:
        value = source.get(key)
        if value is not None:
            document[key] = value
    variants = source.get("warianty_nazw") or []
    document["warianty_nazw_text"] = [v["wariant_nazwy"] for v in variants if isinstance(v, dict) and isinstance(v.get("wariant_nazwy"), str)]
    document["jest_miejscowoscia"] = bool(source.get("typ_punktu_osadniczego"))
    document.update(presence_flags(source))
    return document


def iter_entries(input_dir: Path):
    for path in source_files(input_dir):
        for record_index, row in enumerate(read_volume(path)):
            if row["rodzaj"] == "indywidualne":
                yield normalize(row, path.name, record_index)
            else:
                for element_index, element in enumerate(row["elementy"]):
                    yield normalize(row, path.name, record_index, element, element_index)


def passages(entry: dict, max_chars: int = 1500, overlap: int = 120) -> list[dict]:
    """Split without changing source characters; offsets use Python Unicode positions."""
    if max_chars < 100 or not 0 <= overlap < max_chars // 2:
        raise ValueError("Nieprawidłowe granice fragmentów")
    content = entry["text"]
    result = []
    start = 0
    while start < len(content):
        end = min(len(content), start + max_chars)
        if end < len(content):
            floor = start + int(max_chars * 0.75)
            split = max(content.rfind(mark, floor, end) for mark in (". ", "\n", " "))
            if split > floor:
                end = split + (2 if content[split:split + 2] == ". " else 1)
        item = {key: entry.get(key) for key in FILTER_FIELDS if key in entry}
        for flag, present in presence_flags(entry).items():
            item.setdefault(flag, present)
        item.update({
            "passage_id": f"{entry['ID']}_p{len(result) + 1:04d}", "entry_id": entry["ID"],
            "nazwa": entry["nazwa"], "parent_id": entry.get("parent_id"), "strona": entry["strona"],
            "text": content[start:end], "start_offset": start, "end_offset": end,
        })
        result.append(item)
        if end == len(content):
            break
        start = max(start + 1, end - overlap)
    return result
