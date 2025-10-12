""" app (flask) - sgkp search """
import os
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
import meilisearch
from meilisearch.errors import MeilisearchApiError
from dotenv import load_dotenv



MEILI_HOST = "http://localhost:7700"
INDEX_NAME = "sgkp06"
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)
MEILI_API_KEY = os.environ.get('MEILI_API_KEY')

client = meilisearch.Client(MEILI_HOST, MEILI_API_KEY)
app = Flask(__name__, static_folder='static')

# ------------------------------- FUNCTIONS ------------------------------------
def get_detailed_instruct(task_description: str, query: str) -> str:
    """ przygotowanie instrukcji dla modelu Qwen3 """
    return f'Instruct: {task_description}\nQuery:{query}'

# ------------------------------ API ENDPOINTS ---------------------------------
@app.route("/")
def serve_index():
    """funkcja serwuje główny plik HTML"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/search")
def search():
    """obsługa zapytań wyszukiwania z frontendu"""
    query = request.args.get('q')
    ratio_str = request.args.get('ratio', '0')

    if not query:
        return jsonify({"error": "Parametr 'q' jest wymagany"}), 400

    try:
        ratio_percent = int(ratio_str)
        semantic_ratio = ratio_percent / 100.0
    except (ValueError, TypeError):
        semantic_ratio = 0.0

    search_params = {
            "locales": ["pol"],
            "attributesToCrop": ["text:75"],  # przycięcie pola 'text' do 75 słów
            'attributesToHighlight': ['text'], # podświetlanie pasujących terminów zapytania w określonych atrybutach
            'showRankingScore': True,
            #'sort': ['nazwa:desc']
        }

    # wyszukiwanie hybrydowe jeżeli parametr semantic_ratio > 0
    if semantic_ratio > 0:
        search_params['hybrid'] = {
            "semanticRatio": semantic_ratio,
            "embedder": "qwen3"
        }

        print(f"⚡️ Wykonuję wyszukiwanie hybrydowe z ratio: {semantic_ratio}")
    else:
        print("🔍 Wykonuję wyszukiwanie pełnotekstowe (keyword).")

    index = client.index(INDEX_NAME)
    task = "Given a search query, retrieve relevant passages that answer the query"
    try:
        if semantic_ratio > 0:
            query = get_detailed_instruct(task, query)

        search_results = index.search(query, search_params)
        return jsonify(search_results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/entry/<entry_id>")
def get_entry(entry_id):
    """ pobiera i zwraca dane jednego dokumentu na podstawie jego ID."""
    try:
        index = client.index(INDEX_NAME)
        entry = index.get_document(entry_id)
        return jsonify(dict(entry))
    except MeilisearchApiError as e:
        # jeżeli dokument o danym id nie istnieje, Meilisearch zwróci błąd
        if e.code == 'document_not_found':
            return jsonify({"error": "Nie znaleziono hasła o podanym identyfikatorze."}), 404
        # inne możliwe błędy API
        return jsonify({"error": str(e)}), 500


# -------------------------------- MAIN ----------------------------------------
if __name__ == '__main__':

    app.run(port=8080, debug=True)
