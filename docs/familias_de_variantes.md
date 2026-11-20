# Famílias de variantes: da base até o agrupamento

Explicação técnica de como as "famílias" usadas na RQ3 (§3.3) e na RQ5 (deriva)
são construídas, partindo das tabelas do SQLite. Todos os números são da base
completa (execução de 20/11/2026, população estrita).

Código envolvido:
- [src/gitskills/clean.py](../src/gitskills/clean.py): leitura da base, flags e filtro estrito
- [src/gitskills/reuse.py](../src/gitskills/reuse.py): `normalize_name`, `name_families`, `variant_drift`
- [notebooks/03_rq3_reuse.ipynb](../notebooks/03_rq3_reuse.ipynb) §3.3 e [notebooks/04_rq5_security_capabilities.ipynb](../notebooks/04_rq5_security_capabilities.ipynb) §4.2

---

## 1. O que é uma "família" e uma "variante"

- **Skill distinta**: um texto único de `SKILL.md`, identificado pelo hash git do
  arquivo (`file_sha`). Duas cópias idênticas têm o mesmo `file_sha`.
- **Variante**: uma skill distinta que é uma **versão editada** de outra (texto
  diferente, "mesma" skill).
- **Família**: o conjunto de variantes de uma mesma skill.

A base **não** registra quem copiou de quem nem qual texto deriva de qual.
Precisamos **inferir** as famílias. A implementação atual usa uma regra simples:
**skills com o mesmo nome (normalizado) pertencem à mesma família.**

---

## 2. Passo a passo a partir da base

### Passo 1 — Uma linha por skill distinta (SQLite → `skills.parquet`)

Tabela de origem: `artifacts`. Cada linha é uma ocorrência (arquivo em um
repositório). A base marca uma ocorrência "representante" por conteúdo
(`dedup_primary = 1`); só ela tem o texto e os campos derivados preenchidos.

```sql
SELECT a.file_sha, a.name, a.frontmatter_valid, a.filename, a.content_sha_ok,
       a.first_commit_at, ...,  r.owner, r.stars, ...
FROM artifacts a LEFT JOIN repos r ON r.full_name = a.repo_full_name
WHERE a.dedup_primary = 1
```

Em seguida juntamos a contagem de cópias de cada conteúdo (`clean.copies`):

```sql
SELECT file_sha, COUNT(*) AS copies,
       COUNT(DISTINCT a.repo_full_name) AS n_repos,
       COUNT(DISTINCT r.owner)          AS n_owners
FROM artifacts a LEFT JOIN repos r ON r.full_name = a.repo_full_name
GROUP BY file_sha
```

Resultado: **1.877.981 skills distintas**, cada uma com `name` e `copies`.

**De onde vem `name`:** é a coluna `artifacts.name`, preenchida pelos autores do
dataset a partir do campo `name:` do frontmatter YAML do `SKILL.md`. Nós não
recalculamos esse campo; usamos como está na base.

### Passo 2 — Filtro da população estrita (`clean.strict`)

Mantém só skills com nome exato `SKILL.md`, frontmatter válido, hash verificado,
não anteriores a 01/10/2025 e que não são symlink.

Resultado: **1.610.839 skills**.

### Passo 3 — O que acontece com `name` nulo

| | Toda a base | População estrita |
|---|---|---|
| skills distintas | 1.877.981 | 1.610.839 |
| `name` nulo | **244.470** | **0** |

**Todas** as 244.470 skills com `name` nulo têm `frontmatter_valid = 0`
(frontmatter ausente ou YAML inválido, então não há de onde ler o nome). O
filtro "frontmatter válido" do passo 2 remove todas elas **antes** do
agrupamento. Ou seja: **skills sem nome nunca entram em famílias** — nem como
variante, nem como referência. Elas continuam valendo para as métricas de reuso
exato da RQ3 (§3.1 e §3.2) quando se usa a população completa, mas não para a
deriva.

Por segurança, o código também descarta o nome ausente no passo seguinte
(`normalize_name` devolve `None` para valor vazio, e `dropna` remove a linha).

### Passo 4 — Normalização do nome (`reuse.normalize_name`)

```python
n = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
return n or None
```

1. passa para minúsculas;
2. troca qualquer sequência de caracteres que **não** seja `a–z` ou `0–9` por um hífen;
3. tira hífens das pontas;
4. se não sobrar nada, devolve `None`.

Exemplos reais:

| `name` na base | normalizado |
|---|---|
| `Test` | `test` |
| `deepL` | `deepl` |
| `cleanmatic:release` | `cleanmatic-release` |
| `beta with quotes` | `beta-with-quotes` |
| `会议准备` | `None` (descartada) |

Na população estrita:
- **83.107** nomes mudam com a normalização (maiúsculas, espaços, `:` etc.), o
  que permite juntar "Code Review" com "code-review";
- **3.277** nomes viram `None` e são **descartados**. Na amostra que inspecionei,
  são nomes **inteiramente em caracteres não latinos** (chinês, por exemplo
  `会议准备`, `移动端适配`). Isso é um **viés**: skills nomeadas em chinês,
  japonês, coreano etc. ficam fora da análise de deriva.

### Passo 5 — Agrupamento por nome (`reuse.name_families`)

```python
df = skills.assign(family=skills["name"].map(normalize_name)).dropna(subset=["family"])
sizes = df.groupby("family")["file_sha"].transform("nunique")
return df[sizes >= 2]
```

Agrupa pelo nome normalizado e conta quantos **conteúdos distintos** cada nome
tem. Nomes com só 1 conteúdo não têm variantes e saem.

| Etapa | Nomes | Skills |
|---|---|---|
| nomes normalizados distintos | 818.850 | 1.607.562 |
| nomes com 1 único conteúdo (sem variantes, saem) | 657.807 | 657.807 |
| **famílias (≥ 2 conteúdos)** | **161.043** | **949.755** |

Distribuição do tamanho: a mediana é 1 conteúdo por nome; 90% dos nomes têm
até 2; 99% até 16. As maiores famílias:

| família | variantes | ocorrências |
|---|---|---|
| code-review | 3.772 | 6.129 |
| skill-creator | 2.787 | 10.529 |
| commit | 2.441 | 3.553 |
| review | 2.195 | 3.243 |
| frontend-design | 2.156 | 7.562 |
| release | 1.945 | 2.367 |
| brainstorming | 1.407 | 4.222 |

### Passo 6 — Escolha da referência de cada família (`reuse.variant_drift`)

A "original" é desconhecida. Usamos como **referência** (proxy da original) o
membro **mais copiado** da família:

```python
ref = g.sort_values(["copies", "first_commit_at"], ascending=[False, True]).iloc[0]
```

1. maior número de cópias (`copies`);
2. em caso de empate, o primeiro commit mais antigo;
3. se o empate continua (ou não há data), vale a **ordem das linhas** na tabela.

### Passo 7 — Comparação variante × referência

Para cada outra skill da família (variante) e cada uma das 9 capacidades de risco:
- `added_X` = a variante tem `X` e a referência não;
- `removed_X` = a referência tem `X` e a variante não;
- `any_added` = a variante acrescentou pelo menos uma.

Variantes comparadas: 949.755 skills − 161.043 referências = **788.712**. Esse é o
`n` dos 17,3%, do McNemar e da regressão logística na RQ5.

---

## 3. Fluxo resumido com números

```
artifacts (3.797.117 ocorrências)
  └─ dedup_primary = 1 ─────────────────────► 1.877.981 skills distintas
       └─ filtro estrito ─────────────────────► 1.610.839
            (remove os 244.470 com name nulo, todos com frontmatter inválido)
            └─ normalize_name ─────────────────► 1.607.562 com nome utilizável
                 (descarta 3.277 nomes só com caracteres não latinos)
                 ├─ nome único (nenhum outro texto usa) ► 657.807 skills, fora das famílias
                 │     ├─ nunca copiadas ─────────────► 563.108
                 │     └─ só cópias idênticas ─────────►  94.699
                 └─ agrupar por nome, ≥ 2 conteúdos ► 161.043 famílias / 949.755 skills
                      └─ 1 referência por família ─► 788.712 variantes comparadas
```

Conta de fechamento: 1.610.839 = 949.755 (em famílias) + 657.807 (nome único)
+ 3.277 (nome descartado). As 661.084 skills fora das famílias **não se perdem**:
continuam na concentração e no reuso entre donos (RQ3) e na prevalência de
riscos (RQ5). Só não entram na deriva, porque não têm variante com que comparar.
Este funil é calculado ao vivo no notebook 03, seção 3.3.

---

## 4. Problemas encontrados (afetam a RQ5)

1. **Nomes genéricos juntam skills sem relação.** `commit`, `review`, `release`,
   `test` são nomes que muitas pessoas usam para skills escritas do zero. O
   método trata todas como "variantes" de uma original e conta as diferenças
   como deriva. Isso **infla** a deriva medida.
2. **Referência frágil.**
   - Em **72.741** famílias (45%), a referência tem **1 cópia só**: "mais copiada"
     não diz nada sobre ser a original.
   - Em **80.782** famílias (50%) há **empate** no número máximo de cópias; em
     **71.181** delas o desempate acaba sendo a ordem das linhas (falta data),
     ou seja, a referência é **arbitrária**.
3. **Viés de idioma.** Os 3.277 nomes em escrita não latina são descartados.
4. **Nomes iguais com conteúdos não relacionados não são separados, e skills
   relacionadas com nomes diferentes não são unidas** (ex.: alguém copia e renomeia).

## 5. Como melhorar (antes do artigo de 24/11)

- **Famílias por conteúdo (MinHash/LSH):** `reuse.minhash_families` já existe.
  Divide cada texto em sequências de 5 palavras, calcula uma "impressão digital"
  MinHash e agrupa textos com similaridade de Jaccard estimada ≥ 0,8. Resolve os
  problemas 1, 3 e 4. Custo: algumas horas nas ~1,6 M skills.
- **Critério híbrido (mais barato):** mesmo nome **e** similaridade ≥ 0,8 com a
  referência; separa os nomes genéricos em subfamílias.
- **Referência mais robusta:** restringir a famílias cuja referência tenha
  ≥ 2 cópias (ou ≥ 5), e reportar a análise de sensibilidade.
- **Normalização com Unicode:** usar `\w` em vez de `[a-z0-9]` para manter nomes
  em outras escritas.
- **Relatar os dois resultados** (por nome e por conteúdo) como teste de robustez:
  se a direção do McNemar se mantém, a conclusão fica muito mais forte.
