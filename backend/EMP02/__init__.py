# -*- coding: utf-8 -*-
# ==================================================
# backend/EMP02/__init__.py
# Blueprint Flask — Simulador EMP/EWMP (Módulo 3)
# Registrado em /modulo_3 pelo app.py do MVP01
# ==================================================

import os, io, base64, uuid
import numpy as np
import qrcode
from flask import (Blueprint, render_template, request,
                   session, redirect, url_for, send_file)

from backend.EMP02.calculos import (
    ANOS_BASE, PREMATURO_BASE, ESPERADO_BASE,
    CRITERIOS, ESCALA,
    calcular_im,
    calcular_polinomio, projetar_valores,
    gerar_cenarios_emp, converter_para_ewmp,
    plotar_interpolacao, plotar_multiplos_cenarios,
    figura_para_base64,
    exportar_projecoes, exportar_cenarios,
)

# --------------------------------------------------
# Blueprint — prefixo /modulo_3 definido no app.py
# --------------------------------------------------
modulo_3_bp = Blueprint("modulo_3", __name__)

# Pasta de saída dos Excel — relativa à raiz do projeto MVP01
_HERE       = os.path.dirname(os.path.abspath(__file__))  # backend/EMP02/
_ROOT       = os.path.dirname(os.path.dirname(_HERE))      # raiz MVP01/
PASTA_SAIDA = os.path.join(_ROOT, "static", "outputs", "modulo_3")

QR_TEXTO  = "https://npai.com.br/"
GRAU      = 4
ANO_FINAL = 2050
LETRAS    = ["A", "B", "C", "D", "E"]

# Prefixo das chaves de sessão para não conflitar com outros módulos
_SK_NUM      = "emp02_num_cenarios"
_SK_CENARIOS = "emp02_cenarios"


# --------------------------------------------------
# TELA 0 — Início: escolha do número de cenários
# --------------------------------------------------

@modulo_3_bp.route("/", methods=["GET", "POST"])
def inicio():
    if request.method == "POST":
        num = int(request.form.get("num_cenarios", 1))
        session[_SK_NUM]      = num
        session[_SK_CENARIOS] = {}
        return redirect(url_for("modulo_3.cenario", letra="A"))
    return render_template("modulo_3/inicio.html")


# --------------------------------------------------
# TELA 1..N — Avaliação multicritério por cenário
# --------------------------------------------------

@modulo_3_bp.route("/cenario/<letra>", methods=["GET", "POST"])
def cenario(letra):
    num_cenarios = session.get(_SK_NUM)
    if not num_cenarios:
        return redirect(url_for("modulo_3.inicio"))

    letras_ativas = LETRAS[:num_cenarios]
    if letra not in letras_ativas:
        return redirect(url_for("modulo_3.inicio"))

    idx_atual = letras_ativas.index(letra)
    is_last   = idx_atual == len(letras_ativas) - 1
    erro      = None

    if request.method == "POST":
        try:
            scores_reuso = []
            for i in range(1, len(CRITERIOS) + 1):
                val = request.form.get(f"reuso_{i}", "").strip()
                if not val:
                    raise ValueError(f"Responda o Critério {i} de Reuso.")
                scores_reuso.append(int(val))

            fc_reuso_raw = request.form.get("fc_reuso", "").strip()
            if not fc_reuso_raw:
                raise ValueError("Informe o Fator de Correção de Reuso.")
            fc_reuso = float(fc_reuso_raw) / 100
            if not 0 <= fc_reuso <= 1:
                raise ValueError("O Fator de Correção de Reuso deve estar entre 0 e 100%.")

            scores_reciclagem = []
            for i in range(1, len(CRITERIOS) + 1):
                val = request.form.get(f"reciclagem_{i}", "").strip()
                if not val:
                    raise ValueError(f"Responda o Critério {i} de Reciclagem.")
                scores_reciclagem.append(int(val))

            fc_reciclagem_raw = request.form.get("fc_reciclagem", "").strip()
            if not fc_reciclagem_raw:
                raise ValueError("Informe o Fator de Correção de Reciclagem.")
            fc_reciclagem = float(fc_reciclagem_raw) / 100
            if not 0 <= fc_reciclagem <= 1:
                raise ValueError("O Fator de Correção de Reciclagem deve estar entre 0 e 100%.")

            im_reuso      = calcular_im(scores_reuso,      fc_reuso)
            im_reciclagem = calcular_im(scores_reciclagem, fc_reciclagem)

            cenarios = session.get(_SK_CENARIOS, {})
            cenarios[letra] = {
                "im_reuso":          im_reuso,
                "im_reciclagem":     im_reciclagem,
                "scores_reuso":      scores_reuso,
                "scores_reciclagem": scores_reciclagem,
                "fc_reuso":          round(fc_reuso * 100, 2),
                "fc_reciclagem":     round(fc_reciclagem * 100, 2),
            }
            session[_SK_CENARIOS] = cenarios
            session.modified      = True

            if is_last:
                return redirect(url_for("modulo_3.resultados"))
            return redirect(url_for("modulo_3.cenario",
                                    letra=letras_ativas[idx_atual + 1]))

        except Exception as e:
            erro = str(e)

    return render_template(
        "modulo_3/cenario.html",
        letra         = letra,
        criterios     = CRITERIOS,
        escala        = ESCALA,
        erro          = erro,
        idx_atual     = idx_atual,
        total         = len(letras_ativas),
        is_last       = is_last,
        letras_ativas = letras_ativas,
    )


# --------------------------------------------------
# TELA FINAL — Resultados EMP / EWMP
# --------------------------------------------------

@modulo_3_bp.route("/resultados")
def resultados():
    cenarios_session = session.get(_SK_CENARIOS, {})
    if not cenarios_session:
        return redirect(url_for("modulo_3.inicio"))

    erro = None
    ctx  = {}

    try:
        anos_interp      = np.arange(2016, ANO_FINAL + 1)
        interp_prematuro = calcular_polinomio(ANOS_BASE, PREMATURO_BASE, GRAU)
        interp_esperado  = calcular_polinomio(ANOS_BASE, ESPERADO_BASE,  GRAU)
        prematuro_proj   = projetar_valores(interp_prematuro["polinomio"], anos_interp)
        esperado_proj    = projetar_valores(interp_esperado["polinomio"],  anos_interp)
        total_proj       = prematuro_proj + esperado_proj
        equacao          = interp_prematuro["equacao"]
        r2               = interp_prematuro["r2"]

        taxas_reuso      = {l.lower(): d["im_reuso"]     for l, d in cenarios_session.items()}
        taxas_reciclagem = {l.lower(): d["im_reciclagem"] for l, d in cenarios_session.items()}

        cenarios_emp_base = gerar_cenarios_emp(
            PREMATURO_BASE, ESPERADO_BASE, taxas_reuso, taxas_reciclagem
        )
        cenarios_emp_proj = {}
        for nome, valores in cenarios_emp_base.items():
            pol = calcular_polinomio(ANOS_BASE, valores, GRAU)["polinomio"]
            cenarios_emp_proj[nome] = projetar_valores(pol, anos_interp)

        cenarios_ewmp_proj = converter_para_ewmp(cenarios_emp_proj, total_proj)

        grafico_interpolacao = figura_para_base64(plotar_interpolacao(
            ANOS_BASE, PREMATURO_BASE, anos_interp, prematuro_proj,
            titulo="Interpolação Polinomial - Resíduos Prematuros",
            equacao=equacao, r2=r2,
        ))
        grafico_emp = figura_para_base64(plotar_multiplos_cenarios(
            anos_interp, cenarios_emp_proj,
            titulo="Comparação entre Cenários EMP",
            ylabel="Toneladas de resíduos não tratados",
        ))
        grafico_ewmp = figura_para_base64(plotar_multiplos_cenarios(
            anos_interp, cenarios_ewmp_proj,
            titulo="Comparação entre Cenários EWMP",
            ylabel="Resíduos não tratados [%]",
        ))

        tabela_resultados = [
            {"ano": int(a), "prematuro": round(p, 2),
             "esperado": round(e, 2), "total": round(t, 2)}
            for a, p, e, t in zip(anos_interp, prematuro_proj, esperado_proj, total_proj)
        ]

        os.makedirs(PASTA_SAIDA, exist_ok=True)
        sim_id = uuid.uuid4().hex[:8]

        exportar_projecoes(
            anos=anos_interp, prematuro_proj=prematuro_proj,
            esperado_proj=esperado_proj, total_proj=total_proj,
            equacao=equacao, r2=r2, grau=GRAU,
            coeficientes=interp_prematuro["coeficientes"],
            caminho_arquivo=os.path.join(PASTA_SAIDA, f"{sim_id}_projecoes.xlsx"),
        )
        exportar_cenarios(cenarios_emp_proj,  anos_interp,
                          os.path.join(PASTA_SAIDA, f"{sim_id}_cenarios_emp.xlsx"))
        exportar_cenarios(cenarios_ewmp_proj, anos_interp,
                          os.path.join(PASTA_SAIDA, f"{sim_id}_cenarios_ewmp.xlsx"))

        qr     = qrcode.make(QR_TEXTO)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        resumo_im = [
            {
                "letra":         letra,
                "im_reuso":      round(dados["im_reuso"] * 100, 2),
                "fc_reuso":      dados["fc_reuso"],
                "im_reciclagem": round(dados["im_reciclagem"] * 100, 2),
                "fc_reciclagem": dados["fc_reciclagem"],
            }
            for letra, dados in cenarios_session.items()
        ]

        ctx = dict(
            grafico_interpolacao = grafico_interpolacao,
            grafico_emp          = grafico_emp,
            grafico_ewmp         = grafico_ewmp,
            tabela_resultados    = tabela_resultados,
            equacao              = equacao,
            r2                   = r2,
            sim_id               = sim_id,
            qr_base64            = qr_base64,
            qr_texto             = QR_TEXTO,
            resumo_im            = resumo_im,
        )

    except Exception as e:
        erro = str(e)

    return render_template("modulo_3/resultados.html", erro=erro, **ctx)


# --------------------------------------------------
# Download dos Excel gerados
# --------------------------------------------------

@modulo_3_bp.route("/download/<tipo>/<sim_id>")
def download(tipo, sim_id):
    nomes = {
        "projecoes": f"{sim_id}_projecoes.xlsx",
        "emp":       f"{sim_id}_cenarios_emp.xlsx",
        "ewmp":      f"{sim_id}_cenarios_ewmp.xlsx",
    }
    if tipo not in nomes:
        return "Tipo de download inválido.", 404
    caminho = os.path.join(PASTA_SAIDA, nomes[tipo])
    if os.path.exists(caminho):
        return send_file(caminho, as_attachment=True)
    return "Arquivo ainda não foi gerado.", 404


# --------------------------------------------------
# Reiniciar apenas as chaves do módulo 3 na sessão
# --------------------------------------------------

@modulo_3_bp.route("/reiniciar")
def reiniciar():
    session.pop(_SK_NUM,      None)
    session.pop(_SK_CENARIOS, None)
    return redirect(url_for("modulo_3.inicio"))
