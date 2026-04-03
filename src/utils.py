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
        # ============================================================
        # 1) CH → ULS (colapso direto)
        # ============================================================
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
        "Centro Hospitalar Universitário de Lisboa Central": "Unidade Local de Saúde de São José",
        "Centro Hospitalar Universitário de Lisboa Norte": "Unidade Local de Saúde de Santa Maria",
        "Centro Hospitalar de Lisboa Ocidental": "Unidade Local de Saúde de Lisboa Ocidental",
        "Centro Hospitalar de Lisboa - Zona Ocidental": "Unidade Local de Saúde de Lisboa Ocidental",
        "Centro Hospitalar do Barreiro - Montijo": "Unidade Local de Saúde do Arco Ribeirinho",
        "Centro Hospitalar Barreiro/Montijo": "Unidade Local de Saúde do Arco Ribeirinho",
        "Centro Hospitalar Barreiro Montijo": "Unidade Local de Saúde do Arco Ribeirinho",
        "Centro Hospitalar Médio Tejo": "Unidade Local de Saúde do Médio Tejo",
        "Centro Hospitalar do Médio Tejo": "Unidade Local de Saúde do Médio Tejo",
        "Centro Hospitalar Entre Douro e Vouga": "Unidade Local de Saúde de Entre Douro e Vouga",
        "Centro Hospitalar de Entre o Douro e Vouga": "Unidade Local de Saúde de Entre Douro e Vouga",
        "Centro Hospitalar Médio Ave": "Unidade Local de Saúde do Médio Ave",
        "Centro Hospitalar do Médio Ave": "Unidade Local de Saúde do Médio Ave",
        "Centro Hospitalar Póvoa de Varzim/Vila do Conde": "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde",
        "Centro Hospitalar Vila Nova de Gaia/Espinho": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "Centro Hospitalar de Vila Nova de Gaia/Espinho": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "Centro Hospitalar Trás-os-Montes e Alto Douro": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "Centro Hospitalar de Trás-os-Montes e Alto Douro": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "Centro Hospitalar Tâmega e Sousa": "Unidade Local de Saúde do Tâmega e Sousa",
        "Centro Hospitalar do Tâmega e Sousa": "Unidade Local de Saúde do Tâmega e Sousa",
        "Centro Hospitalar Tondela-Viseu": "Unidade Local de Saúde de Viseu Dão-Lafões",
        "Centro Hospitalar Universitário Cova da Beira": "Unidade Local de Saúde da Cova da Beira",
        "Centro Hospitalar de Leiria": "Unidade Local de Saúde da Região de Leiria",
        "Centro Hospitalar do Baixo Vouga": "Unidade Local de Saúde da Região de Aveiro",
        "Centro Hospitalar do Oeste": "Unidade Local de Saúde do Oeste",
        "Centro Hospitalar Universitário de Santo António": "Unidade Local de Saúde de Santo António",
        "Centro Hospitalar Universitário de S. João": "Unidade Local de Saúde de São João",
        "CENTRO HOSPITALAR UNIVERSITÁRIO DE S. JOÃO": "Unidade Local de Saúde de São João",
        "CENTRO HOSP. UNIVERSITÁRIO SANTO ANTÓNIO": "Unidade Local de Saúde de Santo António",

        # ============================================================
        # 2) Hospitais/Institutos → ULS (colapso direto)
        # ============================================================
        "Hospital Doutor Francisco Zagalo - Ovar": "Unidade Local de Saúde da Região de Aveiro",
        "Hospital Doutor Francisco Zagalo": "Unidade Local de Saúde da Região de Aveiro",
        "Hospital Dr. Francisco Zagalo": "Unidade Local de Saúde da Região de Aveiro",
        "Hospital Dr. Francisco Zagalo - Ovar": "Unidade Local de Saúde da Região de Aveiro",

        "Hospital Distrital da Figueira da Foz": "Unidade Local de Saúde do Baixo Mondego",
        "Hospital Distrital Figueira da Foz": "Unidade Local de Saúde do Baixo Mondego",

        "Hospital Arcebispo João Crisóstomo - Cantanhede": "Unidade Local de Saúde de Coimbra",
        "Hospital Arcebispo João Crisóstomo": "Unidade Local de Saúde de Coimbra",

        "Centro Medicina de Reabilitação da Região Centro Rovisco Pais": "Unidade Local de Saúde de Coimbra",
        "Centro Medicina de Reabilitação da Região Centro - Rovisco Pais": "Unidade Local de Saúde de Coimbra",

        "Hospital Professor Doutor Fernando Fonseca": "Unidade Local de Saúde de Amadora/Sintra",
        "Hospital Fernando Fonseca": "Unidade Local de Saúde de Amadora/Sintra",

        "Hospital Garcia de Orta": "Unidade Local de Saúde de Almada-Seixal",
        "Hospital Garcia de Orta - Almada": "Unidade Local de Saúde de Almada-Seixal",

        "Centro Hospitalar de Setúbal": "Unidade Local de Saúde da Arrábida",
        "Centro Hospitalar do Oeste": "Unidade Local de Saúde do Oeste",

        "Hospital de Loures": "Unidade Local de Saúde de Loures/Odivelas",
        "HOSPITAL DE LOURES": "Unidade Local de Saúde de Loures/Odivelas",
        "Hospital Beatriz Ângelo": "Unidade Local de Saúde de Loures/Odivelas",

        "Hospital de Vila Franca de Xira": "Unidade Local de Saúde do Estuário do Tejo",
        "Hospital De Vila Franca De Xira": "Unidade Local de Saúde do Estuário do Tejo",

        "Hospital Distrital de Santarém": "Unidade Local de Saúde da Lezíria",
        "Hospital Distrital Santarém": "Unidade Local de Saúde da Lezíria",

        "Hospital Espírito Santo de Évora": "Unidade Local de Saúde do Alentejo Central",
        "Hospital do Espírito Santo de Évora": "Unidade Local de Saúde do Alentejo Central",

        "Centro Hospitalar Universitário do Algarve": "Unidade Local de Saúde do Algarve",

        "Hospital Rovisco Pais": "Unidade Local de Saúde de Coimbra",

        "Hospital Santa Maria Maior": "Unidade Local de Saúde de Barcelos/Esposende",

        "Centro Hospitalar Psiquiátrico de Lisboa": "Unidade Local de Saúde de São José",
        "Centro Hospitalar Psiquiatrico de Lisboa": "Unidade Local de Saúde de São José",  # sem acento

        "Instituto de Oftalmologia Dr. Gama Pinto": "Unidade Local de Saúde de São José",
        "Instituto de Oftalmologia Gama Pinto": "Unidade Local de Saúde de São José",
        "Instituto Gama Pinto": "Unidade Local de Saúde de São José",

        "Hospital da Senhora da Oliveira Guimarães": "Unidade Local de Saúde do Alto Ave",
        "Hospital da Senhora da Oliveira, Guimarães": "Unidade Local de Saúde do Alto Ave",
        "Hospital da Senhora da Oliveira - Guimarães": "Unidade Local de Saúde do Alto Ave",

        "Hospital de Braga": "Unidade Local de Saúde de Braga",
        "Hospital de Magalhães Lemos": "Unidade Local de Saúde de Santo António",

        # Variantes ULS residuais (sem artigo / barras / etc.)
        "Unidade Local de Saúde Póvoa de Varzim/Vila do Conde": "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde",
        "Unidade Local de Saúde de Gaia/Espinho": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",

        # IPO maiúsculas (sem acentos) → “F. G.”
        "INSTITUTO PORTUGUES DE ONCOLOGIA DE COIMBRA": "Instituto Português de Oncologia de Coimbra F. G.",
        "INSTITUTO PORTUGUES DE ONCOLOGIA DE LISBOA": "Instituto Português de Oncologia de Lisboa F. G.",
        "INSTITUTO PORTUGUES DE ONCOLOGIA DO PORTO": "Instituto Português de Oncologia do Porto F. G.",

        # ============================================================
        # 3) IPO (todas as variantes) → forma canónica “F. G.”
        # ============================================================
        "Instituto Português Oncologia F. Gentil - Centro": "Instituto Português de Oncologia de Coimbra F. G.",
        "Instituto Português Oncologia de Coimbra": "Instituto Português de Oncologia de Coimbra F. G.",
        "Instituto Português de Oncologia de Coimbra": "Instituto Português de Oncologia de Coimbra F. G.",
        "Instituto Português Oncologia Francisco Gentil - Coimbra": "Instituto Português de Oncologia de Coimbra F. G.",
        "Instituto Português de Oncologia de Coimbra Francisco Gentil": "Instituto Português de Oncologia de Coimbra F. G.",

        "Instituto Português Oncologia F. Gentil - Lisboa": "Instituto Português de Oncologia de Lisboa F. G.",
        "Instituto Português Oncologia de Lisboa": "Instituto Português de Oncologia de Lisboa F. G.",
        "Instituto Português de Oncologia de Lisboa": "Instituto Português de Oncologia de Lisboa F. G.",
        "Instituto Português Oncologia Francisco Gentil - Lisboa": "Instituto Português de Oncologia de Lisboa F. G.",
        "Instituto Português de Oncologia de Lisboa Francisco Gentil": "Instituto Português de Oncologia de Lisboa F. G.",
        "Instituto Português de Oncologia de Lisboa F.G.": "Instituto Português de Oncologia de Lisboa F. G.",

        "Instituto Português Oncologia F. Gentil - Porto": "Instituto Português de Oncologia do Porto F. G.",
        "Instituto Português Oncologia do Porto": "Instituto Português de Oncologia do Porto F. G.",
        "Instituto Português de Oncologia do Porto": "Instituto Português de Oncologia do Porto F. G.",
        "Instituto Português Oncologia Francisco Gentil - Porto": "Instituto Português de Oncologia do Porto F. G.",
        "Instituto Português de Oncologia do Porto Francisco Gentil": "Instituto Português de Oncologia do Porto F. G.",
        "Instituto Português de Oncologia do Porto F.G.": "Instituto Português de Oncologia do Porto F. G.",

        "Inst.port.onc.francisco Gentil-Coimbra": "Instituto Português de Oncologia de Coimbra F. G.",
        "Inst.port.oncologia De Lisboa-franc.gentil": "Instituto Português de Oncologia de Lisboa F. G.",
        "Instituto Port.oncologia Do Porto": "Instituto Português de Oncologia do Porto F. G.",

        # ============================================================
        # 4) ULS canónicas (identidade — manter)
        # ============================================================
        "Unidade Local de Saúde do Baixo Mondego": "Unidade Local de Saúde do Baixo Mondego",
        "Unidade Local de Saúde do Baixo Alentejo": "Unidade Local de Saúde do Baixo Alentejo",
        "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde": "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde",
        "Unidade Local de Saúde do Litoral Alentejano": "Unidade Local de Saúde do Litoral Alentejano",
        "Unidade Local de Saúde do Médio Ave": "Unidade Local de Saúde do Médio Ave",
        "Unidade Local de Saúde do Médio Tejo": "Unidade Local de Saúde do Médio Tejo",
        "Unidade Local de Saúde do Nordeste": "Unidade Local de Saúde do Nordeste",
        "Unidade Local de Saúde do Oeste": "Unidade Local de Saúde do Oeste",
        "Unidade Local de Saúde do Alentejo Central": "Unidade Local de Saúde do Alentejo Central",
        "Unidade Local de Saúde do Algarve": "Unidade Local de Saúde do Algarve",
        "Unidade Local de Saúde da Cova da Beira": "Unidade Local de Saúde da Cova da Beira",
        "Unidade Local de Saúde da Guarda": "Unidade Local de Saúde da Guarda",
        "Unidade Local de Saúde da Região de Aveiro": "Unidade Local de Saúde da Região de Aveiro",
        "Unidade Local de Saúde da Região de Leiria": "Unidade Local de Saúde da Região de Leiria",
        "Unidade Local de Saúde de Castelo Branco": "Unidade Local de Saúde de Castelo Branco",
        "Unidade Local de Saúde de Coimbra": "Unidade Local de Saúde de Coimbra",
        "Unidade Local de Saúde de Viseu Dão-Lafões": "Unidade Local de Saúde de Viseu Dão-Lafões",
        "Unidade Local de Saúde da Arrábida": "Unidade Local de Saúde da Arrábida",
        "Unidade Local de Saúde da Lezíria": "Unidade Local de Saúde da Lezíria",
        "Unidade Local de Saúde de Almada-Seixal": "Unidade Local de Saúde de Almada-Seixal",
        "Unidade Local de Saúde de Amadora/Sintra": "Unidade Local de Saúde de Amadora/Sintra",
        "Unidade Local de Saúde de Lisboa Ocidental": "Unidade Local de Saúde de Lisboa Ocidental",
        "Unidade Local de Saúde de Loures-Odivelas": "Unidade Local de Saúde de Loures/Odivelas",
        "Unidade Local de Saúde de Santa Maria": "Unidade Local de Saúde de Santa Maria",
        "Unidade Local de Saúde de São José": "Unidade Local de Saúde de São José",
        "Unidade Local de Saúde do Arco Ribeirinho": "Unidade Local de Saúde do Arco Ribeirinho",
        "Unidade Local de Saúde do Estuário do Tejo": "Unidade Local de Saúde do Estuário do Tejo",
        "Unidade Local de Saúde de Barcelos/Esposende": "Unidade Local de Saúde de Barcelos/Esposende",
        "Unidade Local de Saúde de Braga": "Unidade Local de Saúde de Braga",
        "Unidade Local de Saúde de Entre Douro e Vouga": "Unidade Local de Saúde de Entre Douro e Vouga",
        "Unidade Local de Saúde de Matosinhos": "Unidade Local de Saúde de Matosinhos",
        "Unidade Local de Saúde de Santo António": "Unidade Local de Saúde de Santo António",
        "Unidade Local de Saúde de São João": "Unidade Local de Saúde de São João",
        "Unidade Local de Saúde de Trás-os-Montes e Alto Douro": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "Unidade Local de Saúde de Vila Nova de Gaia/Espinho": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "Unidade Local de Saúde do Alto Ave": "Unidade Local de Saúde do Alto Ave",
        "Unidade Local de Saúde do Alto Minho": "Unidade Local de Saúde do Alto Minho",
        "Unidade Local de Saúde do Tâmega e Sousa": "Unidade Local de Saúde do Tâmega e Sousa",
        "Unidade Local de Saúde do Norte Alentejano": "Unidade Local de Saúde do Alto Alentejo",

        # ============================================================
        # 5) ULS — VARIANTES (maiúsculas/abreviações/esp. nas barras)
        # ============================================================
        "Unidade Local de Saúde de Dão-Lafões": "Unidade Local de Saúde de Viseu Dão-Lafões",
        "Unidade Local de Saúde Alto Minho": "Unidade Local de Saúde do Alto Minho",
        "Unidade Local de Saúde Litoral Alentejano": "Unidade Local de Saúde do Litoral Alentejano",
        "Unidade Local de Saúde Baixo Alentejo": "Unidade Local de Saúde do Baixo Alentejo",
        "Unidade Local de Saúde Guarda": "Unidade Local de Saúde da Guarda",
        "Unidade Local de Saúde Matosinhos": "Unidade Local de Saúde de Matosinhos",
        "Unidade Local de Saúde Nordeste": "Unidade Local de Saúde do Nordeste",
        "Unidade Local de Saúde Norte Alentejano": "Unidade Local de Saúde do Alto Alentejo",
        "Unidade Local de Saúde de Gaia e Espinho": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "Unidade Local de Saúde de S. João": "Unidade Local de Saúde de São João",

        "UNIDADE LOCAL DE SAUDE DO LITORAL ALENTEJANO": "Unidade Local de Saúde do Litoral Alentejano",
        "UNIDADE LOCAL DO BAIXO ALENTEJO": "Unidade Local de Saúde do Baixo Alentejo",
        "UNIDADE LOCAL DE SAUDE DE CASTELO BRANCO": "Unidade Local de Saúde de Castelo Branco",
        "UNIDADE LOCAL DE SAÚDE DA GUARDA": "Unidade Local de Saúde da Guarda",
        "UNIDADE LOCAL DE SAUDE DO NORDESTE": "Unidade Local de Saúde do Nordeste",
        "UNIDADE LOCAL DE SAÚDE ALTO MINHO": "Unidade Local de Saúde do Alto Minho",
        "UNIDADE LOCAL DE SAÚDE DE MATOSINHOS": "Unidade Local de Saúde de Matosinhos",

        "UNIDADE LOCAL DE SAÚDE DE AMADORA / SINTRA": "Unidade Local de Saúde de Amadora/Sintra",
        "UNIDADE LOCAL DE SAÚDE DE LOURES / ODIVELAS": "Unidade Local de Saúde de Loures/Odivelas",
        "UNIDADE LOCAL DE SAÚDE DO ESTUÁRIO DO TEJO": "Unidade Local de Saúde do Estuário do Tejo",
        "UNIDADE LOCAL DE SAÚDE DE BRAGA": "Unidade Local de Saúde de Braga",
        "UNIDADE LOCAL DE SAÚDE DE SANTO ANTÓNIO": "Unidade Local de Saúde de Santo António",

        "Unidade Local De Saúde Do Alentejo Central": "Unidade Local de Saúde do Alentejo Central",
        "Unidade Local De Saúde Do Alto Alentejo": "Unidade Local de Saúde do Alto Alentejo",
        "Unidade Local de Saúde do Norte Alentejano": "Unidade Local de Saúde do Alto Alentejo",
        "Unidade Local De Saúde Do Baixo Alentejo": "Unidade Local de Saúde do Baixo Alentejo",
        "Unidade Local De Saúde Litoral Alentejano": "Unidade Local de Saúde do Litoral Alentejano",
        "Unidade Local De Saúde Do Algarve": "Unidade Local de Saúde do Algarve",
        "Unidade Local De Saúde Da Cova Da Beira": "Unidade Local de Saúde da Cova da Beira",
        "Unidade Local De Saúde Da Guarda": "Unidade Local de Saúde da Guarda",
        "Unidade Local De Saúde Da Região De Aveiro": "Unidade Local de Saúde da Região de Aveiro",
        "Unidade Local De Saúde Da Região De Leiria": "Unidade Local de Saúde da Região de Leiria",
        "Unidade Local De Saúde De Castelo Branco": "Unidade Local de Saúde de Castelo Branco",
        "Unidade Local De Saúde De Coimbra": "Unidade Local de Saúde de Coimbra",
        "Unidade Local De Saúde De Viseu Dão-Lafões": "Unidade Local de Saúde de Viseu Dão-Lafões",
        "Unidade Local De Saúde Do Baixo Mondego": "Unidade Local de Saúde do Baixo Mondego",
        "Unidade Local De Saúde Da Arrábida": "Unidade Local de Saúde da Arrábida",
        "Unidade Local De Saúde Da Lezíria": "Unidade Local de Saúde da Lezíria",
        "Unidade Local De Saúde De Almada / Seixal": "Unidade Local de Saúde de Almada-Seixal",
        "Unidade Local De Saúde De Amadora / Sintra": "Unidade Local de Saúde de Amadora/Sintra",
        "Unidade Local De Saúde De Lisboa Ocidental": "Unidade Local de Saúde de Lisboa Ocidental",
        "Unidade Local De Saúde De Santa Maria": "Unidade Local de Saúde de Santa Maria",
        "Unidade Local De Saúde De São José": "Unidade Local de Saúde de São José",
        "Unidade Local De Saúde Do Arco Ribeirinho": "Unidade Local de Saúde do Arco Ribeirinho",
        "Unidade Local De Saúde Do Médio Tejo": "Unidade Local de Saúde do Médio Tejo",
        "Unidade Local De Saúde Do Oeste": "Unidade Local de Saúde do Oeste",
        "Unidade Local De Saúde Da Póvoa De Varzim / Vila Do Conde": "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde",
        "Unidade Local De Saúde De Barcelos / Esposende": "Unidade Local de Saúde de Barcelos/Esposende",
        "Unidade Local De Saúde De Entre Douro E Vouga": "Unidade Local de Saúde de Entre Douro e Vouga",
        "Unidade Local De Saúde De Gaia / Espinho": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "Unidade Local De Saúde De São João": "Unidade Local de Saúde de São João",
        "Unidade Local De Saúde De Trás-os-montes E Alto Douro": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "Unidade Local De Saúde Do Alto Ave": "Unidade Local de Saúde do Alto Ave",
        "Unidade Local De Saúde Do Alto Minho": "Unidade Local de Saúde do Alto Minho",
        "Unidade Local De Saúde Do Médio Ave": "Unidade Local de Saúde do Médio Ave",
        "Unidade Local De Saúde Do Nordeste": "Unidade Local de Saúde do Nordeste",
        "Unidade Local De Saúde Do Tâmega E Sousa": "Unidade Local de Saúde do Tâmega e Sousa",
        "Unidade Local Saúde De Matosinhos": "Unidade Local de Saúde de Matosinhos",

        # ============================================================
        # 6) Variantes/duplicados simples → canónico
        # ============================================================
        "Centro Hospitalar Póvoa Varzim / Vila do Conde": "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde",
        "Centro Hospitalar Vila Nova Gaia/Espinho": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "Hospital Distrital S.Maria Maior - Barcelos": "Unidade Local de Saúde de Barcelos/Esposende",

        # ============================================================
        # 7) Organismos centrais → forma canónica (inclui variantes/typos)
        # ============================================================
        "Direção Executiva do Serviço Nacional de Saúde, I.P.": "Direção Executiva do Serviço Nacional de Saúde, I.P.",
        "Direção Executiva do SNS, I.P.": "Direção Executiva do Serviço Nacional de Saúde, I.P.",
        "DIREÇÃO EXECUTIVA DO SERVIÇO NACIONAL DE SAÚDE,I.P": "Direção Executiva do Serviço Nacional de Saúde, I.P.",

        "Instituto Nacional de Emergência Médica": "Instituto Nacional de Emergência Médica",
        "Instituto Nacional de Emergência Médica, I.P.": "Instituto Nacional de Emergência Médica",
        "Instituto Nacional De Emergência Médica": "Instituto Nacional de Emergência Médica",

        # INSA → “Doutor”
        "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.": "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.",
        "Instituto Nacional de Saúde Dr. Ricardo Jorge, I.P.": "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.",
        "Instituto Nacional de Saúde Dr Ricardo Jorge, I.P.": "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.",
        "Instituto Nacional de Saúde Dr. Ricardo Jorge, I.P": "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.",
        "Instituto Nacional de Saúde Dr Ricardo Jorge I.P.": "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.",
        "Instituto Nacional de Saúde Dr. Ricardo Jorge I.P.": "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.",
        "Instituto Nacional De Saúde Dr Ricardo Jorge, I.P.": "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.",
        "Instituto Nacional Saúde Dr. Ricardo Jorge - Lisboa": "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.",

        "Infarmed - Autoridade Nacional do Medicamento e Produtos de Saúde, I.P.": "Infarmed - Autoridade Nacional do Medicamento e Produtos de Saúde, I.P.",
        "Autoridade Nacional Medicamento Produtos de Saúde, I.P.": "Infarmed - Autoridade Nacional do Medicamento e Produtos de Saúde, I.P.",
        "Autoridade Nac. Medicamento Produtos De Saúde, I.P.": "Infarmed - Autoridade Nacional do Medicamento e Produtos de Saúde, I.P.",

        "Instituto Português do Sangue e da Transplantação, I.P.": "Instituto Português do Sangue e da Transplantação, I.P.",
        "Instituto Português Do Sangue e Da Transplantação, IP": "Instituto Português do Sangue e da Transplantação, I.P.",
        "Instituto Portug. Do Sangue E Da Transplantação,I.P.": "Instituto Português do Sangue e da Transplantação, I.P.",

        "Administração Central do Sistema de Saúde, I.P.": "Administração Central do Sistema de Saúde, I.P.",
        "Administração Central do Sistema de Saúde, I.P": "Administração Central do Sistema de Saúde, I.P.",

        "Secretaria-Geral do Ministério da Saúde": "Secretaria-Geral do Ministério da Saúde",
        "Secretaria Geral do Ministério da Saúde": "Secretaria-Geral do Ministério da Saúde",
        "Secretaria-geral Do Ministério Da Saúde": "Secretaria-Geral do Ministério da Saúde",

        "Serviços Partilhados do Ministério da Saúde, E.P.E.": "Serviços Partilhados do Ministério da Saúde, E.P.E.",
        "Serviçortilhados do Ministério da Saúde": "Serviços Partilhados do Ministério da Saúde, E.P.E.",
        "Serviçortilhados Do Ministério Da Saúde": "Serviços Partilhados do Ministério da Saúde, E.P.E.",

        "Ação Governativa": "Ação Governativa",
        "Ação Governativa - MS": "Ação Governativa",

        # ARS — variantes com/sem “, I.P.” → forma canónica (sem “, I.P.”)
        "Administração Regional de Saúde do Alentejo": "Administração Regional de Saúde do Alentejo",
        "Administração Regional de Saúde do Algarve": "Administração Regional de Saúde do Algarve",
        "Administração Regional de Saúde do Centro": "Administração Regional de Saúde do Centro",
        "Administração Regional de Saúde de Lisboa e Vale do Tejo": "Administração Regional de Saúde de Lisboa e Vale do Tejo",
        "Administração Regional de Saúde do Norte": "Administração Regional de Saúde do Norte",

        "Administração Regional de Saúde do Alentejo, I.P.": "Administração Regional de Saúde do Alentejo",
        "Administração Regional de Saúde do Algarve, I.P.": "Administração Regional de Saúde do Algarve",
        "Administração Regional de Saúde do Centro, I.P.": "Administração Regional de Saúde do Centro",
        "Administração Regional de Saúde de Lisboa e Vale do Tejo, I.P.": "Administração Regional de Saúde de Lisboa e Vale do Tejo",
        "Administração Regional de Saúde do Norte, I.P.": "Administração Regional de Saúde do Norte",

        "Administração Regional Saúde Lisboa Vale Tejo, I.P.": "Administração Regional de Saúde de Lisboa e Vale do Tejo",
        "Administração Regional Saúde Norte, I.P.": "Administração Regional de Saúde do Norte",
        "Administracao Regional Saúde Norte, I.P.": "Administração Regional de Saúde do Norte",

        "Administração Regional De Saúde Do Alentejo, I.P.": "Administração Regional de Saúde do Alentejo",
        "Administração Regional De Saúde Do Algarve, I.P.": "Administração Regional de Saúde do Algarve",
        "Administração Regional De Saúde Do Centro, I.P.": "Administração Regional de Saúde do Centro",

        "Administração Regional de Saúde do Algarve , I.P.": "Administração Regional de Saúde do Algarve",
        "Administração Regional de Saúde do Centro , I.P.": "Administração Regional de Saúde do Centro",
        "Administração Regional de Saúde do Norte , I.P.": "Administração Regional de Saúde do Norte",
        "Administração Regional de Saúde de Lisboa e Vale do Tejo , I.P.": "Administração Regional de Saúde de Lisboa e Vale do Tejo",

        # Inspeção-Geral (normalização)
        "Inspeção-Geral das Atividades em Saúde": "Inspeção-Geral das Atividades em Saúde",
        "Inspeção Geral das Atividades da Saúde": "Inspeção-Geral das Atividades em Saúde",

        # ============================================================
        # 8) SICAD — variantes/typos → forma canónica (Instituto)
        # ============================================================
        "Instituto para os Comportamentos Aditivos e as Dependências, I. P.": "Instituto para os Comportamentos Aditivos e as Dependências, I. P.",
        "Instituto para os Comportamentos Aditivos e as Dndências, I. P.": "Instituto para os Comportamentos Aditivos e as Dependências, I. P.",
        "Instituto para os Comportamentos Aditivos e as Dndências, I.P.": "Instituto para os Comportamentos Aditivos e as Dependências, I. P.",
        "Instituto para os Comportamentos Aditivos e as Dndências I.P.": "Instituto para os Comportamentos Aditivos e as Dependências, I. P.",
        "Instituto Para Os Comportamentos Aditivos E As Dndências, I.P.": "Instituto para os Comportamentos Aditivos e as Dependências, I. P.",
        "Serviço de Intervenção nos Comportamentos Aditivos e nas Dndências": "Instituto para os Comportamentos Aditivos e as Dependências, I. P.",
        "Serviço de Intervenção Comportamentos Aditivos e Dndências": "Instituto para os Comportamentos Aditivos e as Dependências, I. P.",

        # ============================================================
        # 9) Itens com IDENTIDADE (por decisão tua — manter)
        # ============================================================
        "Hospital de Cascais": "Hospital de Cascais",
        "Hospital José Luciano de Castro - Anadia": "Hospital José Luciano de Castro - Anadia",

        # ============================================================
        # 10) HOTFIXES FINAIS — ULS Castelo Branco (artigo/esp./NBSP)
        # ============================================================
        "Unidade Local de Saúde Castelo Branco": "Unidade Local de Saúde de Castelo Branco",
        "Unidade Local de Saúde  Castelo Branco": "Unidade Local de Saúde de Castelo Branco",      # duplo espaço
        "Unidade Local de Saúde\u00A0Castelo Branco": "Unidade Local de Saúde de Castelo Branco",  # NBSP entre palavras

        # ============================================================
        # 12) NOVAS ENTRADAS — “ACES …” → ULS
        # ============================================================
        # Algarve
        "ACES Algarve I - Algarve Central": "Unidade Local de Saúde do Algarve",
        "ACES Algarve II - Algarve Barlavento": "Unidade Local de Saúde do Algarve",
        "ACES Algarve III - Algarve Sotavento": "Unidade Local de Saúde do Algarve",
        "ACES Algarve Barlavento": "Unidade Local de Saúde do Algarve",
        "ACES Algarve Sotavento": "Unidade Local de Saúde do Algarve",
        "ACES Algarve Central": "Unidade Local de Saúde do Algarve",

        # Região Centro (Baixo Mondego / Beiras / Leiria)
        "ACES Baixo Mondego": "Unidade Local de Saúde do Baixo Mondego",
        "ACES Beira Interior Sul": "Unidade Local de Saúde de Castelo Branco",
        "ACES Pinhal Interior Norte": "Unidade Local de Saúde de Coimbra",
        "ACES Pinhal Interior Sul": "Unidade Local de Saúde de Castelo Branco",
        "ACES Pinhal Litoral": "Unidade Local de Saúde da Região de Leiria",
        "ACES Baixo Vouga": "Unidade Local de Saúde da Região de Aveiro",
        "ACES Cova da Beira": "Unidade Local de Saúde da Cova da Beira",
        "ACES Dão Lafões": "Unidade Local de Saúde de Viseu Dão-Lafões",
        "ACES Dão-Lafões": "Unidade Local de Saúde de Viseu Dão-Lafões",
        "ACES Guarda": "Unidade Local de Saúde da Guarda",
        "ACES Aveiro Norte": "Unidade Local de Saúde da Região de Aveiro",

        # Altenejo (Alentejo Central / Baixo Alentejo / Litoral Alentejano / Norte Alentejano)
        "ACES Alentejo Central": "Unidade Local de Saúde do Alentejo Central",
        "ACES Baixo Alentejo": "Unidade Local de Saúde do Baixo Alentejo",
        "ACES Alentejo Litoral": "Unidade Local de Saúde do Litoral Alentejano",
        "ACES São Mamede": "Unidade Local de Saúde do Alto Alentejo",

        # Lisboa e Vale do Tejo
        "ACES Amadora": "Unidade Local de Saúde de Amadora/Sintra",
        "ACES Sintra": "Unidade Local de Saúde de Amadora/Sintra",
        "ACES Cascais": "Unidade Local de Saúde de Lisboa Ocidental",
        "ACES Lisboa Central": "Unidade Local de Saúde de São José",
        "ACES Lisboa Norte": "Unidade Local de Saúde de Santa Maria",
        "ACES Lisboa Ocidental e Oeiras": "Unidade Local de Saúde de Lisboa Ocidental",
        "ACES Loures / Odivelas": "Unidade Local de Saúde de Loures/Odivelas",
        "ACES Médio Tejo": "Unidade Local de Saúde do Médio Tejo",
        "ACES Oeste Norte": "Unidade Local de Saúde do Oeste",
        "ACES Oeste Sul": "Unidade Local de Saúde do Oeste",
        "ACES Almada / Seixal": "Unidade Local de Saúde de Almada-Seixal",
        "ACES Arco Ribeirinho": "Unidade Local de Saúde do Arco Ribeirinho",
        "ACES Arrábida": "Unidade Local de Saúde da Arrábida",
        "ACES Estuário do Tejo": "Unidade Local de Saúde do Estuário do Tejo",
        "ACES Lezíria": "Unidade Local de Saúde da Lezíria",

        # Norte (Minho / Douro / Tâmega e Sousa / Grande Porto / Ave)
        "ACES Alto Trás-os-Montes - Alto Tâmega e Barroso": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "ACES Alto Ave - Guimarães, Vizela e Terras de Basto": "Unidade Local de Saúde do Alto Ave",
        "ACES Ave / Famalicão": "Unidade Local de Saúde do Médio Ave",
        "ACES Cávado I - Braga": "Unidade Local de Saúde de Braga",
        "ACES Cávado II - Gerês / Cabreira": "Unidade Local de Saúde de Braga",
        "ACES Douro I - Marão e Douro Norte": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "ACES Douro II - Douro Sul": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "ACES Entre Douro e Vouga I - Feira e Arouca": "Unidade Local de Saúde de Entre Douro e Vouga",
        "ACES Entre Douro e Vouga II - Aveiro Norte": "Unidade Local de Saúde da Região de Aveiro",
        "ACES Grande Porto I - Santo Tirso / Trofa": "Unidade Local de Saúde do Médio Ave",
        "ACES Grande Porto II - Gondomar": "Unidade Local de Saúde de Santo António",
        "ACES Grande Porto III - Maia / Valongo": "Unidade Local de Saúde de São João",
        "ACES Grande Porto V - Porto Ocidental": "Unidade Local de Saúde de Santo António",
        "ACES Grande Porto VI - Porto Oriental": "Unidade Local de Saúde de São João",
        "ACES Grande Porto VII - Gaia": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "ACES Grande Porto VIII - Espinho / Gaia": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "ACES Alto Ave": "Unidade Local de Saúde do Alto Ave",
        "ACES Alto Minho": "Unidade Local de Saúde do Alto Minho",
        "ACES Alto Tâmega e Barroso": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "ACES Barcelos / Esposende": "Unidade Local de Saúde de Barcelos/Esposende",
        "ACES Braga": "Unidade Local de Saúde de Braga",
        "ACES Douro Sul": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "ACES Espinho / Gaia": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "ACES Feira e Arouca": "Unidade Local de Saúde de Entre Douro e Vouga",
        "ACES Gaia": "Unidade Local de Saúde de Vila Nova de Gaia/Espinho",
        "ACES Gerês / Cabreira": "Unidade Local de Saúde de Braga",
        "ACES Gondomar": "Unidade Local de Saúde de Santo António",
        "ACES Maia / Valongo": "Unidade Local de Saúde de São João",
        "ACES Marão e Douro Norte": "Unidade Local de Saúde de Trás-os-Montes e Alto Douro",
        "ACES Matosinhos": "Unidade Local de Saúde de Matosinhos",
        "ACES Nordeste": "Unidade Local de Saúde do Nordeste",
        "ACES Porto Ocidental": "Unidade Local de Saúde de Santo António",
        "ACES Porto Oriental": "Unidade Local de Saúde de São João",
        "ACES Póvoa de Varzim / Vila do Conde": "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde",
        "ACES Póvoa do Varzim / Vila do Conde": "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde",
        "ACES Santo Tirso / Trofa": "Unidade Local de Saúde do Médio Ave",
        "ACES Vale do Sousa Norte": "Unidade Local de Saúde de Entre Douro e Vouga",
        "ACES Vale do Sousa Sul": "Unidade Local de Saúde de Entre Douro e Vouga",

        "ACES Tâmega I - Baixo Tâmega": "Unidade Local de Saúde do Tâmega e Sousa",
        "ACES Baixo Tâmega": "Unidade Local de Saúde do Tâmega e Sousa",
        "ACES Tâmega II - Vale do Sousa Sul": "Unidade Local de Saúde do Tâmega e Sousa",
        "ACES Tâmega III - Vale do Sousa Norte": "Unidade Local de Saúde do Tâmega e Sousa",


        # ============================================================
        # 13) CSP — variantes/typos → forma canónica (Instituto)
        # ============================================================

        "CSP da ULS Alentejo Central": "Área dos CSP da ULS Alentejo Central",
        "CSP da ULS Alto Alentejo": "Área dos CSP da ULS Alto Alentejo",
        "CSP da ULS Baixo Alentejo": "Área dos CSP da ULS Baixo Alentejo",
        "CSP da ULS Litoral Alentejano": "Área dos CSP da ULS Litoral Alentejano",

        "CSP da ULS Algarve": "Área dos CSP da ULS Algarve",

        "CSP da ULS Baixo Mondego": "Área dos CSP da ULS Baixo Mondego",
        "CSP da ULS Castelo Branco": "Área dos CSP da ULS Castelo Branco",
        "CSP da ULS Coimbra": "Área dos CSP da ULS Coimbra",
        "CSP da ULS Cova da Beira": "Área dos CSP da ULS Cova da Beira",
        "CSP da ULS Guarda": "Área dos CSP da ULS Guarda",
        "CSP da ULS Região de Aveiro": "Área dos CSP da ULS Região de Aveiro",
        "CSP da ULS Região de Leiria": "Área dos CSP da ULS Região de Leiria",
        "CSP da ULS Viseu Dão-Lafões": "Área dos CSP da ULS Viseu Dão-Lafões",

        "CSP da ULS Almada / Seixal": "Área dos CSP da ULS Almada-Seixal",
        "CSP da ULS Amadora / Sintra": "Área dos CSP da ULS Amadora / Sintra",
        "CSP da ULS Arco Ribeirinho": "Área dos CSP da ULS Arco Ribeirinho",
        "CSP da ULS Arrábida": "Área dos CSP da ULS Arrábida",
        "CSP da ULS Estuário do Tejo": "Área dos CSP da ULS Estuário do Tejo",
        "CSP da ULS Lezíria": "Área dos CSP da ULS Lezíria",
        "CSP da ULS Lisboa Ocidental": "Área dos CSP da ULS Lisboa Ocidental",
        "CSP da ULS Loures / Odivelas": "Área dos CSP da ULS Loures / Odivelas",
        "CSP da ULS Médio Tejo": "Área dos CSP da ULS Médio Tejo",
        "CSP da ULS Oeste": "Área dos CSP da ULS Oeste",
        "CSP da ULS Santa Maria": "Área dos CSP da ULS Santa Maria",
        "CSP da ULS São José": "Área dos CSP da ULS São José",
        
        "CSP da ULS Alto Ave": "Área dos CSP da ULS Alto Ave",
        "CSP da ULS Alto Minho": "Área dos CSP da ULS Alto Minho",
        "CSP da ULS Barcelos / Esposende": "Área dos CSP da ULS Barcelos / Esposende",
        "CSP da ULS Braga": "Área dos CSP da ULS Braga",
        "CSP da ULS Entre Douro e Vouga": "Área dos CSP da ULS Entre Douro e Vouga",
        "CSP da ULS Gaia / Espinho": "Área dos CSP da ULS Gaia / Espinho",
        "CSP da ULS Matosinhos": "Área dos CSP da ULS Matosinhos",
        "CSP da ULS Médio Ave": "Área dos CSP da ULS Médio Ave",
        "CSP da ULS Nordeste": "Área dos CSP da ULS Nordeste",
        "CSP da ULS Santo António": "Área dos CSP da ULS Santo António",
        "CSP da ULS São João": "Área dos CSP da ULS São João",
        "CSP da ULS Trás-os-Montes e Alto Douro": "Área dos CSP da ULS Trás-os-Montes e Alto Douro",
        "CSP da ULS Tâmega e Sousa": "Área dos CSP da ULS Tâmega e Sousa",
        "CSP da ULS Póvoa Varzim / Vila Conde": "Área dos CSP da ULS Póvoa de Varzim / Vila do Conde",
        "Área dos CSP da ULS Póvoa Varzim / Vila Conde": "Área dos CSP da ULS Póvoa de Varzim / Vila do Conde",
        "CSP da ULS Trás-os-Montes Alto Douro": "Área dos CSP da ULS Trás-os-Montes e Alto Douro",

        # Hotfix final
        "Área dos CSP da ULS Trás-os-Montes Alto Douro": "Área dos CSP da ULS Trás-os-Montes e Alto Douro",
        "Área dos CSP da ULS Almada / Seixal": "Área dos CSP da ULS Almada-Seixal",

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
            # Trim and normalize case to avoid mismatch in mapping keys
            df[inst_col] = df[inst_col].str.strip()
            # Remover E.P.E., PPP, S.P.A., ...
            df[inst_col] = df[inst_col].str.replace(r',?\s*E\.?\s*P\.?\s*E\.?', '', regex=True, flags=re.IGNORECASE)
            df[inst_col] = df[inst_col].str.replace(r',?\s*P\.?\s*P\.?\s*P\.?', '', regex=True, flags=re.IGNORECASE)
            df[inst_col] = df[inst_col].str.replace(r',?\s*S\.?\s*P\.?\s*A\.?', '', regex=True, flags=re.IGNORECASE)
            # Limpar caracteres HTML e espaços duplos.
            df[inst_col] = df[inst_col].str.replace(r'&nbsp;', ' ', regex=True)
            df[inst_col] = df[inst_col].str.replace(r'\s+', ' ', regex=True)
            df[inst_col] = df[inst_col].str.strip()
            
            # Aplica mapeamentos (inclui ACES → ULS)
            df[inst_col] = df[inst_col].replace(inst_mapping)
            df[inst_col] = df[inst_col].replace({k.upper(): v for k, v in inst_mapping.items()})
            df[inst_col] = df[inst_col].replace({k.lower(): v for k, v in inst_mapping.items()})

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