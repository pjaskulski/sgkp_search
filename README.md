# Wyszukiwarka SGKP

Aplikacja Flask / Meilisearch. Służy do wyszukiwania pełnotekstowego, semantycznego i konwersacyjnego w Słowniku Geograficznym Królestwa Polskiego.
Przygotowana z udziałem Codex (gpt-6-sol).

## Uruchomienie

Wymagane: Python 3.11+, Meilisearch 1.54, katalog `json/` z 16 tomami SGKP zapisanymi w formacie JSON.
Model do konwersacji: `qwen3.8-flash-next-gguf`
Model embeddings: `jina-embeddings-v3`

Import tekstowy:

```bash
venv/bin/python -m sgkp_search.ingest --suffix test_tekst
```

Import z embeddingami Jina (1024 wymiary):

```bash
venv/bin/python -m sgkp_search.ingest --suffix test_jina --with-vectors
```

Uruchomienie aplikacji:

```bash
venv/bin/python app.py
```

## Opis 

Interfejs ma dwie zakładki: **Wyszukiwanie** z wynikami i **Konwersacja** z odpowiedziami opartymi na cytowanych hasłach. Opis aplikacji i wskazówki znajdują się w oknie **Pomoc** w nagłówku. W obu widokach dostępny jest ten sam zestaw filtrów. Po wybraniu „Tylko miejscowości” odblokowują się pola: „Tylko Królestwo Polskie”, typ miejscowości, gubernia i gmina. Gminę wybiera się z listy po wpisaniu fragmentu nazwy. 
