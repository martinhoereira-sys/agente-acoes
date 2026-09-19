"""
As três condições da regra 8: este agente merece ser selecionado?

  1. tem posições fechadas que cheguem (MINIMO_FECHADAS);
  2. a vantagem sobre os controlos é estatisticamente significativa;
  3. continua a sê-lo depois de lhe ser retirada a melhor posição.

A condição 2 é o coração; a 1 e a 3 são guardas à volta dela. A 1 impede que
meia dúzia de apostas cheguem para um veredicto. A 3 impede que um único acerto
enorme carregue o agente todo.

Um agente pode acabar acima da moeda ao ar por ter tido sorte. Estas contas
perguntam se a vantagem é maior do que a incerteza com que foi medida -- ou
seja, se sobreviveria a repetir o torneio.

COMO SE MEDE A CONDIÇÃO 2
-------------------------
Para cada posição fechada sabe-se quanto deu, em euros. Com esses números, por
cada par (agente, controlo):

  1. a média por posição de cada um;
  2. o erro-padrão da diferença entre as duas médias, que é o quanto essa
     diferença ainda oscilaria se o torneio voltasse a correr;
  3. a diferença a dividir pelo erro-padrão.

O resultado é quantas vezes a vantagem é maior do que a sua própria margem de
erro. É o t de Welch, que é a versão que não exige que os dois lados tenham o
mesmo número de apostas nem a mesma irregularidade -- e aqui nunca têm.

Passa quem tiver mais de LIMIAR contra os DOIS controlos. "O melhor dos dois
controlos" da regra 8 é, na prática, aquele que der o t mais baixo: é o mais
difícil de bater, e bater o mais difícil é bater os dois.

A CONDIÇÃO 3, O TESTE DE ROBUSTEZ
---------------------------------
Faz-se a mesma conta outra vez, mas depois de tirar ao agente a posição que lhe
deu mais dinheiro. Se a vantagem desaparecer quando se tira uma única aposta, o
agente não tinha um padrão: tinha um dia de sorte.

Tira-se só do lado do agente. Os controlos ficam com tudo o que têm -- tirar
também a melhor deles tornava o teste mais brando, e o objetivo é ser duro.
"Melhor" é a de maior resultado em euros. Se depois de a tirar sobrarem menos de
duas posições, não há conta a fazer e o agente não passa.

Atenção ao que esta condição faz mesmo: o caso do lucro que vem TODO de uma
posição já é chumbado pela condição 2 sozinha. Uma posição enorme puxa a média e
o erro-padrão na mesma proporção, e o resultado tende para 1, nunca para 2,5. A
condição 3 morde nos casos em cima da linha -- vantagem real mas apertada, em
que a melhor posição é o que empurra para o lado bom. Ver o README.

PORQUÊ 2,5 E NÃO 2
------------------
Ver o README, secção "Critério de seleção". Em duas linhas: com dez agentes a
serem avaliados ao mesmo tempo, um limiar de 2 deixaria passar alguém por puro
acaso com demasiada frequência. O 2,5 compensa o número de candidatos.

REGRA DE OURO: este ficheiro é lógica de avaliação. A partir do arranque
oficial do torneio fica congelado, como o posicoes.py e pelo mesmo motivo --
mexer aqui reescreve em silêncio quem passa e quem não passa. Ver regra 7.
"""

import math
import statistics

import posicoes

# Os dois controlos, pelo nome. Estão fixos pela regra 3 do README: nunca se
# removem. Mudar esta lista muda quem é a barra a ultrapassar.
CONTROLOS = ("controlo-sempre-compra", "controlo-moeda-ao-ar")

LIMIAR = 2.5

# Condição 1. Abaixo disto não há como distinguir talento de sorte, por muito
# bom que o número pareça.
MINIMO_FECHADAS = 50


def significancia(resultados_a, resultados_b):
    """
    Quantas vezes a vantagem de A sobre B é maior do que a incerteza da medição.

    Positivo quer dizer que A está à frente. Devolve None quando a conta não se
    pode fazer: é preciso pelo menos duas posições fechadas de cada lado (com
    uma só não há como medir a irregularidade), e os dois lados não podem ser
    ambos constantes, que daria uma divisão por zero.
    """
    if len(resultados_a) < 2 or len(resultados_b) < 2:
        return None

    erro_padrao = math.sqrt(
        statistics.variance(resultados_a) / len(resultados_a)
        + statistics.variance(resultados_b) / len(resultados_b))
    if erro_padrao == 0:
        return None

    return (statistics.fmean(resultados_a) - statistics.fmean(resultados_b)) / erro_padrao


def resultados_por_agente(decisoes, precos):
    """
    {agente: [quanto deu cada posição fechada, em euros]}.

    Só entram as posições já fechadas e com conta feita. As abertas ainda não
    deram nada, e uma venda a descoberto não tem resultado calculado (ver
    posicoes.py), por isso ficam de fora das duas pontas da comparação.
    """
    por_agente = {}
    for estado in posicoes.estado_das_posicoes(decisoes, precos):
        por_agente.setdefault(estado["agente"], [])
        if estado["estado"] != posicoes.ABERTA and estado["resultado_eur"] is not None:
            por_agente[estado["agente"]].append(estado["resultado_eur"])
    return por_agente


def _resumo(resultados):
    return {
        "fechadas": len(resultados),
        "media": statistics.fmean(resultados) if resultados else None,
        "total": sum(resultados),
    }


def _contra_controlos(meus, resultados, limiar):
    """
    O t do agente contra cada controlo, e o veredicto do pior deles.

    Devolve (contra, t_minimo, passa). t_minimo é None quando algum dos dois
    não deu conta calculável -- e uma comparação em falta nunca conta como
    comparação ganha.
    """
    contra = {}
    for controlo in CONTROLOS:
        seus = resultados.get(controlo, [])
        contra[controlo] = dict(_resumo(seus), t=significancia(meus, seus))

    ts = [c["t"] for c in contra.values()]
    t_minimo = min(ts) if ts and all(x is not None for x in ts) else None
    return contra, t_minimo, (t_minimo is not None and t_minimo > limiar)


def sem_a_melhor(resultados):
    """
    A lista sem a posição que deu mais dinheiro. Tira exatamente uma.

    Devolve (restantes, a que saiu). Com a lista vazia devolve (lista, None).
    """
    if not resultados:
        return list(resultados), None
    melhor = max(resultados)
    restantes = list(resultados)
    restantes.remove(melhor)           # tira uma só, mesmo que haja empate
    return restantes, melhor


def avaliar(meus, resultados, limiar=LIMIAR, minimo=MINIMO_FECHADAS):
    """
    Corre as três condições sobre os resultados já apurados de um agente.

    'meus' são os resultados do agente; 'resultados' é o mapa completo, de onde
    saem os dos controlos. Devolve o veredicto -- ver veredictos().
    """
    # 1. apostas que cheguem
    c1 = {
        "fechadas": len(meus),
        "minimo": minimo,
        "passa": len(meus) >= minimo,
    }

    # 2. a vantagem é maior do que a incerteza
    contra2, t2, passa2 = _contra_controlos(meus, resultados, limiar)
    c2 = {"contra": contra2, "t_minimo": t2, "limiar": limiar, "passa": passa2}

    # 3. a mesma conta sem a melhor aposta do agente. Os controlos ficam
    #    intactos de propósito: tirar a melhor dos dois lados tornava o teste
    #    mais brando, e isto existe para ser duro.
    restantes, retirada = sem_a_melhor(meus)
    contra3, t3, passa3 = _contra_controlos(restantes, resultados, limiar)
    c3 = {
        "contra": contra3, "t_minimo": t3, "limiar": limiar,
        "retirada": retirada, "restantes": len(restantes),
        "passa": passa3,
    }

    falhou = next((n for n, c in ((1, c1), (2, c2), (3, c3)) if not c["passa"]), None)
    return {
        "condicao_1": c1, "condicao_2": c2, "condicao_3": c3,
        "passa": falhou is None,
        "falhou": falhou,
    }


def veredictos(decisoes, precos, limiar=LIMIAR, minimo=MINIMO_FECHADAS):
    """
    O veredicto da regra 8 para cada agente que não seja controlo.

    Uma lista, dos que passam para os que não passam:

        {"agente", "fechadas", "media", "total",
         "passa": bool,
         "falhou": None | 1 | 2 | 3,       a PRIMEIRA condição que falhou
         "condicao_1": {"fechadas", "minimo", "passa"},
         "condicao_2": {"contra", "t_minimo", "limiar", "passa"},
         "condicao_3": {"contra", "t_minimo", "limiar", "retirada",
                        "restantes", "passa"}}

    As três são sempre calculadas, mesmo depois de uma falhar: quem estiver a
    ler quer ver os números todos, não só o primeiro que travou.
    """
    resultados = resultados_por_agente(decisoes, precos)
    linhas = []

    for agente, meus in sorted(resultados.items()):
        if agente in CONTROLOS:
            continue
        linhas.append(dict(
            _resumo(meus),
            agente=agente,
            **avaliar(meus, resultados, limiar, minimo)))

    # Primeiro os que passam; dentro de cada grupo, o t da condição 3 (o mais
    # exigente) do maior para o menor.
    def chave(l):
        t = l["condicao_3"]["t_minimo"]
        return (not l["passa"], t is None, -(t if t is not None else 0))

    linhas.sort(key=chave)
    return linhas


def comparar_com_controlos(decisoes, precos, limiar=LIMIAR):
    """
    Só a condição 2, para cada agente. Mantida para quem só quer esse número.

    Devolve uma lista, do t mais alto para o mais baixo:

        {"agente", "fechadas", "media", "total",
         "contra": {controlo: {"t", "fechadas", "media", "total"}},
         "t_minimo", "passa_condicao_2"}
    """
    resultados = resultados_por_agente(decisoes, precos)
    linhas = []

    for agente, meus in sorted(resultados.items()):
        if agente in CONTROLOS:
            continue
        contra, t_minimo, passa = _contra_controlos(meus, resultados, limiar)
        linhas.append(dict(
            _resumo(meus),
            agente=agente, contra=contra,
            t_minimo=t_minimo, passa_condicao_2=passa))

    linhas.sort(key=lambda l: (l["t_minimo"] is None,
                               -(l["t_minimo"] if l["t_minimo"] is not None else 0)))
    return linhas


if __name__ == "__main__":
    import config

    decisoes = posicoes._ler_csv(config.FICHEIRO_DECISOES)
    precos = posicoes._ler_csv(config.FICHEIRO_PRECOS)
    linhas = veredictos(decisoes, precos)

    def t_ou_traco(valor):
        return "—" if valor is None else f"{valor:+.2f}"

    if not linhas:
        print("Ainda não há agentes para avaliar.")

    for l in linhas:
        c1, c2, c3 = l["condicao_1"], l["condicao_2"], l["condicao_3"]
        estado = "PASSA" if l["passa"] else f"não passa (falha a {l['falhou']})"
        print(f"\n{l['agente']}: {estado}")
        print(f"  1. fechadas          {c1['fechadas']} de {c1['minimo']} "
              f"{'ok' if c1['passa'] else 'FALHA'}")
        print(f"  2. t contra os dois  {t_ou_traco(c2['t_minimo'])} "
              f"(preciso > {c2['limiar']}) {'ok' if c2['passa'] else 'FALHA'}")
        for controlo, c in c2["contra"].items():
            print(f"       vs {controlo:24} {t_ou_traco(c['t'])} "
                  f"({c['fechadas']} fechadas)")
        retirada = "—" if c3["retirada"] is None else f"{c3['retirada']:+.2f} EUR"
        print(f"  3. sem a melhor      {t_ou_traco(c3['t_minimo'])} "
              f"(tirou {retirada}, sobram {c3['restantes']}) "
              f"{'ok' if c3['passa'] else 'FALHA'}")

    passaram = [l["agente"] for l in linhas if l["passa"]]
    print()
    if passaram:
        print(f"Passam o critério de seleção: {', '.join(passaram)}")
    else:
        print("Nenhum agente passou o critério de seleção.")
