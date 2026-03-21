import os

from utils import(
    load_sns_dataset,
    standardize_all_datasets,
    add_year_month_columns
)

if __name__ == "__main__":
    print("Downloading datasets...")
    datasets = []

    # Financial data
    datasets.append(("dados_financeiros", load_sns_dataset("agregados-economico-financeiros")))

    # unseen
    datasets.append(("medicamento_hospitalar", load_sns_dataset("despesa-com-medicamentos-nos-hospitais-do-sns")))
    datasets.append(("contas_sns", load_sns_dataset("conta-do-servico-nacional-de-saude")))
    datasets.append(("divida", load_sns_dataset("divida-total-vencida-e-pagamentos")))
    
    # Productivity data
    datasets.append(("internamento_hospitalar", load_sns_dataset("atividade-de-internamento-hospitalar")))
    datasets.append(("consultas", load_sns_dataset("01_sica_evolucao-mensal-das-consultas-medicas-hospitalares")))
    datasets.append(("cirurgias", load_sns_dataset("intervencoes-cirurgicas")))
    
    df_ambulatorio = load_sns_dataset("cirurgias-em-ambulatorio")
    df_ambulatorio = df_ambulatorio.drop(columns=["cir_ambulatorio_gdh_para_procedimentos_ambulatorizaveis"], errors='ignore')
    datasets.append(("cirurgias_ambulatorio", df_ambulatorio))
    
    df_urgencia = load_sns_dataset("atendimentos-por-tipo-de-urgencia-hospitalar-link")
    df_urgencia = df_urgencia.drop(columns=["urgencia_psiquiatrica", "urgencia_obstetricia", "urgencias_pediatricas"], errors='ignore')
    datasets.append(("atendimento_urgencia", df_urgencia))

    # unseen
    datasets.append(("trabalhadores_grupo_profissional", load_sns_dataset("trabalhadores-por-grupo-profissional")))
    datasets.append(("trabalhadores_modalidade", load_sns_dataset("trabalhadores-por-modalidade-de-vinculacao")))
    datasets.append(("utentes_cuidados_primarios", load_sns_dataset("utentes-inscritos-em-cuidados-de-saude-primarios")))
    datasets.append(("acesso_consultas", load_sns_dataset("acesso-de-consultas-medicas-pela-populacao-inscrita")))


    print("\nCleaning and Standardizing datasets...")
    datasets = add_year_month_columns(datasets)
    standardize_all_datasets(datasets)


    print("\nFilling missing values...")
    for name, df in datasets:
        cols_numericas = df.select_dtypes(include=['number']).columns
        df[cols_numericas] = df[cols_numericas].fillna(0)
        
        cols_texto = df.select_dtypes(include=['object', 'string']).columns
        df[cols_texto] = df[cols_texto].fillna("Desconhecido") # talvez colocar outro nome.


    print("\nFiltering data for years between 2016 and 2025...")
    filtered_datasets = []
    for name, df in datasets:
        if "ano" in df.columns:
            df = df[(df["ano"] >= 2016) & (df["ano"] <= 2025)]
        filtered_datasets.append((name, df))
    datasets = filtered_datasets


    print("\nSaving datasets in data/processed/ ...")
    pasta_src = os.path.dirname(os.path.abspath(__file__))
    pasta_raiz = os.path.dirname(pasta_src)
    output_dir = os.path.join(pasta_raiz, "data", "processed")
    os.makedirs(output_dir, exist_ok=True)

    for name, df in datasets:
        file_path = os.path.join(output_dir, f"{name}.csv")
        df.to_csv(file_path, index=False)
        print(f"Saved: {file_path}")


    print("\nDataset processing concluded with success!")