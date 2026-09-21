"""
Sazonalidade -- compra nos meses historicamente mais fortes.

TESE: há meses do ano em que as ações sobem mais, em média, e vale a pena estar
dentro nesses e fora nos outros. É a versão testável do dito "sell in May".

O QUE ELE SABE, E DE ONDE
-------------------------
Lê a tabela do sazonalidade_tabela.csv, gerada uma vez pelo
gerar_sazonalidade.py com dez anos fechados (2016-2025) e as 40 empresas
juntas. Compra se o mês de hoje estiver entre os MESES_BONS com melhor média
histórica.

NUNCA RECALCULA A TABELA. Esta é a parte que interessa: se recalculasse, a
tabela mudava à medida que chegassem dados novos e o agente passava a aprender
durante o torneio. Deixava de ser uma tese fixa a ser testada e passava a ser
um modelo a ajustar-se ao que está a acontecer -- e ninguém dava por isso, nem
sequer ao ler o código, porque a linha seria a mesma. O que garante que isso
não acontece é o agente só saber ler.

A tabela é lida uma vez e fica em memória. Se o ficheiro faltar, o agente não
decide nada e diz porquê -- não inventa uma tabela nem usa uma por omissão.

CONGELADO a partir do arranque do torneio, e o sazonalidade_tabela.csv com ele
(regra 7): mudar a tabela muda retroativamente o que ele sabia à partida.
"""

import csv
import datetime
import os

from base import Agente

FICHEIRO_TABELA = "sazonalidade_tabela.csv"

# Quantos dos doze meses contam como "dos bons".
MESES_BONS = 4

_tabela = None          # {mes: variacao_media_pct}, lida uma vez
_avisou = False


def carregar_tabela(caminho=None):
    """
    {mes: variação média} a partir do ficheiro. {} se não houver ficheiro.

    Lê do disco uma vez por corrida; das seguintes devolve o que já tem.

    O caminho por omissão é resolvido aqui dentro, e não na assinatura, para
    FICHEIRO_TABELA continuar a valer se alguém lhe mexer -- numa assinatura o
    valor ficava preso ao que a constante era quando o módulo foi importado.
    """
    global _tabela, _avisou
    if _tabela is not None:
        return _tabela
    caminho = caminho or FICHEIRO_TABELA

    if not os.path.exists(caminho):
        if not _avisou:
            print(f"AVISO: {caminho} não existe. O agente sazonalidade não "
                  f"decide nada até a tabela ser gerada "
                  f"(python gerar_sazonalidade.py).")
            _avisou = True
        _tabela = {}
        return _tabela

    tabela = {}
    with open(caminho, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            try:
                tabela[int(linha["mes"])] = float(linha["variacao_media_pct"])
            except (TypeError, ValueError, KeyError):
                continue
    _tabela = tabela
    return _tabela


def meses_escolhidos(tabela=None):
    """Os MESES_BONS meses com melhor média, do melhor para o pior."""
    tabela = carregar_tabela() if tabela is None else tabela
    return [mes for mes, _ in
            sorted(tabela.items(), key=lambda par: -par[1])[:MESES_BONS]]


class Sazonalidade(Agente):
    nome = "sazonalidade"
    descricao = ("Compra nos 4 meses com melhor média histórica "
                 "(2016-2025, 40 empresas juntas)")
    racio = 3.0

    def decidir(self, ticker, historico):
        if not historico:
            return None

        tabela = carregar_tabela()
        if not tabela:
            return None                       # sem tabela não há tese nenhuma

        bons = meses_escolhidos(tabela)
        mes = datetime.date.fromisoformat(historico[-1]["data"]).month
        if mes not in bons:
            return None

        return {
            "acao": "COMPRA",
            "razao": (f"mês {mes} está entre os {MESES_BONS} melhores "
                      f"historicamente ({tabela[mes]:+.2f}% de média)"),
            "confianca": 0.55,
        }
