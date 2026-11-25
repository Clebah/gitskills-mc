# Agent Skills as an Informal Supply Chain: Reuse and Security Drift on GitHub

*Cleber Santana Souza*

*Institute of Informatics, Federal University of Rio Grande do Sul (UFRGS), Porto Alegre, Brazil*

*Paper summary (abstract and introduction) — MSR 2027 Mining Challenge*

## Abstract

Agent skills are natural-language instructions, often bundled with scripts, that coding agents built on large language models follow with their users' permissions. Skills spread by copying files between repositories rather than through a package registry, so an edited copy can silently change what an agent is told. This study characterizes this informal supply chain and asks whether edited copies change the security-sensitive capabilities that skills grant to agents. We analyze 3.8 million skill files from 282,200 public GitHub repositories, measuring authorship, reuse concentration, and capability drift. Distinctively, we track drift across copies: we group edited copies sharing a skill name into variant families, compare each variant with its family's most-copied version, and validate the capability detectors on a labelled sample. Reuse is concentrated: 1% of skill contents account for 27% of all copies, two thirds of copied skills cross repository owners, and one in three skills is first committed with an artificial intelligence assistant as co-author. Copying does not make skills riskier overall: edits remove most capability types more often than they add. The exception is piping a downloaded script directly into a shell, the most reliably detected capability, which is added more often than removed. Validation also shows that keyword detection overestimates capabilities such as credential handling, which skills often mention only to forbid. These results imply that reviewing every copied skill is unnecessary: provenance tracking and checks focused on remote code execution would address the risk that does accumulate, and detectors must distinguish instructions from prohibitions.

**Keywords:** agent skills; large language model (LLM) coding agents; software reuse; software supply chain security; mining software repositories (MSR)

---

## I. Introduction

Coding agents built on large language models (LLMs) now read, write and execute code on developers' machines. To extend what these agents can do, a growing number of projects ship *agent skills*: folders containing a `SKILL.md` file whose YAML front matter names and describes the skill, and whose body tells the agent, in natural language, how to perform a task, often with bundled scripts and reference files [1]. When a task matches the description, the agent loads the instructions and follows them with the permissions of its user. A skill is therefore not documentation: it is executable intent.

Skills are distributed in an unusual way. Unlike libraries, which reach users through package registries such as npm or PyPI, skills spread by *copying files* between repositories. There is no registry, no version resolution and no update channel: when the author of a popular skill fixes a problem, the copies already made do not change, and when someone edits a copy, nobody reviews the edit. Software engineering research has shown, in other settings, that this kind of informal reuse propagates problems. Insecure snippets copied from Stack Overflow reached Android applications [2] and thousands of GitHub projects [3]; vulnerabilities in Docker base images are inherited by the images built on them [4]; and even with registries, vulnerable and malicious packages reach large parts of the npm ecosystem through dependencies [5]–[7]. Agent skills add a further risk: their content is read by an agent that can act on it, which makes them a channel for the indirect prompt injection attacks described for LLM-integrated applications [8].

Recent studies have started to examine the security of agent skills. Liu et al. analyzed tens of thousands of skills and reported security vulnerabilities in a substantial share of them [9], and later detected and characterized malicious skills in the wild [10]. Saha et al. studied semantic supply-chain attacks on skill registries [11], and Hasan et al. studied the security and maintainability of Model Context Protocol servers, a neighbouring extension mechanism for agents [12]. These studies analyze skills, or servers, *individually*. They do not follow what happens to a skill *as it is copied and edited* across the ecosystem, which is precisely where an informal supply chain differs from a registry. The GitSkills dataset [13], which preserves every copy of every `SKILL.md` file found on GitHub and is provided by the MSR 2027 Mining Challenge [15], makes this question answerable at scale. This paper responds to that challenge's call for mining challenge papers.

This study characterizes agent skills as an informal supply chain and asks whether edited copies change the security-sensitive capabilities that skills grant to agents. We address three research questions:

- **RQ1 (Adoption and authorship).** How fast has the skill format spread, and what share of skills is created with an AI assistant as co-author?
- **RQ2 (Reuse).** How concentrated is the reuse of skills, and does copying cross repository owners?
- **RQ3 (Security drift).** How prevalent are instructions that grant agents security-sensitive capabilities, and do edited copies add or remove these capabilities relative to the most-copied version of the skill?

RQ1 and RQ2 describe the supply chain: who produces skills and how they travel. RQ3, the focus of the paper, asks what travels with them. The study makes three contributions: (i) a method to measure *capability drift* across copies, based on variant families, an explicit reference version, and a paired test of additions against removals; (ii) a validation of keyword-based capability detectors on a labelled sample, showing which detectors can be trusted; and (iii) an ecosystem-scale baseline of skill reuse and authorship on GitHub. All scripts, notebooks and labels are available in a replication package [14].

---

## References

[1] Agent Skills Specification. https://agentskills.io (accessed Nov. 2026).

[2] F. Fischer, K. Böttinger, H. Xiao, C. Stransky, Y. Acar, M. Backes, and S. Fahl, "Stack Overflow considered harmful? The impact of copy&paste on Android application security," in *Proc. IEEE Symposium on Security and Privacy (S&P)*, 2017.

[3] M. Verdi, A. Sami, J. Akhondali, F. Khomh, G. Uddin, and A. Karami Motlagh, "An empirical study of C++ vulnerabilities in crowd-sourced code examples," arXiv:1910.01321, 2019.

[4] M. U. Haque and M. A. Babar, "Well begun is half done: An empirical study of exploitability & impact of base-image vulnerabilities," arXiv:2112.12597, 2021.

[5] A. Decan, T. Mens, and E. Constantinou, "On the impact of security vulnerabilities in the npm package dependency network," in *Proc. 15th International Conference on Mining Software Repositories (MSR)*, 2018.

[6] M. Zimmermann, C.-A. Staicu, C. Tenny, and M. Pradel, "Small world with high risks: A study of security threats in the npm ecosystem," in *Proc. 28th USENIX Security Symposium*, 2019.

[7] P. Ladisa, H. Plate, M. Martinez, and O. Barais, "SoK: Taxonomy of attacks on open-source software supply chains," in *Proc. IEEE Symposium on Security and Privacy (S&P)*, 2023.

[8] K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, "Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection," in *Proc. 16th ACM Workshop on Artificial Intelligence and Security (AISec)*, 2023.

[9] Y. Liu, W. Wang, R. Feng, Y. Zhang, G. Xu, G. Deng, Y. Li, and L. Zhang, "Agent skills in the wild: An empirical study of security vulnerabilities at scale," arXiv:2601.10338, 2026.

[10] Y. Liu, Z. Chen, Y. Zhang, G. Deng, Y. Li, J. Ning, and L. Y. Zhang, "'Do not mention this to the user': Detecting and understanding malicious agent skills in the wild," arXiv:2602.06547, 2026.

[11] S. Saha, K. Faghih, and S. Feizi, "Under the hood of SKILL.md: Semantic supply-chain attacks on AI agent skill registry," arXiv:2605.11418, 2026.

[12] M. M. Hasan, H. Li, E. Fallahzadeh, G. K. Rajbahadur, B. Adams, and A. E. Hassan, "Model Context Protocol (MCP) at first glance: Studying the security and maintainability of MCP servers," arXiv:2506.13538, 2025.

[13] G. Destefanis, D. Graziotin, M. Vaccargiu, and M. Ortu, "GitSkills: A dataset of agent skills on GitHub," arXiv:2608.10906, 2026. https://arxiv.org/abs/2608.10906. Dataset: Zenodo, doi:10.5281/zenodo.21875637.

[14] Replication package (anonymized for review). https://anonymous.4open.science/ — **[TBD: link]**.

[15] MSR 2027 Mining Challenge, "Call for mining challenge papers," 24th International Conference on Mining Software Repositories (MSR 2027), co-located with ICSE 2027, Dublin, Ireland. https://2027.msrconf.org/track/msr-2027-mining-challenge (accessed Nov. 2026).
