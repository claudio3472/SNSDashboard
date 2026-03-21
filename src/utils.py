import requests
import csv
import os
import tempfile
import pandas as pd
import unicodedata
import re
from io import StringIO, TextIOWrapper

BASE = "https://transparencia.sns.gov.pt/api/explore/v2.1"
CATALOG_URL = f"{BASE}/catalog/datasets"

def load_sns_dataset(dataset_id: str) -> pd.DataFrame:
    """
    Load ANY dataset from transparencia.sns.gov.pt (Explore API v2.1)
    using robust CSV export with automatic delimiter detection.
    No filters, no limits → ALWAYS returns every record.
    """
    url = f"{BASE}/catalog/datasets/{dataset_id}/exports/csv?use_labels_for_header=false"

    # fetch sample to detect delimiter.
    head_bytes = requests.get(url, timeout=120).content[:100_000]
    sample = head_bytes.decode("utf-8-sig", errors="replace")

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        sep = dialect.delimiter
    except Exception:
        sep = ";"

    try:
        # This was giving SSL errors, so switched to requests + TextIOWrapper.
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            r.raw.decode_content = True
            return pd.read_csv(TextIOWrapper(r.raw, encoding="utf-8-sig"), sep=sep, engine="python")
    except Exception as e:
        print(f"Direct read failed for {dataset_id}: {e}. Trying fallback...")

    # fallback: download full file then read.
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
    Standardizes region names, institution names, and removes invalid rows (NaN, None, empty).
    """
    region_mapping = {
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

    inst_mapping = {
        "Centro Hospitalar Universitário de São João": "Unidade Local de Saúde de São João",
        "Centro Hospitalar de São João": "Unidade Local de Saúde de São João",
        "Centro Hospitalar Universitário do Porto": "Unidade Local de Saúde de Santo António",
        "Centro Hospitalar do Porto": "Unidade Local de Saúde de Santo António",
        "Centro Hospitalar Universitário Lisboa Central": "Unidade Local de Saúde de São José",
        "Centro Hospitalar de Lisboa Central": "Unidade Local de Saúde de São José",
        "Centro Hospitalar Universitário Lisboa Norte": "Unidade Local de Saúde de Santa Maria",
        "Centro Hospitalar de Lisboa Norte": "Unidade Local de Saúde de Santa Maria",
        "Centro Hospitalar Universitário de Coimbra": "Unidade Local de Saúde de Coimbra",
        "Centro Hospitalar e Universitário de Coimbra": "Unidade Local de Saúde de Coimbra",
        "Instituto Português Oncologia F. Gentil - Centro": "Instituto Português de Oncologia de Coimbra F. G.",
        "Instituto Português Oncologia de Coimbra": "Instituto Português de Oncologia de Coimbra F. G.",
        "Instituto Português Oncologia F. Gentil - Porto": "Instituto Português de Oncologia do Porto F. G.",
        "Instituto Português Oncologia do Porto": "Instituto Português de Oncologia do Porto F. G.",
        "Instituto Português Oncologia F. Gentil - Lisboa": "Instituto Português de Oncologia de Lisboa F. G.",
        "Instituto Português Oncologia de Lisboa": "Instituto Português de Oncologia de Lisboa F. G.",
        # Adicionar mais mapeamentos se necessário (é necessário ainda).
    }

    invalid_strings = ['nan', 'none', 'null', '', 'inválido']

    for name, df in datasets_list:
        # Regions.
        col = None
        for c in df.columns:
            if "regiao" in _strip_accents(c).lower():
                col = c
                break

        if col is not None:
            initial_rows = len(df)
            df.dropna(subset=[col], inplace=True)
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(region_mapping)
            df.drop(df[df[col].str.lower().isin(invalid_strings)].index, inplace=True)
            removed = initial_rows - len(df)
            if removed > 0:
                print(f"{name}: Removed {removed} invalid rows based on region.")

        # Institutions.
        inst_col = None
        for c in df.columns:
            c_clean = _strip_accents(c).lower()
            if c_clean in ["instituicao", "entidade", "aces"]:
                inst_col = c
                break
        
        if inst_col is not None:
            df[inst_col] = df[inst_col].astype(str)
            # Remover E.P.E., PPP, S.P.A., ...
            df[inst_col] = df[inst_col].str.replace(r',?\s*E\.?\s*P\.?\s*E\.?', '', regex=True, flags=re.IGNORECASE)
            df[inst_col] = df[inst_col].str.replace(r',?\s*P\.?\s*P\.?\s*P\.?', '', regex=True, flags=re.IGNORECASE)
            df[inst_col] = df[inst_col].str.replace(r',?\s*S\.?\s*P\.?\s*A\.?', '', regex=True, flags=re.IGNORECASE)
            # Limpar caracteres HTML e espaços duplos.
            df[inst_col] = df[inst_col].str.replace(r'&nbsp;', ' ', regex=True)
            df[inst_col] = df[inst_col].str.replace(r'\s+', ' ', regex=True)
            df[inst_col] = df[inst_col].str.strip()
            
            df[inst_col] = df[inst_col].replace(inst_mapping)

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