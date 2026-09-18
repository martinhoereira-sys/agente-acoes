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

O máximo e o mínimo de cada dia são alargados até cobrirem a abertura e o
fecho. O Yahoo manda de vez em quando dias impossíveis, e um intervalo que não
cobre a abertura faz o posicoes.py passar ao lado de um stop realmente
atingido. Ver _corrigir_intervalo.

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


def _numero(valor):
    """Devolve o número arredondado, ou None se vier vazio ou NaN."""
    if valor is None or valor != valor:            # NaN != NaN
        return None
    return round(float(valor), 4)


def _corrigir_intervalo(linha):
    """
    Alarga o máximo e o mínimo até cobrirem a abertura e o fecho.

    O Yahoo manda de vez em quando dias impossíveis -- abertura acima do máximo,
    ou abaixo do mínimo. Isto não é um pormenor de arrumação: o posicoes.py usa
    o máximo e o mínimo para ver se o preço tocou no stop ou no alvo, e um
    intervalo que não cobre a abertura pode deixar passar um stop realmente
    atingido. A posição ficava aberta quando já devia ter fechado a perder.

    A correção não inventa nada. A abertura e o fecho são preços a que se
    negociou mesmo, por isso o verdadeiro máximo do dia é pelo menos o maior dos
    três e o verdadeiro mínimo é pelo menos o menor. Só se alarga o intervalo
    até ao que já se sabe ser verdade -- nunca se aperta.

    Devolve True se mexeu em alguma coisa.
    """
    conhecidos = [linha[c] for c in ("abertura", "fecho") if linha[c] is not None]
    if not conhecidos:
        return False

    corrigida = False
    if linha["maximo"] is not None:
        maior = max([linha["maximo"]] + conhecidos)
        if maior != linha["maximo"]:
            linha["maximo"] = maior
            corrigida = True
    if linha["minimo"] is not None:
        menor = min([linha["minimo"]] + conhecidos)
        if menor != linha["minimo"]:
            linha["minimo"] = menor
            corrigida = True
    return corrigida


def _linhas_da_tabela(tabela):
    """
    Converte uma tabela do yfinance na lista de dicionários que o resto do
    programa usa, do mais antigo para o mais recente:

        {"data": "2026-09-15", "abertura": 229.90, "maximo": 232.10,
         "minimo": 229.05, "fecho": 231.40, "volume": 48120000}

    Guarda-se o dia inteiro, não só o fecho, porque o fecho sozinho não chega
    para saber se uma aposta acertou: uma ação pode descer até ao stop a meio
    do dia e fechar acima dele, e se abrir abaixo do stop a perda é maior do
    que a planeada. Isso só se vê com abertura, máximo e mínimo.

    Linhas sem fecho são deitadas fora. Quando se pedem várias empresas de uma
    vez, o yfinance alinha todas pelo mesmo calendário e mete NaN nos dias em
    que uma delas não negociou (feriados diferentes, ações mais recentes).

    Devolve (linhas, quantas tiveram o máximo/mínimo corrigido).
    """
    if tabela is None or len(tabela) == 0:
        return [], 0

    linhas = []
    corrigidas = 0
    for indice, linha in tabela.iterrows():
        fecho = _numero(linha.get("Close"))
        if fecho is None:
            continue
        volume = linha.get("Volume")
        if volume is None or volume != volume:
            volume = 0
        nova = {
            "data": indice.date().isoformat(),
            "abertura": _numero(linha.get("Open")),
            "maximo": _numero(linha.get("High")),
            "minimo": _numero(linha.get("Low")),
            "fecho": fecho,
            "volume": int(volume),
        }
        if _corrigir_intervalo(nova):
            corrigidas += 1
        linhas.append(nova)
    return linhas, corrigidas


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
    corrigidas = {}                                  # ticker -> quantas linhas
    lote = _buscar_lote(yf, tickers, dias)

    if lote is not None:
        for ticker in tickers:
            try:
                tabela = _tabela_da_empresa(lote, ticker)
            except Exception as erro:                # uma empresa estragada
                print(f"AVISO: não se percebeu a tabela de {ticker}: {erro}")
                continue
            resultado[ticker], n_corrigidas = _linhas_da_tabela(tabela)
            if n_corrigidas:
                corrigidas[ticker] = n_corrigidas

    faltam = [t for t in tickers if not resultado[t]]

    # Se não veio NADA, o problema não é de uma empresa ou outra: é a rede ou o
    # Yahoo. Repetir 40 pedidos um a um só ia demorar mais para falhar na mesma.
    if faltam and len(faltam) < len(tickers):
        print(f"  ({len(faltam)} sem dados no lote: {', '.join(faltam)} -- a tentar uma a uma)")
        for ticker in faltam:
            time.sleep(PAUSA_ENTRE_EMPRESAS)
            resultado[ticker], n_corrigidas = _buscar_uma(yf, ticker, dias)
            if n_corrigidas:
                corrigidas[ticker] = n_corrigidas

    if corrigidas:
        # Serve para vigiar a fonte ao longo do torneio: duas empresas num dia
        # é o Yahoo a ser o Yahoo; quinze em quarenta é problema a sério.
        total = sum(corrigidas.values())
        nomes = ", ".join(sorted(corrigidas))
        plural = "linha" if total == 1 else "linhas"
        print(f"  {total} {plural} com máximo/mínimo corrigidos ({nomes})")

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

    return _buscar_uma(yf, ticker, dias)[0]


def _buscar_uma(yf, ticker, dias):
    """Uma empresa só. Devolve (linhas, quantas foram corrigidas)."""
    try:
        tabela = yf.Ticker(ticker).history(period=f"{dias}d", interval="1d")
    except Exception as erro:
        print(f"ERRO ao buscar {ticker}: {erro}")
        return [], 0

    if tabela is None or len(tabela) == 0:
        print(f"AVISO: sem dados para {ticker}")
        return [], 0

    return _linhas_da_tabela(tabela)


def _historico_simulado(ticker, dias):
    """
    Passeio aleatório. Só para testar que o resto do programa funciona.

    A abertura, o máximo e o mínimo são construídos à volta do fecho de modo a
    não poderem sair incoerentes: o máximo parte do maior de (abertura, fecho)
    e sobe, o mínimo parte do menor e desce. Um dia simulado com o máximo
    abaixo do mínimo dava testes que passavam sem provar nada.
    """
    random.seed(ticker)                      # mesmo ticker = mesma série
    preco = 100.0
    linhas = []
    for d in _dias_uteis(dias):
        anterior = preco
        preco *= (1 + random.gauss(0.0004, 0.015))
        abertura = anterior * (1 + random.gauss(0, 0.004))   # gap da noite
        maximo = max(abertura, preco) * (1 + abs(random.gauss(0, 0.005)))
        minimo = min(abertura, preco) * (1 - abs(random.gauss(0, 0.005)))
        linhas.append({
            "data": d.isoformat(),
            "abertura": round(abertura, 4),
            "maximo": round(maximo, 4),
            "minimo": round(minimo, 4),
            "fecho": round(preco, 4),
            "volume": random.randint(10_000_000, 90_000_000),
        })
    return linhas
