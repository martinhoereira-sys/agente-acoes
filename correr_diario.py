"""
O programa que corre uma vez por dia.

Faz sempre as mesmas três coisas:
  1. vai buscar os preços de cada empresa
  2. grava o dia de hoje (abertura, máximo, mínimo, fecho, volume) em
     dados/precos.csv
  3. pergunta a cada agente o que faria, e grava a resposta em dados/decisoes.csv

Cada agente só pode ter UMA posição aberta por empresa de cada vez. Se a aposta
anterior dele nessa empresa ainda não fechou, não se lhe pergunta nada. Uma
pessoa a sério não compra a mesma ação todos os dias, e apostas repetidas na
mesma empresa também não são observações independentes -- enchiam o registo e
davam a ideia de haver mais provas do que há.

Se uma posição já fechou é sempre calculado a partir dos preços (ver
posicoes.py), nunca gravado.

A ÚLTIMA CORRIDA DO DIA GANHA. Se o programa já tiver corrido hoje, as linhas
desse dia são substituídas em vez de saltadas: a corrida a meio da sessão grava
um preço intradiário e a corrida de depois do fecho corrige-o para o fecho
verdadeiro. Como o preço muda, as decisões desse dia são recalculadas -- ficar
com a decisão antiga apontada a um preço de entrada que já não existe seria pior
do que não ter decisão nenhuma.

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
import time

import config
from lista_agentes import AGENTES
from base import calcular_stop_e_alvo
from fonte_dados import buscar_varios
from posicoes import posicoes_abertas

# O dia inteiro, não só o fecho: o fecho sozinho não chega para saber se uma
# aposta acertou. Uma ação pode descer até ao stop a meio do dia e fechar acima
# dele -- com só o fecho, essa perda desaparecia do registo. E se abrir abaixo
# do stop, a perda é maior do que a planeada, o que só se vê pela abertura.
COLUNAS_PRECOS = ["data", "ticker", "abertura", "maximo", "minimo", "fecho", "volume"]
COLUNAS_DECISOES = [
    "data", "agente", "ticker", "acao", "preco_entrada",
    "stop", "alvo", "racio", "confianca", "razao",
    "valor_aposta", "comissao", "slippage_pct",
]

# Uma linha por (data, ticker) nos preços, uma por (data, agente, ticker) nas
# decisões. É isto que nunca pode aparecer repetido nos ficheiros.
CHAVE_PRECO = ("data", "ticker")
CHAVE_DECISAO = ("data", "agente", "ticker")

# O que uma corrida deita fora antes de gravar: tudo o que já lá estava para o
# dia e a empresa que acabou de processar. Nas decisões é de propósito mais
# largo do que a chave única -- se um agente decidiu de manhã e hoje já não
# decide nada, a decisão da manhã tem de desaparecer, não de ficar para trás.
CHAVE_CORRIDA = ("data", "ticker")


def _garantir_ficheiro(caminho, colunas):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    if not os.path.exists(caminho):
        with open(caminho, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(colunas)


def _chave(linha, colunas):
    return tuple(str(linha.get(coluna, "")) for coluna in colunas)


def _ler_csv(caminho, colunas):
    """
    Lê o ficheiro todo para memória: (cabeçalho, linhas como dicionários).

    Os ficheiros têm poucos MB, por isso ler tudo e reescrever é bem mais
    simples do que tentar mexer numa linha no meio do ficheiro.
    """
    if not os.path.exists(caminho):
        return list(colunas), []

    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f, restval="")
        do_ficheiro = list(leitor.fieldnames or [])
        linhas = [dict(linha) for linha in leitor]

    # O cabeçalho é sempre o de agora, pela ordem de agora. Quando se acrescenta
    # uma coluna, as linhas antigas ficam com ela vazia -- não se inventam
    # valores nem se apagam linhas. As colunas que estejam no ficheiro e já não
    # sejam usadas vão para o fim, para não se perder nada que lá esteja.
    cabecalho = list(colunas) + [c for c in do_ficheiro if c not in colunas]
    return cabecalho, linhas


def _escrever_csv(caminho, cabecalho, linhas):
    """Escreve para um ficheiro temporário e só depois substitui o verdadeiro.

    Se o programa morrer a meio, o ficheiro bom fica intacto em vez de ficar
    cortado ao meio.
    """
    temporario = caminho + ".tmp"
    with open(temporario, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=cabecalho,
                                  restval="", extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(linhas)
    os.replace(temporario, caminho)


def _fundir(antigas, novas, dias_tickers, chave_unica):
    """
    Junta as linhas novas às antigas com a regra "a última corrida do dia ganha".

    dias_tickers: os (data, ticker) processados nesta corrida. As linhas antigas
    com essas chaves são deitadas fora; as novas ficam no lugar delas, na mesma
    posição, para a ordem cronológica não mudar. As linhas dos outros dias não
    são tocadas.

    Devolve (linhas, quantas novas, quantas atualizadas, quantas removidas).
    """
    # Se a mesma chave aparecer duas vezes nas novas, fica a última.
    por_chave = {}
    for linha in novas:
        por_chave[_chave(linha, chave_unica)] = linha

    linhas = []
    usadas = set()
    atualizadas = 0
    removidas = 0

    for antiga in antigas:
        if _chave(antiga, CHAVE_CORRIDA) not in dias_tickers:
            linhas.append(antiga)                      # outro dia/empresa: não se mexe
            continue
        chave = _chave(antiga, chave_unica)
        if chave in por_chave and chave not in usadas:
            linhas.append(por_chave[chave])            # substitui no mesmo sítio
            usadas.add(chave)
            atualizadas += 1
        else:
            removidas += 1                             # já não faz sentido hoje

    for chave, linha in por_chave.items():
        if chave not in usadas:
            linhas.append(linha)
            usadas.add(chave)

    return linhas, len(por_chave) - atualizadas, atualizadas, removidas


def _cabecalho_atual(caminho):
    """O cabeçalho tal como está gravado, para se ver se precisa de mudar."""
    if not os.path.exists(caminho):
        return None
    with open(caminho, newline="", encoding="utf-8") as f:
        return next(csv.reader(f), None)


def _gravar(caminho, colunas, chave_unica, dias_tickers, novas):
    """Aplica as linhas novas ao ficheiro. Devolve (novas, atualizadas, removidas)."""
    cabecalho, antigas = _ler_csv(caminho, colunas)
    linhas, n_novas, n_atualizadas, n_removidas = _fundir(
        antigas, novas, dias_tickers, chave_unica)

    # Sem nada para mudar não se toca no ficheiro: evita commits vazios do robô.
    # A exceção é o cabeçalho ter mudado: aí reescreve-se mesmo sem linhas
    # novas, senão um ficheiro antigo nunca chegava a ganhar as colunas novas.
    mudou_cabecalho = _cabecalho_atual(caminho) != cabecalho
    if n_novas or n_atualizadas or n_removidas or mudou_cabecalho:
        _escrever_csv(caminho, cabecalho, linhas)
    return n_novas, n_atualizadas, n_removidas


def _contar(quantidade, singular, plural):
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _resumo(precos, decisoes, falhas, ignoradas=0):
    """'2 preços novos, 1 preço atualizado, 3 decisões atualizadas'."""
    n_precos, a_precos, r_precos = precos
    n_decisoes, a_decisoes, r_decisoes = decisoes

    partes = [
        (n_precos, "preço novo", "preços novos"),
        (a_precos, "preço atualizado", "preços atualizados"),
        (r_precos, "preço removido", "preços removidos"),
        (n_decisoes, "decisão nova", "decisões novas"),
        (a_decisoes, "decisão atualizada", "decisões atualizadas"),
        (r_decisoes, "decisão removida", "decisões removidas"),
        (ignoradas, "ignorada por já haver posição aberta",
                    "ignoradas por já haver posição aberta"),
        (falhas, "falha", "falhas"),
    ]
    texto = [_contar(q, s, p) for q, s, p in partes if q]
    return ", ".join(texto) if texto else "nada a gravar"


def main(simulado=False):
    comeco = time.monotonic()
    _garantir_ficheiro(config.FICHEIRO_PRECOS, COLUNAS_PRECOS)
    _garantir_ficheiro(config.FICHEIRO_DECISOES, COLUNAS_DECISOES)

    dias_tickers = set()      # (data, ticker) processados hoje
    precos_novos = []
    decisoes_novas = []
    falhas = 0

    # Tudo de uma vez: com 40 empresas, uma chamada por empresa apanha limites
    # de pedidos do Yahoo. Ver fonte_dados.py.
    relogio = time.monotonic()
    historicos = buscar_varios(config.EMPRESAS, dias=250, simulado=simulado)
    segundos_dados = time.monotonic() - relogio
    print(f"\nDados: {len(config.EMPRESAS)} empresas em {segundos_dados:.1f}s")

    # Os preços primeiro, todos, porque as posições abertas calculam-se com os
    # preços de hoje já lá dentro.
    for ticker in config.EMPRESAS:
        historico = historicos.get(ticker)
        if not historico:
            # Empresa sem dados não se processa, logo também não se apaga o que
            # já lá estiver gravado para ela. Uma empresa que falhe não pode
            # levar as outras atrás.
            print(f"  {ticker}: SEM DADOS -- ignorado hoje")
            falhas += 1
            continue

        hoje = historico[-1]
        print(f"  {ticker}: {hoje['data']} fecho {hoje['fecho']} "
              f"(min {hoje.get('minimo')} / max {hoje.get('maximo')})")
        dias_tickers.add((hoje["data"], ticker))
        precos_novos.append({
            "data": hoje["data"],
            "ticker": ticker,
            "abertura": hoje.get("abertura"),
            "maximo": hoje.get("maximo"),
            "minimo": hoje.get("minimo"),
            "fecho": hoje["fecho"],
            "volume": hoje["volume"],
        })

    # Que posições é que ainda estão de pé? Calcula-se a partir dos preços, com
    # os de hoje já incluídos -- uma posição pode ter fechado hoje mesmo, e
    # nesse caso o agente já pode voltar a decidir esta empresa.
    _, decisoes_gravadas = _ler_csv(config.FICHEIRO_DECISOES, COLUNAS_DECISOES)
    _, precos_gravados = _ler_csv(config.FICHEIRO_PRECOS, COLUNAS_PRECOS)
    abertas = posicoes_abertas(
        decisoes_gravadas,
        precos_gravados + precos_novos,
        ignorar_datas_tickers=dias_tickers,
    )

    ignoradas = 0
    for ticker in config.EMPRESAS:
        historico = historicos.get(ticker)
        if not historico:
            continue                      # já foi contado como falha acima

        hoje = historico[-1]

        # As decisões são recalculadas sempre, porque o preço de entrada é o
        # preço que acabámos de ir buscar.
        for agente in AGENTES:
            if (agente.nome, ticker) in abertas:
                # A aposta anterior dele nesta empresa ainda está de pé. Não se
                # lhe pergunta nada e não se grava linha nenhuma.
                ignoradas += 1
                continue

            decisao = agente.decidir(ticker, historico)
            if not decisao:
                continue

            stop, alvo = calcular_stop_e_alvo(hoje["fecho"], historico, agente.racio)
            decisoes_novas.append({
                "data": hoje["data"],
                "agente": agente.nome,
                "ticker": ticker,
                "acao": decisao["acao"],
                "preco_entrada": hoje["fecho"],
                "stop": stop,
                "alvo": alvo,
                "racio": agente.racio,
                "confianca": decisao.get("confianca", ""),
                "razao": decisao.get("razao", ""),
                "valor_aposta": config.VALOR_POR_APOSTA,
                "comissao": config.COMISSAO_POR_OPERACAO,
                "slippage_pct": config.SLIPPAGE_PCT,
            })
            print(f"      {agente.nome}: {decisao['acao']} -- {decisao['razao']}")

    precos = _gravar(config.FICHEIRO_PRECOS, COLUNAS_PRECOS,
                     CHAVE_PRECO, dias_tickers, precos_novos)
    decisoes = _gravar(config.FICHEIRO_DECISOES, COLUNAS_DECISOES,
                       CHAVE_DECISAO, dias_tickers, decisoes_novas)

    print(f"\nResumo: {_resumo(precos, decisoes, falhas, ignoradas)}")
    print(f"Tempo: {segundos_dados:.1f}s a ir buscar os dados, "
          f"{time.monotonic() - comeco:.1f}s no total")

    # Se NENHUMA empresa deu dados, sai com erro para o GitHub Actions avisar.
    if falhas and falhas == len(config.EMPRESAS):
        print("ERRO: nenhuma empresa devolveu dados.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(simulado="--simulado" in sys.argv))
