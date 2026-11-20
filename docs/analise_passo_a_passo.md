# Análise passo a passo: o que cada etapa faz e por quê

Guia para entender o pipeline e os notebooks sem ler o código linha a linha.
Para cada etapa: **o que pergunta** (funcional), **como calcula** (técnico),
**onde está no código** e **o que deu na base completa** (execução de 20/11/2026).

---

## 0. Visão geral do fluxo

```
agent_skills_release.db  (SQLite oficial, 44 GB, Zenodo)
        │
        │  scripts/build_features.py   (~2 h, roda uma vez)
        ▼
data/processed/skills.parquet          1 linha por skill distinta + flags de filtro + contagem de cópias
data/processed/skill_features.parquet  features extraídas do texto (riscos, estrutura, autoria por IA)
data/processed/occurrences.parquet     1 linha por arquivo encontrado (ocorrência)
        │
        │  notebooks 01–05  (ou analyses/*.py — mesma lógica)
        ▼
results/tables/*.csv / *.tex   e   results/figures/*.pdf
```

Por que essa divisão: ler 44 GB de texto é caro (horas). Então lemos **uma vez**,
transformamos cada skill em uma linha de números e sim/não, e todas as análises
trabalham em cima dessa tabela pequena (minutos).

### Dois conceitos que aparecem em tudo

| Termo | O que é | Quantos | Usado em |
|---|---|---|---|
| **Ocorrência** | um arquivo `SKILL.md` em um repositório/caminho | 3.797.117 | adoção, reuso (quantas cópias existem) |
| **Skill distinta** (conteúdo) | um texto único, identificado pelo hash git do arquivo (`file_sha`) | 1.877.981 | texto, estrutura, segurança |

Se o mesmo texto aparece em 500 repositórios, isso é **1 skill distinta** com
**500 ocorrências** (`copies = 500`). A base já marca uma cópia "representante"
de cada conteúdo (`dedup_primary = 1`), que é a única com o texto armazenado.

---

## 1. Extração de features — `scripts/build_features.py`

**Funcional:** transformar cada texto de skill em atributos mensuráveis.

**Técnico, em 3 etapas** (as mesmas que aparecem no log `1/3, 2/3, 3/3`):

1. **Skills** (`clean.skills`, [src/gitskills/clean.py](../src/gitskills/clean.py)):
   uma consulta SQL pega os representantes com metadados (repositório, estrelas,
   linguagem, datas de commit) e junta a contagem de cópias de cada conteúdo
   (`copies`, `n_repos`, `n_owners`). Também cria as flags de filtro (seção 2).
2. **Features de texto** (`features.build_features`, [src/gitskills/features.py](../src/gitskills/features.py)):
   lê os textos em blocos de 20 mil, em paralelo nos núcleos da CPU, e para cada
   skill calcula:
   - **frontmatter**: separa o cabeçalho YAML (`---`) do corpo; verifica se `name`
     e `description` seguem a especificação (tamanho, formato);
   - **estrutura**: nº de palavras, linhas, títulos, listas, blocos de código, URLs;
   - **ferramentas citadas**: Claude, Codex, Cursor… (regex em `patterns.AGENT_TOOLS`);
   - **capacidades de risco**: 9 colunas sim/não `risk_*` (regex em `patterns.RISK_PATTERNS`, ver seção 5);
   - **autoria por IA**: procura no texto do primeiro commit um trailer
     `Co-authored-by: Claude/Cursor/Copilot/...` → `first_commit_ai`; e se o autor
     do commit é uma conta do tipo Bot → `first_commit_bot`.
3. **Ocorrências** (`clean.occurrences`): todas as 3,8 M linhas com o dono e os
   metadados do repositório, sem texto.

### 1.1 Seleção das features: critério, descrição e justificativa

**Critério geral.** Não houve seleção automática (correlação, importância,
eliminação recursiva), porque o objetivo não é prever algo, e sim **medir
construtos definidos pelas perguntas de pesquisa**. Cada feature foi definida
**a priori** a partir de três fontes:

1. **Questões de pesquisa:** cada feature responde a uma RQ (tabela abaixo).
2. **Especificação oficial de Agent Skills** (agentskills.io): define o que é uma
   skill válida (`name` em minúsculas com hífens, até 64 caracteres; `description`
   obrigatória e com limite de tamanho; chaves permitidas no frontmatter). As
   features de conformidade medem a aderência a essas regras.
3. **Taxonomias de segurança e literatura:** as categorias de risco seguem
   ataques conhecidos à cadeia de suprimentos de software (execução de código
   baixado sem verificação, escalada de privilégio, exposição de credenciais) e
   foram mapeadas para a CWE mais próxima.

**Critérios de desenho** aplicados a todas:
- **Extraíveis só do texto ou dos metadados do commit**, de forma determinística
  e reprodutível (regex e parsing YAML, sem modelo de linguagem), para rodar em
  1,88 M skills em ~2 h.
- **Interpretáveis**: cada coluna é um sim/não ou uma contagem que se explica em
  uma frase no artigo.
- **Versionadas**: os vocabulários ficam em `patterns.py`, então a lista exata
  vai no pacote de replicação.
- **Validáveis**: as features baseadas em regex têm a precisão medida em uma
  amostra rotulada à mão (notebook 05).

Todas as 1.877.981 skills distintas recebem todas as features (sem filtro de
linhas); os filtros da população estrita são aplicados depois, em cada análise.

#### Grupo A — Capacidades sensíveis à segurança (RQ5, usadas no artigo)

| Feature | Descrição | Justificativa |
|---|---|---|
| `risk_pipe_to_shell` | baixa um script e executa direto (`curl … \| sh`) | executa código remoto sem verificação de integridade; vetor clássico de cadeia de suprimentos (CWE-494) |
| `risk_safety_bypass` | desliga confirmações (`--dangerously-skip-permissions`, `--no-verify`, `--yolo`) | remove a última barreira humana antes de o agente agir (CWE-862) |
| `risk_destructive_fs` | apaga ou sobrescreve dados (`rm -rf`, `mkfs`, `dd if=`) | dano irreversível se a instrução for maliciosa ou errada |
| `risk_dynamic_exec` | executa código montado em tempo de execução (`eval`, `exec(`, `base64 -d`, `subprocess`) | permite esconder o que será executado; injeção de comando (CWE-95/78) |
| `risk_privilege` | pede privilégio elevado (`sudo`, `chmod 777`, `chown`) | amplia o impacto de qualquer outra ação (CWE-250) |
| `risk_secrets` | menciona credenciais (API key, password, `.env`, `~/.ssh`, `.aws/credentials`) | o agente pode ler e vazar segredos (CWE-522); "token" sozinho foi excluído porque em skills costuma significar tokens de LLM |
| `risk_package_install` | instala pacotes (`pip`/`npm`/`brew`/`apt install`, `npx`) | traz código de terceiros para a máquina; ponte para dependências vulneráveis (CWE-1357) |
| `risk_remote_fetch` | baixa conteúdo remoto (`curl`, `wget`, `requests.get`, `fetch(`) | entrada não confiável; gravidade baixa porque costuma ser legítimo |
| `risk_git_push` | publica alterações (`git push`, `--force`) | o agente altera repositórios remotos; gravidade baixa |

Cada uma é um **sim/não** (o texto contém o padrão ou não). Escolhemos sim/não
em vez de contagem porque a pergunta é "a skill concede essa capacidade?", e
porque a comparação entre variante e referência (deriva) fica direta: acrescentou
ou removeu.

#### Grupo B — Autoria (RQ1 e preditor na RQ5, usadas no artigo)

| Feature | Descrição | Justificativa |
|---|---|---|
| `first_commit_ai` | nome do assistente no trailer `Co-authored-by:` do primeiro commit (Claude, Cursor, Copilot…) | é o registro explícito, deixado pela própria ferramenta, de que um agente escreveu o arquivo; mede a autoria por agentes (RQ1) e entra como preditor de deriva (RQ5) |
| `first_commit_bot` | o autor do primeiro commit é uma conta do tipo Bot no GitHub | cobre automações que não deixam trailer |

Usamos o **primeiro** commit porque ele registra quem criou a skill naquele
repositório. É um limite inferior: quem apaga o trailer não é contado.

#### Grupo C — Conformidade com a especificação (RQ2, secundária)

| Feature | Descrição | Justificativa |
|---|---|---|
| `name_spec_ok` | `name` segue o formato e o limite de tamanho da especificação | mede se o ecossistema segue o padrão aberto ou só imita um formato |
| `desc_spec_ok` | `description` existe, respeita o limite e não tem `<` | a descrição é o que o agente usa para decidir quando ativar a skill |
| `fm_keys`, `fm_extra_keys` | chaves do frontmatter e quantas fogem da especificação | mostra extensões proprietárias do formato |
| `has_allowed_tools` | declara `allowed-tools` (restrição de ferramentas) | sinal de preocupação com segurança, contraponto ao grupo A |

#### Grupo D — Ferramentas citadas (RQ2, secundária)

| Feature | Descrição | Justificativa |
|---|---|---|
| `tools_named`, `n_tools_named` | quais agentes o texto menciona (Claude, Codex, Cursor, Gemini…) | testa se a skill é neutra ou presa a uma ferramenta específica |

#### Grupo E — Estrutura e qualidade do texto (RQ4, secundária)

| Feature | Descrição | Justificativa |
|---|---|---|
| `body_words`, `body_lines` | tamanho do corpo | análogo às métricas de tamanho de software (LOC) |
| `n_headings`, `n_list_items`, `n_code_blocks`, `n_shell_blocks` | quanto o texto é estruturado e quanto código traz | instruções estruturadas tendem a ser mais seguidas; blocos shell indicam execução |
| `desc_words`, `desc_chars`, `desc_has_trigger` | tamanho da descrição e se diz **quando** usar ("use when…") | a especificação recomenda dizer quando ativar; testa se isso se associa a mais reuso |
| `n_directives`, `directives_per_100w` | palavras imperativas fortes (MUST, NEVER, ALWAYS, CRITICAL) | mede o "tom" da instrução, análogo a densidade de regras |
| `n_urls`, `non_ascii_ratio` | links externos; proporção de caracteres fora do ASCII | dependência de conteúdo externo; proxy de idioma |

#### O que está no artigo e o que não está

Para RQ1, RQ3 e RQ5, o artigo usa **11 colunas**: as 9 do grupo A e as 2 do
grupo B. A RQ3 não usa este arquivo: ela trabalha com o número de cópias, que
vem do `skills.parquet`. Os grupos C, D e E foram calculados no mesmo passo
porque o custo marginal é quase zero (o texto já está carregado). Eles ficam
disponíveis para RQ2 e RQ4 e para trabalho futuro, mas não entram nas conclusões
do artigo. Também ficaram sem uso: `n_risk_categories` e `last_commit_ai`.

**Limitação comum:** regex detecta **menção**, não intenção ("nunca exponha a API
key" conta como `risk_secrets`). Por isso a precisão por categoria (notebook 05)
precisa ser reportada antes de interpretar as prevalências.

---

## 2. Notebook 01 — Dados, limpeza e população

Corresponde à etapa **2 da metodologia MSR (seleção e coleta de dados)**.

### 1.1 Tamanho da base
Conta linhas das 4 tabelas do SQLite. Resultado: 3.797.117 artifacts,
7.264.865 arquivos irmãos, 282.200 repositórios, 7 execuções de mineração.

### 1.2 Carrega as tabelas processadas
Só lê os Parquets da seção 1.

### 1.3 Critérios de seleção: a população "estrita"
**Funcional:** a base é propositalmente inclusiva (guarda arquivos que não são
skills "de verdade"). Definimos uma população conservadora que corresponde à
especificação, e reportamos quanto cada filtro remove.

**Técnico** (`clean.add_flags` e `clean.strict`), filtros cumulativos:

| Filtro | Regra | Restam |
|---|---|---|
| todos os representantes | — | 1.877.981 (100%) |
| nome exato `SKILL.md` | `filename == "SKILL.md"` | 1.842.600 (98,1%) |
| frontmatter válido | `frontmatter_valid == 1` (campo da própria base) | 1.610.957 (85,8%) |
| hash verificado | `content_sha_ok in (1, 2)` | 1.610.917 |
| não anterior ao formato | primeiro commit ≥ 01/10/2025 (quando há data) | 1.610.839 |
| não é symlink | heurística: 1 linha, sem títulos, sem frontmatter | 1.610.839 (85,8%) |

Atenção: "não anterior ao formato" só age onde há histórico, e o filtro de symlink
não remove nada porque o de frontmatter já pegou esses casos.

### 1.4 Onde os arquivos ficam
`canonical` = `.claude/skills/<nome>/SKILL.md`; `skills-dir` = outra pasta `skills/`;
`other` = qualquer outro lugar.

### 1.5 Qualidade: cobertura do histórico de commits
**Funcional:** a base **não** baixou o histórico de todos os arquivos (seria caro
demais); amostrou. Precisamos saber onde as datas são confiáveis.

| Local | Skills (estrita) | Com histórico |
|---|---|---|
| canonical | 241.559 | 99,6% |
| skills-dir | 901.118 | 11,4% |
| other | 468.162 | 11,3% |

**Consequência:** séries temporais (RQ1) usam só `canonical`. Qualquer número que
dependa de data ou autor de commit vale para ~396 mil skills, não para todas.

### 1.6 Visão exploratória
Distribuição de cópias por skill (escala log-log: muitas skills com 1 cópia,
poucas com centenas) e tamanho do corpo.

---

## 3. Notebook 02 — RQ1: Adoção e autoria por agentes

**Pergunta:** quão rápido o formato se espalhou e quantas skills os próprios
agentes escreveram?

### 2.1 Novas skills por mês
**Técnico** (`adoption.monthly_cohorts`): pega skills com histórico, de locais com
cobertura ≥ 90% (só `canonical`), agrupa pelo mês do primeiro commit e conta.
Isso é uma **coorte mensal**: "quantas skills nasceram em cada mês".

### 2.2 Autoria por assistente
**Técnico:** para cada skill com histórico, `ai_first = tem trailer de IA OU autor é Bot`.
Proporção geral + **intervalo de confiança de Wilson 95%**.

> **Wilson** é a forma recomendada de calcular a margem de erro de uma proporção
> (mais precisa que "p ± 1,96·erro" quando p é pequeno ou n é pequeno).

**Resultado:** 126.424 / 396.247 = **31,9% (IC 31,8–32,1%)**. Assistentes:
Claude 116.609, Cursor 3.311, Copilot 2.435, Codex 250, Devin 51.

**Limitações:** (a) é um **limite inferior**: só conta quem deixou o trailer
`Co-authored-by` (muitos usuários removem ou a ferramenta não adiciona);
(b) o denominador mistura `canonical` (completo) com amostras de ~11% dos outros locais.

---

## 4. Notebook 03 — RQ3: Reuso sem gerenciador de pacotes

**Pergunta:** skills se espalham por cópia. Quanto se copia, quem copia de quem?

### 3.1 Concentração
**Técnico** (`reuse.concentration`, [src/gitskills/reuse.py](../src/gitskills/reuse.py)),
sobre o vetor `copies` de cada skill distinta:

| Métrica | O que significa | Estrita |
|---|---|---|
| `share_singletons` | % de conteúdos que aparecem uma vez só | 79,6% |
| `share_occ_duplicated` | % das ocorrências que são cópias de outra | 52,5% |
| `top1pct_share_of_occ` | quanto do total o 1% mais copiado representa | 27,0% |
| `gini` | desigualdade (0 = todos iguais, 1 = um só concentra tudo) | 0,49 |
| `max_copies` | conteúdo mais copiado (`pdf`) | 1.409 |

Leitura: **cauda longa** — a maioria é única, mas um pequeno grupo de "templates"
domina as cópias.

### 3.2 Reuso entre donos diferentes
Entre conteúdos com mais de 1 cópia, `cross_owner = n_owners > 1`.
**Resultado: 65,6%** cruzam donos → é reuso de ecossistema (gente copiando de
outros), não só uma pessoa duplicando nos próprios repositórios.

### 3.3 Famílias de variantes
**Funcional:** uma "variante" é uma cópia **editada** (texto diferente, mesma skill).
**Técnico atual** (`reuse.name_families`): agrupa skills distintas que têm o mesmo
`name` normalizado no frontmatter (minúsculas, só letras/números/hífen); família
precisa de ≥ 2 conteúdos.

**Limitação importante:** nomes genéricos (`pdf`, `code-review`, `testing`) juntam
skills **sem relação** entre si. Isso infla a "deriva" medida na RQ5. A
alternativa já implementada, mas não executada, é `reuse.minhash_families`
(agrupa por similaridade do texto — MinHash/LSH, limiar 0,8).

---

## 5. Notebook 04 — RQ5: Capacidades sensíveis à segurança e deriva

**Pergunta:** as skills dão ao agente poderes perigosos? E cópias editadas
acrescentam esses poderes?

### O que é "risco" aqui
Não é vulnerabilidade (CVE). É **capacidade**: a skill instrui o agente a fazer
algo que, se a skill for maliciosa ou mal escrita, pode comprometer a máquina ou
os dados do usuário. Detecção por regex no texto (`patterns.RISK_PATTERNS`), com
nível de gravidade e CWE mais próxima (`patterns.py`, adicionado no PR #1):

| Categoria | Exemplo do que casa | Gravidade | CWE |
|---|---|---|---|
| pipe_to_shell | `curl … \| sh` | alta | CWE-494 |
| safety_bypass | `--dangerously-skip-permissions`, `--no-verify` | alta | CWE-862 |
| destructive_fs | `rm -rf`, `mkfs`, `dd if=` | alta | CWE-732 |
| dynamic_exec | `eval`, `exec(`, `base64 -d`, `subprocess` | alta | CWE-95/78 |
| privilege | `sudo`, `chmod 777` | média | CWE-250 |
| secrets | api key, password, `.env`, `~/.ssh` | média | CWE-522 |
| package_install | `pip install`, `npm install`, `npx` | média | CWE-1357 |
| remote_fetch | `curl`, `wget`, `requests.get` | baixa | — |
| git_push | `git push`, `--force` | baixa | — |

### 4.1 Prevalência e exposição
`share_of_skills` = % de skills distintas com a capacidade;
`share_of_occurrences` = o mesmo, ponderado pelo nº de cópias (exposição real).

Resultado (skills): segredos 17,6%, instalar pacotes 11,9%, baixar remoto 8,6%,
execução dinâmica 4,4%, sudo/chmod 2,1%, git push 3,8%, apagar 1,1%,
pipe-to-shell 0,7%, safety bypass 0,7%. **Ao menos uma de gravidade alta: 6,4%.**

### 4.2 Deriva entre cópias editadas
**Técnico** (`reuse.variant_drift`): em cada família, a **referência** é o membro
mais copiado (proxy da "original" — a base não diz qual é a original). Para cada
outra variante e cada categoria:
- `added` = variante tem, referência não tem;
- `removed` = referência tem, variante não tem.

**Resultado:** 136.096 / 788.712 variantes = **17,3% (IC Wilson 17,2–17,3%)**
acrescentam ao menos uma capacidade.

**Teste de McNemar** (exato, via teste binomial nos pares discordantes): se a
deriva fosse aleatória, acrescentar e remover seriam igualmente prováveis (50/50).

| Capacidade | Acrescentou | Removeu | Direção | Precisão do detector (notebook 05) |
|---|---|---|---|---|
| dynamic_exec | 19.016 | 15.605 | mais acrescenta (p ≈ 10⁻⁷⁵) | 0,08: **não interpretar** |
| pipe_to_shell | 3.429 | 3.175 | **mais acrescenta** (p = 0,002) | 1,00 |
| package_install | 40.320 | 51.713 | mais remove | 0,83 |
| secrets | 57.422 | 65.252 | mais remove | 0,17 |
| safety_bypass | 4.477 | 5.527 | mais remove | 0,33 |
| destructive_fs | 5.055 | 5.741 | mais remove | 0,83 |
| git_push | 17.793 | 17.840 | sem diferença (p = 0,81) | 0,58 |

Leitura: a deriva vai **nos dois sentidos**; não há aumento geral de risco. A
exceção confiável é `curl | sh`, que cresce nas cópias. A alta aparente da
execução dinâmica é um artefato do detector: em 7 de 12 trechos validados, a
palavra "eval" significa *evaluation* (avaliação), não execução de código. Nas
categorias de baixa precisão, parte das "remoções" pode ser só uma regra do tipo
"nunca use `--no-verify`" que sumiu do texto.

### 4.3 Regressão logística: quais variantes acrescentam risco?
**Técnico:** variável resposta = variante acrescenta ≥ 1 capacidade (0/1).
Preditores e **razão de chances (OR)** — OR > 1 aumenta a chance, OR < 1 diminui:

| Preditor | OR | Leitura |
|---|---|---|
| log(cópias da referência) | 0,69 | variantes de skills muito populares acrescentam **menos** |
| log(tamanho da família) | 1,36 | famílias maiores → mais acréscimos |
| variante tem scripts | 1,46 | **+46%** de chance |
| variante escrita com assistente | 1,22 | **+22%** de chance |
| variante copiada entre donos | 0,97 | efeito desprezível |

Pseudo R² = 0,03: o modelo **explica pouco** da variação — os efeitos existem
(n grande → todos significativos), mas são modestos. Reportar como associação,
não como previsão.

**Cuidados de interpretação:**
- `ai_authored` só pode ser 1 para variantes com histórico (canonical na maioria):
  parte do efeito pode ser "estar em `.claude/skills/`".
- `cross_owner` aqui é "o conteúdo da variante aparece em >1 dono", não "a variante
  foi feita por outro dono que não o da referência".

---

## 6. Notebook 05 — Validação manual

**Funcional:** as regex detectam **menção**, não intenção ("nunca exponha sua API
key" conta como `secrets`). Antes do artigo precisamos da **precisão** de cada
categoria.

**Técnico:** gera `results/tables/validation_sample.csv` com uma amostra
estratificada por categoria. Você (idealmente com um segundo avaliador) marca cada
linha como verdadeiro/falso positivo; o notebook calcula a precisão por categoria.
Com dois avaliadores, reporte a concordância com **κ de Cohen**.

---

## 7. Mapa para a metodologia MSR (slide da disciplina)

| Etapa MSR | Onde está |
|---|---|
| 1. Questão de pesquisa | RQ1, RQ3, RQ5 (cabeçalho de cada notebook) |
| 2. Seleção e coleta | Notebook 01 (fonte, filtros, cobertura) |
| 3. Análise e modelagem — exploratória | Notebook 01 §1.6, prevalências |
| 3. — estatística | Wilson, McNemar, regressão logística (02, 04) |
| 3. — qualitativa | Notebook 05 (rotulagem manual) |
| 4. Validação e interpretação | Notebook 05 (precisão), limitações acima, robustez com MinHash (pendente) |

## 8. Pendências que afetam os números

1. Famílias por nome → trocar/comparar com MinHash (seção 4, 3.3).
2. Precisão das regex (notebook 05) — especialmente `secrets` e `remote_fetch`.
3. Autoria por IA é limite inferior e depende da amostra com histórico.
