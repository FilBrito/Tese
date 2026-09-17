import numpy as np
from scipy.stats import gmean

def calcular_sistema(A0, At, C0, CA, P0, Classe):
    """
    Calcula a produção e consumo do sistema fotovoltaico ao longo do tempo,
    degradação baseada na Classe e ponto R geométrico.
    """
    Af = A0 + 35
    t = np.arange(A0, Af) - A0  # Normaliza o tempo

    # Taxa de crescimento composta
    i = (CA / C0) ** (1 / (At - A0))

    # Degradação baseada na classe
    classes_y = {
        1: 0.008148,
        2: 0.010519,
        3: 0.007544,
        4: 0.012883,
        5: 0.057615,
        6: 0.012883
    }
    y = classes_y.get(Classe, 0.007544)

    # Ponto R geométrico baseado na classe
    classes_R = {
        1: gmean([25, 30]),
        2: gmean([15, 30]),
        3: gmean([25, 35]),
        4: gmean([10, 30]),
        5: gmean([1, 15]),
        6: gmean([10, 30])
    }
    R = classes_R.get(Classe, gmean([25, 35]))

    # Produção e consumo
    P = P0 * np.exp(-y * t)
    C = C0 * (i ** t)

    return P, C, t, Af, y, R
