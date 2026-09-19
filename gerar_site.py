"""
Escreve o index.html a partir dos CSV.

Corre depois do correr_diario.py, todos os dias, e o index.html vai no mesmo
commit dos dados.

NÃO grava resultados em ficheiro nenhum. Tudo o que a página mostra é
recalculado de raiz a cada corrida, a partir do dados/precos.csv e do
dados/decisoes.csv, pelo posicoes.py -- regras 6 e 7 do README. O index.html é
só o desenho de um cálculo que se refaz sozinho; apagá-lo não perde nada.

Correr à mão:
    python gerar_site.py
"""

import csv
import html
import os
import sys
from datetime import datetime, timezone

import config
import posicoes

FICHEIRO_SITE = "index.html"

AVISO = (
    "FASE DE TESTE TÉCNICO. O torneio a sério começa a 24 de outubro de 2026. "
    "Estes números não significam nada ainda. Com rácio 3:1, as perdas aparecem "
    "em dias e os ganhos em semanas — por isso é normal a tabela parecer má no "
    "início."
)


# ---------------------------------------------------------------------------
# Números
# ---------------------------------------------------------------------------

def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _fmt(valor, casas=2, sinal=False):
    """1234.5 -> '1 234,50'. Vírgula decimal e espaço nos milhares."""
    if valor is None:
        return "—"
    texto = f"{abs(valor):,.{casas}f}".replace(",", " ").replace(".", ",")
    if valor < 0:
        return f"-{texto}"
    return f"+{texto}" if sinal else texto


def _classe(valor):
    """A classe CSS que distingue ganhos de perdas."""
    if valor is None or valor == 0:
        return ""
    return " class=\"pos\"" if valor > 0 else " class=\"neg\""


def _celula_num(valor, texto=None, classe_cor=True):
    """<td> alinhado à direita, com o valor cru para a ordenação."""
    cor = _classe(valor) if classe_cor else ""
    visivel = texto if texto is not None else _fmt(valor)
    crua = "" if valor is None else f"{valor:.6f}"
    marca = cor.replace('class="', 'class="num ') if cor else ' class="num"'
    return f'<td{marca} data-v="{crua}">{html.escape(visivel)}</td>'


# ---------------------------------------------------------------------------
# Contas
# ---------------------------------------------------------------------------

def recolher(decisoes, precos, agora=None):
    """
    Junta tudo o que a página mostra, já calculado.

    Uma decisão conta como CERTA se deu dinheiro depois de custos. Não se usa
    "fechou no alvo", porque uma posição fechada por tempo pode acabar dos dois
    lados e ficaria de fora da conta.
    """
    agora = agora or datetime.now(timezone.utc)
    estados = posicoes.estado_das_posicoes(decisoes, precos)

    ultimo_fecho = {}
    for linha in sorted(precos, key=lambda l: l["data"]):
        fecho = _numero(linha.get("fecho"))
        if fecho is not None:
            ultimo_fecho[linha["ticker"]] = fecho

    por_agente = {}
    em_curso = []
    fechadas = []

    # estado_das_posicoes devolve pela mesma ordem das decisões, por isso
    # dá para ir buscar o stop e o alvo à decisão que lhe deu origem.
    for decisao, estado in zip(decisoes, estados):
        agente = por_agente.setdefault(decisao["agente"], {
            "nome": decisao["agente"], "fechadas": 0, "certas": 0,
            "total": 0.0, "ganhos": [], "perdas": [], "abertas": 0,
        })

        if estado["estado"] == posicoes.ABERTA:
            agente["abertas"] += 1
            entrada = _numero(decisao.get("preco_entrada"))
            alvo = _numero(decisao.get("alvo"))
            atual = ultimo_fecho.get(decisao["ticker"])
            caminho = None
            if None not in (entrada, alvo, atual) and alvo != entrada:
                caminho = (atual - entrada) / (alvo - entrada) * 100
            em_curso.append({
                "agente": decisao["agente"], "ticker": decisao["ticker"],
                "entrada": entrada, "atual": atual,
                "stop": _numero(decisao.get("stop")), "alvo": alvo,
                "caminho": caminho,
            })
            continue

        agente["fechadas"] += 1
        resultado = estado["resultado_eur"]
        if resultado is not None:
            agente["total"] += resultado
            if resultado > 0:
                agente["certas"] += 1
                agente["ganhos"].append(resultado)
            else:
                agente["perdas"].append(resultado)
        fechadas.append({
            "data": estado["data_saida"] or estado["data"],
            "agente": decisao["agente"], "ticker": decisao["ticker"],
            "estado": estado["estado"], "resultado": resultado,
        })

    agentes = []
    for a in por_agente.values():
        agentes.append({
            "nome": a["nome"],
            "fechadas": a["fechadas"],
            "certas": a["certas"],
            "acerto": (a["certas"] / a["fechadas"] * 100) if a["fechadas"] else None,
            "total": a["total"],
            "ganho_medio": (sum(a["ganhos"]) / len(a["ganhos"])) if a["ganhos"] else None,
            "perda_media": (sum(a["perdas"]) / len(a["perdas"])) if a["perdas"] else None,
            "abertas": a["abertas"],
        })
    agentes.sort(key=lambda a: a["total"], reverse=True)

    # Da mais adiantada para a menos. Sem caminho calculável vai para o fim.
    em_curso.sort(key=lambda p: (p["caminho"] is None,
                                 -(p["caminho"] if p["caminho"] is not None else 0)))
    fechadas.sort(key=lambda f: f["data"], reverse=True)

    return {
        "atualizado": agora.strftime("%Y-%m-%d %H:%M UTC"),
        "dias": len({l["data"] for l in precos}),
        "decisoes": len(decisoes),
        "abertas": sum(1 for e in estados if e["estado"] == posicoes.ABERTA),
        "fechadas": sum(1 for e in estados if e["estado"] != posicoes.ABERTA),
        "agentes": agentes,
        "em_curso": em_curso,
        "ultimas": fechadas[:20],
    }


# ---------------------------------------------------------------------------
# Desenho
# ---------------------------------------------------------------------------

ESTILO = """
:root {
  --fundo: #fbfaf8; --caixa: #ffffff; --texto: #1a1a1a; --suave: #5c5c5c;
  --risco: #e3e0d9; --aviso-fundo: #fdf6e3; --aviso-risco: #d8bf7a;
  --sobe: #10673a; --desce: #a3281f; --realce: #f2efe9;
}
@media (prefers-color-scheme: dark) {
  :root {
    --fundo: #16161a; --caixa: #1d1d22; --texto: #ececea; --suave: #9a9a96;
    --risco: #32323a; --aviso-fundo: #2a2418; --aviso-risco: #7a6530;
    --sobe: #58c68d; --desce: #f2867a; --realce: #26262d;
  }
}
* { box-sizing: border-box; }
html, body { max-width: 100%; overflow-x: hidden; }
body {
  margin: 0; padding: 16px;
  background: var(--fundo); color: var(--texto);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  line-height: 1.55; -webkit-font-smoothing: antialiased;
}
main { max-width: 60rem; margin: 0 auto; }
h1 { margin: 0 0 0.2rem; font-size: clamp(1.6rem, 5vw, 2.2rem); letter-spacing: -0.02em; }
h2 { margin: 2.5rem 0 0.4rem; font-size: clamp(1.1rem, 3.5vw, 1.35rem); letter-spacing: -0.01em; }
p { margin: 0 0 1rem; }
.data { margin: 0 0 1.5rem; color: var(--suave); font-size: 0.9rem; }
.legenda { color: var(--suave); font-size: 0.88rem; margin: 0.5rem 0 0; }

.aviso {
  background: var(--aviso-fundo); border: 1px solid var(--aviso-risco);
  border-left-width: 4px; border-radius: 6px;
  padding: 0.9rem 1.1rem; margin: 0 0 1.5rem;
}
.aviso p { margin: 0; }

.contagens {
  display: grid; gap: 0.6rem; margin: 0 0 1rem;
  grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));
}
.contagem {
  background: var(--caixa); border: 1px solid var(--risco);
  border-radius: 6px; padding: 0.7rem 0.85rem;
}
.contagem .valor { font-size: 1.5rem; font-weight: 650; font-variant-numeric: tabular-nums; }
.contagem .etiqueta { color: var(--suave); font-size: 0.82rem; }

.rolar { overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100%; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
th, td { padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--risco); white-space: nowrap; }
thead th {
  text-align: left; font-weight: 600; font-size: 0.82rem;
  text-transform: uppercase; letter-spacing: 0.04em; color: var(--suave);
  border-bottom-width: 2px;
}
.ordenavel thead th { cursor: pointer; user-select: none; }
.ordenavel thead th:focus-visible { outline: 2px solid var(--texto); outline-offset: -2px; }
.ordenavel thead th::after { content: ""; opacity: 0.45; }
.ordenavel thead th[aria-sort="descending"]::after { content: " \\2193"; }
.ordenavel thead th[aria-sort="ascending"]::after { content: " \\2191"; }
tbody tr:hover { background: var(--realce); }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.pos { color: var(--sobe); }
.neg { color: var(--desce); }
.vazio { color: var(--suave); font-style: italic; }
footer {
  margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--risco);
  color: var(--suave); font-size: 0.85rem;
}
"""

SCRIPT = """
document.querySelectorAll("table.ordenavel").forEach(function (tabela) {
  var cabecalhos = tabela.querySelectorAll("thead th");
  cabecalhos.forEach(function (th) {
    th.tabIndex = 0;
    th.setAttribute("role", "button");
    function agir() { ordenar(tabela, th); }
    th.addEventListener("click", agir);
    th.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); agir(); }
    });
  });
  function ordenar(tabela, th) {
    var i = th.cellIndex;
    var descendente = th.getAttribute("aria-sort") !== "descending";
    cabecalhos.forEach(function (o) { o.removeAttribute("aria-sort"); });
    th.setAttribute("aria-sort", descendente ? "descending" : "ascending");
    var corpo = tabela.tBodies[0];
    var linhas = Array.prototype.slice.call(corpo.rows);
    linhas.sort(function (a, b) {
      var ca = a.cells[i], cb = b.cells[i];
      var na = ca.dataset.v, nb = cb.dataset.v;
      var r;
      if (na !== undefined && nb !== undefined) {
        // célula sem valor (um traço) fica sempre no fim
        var va = na === "" ? null : parseFloat(na);
        var vb = nb === "" ? null : parseFloat(nb);
        if (va === null && vb === null) { r = 0; }
        else if (va === null) { return 1; }
        else if (vb === null) { return -1; }
        else { r = va - vb; }
      } else {
        r = ca.textContent.localeCompare(cb.textContent, "pt");
      }
      return descendente ? -r : r;
    });
    linhas.forEach(function (l) { corpo.appendChild(l); });
  }
});
"""


def _contagem(valor, etiqueta):
    return (f'<div class="contagem"><div class="valor">{valor}</div>'
            f'<div class="etiqueta">{html.escape(etiqueta)}</div></div>')


def _th(titulo, numero=False, ordenada=False):
    """Um cabeçalho de coluna. 'ordenada' marca a que ordena a tabela de início."""
    classe = ' class="num"' if numero else ""
    ordem = ' aria-sort="descending"' if ordenada else ""
    return f"<th{classe}{ordem}>{html.escape(titulo)}</th>"


def _tabela_agentes(agentes):
    if not agentes:
        return '<p class="vazio">Ainda não há decisões.</p>'
    colunas = ["Agente", "Fechadas", "Certas", "Acerto", "Dinheiro",
               "Ganho médio", "Perda média", "Abertas"]
    cabecalho = "".join(_th(c, numero=i > 0, ordenada=(c == "Dinheiro"))
                        for i, c in enumerate(colunas))
    linhas = []
    for a in agentes:
        acerto = "—" if a["acerto"] is None else f'{_fmt(a["acerto"], 1)}%'
        linhas.append(
            "<tr>"
            f'<td>{html.escape(a["nome"])}</td>'
            + _celula_num(a["fechadas"], str(a["fechadas"]), classe_cor=False)
            + _celula_num(a["certas"], str(a["certas"]), classe_cor=False)
            + _celula_num(a["acerto"], acerto, classe_cor=False)
            + _celula_num(a["total"], _fmt(a["total"], 2, sinal=True))
            + _celula_num(a["ganho_medio"], _fmt(a["ganho_medio"], 2, sinal=True))
            + _celula_num(a["perda_media"], _fmt(a["perda_media"], 2, sinal=True))
            + _celula_num(a["abertas"], str(a["abertas"]), classe_cor=False)
            + "</tr>")
    return ('<div class="rolar"><table id="tabela-agentes" class="ordenavel">'
            f"<thead><tr>{cabecalho}</tr></thead>"
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def _tabela_em_curso(posicoes_em_curso):
    if not posicoes_em_curso:
        return '<p class="vazio">Nenhuma posição aberta.</p>'
    colunas = ["Agente", "Empresa", "Entrada", "Atual", "Stop", "Alvo", "Caminho"]
    cabecalho = "".join(_th(c, numero=i > 1, ordenada=(c == "Caminho"))
                        for i, c in enumerate(colunas))
    linhas = []
    for p in posicoes_em_curso:
        caminho = "—" if p["caminho"] is None else f'{_fmt(p["caminho"], 1)}%'
        linhas.append(
            "<tr>"
            f'<td>{html.escape(p["agente"])}</td>'
            f'<td>{html.escape(p["ticker"])}</td>'
            + _celula_num(p["entrada"], _fmt(p["entrada"]), classe_cor=False)
            + _celula_num(p["atual"], _fmt(p["atual"]), classe_cor=False)
            + _celula_num(p["stop"], _fmt(p["stop"]), classe_cor=False)
            + _celula_num(p["alvo"], _fmt(p["alvo"]), classe_cor=False)
            + _celula_num(p["caminho"], caminho)
            + "</tr>")
    return ('<div class="rolar"><table id="tabela-abertas" class="ordenavel">'
            f"<thead><tr>{cabecalho}</tr></thead>"
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def _tabela_ultimas(ultimas):
    if not ultimas:
        return '<p class="vazio">Ainda não fechou nenhuma posição.</p>'
    linhas = []
    for f in ultimas:
        linhas.append(
            "<tr>"
            f'<td>{html.escape(f["data"] or "")}</td>'
            f'<td>{html.escape(f["agente"])}</td>'
            f'<td>{html.escape(f["ticker"])}</td>'
            f'<td>{html.escape(f["estado"])}</td>'
            + _celula_num(f["resultado"], _fmt(f["resultado"], 2, sinal=True))
            + "</tr>")
    return ('<div class="rolar"><table id="tabela-fechadas">'
            "<thead><tr><th>Data</th><th>Agente</th><th>Empresa</th>"
            '<th>Fecho</th><th class="num">Resultado</th></tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def desenhar(dados):
    """Devolve o HTML completo da página."""
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agentes de Ações</title>
<meta name="description" content="Resultados do torneio de agentes, com dinheiro simulado.">
<!-- Gerado pelo gerar_site.py. Não editar à mão: é reescrito todos os dias. -->
<style>{ESTILO}</style>
</head>
<body>
<main>
  <h1>Agentes de Ações</h1>
  <p class="data">Atualizado a {html.escape(dados["atualizado"])}</p>

  <div class="aviso"><p>{html.escape(AVISO)}</p></div>

  <div class="contagens">
    {_contagem(dados["dias"], "dias de registo")}
    {_contagem(dados["decisoes"], "decisões")}
    {_contagem(dados["abertas"], "posições abertas")}
    {_contagem(dados["fechadas"], "posições fechadas")}
  </div>

  <h2>Agentes</h2>
  {_tabela_agentes(dados["agentes"])}
  <p class="legenda">
    Clica num cabeçalho para ordenar. Uma decisão conta como certa se deu
    dinheiro depois de custos, não por ter fechado no alvo: uma posição fechada
    por tempo pode acabar dos dois lados.
  </p>
  <p class="legenda">
    Dois dos nomes desta tabela não são agentes a sério.
    <strong>controlo-sempre-compra</strong> compra todos os dias sem ler nada, e
    <strong>controlo-moeda-ao-ar</strong> decide à sorte. Existem para responder
    a uma pergunta só: os agentes a sério são melhores do que não fazer nada? Se
    no fim algum destes estiver à frente, os resultados do torneio são ruído e
    nenhum agente merece ser copiado. Por isso é que aparecem aqui sem qualquer
    distinção — se precisassem de um asterisco para se perceber que perderam,
    a comparação não estava a ser justa.
  </p>

  <h2>Posições abertas</h2>
  <p>
    Apostas ainda em curso, da mais adiantada para a menos. O caminho é a
    percentagem da distância entre a entrada e o alvo que já foi percorrida.
    Nada disto está na tabela de cima: são ganhos e perdas que ainda não
    aconteceram.
  </p>
  {_tabela_em_curso(dados["em_curso"])}

  <h2>Últimas posições fechadas</h2>
  <p>
    As 20 mais recentes. <strong>STOP</strong> saiu a perder,
    <strong>ALVO</strong> saiu a ganhar, <strong>TEMPO</strong> chegou ao limite
    de {config.DIAS_MAXIMOS_POSICAO} dias de bolsa sem tocar em nenhum dos dois.
  </p>
  {_tabela_ultimas(dados["ultimas"])}

  <footer>
    <p>
      Dinheiro simulado. Todos os números são recalculados a partir dos preços
      de cada dia, nunca gravados — corrigir a regra corrige o histórico todo.
      Cada aposta são {_fmt(config.VALOR_POR_APOSTA)} EUR, com
      {_fmt(config.COMISSAO_POR_OPERACAO)} EUR de comissão à entrada e à saída e
      {_fmt(config.SLIPPAGE_PCT)}% de slippage.
    </p>
  </footer>
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""


def main():
    decisoes = posicoes._ler_csv(config.FICHEIRO_DECISOES)
    precos = posicoes._ler_csv(config.FICHEIRO_PRECOS)
    if not precos:
        print("ERRO: sem preços. Corre primeiro o correr_diario.py.")
        return 1

    dados = recolher(decisoes, precos)
    with open(FICHEIRO_SITE, "w", encoding="utf-8") as f:
        f.write(desenhar(dados))

    print(f"{FICHEIRO_SITE}: {dados['dias']} dias, {dados['decisoes']} decisões, "
          f"{dados['abertas']} abertas, {dados['fechadas']} fechadas, "
          f"{len(dados['agentes'])} agentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
