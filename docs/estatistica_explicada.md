# Estatística e modelos do estudo, explicados passo a passo

Documento de apoio (não faz parte do artigo). Explica **cada técnica estatística** usada no estudo, **por que** foi escolhida, **como** é calculada e **como ler** os resultados, sempre com os nossos números. Complementa `analise_passo_a_passo.md` (o que foi feito) e `familias_de_variantes.md` (como as famílias são montadas).

---

## 0. Mapa: que técnica responde a que pergunta

| Pergunta | Técnica | Onde está | Resultado principal |
|---|---|---|---|
| Que fração das skills foi escrita com assistente? | Proporção + intervalo de Wilson | nb02 §2.2 | 31,9% (IC 31,8–32,1%) |
| O reuso é espalhado ou concentrado? | Fração de únicas, top 1%, coeficiente de Gini | nb03 §3.1 | top 1% = 27% das cópias; Gini 0,49 |
| As cópias atravessam donos? | Proporção | nb03 §3.2 | 65,6% |
| Uma skill tem tal capacidade? | Detector por expressão regular | `patterns.py`, nb04 §4.1 | ex.: `curl \| sh` em 0,7% |
| Quanto confiar no detector? | Amostra estratificada, rotulagem, precisão + Wilson | nb05 §5.1–5.3 | `curl \| sh` 12/12; segredos 2/12 |
| Os dois avaliadores concordam? | κ de Cohen | nb05 §5.4 | κ = 0,75 (instrução ou não) |
| As cópias acrescentam ou removem capacidades? | Comparação pareada + teste exato de McNemar | nb04 §4.2 | `curl \| sh`: 3.429 × 3.175, p = 0,002 |
| Que variantes acrescentam capacidades? | Regressão logística (razões de chances) | nb04 §4.3 | scripts OR 1,46; assistente OR 1,22 |

**Sobre "machine learning":** o estudo **não treina nenhum modelo de aprendizado de máquina**. A regressão logística é um modelo **estatístico explicativo**: serve para medir associações, não para prever. Os detectores são **regras escritas à mão** (expressões regulares), não classificadores treinados. O único uso de um modelo de linguagem foi a **pré-rotulagem** da amostra de validação, depois revisada por você (seção 8). A seção 10 lista onde ML entraria como trabalho futuro.

---

## 1. Duas unidades de contagem (lembrete)

* **Ocorrência:** um arquivo `SKILL.md` em um caminho de um repositório (3.797.117). Mede **adoção e exposição**: quantas instalações existem.
* **Skill distinta:** um conteúdo, identificado pelo hash do arquivo (1.877.981; 1.610.839 na população estrita). Mede **propriedades do texto**: o mesmo texto copiado 1.000 vezes é contado uma vez.

Quase todo número do artigo é "fração de alguma coisa". Saber **de quê** (ocorrências ou skills distintas) é o primeiro passo para ler qualquer resultado. Exemplo: "1% dos conteúdos responde por 27% das ocorrências" mistura as duas unidades de propósito.

---

## 2. Proporções e intervalo de confiança de Wilson

### O que é
Uma proporção é `k / n`: das 396.247 skills com histórico, 126.424 tiveram o primeiro commit com assistente ou bot, ou seja, 31,9%. Como os dados são uma **amostra** do que existe (a busca do GitHub não acha tudo, e a fração muda de mês para mês), queremos uma **margem de erro**: o intervalo de confiança (IC) de 95%.

### Por que Wilson e não a fórmula "da escola"
A fórmula comum (aproximação normal, `p ± 1,96·√(p(1−p)/n)`) funciona mal quando `n` é pequeno ou `p` está perto de 0 ou 1. O caso extremo é o nosso `curl | sh` na validação: 12 acertos em 12.

| Método | IC 95% para 12/12 |
|---|---|
| Normal | [1,00; 1,00]: diz que temos **certeza absoluta**, o que é absurdo com 12 casos |
| **Wilson** | **[0,76; 1,00]**: a precisão real pode ser de 76% a 100% |

O intervalo de Wilson inverte o teste estatístico em vez de somar e subtrair uma margem fixa. Por isso ele **nunca sai de [0, 1]** e fica assimétrico perto das bordas. É o padrão recomendado para proporções (Wilson, 1927; Brown, Cai e DasGupta, 2001).

### Como ler
* **IC estreito** (31,8–32,1%): com 396 mil skills, a incerteza de amostragem é desprezível. O que ainda pode estar errado é **viés** (por exemplo, trailers apagados), e isso o IC não mede. Vai para as Ameaças à validade.
* **IC largo** (segredos 2/12 → [0,05; 0,45]): 12 casos só permitem dizer que o detector é **ruim**, não exatamente quão ruim. Serve para separar detectores bons de ruins, não para afinar casas decimais.

---

## 3. Concentração do reuso

Para cada skill distinta contamos `copies` (em quantos caminhos ela aparece). Quatro medidas descrevem a distribuição:

| Medida | Definição | Valor | Leitura |
|---|---|---|---|
| Fração de únicas | skills com `copies = 1` ÷ skills | 79,6% | a maioria nunca foi copiada |
| Ocorrências duplicadas | (ocorrências − skills) ÷ ocorrências | 52,5% | mais da metade dos arquivos repete um texto que já existe |
| Top 1% | cópias do 1% mais copiado ÷ todas as ocorrências | 27,0% | um núcleo pequeno concentra muito |
| Gini | ver abaixo | 0,49 | desigualdade moderada a alta |

### Coeficiente de Gini
Vem da economia (desigualdade de renda). Ordene as skills da menos para a mais copiada e desenhe a **curva de Lorenz**: no eixo x, a fração acumulada de skills; no eixo y, a fração acumulada de cópias. Se todas fossem igualmente copiadas, a curva seria a diagonal. O Gini é a área entre a diagonal e a curva, normalizada:

* **0** = todas as skills igualmente copiadas;
* **1** = uma única skill tem todas as cópias.

Fórmula usada (`reuse.gini`), com `x` ordenado de forma crescente e `i = 1…n`:

`G = Σ (2i − n − 1)·xᵢ / (n · Σ xᵢ)`

**Por que 0,49 e não mais?** Como 80% das skills têm exatamente 1 cópia, a base da distribuição é "plana". A desigualdade vem do topo. Por isso o Gini sozinho engana, e o artigo reporta também o **top 1%**, que é mais intuitivo.

**Por que isso importa para segurança:** se o reuso é concentrado, **revisar poucas skills populares protege muitas instalações**. É o argumento da Discussão.

---

## 4. Detecção de capacidades por expressão regular

### O que é
Para cada uma das 9 capacidades, `patterns.py` tem uma expressão regular. Exemplo simplificado de `pipe_to_shell`: `curl ... | sh` ou `wget ... | bash`. Se o padrão aparece no texto, a skill recebe `risk_pipe_to_shell = True`.

### Por que regras e não um modelo
* **Transparência e reprodutibilidade:** qualquer pessoa pode ler o padrão e reaplicá-lo; um modelo treinado é uma caixa-preta.
* **Escala:** roda em 1,6 milhão de textos em minutos, sem custo.
* **Comparabilidade:** os trabalhos anteriores sobre skills e MCP também usam detecção por padrões.

### O limite: a regra detecta uma **menção**, não uma **instrução**
"Never commit API keys" dispara o detector de segredos. Por isso cada detecção é tratada como **candidata**, e a seção 8 mede quantas candidatas são instruções reais (**precisão**).

### Prevalência e exposição
* **Prevalência** = fração de **skills distintas** com a capacidade (segredos: 17,6%).
* **Exposição** = fração de **ocorrências** com a capacidade (segredos: 19,9%). Quando a exposição é maior que a prevalência, as skills com essa capacidade são **mais copiadas** que a média.

### Prevalência ajustada
`prevalência ajustada ≈ prevalência detectada × precisão`

Segredos: 17,6% × 2/12 ≈ **2,9%**. Instalar pacotes: 11,9% × 10/12 ≈ **9,9%**. É assim que o artigo chega a "no máximo ~2% das skills instruem uma capacidade de gravidade alta".

**O que não medimos: recall** (de todas as instruções reais, quantas o detector acha). Isso exigiria ler skills **não** detectadas, procurando o que a regex deixou passar. Fica como limitação: os números são limites inferiores em relação ao que a regex não cobre.

---

## 5. Famílias de variantes e deriva

(Detalhes em `familias_de_variantes.md`.)

1. Skills com o mesmo `name` normalizado e **pelo menos 2 textos diferentes** formam uma família (161.043 famílias).
2. Em cada família, a **referência** é a skill mais copiada; o empate é resolvido pelo commit mais antigo. Ela é um **proxy** da versão original, que a base não registra.
3. Cada outra skill da família é uma **variante** (788.712). Para cada variante e cada capacidade, comparamos com a referência:

| | Referência **não** tem | Referência **tem** |
|---|---|---|
| Variante **tem** | **acrescentou** (b) | manteve |
| Variante **não** tem | manteve (ausente) | **removeu** (c) |

Esse é um **desenho pareado**: cada variante é comparada com a **sua** referência, não com a média geral. Isso controla tudo o que a família tem em comum (o tema, o tipo de tarefa).

**17,3% das variantes acrescentam pelo menos uma capacidade.** Sozinho, esse número não diz se copiar **piora** as skills, porque elas também podem **remover** capacidades. Para isso serve o McNemar.

---

## 6. Teste exato de McNemar

### A pergunta
"Quando uma variante difere da referência numa capacidade, ela tende mais a **acrescentar** ou a **remover**?"

### A lógica
Na tabela 2×2 acima, as células "manteve" não dizem nada sobre direção. Só os **pares discordantes** importam: `b` (acrescentou) e `c` (removeu). Se as edições não tivessem direção em relação ao risco, cada discordância seria uma "moeda honesta": 50% de chance de ser acréscimo e 50% de ser remoção.

O **teste exato** pergunta: com `b + c` lançamentos de uma moeda honesta, qual a probabilidade de obter um resultado tão desequilibrado quanto `b` contra `c`? Isso é um teste binomial com p = 0,5, implementado como `binomtest(b, b + c, 0.5)` em `analyses/rq5_security.py`.

### Exemplo: `curl | sh`
* b = 3.429 acréscimos, c = 3.175 remoções, total 6.604.
* Sob a moeda honesta, esperaríamos 3.302 de cada lado.
* Observamos 51,9% de acréscimos; a chance de um desvio desses por acaso é **p = 0,002**.
* Conclusão: **`curl | sh` é acrescentado mais do que removido**, e a diferença não é acaso.

Contraexemplo, `git push`: 17.793 × 17.840, p = 0,81. Sem direção: as edições mexem nessa capacidade, mas tanto acrescentam quanto removem.

### Por que McNemar e não qui-quadrado comum
O qui-quadrado de independência supõe grupos **independentes**. Aqui cada variante está **pareada** com a sua referência, e o McNemar é o teste próprio para proporções pareadas (McNemar, 1947). A versão **exata** (binomial) evita aproximações e funciona para qualquer tamanho.

### Cuidado: significância ≠ importância
Com milhares de pares, diferenças **pequenas** já dão p minúsculo. No `curl | sh`, a razão é 3.429 / 3.175 ≈ **1,08**: 8% mais acréscimos que remoções. O resultado é **real**, mas o efeito é **modesto**. O artigo sustenta a conclusão em três coisas juntas: direção consistente, p pequeno **e** detector confiável (12/12). Na execução dinâmica, o p também é minúsculo, mas o detector acerta 1 em 12, então o resultado **não é interpretado**.

---

## 7. Regressão logística

### A pergunta
O McNemar diz **se** há direção. A regressão pergunta **que tipo de variante** tende a acrescentar capacidade.

### O modelo
* **Resposta (y):** 1 se a variante acrescenta pelo menos uma capacidade, 0 se não. Como y é binário, a regressão linear não serve (preveria valores fora de [0, 1]).
* **Preditores (x):**

| Preditor | Definição | Por que entra |
|---|---|---|
| `log_ref_copies` | log(1 + cópias da referência) | skills famosas são copiadas "como estão"? |
| `log_family_size` | log(tamanho da família) | famílias grandes juntam mais edições (e mais skills sem relação) |
| `cross_owner` | 1 se a variante aparece em mais de um dono | cópia entre pessoas edita mais? |
| `has_scripts` | 1 se a variante traz scripts junto | scripts abrem espaço para comandos de shell |
| `ai_authored` | 1 se o primeiro commit tem trailer de assistente | assistentes acrescentam capacidades? |

**Por que o log nas contagens:** cópias vão de 1 a 1.409, uma distribuição muito assimétrica. Com o log, "dobrar as cópias" tem sempre o mesmo efeito, seja de 2 para 4 ou de 500 para 1.000.

### Como funciona
A regressão logística modela o **log da chance (log-odds)**:

`log( P(y=1) / (1 − P(y=1)) ) = β₀ + β₁x₁ + … + β₅x₅`

* **Chance (odds)** = P / (1 − P). Se 15% das variantes acrescentam, a chance é 0,15 / 0,85 ≈ 0,18. (O intercepto do modelo é 0,182: é a chance quando todos os preditores valem 0.)
* Os coeficientes β são estimados por **máxima verossimilhança** (`statsmodels.formula.api.logit`).

### Razão de chances (odds ratio, OR)
`OR = exp(β)` é o **fator que multiplica a chance** quando o preditor aumenta 1 unidade, **mantendo os outros fixos**.

| Preditor | OR | IC 95% | Leitura |
|---|---|---|---|
| `has_scripts` | 1,46 | 1,44–1,49 | ter scripts multiplica a chance por 1,46 (+46%) |
| `log_family_size` | 1,36 | — | cada unidade de log (família ~2,7× maior) → +36% |
| `ai_authored` | 1,22 | 1,19–1,24 | escrita com assistente → +22% |
| `cross_owner` | 0,97 | — | praticamente nenhum efeito |
| `log_ref_copies` | 0,69 | — | referência ~2,7× mais copiada → chance 31% **menor** |

Regras de leitura:
* **OR = 1:** sem efeito. **OR > 1:** aumenta a chance. **OR < 1:** diminui.
* Se o **IC não cruza 1**, o efeito é estatisticamente diferente de zero.
* **Chance não é probabilidade.** OR 1,46 não quer dizer "46% mais provável" em termos de probabilidade. Quando o evento é raro (abaixo de ~10–20%), as duas coisas ficam parecidas; aqui (~17%) é uma aproximação razoável para comunicação, mas o termo correto é **chance**.

### Pseudo-R² de McFadden = 0,03
Mede quanto o modelo melhora em relação a um modelo sem preditores: `1 − logL(modelo) / logL(só intercepto)`. Ele não é o R² da regressão linear (valores de 0,2–0,4 já são considerados bons ajustes). **0,03 é baixo**: os preditores estão associados ao desfecho, mas explicam pouco do porquê uma variante acrescenta capacidade. Por isso o artigo fala em **"associações modestas, não preditores"**.

### Limitações que você precisa saber defender
1. **Associação, não causa.** Não dá para dizer que "usar assistente **causa** acréscimo de capacidades".
2. **Confusão com o local.** `ai_authored` só pode valer 1 onde há histórico, quase só em `.claude/skills/`. Parte do efeito pode ser do **local**, não do assistente.
3. **Observações não independentes.** Variantes da mesma família se parecem entre si, e o modelo trata cada variante como independente. Com isso, os ICs ficam **estreitos demais**. A correção padrão é usar erros-padrão **agrupados por família** (*cluster-robust*). Os ORs não mudam; os ICs alargam. Com 788 mil observações, as conclusões provavelmente se mantêm, mas vale citar nas Ameaças à validade ou rodar como teste de robustez.
4. **p-valores ≈ 0 em tudo.** Com 788 mil linhas, praticamente qualquer efeito é "significativo". Por isso o foco é o **tamanho** do OR, não o p.

---

## 8. Validação dos detectores

### Desenho da amostra
* **Estratificada:** 12 trechos **por capacidade** (9 × 12 = 108), em vez de 108 sorteados do total. Assim capacidades raras, como `curl | sh` com 0,7%, também são avaliadas. Num sorteio geral, quase todos os trechos seriam de segredos.
* **Aleatória com semente fixa (42):** reproduzível, sem escolha a dedo.
* **Contexto:** ~160 caracteres antes e depois do ponto detectado.

### Rótulos
`instructs` (manda o agente fazer), `mentions` (fala sem mandar, por exemplo uma proibição), `false_match` (outro sentido da palavra).

**Precisão** = `instructs` / 12, com IC de Wilson (seção 2).

### Dois avaliadores e κ de Cohen
Se só uma pessoa rotula, não sabemos se o critério é claro ou se é a opinião dela. Com dois avaliadores, medimos a **concordância**. A concordância bruta engana, porque parte dela acontece **por acaso**. O κ (kappa) desconta esse acaso:

`κ = (pₒ − pₑ) / (1 − pₑ)`

* **pₒ** = concordância observada;
* **pₑ** = concordância esperada por acaso, calculada a partir de quanto cada avaliador usa cada rótulo.

**Nosso cálculo (decisão binária: instructs ou não, 108 trechos):**

| | Você: instructs | Você: não |
|---|---|---|
| **Claude: instructs** | 56 | 4 |
| **Claude: não** | 9 | 39 |

* pₒ = (56 + 39) / 108 = **0,880**
* Claude marcou `instructs` em 55,6% dos trechos e você em 60,2%. Por acaso, concordaríamos em pₑ = 0,556 × 0,602 + 0,444 × 0,398 = **0,511**
* κ = (0,880 − 0,511) / (1 − 0,511) = **0,75**

Escala usual (Landis e Koch, 1977): < 0,20 fraca; 0,21–0,40 razoável; 0,41–0,60 moderada; **0,61–0,80 substancial**; > 0,80 quase perfeita.

**Por que reportamos dois κ:**
* **0,75** em todos os 108 trechos. Mas em 65 deles você via os rótulos do avaliador 1, o que tende a **inflar** a concordância (efeito de ancoragem).
* **0,54** nos 43 trechos que você rotulou **às cegas**: é a estimativa mais conservadora e mais honesta da clareza do critério.

**Por que o κ binário e não o de 3 classes (0,66):** a maioria das divergências foi entre `mentions` e `false_match` (ex.: "never skip hooks": proibição ou outro sentido?). As duas classes contam como "não instrução", então essas divergências **não mudam a precisão**. O κ binário mede a concordância **na decisão que importa**.

### Consenso (adjudicação)
As 13 divergências na decisão binária foram discutidas, e o rótulo final foi para `label_final`. A precisão é calculada com `label_final`; o κ, com os rótulos **antes** da discussão (`label` × `label_2`). Misturar os dois inflaria o κ artificialmente.

---

## 9. Princípios que atravessam o estudo

1. **Tamanho de efeito antes de p-valor.** Com amostras de centenas de milhares, quase tudo é "significativo". Pergunte sempre: de quanto é a diferença?
2. **Viés não aparece no intervalo de confiança.** O IC mede erro de **amostragem**. Erros de **medição** (trailer apagado, regex que confunde menção com instrução, família que junta skills sem relação) precisam ser discutidos à parte: Ameaças à validade.
3. **Limites inferiores e superiores.** Autoria por assistente é um **limite inferior** (trailers podem ser apagados). Prevalência detectada é um **limite superior** de instruções reais (a precisão é < 1).
4. **Validar antes de interpretar.** Um resultado estatisticamente forte com um detector ruim (execução dinâmica) não é interpretado.

---

## 10. Onde entraria machine learning (trabalho futuro)

| Problema atual | Abordagem com ML | Ganho esperado |
|---|---|---|
| Regex confunde instrução e proibição | Classificador (por exemplo, um modelo de linguagem como juiz, ou um modelo fino treinado nos rótulos) que decide `instructs`/`mentions` | precisão maior em segredos, execução dinâmica e desligar confirmações |
| Famílias por nome juntam skills sem relação | **MinHash + LSH** (similaridade de Jaccard entre conjuntos de palavras) para agrupar por **conteúdo** | famílias mais fiéis; já existe esboço em `reuse.minhash_families` |
| Não sabemos qual cópia veio de qual | Reconstrução de **genealogia** por similaridade + datas | referência real em vez de proxy |
| Recall desconhecido | Amostra de skills **não** detectadas + rotulagem | estimar o que a regex deixa passar |

Para qualquer um desses, a amostra rotulada (`validation_sample.csv`) é o ponto de partida: vira **conjunto de teste**, e precisaria crescer para servir também de treino.

---

## 11. Glossário rápido

| Termo | Significado |
|---|---|
| IC 95% | faixa que, em repetições do estudo, conteria o valor real em 95% das vezes |
| p-valor | probabilidade de ver um resultado tão extremo **se não houvesse efeito** |
| Chance (odds) | P / (1 − P) |
| Razão de chances (OR) | quanto a chance é multiplicada quando o preditor sobe 1 unidade |
| Pseudo-R² | quanto o modelo logístico melhora sobre um modelo sem preditores |
| Precisão | das detecções, fração que é correta |
| Recall (sensibilidade) | dos casos reais, fração que é detectada (não medido aqui) |
| κ de Cohen | concordância entre avaliadores descontado o acaso |
| Pareado | cada observação é comparada com o seu próprio par (variante × referência) |
| Estratificada | amostra sorteada separadamente dentro de cada grupo |

## Referências das técnicas
* E. B. Wilson (1927), intervalo de Wilson. L. D. Brown, T. T. Cai, A. DasGupta (2001), "Interval Estimation for a Binomial Proportion", *Statistical Science*.
* Q. McNemar (1947), teste para proporções pareadas.
* J. Cohen (1960), kappa. J. R. Landis, G. G. Koch (1977), escala de interpretação do kappa, *Biometrics*.
* D. McFadden (1974), pseudo-R² para modelos de escolha discreta.
* C. Gini (1912), coeficiente de desigualdade.
