"""
Escolhe as 20 ações mais voláteis do S&P 500. CORRE UMA VEZ, à mão.

A REGRA
-------
As 20 ações do S&P 500 com maior volatilidade diária -- o desvio-padrão das
variações de um dia para o outro -- na janela de 12 meses que termina em
FIM_DA_JANELA, excluindo as que já estão no config.EMPRESAS.

A regra está escrita antes de se ver a lista, de propósito. Escolher ações
voláteis "a olho" seria escolher as que dão jeito, e ninguém saberia dizer se
uma empresa entrou por ser volátil ou por alguém gostar dela.

PORQUÊ ADICIONAR VOLÁTEIS
-------------------------
As 40 que já lá estão são as maiores empresas americanas, que se mexem pouco.
Com um stop a 2 desvios-padrão, uma ação calma raramente chega ao stop OU ao
alvo, e a posição fecha por tempo sem dizer nada. Ações mais nervosas fecham
posições mais depressa -- e uma posição fechada é uma observação, que é a
matéria-prima do torneio.

O MÍNIMO DE DIAS
----------------
Uma ação que entrou em bolsa há três semanas pode ter cinco dias muito
agitados e aparecer no topo sem ter história nenhuma. Por isso só entram as
que têm pelo menos MINIMO_DIAS de negociação na janela. Sem este filtro, a
regra escolhia estreias recentes em vez de ações genuinamente nervosas.

CORRER
------
    python escolher_volateis.py

Escreve volateis_escolhidas.csv. Feita a escolha, a lista fica congelada.
"""

import csv
import statistics
import sys
import urllib.request

import config

FICHEIRO = "volateis_escolhidas.csv"

# A janela: 12 meses a terminar aqui. A data está escrita e não é "hoje", para
# a escolha ser sempre reproduzível -- correr isto noutro dia dá o mesmo.
FIM_DA_JANELA = "2026-09-18"
INICIO_DA_JANELA = "2025-09-18"

QUANTAS = 20
MINIMO_DIAS = 200          # de ~250 dias úteis numa janela de 12 meses

FONTE_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def lista_sp500():
    """Os tickers do S&P 500, da Wikipédia. Lista vazia se não der."""
    import pandas as pd

    pedido = urllib.request.Request(
        FONTE_SP500,
        headers={"User-Agent": "agente-acoes/1.0 (projeto pessoal; python)"})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as resposta:
            html = resposta.read().decode("utf-8")
    except Exception as erro:
        print(f"ERRO ao ir buscar a lista do S&P 500: {erro}")
        return []

    try:
        tabelas = pd.read_html(html)
    except Exception as erro:
        print(f"ERRO ao ler a tabela: {erro}")
        return []

    for tabela in tabelas:
        if "Symbol" in tabela.columns:
            # O Yahoo usa hífen onde a Wikipédia usa ponto (BRK.B -> BRK-B).
            return [str(s).strip().replace(".", "-") for s in tabela["Symbol"]]

    print("ERRO: não se encontrou a coluna Symbol na página.")
    return []


def volatilidade(fechos):
    """Desvio-padrão das variações diárias, em percentagem. None se não der."""
    variacoes = []
    for anterior, atual in zip(fechos, fechos[1:]):
        if anterior and anterior > 0:
            variacoes.append((atual / anterior - 1) * 100)
    if len(variacoes) < 2:
        return None, 0
    return statistics.stdev(variacoes), len(variacoes) + 1


def main():
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError:
        print("ERRO: falta o yfinance. Corre: pip install -r requirements.txt")
        return 1

    todos = lista_sp500()
    if not todos:
        return 1
    print(f"S&P 500: {len(todos)} tickers")

    ja_temos = set(config.EMPRESAS)
    candidatos = [t for t in todos if t not in ja_temos]
    print(f"{len(ja_temos)} já estão na lista e ficam de fora; "
          f"sobram {len(candidatos)} candidatos")

    print(f"A ir buscar {INICIO_DA_JANELA} a {FIM_DA_JANELA}...")
    lote = yf.download(
        candidatos,
        start=INICIO_DA_JANELA,
        end=FIM_DA_JANELA,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )
    if lote is None or len(lote) == 0:
        print("ERRO: o Yahoo não devolveu dados.")
        return 1

    medidos, curtos, sem_dados = [], 0, 0
    for ticker in candidatos:
        try:
            if isinstance(lote.columns, pd.MultiIndex):
                if ticker not in lote.columns.get_level_values(0):
                    sem_dados += 1
                    continue
                tabela = lote[ticker]
            else:
                tabela = lote
            fechos = [float(v) for v in tabela["Close"].tolist()
                      if v is not None and v == v]
        except Exception:
            sem_dados += 1
            continue

        if not fechos:
            sem_dados += 1
            continue

        vol, dias = volatilidade(fechos)
        if vol is None:
            sem_dados += 1
            continue
        if dias < MINIMO_DIAS:
            curtos += 1
            continue
        medidos.append({"ticker": ticker,
                        "volatilidade_diaria_pct": round(vol, 4),
                        "dias": dias})

    print(f"{len(medidos)} medidos, {curtos} com menos de {MINIMO_DIAS} dias "
          f"(fora), {sem_dados} sem dados")

    if len(medidos) < QUANTAS:
        print(f"ERRO: só {len(medidos)} candidatos válidos, "
              f"precisava de {QUANTAS}.")
        return 1

    # Desempate pelo ticker, para a escolha não depender da ordem de chegada.
    medidos.sort(key=lambda m: (-m["volatilidade_diaria_pct"], m["ticker"]))
    escolhidas = medidos[:QUANTAS]

    with open(FICHEIRO, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(
            f, fieldnames=["posicao", "ticker", "volatilidade_diaria_pct", "dias"])
        escritor.writeheader()
        for i, linha in enumerate(escolhidas, start=1):
            escritor.writerow(dict(linha, posicao=i))

    print(f"\n{FICHEIRO} escrito. Janela {INICIO_DA_JANELA} a {FIM_DA_JANELA}.\n")
    print(f"{'#':>3} {'ticker':<8} {'vol diária %':>13} {'dias':>6}")
    for i, linha in enumerate(escolhidas, start=1):
        print(f"{i:>3} {linha['ticker']:<8} "
              f"{linha['volatilidade_diaria_pct']:>13.3f} {linha['dias']:>6}")

    print("\nPara o config.py:")
    for i in range(0, QUANTAS, 5):
        print("    " + ", ".join(f'"{l["ticker"]}"'
                                 for l in escolhidas[i:i + 5]) + ",")

    corte = escolhidas[-1]["volatilidade_diaria_pct"]
    seguinte = medidos[QUANTAS]["volatilidade_diaria_pct"] if len(medidos) > QUANTAS else None
    print(f"\nCorte: a 20.a tem {corte:.3f}%. "
          + (f"A 21.a tinha {seguinte:.3f}%." if seguinte is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
