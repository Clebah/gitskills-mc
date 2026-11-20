"""Generate the Jupyter notebooks in notebooks/ (one per methodology step / RQ).

    python scripts/build_notebooks.py          # writes notebooks/*.ipynb (no outputs)
    jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb

The notebooks read data/processed/*.parquet, so run `make features` first.
"""

from pathlib import Path

import nbformat as nbf

OUT = Path(__file__).resolve().parents[1] / "notebooks"
SETUP = """import os, sys
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("GITSKILLS_DB", str(ROOT / "data/raw/agent_skills_release.db"))
import numpy as np, pandas as pd, matplotlib.pyplot as plt
pd.set_option("display.max_colwidth", 80)
from gitskills import clean, db, reuse, adoption, patterns
from gitskills.plots import save, save_table
%matplotlib inline
print("database:", os.environ["GITSKILLS_DB"])"""


def nb(cells):
    book = nbf.v4.new_notebook()
    book.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    book.cells = [nbf.v4.new_markdown_cell(c[3:]) if c.startswith("md:") else nbf.v4.new_code_cell(c) for c in cells]
    return book


NOTEBOOKS = {
"01_data_and_cleaning.ipynb": [
"""md:# 1. Dados: seleção, coleta e limpeza

## O fio da história (os 5 notebooks)
Agent skills são arquivos `SKILL.md` com instruções em linguagem natural que um agente de IA de programação segue com as permissões do usuário. Não existe um registro central (como npm ou PyPI): as skills se espalham **copiando arquivos** entre repositórios. Isso levanta três perguntas, uma por notebook:

1. **Notebook 02 (RQ1):** o ecossistema está crescendo, e quem escreve as skills, pessoas ou os próprios agentes?
2. **Notebook 03 (RQ3):** quanto as skills são copiadas, e as cópias atravessam donos diferentes?
3. **Notebook 04 (RQ5):** as skills dão poderes perigosos ao agente, e as cópias editadas aumentam esses poderes?
4. **Notebook 05:** as regras que detectam esses poderes são confiáveis?

**Este notebook** prepara o terreno: de onde vêm os dados, o que conta como "skill" e onde os dados são confiáveis.

---

### English summary

**Methodology step 2 (MSR): selection and collection of data.**

* **Source:** GitSkills, July 2026 snapshot (Zenodo 10.5281/zenodo.21875637): every `SKILL.md` file found by GitHub code search, with repository metadata, bundled files and sampled commit history.
* **Units of analysis:** an *occurrence* is one file at one repository path (used for adoption and reuse); a *skill* is one distinct content, identified by its git blob hash (used for text and security analyses).
* **Selection criteria:** the *strict* population keeps skills with the exact `SKILL.md` basename, valid front matter, a verified content hash, no symlink, and a first commit on or after October 2025, when the format was released.
* **Quality validation:** we report how many skills each filter removes and how complete the commit history is per location class.""",
SETUP,
"""md:## 1.1 Tamanho da base
**Objetivo:** confirmar que estamos usando a base completa, não a amostra.""",
"""counts = db.table_counts()
counts""",
"""md:**O que os dados mostram:** 3.797.117 arquivos `SKILL.md` (ocorrências) em 282.200 repositórios, mais 7,3 milhões de arquivos que vêm junto com as skills (scripts, referências). É a base completa do snapshot de julho/2026.""",
"""md:## 1.2 Carregar as tabelas processadas
**Objetivo:** separar as duas unidades de análise. Uma **ocorrência** é um arquivo em um repositório (mede adoção e reuso); uma **skill distinta** é um texto único, identificado pelo hash (mede conteúdo e segurança). Se o mesmo texto está em 500 repositórios, é 1 skill com 500 cópias.

`scripts/build_features.py` streams the database once and writes one row per skill (with features) and one row per occurrence.""",
"""skills = clean.load_skills()
occ = clean.load_occurrences()
print(f"{len(skills):,} distinct skills, {len(occ):,} occurrences, {occ.repo_full_name.nunique():,} repositories")""",
"""md:**O que os dados mostram:** 3,8 milhões de arquivos correspondem a só 1,88 milhão de textos diferentes: **metade dos arquivos repete um texto que já existe em outro lugar**. Isso **não** quer dizer que a maioria das skills é copiada. Na seção 1.6 veremos que 79% dos **textos** aparecem uma vez só, e que as cópias se concentram em poucos textos muito populares. Contar arquivos ou contar textos dá respostas diferentes, e as duas são verdadeiras.""",
"""md:## 1.3 Critérios de seleção: a população estrita
**Objetivo:** a base é propositalmente inclusiva e guarda arquivos que não são skills válidas. Definimos uma população conservadora que segue a especificação oficial e mostramos quanto cada filtro remove (cada linha aplica mais um filtro sobre a anterior).

Filtros: nome exato `SKILL.md`; frontmatter YAML válido (de onde vêm `name` e `description`); hash do conteúdo verificado; primeiro commit a partir de out/2025 (lançamento do formato); não ser symlink.""",
"""pop = clean.population_report(skills)
save_table(pop, "eda_population_filters")
pop""",
"""md:**O que os dados mostram:** ficam **1.610.839 skills (85,8%)**. Quase todo o corte vem de dois filtros: frontmatter inválido (−12,3%) e nome diferente de `SKILL.md` (−1,9%). Os outros três removem só 118 skills: os dados são consistentes. As 244.470 skills sem `name` caem todas no filtro de frontmatter.

**Por que importa:** todas as análises de conteúdo (notebooks 02–05) usam esta população, então os resultados valem para skills que seguem o padrão.""",
"""md:## 1.4 Onde os arquivos ficam
**Objetivo:** saber em que pasta as skills ficam, porque isso define a qualidade dos dados de histórico (próxima seção). `canonical` = `.claude/skills/<nome>/SKILL.md`; `skills-dir` = outra pasta `skills/`; `other` = qualquer outro lugar.""",
"""occ["location_class"].value_counts(normalize=True).rename("share").to_frame()""",
"""occ["filename"].value_counts().head(10).rename("files").to_frame()""",
"""md:**O que os dados mostram:** só **9,8%** dos arquivos estão no caminho do Claude Code (`canonical`); 55,4% estão em outras pastas `skills/` e 34,8% em outros lugares. O formato já não é exclusivo de uma ferramenta. Variações do nome (`skill.md`, `Skill.md`) somam ~54 mil arquivos e são excluídas da população estrita.""",
"""md:## 1.5 Qualidade: cobertura do histórico de commits
**Objetivo:** os autores do dataset não baixaram o histórico de commits de todos os arquivos, só de uma amostra. Precisamos saber **onde as datas e os autores são confiáveis** antes de analisar tempo e autoria.""",
"""cov = adoption.history_coverage(clean.strict(skills))
save_table(cov, "rq1_history_coverage")
cov""",
"""md:**O que os dados mostram:** o histórico cobre **99,6%** das skills em `canonical`, mas só **~11%** nas outras pastas. **Consequência para o notebook 02:** a curva de crescimento usa só `canonical`, e a autoria por IA vale para as 396.247 skills com histórico, não para todas.""",
"""md:## 1.6 Visão exploratória: cópias por skill e tamanho do texto
**Objetivo:** ver a forma das distribuições antes de medir. Esquerda: quantas skills têm 1, 2, 10, 100… cópias (eixos em log). Direita: tamanho do texto.""",
"""fig, axes = plt.subplots(1, 2, figsize=(7, 2.6))
vc = skills["copies"].value_counts().sort_index()
axes[0].loglog(vc.index, vc.values, ".", ms=3)
axes[0].set(xlabel="copies of a distinct skill", ylabel="# skills")
b = skills["body_chars"].dropna(); b = b[b > 0]
axes[1].hist(np.log10(b), bins=50)
axes[1].set(xlabel="log10(body characters)", ylabel="# skills")
plt.tight_layout(); plt.show()""",
"""md:**Textos × arquivos.** A tabela abaixo liga os dois jeitos de contar: quantos **textos** são únicos ou copiados, e quantos **arquivos** cada grupo ocupa.""",
"""single = skills["copies"] == 1
view = pd.DataFrame({
    "distinct texts": [int(single.sum()), int((~single).sum())],
    "files (occurrences)": [int(skills.loc[single, "copies"].sum()), int(skills.loc[~single, "copies"].sum())],
}, index=["text appears once", "text has copies"])
view.loc["total"] = view.sum()
view["% of texts"] = (100 * view["distinct texts"] / view.loc["total", "distinct texts"]).round(1)
view["% of files"] = (100 * view["files (occurrences)"] / view.loc["total", "files (occurrences)"]).round(1)
print(f"files that repeat an existing text: {len(occ) - len(skills):,} ({1 - len(skills) / len(occ):.1%})")
view""",
"""md:**O que os dados mostram:**

*Gráfico da esquerda (cópias por skill, eixos em log).* Cada ponto diz quantos textos têm exatamente *x* cópias. Os pontos formam quase uma reta descendente: **cauda longa**. **79%** dos textos aparecem uma vez só, e poucos são copiados centenas de vezes (o máximo é 1.409).

*Por que isso não contradiz a seção 1.2:* os 21% de textos copiados ocupam **61%** dos arquivos, porque cada um aparece muitas vezes (em média ~6 arquivos, alguns centenas). A maioria dos **textos** é única, mas a maioria dos **arquivos** é cópia. É como uma biblioteca em que quase todos os títulos têm um exemplar, mas alguns best-sellers com centenas de exemplares ocupam metade das prateleiras.

*Gráfico da direita (tamanho do texto).* Histograma do tamanho do corpo do `SKILL.md` (sem o cabeçalho), em log10 de caracteres: 2 = 100, 3 = 1.000, 4 = 10.000 caracteres. O log é necessário porque os tamanhos vão de dezenas a centenas de milhares de caracteres. A forma é de sino:
* o pico fica entre ~6.000 e ~7.700 caracteres, e a **mediana é 4.601 caracteres** (umas 2 páginas);
* 80% das skills têm menos de 10.000 caracteres; só 11% têm menos de 1.000;
* nas pontas, ~1% tem menos de 100 caracteres (stubs, testes) e ~1% passa de 41.000 (manuais inteiros).

Leitura: a skill típica não é um atalho de uma linha, e sim um documento de algumas páginas que o agente lê e segue. Em um texto desse tamanho, uma instrução sensível editada no meio passa despercebida por quem copia, o que motiva a RQ5. O gráfico usa as 1,88 M skills distintas; as 92 com corpo vazio ficam de fora (não há log de zero).

## Conclusão do notebook 01
* Trabalhamos com **1.610.839 skills** que seguem a especificação (85,8% da base).
* O reuso por cópia é massivo: metade dos arquivos é cópia de outro.
* Datas e autores só são confiáveis em `.claude/skills/` (99,6%); no resto, ~11%. Toda análise temporal e de autoria herda essa limitação.

**Próximo passo:** com a população definida, o notebook 02 mede o crescimento e a autoria.""",
],
"02_rq1_adoption_and_authorship.ipynb": [
"""md:# 2. RQ1: Adoção e autoria por agentes

**Pergunta:** o formato está se espalhando? E quem escreve as skills: pessoas ou os próprios agentes de IA?

**Por que importa:** se boa parte das instruções que os agentes seguem foi escrita por agentes, o ecossistema se retroalimenta, e ninguém revisa um texto que nenhuma pessoa escreveu inteiramente.

**Como medimos:** (1) contamos novas skills por mês desde o lançamento (out/2025); (2) olhamos o primeiro commit de cada skill: se ele tem um trailer `Co-authored-by: Claude` (ou Cursor, Copilot…) ou foi feito por uma conta bot, contamos como escrita por assistente. A margem de erro é o intervalo de confiança de Wilson a 95%.

---

### English summary

**Methodology step 3: quantitative descriptive analysis.**

* RQ1.1 How fast did the format spread after October 2025?
* RQ1.2 What share of skills were first committed with an AI assistant credited as co-author (a `Co-authored-by` trailer) or by a bot account?

Proportions are reported with 95% Wilson confidence intervals.""",
SETUP + "\nfrom statsmodels.stats.proportion import proportion_confint",
"""skills = clean.strict(clean.load_skills())
cov = adoption.history_coverage(skills)
complete = cov.loc[cov["share"] >= 0.9, "location_class"].tolist()
print("location classes with complete history:", complete)""",
"""md:## 2.1 Novas skills por mês
**Objetivo:** medir o ritmo de adoção. Usamos só `canonical`, o único local com histórico completo (notebook 01, §1.5); misturar locais amostrados distorceria a curva.""",
"""std = skills[skills["location_class"].isin(complete)]
cohorts = adoption.monthly_cohorts(std)
ax = cohorts.set_index("first_month")["new_skills"].plot(marker=".", figsize=(6, 2.6))
ax.set_ylabel("new distinct skills"); plt.show()
cohorts""",
"""md:**O que os dados mostram:** de **953** novas skills em out/2025 para **45.672** em jun/2026, cerca de **48 vezes** em oito meses. O crescimento acelera até mar/2026 e depois se estabiliza em ~40–45 mil por mês. Julho cai porque o snapshot foi coletado no meio do mês, não por queda de adoção.""",
"""md:## 2.2 Autoria por assistente
**Objetivo:** estimar que fração das skills foi criada com um agente de IA registrado como coautor.""",
"""h = skills[skills["has_history"]].copy()
h["ai_first"] = h["first_commit_ai"].notna() | h["first_commit_bot"]
k, n = int(h["ai_first"].sum()), len(h)
lo, hi = proportion_confint(k, n, method="wilson")
print(f"first commit by an assistant or bot: {k:,}/{n:,} = {k/n:.1%} (95% CI {lo:.1%}-{hi:.1%})")""",
"""md:**O que os dados mostram:** **31,9%** (IC 95%: 31,8–32,1%) das skills com histórico nasceram em um commit assinado por um assistente ou bot. **Cerca de uma em cada três skills foi escrita com um agente.**""",
"""h["first_commit_ai"].value_counts().rename("skills").to_frame()""",
"""md:**O que os dados mostram:** o Claude responde por **95%** desses casos (116.609), seguido de longe por Cursor (3.311) e Copilot (2.435). Isso reflete tanto a origem do formato (Claude Code) quanto o fato de o Claude adicionar o trailer por padrão; outras ferramentas podem estar sub-representadas.""",
"""by_month = h.groupby("first_month")["ai_first"].agg(skills="size", share="mean")
ax = by_month["share"].plot(marker=".", figsize=(6, 2.6)); ax.set_ylabel("share assistant-authored"); plt.show()
by_month""",
"""md:**O que os dados mostram:** a fração fica entre **29% e 40%** em todos os meses, sem tendência clara de queda ou alta. A autoria por agentes não é uma fase inicial: acompanha o crescimento do ecossistema.

## Conclusão da RQ1
* O ecossistema cresceu cerca de **48×** em oito meses.
* **Cerca de 1 em cada 3** skills foi criada com um agente como coautor, quase sempre o Claude, e essa fração é estável no tempo.

**Limitações:** é um **limite inferior** (só conta quem manteve o trailer `Co-authored-by`); vale para as 396.247 skills com histórico, concentradas em `.claude/skills/`.

**Próximo passo:** se as skills são criadas tão rápido, de onde vêm? O notebook 03 mostra que boa parte vem de cópia.""",
],
"03_rq3_reuse.ipynb": [
"""md:# 3. RQ3: Reuso sem gerenciador de pacotes

**Pergunta:** como as skills se espalham, se não há registro central nem gerenciador de pacotes?

**Por que importa:** em npm ou PyPI, quando um pacote é corrigido, quem depende dele pode atualizar. Uma skill copiada é um arquivo solto: a correção na origem **não chega** às cópias. Quanto mais concentrado e espalhado o reuso, maior o efeito de uma skill problemática.

**Como medimos:** (1) concentração das cópias (coeficiente de Gini, fatia do 1% mais copiado); (2) se as cópias atravessam donos diferentes; (3) famílias de variantes (cópias editadas), base da análise de deriva do notebook 04.

---

### English summary

**Methodology step 3: quantitative analysis.**

* RQ3.1 How concentrated is reuse? Gini coefficient and share of occurrences held by the top 1% of skills.
* RQ3.2 Does copying cross owners (ecosystem reuse) or stay within one owner?
* RQ3.3 How many edited variants do popular skills have? Families are grouped by normalised skill name (baseline); `reuse.minhash_families` groups by content similarity.""",
SETUP,
"""skills = clean.load_skills()
strict = clean.strict(skills)""",
"""md:## 3.1 Concentração do reuso
**Objetivo:** saber se o reuso é espalhado (todos copiam um pouco de tudo) ou concentrado em poucos "templates". Gini vai de 0 (todas as skills igualmente copiadas) a 1 (uma única skill concentra todas as cópias).""",
"""conc = pd.DataFrame([{"population": "all", **reuse.concentration(skills["copies"])},
                     {"population": "strict", **reuse.concentration(strict["copies"])}])
save_table(conc, "rq3_concentration")
conc.T""",
"""md:**O que os dados mostram (coluna strict):**
* **79,6%** dos textos aparecem uma única vez (`share_singletons`);
* mesmo assim, **52,5%** de todas as ocorrências são cópias (`share_occ_duplicated`);
* o **1%** de textos mais copiados responde por **27%** de todas as ocorrências (`top1pct_share_of_occ`); Gini = **0,49**.

Leitura: duas populações convivem, uma cauda longa de skills únicas e um núcleo pequeno de skills copiadas em massa.""",
"""md:## 3.2 Reuso entre donos diferentes
**Objetivo:** distinguir duplicação interna (uma pessoa copiando entre os próprios repositórios) de reuso de ecossistema (pessoas copiando umas das outras). O dono é a conta ou organização do GitHub.""",
"""dup = strict[strict["copies"] > 1]
print(f"copied skills: {len(dup):,}; spread across >1 owner: {(dup.n_owners > 1).mean():.1%}")
strict.nlargest(15, "copies")[["name", "copies", "n_repos", "n_owners", "location_class", "has_scripts"]]""",
"""md:**O que os dados mostram:** das 328.391 skills com mais de uma cópia, **65,6%** aparecem em mais de um dono: o reuso é majoritariamente **entre pessoas**. As mais copiadas são skills de uso geral, publicadas em coleções conhecidas (`pdf` com 1.409 cópias em 612 donos, `frontend-design`, `webapp-testing`, `test-driven-development`), e várias trazem scripts executáveis (`has_scripts = 1`). Exceção: `skill-creator` tem 1.074 cópias em só 27 donos, um caso de duplicação interna.""",
"""md:## 3.3 Famílias de variantes
**Objetivo:** encontrar **cópias editadas** (variantes) da mesma skill. Elas são a base do notebook 04: comparamos cada variante com a versão mais copiada da família para ver o que mudou.

**Como:** skills distintas com o mesmo `name` normalizado (minúsculas; símbolos viram hífen) formam uma família, desde que tenham pelo menos 2 textos diferentes. Detalhes técnicos em `docs/familias_de_variantes.md`.""",
"""fam = reuse.name_families(strict)
sizes = fam.groupby("family").agg(variants=("file_sha", "nunique"), occurrences=("copies", "sum"))
print(f"{len(sizes):,} families with >=2 variants, covering {sizes.variants.sum():,} skills")
sizes.sort_values("variants", ascending=False).head(15)""",
"""md:### Funil: da população estrita às famílias
**Objetivo:** mostrar o que acontece com **todas** as skills da população estrita, e não só com as que formam família. Só a análise de deriva (notebook 04) usa o subconjunto das famílias; concentração, reuso entre donos e prevalência de riscos usam a população estrita inteira.""",
"""norm = strict["name"].map(reuse.normalize_name)
named = strict[norm.notna()].assign(family=norm[norm.notna()])
n_texts = named.groupby("family")["file_sha"].transform("nunique")
solo = named[n_texts == 1]
in_fam = named[n_texts >= 2]
funnel = pd.DataFrame([
    ("strict population (notebook 01)", len(strict), int(strict["copies"].sum())),
    ("  name unusable after normalisation (non-Latin only)", int(norm.isna().sum()), int(strict.loc[norm.isna(), "copies"].sum())),
    ("  unique name: no other text shares it", len(solo), int(solo["copies"].sum())),
    ("      of which: never copied", int((solo["copies"] == 1).sum()), int(solo.loc[solo["copies"] == 1, "copies"].sum())),
    ("      of which: only identical copies", int((solo["copies"] > 1).sum()), int(solo.loc[solo["copies"] > 1, "copies"].sum())),
    ("  shared name with >= 2 texts (in families)", len(in_fam), int(in_fam["copies"].sum())),
    ("      families", in_fam["family"].nunique(), None),
    ("      variants compared in notebook 04 (minus 1 reference per family)", len(in_fam) - in_fam["family"].nunique(), None),
], columns=["group", "skills", "files (occurrences)"])
funnel["% of strict"] = (100 * funnel["skills"] / len(strict)).round(1)
funnel.loc[funnel["group"].str.contains("families$|variants compared"), "% of strict"] = None
funnel""",
"""md:**O que os dados mostram:** das 1.610.839 skills da população estrita:
* **949.755 (59%)** compartilham o nome com pelo menos um texto diferente e formam **161.043 famílias**. Tirando uma referência por família, sobram as **788.712 variantes** comparadas no notebook 04.
* **657.807 (41%)** têm **nome único**: nenhuma outra skill usa o mesmo nome, então não há variante com que comparar. A maioria (563.108) nunca foi copiada; **94.699** foram copiadas só de forma **idêntica**, sem nenhuma versão editada.
* **3.277 (0,2%)** têm nome só com caracteres não latinos (por exemplo `会议准备`) e ficam fora das famílias por causa da normalização. É um viés de idioma, registrado como limitação.

Essas skills não se perdem: continuam nas métricas de concentração (§3.1), reuso entre donos (§3.2) e prevalência de riscos (notebook 04, §4.1). Só não entram na análise de deriva.

**Sobre as famílias:** **161.043** famílias reúnem **949.755** skills, ou seja, **59%** da população estrita tem pelo menos uma "irmã" com o mesmo nome e texto diferente. Algumas famílias são claramente cópias editadas de skills conhecidas (`skill-creator`, `frontend-design`, `systematic-debugging`). Outras são **nomes genéricos** (`commit`, `review`, `release`, `plan`, `setup`) que juntam skills escritas do zero por pessoas diferentes.

**Atenção:** esse segundo grupo é uma limitação do método por nome. Ele trata skills independentes como variantes e tende a **inflar a deriva** medida no notebook 04. O agrupamento por similaridade de texto (`reuse.minhash_families`) corrige isso e está planejado como teste de robustez.

## Conclusão da RQ3
* O reuso é **concentrado**: 1% dos textos responde por 27% das ocorrências.
* O reuso é **de ecossistema**: 65,6% das skills copiadas atravessam donos.
* Mais da metade das skills tem variantes, e é aí que mudanças (inclusive de segurança) podem entrar sem revisão.

**Próximo passo:** o notebook 04 pergunta se essas variantes mudam o que o agente pode fazer.""",
],
"04_rq5_security_capabilities.ipynb": [
"""md:# 4. RQ5: Capacidades sensíveis à segurança e sua deriva nas cópias

**Pergunta:** as skills mandam o agente fazer coisas perigosas? E, quando uma skill é copiada e editada, a cópia fica mais perigosa?

**Por que importa:** o agente executa o que a skill manda, com as permissões do usuário. Uma cópia editada que acrescenta `curl … | sh` ou `--dangerously-skip-permissions` é o equivalente, sem registro e sem revisão, a um pacote adulterado na cadeia de suprimentos.

**Como medimos:** 9 categorias de capacidade detectadas por expressões regulares no texto, cada uma com nível de gravidade e a CWE mais próxima. (1) prevalência; (2) deriva: o que cada variante acrescenta ou remove em relação à versão mais copiada da família, com teste de McNemar; (3) regressão logística para ver que tipo de variante acrescenta capacidades.

**Importante:** medimos **capacidade** (potencial de dano), não vulnerabilidade nem ataque confirmado.

---

### English summary

**What we measure.** Not vulnerabilities and not attacks, but *security-sensitive capabilities*: instructions that give the agent the power to cause harm if the skill were malicious, tampered with in a copy, or misused. Each capability maps to the closest CWE weakness class and a severity tier.

**Methodology step 3: quantitative + statistical modelling.**

* RQ5.1 Prevalence of each capability, also weighted by copies (exposure).
* RQ5.2 Drift: within each variant family, which capabilities an edited copy **adds** or **removes** relative to the most-copied member. Additions vs removals are tested with an exact McNemar test.
* RQ5.3 Logistic regression: which variants add capabilities?

**Methodology step 4 (validation)** happens in notebook 05: manual labelling to measure detector precision.""",
SETUP + "\nfrom scipy.stats import binomtest\nfrom statsmodels.stats.proportion import proportion_confint\nimport statsmodels.formula.api as smf",
"""skills = clean.strict(clean.load_skills())
risk_cols = [c for c in skills.columns if c.startswith("risk_")]
pd.DataFrame({"capability": [c[5:] for c in risk_cols],
              "severity": [patterns.RISK_SEVERITY[c[5:]] for c in risk_cols],
              "closest CWE": [patterns.RISK_CWE[c[5:]] for c in risk_cols]})""",
"""md:A tabela acima é o "dicionário" da RQ5: cada capacidade, sua gravidade (alta, média, baixa) e a classe de fraqueza CWE mais próxima. Os padrões exatos estão em `src/gitskills/patterns.py`.""",
"""md:## 4.1 Prevalência e exposição
**Objetivo:** saber quão comum é cada capacidade. `share_of_skills` conta cada texto uma vez; `share_of_occurrences` pondera pelo número de cópias, ou seja, quantas instalações carregam a capacidade (exposição).""",
"""prev = pd.DataFrame({
    "severity": [patterns.RISK_SEVERITY[c[5:]] for c in risk_cols],
    "share_of_skills": skills[risk_cols].mean().values,
    "share_of_occurrences": (skills[risk_cols].mul(skills["copies"], axis=0).sum() / skills["copies"].sum()).values,
}, index=[c[5:] for c in risk_cols]).sort_values(["severity", "share_of_skills"], ascending=[True, False])
save_table(prev.reset_index(names="capability"), "rq5_risk_prevalence")
high = [c for c in risk_cols if patterns.RISK_SEVERITY[c[5:]] == "high"]
print(f"skills with >=1 high-severity capability: {skills[high].any(axis=1).mean():.1%}")
prev""",
"""md:**O que os dados mostram:**
* **6,4%** das skills têm pelo menos uma capacidade de **gravidade alta**. A mais comum é a execução dinâmica (4,4%); `curl | sh` e desligar confirmações aparecem em 0,7% cada.
* As mais frequentes no geral são de gravidade média: mencionar segredos (**17,6%**) e instalar pacotes (**11,9%**).
* A exposição (por cópias) é um pouco **maior** que a prevalência em várias categorias (instalar pacotes: 11,9% → 15,0%): skills com essas capacidades tendem a ser mais copiadas.

**Cuidado: estes números são detecções, não instruções confirmadas.** A validação do notebook 05 (pré-rotulagem de 12 trechos por categoria, ainda sem o segundo avaliador) mostra precisões muito diferentes entre categorias:

| Capacidade | Detectado | Precisão | Prevalência ajustada |
|---|---|---|---|
| `curl \\| sh` | 0,7% | 1,00 | **0,7%** |
| instalar pacotes | 11,9% | 0,83 | **~10%** |
| apagar arquivos | 1,1% | 0,83 | ~0,9% |
| privilégio | 2,1% | 0,75 | ~1,6% |
| segredos | 17,6% | 0,17 | ~3% |
| execução dinâmica | 4,4% | 0,08 | ~0,4% |
| desligar confirmações | 0,7% | 0,33 | ~0,2% |

Os detectores de `curl | sh`, instalação de pacotes, apagar arquivos e privilégio são confiáveis. Os de segredos, execução dinâmica e desligar confirmações disparam sobretudo em **menções** ("never store credentials", "never use `--no-verify`") ou em outro sentido da palavra ("eval" de *evaluation*). Com a precisão descontada, a fração de skills com alguma capacidade de gravidade alta cai de 6,4% para **no máximo ~2%**.""",
"""md:## 4.2 Deriva nas cópias editadas
**Objetivo:** a pergunta central. Em cada família, a referência é a variante mais copiada (proxy da original, que a base não identifica). Para cada outra variante, marcamos que capacidades ela **acrescentou** e quais **removeu**.

**Teste de McNemar:** se as edições fossem aleatórias em relação ao risco, acrescentar e remover seriam igualmente prováveis (50/50). Um p pequeno indica que um dos lados predomina.""",
"""fam = reuse.name_families(skills)
drift = reuse.variant_drift(fam, risk_cols)
k, n = int(drift["any_added"].sum()), len(drift)
lo, hi = proportion_confint(k, n, method="wilson")
print(f"variants adding >=1 capability: {k:,}/{n:,} = {k/n:.1%} (95% CI {lo:.1%}-{hi:.1%})")
rows = []
for c in risk_cols:
    a, r = int(drift[f"added_{c}"].sum()), int(drift[f"removed_{c}"].sum())
    rows.append({"capability": c[5:], "severity": patterns.RISK_SEVERITY[c[5:]], "added": a, "removed": r,
                 "mcnemar_p": binomtest(a, a + r, 0.5).pvalue if a + r else np.nan})
mc = pd.DataFrame(rows)
save_table(mc, "rq5_mcnemar_added_vs_removed")
mc""",
"""md:**O que os dados mostram:**
* **17,3%** das 788.712 variantes (IC 95%: 17,2–17,3%) acrescentam pelo menos uma capacidade que a referência não tinha.
* Mas a deriva vai **nos dois sentidos**. Na maioria das categorias as edições **mais removem do que acrescentam** (instalar pacotes: 40.320 acréscimos × 51.713 remoções; segredos: 57.422 × 65.252; desligar confirmações: 4.477 × 5.527).
* **A exceção confiável é `curl | sh`:** baixar um script e executá-lo direto é acrescentado mais vezes do que removido (3.429 × 3.175, p = 0,002), e o detector teve precisão de 12/12 na validação.
* A execução dinâmica também aparece como "mais acrescentada" (19.016 × 15.605), mas **não deve ser interpretada**: o detector acerta só 1 em 12, porque a palavra "eval" quase sempre significa *evaluation* (avaliação de modelos). O efeito provavelmente reflete skills que passaram a falar de avaliação.
* Nas categorias de baixa precisão (segredos, desligar confirmações), parte das "remoções" pode ser só uma **regra** do tipo "nunca use `--no-verify`" que sumiu do texto.

Leitura: copiar e editar **não** torna as skills mais perigosas de forma geral; as cópias tendem a ser enxugadas. A forma mais direta de executar código remoto, `curl | sh`, é a que se acumula.""",
"""md:## 4.3 Que variantes acrescentam capacidades? (regressão logística)
**Objetivo:** ir além da média e ver **que características** se associam a uma variante acrescentar capacidade.

**Resposta (0/1):** a variante acrescenta pelo menos uma capacidade. **Preditores:** popularidade da referência (log de cópias), tamanho da família, se a variante é copiada entre donos, se traz scripts, se foi escrita com assistente.

**Como ler a razão de chances (odds ratio, OR):** OR = 1 não muda nada; OR = 1,46 aumenta a chance em 46%; OR = 0,69 reduz em 31%.""",
"""d = drift.join(skills.set_index("file_sha")[["n_owners", "has_scripts", "first_commit_ai"]], on="file_sha")
d["family_size"] = d.groupby("family")["file_sha"].transform("size") + 1
d = d.assign(added=d["any_added"].astype(int), log_ref_copies=np.log1p(d["ref_copies"]),
             log_family_size=np.log(d["family_size"]), cross_owner=(d["n_owners"] > 1).astype(int),
             has_scripts=d["has_scripts"].fillna(0).astype(int), ai_authored=d["first_commit_ai"].notna().astype(int))
model = smf.logit("added ~ log_ref_copies + log_family_size + cross_owner + has_scripts + ai_authored", data=d).fit(disp=False)
odds = pd.DataFrame({"odds_ratio": np.exp(model.params), "ci_low": np.exp(model.conf_int()[0]),
                     "ci_high": np.exp(model.conf_int()[1]), "p": model.pvalues})
save_table(odds.reset_index(names="term"), "rq5_logit_odds_ratios")
odds.round(3)""",
"""md:**O que os dados mostram:**
* **Ter scripts** aumenta a chance de acrescentar capacidade em **46%** (OR 1,46).
* **Ser escrita com assistente** aumenta em **22%** (OR 1,22).
* **Famílias maiores** acrescentam mais (OR 1,36 por unidade de log).
* Variantes de skills **muito populares** acrescentam **menos** (OR 0,69): quem copia uma skill famosa tende a mantê-la.
* Ser copiada entre donos quase não importa (OR 0,97).

**Cuidado:** com 788 mil observações tudo é estatisticamente significativo, mas o modelo explica pouco (pseudo R² = 0,03). São **associações modestas**, não previsões. E a autoria por assistente só pode ser 1 onde há histórico (quase só em `.claude/skills/`), então parte do efeito pode ser o local.

## Conclusão da RQ5
* Detectamos alguma capacidade de gravidade alta em 6,4% das skills; descontada a precisão dos detectores, são **no máximo ~2%**. A capacidade confirmada mais comum é instalar pacotes (~10%).
* **17,3%** das variantes acrescentam alguma capacidade, mas as edições, no geral, **mais removem do que acrescentam**.
* A exceção confiável é **`curl | sh`**, que cresce nas cópias. A aparente alta da execução dinâmica é um artefato do detector ("eval" = avaliação).
* Variantes com scripts ou escritas com assistente acrescentam capacidades com mais frequência.

**Limitações:** (1) a precisão vem de uma pré-rotulagem de 108 trechos feita com apoio de um modelo de linguagem, ainda sem o segundo avaliador humano; (2) os detectores de segredos, execução dinâmica e desligar confirmações precisam ser refinados antes de os números dessas categorias irem para o artigo; (3) famílias agrupadas pelo nome juntam skills sem relação; (4) a referência é um proxy da original e, em muitas famílias, tem só 1 cópia ou empata com outras.

**Próximo passo:** o notebook 05 mede quanto confiar nos detectores.""",
],
"05_validation_sample.ipynb": [
"""md:# 5. Validação: os detectores de risco são confiáveis?

**Pergunta:** quando o código diz "esta skill tem `curl | sh`" ou "esta skill lida com segredos", ele está certo?

**Por que este notebook existe:** todos os números do notebook 04 (6,4% de gravidade alta, 17,3% de variantes que acrescentam capacidade, McNemar) vêm de **expressões regulares**, que procuram palavras no texto. Uma regex não entende contexto:

| Trecho | A regex marca | Na verdade é |
|---|---|---|
| "Instale com `curl -sSL https://… \\| bash`" | pipe_to_shell | **instrução real** |
| "Nunca coloque a API key no código" | secrets | só uma **menção** (é até um conselho de segurança) |
| "o arquivo `.env.example` lista as variáveis" | secrets | menção, sem acesso a segredo |

Se a maioria das detecções de uma categoria for menção, a prevalência daquela categoria está **superestimada**. Precisamos medir a **precisão** de cada detector: de tudo que ele marcou, quanto é instrução de verdade.

**Por que uma amostra:** não dá para ler 1,6 milhão de skills à mão. Sorteamos aleatoriamente alguns trechos detectados em cada categoria, rotulamos esses à mão e usamos a proporção correta na amostra como **estimativa** da precisão do detector, com intervalo de confiança. É o procedimento padrão para validar heurísticas em estudos de mineração de repositórios.

**Etapas:** 5.1 sortear a amostra → 5.2 rotular à mão (trabalho humano, fora do notebook) → 5.3 calcular a precisão → 5.4 medir a concordância entre dois avaliadores → 5.5 ver o efeito nos números do notebook 04.

**Este notebook não está quebrado: ele está à espera da rotulagem.** Enquanto a coluna `label` do CSV estiver vazia, as seções 5.3–5.5 mostram só o status. Elas se preenchem sozinhas quando o CSV for rotulado e o notebook rodar de novo.

---

### English summary
Regular expressions detect a *mention*, not an *instruction*. We draw a stratified random sample (seed 42) of matched snippets per capability and label each by hand as `instructs`, `mentions` or `false_match`. Precision = `instructs` / labelled, reported with 95% Wilson intervals; inter-rater agreement with Cohen's kappa.""",
SETUP + "\nimport re\nfrom statsmodels.stats.proportion import proportion_confint",
"""md:## 5.1 Sortear a amostra
**Objetivo:** para cada uma das 9 categorias, sortear 12 skills em que a regex disparou (108 trechos no total) e guardar ~160 caracteres antes e depois do ponto detectado, para dar contexto a quem rotula. A semente fixa (42) faz o sorteio ser reproduzível. O arquivo só é criado se ainda não existir, para nunca apagar rótulos já feitos.""",
"""PER_CATEGORY = 12   # 9 categories x 12 = 108 snippets
skills = clean.strict(clean.load_skills())
rows = []
for cap, rx in patterns.COMPILED_RISKS.items():
    hits = skills[skills[f"risk_{cap}"].fillna(False)]
    pick = hits.sample(min(PER_CATEGORY, len(hits)), random_state=42)
    texts = db.query(f"SELECT file_sha, content FROM artifacts WHERE dedup_primary = 1 AND file_sha IN ({','.join('?' * len(pick))})",
                     tuple(pick["file_sha"]))
    for _, t in texts.iterrows():
        m = rx.search(t["content"] or "")
        if m:
            s = max(0, m.start() - 160); e = min(len(t["content"]), m.end() + 160)
            rows.append({"capability": cap, "file_sha": t["file_sha"], "snippet": t["content"][s:e].replace("\\n", " "), "label": "", "label_2": ""})
sample = pd.DataFrame(rows)
out = ROOT / "results/tables/validation_sample.csv"
if not out.exists():
    sample.to_csv(out, index=False)
print(f"{len(sample)} snippets -> {out}")
sample.groupby("capability").size().rename("snippets").to_frame()""",
"""md:## 5.2 Como rotular (trabalho manual)
Abra `results/tables/validation_sample.csv` (Excel, Numbers ou Google Sheets), leia o `snippet` de cada linha e preencha a coluna **`label`** com uma de três palavras:

* **`instructs`**: o texto manda o agente executar a ação ("rode `curl … | bash`", "leia o arquivo `.env`");
* **`mentions`**: o texto fala da ação sem mandar executar ("nunca exponha a API key", "evite `rm -rf`");
* **`false_match`**: a regex casou com outra coisa ("token" no sentido de LLM, `--force` de outra ferramenta).

**Segundo avaliador (recomendado):** outra pessoa preenche a coluna **`label_2`** de forma independente, sem ver a `label`. Isso mede se o critério é claro (5.4). Depois as divergências são discutidas e a `label` final fica com o consenso.

Salve como CSV, sem mudar os nomes das colunas, e rode o notebook de novo.""",
"""md:## 5.3 Precisão por categoria
**Objetivo:** estimar, para cada categoria, a fração de detecções que são instruções reais, com intervalo de confiança de Wilson a 95%.""",
"""VALID = {"instructs", "mentions", "false_match"}
lab = pd.read_csv(ROOT / "results/tables/validation_sample.csv", dtype=str, keep_default_na=False)
if "label_2" not in lab:
    lab["label_2"] = ""
lab["label"] = lab["label"].str.strip().str.lower()
lab["label_2"] = lab["label_2"].str.strip().str.lower()
bad = lab[(lab["label"] != "") & ~lab["label"].isin(VALID)]
done = lab[lab["label"].isin(VALID)]
print(f"labelled: {len(done)}/{len(lab)} snippets" + (f"; {len(bad)} with an unknown label: {sorted(bad['label'].unique())}" if len(bad) else ""))
if done.empty:
    print("STATUS: waiting for manual labels (see 5.2). Precision cannot be computed yet.")
    prec = None
else:
    g = done.groupby("capability")["label"]
    prec = pd.DataFrame({"labelled": g.size(), "instructs": g.apply(lambda s: int((s == "instructs").sum()))})
    prec["precision"] = prec["instructs"] / prec["labelled"]
    ci = [proportion_confint(k, n, method="wilson") for k, n in zip(prec["instructs"], prec["labelled"])]
    prec["ci_low"], prec["ci_high"] = [c[0] for c in ci], [c[1] for c in ci]
    save_table(prec.reset_index(), "validation_precision")
    display(prec.round(2))""",
"""md:**Como ler:** precisão 0,90 quer dizer que 9 em cada 10 detecções daquela categoria são instruções reais. Com 12 trechos por categoria, o intervalo de confiança é largo (cerca de ±25 pontos percentuais): serve para separar detectores bons de ruins, não para afinar a segunda casa decimal. Se uma categoria ficar abaixo de ~0,7, o número dela no notebook 04 deve ser reportado com ressalva, ou o detector deve ser refinado em `patterns.py`.""",
"""md:## 5.4 Concordância entre avaliadores (κ de Cohen)
**Objetivo:** verificar se duas pessoas, rotulando de forma independente, chegam ao mesmo rótulo. κ desconta a concordância que aconteceria por acaso: acima de 0,6 é considerado substancial, acima de 0,8 quase perfeito.""",
"""both = lab[lab["label"].isin(VALID) & lab["label_2"].isin(VALID)]
if both.empty:
    print("STATUS: no snippet has both 'label' and 'label_2' yet; kappa needs a second rater.")
else:
    cats = sorted(VALID)
    po = (both["label"] == both["label_2"]).mean()
    pe = sum((both["label"] == c).mean() * (both["label_2"] == c).mean() for c in cats)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    print(f"snippets rated twice: {len(both)}; raw agreement {po:.1%}; Cohen's kappa {kappa:.2f}")
    display(pd.crosstab(both["label"], both["label_2"]))""",
"""md:## 5.5 Efeito nos números do notebook 04
**Objetivo:** mostrar o que a precisão muda na prevalência. Prevalência ajustada ≈ prevalência detectada × precisão. Por exemplo, se 17,6% das skills disparam `secrets` e só metade das detecções é instrução real, a prevalência real de instruções que lidam com segredos é ~9%.""",
"""strict = skills
detected = pd.Series({c: strict[f"risk_{c}"].mean() for c in patterns.COMPILED_RISKS}, name="detected_share")
if prec is None:
    print("STATUS: waiting for labels; showing detected prevalence only.")
    display(detected.to_frame().round(3))
else:
    adj = detected.to_frame().join(prec[["precision", "ci_low", "ci_high"]])
    adj["adjusted_share"] = adj["detected_share"] * adj["precision"]
    adj["adjusted_low"] = adj["detected_share"] * adj["ci_low"]
    adj["adjusted_high"] = adj["detected_share"] * adj["ci_high"]
    display(adj.round(3))""",
"""md:## Conclusão do notebook 05
Este é o passo de **validação** da metodologia: transforma "a regex disparou" em uma estimativa de quanto confiar em cada número da RQ5. Sem ele, os resultados do notebook 04 devem ser lidos como **limites superiores** (detecções, não instruções confirmadas). Com ele, cada prevalência pode ser reportada com a precisão do detector e, se houver dois avaliadores, com a concordância κ.""",
],
}

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        nbf.write(nb(cells), OUT / name)
        print("wrote", OUT / name)
