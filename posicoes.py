"""
Saber o que aconteceu a cada decisão, a partir dos preços que vieram a seguir.

Isto NUNCA se grava em ficheiro. O estado de uma posição é sempre recalculado
a partir do dados/precos.csv -- se estivesse gravado, ficávamos com anos de
resultados calculados por uma regra que já não usamos e sem maneira de saber
quais.

REGRA DE OURO: a partir do arranque oficial do torneio, este ficheiro fica
congelado tal como os agentes -- e com ele o config.DIAS_MAXIMOS_POSICAO, que é
uma regra de avaliação apesar de viver no config.py.

É o reverso de não gravar nada: como os resultados são sempre recalculados,
mexer aqui reescreve em silêncio os resultados de todo o histórico, e não há
número nenhum gravado que passe a não bater certo e avise. Mexer numa linha em
junho muda o vencedor de outubro sem deixar rasto. Se for mesmo indispensável,
a data, o motivo e o que mudou vão para o README (regra 7), e a análise final
tem de dizer com que versão foi feita.

Serve duas coisas:

  1. o correr_diario, para não deixar um agente comprar a mesma empresa outra
     vez enquanto a aposta anterior ainda está de pé;
  2. a análise do fim do torneio -- é a mesma conta.

AS REGRAS
---------
Uma posição aberta no dia D, com stop S e alvo A, fecha no primeiro dia a
seguir a D em que:

  * a abertura já vem fora do intervalo -> sai à ABERTURA, não ao stop nem ao
    alvo. É o primeiro preço do dia: a ordem executa logo ali e nada do que
    aconteça a seguir nesse dia interessa. Abaixo do stop é a notícia má
    durante a noite -- o stop não protege e perde-se mais do que o planeado;
    acima do alvo é o contrário, e ganha-se mais. Nos dois casos o preço é o
    que o mercado deu. Fingir o contrário era inventar dinheiro num sentido ou
    deitá-lo fora no outro.
  * o mínimo chega ao stop              -> sai ao STOP
  * o máximo chega ao alvo              -> sai ao ALVO

Se DEPOIS DA ABERTURA o mínimo tocar no stop E o máximo tocar no alvo no mesmo
dia, conta como STOP. Com preços diários não dá para saber qual veio primeiro,
e é preferível ser pessimista a dar aos agentes um resultado melhor do que a
realidade. Na abertura não há esta dúvida -- é o primeiro preço do dia, e por
isso é que os dois gaps são vistos antes.

Ao fim de config.DIAS_MAXIMOS_POSICAO dias de bolsa sem tocar em nada, fecha ao
preço de fecho desse dia.

DIAS ANTIGOS SEM MÁXIMO E MÍNIMO
--------------------------------
As primeiras linhas do precos.csv só têm o fecho. Nesses dias usa-se o fecho no
lugar do máximo e do mínimo. Não é inventar nada: como mínimo <= fecho <= máximo,
um fecho abaixo do stop garante que o mínimo também esteve, e um fecho acima do
alvo garante o mesmo do máximo. O que pode acontecer é passar ao lado de um
toque que só se via pelo máximo ou pelo mínimo -- falhar um fecho é melhor do
que inventar um.
"""

import csv
import os

import config

ABERTA = "ABERTA"
STOP = "STOP"
ALVO = "ALVO"
TEMPO = "TEMPO"      # fechada por limite de dias


def _numero(valor):
    """Converte para float. Devolve None se estiver vazio ou não for número."""
    if valor is None or valor == "":
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return None if numero != numero else numero        # NaN != NaN


def _por_ticker(precos):
    """{ticker: [linhas ordenadas por data]} -- o histórico de cada empresa."""
    mapa = {}
    for linha in precos:
        mapa.setdefault(linha["ticker"], []).append(linha)
    for linhas in mapa.values():
        linhas.sort(key=lambda l: l["data"])
    return mapa


def _resultado_euros(decisao, preco_saida):
    """
    Quanto se ganhou ou perdeu, em euros, já com custos.

    Os custos vêm da própria linha da decisão, não do config.py de hoje: se um
    dia mudarmos a comissão, as decisões antigas têm de continuar avaliadas com
    a comissão que tinham na altura.

    Compra-se um pouco acima do preço no ecrã e vende-se um pouco abaixo (é isso
    o slippage), e paga-se comissão à entrada e à saída.
    """
    entrada = _numero(decisao.get("preco_entrada"))
    if entrada is None or preco_saida is None or entrada <= 0:
        return None

    valor = _numero(decisao.get("valor_aposta"))
    comissao = _numero(decisao.get("comissao"))
    slippage = _numero(decisao.get("slippage_pct"))
    if valor is None: valor = config.VALOR_POR_APOSTA
    if comissao is None: comissao = config.COMISSAO_POR_OPERACAO
    if slippage is None: slippage = config.SLIPPAGE_PCT

    fracao = slippage / 100.0                  # 0.05 no config = 0,05%
    preco_compra = entrada * (1 + fracao)
    preco_venda = preco_saida * (1 - fracao)
    if preco_compra <= 0:
        return None

    quantidade = valor / preco_compra
    return round(quantidade * (preco_venda - preco_compra) - 2 * comissao, 2)


def _fecho_da_posicao(decisao, dias_seguintes):
    """
    Percorre os dias a seguir à decisão e devolve
    (estado, data_saida, preco_saida, dias_passados).

    dias_seguintes já vem só com os dias posteriores ao da decisão, por ordem.
    """
    stop = _numero(decisao.get("stop"))
    alvo = _numero(decisao.get("alvo"))

    for passados, dia in enumerate(dias_seguintes, start=1):
        fecho = _numero(dia.get("fecho"))
        if fecho is None:
            continue                       # dia sem preço não decide nada

        # Sem máximo/mínimo (linhas antigas) usa-se o fecho: mínimo <= fecho
        # <= máximo, por isso isto nunca inventa um toque que não houve.
        abertura = _numero(dia.get("abertura"))
        maximo = _numero(dia.get("maximo"))
        minimo = _numero(dia.get("minimo"))
        if maximo is None: maximo = fecho
        if minimo is None: minimo = fecho

        # 1. A abertura primeiro, porque é o primeiro preço do dia. Se já vem
        #    fora do intervalo, a ordem executa logo ali e nada do que aconteça
        #    depois nesse dia interessa. Sai-se ao preço que o mercado deu, não
        #    ao que estava planeado -- para baixo perde-se mais, para cima
        #    ganha-se mais. Os dois casos nunca colidem: o stop é sempre
        #    abaixo do alvo.
        if abertura is not None:
            if stop is not None and abertura <= stop:
                return STOP, dia["data"], abertura, passados
            if alvo is not None and abertura >= alvo:
                return ALVO, dia["data"], abertura, passados

        # 2. Dentro do dia, o stop ganha ao alvo: quando os dois são tocados no
        #    mesmo dia não sabemos qual veio primeiro, e assume-se a pior. Isto
        #    é só para o que acontece depois da abertura -- aí sim há dúvida.
        if stop is not None and minimo <= stop:
            return STOP, dia["data"], stop, passados

        if alvo is not None and maximo >= alvo:
            return ALVO, dia["data"], alvo, passados

        if passados >= config.DIAS_MAXIMOS_POSICAO:
            return TEMPO, dia["data"], fecho, passados

    return ABERTA, None, None, len(dias_seguintes)


def estado_das_posicoes(decisoes, precos):
    """
    Devolve uma lista com o estado de cada decisão, pela mesma ordem:

        {"data", "agente", "ticker", "estado", "data_saida", "preco_saida",
         "resultado_eur", "dias"}

    estado é ABERTA, STOP, ALVO ou TEMPO.
    """
    historicos = _por_ticker(precos)
    estados = []

    for decisao in decisoes:
        dias = historicos.get(decisao["ticker"], [])
        seguintes = [d for d in dias if d["data"] > decisao["data"]]
        estado, data_saida, preco_saida, passados = _fecho_da_posicao(decisao, seguintes)

        # Só se sabe fazer a conta de uma compra. O stop e o alvo são calculados
        # como se fosse sempre compra (ver base.py), por isso uma venda a
        # descoberto daria um número errado -- mais vale não dar número nenhum.
        if estado == ABERTA or str(decisao.get("acao", "")).upper() != "COMPRA":
            resultado = None
        else:
            resultado = _resultado_euros(decisao, preco_saida)

        estados.append({
            "data": decisao["data"],
            "agente": decisao["agente"],
            "ticker": decisao["ticker"],
            "estado": estado,
            "data_saida": data_saida,
            "preco_saida": preco_saida,
            "resultado_eur": resultado,
            "dias": passados,
        })
    return estados


def posicoes_abertas(decisoes, precos, ignorar_datas_tickers=()):
    """
    Devolve o conjunto de (agente, ticker) com posição ainda aberta.

    ignorar_datas_tickers: (data, ticker) a deixar de fora da conta. O
    correr_diario passa aqui o dia e as empresas que está a processar, porque
    essas decisões vão ser substituídas nesta corrida. Sem isto, a segunda
    corrida do dia via a decisão da primeira como posição aberta, não perguntava
    nada ao agente, e a decisão desaparecia do registo.
    """
    ignorar = set(ignorar_datas_tickers)
    em_jogo = [d for d in decisoes if (d["data"], d["ticker"]) not in ignorar]
    return {(e["agente"], e["ticker"])
            for e in estado_das_posicoes(em_jogo, precos)
            if e["estado"] == ABERTA}


def _ler_csv(caminho):
    if not os.path.exists(caminho):
        return []
    with open(caminho, newline="", encoding="utf-8") as f:
        return [dict(linha) for linha in csv.DictReader(f, restval="")]


def carregar(ficheiro_decisoes=None, ficheiro_precos=None):
    """Lê os dois CSV e devolve o estado de todas as decisões."""
    decisoes = _ler_csv(ficheiro_decisoes or config.FICHEIRO_DECISOES)
    precos = _ler_csv(ficheiro_precos or config.FICHEIRO_PRECOS)
    return estado_das_posicoes(decisoes, precos)


if __name__ == "__main__":
    from collections import Counter

    estados = carregar()
    contagem = Counter(e["estado"] for e in estados)
    print(f"{len(estados)} decisões: " +
          ", ".join(f"{n} {estado}" for estado, n in sorted(contagem.items())))

    fechadas = [e for e in estados if e["resultado_eur"] is not None]
    if fechadas:
        total = sum(e["resultado_eur"] for e in fechadas)
        ganhas = sum(1 for e in fechadas if e["resultado_eur"] > 0)
        print(f"{len(fechadas)} fechadas com conta feita: "
              f"{ganhas} a ganhar, {total:+.2f} EUR no total")
