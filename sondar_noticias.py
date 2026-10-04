"""
Sondagem: há notícias suficientes para valer a pena construir agentes delas?

CORRE UMA VEZ, À MÃO. Isto NÃO é um agente, NÃO toma decisões, NÃO entra no
torneio e NÃO escreve nada em dados/. Só vai contar notícias e dizer o que
encontrou. A decisão de construir ou não construir agentes de notícias é de
quem lê os números, não deste ficheiro.

O QUE MEDE, POR FONTE
---------------------
 1. quantas das 60 empresas tiveram pelo menos uma notícia na janela;
 2. quantas tiveram notícias em pelo menos 10 dias distintos da janela;
 3. média e mediana de notícias por empresa por dia;
 4. as 10 empresas com menos notícias;
 5. o que vem nos campos de data/hora -- em bruto, sem interpretar por cima;
 6. que campos vêm em cada notícia.

PORQUE É QUE A PERGUNTA DA HORA É A QUE INTERESSA
-------------------------------------------------
Um agente de notícias decide uma vez por dia, depois do fecho. Se uma notícia
só trouxer a data, não há maneira de saber se saiu antes ou depois do fecho --
e usar uma notícia que saiu depois do fecho para explicar o preço do fecho é
olhar para o futuro. Com dinheiro simulado isso não dói, mas inventa um agente
que nunca existiria a sério.

Por isso este ficheiro não escreve "tem hora, sim". Despeja os valores em
bruto, diz em que campo vinham, mostra o que dá quando se lê como UTC, e
aponta o que NÃO consegue provar. A diferença entre hora de publicação e hora
de recolha não se vê num campo chamado "time": vê-se a comparar fontes e a
olhar para a distribuição das horas. É isso que a secção 5 faz.

CORRER
------
    python sondar_noticias.py                 # as duas fontes
    python sondar_noticias.py --fonte yfinance
    FINNHUB_API_KEY=xxx python sondar_noticias.py

Escreve sondagem_noticias.json (tudo, para reler) e sondagem_noticias.md
(o resumo para ler). Sem a chave do Finnhub, faz só o yfinance e diz que o
Finnhub ficou de fora -- não inventa números nem falha a corrida.
"""

import argparse
import csv
import datetime as dt
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import config

JANELA_DIAS = 30
DIAS_COM_NOTICIAS_MINIMOS = 10      # o critério 2 da sondagem

FICHEIRO_JSON = "sondagem_noticias.json"
FICHEIRO_RESUMO = "sondagem_noticias.md"

# Quantas notícias em bruto se guardam por fonte para a secção 5 e 6.
EXEMPLOS_EM_BRUTO = 6

# Pausas entre pedidos. O Finnhub grátis dá 60 pedidos por minuto, e são 60
# empresas: 1,1s chega para não bater no limite sem demorar o dobro.
PAUSA_FINNHUB = 1.1
PAUSA_YFINANCE = 0.3

FINNHUB_URL = "https://finnhub.io/api/v1/company-news"

# Nomes de campo que podem trazer data ou hora. Não se assume que existem: isto
# é só a lista de candidatos a procurar, e o que se encontrar é relatado.
PISTAS_DE_TEMPO = ("time", "date", "pub", "publish", "display", "created",
                   "updated", "timestamp", "epoch")


# ---------------------------------------------------------------------------
# utilitários de leitura: nunca assumem a forma do que vem
# ---------------------------------------------------------------------------

def _caminhos(objeto, prefixo=""):
    """
    Todos os caminhos de chaves de uma estrutura aninhada, com tipo e exemplo.

    Devolve {caminho: (nome_do_tipo, exemplo_truncado)}. Serve para responder à
    pergunta 6 sem ter de saber de antemão o que a fonte manda -- se um dia a
    forma mudar, a sondagem relata a forma nova em vez de rebentar.
    """
    encontrados = {}
    if isinstance(objeto, dict):
        for chave, valor in objeto.items():
            caminho = f"{prefixo}.{chave}" if prefixo else str(chave)
            if isinstance(valor, (dict, list)):
                encontrados.update(_caminhos(valor, caminho))
                if isinstance(valor, list) and not valor:
                    encontrados[caminho] = ("list (vazia)", "[]")
            else:
                encontrados[caminho] = (type(valor).__name__,
                                        _curto(valor))
    elif isinstance(objeto, list):
        # Só o primeiro elemento: a lista é de coisas do mesmo tipo e o que
        # interessa é a forma, não quantas são.
        if objeto:
            encontrados.update(_caminhos(objeto[0], f"{prefixo}[]"))
    return encontrados


def _curto(valor, maximo=120):
    texto = str(valor).replace("\n", " ")
    return texto if len(texto) <= maximo else texto[:maximo] + "..."


def _procurar_tempo(objeto, prefixo=""):
    """
    Candidatos a data/hora dentro de uma notícia: [(caminho, valor_em_bruto)].

    Apanha por duas vias, porque nenhuma das duas chega sozinha:
      * o nome da chave parece de tempo (PISTAS_DE_TEMPO);
      * o valor parece um epoch em segundos ou uma data ISO, seja a chave
        chamada o que for.
    """
    achados = []
    if isinstance(objeto, dict):
        for chave, valor in objeto.items():
            caminho = f"{prefixo}.{chave}" if prefixo else str(chave)
            if isinstance(valor, (dict, list)):
                achados.extend(_procurar_tempo(valor, caminho))
                continue
            nome_sugere = any(p in str(chave).lower() for p in PISTAS_DE_TEMPO)
            if nome_sugere or _parece_tempo(valor):
                achados.append((caminho, valor))
    elif isinstance(objeto, list) and objeto:
        achados.extend(_procurar_tempo(objeto[0], f"{prefixo}[]"))
    return achados


def _parece_tempo(valor):
    """Um epoch em segundos ou milissegundos, ou uma data tipo ISO."""
    if isinstance(valor, bool):
        return False
    if isinstance(valor, (int, float)):
        return 1_000_000_000 <= valor <= 4_000_000_000_000
    if isinstance(valor, str) and len(valor) >= 10:
        inicio = valor[:10]
        return (inicio[4:5] in "-/" and inicio[7:8] in "-/"
                and inicio[:4].isdigit())
    return False


def _instante(valor):
    """
    Lê um valor de tempo e devolve (datetime em UTC, como_foi_lido).

    Devolve (None, motivo) quando não dá. Não adivinha fusos: um epoch é UTC
    por definição, uma data ISO com Z ou com deslocamento traz o fuso consigo,
    e uma data ISO sem nada NÃO tem fuso -- e isso é dito em vez de tapado.
    """
    if isinstance(valor, bool) or valor is None:
        return None, "não é tempo"

    if isinstance(valor, (int, float)):
        segundos = valor / 1000.0 if valor > 4_000_000_000 else float(valor)
        unidade = "epoch em milissegundos" if valor > 4_000_000_000 else "epoch em segundos"
        try:
            return (dt.datetime.fromtimestamp(segundos, dt.timezone.utc),
                    f"{unidade} (epoch é sempre UTC)")
        except (OverflowError, OSError, ValueError):
            return None, "epoch fora de alcance"

    if isinstance(valor, str):
        texto = valor.strip()
        if texto.endswith("Z"):
            texto_iso, como = texto[:-1] + "+00:00", "ISO com Z, ou seja UTC"
        else:
            texto_iso = texto
            tem_fuso = ("+" in texto[10:] or
                        (texto[10:].count("-") > 0 and ":" in texto[10:]))
            como = ("ISO com deslocamento de fuso" if tem_fuso
                    else "ISO SEM FUSO -- o fuso não vem nos dados")
        try:
            lido = dt.datetime.fromisoformat(texto_iso)
        except ValueError:
            return None, "texto que não se consegue ler como ISO"
        if lido.tzinfo is None:
            return lido.replace(tzinfo=dt.timezone.utc), como
        return lido.astimezone(dt.timezone.utc), como

    return None, f"tipo inesperado ({type(valor).__name__})"


# ---------------------------------------------------------------------------
# as fontes
# ---------------------------------------------------------------------------

def noticias_yfinance(tickers, inicio, fim):
    """
    O campo .news de cada Ticker. Devolve (por_ticker, erros, nota_de_acesso).

    O .news não é uma API documentada do Yahoo: a forma já mudou entre versões
    do yfinance, e nada garante que devolva a janela toda em vez das últimas N.
    Por isso o caminho de acesso que funcionou fica registado, e a cobertura
    real da janela é medida em vez de assumida.
    """
    import yfinance as yf

    por_ticker, erros = {}, {}
    nota = {"versao_yfinance": getattr(yf, "__version__", "desconhecida"),
            "caminho_de_acesso": None}

    for i, ticker in enumerate(tickers):
        try:
            alvo = yf.Ticker(ticker)
            itens, caminho = _ler_news(alvo)
            nota["caminho_de_acesso"] = nota["caminho_de_acesso"] or caminho
            por_ticker[ticker] = itens or []
        except Exception as erro:
            erros[ticker] = f"{type(erro).__name__}: {str(erro)[:200]}"
            por_ticker[ticker] = []
        if i + 1 < len(tickers):
            time.sleep(PAUSA_YFINANCE)

    return por_ticker, erros, nota


def _ler_news(alvo):
    """
    Tenta as várias maneiras de pedir notícias a um Ticker, pela ordem que dá
    mais itens primeiro. Devolve (itens, descrição do caminho que funcionou).
    """
    try:
        return alvo.get_news(count=100), "get_news(count=100)"
    except TypeError:
        pass                                   # versão sem o parâmetro count
    except AttributeError:
        pass                                   # versão sem get_news
    try:
        return alvo.get_news(), "get_news()"
    except AttributeError:
        pass
    return alvo.news, ".news"


def noticias_finnhub(tickers, inicio, fim, chave):
    """
    O endpoint company-news do Finnhub, um pedido por empresa.

    Devolve (por_ticker, erros, nota_de_acesso). A chave nunca é impressa nem
    guardada em ficheiro: entra no URL no último momento e as mensagens de erro
    são limpas antes de sair daqui.
    """
    por_ticker, erros = {}, {}
    nota = {"endpoint": FINNHUB_URL,
            "janela_pedida": f"{inicio.isoformat()} a {fim.isoformat()}"}

    for i, ticker in enumerate(tickers):
        parametros = urllib.parse.urlencode({
            "symbol": ticker,
            "from": inicio.isoformat(),
            "to": fim.isoformat(),
            "token": chave,
        })
        pedido = urllib.request.Request(
            f"{FINNHUB_URL}?{parametros}",
            headers={"User-Agent": "agente-acoes/1.0 (sondagem; python)"})
        try:
            with urllib.request.urlopen(pedido, timeout=60) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
            por_ticker[ticker] = dados if isinstance(dados, list) else []
            if not isinstance(dados, list):
                erros[ticker] = f"resposta não foi uma lista: {_curto(dados, 150)}"
        except Exception as erro:
            erros[ticker] = _sem_chave(
                f"{type(erro).__name__}: {str(erro)[:200]}", chave)
            por_ticker[ticker] = []
        if i + 1 < len(tickers):
            time.sleep(PAUSA_FINNHUB)

    return por_ticker, erros, nota


def _sem_chave(texto, chave):
    """Tira a chave de qualquer texto que vá para o ecrã ou para ficheiro."""
    return texto.replace(chave, "***") if chave else texto


# ---------------------------------------------------------------------------
# as contas
# ---------------------------------------------------------------------------

def dias_de_bolsa(inicio, fim, ficheiro=None):
    """
    Os dias da janela em que houve bolsa, tirados do precos.csv.

    Um agente só decide em dias de bolsa, por isso "teve notícias em 10 dos 30
    dias" diz uma coisa e "teve notícias em 10 dos dias em que havia decisão a
    tomar" diz outra. Mede-se as duas. Se o ficheiro não existir, devolve
    vazio e a coluna dos dias de bolsa fica a None em vez de inventada.
    """
    caminho = ficheiro or config.FICHEIRO_PRECOS
    if not os.path.exists(caminho):
        return set()
    with open(caminho, newline="", encoding="utf-8") as f:
        datas = {linha["data"] for linha in csv.DictReader(f)}
    return {d for d in datas if inicio.isoformat() <= d <= fim.isoformat()}


def medir(por_ticker, inicio, fim, bolsa):
    """
    As respostas 1 a 4, mais a cobertura real da janela.

    Uma notícia conta para um dia pela data UTC do seu instante. Notícias sem
    instante legível são contadas à parte: entram no total e não entram em
    nenhum dia, e o número delas é relatado -- se for grande, as contagens por
    dia valem menos e isso tem de se ver.
    """
    por_empresa, sem_instante_total = {}, 0
    for ticker, itens in por_ticker.items():
        dias, instantes, sem_instante = set(), [], 0
        for item in itens:
            quando = _instante_do_item(item)
            if quando is None:
                sem_instante += 1
                continue
            instantes.append(quando)
            dias.add(quando.date().isoformat())
        sem_instante_total += sem_instante
        na_janela = [q for q in instantes
                     if inicio <= q.date() <= fim]
        dias_na_janela = {d for d in dias
                          if inicio.isoformat() <= d <= fim.isoformat()}
        por_empresa[ticker] = {
            "noticias": len(itens),
            "noticias_na_janela": len(na_janela),
            "sem_instante": sem_instante,
            "dias_distintos": len(dias_na_janela),
            "dias_de_bolsa_cobertos": len(dias_na_janela & bolsa) if bolsa else None,
            "mais_antiga": min(instantes).isoformat() if instantes else None,
            "mais_recente": max(instantes).isoformat() if instantes else None,
        }

    totais = [e["noticias_na_janela"] for e in por_empresa.values()]
    por_dia = [n / JANELA_DIAS for n in totais]
    com_alguma = [t for t, e in por_empresa.items()
                  if e["noticias_na_janela"] >= 1]
    com_dez_dias = [t for t, e in por_empresa.items()
                    if e["dias_distintos"] >= DIAS_COM_NOTICIAS_MINIMOS]

    piores = sorted(por_empresa.items(),
                    key=lambda par: (par[1]["noticias_na_janela"], par[0]))[:10]

    # Cobertura: a mais antiga de cada empresa diz até onde a fonte foi mesmo.
    idades = [(fim - dt.date.fromisoformat(e["mais_antiga"][:10])).days
              for e in por_empresa.values() if e["mais_antiga"]]

    return {
        "empresas": len(por_empresa),
        "empresas_com_pelo_menos_uma": len(com_alguma),
        "empresas_sem_nenhuma": sorted(set(por_ticker) - set(com_alguma)),
        "empresas_com_noticias_em_10_dias": len(com_dez_dias),
        "total_de_noticias_na_janela": sum(totais),
        "noticias_sem_instante_legivel": sem_instante_total,
        "media_por_empresa_por_dia": round(statistics.mean(por_dia), 3) if por_dia else None,
        "mediana_por_empresa_por_dia": round(statistics.median(por_dia), 3) if por_dia else None,
        "media_por_empresa_na_janela": round(statistics.mean(totais), 2) if totais else None,
        "mediana_por_empresa_na_janela": statistics.median(totais) if totais else None,
        "mediana_dias_distintos": statistics.median(
            [e["dias_distintos"] for e in por_empresa.values()]) if por_empresa else None,
        "dez_com_menos": [{"ticker": t, **e} for t, e in piores],
        "cobertura_dias_para_tras": {
            "mediana": statistics.median(idades) if idades else None,
            "maxima": max(idades) if idades else None,
            "empresas_que_chegam_aos_30": sum(1 for i in idades if i >= 29),
        },
        "por_empresa": por_empresa,
    }


def _instante_do_item(item):
    """O melhor instante de uma notícia, ou None. Prefere o primeiro legível."""
    for _, valor in _procurar_tempo(item):
        quando, _ = _instante(valor)
        if quando is not None:
            return quando
    return None


def analisar_tempo(por_ticker, agora):
    """
    A resposta 5: o que os campos de tempo trazem mesmo.

    Três coisas, porque nenhuma responde sozinha:
      * que campos de tempo existem, com valores em bruto e como se leem;
      * se a parte da hora é sempre 00:00:00 -- se for, é data e não hora;
      * a distribuição de "há quanto tempo" cada notícia diz ter saído. Se
        muitas disserem o instante da corrida, é hora de recolha e não de
        publicação. Isto é um indício, não uma prova, e é dito como indício.
    """
    campos, exemplos = {}, []
    horas_zero, horas_totais = 0, 0
    minutos_do_dia = []
    atrasos_horas = []
    futuras = 0

    for ticker, itens in por_ticker.items():
        for item in itens:
            for caminho, valor in _procurar_tempo(item):
                quando, como = _instante(valor)
                registo = campos.setdefault(caminho, {
                    "vezes": 0, "como_se_le": como, "exemplos_em_bruto": [],
                    "tipo": type(valor).__name__, "ilegiveis": 0,
                })
                registo["vezes"] += 1
                if quando is None:
                    registo["ilegiveis"] += 1
                if len(registo["exemplos_em_bruto"]) < 3:
                    registo["exemplos_em_bruto"].append({
                        "ticker": ticker,
                        "em_bruto": valor,
                        "lido_como_utc": quando.isoformat() if quando else None,
                    })

            quando = _instante_do_item(item)
            if quando is None:
                continue
            horas_totais += 1
            if (quando.hour, quando.minute, quando.second) == (0, 0, 0):
                horas_zero += 1
            minutos_do_dia.append(quando.hour * 60 + quando.minute)
            delta = (agora - quando).total_seconds() / 3600.0
            atrasos_horas.append(delta)
            if delta < 0:
                futuras += 1

    perto_da_corrida = sum(1 for a in atrasos_horas if abs(a) < 0.25)

    for ticker, itens in por_ticker.items():
        for item in itens[:2]:
            if len(exemplos) < EXEMPLOS_EM_BRUTO:
                exemplos.append({"ticker": ticker, "noticia_em_bruto": item})

    return {
        "campos_de_tempo": campos,
        "noticias_com_instante": horas_totais,
        "com_hora_a_zero": horas_zero,
        "parece_so_data": horas_totais > 0 and horas_zero == horas_totais,
        "horas_utc_distintas": len(set(minutos_do_dia)),
        "distribuicao_do_atraso_em_horas": {
            "minimo": round(min(atrasos_horas), 2) if atrasos_horas else None,
            "mediana": round(statistics.median(atrasos_horas), 2) if atrasos_horas else None,
            "maximo": round(max(atrasos_horas), 2) if atrasos_horas else None,
        },
        "com_instante_no_futuro": futuras,
        "a_menos_de_15min_da_corrida": perto_da_corrida,
        "exemplos_em_bruto": exemplos,
    }


def inventario_de_campos(por_ticker):
    """A resposta 6: que campos vêm, quantas vezes, com exemplo."""
    contagem, exemplos, tipos, total = {}, {}, {}, 0
    for itens in por_ticker.values():
        for item in itens:
            total += 1
            for caminho, (tipo, exemplo) in _caminhos(item).items():
                contagem[caminho] = contagem.get(caminho, 0) + 1
                tipos.setdefault(caminho, tipo)
                exemplos.setdefault(caminho, exemplo)
    return {
        "noticias_observadas": total,
        "campos": [
            {"campo": c, "tipo": tipos[c], "em_quantas": contagem[c],
             "em_percentagem": round(100 * contagem[c] / total, 1) if total else 0,
             "exemplo": exemplos[c]}
            for c in sorted(contagem, key=lambda c: (-contagem[c], c))
        ],
    }


def comparar_fontes(resultados):
    """
    A mesma notícia nas duas fontes: as horas batem certo?

    É a única maneira honesta de atacar a pergunta "publicação ou recolha?".
    Duas fontes que recolheram em momentos diferentes e dão a mesma hora estão
    a dar a hora de publicação. Se derem horas muito diferentes, pelo menos uma
    delas não é hora de publicação -- e aí não dá para saber qual sem ir ao
    artigo. Isso é dito, não resolvido por adivinha.
    """
    nomes = [n for n in resultados if resultados[n].get("por_ticker")]
    if len(nomes) < 2:
        return {"possivel": False,
                "motivo": "é preciso haver duas fontes com dados"}

    def indexar(por_ticker):
        indice = {}
        for ticker, itens in por_ticker.items():
            for item in itens:
                titulo = _titulo(item)
                quando = _instante_do_item(item)
                if titulo and quando:
                    indice.setdefault((ticker, _chave_de_titulo(titulo)),
                                      []).append((titulo, quando))
        return indice

    a, b = nomes[0], nomes[1]
    ia = indexar(resultados[a]["por_ticker"])
    ib = indexar(resultados[b]["por_ticker"])
    comuns = set(ia) & set(ib)

    pares = []
    for chave in sorted(comuns)[:20]:
        titulo_a, quando_a = ia[chave][0]
        titulo_b, quando_b = ib[chave][0]
        pares.append({
            "ticker": chave[0],
            "titulo": _curto(titulo_a, 90),
            f"instante_{a}": quando_a.isoformat(),
            f"instante_{b}": quando_b.isoformat(),
            "diferenca_em_minutos": round(
                (quando_a - quando_b).total_seconds() / 60.0, 1),
        })

    difs = [abs(p["diferenca_em_minutos"]) for p in pares]
    return {
        "possivel": True,
        "fontes": [a, b],
        "titulos_iguais_encontrados": len(comuns),
        "diferenca_absoluta_em_minutos": {
            "mediana": round(statistics.median(difs), 1) if difs else None,
            "maxima": max(difs) if difs else None,
            "iguais_ao_minuto": sum(1 for d in difs if d < 1),
        },
        "pares": pares,
    }


def _titulo(item):
    """O título de uma notícia, onde quer que ele venha."""
    for caminho in ("title", "headline", "content.title", "content.headline"):
        valor = item
        for parte in caminho.split("."):
            valor = valor.get(parte) if isinstance(valor, dict) else None
            if valor is None:
                break
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return None


def _chave_de_titulo(titulo):
    """Título normalizado, para casar a mesma notícia entre fontes."""
    limpo = "".join(c.lower() if c.isalnum() else " " for c in titulo)
    return " ".join(limpo.split())[:80]


# ---------------------------------------------------------------------------
# o resumo em texto
# ---------------------------------------------------------------------------

def escrever_resumo(relatorio):
    linhas = ["# Sondagem de notícias", ""]
    linhas.append(f"Corrida a {relatorio['corrido_em']} (UTC). "
                  f"Janela: {relatorio['janela']['inicio']} a "
                  f"{relatorio['janela']['fim']} "
                  f"({relatorio['janela']['dias']} dias de calendário, "
                  f"{relatorio['janela']['dias_de_bolsa']} de bolsa). "
                  f"{relatorio['empresas']} empresas.")
    linhas.append("")
    linhas.append("**Isto é uma sondagem.** Não decide nada e não cria "
                  "agentes nenhuns.")
    linhas.append("")

    for nome, fonte in relatorio["fontes"].items():
        linhas.append(f"## {nome}")
        linhas.append("")
        if not fonte.get("correu"):
            linhas.append(f"Não correu: {fonte.get('motivo')}")
            linhas.append("")
            continue

        m = fonte["medidas"]
        t = fonte["tempo"]
        linhas.append(f"- **1. com pelo menos uma notícia:** "
                      f"{m['empresas_com_pelo_menos_uma']} de {m['empresas']}")
        linhas.append(f"- **2. com notícias em {DIAS_COM_NOTICIAS_MINIMOS}+ "
                      f"dias distintos:** {m['empresas_com_noticias_em_10_dias']} "
                      f"de {m['empresas']}")
        linhas.append(f"- **3. por empresa por dia:** média "
                      f"{m['media_por_empresa_por_dia']}, mediana "
                      f"{m['mediana_por_empresa_por_dia']}")
        linhas.append(f"  (na janela toda: média {m['media_por_empresa_na_janela']}, "
                      f"mediana {m['mediana_por_empresa_na_janela']} notícias)")
        linhas.append(f"- total de notícias na janela: "
                      f"{m['total_de_noticias_na_janela']}")
        linhas.append(f"- notícias sem instante legível: "
                      f"{m['noticias_sem_instante_legivel']}")
        cob = m["cobertura_dias_para_tras"]
        linhas.append(f"- **cobertura real:** a notícia mais antiga de cada "
                      f"empresa está a {cob['mediana']} dias (mediana), "
                      f"{cob['maxima']} no máximo; "
                      f"{cob['empresas_que_chegam_aos_30']} empresas chegam "
                      f"aos 30 dias")
        if fonte.get("erros"):
            linhas.append(f"- empresas com erro: {len(fonte['erros'])}")
        linhas.append("")

        linhas.append("### 4. as 10 com menos notícias")
        linhas.append("")
        linhas.append("| ticker | notícias | dias distintos | mais recente |")
        linhas.append("|---|---:|---:|---|")
        for e in m["dez_com_menos"]:
            linhas.append(f"| {e['ticker']} | {e['noticias_na_janela']} | "
                          f"{e['dias_distintos']} | "
                          f"{e['mais_recente'] or '—'} |")
        linhas.append("")

        linhas.append("### 5. data e hora")
        linhas.append("")
        linhas.append(f"- notícias com instante legível: "
                      f"{t['noticias_com_instante']}")
        linhas.append(f"- com a hora exactamente a 00:00:00: "
                      f"{t['com_hora_a_zero']}")
        linhas.append(f"- **só data, sem hora:** "
                      f"{'SIM' if t['parece_so_data'] else 'não'}")
        linhas.append(f"- horas distintas do dia observadas: "
                      f"{t['horas_utc_distintas']}")
        d = t["distribuicao_do_atraso_em_horas"]
        linhas.append(f"- idade das notícias em horas: mínimo {d['minimo']}, "
                      f"mediana {d['mediana']}, máximo {d['maximo']}")
        linhas.append(f"- com instante no futuro: {t['com_instante_no_futuro']}")
        linhas.append(f"- a menos de 15 min do momento da corrida: "
                      f"{t['a_menos_de_15min_da_corrida']}")
        linhas.append("")
        linhas.append("Campos de tempo encontrados:")
        linhas.append("")
        linhas.append("| campo | tipo | vezes | como se lê |")
        linhas.append("|---|---|---:|---|")
        for campo, info in sorted(t["campos_de_tempo"].items(),
                                  key=lambda p: -p[1]["vezes"]):
            linhas.append(f"| `{campo}` | {info['tipo']} | {info['vezes']} | "
                          f"{info['como_se_le']} |")
        linhas.append("")
        for campo, info in sorted(t["campos_de_tempo"].items(),
                                  key=lambda p: -p[1]["vezes"]):
            for ex in info["exemplos_em_bruto"]:
                linhas.append(f"- `{campo}` em {ex['ticker']}: "
                              f"`{ex['em_bruto']!r}` → "
                              f"{ex['lido_como_utc'] or 'não se lê'}")
        linhas.append("")

        linhas.append("### 6. campos de cada notícia")
        linhas.append("")
        linhas.append("| campo | tipo | em % das notícias | exemplo |")
        linhas.append("|---|---|---:|---|")
        for c in fonte["campos"]["campos"]:
            exemplo = str(c["exemplo"]).replace("|", "\\|")
            linhas.append(f"| `{c['campo']}` | {c['tipo']} | "
                          f"{c['em_percentagem']}% | {exemplo} |")
        linhas.append("")

    comp = relatorio["comparacao_entre_fontes"]
    linhas.append("## As duas fontes dão a mesma hora?")
    linhas.append("")
    if not comp.get("possivel"):
        linhas.append(f"Não se pôde comparar: {comp.get('motivo')}")
    else:
        dif = comp["diferenca_absoluta_em_minutos"]
        linhas.append(f"Títulos iguais nas duas fontes: "
                      f"{comp['titulos_iguais_encontrados']}. "
                      f"Diferença absoluta de hora: mediana "
                      f"{dif['mediana']} min, máxima {dif['maxima']} min, "
                      f"{dif['iguais_ao_minuto']} iguais ao minuto.")
        if comp["pares"]:
            linhas.append("")
            cabecalhos = [k for k in comp["pares"][0] if k != "titulo"]
            linhas.append("| " + " | ".join(cabecalhos) + " | título |")
            linhas.append("|" + "---|" * (len(cabecalhos) + 1))
            for p in comp["pares"][:10]:
                valores = [str(p[k]) for k in cabecalhos]
                linhas.append("| " + " | ".join(valores) + f" | {p['titulo']} |")
    linhas.append("")

    with open(FICHEIRO_RESUMO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


# ---------------------------------------------------------------------------

def main(argumentos=None):
    analise = argparse.ArgumentParser(description="Sondagem de notícias.")
    analise.add_argument("--fonte", choices=["yfinance", "finnhub", "todas"],
                         default="todas")
    analise.add_argument("--dias", type=int, default=JANELA_DIAS)
    opcoes = analise.parse_args(argumentos)

    agora = dt.datetime.now(dt.timezone.utc)
    fim = agora.date()
    inicio = fim - dt.timedelta(days=opcoes.dias)
    tickers = list(config.EMPRESAS)
    bolsa = dias_de_bolsa(inicio, fim)

    print(f"Sondagem de notícias -- {len(tickers)} empresas, "
          f"{inicio} a {fim} ({opcoes.dias} dias)")
    print(f"Dias de bolsa na janela, pelo precos.csv: {len(bolsa)}")
    print("Isto é uma sondagem: não decide nada e não cria agentes.\n")

    fontes = {}

    if opcoes.fonte in ("yfinance", "todas"):
        print("yfinance: a ir buscar o .news de cada empresa...")
        try:
            por_ticker, erros, nota = noticias_yfinance(tickers, inicio, fim)
            fontes["yfinance"] = {"correu": True, "por_ticker": por_ticker,
                                  "erros": erros, "acesso": nota}
            print(f"  {sum(len(v) for v in por_ticker.values())} notícias, "
                  f"{len(erros)} empresas com erro "
                  f"(via {nota['caminho_de_acesso']}, "
                  f"yfinance {nota['versao_yfinance']})")
        except Exception as erro:
            fontes["yfinance"] = {
                "correu": False,
                "motivo": f"{type(erro).__name__}: {str(erro)[:300]}"}
            print(f"  ERRO: {fontes['yfinance']['motivo']}")

    if opcoes.fonte in ("finnhub", "todas"):
        chave = os.environ.get("FINNHUB_API_KEY", "").strip()
        if not chave:
            fontes["finnhub"] = {
                "correu": False,
                "motivo": ("falta a chave. Põe-se FINNHUB_API_KEY no ambiente "
                           "(no workflow, em Settings > Secrets). A sondagem "
                           "continua só com o yfinance em vez de falhar.")}
            print(f"finnhub: {fontes['finnhub']['motivo']}")
        else:
            print(f"finnhub: um pedido por empresa, "
                  f"{PAUSA_FINNHUB}s entre cada (limite do plano grátis)...")
            por_ticker, erros, nota = noticias_finnhub(
                tickers, inicio, fim, chave)
            fontes["finnhub"] = {"correu": True, "por_ticker": por_ticker,
                                 "erros": erros, "acesso": nota}
            print(f"  {sum(len(v) for v in por_ticker.values())} notícias, "
                  f"{len(erros)} empresas com erro")

    for nome, fonte in fontes.items():
        if fonte.get("correu"):
            fonte["medidas"] = medir(fonte["por_ticker"], inicio, fim, bolsa)
            fonte["tempo"] = analisar_tempo(fonte["por_ticker"], agora)
            fonte["campos"] = inventario_de_campos(fonte["por_ticker"])

    relatorio = {
        "corrido_em": agora.isoformat(),
        "janela": {"inicio": inicio.isoformat(), "fim": fim.isoformat(),
                   "dias": opcoes.dias, "dias_de_bolsa": len(bolsa)},
        "empresas": len(tickers),
        "fontes": fontes,
        "comparacao_entre_fontes": comparar_fontes(fontes),
    }

    # O JSON leva tudo, incluindo as notícias em bruto -- é o que permite
    # voltar a estas contas sem ir outra vez à rede.
    with open(FICHEIRO_JSON, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)
    escrever_resumo(relatorio)

    print(f"\n{FICHEIRO_JSON} e {FICHEIRO_RESUMO} escritos.\n")
    print(open(FICHEIRO_RESUMO, encoding="utf-8").read())

    # Só falha se nenhuma fonte correu: uma fonte em baixo não deve esconder
    # o que a outra tem para dizer.
    return 0 if any(f.get("correu") for f in fontes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
