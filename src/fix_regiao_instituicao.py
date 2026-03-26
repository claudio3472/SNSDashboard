"""
Script para corrigir designações de regiões de instituições no master_dataset.csv
"""

import os
import pandas as pd


def get_project_root():
    """Obtém o diretório raiz do projeto"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(current_dir)


def apply_corrections():
    """Aplica todas as correções de regiões ao master_dataset"""
    
    # Mapeamento de correções: (instituicao) -> (nova_regiao)
    corrections = {
        # Alentejo
        "Unidade Local de Saúde do Estuário do Tejo": "Lisboa e Vale do Tejo",
        "Unidade Local de Saúde da Póvoa de Varzim/Vila do Conde": "Norte",
        
        # Centro
        "Unidade Local de Saúde do Baixo Alentejo": "Alentejo",
        
        # Lisboa e Vale do Tejo
        "Unidade Local de Saúde do Baixo Mondego": "Centro",
        "Unidade Local de Saúde do Médio Ave": "Norte",
        "Unidade Local de Saúde do Nordeste": "Norte",
        
        # Norte
        "Unidade Local de Saúde da Região de Aveiro": "Centro",
        "Unidade Local de Saúde do Litoral Alentejano": "Alentejo",
        "Unidade Local de Saúde do Médio Tejo": "Lisboa e Vale do Tejo",
        "Unidade Local de Saúde do Oeste": "Lisboa e Vale do Tejo",
    }
    
    # Paths
    root_dir = get_project_root()
    input_path = os.path.join(root_dir, 'data', 'processed', 'master_dataset.csv')
    output_path = input_path  # Sobrescrever o ficheiro original
    
    # Validar ficheiro de entrada
    if not os.path.exists(input_path):
        print(f"❌ Erro: Ficheiro não encontrado em {input_path}")
        return False
    
    # Carregar dados
    print("📂 Carregando master_dataset.csv...")
    df = pd.read_csv(input_path)
    print(f"   ✓ {len(df)} registos carregados\n")
    
    # Aplicar correções
    changes_count = 0
    print("🔄 Aplicando correções...\n")
    
    for instituicao, nova_regiao in corrections.items():
        mask = df['instituicao'] == instituicao
        if mask.any():
            count = mask.sum()
            regiao_anterior = df.loc[mask, 'regiao'].iloc[0]
            df.loc[mask, 'regiao'] = nova_regiao
            changes_count += count
            print(f"✓ {instituicao}")
            print(f"  → {count} registos: {regiao_anterior} → {nova_regiao}\n")
        else:
            print(f"✗ {instituicao} - NÃO ENCONTRADA\n")
    
    # Resumo
    print(f"{'='*70}")
    print(f"Total de registos alterados: {changes_count}")
    print(f"{'='*70}\n")
    
    # Salvar ficheiro
    print(f"💾 Guardando ficheiro corrigido...")
    df.to_csv(output_path, index=False)
    print(f"   ✓ Ficheiro guardado em: {output_path}\n")
    
    return True


if __name__ == "__main__":
    apply_corrections()
