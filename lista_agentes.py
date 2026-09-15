"""
Lista dos agentes ativos no torneio.

Para acrescentar um agente: cria o ficheiro, importa-o aqui, junta-o à lista.
Para "desligar" um agente: NUNCA o apagues -- comenta a linha e escreve a data,
para o histórico continuar a fazer sentido.
"""

from controlos import MoedaAoAr, SempreCompra
from momentum import MomentumSimples

AGENTES = [
    MomentumSimples(),

    # Controlos -- correm sempre, em igualdade de circunstâncias.
    SempreCompra(),
    MoedaAoAr(),
]
