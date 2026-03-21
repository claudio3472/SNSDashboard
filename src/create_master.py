import os
import pandas as pd

def create_master_dataset():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(src_dir)
    data_dir = os.path.join(root_dir, "data", "processed")
    
    target_datasets = ['dados_financeiros', 'atendimento_urgencia', 'internamento_hospitalar', 'cirurgias', 'consultas']
    master_df = None

    print(f"Reading datasets from {data_dir}...\n")
    
    for name in target_datasets:
        file_path = os.path.join(data_dir, f"{name}.csv")
        
        if os.path.exists(file_path):
            print(f"Joining: {name}.csv")
            df_temp = pd.read_csv(file_path)
            
            if 'entidade' in df_temp.columns:
                df_temp.rename(columns={'entidade': 'instituicao'}, inplace=True)
            
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
        
        master_path = os.path.join(data_dir, "master_dataset.csv")
        master_df.to_csv(master_path, index=False)
        print(f"\nSuccess! Saved Master Dataset: {master_path}")

if __name__ == "__main__":
    create_master_dataset()
