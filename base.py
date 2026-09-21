"""
Base comum a todos os agentes.

REGRA DE OURO: depois do arranque oficial do torneio, o ficheiro de um agente
NÃO se altera. Corrige-se o que está avariado; não se muda o que ele pensa.
Se tiveres uma ideia nova, cria um agente NOVO -- não modifiques um que já
está a correr.
"""

import statistics


class Agente:
    """Um agente = uma tese fixa sobre como o mercado funciona."""

    nome = "sem-nome"
    descricao = ""
    racio = 3.0          # alvo = racio x stop. 3.0 => precisa de acertar >25%

    def decidir(self, ticker, historico):
        """
        historico: lista de dicionários {data, fecho, volume}, o último é hoje.

        Devolve None (não faz nada) ou um dicionário:
            {"acao": "COMPRA", "razao": "...", "confianca": 0.6}

        O stop e o alvo são calculados automaticamente a partir do rácio,
        por isso o agente não precisa de os devolver.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Ferramentas que os agentes podem usar
# ---------------------------------------------------------------------------

def media_movel(historico, dias):
    """Média dos fechos dos últimos N dias. None se não houver dados que cheguem."""
    if len(historico) < dias:
        return None
    return sum(linha["fecho"] for linha in historico[-dias:]) / dias


def volatilidade_diaria(historico, dias=20):
    """
    Desvio-padrão das variações diárias, em percentagem.

    Serve para dimensionar o stop à ação: 100 euros de stop numa ação calma
    e numa ação nervosa são coisas completamente diferentes.
    """
    if len(historico) < dias + 1:
        return None
    variacoes = []
    for i in range(len(historico) - dias, len(historico)):
        anterior = historico[i - 1]["fecho"]
        atual = historico[i]["fecho"]
        if anterior:
            variacoes.append((atual - anterior) / anterior)
    if len(variacoes) < 2:
        return None
    return statistics.stdev(variacoes)


# Limites para a distância do stop, em percentagem do preço.
# Sem o mínimo, uma ação muito calma dava um stop colado ao preço, disparado
# na primeira oscilação. Sem o máximo, um dia de pânico dava um stop absurdo.
#
# O máximo subiu de 10% para 15% a 21 de setembro de 2026, antes do arranque.
# Com 10%, as ações mais nervosas ficavam com o stop cortado muito abaixo dos
# 2 desvios-padrão que a regra manda -- na MRNA o stop ficava DENTRO de um
# movimento normal de um dia, e fechava quase sempre de imediato. Isso não
# afetava os agentes por igual: quem comprasse mais essas ações apanhava mais
# perdas, e o controlo-sempre-compra, que compra tudo, era o mais penalizado.
# Baixava artificialmente a barra que os agentes têm de bater. Ver o README.
STOP_MINIMO_PCT = 0.015     # 1,5%
STOP_MAXIMO_PCT = 0.15      # 15%


def calcular_stop_e_alvo(preco, historico, racio):
    """
    Stop a 2 desvios-padrão diários abaixo do preço (o suficiente para não ser
    apanhado pelo ruído normal), alvo a 'racio' vezes essa distância acima.

    A distância é sempre mantida entre STOP_MINIMO_PCT e STOP_MAXIMO_PCT.
    Se não houver volatilidade calculável, usa 3%.
    """
    vol = volatilidade_diaria(historico)
    fracao = 2 * vol if vol else 0.03
    fracao = max(STOP_MINIMO_PCT, min(fracao, STOP_MAXIMO_PCT))
    distancia = preco * fracao
    return round(preco - distancia, 4), round(preco + distancia * racio, 4)
