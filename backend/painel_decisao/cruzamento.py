import numpy as np
import pandas as pd

def detectar_cruzamento(P, C, t, y, R, Payback, A0):
    """
    Detecta o cruzamento entre Produção (P) e Consumo (C) e calcula:
    - ponto E (ano e idade do sistema)
    - status estimado
    - estratégia recomendada
    Retorna também um DataFrame resumido.
    """

    diferenca = P - C
    ano_cruzamento, t_cruzamento = None, None

    # Detecta o primeiro cruzamento
    for i in range(1, len(diferenca)):
        if diferenca[i-1] > 0 and diferenca[i] <= 0:
            # Interpolação linear para maior precisão
            frac = diferenca[i-1] / (diferenca[i-1] - diferenca[i])
            t_cruzamento = t[i-1] + frac * (t[i] - t[i-1])
            ano_cruzamento = A0 + t_cruzamento
            break

    # Se não houver cruzamento, define como último ano
    if t_cruzamento is None:
        t_cruzamento = t[-1]
        ano_cruzamento = A0 + t_cruzamento

    # Calcula status e estratégia
    status = np.exp(-y * t_cruzamento)  # degradação estimada no ponto E
    estrategia = "Reuso" if status >= 0.8 else "Reciclagem"
    # Produção interpolada no ponto E
    P_cruzamento = np.interp(t_cruzamento, t, P)

    # Cria DataFrame resumido
    df_resultados = pd.DataFrame({
        "Ano do Cruzamento": [ano_cruzamento],
        "Idade do Sistema (anos)": [t_cruzamento],
        "Produção no Cruzamento [kWh]": [P_cruzamento],
        "Desempenho Estimado [%]": [status * 100],
        "Estratégia Recomendada": [estrategia]
    })

    return df_resultados, ano_cruzamento, t_cruzamento, estrategia, status
