"""
O programa que corre uma vez por dia.

Faz sempre as mesmas três coisas:
  1. vai buscar os preços de cada empresa
  2. grava o preço de hoje em dados/precos.csv
  3. pergunta a cada agente o que faria, e grava a resposta em dados/decisoes.csv

Não avalia se os agentes acertaram. Isso calcula-se depois, a partir destes
dois ficheiros -- o resultado de uma decisão é sempre derivado dos preços que
vieram a seguir, nunca escrito à mão.

Correr:
    python correr_diario.py              # a sério
    python correr_diario.py --simulado   # com dados falsos, para testar
"""

import csv
import os
import sys

import config
from agentes import AGENTES
from agentes.base import calcular_stop_e_alvo
from fonte_dados import buscar_historico

COLUNAS_PRECOS = ["data", "ticker", "fecho", "volume"]
COLUNAS_DECISOES = [
    "data", "agente", "ticker", "acao", "preco_entrada",
    "stop", "alvo", "racio", "confianca", "razao",
    "valor_aposta", "comissao", "slippage_pct",
]


def _garantir_ficheiro(caminho, colunas):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    if not os.path.exists(caminho):
        with open(caminho, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(colunas)


def _chaves_existentes(caminho, indices):
    """Lê as chaves já gravadas, para não duplicar linhas se o programa correr duas vezes."""
    if not os.path.exists(caminho):
        return set()
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.reader(f)
        next(leitor, None)
        return {tuple(linha[i] for i in indices) for linha in leitor if len(linha) > max(indices)}


def _acrescentar(caminho, linha):
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(linha)


def main(simulado=False):
    _garantir_ficheiro(config.FICHEIRO_PRECOS, COLUNAS_PRECOS)
    _garantir_ficheiro(config.FICHEIRO_DECISOES, COLUNAS_DECISOES)

    precos_gravados = _chaves_existentes(config.FICHEIRO_PRECOS, [0, 1])
    decisoes_gravadas = _chaves_existentes(config.FICHEIRO_DECISOES, [0, 1, 2])

    novos_precos = 0
    novas_decisoes = 0
    falhas = 0

    for ticker in config.EMPRESAS:
        historico = buscar_historico(ticker, dias=250, simulado=simulado)
        if not historico:
            print(f"  {ticker}: SEM DADOS -- ignorado hoje")
            falhas += 1
            continue

        hoje = historico[-1]
        print(f"  {ticker}: {hoje['data']} fecho {hoje['fecho']}")

        # 1. preço
        if (hoje["data"], ticker) not in precos_gravados:
            _acrescentar(config.FICHEIRO_PRECOS,
                         [hoje["data"], ticker, hoje["fecho"], hoje["volume"]])
            novos_precos += 1

        # 2. decisões
        for agente in AGENTES:
            chave = (hoje["data"], agente.nome, ticker)
            if chave in decisoes_gravadas:
                continue

            decisao = agente.decidir(ticker, historico)
            if not decisao:
                continue

            stop, alvo = calcular_stop_e_alvo(hoje["fecho"], historico, agente.racio)
            _acrescentar(config.FICHEIRO_DECISOES, [
                hoje["data"], agente.nome, ticker, decisao["acao"],
                hoje["fecho"], stop, alvo, agente.racio,
                decisao.get("confianca", ""), decisao.get("razao", ""),
                config.VALOR_POR_APOSTA, config.COMISSAO_POR_OPERACAO,
                config.SLIPPAGE_PCT,
            ])
            novas_decisoes += 1
            print(f"      {agente.nome}: {decisao['acao']} -- {decisao['razao']}")

    print(f"\nResumo: {novos_precos} preços, {novas_decisoes} decisões, {falhas} falhas")

    # Se NENHUMA empresa deu dados, sai com erro para o GitHub Actions avisar.
    if falhas and falhas == len(config.EMPRESAS):
        print("ERRO: nenhuma empresa devolveu dados.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(simulado="--simulado" in sys.argv))
