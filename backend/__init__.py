# backend/painel_decisao/__init__.py
from .estimador_ewaste import e_waste

# Expondo os submódulos do módulo 2 (painel_decisao) para import direto
from .painel_decisao import calculos, cruzamento, graficos, exportar

# Módulo 3 (painel_reuso) pode ser exposto se quiser, mas por enquanto só __init__.py vazio
from .painel_reuso import *
