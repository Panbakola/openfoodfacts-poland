# Open Food Facts – Polska Baza Produktów

Repozytorium zawierające skrypt przetwarzający dane Open Food Facts oraz wygenerowaną bazę produktów sprzedawanych w Polsce, przeznaczoną dla aplikacji na Androida.

## Struktura plików

| Ścieżka | Opis |
|---------|------|
| `scripts/build_db.py` | Skrypt przetwarzający dane Open Food Facts do bazy SQLite |
| `dist/poland_products.db.zip` | Skompresowana baza SQLite (trafia do repozytorium) |
| `dist/version.json` | Metadane: data wygenerowania i liczba rekordów |
| `.github/workflows/update_database.yml` | Automatyzacja GitHub Actions (aktualizacja co tydzień) |
| `requirements.txt` | Zależności Python |
| `.gitignore` | Reguły ignorowania plików przez Git |

## Uruchomienie lokalne (testy)

### Wymagania

- Python 3.9+
- Biblioteka `duckdb`

### Instalacja zależności

```bash
pip install -r requirements.txt
```

### Uruchomienie skryptu

```bash
python scripts/build_db.py
```

Skrypt wykonuje następujące kroki:

1. Pobiera dane Open Food Facts przez publiczne API Hugging Face Datasets Server (paginacja, 100 rekordów na stronę) – bez ładowania wielogigabajtowego pliku do RAM.
2. Filtruje produkty sprzedawane w Polsce (`'en:poland'` w `countries_tags`).
3. Tworzy bazę SQLite `dist/poland_products.db` z kolumnami:
   - `code` (TEXT, PRIMARY KEY) – kod EAN,
   - `product_name` (TEXT) – nazwa produktu (priorytet: `product_name_pl`, fallback: `product_name`),
   - `brands` (TEXT) – marka/producent (pusty ciąg jeśli brak).
4. Tworzy indeks na kolumnie `code` dla szybkiego wyszukiwania.
5. Kompresuje bazę do `dist/poland_products.db.zip` (ZIP_DEFLATED).
6. Generuje `dist/version.json` z datą wygenerowania (ISO 8601) i liczbą rekordów.

> **Uwaga dotycząca czasu przetwarzania:** API Hugging Face Datasets Server ogranicza liczbę rekordów do 100 na stronę. Baza Open Food Facts zawiera ok. 4,8 miliona produktów, więc pełne przetwarzanie wymaga ok. 48 000 zapytań i może zająć kilka godzin. Uruchom skrypt i pozostaw go działającego w tle (np. na noc).

Uwaga: niespakowany plik `dist/poland_products.db` jest ignorowany przez Git (`.gitignore`). Do repozytorium trafia wyłącznie spakowany `.zip` oraz `version.json`.

## Linki dla aplikacji Android

Aplikacja Android może pobierać pliki bezpośrednio z GitHub przez serwer `raw.githubusercontent.com`:

- **version.json**:  
  `https://raw.githubusercontent.com/<użytkownik>/<repozytorium>/main/dist/version.json`
- **poland_products.db.zip**:  
  `https://raw.githubusercontent.com/<użytkownik>/<repozytorium>/main/dist/poland_products.db.zip`

Zastąp `<użytkownik>` i `<repozytorium>` odpowiednimi wartościami swojego konta GitHub.

## Automatyzacja

Baza jest odświeżana automatycznie raz w tygodniu (niedziela, 03:00 UTC) za pośrednictwem GitHub Actions. Można również uruchomić aktualizację ręcznie przez zakładkę „Actions” w repozytorium na GitHubie.

Po pomyślnym przebiegu workflow zaktualizowane pliki `dist/poland_products.db.zip` oraz `dist/version.json` są committowane i wypychane z powrotem do repozytorium (używając `GITHUB_TOKEN`).
