"""
Lista dos agentes ativos no torneio.

Para acrescentar um agente: cria o ficheiro, importa-o aqui, junta-o à lista.
Para "desligar" um agente: NUNCA o apagues -- comenta a linha e escreve a data,
para o histórico continuar a fazer sentido.
"""

from contrarian import Contrarian
from controlos import MoedaAoAr, SempreCompra
from momentum import Momentum2Para1, Momentum5Para1, MomentumSimples
from sazonalidade import Sazonalidade

AGENTES = [
    # A mesma tese com três rácios, para responder a "qual é o rácio certo?".
    MomentumSimples(),
    Momentum2Para1(),
    Momentum5Para1(),

    # O oposto do momentum. Os dois não podem ter razão ao mesmo tempo.
    Contrarian(),

    # Lê a tabela do sazonalidade_tabela.csv; não decide nada sem ela.
    Sazonalidade(),

    # Controlos -- correm sempre, em igualdade de circunstâncias.
    SempreCompra(),
    MoedaAoAr(),
]
