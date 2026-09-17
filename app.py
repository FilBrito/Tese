# -*- coding: utf-8 -*-
# ==================================================
# app.py  —  MVP01
# ==================================================

import io
import base64

import pandas as pd
import qrcode
from flask import Flask, render_template, request, send_file

from backend.estimador_ewaste import e_waste as ew
from backend.painel_decisao import calculos, cruzamento, graficos
from backend.EMP02 import modulo_3_bp

app = Flask(__name__)
app.secret_key = "mvp01-dev-key-2026"  # altere em produção

# Registra o Blueprint do EMP02 sob /modulo_3
app.register_blueprint(modulo_3_bp, url_prefix="/modulo_3")


# ==================================================
# TELA INICIAL
# ==================================================

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# ==================================================
# MÓDULO 1 — Painel de Apoio à Decisão Fotovoltaica
# ==================================================

ultimo_resultado_mod2  = None
ultimo_dados_grafico   = None

@app.route("/modulo_1", methods=["GET", "POST"])
def modulo_1():
    global ultimo_resultado_mod2, ultimo_dados_grafico

    resultado       = []
    grafico         = None
    estrategia      = None
    cenario         = None
    descricao_classe = None
    qr_base64       = None
    erro            = None

    if request.method == "POST":
        try:
            A0      = int(request.form["Ano_instalacao"])
            At      = int(request.form["Ano_atual"])
            C0      = float(request.form["Consumo_inicial_anual"])
            CA      = float(request.form["Consumo_atual_anual"])
            PNP     = float(request.form["Potencia_Nominal_Placa"])
            QP      = int(request.form["Quantidade_Placa"])
            Payback = float(request.form["Payback"])
            Classe  = int(request.form["Classe"])

            P0 = QP * 5.8 * 365 * PNP / 1000

            P, C, t, Af, y, R = calculos.calcular_sistema(A0, At, C0, CA, P0, Classe)

            df_series          = pd.DataFrame({"Ano": t, "Produção": P, "Consumo": C})
            ultimo_dados_grafico = df_series.copy()

            df_resultados, ano_cruzamento, t_cruzamento, estrategia, status = \
                cruzamento.detectar_cruzamento(P, C, t, y, R, Payback, A0)
            resultado = df_resultados.to_dict(orient="records")

            t_atual = At - A0
            if R is not None and t_cruzamento is not None:
                ponto_A = t_cruzamento - Payback if t_cruzamento < R else R - Payback
            else:
                ponto_A = None

            if ponto_A is not None:
                if t_atual <= ponto_A:
                    cenario = "Ce1 – Alta satisfação com o sistema: Momento em que ocorre excesso de energia, pois a produção de eletricidade supera o consumo, embora a capacidade de geração diminua gradualmente devido à degradação dos módulos fotovoltaicos. Ou seja, não há justificativa econômica para alterar o sistema de geração."
                elif t_cruzamento is not None and t_atual <= t_cruzamento:
                    cenario = "Ce2 – Satisfação próxima da insatisfação: Momento em que se deve prestar atenção, pois a diferença entre produção e consumo vai diminuindo progressivamente até que o sistema atinja o ponto de equilíbrio, sinalizando o início da insatisfação. Ou seja, neste intervalo o pode haver alguma preocupação ou sinalização para alterar o sistema de geração."
                elif t_atual <= R if R is not None else False:
                    cenario = "Ce3 – Insatisfação com a produção: Momento em que ocorre o déficit de energia, pois o consumo de eletricidade supera a produção. Nesse ponto, não há mais excedente de geração disponível, o qual pode fazer ele perder os benéficos gerados como voltar a dependência do fornecimento externo de eletricidade. O que pode contribuir para alterar o sistema de geração. Neste contexto pode haver o reuso, a reciclagem ou o descarte de parte dos componentes do sistema."
                else:
                    cenario = "Ce4 – Sistema sem viabilidade de reuso: Momento em que ocorre o déficit de energia, pois a produção permanece abaixo do consumo, o qual pode fazer ele perder os benéficos gerados como voltar a dependência do fornecimento externo de eletricidade. O que pode contribuir para alterar o sistema de geração. Contudo, parte dos equipamentos atingiu o limite técnico do fim de vida útil, convencionalmente definido como 80% de sua capacidade original de geração, de acordo com as diretrizes do NREL. Nesta fase, o módulo não é mais considerado adequado para reutilização e, portanto, a gestão do fim da vida útil deve se concentrar em caminhos alternativos, como a reciclagem ou o descarte final."
            else:
                cenario = "Ce4 – Sistema sem viabilidade de reuso"

            descricao_classe = f"Classe {Classe}"

            grafico = graficos.gerar_grafico(
                df_series, A0=A0, At=At, R=R,
                ponto_E=t_cruzamento, Payback=Payback,
            )

            qr = qrcode.QRCode(box_size=5, border=1)
            qr.add_data("https://doi.org/10.3390/cleantechnol8050141")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qr_base64 = base64.b64encode(buf.read()).decode("utf-8")

            ultimo_resultado_mod2 = df_resultados

        except Exception as e:
            erro = f"Erro módulo 1: {e}"
            print(erro)

    return render_template(
        "modulo_2.html",
        resultado        = resultado,
        grafico          = grafico,
        estrategia       = estrategia,
        cenario          = cenario,
        descricao_classe = descricao_classe,
        qr_base64        = qr_base64,
        erro             = erro,
    )


@app.route("/modulo_2/download")
def modulo_1_download():
    global ultimo_resultado_mod2
    if ultimo_resultado_mod2 is None:
        return "Nenhum dado disponível para download."
    try:
        output = io.BytesIO()
        ultimo_resultado_mod2.to_excel(output, index=False)
        output.seek(0)
        return send_file(output,
                         download_name="dataset.result.xlsx",
                         as_attachment=True,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return f"Erro ao gerar Excel: {e}"


@app.route("/modulo_1/download_grafico")
def modulo_1_download_grafico():
    global ultimo_dados_grafico
    if ultimo_dados_grafico is None:
        return "Nenhum dado do gráfico disponível para download."
    try:
        output = io.BytesIO()
        ultimo_dados_grafico.to_excel(output, index=False)
        output.seek(0)
        return send_file(output,
                         download_name="dataset.graphic.xlsx",
                         as_attachment=True,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return f"Erro ao gerar Excel dos dados do gráfico: {e}"


# ==================================================
# MÓDULO 2 — Estimador de Resíduos E-waste
# ==================================================

ultima_tabela    = None
ultimo_grafico   = None
dados_anteriores = {}
ultimo_descarte  = None


@app.route("/modulo_2", methods=["GET", "POST"])
def modulo_2():
    global ultima_tabela, ultimo_grafico, dados_anteriores, ultimo_descarte
    erro    = None
    etapa   = 1
    tabela  = grafico = None
    tsis    = potencia = peso = descarte = None

    if request.method == "POST":
        tsis     = request.form.get("tsis")
        potencia = float(request.form.get("potencia", 0))
        peso     = float(request.form.get("peso", 0))

        if "descarte" in request.form:
            etapa           = 2
            descarte_input  = request.form.get("descarte")
            try:
                descarte = float(descarte_input) if descarte_input else 0.0
            except ValueError:
                erro     = "Informe um número válido para o percentual de descarte."
                descarte = 0.0
        else:
            etapa    = 2
            descarte = 0.0

        try:
            tabela, grafico = ew.calcular_estimativas(tsis, potencia, peso, descarte)
            ultima_tabela   = tabela
            ultimo_grafico  = grafico
            ultimo_descarte = descarte
            dados_anteriores = {"tsis": tsis, "potencia": potencia, "peso": peso}
        except Exception as e:
            erro = f"Erro ao calcular estimativas: {str(e)}"

    if tabela is None and ultima_tabela is not None:
        tabela  = ultima_tabela
        grafico = ultimo_grafico
        if ultimo_descarte is not None:
            descarte = ultimo_descarte
        tsis     = dados_anteriores.get("tsis")
        potencia = dados_anteriores.get("potencia")
        peso     = dados_anteriores.get("peso")

    return render_template(
        "modulo_1.html",          # template original mantido
        erro     = erro,
        etapa    = etapa,
        tabela   = tabela,
        grafico  = grafico,
        tsis     = tsis,
        potencia = potencia,
        peso     = peso,
        descarte = descarte,
    )


@app.route("/modulo_2/download")
def modulo_2_download():
    global ultima_tabela
    if ultima_tabela is None or ultima_tabela.empty:
        return "Nenhum dado disponível para download."
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            ultima_tabela.to_excel(writer, index=False)
        output.seek(0)
        return send_file(output,
                         download_name="ewaste_dataset.xlsx",
                         as_attachment=True,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return f"Erro ao gerar Excel: {str(e)}"


# ==================================================
# MÓDULO 4 — Em construção
# ==================================================

@app.route("/modulo_4")
def modulo_4():
    return render_template("under_construction.html")


# ==========================================================
# EXECUÇÃO
# ==========================================================
if __name__ == "__main__":
    import os

    # O Render define a porta automaticamente através da variável PORT.
    # Se estiver rodando local no PyCharm, ele mantém a sua porta 5005.
    port = int(os.environ.get("PORT", 5100))

    # Em produção (Render), desativamos o debug e permitimos conexões externas (0.0.0.0)
    if "PORT" in os.environ:
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        app.run(port=port, debug=True)
