"""Service clients, configuration, and source lookups for SGKP."""

from __future__ import annotations

import json
import os
import re
import shlex
import sqlite3
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import requests

from sgkp_core import FILTER_FIELDS, read_volume


ROOT = Path(__file__).resolve().parent
ROMAN = {f"{i:02d}": v for i, v in enumerate((
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV_cz.1", "XV_cz.2"
), 1)}


def load_env(path: Path = ROOT / ".env") -> None:
    """Read simple .env assignments without exposing or overriding secrets."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            parts = shlex.split(line, comments=True)
        except ValueError:
            continue
        if parts and parts[0] == "export":
            parts = parts[1:]
        if len(parts) == 1 and "=" in parts[0]:
            name, value = parts[0].split("=", 1)
            if name.isidentifier():
                os.environ.setdefault(name, value)


load_env()


class ServiceError(RuntimeError):
    def __init__(self, service: str, status: int | None = None, message: str = ""):
        super().__init__(f"{service}: {message or status or 'unavailable'}")
        self.service = service
        self.status = status
        self.message = message


class Meili:
    def __init__(self, write: bool = False):
        self.base = os.getenv("MEILI_HOST", "http://localhost:7700").rstrip("/")
        admin_key = os.getenv("MEILI_API_KEY") or os.getenv("API_MEILISEARCH_ADMIN")
        search_key = os.getenv("MEILI_READ_API_KEY") or os.getenv("API_MEILISEARCH_SEARCH")
        self.key = admin_key if write else (search_key or admin_key)
        self.session = requests.Session()

    def request(self, method: str, path: str, *, body=None, timeout: int = 30):
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        try:
            response = self.session.request(method, self.base + path, json=body, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            raise ServiceError("meilisearch", message=type(exc).__name__) from exc
        if response.status_code >= 400:
            try:
                code = response.json().get("code", "request_failed")
            except ValueError:
                code = "request_failed"
            raise ServiceError("meilisearch", response.status_code, code)
        return response.json()

    def health(self):
        return self.request("GET", "/health")

    def version(self):
        return self.request("GET", "/version")

    def search(self, index: str, payload: dict):
        return self.request("POST", f"/indexes/{quote(index, safe='')}/search", body=payload, timeout=40)

    def wait_task(self, task: dict, timeout: int = 600):
        uid = task.get("taskUid", task.get("uid"))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.request("GET", f"/tasks/{uid}")
            if state["status"] == "succeeded":
                return state
            if state["status"] in ("failed", "canceled"):
                raise ServiceError("meilisearch", message=f"task {uid}: {state.get('error', {}).get('code', state['status'])}")
            time.sleep(0.2)
        raise ServiceError("meilisearch", message=f"task {uid}: timeout")

    def create_index(self, uid: str, primary_key: str):
        task = self.request("POST", "/indexes", body={"uid": uid, "primaryKey": primary_key})
        self.wait_task(task)

    def settings(self, uid: str, settings: dict):
        task = self.request("PATCH", f"/indexes/{quote(uid, safe='')}/settings", body=settings)
        self.wait_task(task)

    def add_documents(self, uid: str, batch: list[dict], timeout: int = 1800):
        task = self.request("POST", f"/indexes/{quote(uid, safe='')}/documents", body=batch, timeout=120)
        self.wait_task(task, timeout=timeout)

    def stats(self, uid: str):
        return self.request("GET", f"/indexes/{quote(uid, safe='')}/stats")


class Embeddings:
    def __init__(self):
        self.url = os.getenv("EMBEDDING_ENDPOINT", "https://ai-test.ihpan.edu.pl/engines/jina-embeddings-v3/embeddings")
        self.model = os.getenv("EMBEDDING_MODEL", "jina-embeddings-v3")
        self.key = os.getenv("AI_TEST_KEY")
        self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
        self.session = requests.Session()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.key:
            raise ServiceError("embedding", message="missing AI_TEST_KEY")
        try:
            response = self.session.post(self.url, json={"model": self.model, "input": texts},
                headers={"Authorization": f"Bearer {self.key}"}, timeout=(10, 120))
        except requests.RequestException as exc:
            raise ServiceError("embedding", message=type(exc).__name__) from exc
        if response.status_code >= 400:
            raise ServiceError("embedding", response.status_code, "request_failed")
        try:
            items = sorted(response.json()["data"], key=lambda item: item.get("index", 0))
            vectors = [item["embedding"] for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise ServiceError("embedding", message="invalid_response") from exc
        if len(vectors) != len(texts) or any(len(vector) != self.dimensions for vector in vectors):
            raise ServiceError("embedding", message="invalid_vector_count_or_dimensions")
        return vectors


class Chat:
    def __init__(self):
        self.url = os.getenv("CHAT_ENDPOINT", "https://ai-test.ihpan.edu.pl/v1/chat/completions")
        self.model = os.getenv("CHAT_MODEL", "qwen3.8-flash-next-fp8")
        self.key = os.getenv("AI_TEST_KEY")
        self.timeout = (10, float(os.getenv("CHAT_READ_TIMEOUT", "45")))
        self.max_output_tokens = int(os.getenv("CHAT_MAX_OUTPUT_TOKENS", "3000"))

    def answer(self, messages: list[dict], max_tokens: int | None = None) -> str:
        if not self.key:
            raise ServiceError("chat", message="missing AI_TEST_KEY")
        max_tokens = max_tokens if max_tokens is not None else self.max_output_tokens
        try:
            response = requests.post(self.url, json={"model": self.model, "messages": messages, "max_tokens": max_tokens,
                "temperature": 0.1, "stream": False, "chat_template_kwargs": {"enable_thinking": False}},
                headers={"Authorization": f"Bearer {self.key}"}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ServiceError("chat", message=type(exc).__name__) from exc
        if response.status_code >= 400:
            raise ServiceError("chat", response.status_code, "request_failed")
        try:
            choice = response.json()["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ServiceError("chat", message="invalid_response") from exc
        if choice.get("finish_reason") == "length":
            raise ServiceError("chat", message="output_limit")
        if not isinstance(content, str) or not content.strip():
            raise ServiceError("chat", message="empty_answer")
        return content

    def stream(self, messages: list[dict], max_tokens: int | None = None):
        if not self.key:
            raise ServiceError("chat", message="missing AI_TEST_KEY")
        max_tokens = max_tokens if max_tokens is not None else self.max_output_tokens
        try:
            response = requests.post(self.url, json={"model": self.model, "messages": messages,
                "max_tokens": max_tokens, "temperature": 0.1, "stream": True,
                "chat_template_kwargs": {"enable_thinking": False}},
                headers={"Authorization": f"Bearer {self.key}"}, timeout=self.timeout, stream=True)
        except requests.RequestException as exc:
            raise ServiceError("chat", message=type(exc).__name__) from exc
        if response.status_code >= 400:
            response.close()
            raise ServiceError("chat", response.status_code, "request_failed")

        def chunks():
            completed = hit_limit = False
            try:
                with response:
                    for line in response.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            completed = True
                            break
                        try:
                            choice = json.loads(data)["choices"][0]
                            part = choice["delta"].get("content")
                        except (ValueError, KeyError, IndexError, TypeError) as exc:
                            raise ServiceError("chat", message="invalid_stream") from exc
                        if choice.get("finish_reason") == "length":
                            hit_limit = True
                        if part:
                            yield part
            except requests.RequestException as exc:
                raise ServiceError("chat", message=type(exc).__name__) from exc
            if not completed:
                raise ServiceError("chat", message="incomplete_stream")
            if hit_limit:
                raise ServiceError("chat", message="output_limit")

        return chunks()


class OpenAIChat:
    """External fallback for grounded answers when the local chat service fails."""

    def __init__(self):
        self.url = "https://api.openai.com/v1/responses"
        self.model = os.getenv("OPENAI_CHAT_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"
        configured_effort = os.getenv("OPENAI_REASONING_EFFORT")
        self.reasoning_effort = configured_effort.strip() if configured_effort is not None else (
            "low" if self.model.startswith("gpt-6-") else "")
        self.key = os.getenv("OPENAI_API_KEY")
        self.max_output_tokens = int(os.getenv("OPENAI_CHAT_MAX_OUTPUT_TOKENS", "3000"))

    def request(self, messages: list[dict], max_tokens: int, *, stream: bool):
        if not self.key:
            raise ServiceError("openai", message="missing OPENAI_API_KEY")
        payload = {"model": self.model, "input": messages, "max_output_tokens": max_tokens,
            "store": False, "stream": stream}
        if self.reasoning_effort:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        try:
            response = requests.post(self.url, json=payload,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                timeout=(10, 120), stream=stream)
        except requests.RequestException as exc:
            raise ServiceError("openai", message=type(exc).__name__) from exc
        if response.status_code >= 400:
            try:
                error_code = response.json().get("error", {}).get("code")
            except (ValueError, TypeError, AttributeError):
                error_code = None
            response.close()
            raise ServiceError("openai", response.status_code, error_code or "request_failed")
        return response

    def answer(self, messages: list[dict], max_tokens: int | None = None) -> str:
        max_tokens = max_tokens if max_tokens is not None else self.max_output_tokens
        with self.request(messages, max_tokens, stream=False) as response:
            try:
                data = response.json()
                if data.get("status") != "completed":
                    raise ValueError("incomplete response")
                text = "".join(part.get("text", "") for item in data["output"]
                    if item.get("type") == "message" for part in item.get("content", [])
                    if part.get("type") == "output_text")
            except (KeyError, TypeError, ValueError) as exc:
                raise ServiceError("openai", message="invalid_response") from exc
        if not text.strip():
            raise ServiceError("openai", message="empty_answer")
        return text

    def stream(self, messages: list[dict], max_tokens: int | None = None):
        max_tokens = max_tokens if max_tokens is not None else self.max_output_tokens
        response = self.request(messages, max_tokens, stream=True)

        def chunks():
            completed = False
            try:
                with response:
                    for line in response.iter_lines(decode_unicode=True):
                        if isinstance(line, bytes):
                            line = line.decode("utf-8")
                        if not line or not line.startswith("data: "):
                            continue
                        if line[6:] == "[DONE]":
                            break
                        try:
                            event = json.loads(line[6:])
                        except ValueError as exc:
                            raise ServiceError("openai", message="invalid_stream") from exc
                        kind = event.get("type")
                        if kind == "response.output_text.delta":
                            part = event.get("delta")
                            if isinstance(part, str) and part:
                                yield part
                        elif kind == "response.completed":
                            completed = event.get("response", {}).get("status") == "completed"
                        elif kind in ("response.failed", "response.incomplete", "error"):
                            raise ServiceError("openai", message="response_failed")
            except requests.RequestException as exc:
                raise ServiceError("openai", message=type(exc).__name__) from exc
            if not completed:
                raise ServiceError("openai", message="incomplete_stream")

        return chunks()


def scan_url(tom: str, strona: int) -> str | None:
    if tom not in ROMAN or not isinstance(strona, int) or not 1 <= strona <= 1000:
        return None
    return f"https://dir.icm.edu.pl/Slownik_geograficzny/Tom_{ROMAN[tom]}/{strona}"


def filter_expression(values: dict) -> list[str]:
    expressions = []
    for key, raw in values.items():
        if key not in FILTER_FIELDS or raw in (None, ""):
            continue
        if key in ("jest_miejscowoscia", "królestwo_polskie"):
            if raw not in ("true", "false", True, False):
                raise ValueError(f"Nieprawidłowa wartość filtra {key}")
            value = str(raw).lower()
        else:
            if not isinstance(raw, str) or len(raw) > 120 or any(ord(c) < 32 for c in raw):
                raise ValueError(f"Nieprawidłowa wartość filtra {key}")
            value = json.dumps(raw, ensure_ascii=False)
        expressions.append(f"{key} = {value}")
    return expressions


@lru_cache(maxsize=2)
def cached_volume(path: str):
    return read_volume(Path(path))


def source_detail(input_dir: Path, lookup_db: Path, identifier: str) -> dict | None:
    with sqlite3.connect(lookup_db) as db:
        row = db.execute("SELECT source_file, record_index, element_index FROM entries WHERE id = ?", (identifier,)).fetchone()
    if row is None:
        return None
    filename, record_index, element_index = row
    if not re.fullmatch(r"sgkp_\d\d\.json", filename):
        raise ValueError("Nieprawidłowa ścieżka źródła")
    parent = cached_volume(str(input_dir / filename))[record_index]
    entry = parent if element_index is None else parent["elementy"][element_index]
    if entry.get("ID") != identifier:
        raise ValueError("Manifest nie odpowiada plikom źródłowym")
    return {"entry": entry, "parent": parent if element_index is not None else None,
        "tom": parent["tom"], "strona": parent["strona"]}
