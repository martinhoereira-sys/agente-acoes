"""
Contrarian -- o oposto do momentum.

TESE: uma ação que caiu muito abaixo da sua média tende a voltar lá. O mercado
exagera nas descidas, e quem compra no exagero apanha a correção.

É o par do momentum de propósito. Os dois não podem ter razão ao mesmo tempo, e
é isso que os torna informativos: se ambos ficarem abaixo dos controlos, a
resposta é que nenhuma das duas histórias funciona nestes dados. Ter só um dos
lados a correr daria uma resposta que parecia conclusiva e não era.

Usa o mesmo limiar de 5% para os dois lados? Não: o momentum entra a 1% acima e
este a 5% abaixo. A assimetria é deliberada -- uma ação 1% abaixo da média é
ruído, enquanto 1% acima já é uma tendência a formar-se.

CONGELADO a partir do arranque do torneio.
"""

from base import Agente, media_movel

# Quanto tem de estar abaixo da média para contar como exagero e não como ruído.
DISTANCIA_MINIMA = 0.05


class Contrarian(Agente):
    nome = "contrarian"
    descricao = "Compra quando o preço está mais de 5% abaixo da média de 50 dias"
    racio = 3.0

    def decidir(self, ticker, historico):
        if len(historico) < 51:
            return None                       # ainda não há histórico que chegue

        preco = historico[-1]["fecho"]
        media50 = media_movel(historico, 50)
        if not media50:                       # None ou zero
            return None

        if preco < media50 * (1 - DISTANCIA_MINIMA):
            distancia = (1 - preco / media50) * 100
            return {
                "acao": "COMPRA",
                "razao": f"preço {distancia:.1f}% abaixo da média de 50 dias",
                "confianca": 0.55,
            }
        return None
