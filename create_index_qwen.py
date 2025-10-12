""" tworzenie indeksu na podstawie danych w pliku json """
import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import meilisearch
from meilisearch.errors import MeilisearchApiError
import stopwordsiso as stopwords


MEILI_HOST = "http://localhost:7700"
INDEX_NAME = "sgkp"
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)
MEILI_API_KEY = os.environ.get('MEILI_API_KEY')

client = meilisearch.Client(MEILI_HOST, MEILI_API_KEY)


# -------------------------------- FUNCTIONS -----------------------------------
def setup_index_and_documents():
    """ utworzenie indeksu Meilisearch """

    print("Konfiguracja indeksu...")
    try:
        task = client.delete_index(INDEX_NAME)
        client.wait_for_task(task.task_uid, timeout_in_ms=50000)
        print(f"Indeks '{INDEX_NAME}' został usunięty.")
    except MeilisearchApiError as e:
        if e.code == 'index_not_found':
            print(f"Indeks '{INDEX_NAME}' nie istniał, tworzę nowy.")
        else:
            raise e

    client.create_index(uid=INDEX_NAME, options={'primaryKey': 'ID'})
    index = client.index(INDEX_NAME)

    template = (
        "{% for field in fields %} {% if field.is_searchable and field.value != nil and field.name != 'text' %}{{ field.name }}: {{ field.value }}{% elsif field.name == 'text' %}{{ field.value|truncatewords: 80}}{% endif %} {% endfor %}"
    )

    stop_words_pl = stopwords.stopwords('pl')

    settings = {
        'searchableAttributes': ['text', 'mlyny', 'przemyslowe', 'obiekty_sakralne', 'archeo', 'typ_punktu_osadniczego', 'typ', 'nazwa'],
        'filterableAttributes': ['powiat', 'tom'],
        'sortableAttributes': ['nazwa', 'powiat', 'tom'],
        'rankingRules': [
            'words',
            'typo',
            'proximity',
            'attribute',
            'sort',
            'exactness'
        ],
        'stopWords': list(stop_words_pl),
        'localizedAttributes': [
            {'attributePatterns': ['*'], 'locales': ['pol']}
        ],
        'embedders': {
            "qwen3": {
                "source": "ollama",
                "model": "qwen3-embedding:0.6b",
                "dimensions": 1024,
                "url": "http://localhost:11434/api/embed",
                "documentTemplate": template,
                "documentTemplateMaxBytes": 800,
            }
        }
    }

    print("Aktualizacja ustawień indeksu...")
    task = index.update_settings(settings)
    client.wait_for_task(task.task_uid, timeout_in_ms=50000)

    print("Dodawanie dokumentów do indeksu...")
    with open('sgkp_scalone.json', 'r', encoding='utf-8') as f:
        sgkp_data = json.load(f)

    #task = index.add_documents(sgkp_data)
    for entry in sgkp_data:
        nazwa = entry.get("nazwa", None)
        tom = entry.get("tom", None)
        entry_id = entry.get("ID", None)
        print(f'Dodawanie do indeksu: {nazwa}, tom: {tom}, ID: {entry_id}...')
        task = index.add_documents(entry)
        client.wait_for_task(task.task_uid, timeout_in_ms=50000)

    print("✅ Konfiguracja indeksu Meilisearch zakończona pomyślnie.")


# ------------------------------- MAIN -----------------------------------------
if __name__ == '__main__':
    # pomiar czasu wykonania
    start_time = time.time()

    setup_index_and_documents()

    # czas wykonania programu
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Czas wykonania programu: {time.strftime("%H:%M:%S", time.gmtime(elapsed_time))} s.')
