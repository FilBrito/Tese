# ==========================================================
# BACKEND - MÓDULO 3 | REUSO DE MÓDULOS FV
# ==========================================================

import numpy as np
import pandas as pd
from scipy.stats import gmean
from math import ceil

# ==========================================================
# DADOS FIXOS
# ==========================================================

# Consumo mensal inicial por classe social [kWh]
CONSUMOS_SOCIAIS = {
    "A": 1535.70,
    "B1": 847.80,
    "B2": 576.75,
    "C1": 391.35,
    "C2": 217.35,
    "D/E": 115.13
}

# Classes / tipos de placas (degradação)
CLASSES_PLACAS = {
    1: {"nome": "III-V Multijunction Cells", "y": 0.008148, "Y": 0.000679, "R": gmean([25, 30])},
    2: {"nome": "Single Junction", "y": 0.010519, "Y": 0.000877, "R": gmean([15, 30])},
    3: {"nome": "Crystalline Si Cells", "y": 0.007544, "Y": 0.000629, "R": gmean([25, 35])},
    4: {"nome": "Thin-Film Technologies", "y": 0.012883, "Y": 0.001074, "R": gmean([10, 30])},
    5: {"nome": "Emerging PV", "y": 0.057615, "Y": 0.004801, "R": gmean([1, 15])},
    6: {"nome": "Hybrid Tandems", "y": 0.012883, "Y": 0.001074, "R": gmean([10, 30])}
}

# Incremento esperado (fixo conforme definido)
INCREMENTO_ESPERADO = 0.25
LIMITE_STATUS = 0.8

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================

def detectar_cruzamento_continuo(producao, consumo, eixo):
    for i in range(1, len(producao)):
        if producao[i-1] > consumo[i-1] and producao[i] <= consumo[i]:
            frac = (producao[i-1] - consumo[i-1]) / (
                (producao[i-1] - consumo[i-1]) - (producao[i] - consumo[i])
            )
            return eixo[i-1] + frac * (eixo[i] - eixo[i-1])
    return None


def calcular_status(Y, tempo_meses):
    return np.exp(-Y * tempo_meses)


# ==========================================================
# 1ª VIDA
# ==========================================================

def primeira_vida(inputs):
    A0 = inputs["ano_instalacao"]
    At = inputs["ano_atual"]
    C0 = inputs["consumo_inicial"]
    CA = inputs["consumo_atual"]
    Payback = inputs["payback"]
    PN_total = inputs["potencia_total"]  # kWh/ano
    classe = inputs["classe_placa"]

    classe_dados = CLASSES_PLACAS[classe]
    y = classe_dados["y"]
    Y = classe_dados["Y"]
    R = classe_dados["R"]

    anos = np.arange(A0, A0 + 35)
    t = anos - A0

    taxa_crescimento = (CA / C0) ** (1 / (At - A0))

    producao = PN_total * np.exp(-y * t)
    consumo = C0 * (taxa_crescimento ** t)

    ano_cruz = detectar_cruzamento_continuo(producao, consumo, anos)

    if ano_cruz:
        idade = ano_cruz - A0
        status = np.exp(-y * idade)
    else:
        idade = None
        status = None

    tabela = pd.DataFrame([{
        "Ano do Cruzamento": round(ano_cruz, 2) if ano_cruz else "Nunca",
        "Mês do Cruzamento": round(idade * 12, 2) if idade else "-",
        "Idade do Sistema (anos)": round(idade, 2) if idade else "-",
        "Produção no Cruzamento [kWh]": round(PN_total * np.exp(-y * idade), 2) if idade else "-",
        "Desempenho Estimado [%]": round(status * 100, 2) if status else "-"
    }])

    return {
        "vida": 1,
        "classe_placa": classe,
        "Y": Y,
        "R": R,
        "status_final": status,
        "tabela_resumo": tabela,
        "serie": {
            "anos": t,
            "producao": producao,
            "consumo": consumo
        },
        "mes_fim": int(idade * 12) if idade else None
    }


# ==========================================================
# 2ª VIDA
# ==========================================================

def segunda_vida(vida1, mes_inicio, taxa_crescimento):
    Y = vida1["Y"]
    PN_total = vida1["serie"]["producao"][0]
    energia_modulo = PN_total / 8

    T = np.arange(0, 600)
    resultados = []

    for classe, consumo_base in CONSUMOS_SOCIAIS.items():
        consumo = np.full_like(T, np.nan, dtype=float)
        producao = np.full_like(T, np.nan, dtype=float)

        consumo[mes_inicio:] = consumo_base * (taxa_crescimento ** T[mes_inicio:])
        producao[mes_inicio:] = energia_modulo * 8 * np.exp(-Y * T[mes_inicio:])

        mes_cruz = detectar_cruzamento_continuo(
            producao[mes_inicio:], consumo[mes_inicio:], T[mes_inicio:]
        )

        if mes_cruz:
            status = calcular_status(Y, mes_cruz)
        else:
            status = None

        resultados.append({
            "Classe Social": classe,
            "Ano do Cruzamento": round(mes_cruz / 12, 2) if mes_cruz else "Nunca",
            "Mês do Cruzamento": round(mes_cruz, 2) if mes_cruz else "-",
            "Idade do Sistema (anos)": round(mes_cruz / 12, 2) if mes_cruz else "-",
            "Produção no Cruzamento [kWh]": round(
                energia_modulo * 8 * np.exp(-Y * mes_cruz), 2
            ) if mes_cruz else "-",
            "Desempenho Estimado [%]": round(status * 100, 2) if status else "-"
        })

    tabela = pd.DataFrame(resultados)

    return {
        "vida": 2,
        "tabela_resumo": tabela,
        "serie": {"T": T},
        "mes_fim": tabela["Mês do Cruzamento"].replace("-", np.inf).astype(float).min()
    }


# ==========================================================
# 3ª VIDA EM DIANTE
# ==========================================================

def vidas_multiplas(vida2, classe_escolhida, mes_inicio, taxa_crescimento, Y):
    vidas = []
    vida_atual = 3
    mes_uso = mes_inicio

    while calcular_status(Y, mes_uso) >= LIMITE_STATUS:
        resultados = []

        for classe, consumo_base in CONSUMOS_SOCIAIS.items():
            consumo = consumo_base * (taxa_crescimento ** mes_uso)
            producao = consumo * (1 + INCREMENTO_ESPERADO)

            mes_cruz = mes_uso
            while producao >= consumo:
                mes_cruz += 1
                producao *= np.exp(-Y)
                consumo *= taxa_crescimento

            status = calcular_status(Y, mes_cruz)

            resultados.append({
                "Classe Social": classe,
                "Ano do Cruzamento": round(mes_cruz / 12, 2),
                "Mês do Cruzamento": mes_cruz,
                "Idade do Sistema (anos)": round(mes_cruz / 12, 2),
                "Produção no Cruzamento [kWh]": round(producao, 2),
                "Desempenho Estimado [%]": round(status * 100, 2)
            })

        tabela = pd.DataFrame(resultados)

        vidas.append({
            "vida": vida_atual,
            "opcao_vida_anterior": classe_escolhida,
            "tabela_resumo": tabela
        })

        mes_uso = tabela["Mês do Cruzamento"].min()
        vida_atual += 1

    return vidas
