"""
Agente 1 -- Momentum simples.

TESE: uma ação que vem a subir tende a continuar a subir durante algum tempo.
É o agente da fatia fina: não usa IA nem notícias, só o gráfico.
Custo de funcionamento: zero.

CONGELADO a partir do arranque do torneio.
"""

from agentes.base import Agente, media_movel


class MomentumSimples(Agente):
    nome = "momentum-simples"
    descricao = "Compra quando o preço está acima da média de 50 dias"
    racio = 3.0

    def decidir(self, ticker, historico):
        if len(historico) < 51:
            return None                       # ainda não há histórico que chegue

        preco = historico[-1]["fecho"]
        media50 = media_movel(historico, 50)
        if media50 is None:
            return None

        # Só entra se o preço estiver claramente acima da média (>1%),
        # para não estar a entrar e sair com o preço colado à linha.
        if preco > media50 * 1.01:
            distancia = (preco / media50 - 1) * 100
            return {
                "acao": "COMPRA",
                "razao": f"preço {distancia:.1f}% acima da média de 50 dias",
                "confianca": 0.55,
            }
        return None
