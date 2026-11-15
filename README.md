# gitskills-mc

Programa de análise do dataset **GitSkills** para o
[MSR 2027 Mining Challenge](https://2027.msrconf.org/track/msr-2027-mining-challenge).

GitSkills (Destefanis, Graziotin, Vaccargiu, Ortu; arXiv 2608.10906) reúne
3.797.117 arquivos `SKILL.md` de 282.200 repositórios públicos do GitHub,
coletados em julho de 2026, agrupados em 1.877.981 conteúdos distintos.
Um único arquivo SQLite (~41 GB) com quatro tabelas: `artifacts`, `repos`,
`artifact_siblings` e `mining_runs`.

## Prazos (AoE)

| Marco | Data |
|---|---|
| Resumo (HotCRP) | **18/12/2026** |
| Artigo (4 págs + 1 de referências, IEEEtran `10pt,conference`, double-anonymous, seção de ética obrigatória) | **23/12/2026** |
| Notificação | 19/01/2027 |
| Camera-ready | 26/01/2027 |

## Início rápido

```bash
python -m venv .venv && source .venv/bin/activate
make install          # pacote + extras (nlp, hf, notebooks, dev)
make sample           # amostra oficial: 13k skills, 277 MB (mesmo schema do dataset completo)
make features         # limpeza + features -> data/processed/*.parquet
make analyses         # EDA + scripts de RQ -> results/tables, results/figures
make test
```

Para o dataset completo: `make full` (Zenodo, ~41 GB) ou `make parquet`
(espelho Parquet no Hugging Face) e depois
`make features DB=data/raw/<arquivo>.db`. Toda consulta escrita sobre a
amostra roda sem mudanças no dataset completo.

## Estrutura

```
src/gitskills/
  config.py      caminhos, URLs, limites da especificação, snapshot
  db.py          acesso somente-leitura ao SQLite (query / iter_query em chunks)
  clean.py       populações e filtros (população "strict") + relatório de filtros
  features.py    features por skill: front matter, conformidade com a spec,
                 estrutura do corpo, ferramentas citadas, capacidades de risco,
                 coautoria por IA nos commits, idioma (opcional)
  patterns.py    vocabulários regex versionados (ferramentas, gatilhos, riscos)
  reuse.py       concentração do reuso (Gini, top-k), famílias de variantes
                 (por nome ou MinHash) e deriva de variantes
  adoption.py    coortes mensais, cobertura do histórico, perfil dos adotantes
  plots.py       estilo de figura para coluna IEEE e exportação de tabelas (.csv/.tex)
scripts/
  download.py         amostra (GitHub) | dataset completo (Zenodo) | Parquet (HF)
  build_features.py   gera data/processed/skills.parquet e occurrences.parquet
analyses/             scripts no formato "percent" (abrem como notebook via jupytext)
  00_eda.py  rq1_adoption.py  rq2_shared_format.py  rq3_reuse.py
  rq4_description_quality.py  rq5_security.py
tests/                banco sintético com o schema real + testes de features e pipeline
```

## Cuidados com os dados (já tratados em `clean.py`)

- **Duas unidades de análise.** Ocorrência (linha de `artifacts`) para adoção
  e reuso; skill distinta (`dedup_primary = 1`, a única com `content`) para
  texto, estrutura e segurança.
- **População "strict".** O dataset inclui `skill.md` em minúsculas, front
  matter inválido e arquivos anteriores ao formato (out/2025). `clean.strict`
  remove esses casos; `population_report` mostra quanto cada filtro retira.
  Na amostra: 13.000 → 11.195 skills (86%).
- **Histórico é amostrado.** Na amostra, `first_commit_at` cobre ~100% das
  skills `canonical` (`.claude/skills/`) mas só ~11% de `skills-dir` e
  `other`. Séries temporais devem usar só classes com cobertura completa ou
  reponderar o estrato.
- **Representante ≠ original.** A cópia enriquecida é escolhida por regra
  determinística; pastas e histórico descrevem só aquele repositório.
- **Caminho atual.** Para arquivos renomeados, `first_commit_at` data o rename.
- **Limite inferior.** Code search só indexa branch padrão, arquivos < 384 KB
  e forks mais estrelados que o pai.

## Questões de pesquisa candidatas

Cada RQ tem um script em `analyses/`. Os números abaixo são da **amostra**
(13k skills) e servem só para avaliar se a pergunta rende; o artigo precisa
dos números do dataset completo.

**RQ1 — Adoção e autoria por agentes.** Com que velocidade o formato se
espalhou depois de out/2025, quem adota primeiro (linguagem, estrelas, idade
do repositório) e quantas skills são escritas pelos próprios agentes?
*Sinal na amostra:* ~30% das skills com histórico têm um trailer
`Co-authored-by` de um assistente de IA no primeiro commit (quase todos Claude).

**RQ2 — Formato compartilhado ou formato do Claude Code?** Qual a fração em
locais neutros (`skills/`) vs específicos (`.claude/skills/`), quantas skills
citam uma ferramenta específica e quão bem seguem a especificação?
*Sinal:* 94% dos `name` e 98% dos `description` respeitam os limites da spec;
Claude é citado em ~2,5k skills, Codex em ~770, Cursor em ~510.

**RQ3 — Reuso sem gerenciador de pacotes.** Quão concentrado é o reuso e ele
atravessa donos diferentes? Quantas variantes (cópias editadas) as skills
populares têm?
*Sinal:* 74% dos conteúdos são únicos, mas 1% dos conteúdos responde por 23%
das ocorrências (Gini 0,53); 76% dos conteúdos duplicados aparecem em mais de
um dono.

**RQ4 — Métricas para instruções em linguagem natural.** Quais métricas de
software (tamanho, churn, clones, legibilidade) têm equivalente em skills? A
descrição (o que o agente casa com a tarefa) prevê reuso e manutenção?
*Sinal:* efeito pequeno; descrições fora da spec são menos copiadas (Cliff's δ ≈ 0,1).

**RQ5 — Confiança e cadeia de suprimentos.** Com que frequência as skills
mandam o agente buscar código remoto, instalar pacotes, tocar em segredos ou
pular confirmações? Variantes de skills populares *acrescentam* essas
capacidades em relação ao membro mais copiado da família?
*Sinal:* 8% das skills fazem fetch remoto e 11% instalam pacotes; ~21% das
variantes acrescentam pelo menos uma categoria de risco ausente da versão mais
copiada (heurística por nome; precisa ser validada).

### Recomendação de foco

Um artigo de 4 páginas comporta 2 ou 3 RQs bem feitas. A combinação mais
original e que mais aproveita o diferencial do dataset (todas as cópias
preservadas) é **RQ3 + RQ5: "reuso por cópia e deriva de segurança entre
variantes"**, com RQ1 (autoria por agentes) como contexto. É o análogo de um
ataque de cadeia de suprimentos num ecossistema sem registro, que os próprios
autores do dataset apontam como aberto.

## Próximos passos

1. Rodar o pipeline no dataset completo (`make full`, depois `make features`;
   a extração é paralela e leva ~20 s por 13k skills em 4 núcleos).
2. Trocar as famílias por nome por `reuse.minhash_families` sobre o conteúdo.
3. Validar os regex de `patterns.py` com uma amostra rotulada manualmente
   (reportar precisão) antes de usar os números no artigo.
4. Taxonomia de propósitos (RQ1b do artigo do dataset): clusterização de
   embeddings das descrições + rotulagem manual.
5. Pacote de replicação anônimo (anonymous.4open.science / Zenodo) e citação
   do snapshot `GitSkills July 2026 (10.5281/zenodo.21875637)`.

## Citação do dataset

G. Destefanis, D. Graziotin, M. Vaccargiu, and M. Ortu, "GitSkills: A Dataset
of Agent Skills on GitHub," in *Proc. MSR '27*, 2027. arXiv:2608.10906.
