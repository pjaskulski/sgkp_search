import os
from pathlib import Path
from dotenv import load_dotenv
import meilisearch

# Konfiguracja (taka sama jak w app.py)
MEILI_HOST = "http://localhost:7700"
INDEX_NAME = "sgkp"
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)
MEILI_API_KEY = os.environ.get('MEILI_API_KEY')

client = meilisearch.Client(MEILI_HOST, MEILI_API_KEY)
index = client.index(INDEX_NAME)

# Pobranie obecnych ustawień, aby nic nie zepsuć
current_settings = index.get_settings()

# Aktualizacja limitu wyników
pagination_settings = {
    'pagination': {
        'maxTotalHits': 10000 # Ustawienie np. na 10 tysięcy
    }
}

print("Aktualizuję limit maxTotalHits...")
task = index.update_settings(pagination_settings)
print(f"Zlecono zadanie aktualizacji: {task.task_uid}")

# Oczekiwanie na zakończenie
client.wait_for_task(task.task_uid)
print("Gotowe! Limit został zwiększony.")

