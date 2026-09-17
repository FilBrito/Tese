# graficos.py
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd


def gerar_grafico(DF, A0, At, R=None, ponto_E=None, Payback=0):
    """
    Gera um gráfico 2x1 para o módulo 2:
    - Gráfico técnico: Produção x Consumo
    - Gráfico econômico: Satisfação marginal e Utilidade total

    Parâmetros:
    DF       : pd.DataFrame com colunas 'Ano', 'Produção', 'Consumo'
    A0       : Ano de instalação
    At       : Ano atual
    R        : Ponto geométrico (pode ser None)
    ponto_E  : Ano de cruzamento Produção x Consumo (pode ser None)
    Payback  : Valor de payback (anos)
    """

    DF = DF.copy()

    # Calcula Satisfação e Utilidade
    DF["Satisfação"] = DF["Produção"] - DF["Consumo"]
    DF["Utilidade"] = DF["Satisfação"].cumsum()

    t_atual = At - A0

    # Ponto A (apenas se ponto_E e R existirem)
    if ponto_E is not None and R is not None:
        ponto_A = ponto_E - Payback if ponto_E < R else R - Payback
    else:
        ponto_A = None

    # Cria figura 2x1
    fig, axs = plt.subplots(2, 1, figsize=(18, 10))

    # ------------------------
    # Gráfico 1 – Perspectiva Técnica
    # ------------------------
    axs[0].plot(DF["Ano"], DF["Produção"], label="Produção", linestyle="--", color="blue")
    axs[0].plot(DF["Ano"], DF["Consumo"], label="Consumo", color="orange")

    # Ano atual
    if not DF.empty:
        prod_atual_idx = (DF["Ano"] - t_atual).abs().idxmin()
        prod_atual = DF.loc[prod_atual_idx, "Produção"]
        axs[0].scatter(t_atual, prod_atual, color="green", s=100, label="Ano atual")

    axs[0].set_title("Perspectiva Técnica")
    axs[0].set_ylabel("Energia (kWh)")
    axs[0].set_xlim(left=0)
    axs[0].legend()
    axs[0].grid(True)

    # ------------------------
    # Gráfico 2 – Perspectiva Econômica
    # ------------------------
    if not DF.empty:
        sat_atual_idx = (DF["Ano"] - t_atual).abs().idxmin()
        sat_atual = DF.loc[sat_atual_idx, "Satisfação"]

        axs[1].plot(DF["Ano"], DF["Satisfação"], label="Utilidade Marginal", color="purple")
        axs[1].plot(DF["Ano"], DF["Utilidade"], label="Utilidade Total", color="red", linestyle="--")
        axs[1].scatter(t_atual, sat_atual, color="green", s=100, label="Ano atual")

    axs[1].axhline(0, color="black", linestyle="--", linewidth=1)
    axs[1].set_title("Perspectiva Econômica")
    axs[1].set_xlabel("Ano")
    axs[1].set_ylabel("Energia (kWh)")
    axs[1].set_xlim(left=0)
    axs[1].legend()
    axs[1].grid(True)

    # ------------------------
    # Linhas de referência (A, E, R, Ano atual)
    # ------------------------
    for ax in axs:
        y_min, y_max = ax.get_ylim()

        if R is not None:
            ax.axvline(R, color="darkred", linestyle="-.", linewidth=2.5)
            ax.text(R, y_min + 0.05*(y_max-y_min), "R", fontweight="bold")

        if ponto_E is not None:
            ax.axvline(ponto_E, color="black", linestyle="-.", linewidth=2.5)
            ax.text(ponto_E, y_min + 0.05*(y_max-y_min), "E", fontweight="bold")

        if ponto_A is not None:
            ax.axvline(ponto_A, color="olive", linestyle="-.", linewidth=2.5)
            ax.text(ponto_A, y_min + 0.05*(y_max-y_min), "A", fontweight="bold")

        # Ano atual
        ax.axvline(t_atual, color="green", linestyle="-", linewidth=1.5)
        ax.text(
            t_atual,
            y_max - 0.05*(y_max-y_min),
            "Você está aqui",
            color="green",
            fontweight="bold"
        )

    plt.tight_layout()

    # ------------------------
    # Converte figura para Base64
    # ------------------------
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    return plot_base64
