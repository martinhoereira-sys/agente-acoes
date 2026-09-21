"""
Momentum -- três agentes com a mesma tese e rácios diferentes.

TESE: uma ação que vem a subir tende a continuar a subir durante algum tempo.
Não usa IA nem notícias, só o gráfico. Custo de funcionamento: zero.

Os três decidem exatamente da mesma maneira e só diferem no rácio entre o alvo
e o stop. É de propósito: com a tese fixa, a única coisa que muda é a pergunta
"qual é o rácio certo?", e no fim compara-se.

  2:1  precisa de acertar mais de 33% -- alvos mais perto, mais fáceis de tocar
  3:1  precisa de acertar mais de 25%
  5:1  precisa de acertar mais de 17% -- alvos longe, tocados muito menos vezes

CONGELADOS a partir do arranque do torneio.
"""

from base import Agente, media_movel


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


class Momentum2Para1(MomentumSimples):
    """O mesmo, com o alvo a 2 vezes a distância do stop."""

    nome = "momentum-2-1"
    descricao = "Momentum com rácio 2:1 -- alvo mais perto, precisa de acertar >33%"
    racio = 2.0


class Momentum5Para1(MomentumSimples):
    """O mesmo, com o alvo a 5 vezes a distância do stop."""

    nome = "momentum-5-1"
    descricao = "Momentum com rácio 5:1 -- alvo mais longe, precisa de acertar >17%"
    racio = 5.0
