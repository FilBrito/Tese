# -*- coding: utf-8 -*-
# ==================================================
# backend/calculos.py
# Critérios, Índice de Maturidade (IM), EMP, EWMP,
# interpolação de Lagrange e exportação Excel
# ==================================================

import io
import base64

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score


# ==================================================
# Dados históricos base (Global)
# ==================================================

ANOS_BASE      = np.array([2016,   2020,    2030,     2040,      2050])
PREMATURO_BASE = np.array([206500, 750000,  6300000,  17000000,  18000000])
ESPERADO_BASE  = np.array([43500,  100000,  1700000,  15000000,  60000000])


# ==================================================
# Critérios de avaliação do Índice de Maturidade
# (pergunta_reuso → avalia IM de Reuso)
# (pergunta_reciclagem → avalia IM de Reciclagem)
# ==================================================

CRITERIOS = [
    {
        "numero": 1,
        "nome": "Governança e Regulação",
        "objetivo": "Avaliar a existência de instrumentos regulatórios e diretrizes que orientem a gestão de módulos fotovoltaicos ao fim da vida útil.",
        "pergunta_reuso": "Existe mercado secundário formal ou informal para módulos fotovoltaicos usados?",
        "pergunta_reciclagem": "Existem normas, diretrizes ou obrigações atualmente aplicáveis à destinação ou reciclagem de módulos fotovoltaicos ao fim da vida útil?",
    },
    {
        "numero": 2,
        "nome": "Responsabilidade e Monitoramento",
        "objetivo": "Avaliar mecanismos de responsabilização dos agentes e sistemas de controle da gestão dos módulos.",
        "pergunta_reuso": "Existem diretrizes, normas ou procedimentos para avaliação de módulos destinados à segunda vida?",
        "pergunta_reciclagem": "Há infraestrutura instalada para recebimento, desmontagem, separação ou processamento de módulos fotovoltaicos descartados?",
    },
    {
        "numero": 3,
        "nome": "Infraestrutura de Tratamento",
        "objetivo": "Avaliar a disponibilidade de instalações e operadores para processamento dos módulos ao fim da vida útil.",
        "pergunta_reuso": "Há protocolos de inspeção, teste, classificação ou certificação de módulos usados?",
        "pergunta_reciclagem": "Existem empresas ou operadores capazes de reciclar módulos fotovoltaicos em escala comercial ou pré-comercial?",
    },
    {
        "numero": 4,
        "nome": "Capacidade Técnica",
        "objetivo": "Avaliar a existência de procedimentos técnicos para identificar módulos aptos à segunda vida.",
        "pergunta_reuso": "Existem agentes econômicos capazes de operar triagem, recondicionamento, revenda ou reinstalação de módulos?",
        "pergunta_reciclagem": "A logística reversa atual permite coletar e transportar módulos descartados até pontos de tratamento ou reciclagem?",
    },
    {
        "numero": 5,
        "nome": "Cadeia Operacional e Logística",
        "objetivo": "Avaliar a capacidade operacional de movimentar módulos para reutilização ou reciclagem.",
        "pergunta_reuso": "Há aceitação regulatória ou institucional para a reinserção de módulos usados em aplicações secundárias?",
        "pergunta_reciclagem": "Há mecanismos de financiamento, responsabilidade compartilhada ou obrigação do produtor/importador para custear a reciclagem?",
    },
    {
        "numero": 6,
        "nome": "Mercado e Agentes Econômicos",
        "objetivo": "Avaliar a existência de agentes econômicos capazes de viabilizar as estratégias de fim de vida.",
        "pergunta_reuso": "Existem mecanismos de rastreabilidade ou responsabilidade técnica para módulos reutilizados?",
        "pergunta_reciclagem": "Os materiais recuperados possuem mercado ou destinação economicamente viável no contexto atual?",
    },
    {
        "numero": 7,
        "nome": "Viabilidade Econômica da Circularidade",
        "objetivo": "Avaliar se há condições econômicas para sustentar as estratégias de reuso e reciclagem.",
        "pergunta_reuso": "A estrutura logística permite coletar, transportar, armazenar e redistribuir módulos ainda funcionais?",
        "pergunta_reciclagem": "Existem dados, registros ou sistemas de monitoramento sobre volumes de módulos descartados e reciclados?",
    },
    {
        "numero": 8,
        "nome": "Controle e Rastreabilidade",
        "objetivo": "Avaliar a capacidade de acompanhar os fluxos dos módulos e prevenir o descarte inadequado.",
        "pergunta_reuso": "O contexto socioeconômico apresenta demanda potencial por módulos de menor custo ou menor exigência de desempenho?",
        "pergunta_reciclagem": "O descarte inadequado é controlado por fiscalização, licenciamento ou instrumentos de gestão de resíduos?",
    },
]

# Escala ordinal: apresentada do maior para o menor (mais intuitivo no formulário)
ESCALA = [
    (4, "Atendimento consolidado"),
    (3, "Atendimento avançado"),
    (2, "Atendimento parcial"),
    (1, "Atendimento incipiente"),
    (0, "Ausência do critério"),
]


# ==================================================
# Cálculo do Índice de Maturidade (IM)
# ==================================================

def calcular_im(scores, fc):
    """
    Calcula o Índice de Maturidade normalizado para uma estratégia.

    IM_j = (∑ N_ij / Q_j) × (1 / N_max) × FC_j

    scores : lista de notas (1–5), uma por critério
    fc     : fator de correção da estratégia (0–1)
    retorna: IM ∈ [0, 1]
    """
    Q     = len(scores)   # número de critérios
    N_max = 4             # valor máximo da escala
    media = sum(scores) / Q
    im    = (media / N_max) * fc
    return round(im, 4)


# ==================================================
# Interpolação polinomial
# ==================================================

def calcular_polinomio(anos, valores, grau):
    coef = np.polyfit(anos, valores, grau)
    pol  = np.poly1d(coef)
    r2   = r2_score(valores, pol(anos))

    termos  = [f"{c:.4g}x^{len(coef) - 1 - i}" for i, c in enumerate(coef)]
    equacao = " + ".join(termos).replace("+ -", "- ")

    return {"coeficientes": coef, "polinomio": pol, "equacao": equacao, "r2": r2}


def projetar_valores(polinomio, anos_futuros):
    return polinomio(anos_futuros)


# ==================================================
# Cenários EMP e EWMP (chaves dinâmicas)
# ==================================================

def gerar_cenarios_emp(prematuro, esperado, taxas_reuso, taxas_reciclagem):
    """
    taxas_reuso / taxas_reciclagem: dicts com chaves dinâmicas (ex: 'a', 'b', 'c')

    EMP_i(t) = (1 − reuso_i) × prematuro(t) + (1 − reciclagem_i) × esperado(t)
    """
    cenarios = {}
    for chave in taxas_reuso:
        reuso      = taxas_reuso[chave]
        reciclagem = taxas_reciclagem[chave]
        cenarios[f"EMP Cenário {chave.upper()}"] = (
            (1 - reuso) * prematuro + (1 - reciclagem) * esperado
        )
    return cenarios


def converter_para_ewmp(cenarios_emp, total_residuos):
    return {
        nome.replace("EMP", "EWMP"): (valores / total_residuos) * 100
        for nome, valores in cenarios_emp.items()
    }


# ==================================================
# Gráficos → base64
# ==================================================

def figura_para_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def plotar_interpolacao(anos_originais, valores_originais, anos_interp, valores_interp, titulo, equacao, r2):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(anos_originais, valores_originais, color="darkred", label="Dados originais", zorder=3)
    ax.plot(anos_interp, valores_interp, color="steelblue", label="Interpolação")
    ax.set_title(f"{titulo}\nR² = {r2:.4f}")
    ax.set_xlim(2016, 2050)
    ax.set_xlabel("Ano")
    ax.set_ylabel("Toneladas")
    ax.grid(True)
    ax.ticklabel_format(style="plain", axis="y")
    ax.legend()
    fig.tight_layout()
    return fig


def plotar_multiplos_cenarios(anos, cenarios, titulo, ylabel):
    fig, ax = plt.subplots(figsize=(10, 5))
    estilos = ["-", "-", "-"]
    for i, (nome, valores) in enumerate(cenarios.items()):
        ax.plot(anos, valores, label=nome, linestyle=estilos[i % len(estilos)], linewidth=3)
    ax.set_title(titulo)
    ax.set_xlim(2026, 2050)
    ax.set_xlabel("Ano")
    ax.set_ylabel(ylabel)
    ax.grid(True)
    ax.ticklabel_format(style="plain", axis="y")
    ax.legend()
    fig.tight_layout()
    return fig


# ==================================================
# Exportação Excel
# ==================================================

def exportar_projecoes(anos, prematuro_proj, esperado_proj, total_proj,
                       equacao, r2, grau, coeficientes, caminho_arquivo):
    df = pd.DataFrame({
        "Ano":             anos.astype(int),
        "Prematuro [t]":  prematuro_proj,
        "Esperado [t]":   esperado_proj,
        "Total [t]":      total_proj,
    })
    info = pd.DataFrame({
        "Parâmetro": ["Grau do polinômio", "Equação", "R²"],
        "Valor":     [grau, equacao, r2],
    })
    with pd.ExcelWriter(caminho_arquivo, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Projeções", index=False)
        info.to_excel(writer, sheet_name="Info do Modelo", index=False)


def exportar_cenarios(cenarios, anos, caminho_arquivo):
    df = pd.DataFrame({"Ano": anos.astype(int)})
    for nome, valores in cenarios.items():
        df[nome] = valores
    with pd.ExcelWriter(caminho_arquivo, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Cenários", index=False)
