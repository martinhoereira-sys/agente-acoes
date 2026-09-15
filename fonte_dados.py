"""
Ir buscar os preços das empresas.

Usa o yfinance (grátis, sem chave de API).

Modo --simulado: gera preços falsos para testar a canalização sem rede.
Serve para desenvolvimento. NUNCA usar dados simulados no torneio a sério.
"""

import random
from datetime import date, timedelta


def _dias_uteis(n):
    """Devolve os últimos n dias úteis, do mais antigo para o mais recente."""
    dias, d = [], date.today()
    while len(dias) < n:
        if d.weekday() < 5:          # 0-4 = segunda a sexta
            dias.append(d)
        d -= timedelta(days=1)
    return list(reversed(dias))


def buscar_historico(ticker, dias=250, simulado=False):
    """
    Devolve uma lista de dicionários, do mais antigo para o mais recente:
        {"data": "2026-09-15", "fecho": 231.40, "volume": 48120000}

    Devolve lista vazia se não conseguir dados -- quem chama trata disso.
    """
    if simulado:
        return _historico_simulado(ticker, dias)

    try:
        import yfinance as yf
    except ImportError:
        print("ERRO: yfinance não instalado. Corre: pip install -r requirements.txt")
        return []

    try:
        tabela = yf.Ticker(ticker).history(period=f"{dias}d", interval="1d")
    except Exception as erro:
        print(f"ERRO ao buscar {ticker}: {erro}")
        return []

    if tabela is None or len(tabela) == 0:
        print(f"AVISO: sem dados para {ticker}")
        return []

    linhas = []
    for indice, linha in tabela.iterrows():
        linhas.append({
            "data": indice.date().isoformat(),
            "fecho": round(float(linha["Close"]), 4),
            "volume": int(linha["Volume"]),
        })
    return linhas


def _historico_simulado(ticker, dias):
    """Passeio aleatório. Só para testar que o resto do programa funciona."""
    random.seed(ticker)                      # mesmo ticker = mesma série
    preco = 100.0
    linhas = []
    for d in _dias_uteis(dias):
        preco *= (1 + random.gauss(0.0004, 0.015))
        linhas.append({
            "data": d.isoformat(),
            "fecho": round(preco, 4),
            "volume": random.randint(10_000_000, 90_000_000),
        })
    return linhas
