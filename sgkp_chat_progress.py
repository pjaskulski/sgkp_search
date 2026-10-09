"""Stream real preparation progress before the answer generator is ready."""
from contextvars import ContextVar, copy_context
from functools import wraps
import json
import queue
import threading

from flask import Response, copy_current_request_context, current_app, make_response, request
from sgkp_chat_log import record

_progress = ContextVar("sgkp_chat_progress", default=None)


def report_progress(phase):
    callback = _progress.get()
    if callback is not None:
        callback(phase)


def streamed_preparation(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if "text/event-stream" not in request.headers.get("Accept", ""):
            return function(*args, **kwargs)
        messages = queue.Queue()
        context = copy_context()

        @copy_current_request_context
        def prepare():
            token = _progress.set(lambda phase: messages.put(("progress", phase)))
            try:
                try:
                    response = make_response(function(*args, **kwargs))
                except Exception as exc:
                    response = make_response(current_app.handle_user_exception(exc))
                messages.put(("response", response))
            except Exception:
                messages.put(("error", None))
            finally:
                _progress.reset(token)

        def events():
            threading.Thread(target=lambda: context.run(prepare), daemon=True).start()
            while True:
                try:
                    kind, value = messages.get(timeout=10)
                except queue.Empty:
                    yield ": preparation in progress\n\n"
                    continue
                if kind == "progress":
                    yield "event: progress\ndata: " + json.dumps({"phase": value}) + "\n\n"
                elif kind == "response":
                    if value.status_code >= 400:
                        record("błąd przygotowania odpowiedzi", status="error", http=value.status_code)
                        data = value.get_json(silent=True) or {"error": "Usługa konwersacji jest niedostępna"}
                        yield "event: error\ndata: " + json.dumps(data, ensure_ascii=False) + "\n\n"
                    else:
                        try:
                            yield from value.response
                        finally:
                            value.close()
                    return
                else:
                    record("błąd przygotowania odpowiedzi", status="error")
                    yield 'event: error\ndata: {"error": "Usługa konwersacji jest niedostępna"}\n\n'
                    return
        return Response(events(), mimetype="text/event-stream")
    return wrapped
