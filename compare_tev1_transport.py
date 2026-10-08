"""Compare SDK and requests with exactly the SDK's body and in-memory headers."""
import argparse
import csv
import json
import logging
import math
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx2
import requests
from typesafe_sdk import Noul, TypeSafeClient
from typesafe_sdk._core.retry import RetryPolicy

from sgkp_relevance import INSTRUCTIONS, RelevanceDiagnostic


def capture_request(request, directory, captured):
    """Persist body only. Authorization stays in memory for the paired request."""
    body = request.content
    json.loads(body)  # Require a JSON request, not a streaming or binary body.
    captured.update(url=str(request.url), body=body, headers=dict(request.headers))
    (directory / 'tev1_request.json').write_bytes(body)


def direct_call(captured, timeout):
    # Let requests calculate transport headers while preserving SDK headers.
    headers = {key: value for key, value in captured['headers'].items()
               if key.lower() not in {'host', 'content-length', 'transfer-encoding', 'connection'}}
    with requests.post(captured['url'], data=captured['body'], headers=headers,
                       timeout=timeout) as response:
        result = {'http_status': response.status_code}
        if response.ok:
            data = response.json()
            result['score'] = float(data['answers']['relevant']['noul'])
            result['status'] = 'ok'
        else:
            result['status'] = 'http_error'
        return result


def sdk_call(state, url, key, model, timeout, directory, captured, prepare_only=False):
    def offline(request):
        capture_request(request, directory, captured)
        raise RuntimeError('Request captured without network access')

    with httpx2.Client(timeout=timeout,
            transport=httpx2.MockTransport(offline) if prepare_only else None,
            event_hooks={'request': [lambda request: capture_request(request, directory, captured)]}) as http:
        with TypeSafeClient(base_url=url, api_key=key, model=model, timeout=timeout,
                            retry=RetryPolicy(max_retries=0), http_client=http) as client:
            answer = client.system_one(state=state, questions={'relevant': Noul(
                instructions=INSTRUCTIONS, criteria={
                    'true': 'The passage or metadata substantively addresses the query.',
                    'false': 'The passage and metadata do not substantively address the query.'})})
    return {'status': 'ok', 'score': float(answer.nouls['relevant'].noul)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, help='CSV export from search diagnostics')
    parser.add_argument('--row', type=int, default=1, help='Data row in CSV, counted from 1')
    parser.add_argument('--count', type=int, default=10, help='Number of distinct nonempty fragments, default 10')
    parser.add_argument('--text-file', type=Path)
    parser.add_argument('--query', default='młyny')
    parser.add_argument('--name', default='Przykład testowy')
    parser.add_argument('--url')
    parser.add_argument('--model', default='tev1:4b')
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--repeats', type=int, default=2)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    if args.csv and args.text_file:
        parser.error('Choose --csv or --text-file')
    if args.row < 1 or args.count < 1 or args.repeats < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('Invalid row, repeats or timeout')
    service = RelevanceDiagnostic()
    url = (args.url or service.url).rstrip('/')
    if urlsplit(url).username or urlsplit(url).password or urlsplit(url).query:
        parser.error('URL must not contain credentials or query parameters')
    service.url = url
    # Use the same key selection as application code; never print it.
    import os
    key = os.getenv('SEARCH_RELEVANCE_API_KEY') or (
        'ollama' if urlsplit(url).hostname in {'localhost', '127.0.0.1', '::1'} else os.getenv('AI_TEST_KEY'))
    if not key:
        parser.error('Missing AI_TEST_KEY or SEARCH_RELEVANCE_API_KEY')
    query, name = args.query, args.name
    evidence = args.text_file.read_text(encoding='utf-8') if args.text_file else 'We wsi działał młyn wodny.'
    cases = [(1, query, name, evidence)]
    if args.csv:
        with args.csv.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        if args.row > len(rows):
            parser.error('CSV row is out of range')
        cases, seen = [], set()
        for row_number, row in enumerate(rows[args.row - 1:], args.row):
            text = row['badany fragment hasła'][:2500]
            if not text.strip() or text in seen:
                continue
            seen.add(text)
            cases.append((row_number, row['pytanie użytkownika'], row['nazwa hasła'], text))
            if len(cases) >= args.count:
                break
    if not cases or not cases[0][3].strip():
        parser.error('No nonempty evidence')
    directory = args.output_dir or Path('log') / f'tev1_transport_{datetime.now():%Y%m%d_%H%M%S_%f}'
    directory.mkdir(parents=True, exist_ok=False)
    results = []
    # Avoid SDK/network debug logging of headers, including on exceptions.
    for logger_name in ('typesafe_sdk', 'httpx2', 'httpcore'):
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    print(f'Różne fragmenty: {len(cases)}, par na fragment: {args.repeats}', flush=True)
    for case_number, (row_number, query, name, evidence) in enumerate(cases, 1):
        case_directory = directory / f'case_{case_number:03d}'
        case_directory.mkdir()
        state = {'query': query, 'entry_name': name, 'passage': evidence[:2500], 'metadata': '{}'}
        captured = {}
        # Prepare through a mock transport: no model call, so HTTP can be first
        # while still using the SDK's exact request serialization.
        try:
            sdk_call(state, url, key, args.model, args.timeout, case_directory, captured, prepare_only=True)
        except Exception:
            if not captured:
                raise RuntimeError('Unable to prepare SDK request') from None
        for number in range(1, args.repeats + 1):
            methods = ['sdk', 'requests'] if (case_number + number) % 2 == 0 else ['requests', 'sdk']
            for position, method in enumerate(methods, 1):
                started = time.monotonic()
                try:
                    result = (sdk_call(state, url, key, args.model, args.timeout, case_directory, captured)
                              if method == 'sdk' else direct_call(captured, args.timeout))
                except Exception as exc:
                    result = {'status': type(exc).__name__}
                result.update(method=method, run=number, case=case_number, csv_row=row_number,
                              name=name, position=position, text_chars=len(state['passage']),
                              seconds=time.monotonic() - started)
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
                (directory / 'timings.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Pliki: {directory}; request JSON nie zawiera nagłówków ani klucza.')
    print('Kolejność metod jest naprzemienna. Powtórzenia mogą korzystać z cache serwera.')
    return 0 if all(result['status'] == 'ok' for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
