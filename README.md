# Agentes de Ações

Torneio de agentes que analisam empresas e apostam com dinheiro **simulado**.
O objetivo não é ganhar dinheiro já — é descobrir, com números, se alguma das
ideias funciona antes de arriscar seja o que for.

---

## As regras do torneio

Estas regras existem para o resultado significar alguma coisa. Sem elas,
ao fim de oito meses ficas com um sistema que prevê o passado e mais nada.

**1. Depois do arranque oficial, nenhum agente é alterado.**
Nem a tese, nem as fontes, nem os números. Arranjar o que está *avariado*
(o programa rebentou, a fonte de dados falhou) é obrigatório e não conta como
mexer. Mudar o que o agente *pensa* é que estraga tudo.

**2. Podes acrescentar, nunca modificar.**
Ideia nova a meio do torneio? Cria um agente novo, com o seu próprio relógio.
Os que já lá estavam continuam limpos.

**3. Os controlos idiotas correm sempre.**
`controlo-sempre-compra` e `controlo-moeda-ao-ar` não leem nada e não pensam
nada. No fim, qualquer agente que não os bata com margem clara **não vale nada**,
por muito bons que os números pareçam isoladamente. Se um controlo ficar no
top 3, os resultados do torneio são ruído.

**4. Todos apostam o mesmo valor.**
Senão estarias a comparar tamanho de aposta, não qualidade de análise.

**5. Os custos entram desde o primeiro dia.**
Comissão e slippage estão no `config.py` e nunca vão a zero. Muitíssima
estratégia parece lucrativa no papel e passa a perdedora assim que se somam
os custos reais.

**6. Os resultados são calculados, nunca escritos à mão.**
O programa só grava preços e decisões. Se um agente acertou ou não é sempre
derivado dos preços que vieram depois.

**7. A partir de 24 de outubro, a lógica de avaliação fica congelada.**
Ficam trancados, tal como os agentes:

- o `posicoes.py` inteiro;
- o `DIAS_MAXIMOS_POSICAO` no `config.py` — é uma regra de avaliação disfarçada
  de definição. Mudá-lo de 60 para 40 fecha ao fim de 40 dias apostas que já
  tinham sido dadas como fechadas aos 60, com outro preço e outro resultado.

É o reverso da regra 6: como os resultados são sempre recalculados e nunca
gravados, mexer em qualquer um deles **reescreve em silêncio os resultados de
todo o histórico** — não há número nenhum gravado que passe a não bater certo e
te avise. Mexer numa linha em junho muda o vencedor de outubro sem deixar rasto.

Os outros números do `config.py` não entram aqui: o `VALOR_POR_APOSTA`, a
`COMISSAO_POR_OPERACAO` e o `SLIPPAGE_PCT` são copiados para cada linha do
`decisoes.csv` no dia em que a decisão é tomada, e é de lá que a avaliação os
lê. Mudá-los afeta as decisões daí para a frente, nunca as antigas.

Se for mesmo indispensável alterar, tem de ficar registado aqui em baixo a
data, o motivo e o que mudou, e a análise final tem de dizer com que versão
foi feita.

### Alterações à lógica de avaliação depois do arranque

Nenhuma até hoje.

<!-- Formato: | data | o que mudou | porque é que era indispensável | -->

---

## Regra de paragem (decidida antes de haver resultados)

> **No fim de janeiro de 2027:** se nenhum agente estiver claramente acima dos
> controlos, lanço uma segunda geração de 5 ideias novas.
> **Não altero nenhum dos originais.**

Isto está escrito aqui de propósito, antes de saber os resultados. Serve para
impedir que mais tarde se invente uma justificação para mexer nos agentes só
por frustração.

---

## Calendário

| Data | Fase |
|---|---|
| 15 set 2026 | Fatia fina a correr — 1 empresa, 1 agente |
| 15 set → 3 out | **Teste técnico.** Só verificar que grava todos os dias. Dados deitados fora. |
| 3 out → 17 out | Construir o sistema completo: 10 agentes, 40+ empresas, notícias, site |
| 17 out → 24 out | Teste técnico do sistema completo. Dados deitados fora. |
| **24 out 2026** | **Arranque oficial. A partir daqui não se toca em nada.** |
| 28 nov · 26 dez · 30 jan · 27 fev · 27 mar · 30 abr · 31 mai | Pontos de observação — só olhar (ver **Registo de observação**) |
| 30 jun 2027 | Fim do torneio |
| 3 jul 2027 | Análise dos resultados |
| 10 jul 2027 | Escolher os 3 melhores, criar clones com variações |
| 17 jul → out 2027 | Fase de confirmação (3 meses congelados) |

---

## Como pôr a funcionar

**1.** Cria um repositório no GitHub e mete lá estes ficheiros.

**2.** Vai a **Settings → Actions → General → Workflow permissions** e escolhe
**"Read and write permissions"**. Sem isto o robô não consegue gravar os
resultados e a tarefa falha todos os dias.

**3.** Vai ao separador **Actions**, escolhe "Registo diário" e carrega em
**"Run workflow"** para correr à mão uma primeira vez.

**4.** Se correu bem, aparece um ficheiro novo em `dados/precos.csv`.
A partir daí corre sozinho todos os dias úteis às 23:00 UTC.

### Correr no teu computador

```bash
pip install -r requirements.txt
python correr_diario.py                # dados a sério
python correr_diario.py --simulado     # dados falsos, para testar
```

### Correr duas vezes no mesmo dia

Pode-se correr as vezes que se quiser: **a última corrida do dia ganha.** Se já
houver linhas para esse dia e essa empresa, são substituídas, não repetidas.

Isto serve para o caso de se correr a meio da sessão de bolsa por engano: o
preço que fica gravado é um preço intradiário e não o fecho. Basta correr outra
vez depois do fecho que o preço fica corrigido e as decisões desse dia são
recalculadas com o preço certo — uma decisão apontada a um preço de entrada que
nunca existiu não serve para medir nada.

Fica sempre **uma linha por (data, empresa)** em `precos.csv` e **uma por
(data, agente, empresa)** em `decisoes.csv`. Os outros dias não são tocados.

---

## O que há aqui dentro

Todos os ficheiros ficam na raiz do repositório, sem pastas. A única pasta
é `.github/workflows/`, que o GitHub exige, e `dados/`, que o programa cria
sozinho na primeira vez que corre.

```
config.py                  empresas, valor das apostas, custos, datas
fonte_dados.py             ir buscar os preços (yfinance)
base.py                    classe base + cálculo do stop e do alvo
momentum.py                Agente 1 — momentum simples (só gráfico)
controlos.py               os dois controlos idiotas
lista_agentes.py           a lista de agentes ativos
posicoes.py                que apostas já fecharam, e com que resultado
correr_diario.py           o programa que corre uma vez por dia
requirements.txt           dependências
.github/workflows/
  diario.yml               a tarefa automática
dados/                     criada pelo programa
  precos.csv               o dia de cada empresa: abertura, máximo,
                           mínimo, fecho e volume
  decisoes.csv             uma linha por decisão tomada
```

---

## Uma posição de cada vez

Cada agente só pode ter **uma posição aberta por empresa** ao mesmo tempo.
Enquanto a aposta anterior dele nessa empresa não fechar, não se lhe pergunta
nada e não se grava linha nenhuma.

Uma pessoa a sério não compra a mesma ação todos os dias. E comprar a mesma
empresa 60 dias seguidos não são 60 provas de que o agente é bom: é a mesma
aposta contada 60 vezes. Isso dava a ideia de haver muito mais provas do que há.

Uma posição aberta no dia D fecha no primeiro dia a seguir em que:

| o que acontece | fecha em | sai a que preço |
|---|---|---|
| a abertura já vem abaixo do stop | STOP | **à abertura** — pior do que o stop |
| a abertura já vem acima do alvo | ALVO | **à abertura** — melhor do que o alvo |
| o mínimo chega ao stop | STOP | ao stop |
| o máximo chega ao alvo | ALVO | ao alvo |
| passam `DIAS_MAXIMOS_POSICAO` dias de bolsa | TEMPO | ao fecho desse dia |

A abertura é vista primeiro porque é o primeiro preço do dia: se já vem fora do
intervalo, a ordem executa logo ali e o que a cotação fizer a seguir nesse dia
não interessa. Sai-se ao preço que o mercado deu, nos dois sentidos — para baixo
perde-se mais do que o planeado, para cima ganha-se mais.

**Se, depois da abertura, tocar no stop e no alvo no mesmo dia, conta como
stop.** Com preços diários não dá para saber qual veio primeiro, e é preferível
ser pessimista a dar aos agentes um resultado melhor do que a realidade. Na
abertura não há esta dúvida.

Nada disto é gravado em ficheiro. O estado é sempre recalculado a partir dos
preços — se um dia corrigirmos a regra, todo o histórico fica corrigido sozinho.
É também a mesma conta que dirá, em julho, quem ganhou:

```bash
python posicoes.py
```

---

## Stop e alvo

Cada decisão leva um stop (onde sai a perder) e um alvo (onde sai a ganhar),
com um rácio de 3:1 — arrisca 1 para poder ganhar 3.

A conta que interessa: **a 3:1 podes errar 3 em cada 4 vezes e ainda assim
sair a ganhar.** Precisas de acertar mais de 25%.

A distância do stop não é um número fixo: é medida pela volatilidade da própria
ação (2 desvios-padrão diários), limitada entre 1,5% e 10%. Um stop fixo seria
apertado de mais numa ação nervosa e largo de mais numa calma.

**Atenção:** o stop não garante a perda máxima. Se sair uma notícia má durante
a noite, a ação abre abaixo do stop e perde-se mais do que o planeado.

É por isso que o `precos.csv` guarda a abertura, o máximo e o mínimo, e não só o
fecho: sem eles não dava para ver que isso aconteceu. Pelo mesmo motivo, uma
ação que desça até ao stop a meio do dia e feche acima dele é uma perda a sério
— com só o fecho, essa perda desaparecia do registo e os agentes pareciam
melhores do que são.

**O máximo e o mínimo são alargados até cobrirem a abertura e o fecho.** O Yahoo
manda de vez em quando dias impossíveis (a 17 de setembro de 2026, a MS e a CAT
vieram com a abertura acima do máximo). Como o `posicoes.py` usa o máximo e o
mínimo para ver se o preço tocou no stop, um intervalo que não cobre a abertura
pode deixar passar um stop realmente atingido, e a posição fica aberta quando já
devia ter fechado a perder. A correção não inventa nada: a abertura e o fecho
são preços a que se negociou mesmo, logo o verdadeiro máximo do dia é pelo menos
o maior dos três. Só se alarga até ao que já se sabe ser verdade, nunca se
aperta. Cada corrida diz quantas linhas corrigiu — se um dia forem muitas, é
sinal de problema maior na fonte.

---

## Fase atual

**Teste técnico.** 40 empresas (por setor, ver `config.py`), 1 agente + 2 controlos.
Nesta fase não se olha para acertos — só se confirma que o registo grava todos
os dias sem falhar. Estes dados não contam para nada.

---

## Registo de observação

Uma linha por ponto de observação. Serve para duas coisas: guardar o que foi
observado em cada data, e garantir atividade manual no repositório — o GitHub
desliga tarefas agendadas em repositórios sem atividade durante cerca de 60
dias. Os commits diários são empurrados pelo próprio GitHub Actions, com o
token dele, e não se deve contar com eles para isto: daí a linha ser escrita à
mão. Se isto ficar por fazer, o registo diário pára sozinho e só se dá por isso
quando faltarem semanas de dados.

Escrever aqui é **olhar, não mexer**. A partir de 24 de outubro valem as regras
1, 2 e 7: nem os agentes nem a lógica de avaliação se tocam. Se alguma vez for
mesmo indispensável alterar, isso vai para **Alterações à lógica de avaliação
depois do arranque**, lá em cima, e não para aqui.

Datas previstas: 28 nov 2026 · 26 dez 2026 · 30 jan 2027 · 27 fev 2027 ·
27 mar 2027 · 30 abr 2027 · 31 mai 2027.

Formato:

```
- AAAA-MM-DD — o que foi observado. Nada foi alterado.
```

### Observações

*(ainda nenhuma — a primeira é a 28 de novembro de 2026)*
