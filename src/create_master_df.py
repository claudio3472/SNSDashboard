import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def categorizar_instituicao(nome):
    """Categoriza o tipo de instituição com base no nome."""
    if pd.isna(nome):
        return "Desconhecido"
    
    nome_upper = str(nome).upper()
    if "UNIDADE LOCAL DE SAÚDE" in nome_upper:
        return "ULS"
    elif "CSP" in nome_upper:
        return "CSP"
    elif "HOSPITAL" in nome_upper or "CENTRO HOSPITALAR" in nome_upper:
        return "Hospital"
    elif "ONCOLOGIA" in nome_upper or "IPO" in nome_upper:
        return "IPO"
    else:
        return "Outro/SNS"

def create_master_dataset():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(src_dir)
    data_dir = os.path.join(root_dir, "data", "processed")
    
    # Mapeamento de correções de região
    corrections = {
        "Unidade Local de Saúde do Estuário do Tejo": "Lisboa e Vale do Tejo",
        "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde": "Norte",
        "Unidade Local de Saúde do Baixo Alentejo": "Alentejo",
        "Unidade Local de Saúde do Baixo Mondego": "Centro",
        "Unidade Local de Saúde do Médio Ave": "Norte",
        "Unidade Local de Saúde do Nordeste": "Norte",
        "Unidade Local de Saúde da Região de Aveiro": "Centro",
        "Unidade Local de Saúde do Litoral Alentejano": "Alentejo",
        "Unidade Local de Saúde do Médio Tejo": "Lisboa e Vale do Tejo",
        "Unidade Local de Saúde do Oeste": "Lisboa e Vale do Tejo",
        "Ação Governativa": "Serviços Centrais",
        "Administração Central do Sistema de Saúde, I.P.": "Serviços Centrais",
        "Direção Executiva do Serviço Nacional de Saúde, I.P.": "Serviços Centrais",
        "Direção-Geral da Saúde": "Serviços Centrais",
        "Infarmed - Autoridade Nacional do Medicamento e Produtos de Saúde, I.P.": "Serviços Centrais",
        "Inspeção-Geral das Atividades em Saúde": "Serviços Centrais",
        "Instituto Nacional de Emergência Médica": "Serviços Centrais",
        "Instituto Nacional de Saúde Doutor Ricardo Jorge, I.P.": "Serviços Centrais",
        "Instituto Português do Sangue e da Transplantação, I.P.": "Serviços Centrais",
        "Instituto para os Comportamentos Aditivos e as Dependências, I. P.": "Serviços Centrais",
        "Secretaria-Geral do Ministério da Saúde": "Serviços Centrais",
        "Serviços Partilhados do Ministério da Saúde, E.P.E.": "Serviços Centrais",
    }

    target_datasets = ['dados_financeiros', 'atendimento_urgencia', 'internamento_hospitalar', 'cirurgias', 'consultas', 'divida', 'contas_sns', 'medicamento_hospitalar', 'trabalhadores_grupo_profissional', 'utentes_cuidados_primarios', 'trabalhadores_modalidade', 'acesso_consultas', 'cirurgias_ambulatorio']
    master_df = None

    print(f"Reading datasets from {data_dir}...\n")
    
    for name in target_datasets:
        file_path = os.path.join(data_dir, f"{name}.csv")
        
        if os.path.exists(file_path):
            print(f"Joining: {name}.csv")
            df_temp = pd.read_csv(file_path)
            
            if 'entidade' in df_temp.columns:
                df_temp.rename(columns={'entidade': 'instituicao'}, inplace=True)
            
            # Aplicar correções de região antes do groupby e merge
            if 'instituicao' in df_temp.columns and 'regiao' in df_temp.columns:
                for instituicao, nova_regiao in corrections.items():
                    mask = df_temp['instituicao'] == instituicao
                    if mask.any():
                        df_temp.loc[mask, 'regiao'] = nova_regiao

            keys = ['regiao', 'instituicao', 'ano', 'mes']
            
            if all(k in df_temp.columns for k in keys):
                num_cols = [c for c in df_temp.select_dtypes(include=['number']).columns if c not in ['ano', 'mes']]
                
                df_agg = df_temp.groupby(keys)[num_cols].sum().reset_index()
                
                if master_df is None:
                    master_df = df_agg
                else:
                    master_df = pd.merge(master_df, df_agg, on=keys, how='outer')
        else:
            print(f"Warning: '{name}.csv' file not found. Run data_prep.py first.")

    if master_df is not None:
        num_cols_master = [c for c in master_df.columns if c not in keys]
        master_df[num_cols_master] = master_df[num_cols_master].fillna(0)
        
        # Adicionar coluna com o tipo de instituição
        print("🏷️ A criar a nova coluna 'tipo_instituicao'...")
        master_df['tipo_instituicao'] = master_df['instituicao'].apply(categorizar_instituicao)

        master_path = os.path.join(data_dir, "master_dataset.csv")
        master_df.to_csv(master_path, index=False)
        print(f"\nSuccess! Saved Master Dataset: {master_path}")
        

if __name__ == "__main__":
    create_master_dataset()
