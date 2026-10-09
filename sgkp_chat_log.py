"""Request-local chat diagnostics, appended as one block after response completion."""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime
from functools import wraps
import fcntl
import json
import logging
import os
from pathlib import Path
import time
from uuid import uuid4

CHAT_LOG_PATH = Path(__file__).resolve().parent / "log" / "chat.log"
_current = ContextVar("sgkp_chat_debug", default=None)


def record(stage, seconds=None, **details):
    trace = _current.get()
    if trace is not None:
        if details.get("status") == "error":
            trace.status = "error"
        trace.events.append({"etap": stage, "czas_s": seconds,
                             "od_poczatku_s": round(time.monotonic() - trace.started, 3), **details})


def timed_stage(stage):
    """Measure a function, including consumption if it returns a stream iterator."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if _current.get() is None:
                return function(*args, **kwargs)
            stage_name = stage(*args, **kwargs) if callable(stage) else stage
            started = time.monotonic()
            try:
                result = function(*args, **kwargs)
            except BaseException as exc:
                record(stage_name, time.monotonic() - started, status=type(exc).__name__)
                raise
            if hasattr(result, "__next__"):
                def stream():
                    status = "ok"
                    try:
                        yield from result
                    except BaseException as exc:
                        status = type(exc).__name__
                        raise
                    finally:
                        record(stage_name, time.monotonic() - started, status=status)
                return stream()
            record(stage_name, time.monotonic() - started, status="ok")
            return result
        return wrapped
    return decorate


class ChatTrace:
    def __init__(self, body):
        self.started = time.monotonic()
        self.timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        self.identifier = uuid4().hex[:12]
        self.body = body if isinstance(body, dict) else {}
        self.events = []
        self.status = "ok"
        self.written = False

    def finish(self):
        if self.written:
            return
        self.written = True
        header = {"pytanie": self.body.get("question"), "filtry": self.body.get("filters", {}),
                  "weryfikacja_zadana": self.body.get("verify", True),
                  "poglebiona_analiza": self.body.get("deeper_analysis", False),
                  "jezyk": self.body.get("language", "pl"),
                  "liczba_tur_historii": len(self.body.get("history", []))
                  if isinstance(self.body.get("history", []), list) else None}
        lines = [f"=== CHAT {self.identifier} | {self.timestamp} ===",
                 json.dumps(header, ensure_ascii=False)]
        for event in self.events:
            event = dict(event)
            if event.get("czas_s") is not None:
                event["czas_s"] = round(event["czas_s"], 3)
            lines.append(json.dumps(event, ensure_ascii=False))
        lines.append(f"KONIEC | status={self.status} | czas_calkowity_s={time.monotonic() - self.started:.3f}")
        block = "\n".join(lines) + "\n\n"
        try:
            CHAT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Gunicorn workers append complete blocks under a process-shared file lock.
            with CHAT_LOG_PATH.open("a", encoding="utf-8") as output:
                fcntl.flock(output.fileno(), fcntl.LOCK_EX)
                output.write(block)
                output.flush()
                fcntl.flock(output.fileno(), fcntl.LOCK_UN)
        except OSError:
            logging.getLogger(__name__).exception("Nie udało się zapisać log/chat.log")


def traced_chat(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        from flask import make_response, request
        if os.getenv("CHAT_DEBUG", "false").strip().lower() not in {"true", "1", "yes", "on"}:
            return function(*args, **kwargs)
        trace = ChatTrace(request.get_json(silent=True))
        token = _current.set(trace)
        try:
            response = make_response(function(*args, **kwargs))
            if response.status_code >= 400:
                trace.status = f"http_{response.status_code}"
        except BaseException as exc:
            trace.status = type(exc).__name__
            trace.finish()
            raise
        finally:
            _current.reset(token)
        original = response.response

        def stream():
            iterator = iter(original)
            completed = False
            try:
                while True:
                    token = _current.set(trace)
                    try:
                        item = next(iterator)
                    except StopIteration:
                        completed = True
                        break
                    except BaseException as exc:
                        trace.status = type(exc).__name__
                        raise
                    finally:
                        _current.reset(token)
                    # Do not leave request-local state installed while the WSGI server sends a chunk.
                    yield item
            finally:
                if not completed and trace.status == "ok":
                    trace.status = "interrupted"
                token = _current.set(trace)
                try:
                    if hasattr(iterator, "close"):
                        iterator.close()
                finally:
                    _current.reset(token)
                    trace.finish()
        response.response = stream()
        response.call_on_close(trace.finish)
        return response
    return wrapped
