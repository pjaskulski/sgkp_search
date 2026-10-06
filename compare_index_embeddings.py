"""Read stored passage vectors and compare direct local/Jina recomputation."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

from compare_jina_embeddings import compare_vectors, request_vector
from sgkp_services import Embeddings, Meili


def stored_vector(document):
    value = document['_vectors']['jina']
    if isinstance(value, dict):
        value = value['embeddings']
    if value and isinstance(value[0], list):
        if len(value) != 1:
            raise ValueError('Expected a single passage vector')
        value = value[0]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids', nargs='+', default=[
        '01-06784_p0001', '07-07363-002_p0001', '01-06332_p0001', '01-06332_p0003'])
    parser.add_argument('--local-task', default=None)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    service = Embeddings()
    meili = Meili(write=True)
    manifest = json.loads(Path('runtime/active_manifest.json').read_text())
    index = manifest['passages_index']
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'index': index,
              'local_task': args.local_task, 'jina_task': service.jina_task,
              'samples': []}
    with requests.Session() as session:
        for passage_id in args.ids:
            doc = meili.request('GET', f'/indexes/{quote(index, safe="")}/documents/'
                                f'{quote(passage_id, safe="")}?retrieveVectors=true')
            vector = stored_vector(doc)
            text = doc['text']
            sample = {'id': passage_id, 'name': doc.get('nazwa'), 'text': text,
                      'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                      'stored_vector': vector, 'runs': {}, 'comparisons': {}}
            print(f'{passage_id} {doc.get("nazwa")} ({len(text)} znaków)', flush=True)
            local_payload = {'model': service.model, 'input': [text]}
            if args.local_task:
                local_payload['task'] = args.local_task
            for provider, url, key, payload in (
                ('local', service.url, service.key, local_payload),
                ('jina', service.jina_url, service.jina_key,
                 {'model': service.jina_model, 'task': service.jina_task, 'input': [text]}),
            ):
                run = request_vector(session, url, key, payload, args.timeout)
                sample['runs'][provider] = run
                if run['status'] == 'ok':
                    comparison = compare_vectors(vector, run['vector'])
                    sample['comparisons']['stored_vs_' + provider] = comparison
                    print(f'  indeks/{provider}: cos={comparison.get("cosine_similarity")} '
                          f'L2={comparison.get("l2_distance")} ({run["seconds"]:.2f} s)', flush=True)
                else:
                    print(f'  {provider}: {run["error"]}', flush=True)
            runs = sample['runs']
            if all(run['status'] == 'ok' for run in runs.values()):
                sample['comparisons']['local_vs_jina'] = compare_vectors(
                    runs['local']['vector'], runs['jina']['vector'])
            report['samples'].append(sample)
    output = args.output or Path('runtime') / ('index_embedding_comparison_' +
        datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'Raport: {output}', flush=True)


if __name__ == '__main__':
    main()
