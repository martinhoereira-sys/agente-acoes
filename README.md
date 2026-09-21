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

- o `posicoes.py` e o `selecao.py` inteiros;
- o `sazonalidade_tabela.csv` — é o que o agente da sazonalidade sabia à
  partida. Regerá-lo com dados mais recentes muda retroativamente a tese
  dele, e ninguém dava por isso a olhar para o código;
- o `TETO_ACIMA_DA_MEDIA` do `momentum.py` — é o que o par
  `momentum-simples` / `momentum-com-teto` está a medir;
- a lista `EMPRESAS` do `config.py` — acrescentar ou tirar empresas a meio
  muda o terreno debaixo dos agentes, e um agente que só corra em metade das
  empresas não é comparável com os outros;
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

**8. O critério de seleção do fim está decidido desde já.**
No fim do torneio não se escolhem "os três melhores". Escolhem-se todos os
agentes que passarem as três condições abaixo, e apenas esses — podem ser
cinco, podem ser dois, pode não ser nenhum. As condições têm números fixos
desde já, incluindo o limiar de significância de 2,5. Ver **Critério de
seleção**.

### Alterações antes do arranque

O congelamento só começa a 24 de outubro. Estas foram feitas antes disso, mas
**depois de a lista das voláteis já estar gerada**, por isso ficam registadas
aqui na mesma — para se poder ver que não foram feitas a olhar para resultados.

| data | o que mudou | porquê |
|---|---|---|
| 2026-09-21 | `STOP_MAXIMO_PCT` de 10% para 15% (`base.py`) | Com 10%, o stop das ações mais nervosas ficava cortado muito abaixo dos 2 desvios-padrão que a regra manda. Na MRNA ficava *dentro* de um movimento normal de um dia: a posição fechava quase sempre de imediato, e sempre para o mesmo lado. |
| 2026-09-21 | A regra da escolha das voláteis passa a excluir candidatas acima de 7,5% de volatilidade diária (`escolher_volateis.py`), e a lista foi gerada outra vez com a regra nova | O mesmo problema, visto do outro lado: uma ação em que o stop cabe dentro de um dia normal não é uma observação, é uma perda combinada de antemão. O limite é `STOP_MAXIMO_PCT / 2`, derivado e não escrito à mão. |

**O motivo é a mecânica do stop, não o desempenho de nenhuma ação.** O que se
mediu foi o rácio entre a distância do stop e o movimento diário normal, que
sai só da volatilidade — não se olhou para nenhum resultado, nem para nenhum
agente, nem para o que a MRNA ou qualquer outra fez. O que empurrou a mudança
foi quem mais sofria com ela: o `controlo-sempre-compra` compra tudo todos os
dias, por isso apanhava estas perdas mais do que ninguém, e isso **baixava a
barra que os agentes têm de bater**. Corrigir isto torna o torneio mais
exigente, não menos.

A lista final saiu da regra corrida outra vez, não de uma remoção à mão: saiu
a MRNA e entrou a 21.ª classificada. Ver **As empresas**.

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

## Critério de seleção (decidido antes de haver resultados)

No fim do torneio **não se escolhem "os três melhores"**. Escolher os três
primeiros de uma lista garante sempre três vencedores, mesmo que os três sejam
ruído. Em vez disso há uma barra fixa, e passa quem a passar.

Um agente só é selecionado se cumprir as **três** condições:

> **1. Pelo menos 50 posições fechadas.**
> Abaixo disso não há como distinguir talento de sorte.
>
> **2. A vantagem sobre o melhor dos dois controlos tem de ser
> estatisticamente significativa.**
> Calcula-se o resultado médio por posição fechada do agente e o do controlo,
> o erro-padrão da diferença entre as duas médias, e divide-se a diferença por
> esse erro-padrão. O resultado tem de ser **maior que 2,5**. Em texto simples:
> a vantagem tem de ser pelo menos 2,5 vezes maior do que a incerteza com que
> foi medida. Empatar com a moeda ao ar não é passar.
>
> **3. Continua acima dos controlos depois de lhe ser retirada a sua melhor
> posição isolada.**
> Se todo o resultado vier de um único acerto grande, foi sorte.

Podem passar cinco, podem passar dois, pode não passar nenhum.

**Se nenhum agente passar, o site diz isso com todas as letras:** *"nenhum
agente passou o critério de seleção"*. Isso é um resultado válido e publica-se
na mesma. Oito meses a descobrir que nenhuma das ideias funciona é informação
que vale o mesmo que o contrário — e é bem mais barata do que descobri-lo com
dinheiro a sério.

### Porquê um número e não "margem clara"

A condição 2 já teve escrito "com margem clara". Isso não é um critério: é uma
decisão adiada. Em julho de 2027 alguém olharia para os números e decidiria ali
o que conta como clara — que é exatamente o que este capítulo existe para
impedir. Agora tem um número.

**O que é o erro-padrão.** Um agente que fechou 60 posições tem uma média de
euros por posição. Se o torneio voltasse a correr, essa média não dava
exatamente o mesmo: umas apostas corriam melhor, outras pior. O erro-padrão é a
estimativa de quanto essa média ainda oscilaria. Uma vantagem de 5 euros por
posição quer dizer coisas muito diferentes conforme a medição tenha uma margem
de 1 euro ou de 10.

**Por isso se divide.** A diferença entre as duas médias a dividir pelo
erro-padrão dessa diferença dá a vantagem medida na sua própria unidade de
incerteza. Um valor de 2,5 quer dizer que a vantagem é duas vezes e meia maior
do que a margem de erro. Abaixo disso, não se consegue distinguir de ruído.

**Porquê 2,5 e não 2.** O limiar habitual seria 2. Mas 2 é o valor para quando
se testa **um** candidato. Nós vamos ter dez agentes a serem avaliados ao mesmo
tempo, e quanto mais candidatos houver, maior a hipótese de um deles passar por
puro acaso — é como atirar dez moedas ao ar em vez de uma e depois reparar que
uma saiu cinco vezes seguidas a cara.

Por alto, e assumindo os agentes independentes uns dos outros:

| limiar | hipótese de **algum** dos 10 passar só por acaso |
|---|---|
| 2,0 | cerca de 21%, ou seja 1 em cada 5 torneios |
| 2,5 | cerca de 6%, ou seja 1 em cada 17 |
| 3,0 | cerca de 1% |

O 2,5 é o meio-termo: aperta o suficiente para o falso vencedor deixar de ser
provável, sem ser tão exigente que um agente genuinamente bom seja chumbado por
não ter apostas que cheguem.

**Contra qual dos controlos.** O melhor dos dois é, na prática, o que for mais
difícil de bater — o que der o valor mais baixo. Passar contra esse é passar
contra os dois.

**Uma limitação que fica dita.** O t-teste assume que cada posição é uma
observação independente. Não são. Um agente que abra vinte posições no mesmo
dia, nas vinte empresas, pelo mesmo motivo, está a fazer uma aposta contada
vinte vezes — se o mercado cair nesse dia, caem as vinte juntas. O erro-padrão
sai mais pequeno do que devia e a confiança sai maior do que é.

Isto afeta **todos** os agentes um pouco, porque todos decidem os mesmos dias
sobre as mesmas 60 empresas. Afeta mais os de regra de calendário, como o
`sazonalidade`, em que a razão para comprar é literalmente a mesma para toda a
gente no mesmo dia. Não há correção simples que não abra a porta a escolher a
correção que dá jeito, por isso fica registado em vez de corrigido: **o valor
da condição 2 é um limite superior da confiança, não a confiança.**

As três condições estão no `selecao.py` e podem ser corridas a qualquer momento:

```bash
python selecao.py
```

Mostra, por agente, o veredicto e os números de cada condição — incluindo as
que não chegaram a decidir, para se ver onde ficou.

### Porquê a condição 3

As duas primeiras condições olham para o total. A terceira é um **teste de
robustez**: mede se o agente ganha por acumulação ou por um golpe de sorte.

Um agente que faça 60 apostas pequenas e termine acima dos controlos mostrou um
padrão. Um agente cujo lucro venha em boa parte de uma posição que disparou
mostrou muito menos. O que se quer saber é se a ideia se repete, não se teve um
bom dia, e retirar a melhor posição é a maneira mais simples de perguntar isso.

**Uma surpresa, descoberta ao implementar isto.** O caso extremo — o agente cujo
lucro vem *todo* de uma única posição — **já é chumbado pela condição 2, sozinha**.
A razão é aritmética: uma posição enorme puxa a média para cima, mas puxa o
erro-padrão exatamente na mesma proporção. Os dois crescem ao mesmo ritmo e o
resultado da divisão tende para 1, por muito grande que a posição seja. Nunca
chega perto de 2,5.

| 59 apostas de −2 EUR, mais uma de… | valor da condição 2 |
|---|---|
| 100 EUR | −0,12 |
| 1 000 EUR | 0,88 |
| 100 000 EUR | 1,00 |
| 1 000 000 000 EUR | 1,00 |

Ou seja: a condição 3 **não** é o que apanha o golpe de sorte. Ela aperta a
margem para os casos em cima da linha — um agente com vantagem real mas apertada,
em que a melhor posição é o que o empurra para o lado bom do limiar. Num exemplo
testado: 2,51 com todas as posições, 2,31 sem a melhor. Passa a 2, chumba na 3.

Fica na mesma, e fica de propósito: é uma barra a mais e não custa nada. Mas o
trabalho pesado de rejeitar a sorte é da condição 2.

### Porquê escrito agora

Este critério está aqui **antes de existirem resultados**, de propósito. Uma
linha de corte traçada depois de se ver os números acaba sempre a passar no
sítio onde algum agente fica do lado bom. Escrita antes, ou passa, ou não passa.

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
| 10 jul 2027 | Aplicar o **critério de seleção** — passa quem passar, podem ser zero. Criar clones com variações dos que passarem |
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
controlos.py               os dois controlos idiotas
lista_agentes.py           a lista de agentes ativos
momentum.py                Agentes 1-4 — momentum 3:1, 2:1, 5:1 e com teto
contrarian.py              Agente 4 — o oposto do momentum
sazonalidade.py            Agente 5 — compra nos melhores meses do ano
gerar_sazonalidade.py      gera a tabela da sazonalidade (corre uma vez)
sazonalidade_tabela.csv    a tabela, congelada (regra 7)
escolher_volateis.py       escolhe as 20 voláteis por regra (corre uma vez)
volateis_escolhidas.csv    a escolha, com a volatilidade de cada uma
posicoes.py                que apostas já fecharam, e com que resultado
selecao.py                 as três condições da regra 8, congelado
correr_diario.py           o programa que corre uma vez por dia
gerar_site.py              escreve o index.html a partir dos CSV
index.html                 a página de resultados (gerada, não editar)
requirements.txt           dependências
.github/workflows/
  diario.yml               a tarefa automática de todos os dias
  sazonalidade.yml         gera a tabela da sazonalidade (à mão, uma vez)
  volateis.yml             escolhe as 20 voláteis (à mão, uma vez)
dados/                     criada pelo programa
  precos.csv               o dia de cada empresa: abertura, máximo,
                           mínimo, fecho e volume
  decisoes.csv             uma linha por decisão tomada
```

---

## Os agentes

Cada agente é uma tese fixa sobre como o mercado funciona. Nenhum usa IA nem
notícias: só preços do yfinance. A partir de 24 de outubro nenhum se altera
(regra 1).

| Agente | Rácio | A tese |
|---|---|---|
| `momentum-simples` | 3:1 | Uma ação que vem a subir continua a subir. Compra >1% acima da média de 50 dias. |
| `momentum-2-1` | 2:1 | A mesma tese, alvo mais perto. Precisa de acertar >33%. |
| `momentum-5-1` | 5:1 | A mesma tese, alvo mais longe. Precisa de acertar >17%. |
| `momentum-com-teto` | 3:1 | A mesma tese, mas recusa acima de **15%** da média. Comprar esticado é pior? |
| `contrarian` | 3:1 | O mercado exagera nas descidas. Compra >5% **abaixo** da média de 50 dias. |
| `sazonalidade` | 3:1 | Há meses do ano que são sistematicamente maus. Compra sempre, **exceto** nos 4 piores. |
| `controlo-sempre-compra` | 3:1 | CONTROLO: compra todos os dias sem ler nada. |
| `controlo-moeda-ao-ar` | 3:1 | CONTROLO: decide à sorte. |

**Os três primeiros momentum existem para responder a uma pergunta só: qual é
o rácio certo?** A tese é idêntica e o código é o mesmo — a única coisa que muda é a
distância do alvo. No fim, a diferença entre eles é atribuível ao rácio e a
mais nada.

**O `momentum-com-teto` é um par controlado com o `momentum-simples`.** São
iguais em tudo — mesmo limiar de entrada (1% acima da média), mesmo rácio,
mesmo código, por herança — menos numa coisa: o de teto recusa comprar quando o
preço já está mais de **15%** acima da média de 50 dias.

Isso torna a comparação entre os dois limpa. Em julho, a diferença de
resultados entre eles é atribuível ao teto e a mais nada, e responde a uma
pergunta sozinha: **comprar uma ação que já subiu de mais é pior do que comprar
uma que só começou a subir?** Com dois agentes que diferissem em duas coisas,
não haveria maneira de saber qual delas explicava a diferença.

O valor de 15% está fixo no `momentum.py` (`TETO_ACIMA_DA_MEDIA`) e fica
congelado a partir de 24 de outubro, como o resto: mexer nele muda o que o par
está a medir, retroativamente.

**O `sazonalidade` é um par controlado com o `controlo-sempre-compra`.** O
controlo compra todos os dias, sem ler nada; o sazonalidade compra todos os
dias exceto nos quatro meses historicamente piores. A diferença entre os dois
mede exatamente uma coisa: **vale a pena ficar de fora nos meses maus?**

**O contrarian é o par do momentum, de propósito.** Os dois não podem ter razão
ao mesmo tempo, e nunca compram a mesma empresa no mesmo dia. Se ambos ficarem
abaixo dos controlos, a resposta é que nenhuma das duas histórias funciona
nestes dados — com só um dos lados a correr, uma derrota pareceria conclusiva
sem o ser.

### Como a sazonalidade sabe o que sabe

A tabela está no `sazonalidade_tabela.csv`, gerada **uma vez** pelo
`gerar_sazonalidade.py` com dados de janeiro de 2016 a dezembro de 2025 — dez
anos fechados, nenhum a meio.

A variação média mensal é calculada com as **40 empresas juntas**, não empresa
a empresa. Por empresa cada mês teria dez observações, e dez números chegam
para qualquer mês parecer o melhor do ano por puro acaso. Juntas são cerca de
400 por mês. Continua a não ser muito — os meses das mesmas 40 empresas
americanas andam bastante juntos, por isso 400 observações valem menos do que
400 independentes — mas é outra ordem de grandeza.

**O agente lê o ficheiro e nunca o recalcula.** Se recalculasse, a tabela mudava
à medida que chegassem dados novos e o agente passava a aprender durante o
torneio: deixava de ser uma tese fixa a ser testada e passava a ser um modelo a
ajustar-se ao que está a acontecer. Seria a regra 1 a ser violada sem ninguém
dar por isso, porque a linha de código seria exatamente a mesma.

### A tabela, tal como ficou

Gerada a 21 de setembro de 2026, com 400 observações por mês (40 empresas ×
10 anos). Fica aqui registada para se saber **o que o agente sabia à partida**,
mesmo que o ficheiro se perca.

| Mês | Média | | Mês | Média |
|---|---:|---|---|---:|
| **novembro** | **+4,78%** | | maio | +1,78% |
| **julho** | **+3,19%** | | junho | +1,76% |
| **janeiro** | **+2,05%** | | abril | +1,66% |
| **agosto** | **+1,95%** | | outubro | +0,99% |
| | | | dezembro | +0,77% |
| | | | março | −0,01% |
| | | | setembro | −0,54% |
| | | | fevereiro | −0,57% |

**Os 4 meses evitados: fevereiro, setembro, março e dezembro.** Nos outros
oito, o agente compra. O quinto pior, outubro (+0,99%), fica de fora da
exclusão — o corte foi entre dezembro (+0,77%) e outubro.

#### Registo: a regra mudou a 21 de setembro de 2026, depois de a tabela existir

A tabela **não mudou** — é a mesma, gerada a 21 de setembro com dados de
2016-2025. O que mudou foi a regra que a lê.

**Antes:** comprava nos 4 melhores meses (novembro, julho, janeiro, agosto).
**Agora:** compra sempre, exceto nos 4 piores (fevereiro, setembro, março,
dezembro).

**O motivo é de calendário, não de desempenho.** O torneio vai de 24 de outubro
de 2026 a 30 de junho de 2027. Dos quatro melhores meses, só novembro e janeiro
caem lá dentro: o agente ficava ativo em 2 dos 8 meses. E em cada um desses
comprava quase todas as empresas ao mesmo tempo, pelo mesmo motivo — na prática
eram **duas apostas, não centenas**. O t-teste da condição 2 trataria as
centenas como independentes e daria uma confiança que não existe.

Virado ao contrário fica ativo em 6 dos meses do torneio e transforma-se num
par controlado com o `controlo-sempre-compra`.

Isto é dito com todas as letras porque a mudança **podia** ter sido feita a
olhar para resultados, e não foi: à data desta alteração o agente ainda não
tinha tomado uma única decisão, porque setembro é um dos meses que ele evita.
Não havia desempenho nenhum para olhar.

Vale a pena olhar para os números com desconfiança antes de acreditar neles.
Novembro está muito à frente, mas dez novembros não são dez observações
independentes: são dez momentos do mesmo mercado, e as 40 empresas dentro de
cada um andam juntas. O agente existe para pôr isto à prova com dinheiro
simulado, não porque a tabela já prove alguma coisa. Se no fim ele ficar abaixo
dos controlos, a resposta é que o padrão era do passado e não se repetiu.

---

## As empresas

60 no total: 40 grandes empresas americanas, escolhidas por setor, e 20
voláteis, escolhidas por regra. A lista está no `config.py` e fica **congelada
a partir de 24 de outubro** (regra 7).

### Porquê 20 voláteis

As 40 grandes mexem-se pouco. Com um stop a 2 desvios-padrão, uma ação calma
raramente chega ao stop **ou** ao alvo, e a posição acaba a fechar por tempo ao
fim de 60 dias — que é uma observação que não diz nada sobre o agente. Ações
mais nervosas resolvem-se mais depressa, e uma posição fechada é a
matéria-prima do torneio.

### A regra da escolha

> As 20 ações do S&P 500 com **maior desvio-padrão das variações diárias** nos
> 12 meses que terminam a **18 de setembro de 2026**, excluindo as 40 que já
> estavam na lista, exigindo pelo menos 200 dias de negociação na janela, e
> **excluindo as que são voláteis de mais** — aquelas cujo movimento de 2
> desvios-padrão diários passa o teto do stop, ou seja, acima de 7,5% de
> volatilidade diária.

A regra foi escrita **antes** de se ver a lista, e a janela está fixada no
código em vez de ser "hoje": correr o `escolher_volateis.py` noutro dia tem de
dar o mesmo resultado. Escolher ações voláteis a olho seria escolher as que dão
jeito, e ninguém saberia dizer se uma empresa entrou por ser volátil ou por
alguém gostar dela.

Dos 463 candidatos, foram medidos 459. Dois ficaram de fora por terem menos de
200 dias — sem esse filtro, uma empresa que entrou em bolsa há três semanas com
cinco dias agitados aparecia no topo sem ter história nenhuma. Um ficou de fora
pelo teto (a MRNA). E um ficou por medir: o Yahoo falhou o download da PH nessa
corrida. A PH é uma industrial calma, a uma distância enorme do corte de 4,24%,
por isso não mudava nada — mas fica dito em vez de escondido. A escolha foi
corrida duas vezes, e a segunda deu exatamente a mesma lista.

**Porquê excluir as voláteis de mais.** O stop é 2 desvios-padrão diários,
limitado a `STOP_MAXIMO_PCT` (15%). Numa ação cuja volatilidade passe metade
desse teto, o stop fica mais apertado do que a regra manda, e no caso extremo
fica *dentro* de um movimento normal de um dia — a posição fecha quase de
imediato, sempre para o mesmo lado. Isso não afeta os agentes por igual: quem
comprar mais essas ações apanha mais perdas, e o `controlo-sempre-compra`, que
compra tudo todos os dias, é o que mais apanha. Baixa artificialmente a barra
que os agentes têm de bater, que é o contrário do que um torneio serve.

O limite de 7,5% não está escrito à mão no código: é `STOP_MAXIMO_PCT / 2`.
Os dois não podem sair de sincronia — se o teto do stop mudar, este muda com
ele.

### As 20 escolhidas

Volatilidade diária, em percentagem, na janela acima:

| # | Ticker | Vol. | # | Ticker | Vol. | # | Ticker | Vol. | # | Ticker | Vol. |
|---|---|---:|---|---|---:|---|---|---:|---|---|---:|
| 1 | SNDK | 7,34% | 6 | MU | 5,15% | 11 | STX | 4,73% | 16 | COIN | 4,55% |
| 2 | BE | 7,22% | 7 | WDC | 5,08% | 12 | APP | 4,63% | 17 | RDDT | 4,51% |
| 3 | LITE | 6,18% | 8 | MRVL | 5,02% | 13 | HOOD | 4,58% | 18 | DDOG | 4,40% |
| 4 | SMCI | 5,84% | 9 | TER | 4,89% | 14 | CIEN | 4,57% | 19 | FLEX | 4,36% |
| 5 | COHR | 5,41% | 10 | DELL | 4,75% | 15 | GLW | 4,56% | 20 | P | 4,24% |

O corte foi limpo: a 20.ª tem 4,238% e a 21.ª tinha 4,197%. Não foi um empate
decidido por acaso.

**Uma só candidata ficou de fora pelo teto: a MRNA, com 12,15%.** A lista
começou com ela lá dentro, porque o teto de 7,5% só foi acrescentado à regra
a 21 de setembro, depois de a lista estar gerada. Não foi tirada à mão: a
regra foi corrida outra vez com o critério novo, e o lugar vago foi ocupado
pela 21.ª classificada, que era a P. Ver o registo em **As regras do torneio**.

### O que isto faz ao stop

O stop é 2 desvios-padrão diários, **limitado a 15%** (ver `base.py`). Com o
teto a 15% e o critério a cortar acima de 7,5%, **nenhuma das vinte bate no
limite**: a mais nervosa das que ficaram é a SNDK, com 7,34%, cujos 2 desvios
dão 14,7%. Todas ficam com o stop exatamente onde a regra o quer.

Não era assim antes de 21 de setembro. Com o teto a 10%, oito destas
passavam-no — e a MRNA, que então estava na lista, passava-o de longe: o
stop ficava-lhe *dentro* de um movimento normal de um dia, por isso quase
todas as posições nela fechariam no stop quase de imediato. Não é aleatório:
é previsível e é sempre para o mesmo lado.

E não afetava todos os agentes por igual, que é o que incomodava. Um agente
que comprasse essas ações muitas vezes apanhava muitas destas perdas; um que
comprasse poucas, poucas. O `controlo-sempre-compra` compra tudo todos os
dias, por isso era o que mais apanhava — o que fazia os agentes a sério
parecerem melhores do que são em comparação com ele. As duas mudanças de 21
de setembro tratam disso pelos dois lados: o teto sobe, e as ações em que ele
morderia deixam de entrar.

**Atenção ao que isto não é.** O teto do stop continua a existir, e continua a
poder morder: as 40 grandes também têm dias agitados, e a volatilidade que
conta para o stop é a dos últimos 20 dias, não a dos 12 meses da escolha. A
CRM, que é das 40, chegou a bater no teto de 10% a 16 e a 18 de setembro. O
que o critério novo garante é só que nenhuma empresa entra na lista já com o
stop condenado a ficar dentro de um dia normal.

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
ação (2 desvios-padrão diários), limitada entre 1,5% e 15%. Um stop fixo seria
apertado de mais numa ação nervosa e largo de mais numa calma.

O teto de 15% foi 10% até 21 de setembro de 2026 — ver o registo em
**As regras do torneio**.

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

**Teste técnico.** 60 empresas (40 grandes + 20 voláteis), 6 agentes + 2 controlos.
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
