""" tworzenie indeksu na podstawie danych w pliku json """
import os
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
OPENAI_ORG_ID = os.environ.get('OPENAI_ORG_ID')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

VOLUMES = ['01', '02', '03', '04', '05', '06', '07', '08',
           '09', '10', '11', '12', '13', '14', '15', '16']

VOLUMES = [ '02']

client = meilisearch.Client(MEILI_HOST, MEILI_API_KEY)

SCRIPT_MODE = "UPDATE" # CREATE or UPDATE

# -------------------------------- FUNCTIONS -----------------------------------
def setup_index_and_documents():
    """ utworzenie lub uzupełnianie indeksu Meilisearch """

    if SCRIPT_MODE == "CREATE":
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
        "{% for field in fields %} {% if field.is_searchable and field.value != nil %}{{ field.name }}: {{ field.value|truncatewords: 80 }} {% endif %} {% endfor %}"
    )

    stop_words_pl = stopwords.stopwords('pl')

    settings = {
        'searchableAttributes': ['nazwa', 'typ_punktu_osadniczego', 'typ', 'text', 'mlyny', 'przemyslowe', 'obiekty_sakralne', 'archeo'],
        'filterableAttributes': ['powiat', 'tom'],
        'stopWords': list(stop_words_pl),
        'localizedAttributes': [
            {'attributePatterns': ['*'], 'locales': ['pol']}
        ],
        'embedders': {
            "openai": {
                "source": "openAi",
                "model": "text-embedding-3-small",
                "apiKey": OPENAI_API_KEY,
                "documentTemplate": template
            }
        }
    }

    print("Aktualizacja ustawień indeksu...")
    task = index.update_settings(settings)
    client.wait_for_task(task.task_uid, timeout_in_ms=50000)


    for VOLUME in VOLUMES:
        input_path = Path('.') / 'scalone' / f'sgkp_{VOLUME}_scalone.json'

        print(f"Tom {VOLUME}: dodawanie dokumentów do indeksu...")
        with open(input_path, 'r', encoding='utf-8') as f:
            sgkp_data = json.load(f)

        max_timeout = 3600 *1000

        try:
            task = index.add_documents(sgkp_data)

            tmp = client.wait_for_task(task.task_uid, timeout_in_ms=max_timeout)
            if tmp.status == 'failed':
                print(tmp.error)

        except MeilisearchApiError as e:
            print(e.message)

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
