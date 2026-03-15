import requests
import csv
import os
import tempfile
import pandas as pd
import unicodedata
from io import StringIO

BASE = "https://transparencia.sns.gov.pt/api/explore/v2.1"
CATALOG_URL = f"{BASE}/catalog/datasets"

def load_sns_dataset(dataset_id: str) -> pd.DataFrame:
    """
    Load ANY dataset from transparencia.sns.gov.pt (Explore API v2.1)
    using robust CSV export with automatic delimiter detection.
    No filters, no limits → ALWAYS returns every record.
    """
    url = f"{BASE}/catalog/datasets/{dataset_id}/exports/csv?use_labels_for_header=false"

    # fetch sample to detect delimiter
    head_bytes = requests.get(url, timeout=120).content[:100_000]
    sample = head_bytes.decode("utf-8-sig", errors="replace")

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        sep = dialect.delimiter
    except Exception:
        sep = ";"

    # try direct read
    try:
        return pd.read_csv(StringIO(head_bytes.decode()), sep=sep, engine="python")
    except Exception as e:
        print(f"Direct read failed for {dataset_id}: {e}. Trying fallback...")

    # fallback: download full file then read
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            for chunk in r.iter_content(chunk_size=1 << 20):
                tmp.write(chunk)
            tmp_path = tmp.name

    try:
        df = pd.read_csv(tmp_path, sep=sep, engine="python")
    finally:
        try: os.remove(tmp_path)
        except Exception: pass

    return df

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))

def standardize_all_datasets(datasets_list: list[tuple[str, pd.DataFrame]]) -> None:
    """
    Standardizes region names and removes invalid rows (NaN, None, empty).
    """
    mapping = {
        "Região de Saúde LVT": "Lisboa e Vale do Tejo",
        "LVT": "Lisboa e Vale do Tejo",
        "Lisbo" : "Lisboa e Vale do Tejo",
        "Região de Saúde do Centro": "Centro",
        "Região de Saúde Centro ": "Centro",
        "Região de Saúde do Norte": "Norte",
        "Região de Saúde Norte": "Norte",
        "Região de Saúde do Algarve": "Algarve",
        "Região de Saúde do Alentejo": "Alentejo",
        "Região de Saúde do ": "Inválido",
        "Região de Saúd": "Inválido"
    }

    invalid_strings = ['nan', 'none', 'null', '', 'inválido']

    for name, df in datasets_list:
        col = None
        for c in df.columns:
            if "regiao" in _strip_accents(c).lower():
                col = c
                break

        if col is None:
            print(f"{name}: No region column found.")
            continue

        initial_rows = len(df)

        df.dropna(subset=[col], inplace=True)
        df[col] = df[col].astype(str).str.strip()
        
        # Apply mapping to standardize errors in region names.
        df[col] = df[col].replace(mapping)
        
        # Then remove rows with invalid region names (after mapping).
        df.drop(df[df[col].str.lower().isin(invalid_strings)].index, inplace=True)

        final_rows = len(df)
        removed = initial_rows - final_rows
        print(f"{name}: Removed {removed} invalid rows and standardized regions.")

def add_year_month_columns(datasets):
    """
    Goes through each (name, df) in datasets, finds a time column,
    converts it to datetime, and creates df['ano'] and df['mes'].
    """
    possible_time_cols = ["tempo", "data", "date", "periodo", "mes_ano", "ano_mes"]

    for name, df in datasets:
        if not isinstance(df, pd.DataFrame):
            continue

        if "ano" in df.columns and "mes" in df.columns:
            print(f"{name}: already has ano/mes")
            continue

        time_col = None
        for col in df.columns:
            if col.lower() in possible_time_cols:
                time_col = col
                break

        if time_col is None:
            for col in df.columns:
                if df[col].astype(str).str.match(r"^\d{4}[-/]\d{2}$").any():
                    time_col = col
                    break

        if time_col is None:
            print(f"{name}: no time column found")
            continue

        try:
            df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        except Exception:
            print(f"{name}: could not parse time column '{time_col}'")
            continue

        df["ano"] = df[time_col].dt.year
        df["mes"] = df[time_col].dt.month

        print(f"{name}: ano/mes created from '{time_col}'")

    return datasets