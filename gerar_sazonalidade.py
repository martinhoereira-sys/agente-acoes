"""
Gera a tabela de sazonalidade. CORRE UMA VEZ, à mão, e nunca mais.

Vai buscar os preços de 2016-01-01 a 2025-12-31 -- dez anos inteiros, todos
fechados, nenhum a meio -- e calcula a variação média de cada mês do ano com as
40 empresas JUNTAS.

PORQUÊ JUNTAS E NÃO POR EMPRESA
-------------------------------
Por empresa, cada mês tem dez observações. Dez números chegam para qualquer
mês parecer o melhor ou o pior do ano por puro acaso, e o agente ficaria a
seguir ruído com ar de padrão. Juntando as 40 empresas são cerca de 400
observações por mês. Continua a não ser muito -- os meses das mesmas 40
empresas americanas andam bastante juntos, por isso 400 observações valem
menos do que 400 observações independentes -- mas é outra ordem de grandeza.

PORQUÊ UM FICHEIRO E NÃO UMA CONTA AO VIVO
------------------------------------------
Se o agente recalculasse isto a cada corrida, a tabela mudava à medida que
chegassem dados novos e o agente passava a aprender durante o torneio. Deixava
de ser uma tese fixa a ser testada e passava a ser um modelo a ajustar-se ao
que está a acontecer -- que é precisamente o que a regra 1 proíbe, e sem se
dar por isso. Por isso a tabela é gravada uma vez e o agente só a lê.

CORRER
------
    python gerar_sazonalidade.py

Escreve sazonalidade_tabela.csv. Depois de gravado, o ficheiro fica congelado
pela regra 7: mexer nele muda o que o agente sabe, retroativamente.
"""

import csv
import sys
from collections import defaultdict

import config

FICHEIRO = "sazonalidade_tabela.csv"
PRIMEIRO_ANO = 2016
ULTIMO_ANO = 2025

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def variacoes_mensais(tabela, ticker):
    """
    A variação de cada mês de cada ano, em percentagem.

    Do primeiro ao último fecho de cada mês. Devolve [(mes, variacao), ...].
    """
    por_mes = defaultdict(list)
    for indice, linha in tabela.iterrows():
        fecho = linha.get("Close")
        if fecho is None or fecho != fecho:          # NaN
            continue
        d = indice.date()
        por_mes[(d.year, d.month)].append(float(fecho))

    variacoes = []
    for (ano, mes), fechos in sorted(por_mes.items()):
        if not (PRIMEIRO_ANO <= ano <= ULTIMO_ANO):
            continue
        if len(fechos) < 5 or fechos[0] <= 0:        # mês truncado não conta
            continue
        variacoes.append((mes, (fechos[-1] / fechos[0] - 1) * 100))
    return variacoes


def main():
    try:
        import yfinance as yf
    except ImportError:
        print("ERRO: yfinance não instalado. Corre: pip install -r requirements.txt")
        return 1

    print(f"A ir buscar {PRIMEIRO_ANO}-01-01 a {ULTIMO_ANO}-12-31, "
          f"{len(config.EMPRESAS)} empresas...")
    lote = yf.download(
        list(config.EMPRESAS),
        start=f"{PRIMEIRO_ANO}-01-01",
        end=f"{ULTIMO_ANO + 1}-01-01",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )
    if lote is None or len(lote) == 0:
        print("ERRO: o Yahoo não devolveu dados.")
        return 1

    import pandas as pd

    por_mes = defaultdict(list)
    empresas_usadas = 0
    for ticker in config.EMPRESAS:
        if isinstance(lote.columns, pd.MultiIndex):
            if ticker not in lote.columns.get_level_values(0):
                print(f"  {ticker}: sem dados -- fica de fora")
                continue
            tabela = lote[ticker]
        else:
            tabela = lote
        variacoes = variacoes_mensais(tabela, ticker)
        if not variacoes:
            print(f"  {ticker}: sem meses completos -- fica de fora")
            continue
        empresas_usadas += 1
        for mes, variacao in variacoes:
            por_mes[mes].append(variacao)

    if not por_mes:
        print("ERRO: nenhuma empresa deu meses completos.")
        return 1

    linhas = []
    for mes in range(1, 13):
        valores = por_mes.get(mes, [])
        if not valores:
            print(f"ERRO: o mês {mes} ficou sem observações.")
            return 1
        linhas.append({
            "mes": mes,
            "nome": MESES[mes - 1],
            "variacao_media_pct": round(sum(valores) / len(valores), 4),
            "observacoes": len(valores),
        })

    with open(FICHEIRO, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(
            f, fieldnames=["mes", "nome", "variacao_media_pct", "observacoes"])
        escritor.writeheader()
        escritor.writerows(linhas)

    print(f"\n{FICHEIRO} escrito: {empresas_usadas} empresas, "
          f"{PRIMEIRO_ANO}-{ULTIMO_ANO}\n")
    print(f"{'mês':<12} {'média %':>9} {'obs':>6}")
    for linha in sorted(linhas, key=lambda l: -l["variacao_media_pct"]):
        print(f"{linha['nome']:<12} {linha['variacao_media_pct']:>9.3f} "
              f"{linha['observacoes']:>6}")

    melhores = sorted(linhas, key=lambda l: -l["variacao_media_pct"])[:4]
    print("\nOs 4 melhores meses: " + ", ".join(l["nome"] for l in melhores))
    return 0


if __name__ == "__main__":
    sys.exit(main())
