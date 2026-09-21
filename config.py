"""
Definições do projeto.

FASE ATUAL: teste técnico.
60 empresas (40 grandes + 20 voláteis), 6 agentes + 2 controlos.
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

    # Voláteis -- as 20 ações do S&P 500 com maior desvio-padrão das variações
    # diárias nos 12 meses até 18 de setembro de 2026, excluindo as de cima.
    # Escolhidas por regra, não a dedo: ver escolher_volateis.py e o README.
    # As 40 de cima são as maiores empresas americanas e mexem-se pouco; com um
    # stop a 2 desvios-padrão, uma ação calma raramente chega ao stop ou ao
    # alvo e a posição fecha por tempo sem dizer nada. Estas fecham posições
    # mais depressa, e uma posição fechada é uma observação.
    "MRNA", "SNDK", "BE", "LITE", "SMCI",
    "COHR", "MU", "WDC", "MRVL", "TER",
    "DELL", "STX", "APP", "HOOD", "CIEN",
    "GLW", "COIN", "RDDT", "DDOG", "FLEX",
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

# Ao fim de quantos dias de bolsa se fecha uma posição que não chegou ao stop
# nem ao alvo, ao preço de fecho desse dia.
#
# Cada agente só pode ter uma posição aberta por empresa de cada vez. Sem este
# limite, uma ação que ficasse parada entre o stop e o alvo bloqueava o agente
# nessa empresa durante meses -- e uma aposta que nunca fecha também nunca
# entra nas contas do fim.
#
# CONGELADO a partir do arranque do torneio (regra 7 do README). Isto não é uma
# definição como as outras: é uma regra de avaliação. Ao contrário do valor da
# aposta e dos custos, que ficam copiados em cada linha do decisoes.csv no dia
# em que a decisão é tomada, este número é lido no momento em que as contas são
# feitas -- e as contas são refeitas de raiz de cada vez. Baixá-lo de 60 para 40
# passa a fechar aos 40 dias apostas antigas que já tinham sido dadas como
# fechadas aos 60, com outro preço e outro resultado, e nada avisa que mudou.
# Se for mesmo indispensável, regista no README a data, o motivo e o que mudou.
DIAS_MAXIMOS_POSICAO = 60

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
