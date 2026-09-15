"""
Definições do projeto.

FASE ATUAL: fatia fina (teste técnico).
Só uma empresa e um agente. Não mexer nos agentes depois do arranque oficial
do torneio -- ver README.md.
"""

# ---------------------------------------------------------------------------
# Empresas a seguir
# ---------------------------------------------------------------------------
# Fase 1 (teste técnico): apenas uma.
# Fase 2 (torneio): sobe para 40-50 para haver decisões suficientes.
EMPRESAS = [
    "AAPL",   # Apple
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
