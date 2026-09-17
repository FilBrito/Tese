import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import io
import base64
from scipy.stats import poisson

def calcular_estimativas(tsis, potencia, peso, descarte):
    """
    Função que recebe os dados do usuário:
        - tsis: Tipo de sistema
        - potencia: Potência da placa
        - peso: Peso da placa
        - descarte: percentual de descarte prematuro
    Retorna:
        - DataFrame com estimativas
        - gráfico em base64 para exibição no HTML
    """

    # ETAPA 1 e 2 – Dados históricos

    # --- Dados históricos ---
    Dados01 = {
        "Ano": ["2013","2014","2015","2016","2017","2018","2019","2020","2021","2022","2023","2024","2025"],
        "A1": [0,0,2,5,5,5,11,57,126,714,72,34,14],
        "A2": [0,0,0,0,1,9,25,49,15,19,8,18,14],
        "A3": [0,1,1,6,0,2,21,83,13,174,88,40,36],
        "A3a":[0,1,0,1,3,18,29,80,134,226,371,102,103],
        "A4": [15,13,33,90,229,692,1166,2018,2390,3512,5548,2165,1838],
        "AS": [0,0,0,1,5,10,24,68,366,491,896,1216,971],
        "B1": [151,198,1003,4911,9869,25124,85305,161480,348505,623750,521213,731157,694510],
        "B2": [12,4,21,102,738,2336,8265,17651,38519,72297,67942,71976,71927],
        "B3": [29,53,196,1075,2119,6526,24056,36563,49300,75899,69741,64552,62092],
        "B4": [0,0,1,1,2,11,82,167,93,139,201,53,53]
    }
    df01 = pd.DataFrame(Dados01)

    # --- Dados de potência MW ---
    Dados02 = {
        "Ano": Dados01["Ano"],
        "A1": [0,0,0.0088,0.05522,0.05664,0.03812,0.13352,0.68218,1.33854,9.91234,4.01811,0.54974,0.30788],
        "A2": [0,0,0,0,0.04772,0.1592,0.29197,0.54634,0.48603,0.45753,0.19804,0.26065,0.23536],
        "A3": [0,0.02599,0.0042,0.2266,0,0.09024,1.00961,3.11716,0.86485,5.1576,5.00214,2.11868,2.29554],
        "A3a": [0,0.006,0,0.0175,0.225,1.078,1.41978,3.7751,7.75842,13.06863,18.03712,5.37389,5.30501],
        "A4": [0.33175,0.23464,0.61296,2.68241,8.70187,19.22237,48.48021,95.8136,122.89701,186.45506,229.5168,109.89011,93.96852],
        "AS": [0,0,0,0.01178,0.0832,0.06697,0.21631,0.61528,4.33706,10.34971,19.24592,23.78897,20.76585],
        "B1": [0.93876,0.80164,4.15567,19.16253,47.27693,137.46064,580.31188,1022.07914,2153.01011,4103.07374,3760.74246,5218.42588,4949.1476],
        "B2": [0.12494,0.01139,0.14644,0.65454,7.45628,35.07584,143.4994,312.46892,597.07469,1039.36471,1046.67571,872.05039,828.85523],
        "B3": [0.24537,0.45585,2.24843,15.67719,35.02555,131.29371,496.30845,771.5918,971.33324,1479.5984,1553.9999,1261.68962,1170.3308],
        "B4": [0,0,0.017,0.025,0.037,0.17186,1.88952,3.6868,2.23057,3.73181,4.68423,1.07942,1.47996]
    }
    df02 = pd.DataFrame(Dados02)

    # --- Cálculos ---
    df_div = df02.drop(columns=['Ano']) / (potencia / 1_000_000)
    df_div = round(df_div,0)
    df_num = df_div[tsis]
    df_num_cum = df_num.cumsum()
    df_ton = (df_div[tsis] * peso / 1000).cumsum()
    dfdp = df_ton * (descarte/100)

    DATA = pd.DataFrame({
        'Ano': df01['Ano'],
        'Número estimado das placas': df_num,
        'Número estimado acumulado de placas': df_num_cum,
        'Peso acumulado dos módulos (ton)': df_ton,
        'Estimativa do valor máximo de descarte (ton)': dfdp
    })

    # --- Gráfico ---
    x = np.arange(len(DATA))
    fig, ax1 = plt.subplots(figsize=(12,6))
    ax1.plot(x, DATA['Número estimado acumulado de placas'], color='yellow', marker='o',
             linestyle='dashed', linewidth=2, markerfacecolor='blue', label='Número de Sistemas PV')
    ax1.set_xticks(x)
    ax1.set_xticklabels(DATA['Ano'], rotation=45)
    ax1.set_xlabel('Ano')
    ax1.set_ylabel('Número de Sistemas PV')
    ax1.yaxis.set_major_formatter(ScalarFormatter())
    ax1.ticklabel_format(style='plain', axis='y')

    ax2 = ax1.twinx()
    width = 0.35
    bar1 = ax2.bar(x - width/2, DATA['Peso acumulado dos módulos (ton)'], width, color='lightgray', alpha=0.7)
    bar2 = ax2.bar(x + width/2, DATA['Estimativa do valor máximo de descarte (ton)'], width, color='darkgray', alpha=0.9)
    ax2.set_ylabel('Peso acumulado (ton)')
    ax2.yaxis.set_major_formatter(ScalarFormatter())
    ax2.ticklabel_format(style='plain', axis='y')

    ax1.legend(loc='upper left')
    ax2.legend([bar1, bar2], ['Peso acumulado módulos', 'Descarte (valor máximo)'], loc='upper right')
    plt.tight_layout()

    # Salvar figura em base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    grafico_base64 = base64.b64encode(buf.read()).decode('utf-8')
    grafico_uri = f"data:image/png;base64,{grafico_base64}"

    return DATA, grafico_uri
