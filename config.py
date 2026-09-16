"""
Definições do projeto.

FASE ATUAL: teste técnico.
40 empresas, 1 agente + 2 controlos. As empresas subiram de 1 para 40 antes do
arranque para dar para ver se o yfinance aguenta o volume de pedidos.
Não mexer nos agentes depois do arranque oficial do torneio -- ver README.md.
"""

# ---------------------------------------------------------------------------
# Empresas a seguir
# ---------------------------------------------------------------------------
# Agrupadas por setor. O setor não é usado pelo programa -- serve para depois
# dar para ter agentes especialistas (um só de tecnologia, um só de energia) e
# para comparar o mesmo agente entre setores.
EMPRESAS = [
    # Tecnologia
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "AMD", "INTC", "CRM", "ORCL",

    # Financeira
    "JPM", "BAC", "GS", "MS", "V", "MA",

    # Saúde
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "LLY",

    # Energia
    "XOM", "CVX", "COP",

    # Consumo
    "KO", "PEP", "MCD", "NKE", "SBUX", "WMT", "COST", "PG",

    # Outros
    "BA", "CAT", "GE", "DIS", "T", "VZ", "TSLA",
]

# ---------------------------------------------------------------------------
# Regras de aposta (iguais para TODOS os agentes)
# ---------------------------------------------------------------------------
# Todos apostam sempre o mesmo valor. Se cada agente apostasse valores
# diferentes, estaríamos a comparar tamanho de aposta e não qualidade
# de análise.
VALOR_POR_APOSTA = 1000.0      # euros simulados por posição

# Custos por operação. NUNCA pôr a zero: uma estratégia que parece lucrativa
# sem custos costuma passar a perdedora assim que se somam.
COMISSAO_POR_OPERACAO = 1.00   # euros, à entrada e à saída
SLIPPAGE_PCT = 0.05            # % -- compras um pouco acima do preço no ecrã

# ---------------------------------------------------------------------------
# Ficheiros de registo
# ---------------------------------------------------------------------------
FICHEIRO_PRECOS = "dados/precos.csv"
FICHEIRO_DECISOES = "dados/decisoes.csv"

# ---------------------------------------------------------------------------
# Datas do plano (só para referência e para o site mostrar)
# ---------------------------------------------------------------------------
INICIO_TESTE_TECNICO = "2026-09-15"
ARRANQUE_TORNEIO = "2026-10-24"
FIM_TORNEIO = "2027-06-30"
