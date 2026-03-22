import os
import pandas as pd
from utils import standardize_all_datasets, add_year_month_columns

if __name__ == "__main__":
    print("Loading raw datasets...")
    
    pasta_src = os.path.dirname(os.path.abspath(__file__))
    pasta_raiz = os.path.dirname(pasta_src)
    raw_dir = os.path.join(pasta_raiz, "data", "raw")
    processed_dir = os.path.join(pasta_raiz, "data", "processed")
    os.makedirs(processed_dir, exist_ok=True)

    datasets = []
    raw_files = [
        "dados_financeiros", "medicamento_hospitalar", "contas_sns", "divida",
        "internamento_hospitalar", "consultas", "cirurgias", "cirurgias_ambulatorio",
        "atendimento_urgencia", "trabalhadores_grupo_profissional", "trabalhadores_modalidade",
        "utentes_cuidados_primarios", "acesso_consultas"
    ]

    for name in raw_files:
        file_path = os.path.join(raw_dir, f"{name}.csv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, low_memory=False)
            
            if name == "cirurgias_ambulatorio":
                df = df.drop(columns=["cir_ambulatorio_gdh_para_procedimentos_ambulatorizaveis"], errors='ignore')
            elif name == "atendimento_urgencia":
                df = df.drop(columns=["urgencia_psiquiatrica", "urgencia_obstetricia", "urgencias_pediatricas"], errors='ignore')
            
            datasets.append((name, df))
        else:
            print(f"Warning: Raw file '{name}.csv' not found. Run download_raw.py first.")

    print("\nCleaning and Standardizing datasets...")
    datasets = add_year_month_columns(datasets)
    standardize_all_datasets(datasets)

    print("\nFilling missing values...")
    for name, df in datasets:
        cols_numericas = df.select_dtypes(include=['number']).columns
        df[cols_numericas] = df[cols_numericas].fillna(0)
        
        cols_texto = df.select_dtypes(include=['object', 'string']).columns
        df[cols_texto] = df[cols_texto].fillna("Desconhecido")

    print("\nFiltering data for years between 2016 and 2025...")
    filtered_datasets = []
    for name, df in datasets:
        if "ano" in df.columns:
            df = df[(df["ano"] >= 2016) & (df["ano"] <= 2025)]
        filtered_datasets.append((name, df))
    datasets = filtered_datasets

    print("\nSaving datasets in data/processed/ ...")
    for name, df in datasets:
        file_path = os.path.join(processed_dir, f"{name}.csv")
        df.to_csv(file_path, index=False)
        print(f"Saved: {file_path}")

    print("\nDataset processing concluded with success!")
