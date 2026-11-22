#!/usr/bin/env python3
import duckdb
import sqlite3
import zipfile
import os
import json
import sys
from datetime import datetime, timezone

PARQUET_URL = "https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet"

DIST_DIR = "dist"
SQLITE_DB = os.path.join(DIST_DIR, "poland_products.db")
ZIP_FILE = os.path.join(DIST_DIR, "poland_products.db.zip")
VERSION_JSON = os.path.join(DIST_DIR, "version.json")

BATCH_SIZE = 10_000

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}")

def main():
    os.makedirs(DIST_DIR, exist_ok=True)
    for path in (SQLITE_DB, ZIP_FILE, VERSION_JSON):
        if os.path.exists(path):
            os.remove(path)
            log("Usunięto stare pliki: " + path)

    log("Rozpoczynanie przetwarzania Open Food Facts…")
    log("Źródło: " + PARQUET_URL)

    con = duckdb.connect()
    try:
        log("Ładowanie rozszerzenia httpfs…")
        con.execute("INSTALL httpfs;")
        con.execute("LOAD httpfs;")

        log("Przetwarzanie Parquet i filtrowanie dla Polski…")
        con.execute(
            "CREATE OR REPLACE TABLE poland_products AS "
            "SELECT CAST(code AS TEXT) AS code, "
            "COALESCE((SELECT pn.text FROM UNNEST(product_name) AS pn WHERE pn.lang = 'pl' LIMIT 1), "
            "(SELECT pn.text FROM UNNEST(product_name) AS pn LIMIT 1)) AS product_name, "
            "COALESCE(brands, '') AS brands, "
            "COALESCE(image_small_url, '') AS image_small_url "  # --- DODANE ---
            "FROM read_parquet('" + PARQUET_URL + "') "
            "WHERE code IS NOT NULL AND CAST(code AS TEXT) <> '' "
            "AND COALESCE((SELECT pn.text FROM UNNEST(product_name) AS pn WHERE pn.lang = 'pl' LIMIT 1), "
            "(SELECT pn.text FROM UNNEST(product_name) AS pn LIMIT 1)) IS NOT NULL "
            "AND COALESCE((SELECT pn.text FROM UNNEST(product_name) AS pn WHERE pn.lang = 'pl' LIMIT 1), "
            "(SELECT pn.text FROM UNNEST(product_name) AS pn LIMIT 1)) <> '' "
            "AND 'en:poland' = ANY(countries_tags)"
        )

        count = con.execute("SELECT COUNT(*) FROM poland_products").fetchone()[0]
        log("Znaleziono " + str(count) + " produktów dla Polski.")

        if count == 0:
            log("OSTRZEŻENIE: Nie znaleziono żadnych produktów spełniających kryteria!")
            sys.exit(1)

        log("Tworzenie bazy SQLite: " + SQLITE_DB)
        sqlite_con = sqlite3.connect(SQLITE_DB)
        sqlite_con.execute(
            "CREATE TABLE products ("
            "code    TEXT PRIMARY KEY, "
            "product_name TEXT, "
            "brands  TEXT, "
            "image_small_url TEXT DEFAULT ''"
        )
        sqlite_con.execute("CREATE INDEX idx_code ON products(code);")
        sqlite_con.commit()

        log("Kopiowanie danych do SQLite (partie po " + str(BATCH_SIZE) + "…)")
        cursor = con.execute("SELECT code, product_name, brands, image_small_url FROM poland_products")

        total_inserted = 0
        while True:
            rows = cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break
            sqlite_con.executemany(
                "INSERT OR REPLACE INTO products (code, product_name, brands, image_small_url) VALUES (?, ?, ?, ?)",
                rows,
            )
            sqlite_con.commit()
            total_inserted += len(rows)
            log("  Wstawiono " + str(total_inserted) + "/" + str(count) + " rekordów…")

        sqlite_con.close()
        con.close()
        log("Baza SQLite utworzona (" + str(total_inserted) + " rekordów).")

    except Exception as exc:
        log("BŁĄD podczas przetwarzania: " + str(exc))
        try:
            con.close()
        except Exception:
            pass
        sys.exit(1)

    log("Kompresja do " + ZIP_FILE + "…")
    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(SQLITE_DB, arcname="poland_products.db")
    log("Plik ZIP utworzony.")

    os.remove(SQLITE_DB)
    log("Usunięto niespakowany plik .db.")

    version_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": count,
    }
    with open(VERSION_JSON, "w", encoding="utf-8") as f:
        json.dump(version_data, f, ensure_ascii=False, indent=2)
    log("Wygenerowano " + VERSION_JSON + ": " + str(version_data))

    log("Zakończono pomyślnie!")

if __name__ == "__main__":
    main()
