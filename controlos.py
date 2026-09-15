"""
Agentes-controlo -- os "idiotas" do torneio.

Não leem nada, não pensam nada. Existem para responderes a esta pergunta no
fim: "os meus agentes a sério são melhores do que não fazer nada?"

Se algum destes ficar no top 3 ao fim de seis meses, os resultados do torneio
são ruído e nenhum agente merece ser copiado.

NUNCA remover. NUNCA dar-lhes vantagens.
"""

import random

from agentes.base import Agente


class SempreCompra(Agente):
    nome = "controlo-sempre-compra"
    descricao = "CONTROLO: compra todos os dias, sem ler nada"
    racio = 3.0

    def decidir(self, ticker, historico):
        if len(historico) < 51:
            return None
        return {"acao": "COMPRA", "razao": "controlo: compra sempre", "confianca": 0.5}


class MoedaAoAr(Agente):
    nome = "controlo-moeda-ao-ar"
    descricao = "CONTROLO: decide à sorte, 50/50"
    racio = 3.0

    def decidir(self, ticker, historico):
        if len(historico) < 51:
            return None
        # Semente pela data + ticker: reprodutível, mas na prática aleatório.
        random.seed(f"{historico[-1]['data']}-{ticker}")
        if random.random() < 0.5:
            return {"acao": "COMPRA", "razao": "controlo: moeda ao ar", "confianca": 0.5}
        return None
