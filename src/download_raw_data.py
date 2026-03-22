import os
from utils import load_sns_dataset

if __name__ == "__main__":
    print("Downloading datasets to data/raw...")
    
    datasets_info = [
        ("dados_financeiros", "agregados-economico-financeiros"),
        ("medicamento_hospitalar", "despesa-com-medicamentos-nos-hospitais-do-sns"),
        ("contas_sns", "conta-do-servico-nacional-de-saude"),
        ("divida", "divida-total-vencida-e-pagamentos"),
        ("internamento_hospitalar", "atividade-de-internamento-hospitalar"),
        ("consultas", "01_sica_evolucao-mensal-das-consultas-medicas-hospitalares"),
        ("cirurgias", "intervencoes-cirurgicas"),
        ("cirurgias_ambulatorio", "cirurgias-em-ambulatorio"),
        ("atendimento_urgencia", "atendimentos-por-tipo-de-urgencia-hospitalar-link"),
        ("trabalhadores_grupo_profissional", "trabalhadores-por-grupo-profissional"),
        ("trabalhadores_modalidade", "trabalhadores-por-modalidade-de-vinculacao"),
        ("utentes_cuidados_primarios", "utentes-inscritos-em-cuidados-de-saude-primarios"),
        ("acesso_consultas", "acesso-de-consultas-medicas-pela-populacao-inscrita"),
    ]

    src_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(src_dir)
    output_dir = os.path.join(root_dir, "data", "raw")
    os.makedirs(output_dir, exist_ok=True)

    for name, endpoint in datasets_info:
        df = load_sns_dataset(endpoint)
        file_path = os.path.join(output_dir, f"{name}.csv")
        df.to_csv(file_path, index=False)
        print(f"Saved: {file_path}")

    print("\nAll raw datasets downloaded successfully!")
