"""Evaluate tev1 directly on labelled XLSX rows; export incremental CSV results."""
import argparse
import csv
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path

import openpyxl

from sgkp_relevance import RelevanceDiagnostic

HEADERS = ['szukane pojęcie, temat, wyrażenie', 'Hasło SGKP',
           'Treść hasła lub fragment', 'Ocena człowieka']
EXTRA = ['Ocena modelu', 'Decyzja modelu', 'Zgodność z człowiekiem',
         'Status', 'Czas wywołania (s)', 'Model', 'Wiersz źródłowy']


def read_cases(path, sheet=None):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet] if sheet else workbook.active
        # The supplied file declares 1,048,576 rows despite having 208 cases.
        worksheet.reset_dimensions()
        rows = worksheet.iter_rows(values_only=True)
        header = next(rows)
        names = [str(value).strip() if value is not None else '' for value in header]
        columns = [names.index(name) for name in HEADERS]
        for number, row in enumerate(rows, 2):
            values = [row[index] if index < len(row) else None for index in columns]
            if not any(value is not None and str(value).strip() for value in values):
                continue
            yield number, values
    finally:
        workbook.close()


def evaluate_case(service, values, threshold, timeout, backend='tev1'):
    query, name, evidence, human = values
    if not isinstance(query, str) or not query.strip() or not isinstance(evidence, str) or not evidence.strip():
        return ['', '', '', 'niekompletne dane', '', service.model]
    # No truncation, retrieval, translation, cache or human label in the prompt.
    state = {'query': query, 'entry_name': name or '', 'passage': evidence,
             'metadata': json.dumps({}, ensure_ascii=False)}
    started = time.monotonic()
    try:
        scorer = {'basal': service._score_basal, 'tev1': service._score_tev1,
                  'openrouter': service._score_openrouter}[backend]
        score = scorer(state, timeout)
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('invalid_score')
        decision = 'TAK' if score >= threshold else 'NIE'
        label = str(human or '').strip().upper()
        agreement = ('TAK' if decision == label else 'NIE') if label in {'TAK', 'NIE'} else ''
        return [score, decision, agreement, 'ok', time.monotonic() - started, service.model]
    except Exception as exc:
        # Error class only: avoid logging credentials from transport exceptions.
        return ['', '', '', type(exc).__name__, time.monotonic() - started, service.model]


def main(backend='tev1', default_model='tev1:4b', default_url=None):
    parser = argparse.ArgumentParser(description=f'Evaluate {backend} on labelled XLSX rows and export CSV.')
    parser.add_argument('--input', type=Path, default=Path('modele_decyzyjne_test.xlsx'))
    parser.add_argument('--sheet')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--model', default=default_model,
                        help='For basal: report label; model is loaded by basal-serve')
    parser.add_argument('--url', default=default_url)
    parser.add_argument('--threshold', type=float, default=0.5)
    parser.add_argument('--timeout', type=float, default=120 if backend == 'tev1' else 30)
    parser.add_argument('--limit', type=int, help='Only the first N nonempty cases')
    args = parser.parse_args()
    if not math.isfinite(args.threshold) or not 0 <= args.threshold <= 1 or not math.isfinite(args.timeout) or args.timeout <= 0 or (args.limit is not None and args.limit < 1):
        parser.error('Invalid threshold, timeout or limit')
    output = args.output or Path('log') / f'{backend}_test_{datetime.now():%Y%m%d_%H%M%S_%f}.csv'
    if output.suffix.lower() != '.csv':
        parser.error('Output must have .csv extension')
    if output.exists():
        parser.error('Output already exists; choose a new file')
    service = RelevanceDiagnostic()
    service.model, service.backend = args.model, backend
    service.url = args.url or os.getenv('SEARCH_RELEVANCE_URL', 'https://ai-test.ihpan.edu.pl')
    cases = list(read_cases(args.input, args.sheet))
    if args.limit:
        cases = cases[:args.limit]
    output.parent.mkdir(parents=True, exist_ok=True)
    successful = matching = compared = 0
    print(f'Próby: {len(cases)}, model: {args.model}, próg: {args.threshold}', flush=True)
    with output.open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS + EXTRA)
        for index, (row, values) in enumerate(cases, 1):
            result = evaluate_case(service, values, args.threshold, args.timeout, backend)
            writer.writerow(values + result + [row])
            stream.flush()
            successful += result[3] == 'ok'
            compared += result[2] in {'TAK', 'NIE'}
            matching += result[2] == 'TAK'
            print(f'{index}/{len(cases)}: wiersz {row}, status={result[3]}, '
                  f'ocena={result[0]}, decyzja={result[1]}', flush=True)
    print(f'Raport: {output}; poprawne wywołania: {successful}/{len(cases)}')
    if compared:
        print(f'Zgodność z człowiekiem: {matching}/{compared} ({matching / compared:.1%}); próg={args.threshold}')
    return 0 if successful == len(cases) else 1


if __name__ == '__main__':
    raise SystemExit(main())
