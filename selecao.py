"""
A condição 2 da regra 8: a vantagem sobre os controlos é a sério?

Um agente pode acabar acima da moeda ao ar por ter tido sorte. Esta conta
pergunta se a vantagem é maior do que a incerteza com que foi medida -- ou seja,
se sobreviveria a repetir o torneio.

COMO SE MEDE
------------
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


def comparar_com_controlos(decisoes, precos, limiar=LIMIAR):
    """
    Para cada agente que não seja controlo, o t contra cada um dos controlos.

    Devolve uma lista, do t mais alto para o mais baixo:

        {"agente", "fechadas", "media", "total",
         "contra": {controlo: {"t", "fechadas", "media", "total"}},
         "t_minimo", "passa_condicao_2"}

    t_minimo é o pior dos dois: é esse que decide, porque a vantagem tem de se
    aguentar contra os dois controlos, não só contra o mais fácil.
    """
    resultados = resultados_por_agente(decisoes, precos)
    linhas = []

    for agente, meus in sorted(resultados.items()):
        if agente in CONTROLOS:
            continue

        contra = {}
        for controlo in CONTROLOS:
            seus = resultados.get(controlo, [])
            contra[controlo] = dict(_resumo(seus),
                                    t=significancia(meus, seus))

        ts = [c["t"] for c in contra.values()]
        # Sem os dois controlos calculáveis não há veredicto nenhum: uma
        # comparação em falta não é uma comparação ganha.
        t_minimo = min(ts) if ts and all(t is not None for t in ts) else None

        linhas.append(dict(
            _resumo(meus),
            agente=agente,
            contra=contra,
            t_minimo=t_minimo,
            passa_condicao_2=(t_minimo is not None and t_minimo > limiar),
        ))

    linhas.sort(key=lambda l: (l["t_minimo"] is None,
                               -(l["t_minimo"] if l["t_minimo"] is not None else 0)))
    return linhas


if __name__ == "__main__":
    import config

    decisoes = posicoes._ler_csv(config.FICHEIRO_DECISOES)
    precos = posicoes._ler_csv(config.FICHEIRO_PRECOS)
    linhas = comparar_com_controlos(decisoes, precos)

    if not linhas:
        print("Ainda não há agentes para comparar.")
    for l in linhas:
        t = "—" if l["t_minimo"] is None else f"{l['t_minimo']:+.2f}"
        estado = "passa" if l["passa_condicao_2"] else "não passa"
        print(f"{l['agente']:24} {l['fechadas']:>4} fechadas  t={t:>7}  {estado}")
        for controlo, c in l["contra"].items():
            seu_t = "—" if c["t"] is None else f"{c['t']:+.2f}"
            print(f"    contra {controlo:24} t={seu_t:>7}  "
                  f"({c['fechadas']} fechadas)")
    print(f"\nCondição 2 da regra 8: é preciso t > {LIMIAR} contra os dois controlos.")
