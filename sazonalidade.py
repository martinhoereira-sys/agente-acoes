"""
Sazonalidade -- compra nos meses historicamente mais fortes.

TESE: há meses do ano que são sistematicamente maus, e vale a pena estar fora
nesses. É a versão testável do dito "sell in May".

O QUE ELE SABE, E DE ONDE
-------------------------
Lê a tabela do sazonalidade_tabela.csv, gerada uma vez pelo
gerar_sazonalidade.py com dez anos fechados (2016-2025) e as 40 empresas
juntas. Compra sempre, EXCETO nos MESES_MAUS com pior média histórica.

PORQUÊ "COMPRA EXCETO" E NÃO "COMPRA NOS MELHORES"
--------------------------------------------------
A primeira versão comprava nos 4 melhores meses -- novembro, julho, janeiro e
agosto. Só que o torneio vai de 24 de outubro de 2026 a 30 de junho de 2027, e
desses quatro só novembro e janeiro lá caem dentro. O agente ficava ativo em 2
dos 8 meses, e em cada um comprava quase todas as empresas ao mesmo tempo pelo
mesmo motivo. Na prática eram duas apostas, não centenas -- e o t-teste da
regra 8 trataria as centenas como independentes e daria uma confiança que não
existe.

Virado ao contrário, fica ativo em 6 dos 8 meses e passa a ser um par
controlado com o controlo-sempre-compra: iguais em tudo menos nos meses
excluídos. A diferença entre os dois mede exatamente o valor de ficar de fora
nos meses maus.

A mudança é de calendário, não de desempenho -- está registada no README com
a data e o motivo.

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

# Quantos dos doze meses se evitam. Com a tabela atual são fevereiro,
# setembro, março e dezembro.
MESES_MAUS = 4

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


def meses_evitados(tabela=None):
    """Os MESES_MAUS meses com pior média, do pior para o menos mau."""
    tabela = carregar_tabela() if tabela is None else tabela
    return [mes for mes, _ in
            sorted(tabela.items(), key=lambda par: par[1])[:MESES_MAUS]]


class Sazonalidade(Agente):
    nome = "sazonalidade"
    descricao = ("Compra sempre, exceto nos 4 meses com pior média histórica "
                 "(2016-2025, 40 empresas juntas)")
    racio = 3.0

    def decidir(self, ticker, historico):
        if not historico:
            return None

        tabela = carregar_tabela()
        if not tabela:
            return None                       # sem tabela não há tese nenhuma

        maus = meses_evitados(tabela)
        mes = datetime.date.fromisoformat(historico[-1]["data"]).month
        if mes in maus:
            return None

        return {
            "acao": "COMPRA",
            "razao": (f"mês {mes} não está entre os {MESES_MAUS} piores "
                      f"historicamente ({tabela[mes]:+.2f}% de média)"),
            "confianca": 0.55,
        }
