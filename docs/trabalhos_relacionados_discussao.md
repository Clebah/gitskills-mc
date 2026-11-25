# Trabalhos relacionados e ferramentas: base da Discussão e do Trabalho futuro

Levantamento feito em 2026-11-24 para sustentar as implicações do artigo. Nível de confiança de cada fonte:
- **[V]**: a página do arXiv foi aberta e conferida.
- **[S]**: só trechos de busca, confirmados por mais de uma fonte.
- **[K]**: referência clássica, não reconferida.

**Antes de citar no artigo, confira os metadados de toda fonte [S] ou [K].**

## 1. Usuários e mantenedores: revisar poucos modelos populares cobre a maioria das cópias
- **Zimmermann, Staicu, Tenny, Pradel, "Small World with High Risks: A Study of Security Threats in the npm Ecosystem", USENIX Security 2019** [S]
  - No npm, poucas contas de mantenedores alcançam a maior parte dos pacotes.
  - Os autores concluem que verificar um conjunto selecionado de pacotes e mantenedores reduziria muito o risco.
- **Nagle et al., "Census II of Free and Open Source Software – Application Libraries", Linux Foundation/Harvard LISH, 2022** [S]
  - Ranqueia os pacotes mais usados para priorizar o esforço de segurança.
- **OpenSSF Criticality Score**, https://github.com/ossf/criticality_score [S]
  - Nota de 0 a 1 que indica quais projetos devem receber investimento em segurança primeiro.
- **Lopes et al., "DéjàVu: A Map of Code Duplicates on GitHub", OOPSLA 2017** [S]
  - Dos 428 milhões de arquivos analisados, só 85 milhões são únicos.
- **Baltes e Diehl, "Usage and Attribution of Stack Overflow Code Snippets in GitHub Projects", EMSE 2019, arXiv:1802.02938** [S]
  - Trechos copiados quase nunca citam a origem, ou seja, a proveniência se perde.
- **Liu et al., arXiv:2602.06547** [V]
  - Mais da metade das skills maliciosas confirmadas vem de um único ator.

## 2. Plataformas e ferramentas
**(a) Proveniência**
- **SLSA** (slsa.dev) [K]
- **Sigstore** (Newman et al., CCS 2022) [K]
- **in-toto** (Torres-Arias et al., USENIX Security 2019) [K]
- **CycloneDX ML-BOM e perfis de IA do SPDX 3.0** [S]
  - Nenhum deles cobre `SKILL.md`.
- **Plugins do Claude Code** [S]
  - A documentação avisa que um plugin roda código com os privilégios do usuário.
  - Não encontrei assinatura nativa; um projeto de terceiros acrescenta proveniência SLSA e SBOM.
  - **Confirmar na documentação antes de afirmar no artigo.**
- **Hereiz, Lyu, Li, Adams, Hassan, "On the Maintenance and Co-evolution of Agent Plugins: An Empirical Study of Claude Code Plugin Marketplaces", arXiv:2608.28497, 2026** [V]
  - Estudo de 8.351 plugins: o Claude é coautor de 34,9% dos commits, o que corrobora o nosso "1 em 3".
  - É o vizinho MSR mais próximo do nosso estudo.

**(b) Scanners**
- **Cisco AI Defense skill-scanner**, github.com/cisco-ai-defense/skill-scanner [S]
  - Combina análise estática, de fluxo de dados e por LLM; gera saída SARIF.
- **Snyk Agent Scan** (antigo mcp-scan, da Invariant Labs), github.com/snyk/agent-scan [S]
  - Analisa servidores MCP e, com a opção `--skills`, também skills.
- **Regra do Semgrep `bash.curl.security.curl-pipe-bash.curl-pipe-bash`** [S]
  - Detecta `curl | bash` e variantes.
  - O projeto CHAINS (KTH) aponta lacunas da regra e mostra um hook do Claude Code que roda o Semgrep.

**(c) Distinguir instrução de proibição**
- **Chapman et al., NegEx, *J. Biomed. Informatics* 34(5), 2001** [S]
  - Detecta negações a partir de palavras-gatilho numa janela curta de texto.
- **Yang et al., "SkillGate: Cost Efficient Runtime Malicious Skill File Detection in Coding Agents", arXiv:2607.25619, 2026** [V]
  - Usa regex como filtro inicial e depois um LLM como juiz; F1 de 0,817.
- **Truong-Le et al., "The Devil Wears Markdown…", arXiv:2611.10830, 2026** [V]
  - Em 60 skills benignas, o Cisco skill-scanner gerou 33 a 40 falsos positivos, contra 5 do pipeline híbrido dos autores.
- **Wang et al., "When Safe Skills Collide", arXiv:2606.00448, 2026** [V]
  - Só cerca de 18% dos candidatos sinalizados pela análise estática foram confirmados por humanos.
- **Llama Prompt Guard 2** [S]
  - Detecta ataques de injeção, não intenção de segurança; **não resolve** o nosso problema.

## 3. Pesquisadores
- **Famílias por similaridade**
  - SourcererCC (Sajnani et al., ICSE 2016) [K]
  - MinHash (Broder, 1997) [K]
  - Allamanis, Onward! 2019 [S]: duplicatas distorcem resultados.
- **Segurança de código escrito por IA**
  - Pearce et al., S&P 2022 [S]: cerca de 40% dos programas gerados pelo Copilot eram vulneráveis.
  - Perry et al., CCS 2023 [S]
  - Fu et al., TOSEM 2025 [S]: 29,5% dos trechos Python e 24,2% dos JavaScript gerados pelo Copilot e encontrados no GitHub tinham fraquezas CWE.
- **Rastros de coautoria por IA**
  - "Agentic Much?", arXiv:2601.18341 [S]
  - AIDev, arXiv:2602.09185 [S]

## 4. Trabalho futuro: ligar capacidades a vulnerabilidades
- **Estudos anteriores de segurança de skills**
  - Liu et al. 2601.10338 (SkillScan) [V]: 26,1% de 31.132 skills vulneráveis; skills com scripts têm 2,12× mais chance de serem vulneráveis.
  - Liu et al. 2602.06547 [V]: 157 skills maliciosas confirmadas.
  - Saha et al. 2605.11418 [V]
  - Hasan et al. 2506.13538 [S]
  - Gao et al. 2611.03772 (RuntimeTickets) [V]
  - **Nenhum desses trabalhos liga as capacidades a identificadores CWE, CVE, OSV ou GHSA**, pelo que diz o resumo de cada um.
- **CVEs em ferramentas de agentes** [S]. Cada um tem CWE atribuída, o que serve de modelo para o mapeamento:
  - **CVE-2025-54795** (Claude Code < 1.0.20): injeção de comando que contorna a confirmação; CWE-78.
  - **CVE-2025-54135** (Cursor, "CurXecute"): injeção de prompt que leva a execução de código.
  - **CVE-2025-53773** (GitHub Copilot): injeção de prompt que leva a execução remota de código; CWE-77.
  - **CVE-2025-6514** (mcp-remote): injeção de comando no sistema operacional; CWE-78; CVSS 9,6.
- **Taxonomias**
  - OWASP Top 10 for LLM Applications 2025 [K]
  - OWASP Top 10 for Agentic Applications 2026 [S], que introduz o princípio de "least agency"
  - MITRE ATLAS [K]
  - OSV / GitHub Advisory Database [K]
