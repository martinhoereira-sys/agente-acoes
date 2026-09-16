"""
Ir buscar os preços das empresas.

Usa o yfinance (grátis, sem chave de API).

Vai buscar TUDO DE UMA VEZ, com yf.download(), em vez de uma chamada por
empresa. Com 40 empresas, uma chamada por empresa são 40 pedidos ao Yahoo (mais
o handshake de cookie/crumb que cada Ticker() faz por sua conta) em poucos
segundos, sempre do mesmo IP -- é assim que se apanha um 429. O yfinance já
sabe agrupar os pedidos; era só pedir-lho.

O que não vier no lote é tentado empresa a empresa, com pausas. Assim uma
empresa estragada (símbolo mudado, ação saída de bolsa) não leva as outras
atrás, que é o que interessa: o torneio não pode ficar sem 39 empresas por
causa de uma.

Modo --simulado: gera preços falsos para testar a canalização sem rede.
Serve para desenvolvimento. NUNCA usar dados simulados no torneio a sério.
"""

import random
import time
from datetime import date, timedelta

# Quantas vezes se tenta o lote antes de desistir, e quanto se espera entre
# tentativas (2s, 4s). Uma falha de rede costuma passar à segunda.
TENTATIVAS_LOTE = 3
ESPERA_INICIAL = 2

# Pausa entre as tentativas empresa a empresa. Só corre para as que faltaram,
# por isso na prática são poucas -- a pausa é para não voltar a martelar o
# Yahoo logo a seguir a ele já ter falhado uma vez.
PAUSA_ENTRE_EMPRESAS = 1.0


def _dias_uteis(n):
    """Devolve os últimos n dias úteis, do mais antigo para o mais recente."""
    dias, d = [], date.today()
    while len(dias) < n:
        if d.weekday() < 5:          # 0-4 = segunda a sexta
            dias.append(d)
        d -= timedelta(days=1)
    return list(reversed(dias))


def _linhas_da_tabela(tabela):
    """
    Converte uma tabela do yfinance na lista de dicionários que o resto do
    programa usa, do mais antigo para o mais recente.

    Linhas sem fecho são deitadas fora. Quando se pedem várias empresas de uma
    vez, o yfinance alinha todas pelo mesmo calendário e mete NaN nos dias em
    que uma delas não negociou (feriados diferentes, ações mais recentes).
    """
    if tabela is None or len(tabela) == 0:
        return []

    linhas = []
    for indice, linha in tabela.iterrows():
        fecho = linha.get("Close")
        if fecho is None or fecho != fecho:        # NaN != NaN
            continue
        volume = linha.get("Volume")
        if volume is None or volume != volume:
            volume = 0
        linhas.append({
            "data": indice.date().isoformat(),
            "fecho": round(float(fecho), 4),
            "volume": int(volume),
        })
    return linhas


def _tabela_da_empresa(lote, ticker):
    """Tira a tabela de uma empresa do resultado do lote."""
    import pandas as pd

    if isinstance(lote.columns, pd.MultiIndex):
        if ticker not in lote.columns.get_level_values(0):
            return None
        return lote[ticker]
    # Com uma só empresa o yfinance devolve as colunas direitas, sem nível.
    return lote


def buscar_varios(tickers, dias=250, simulado=False):
    """
    Devolve {ticker: [{"data", "fecho", "volume"}, ...]}, do mais antigo para o
    mais recente.

    As empresas que não derem dados ficam com lista vazia -- nunca levanta
    exceção por causa de uma empresa. Quem chama é que decide o que fazer.
    """
    tickers = list(tickers)
    if simulado:
        return {t: _historico_simulado(t, dias) for t in tickers}

    try:
        import yfinance as yf
    except ImportError:
        print("ERRO: yfinance não instalado. Corre: pip install -r requirements.txt")
        return {t: [] for t in tickers}

    resultado = {t: [] for t in tickers}
    lote = _buscar_lote(yf, tickers, dias)

    if lote is not None:
        for ticker in tickers:
            try:
                tabela = _tabela_da_empresa(lote, ticker)
            except Exception as erro:                # uma empresa estragada
                print(f"AVISO: não se percebeu a tabela de {ticker}: {erro}")
                continue
            resultado[ticker] = _linhas_da_tabela(tabela)

    faltam = [t for t in tickers if not resultado[t]]

    # Se não veio NADA, o problema não é de uma empresa ou outra: é a rede ou o
    # Yahoo. Repetir 40 pedidos um a um só ia demorar mais para falhar na mesma.
    if faltam and len(faltam) < len(tickers):
        print(f"  ({len(faltam)} sem dados no lote: {', '.join(faltam)} -- a tentar uma a uma)")
        for ticker in faltam:
            time.sleep(PAUSA_ENTRE_EMPRESAS)
            resultado[ticker] = buscar_historico(ticker, dias=dias)

    return resultado


def _buscar_lote(yf, tickers, dias):
    """Pede as empresas todas de uma vez. Devolve a tabela ou None."""
    espera = ESPERA_INICIAL
    for tentativa in range(1, TENTATIVAS_LOTE + 1):
        try:
            lote = yf.download(
                tickers,
                period=f"{dias}d",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,      # o mesmo que o Ticker().history() fazia
                threads=True,
                progress=False,
            )
        except Exception as erro:
            print(f"ERRO no lote (tentativa {tentativa}/{TENTATIVAS_LOTE}): {erro}")
            lote = None

        if lote is not None and len(lote):
            return lote

        if tentativa < TENTATIVAS_LOTE:
            print(f"  lote vazio -- nova tentativa daqui a {espera}s")
            time.sleep(espera)
            espera *= 2
    return None


def buscar_historico(ticker, dias=250, simulado=False):
    """
    Uma empresa só. Serve para as que faltarem ao lote e para experimentar à mão.

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

    return _linhas_da_tabela(tabela)


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
