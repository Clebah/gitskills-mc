"""Regular-expression vocabularies used by the feature extractors.

Keep them here, versioned, so the paper can list them in the replication
package. Each list is a starting point to refine by manual inspection of
samples (report precision on a labelled sample in the paper).
"""

from __future__ import annotations

import re

# --- Agent tools named in skill text (RQ2: vendor-neutral vs tool-specific) ---
AGENT_TOOLS: dict[str, str] = {
    "claude": r"\bclaude(?:[ -]code)?\b|\.claude/",
    "codex": r"\bcodex\b|\.codex/",
    "cursor": r"\bcursor\b|\.cursor/",
    "copilot": r"\bcopilot\b|\.github/copilot",
    "gemini": r"\bgemini(?:[ -]cli)?\b|\.gemini/",
    "windsurf": r"\bwindsurf\b",
    "opencode": r"\bopencode\b|\.opencode/",
    "cline": r"\bcline\b",
    "kiro": r"\bkiro\b",
    "amp": r"\bampcode\b|\bsourcegraph amp\b",
    "goose": r"\bgoose\b",
}

# --- Co-authored-by trailers that name AI assistants (RQ1d: machine authorship) ---
AI_TRAILER = re.compile(
    r"co-authored-by:\s*(claude|cursor|copilot|codex|gemini|chatgpt|openai|"
    r"windsurf|devin|aider|cline|kiro|amp|opencode|jules)",
    re.IGNORECASE,
)

# --- Trigger phrases in descriptions (RQ4c: description quality) ---
TRIGGER_PHRASES = re.compile(
    r"\b(use (this )?(skill )?(when|whenever|for|to)|when (the )?user|triggers? (on|when)|"
    r"invoke (when|for)|activate (when|for))\b",
    re.IGNORECASE,
)

# --- Directive strength in instructions ---
DIRECTIVES = re.compile(r"\b(MUST|NEVER|ALWAYS|DO NOT|IMPORTANT|CRITICAL|REQUIRED)\b")

# --- Capabilities with security relevance (RQ5) ---
RISK_PATTERNS: dict[str, str] = {
    "pipe_to_shell": r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b",
    "remote_fetch": r"\b(curl|wget|Invoke-WebRequest|iwr)\b|requests\.(get|post)|fetch\(",
    "destructive_fs": r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*r|\bmkfs\b|\bdd\s+if=",
    "privilege": r"\bsudo\b|\bchmod\s+(\+x|777|[0-7]{3})\b|\bchown\b",
    "dynamic_exec": r"\beval\b|\bexec\(|base64\s+(-d|--decode)|\bsubprocess\b|os\.system",
    "package_install": r"\b(pip|pip3|uv)\s+install\b|\bnpm\s+(i|install)\b|\bnpx\b|\bbrew\s+install\b|\bapt(-get)?\s+install\b",
    # "token" alone is avoided on purpose: in skills it usually means LLM tokens.
    "secrets": r"\b(api[_-]?keys?|secret[_-]?keys?|access[_-]?tokens?|auth[_-]?tokens?|passwords?|credentials)\b|\.env\b|~/\.ssh|\.aws/credentials",
    "git_push": r"\bgit\s+push\b|--force\b",
    "safety_bypass": r"--dangerously-skip-permissions|--no-verify|--yolo\b|bypass(ing)? (the )?(permission|safety|approval)",
}

URL = re.compile(r"https?://[^\s)>\]\"'`]+")
CODE_FENCE = re.compile(r"^```\s*([\w+-]*)", re.MULTILINE)
HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s", re.MULTILINE)

# Spec: lowercase letters, digits, hyphens; at most 64 characters.
SPEC_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Front-matter keys defined by the open specification (agentskills.io).
SPEC_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}

SCRIPT_EXTENSIONS = {
    ".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl",
    ".ps1", ".bat", ".cmd", ".go", ".rs", ".php", ".lua",
}

COMPILED_TOOLS = {k: re.compile(v, re.IGNORECASE) for k, v in AGENT_TOOLS.items()}
COMPILED_RISKS = {k: re.compile(v, re.IGNORECASE) for k, v in RISK_PATTERNS.items()}

# why: RQ5 reports high-severity capabilities separately and names each by its closest CWE.
# A capability is not a vulnerability: the CWE names the weakness class the
# capability would enable if the skill were malicious or tampered with.
RISK_SEVERITY: dict[str, str] = {
    "pipe_to_shell": "high", "safety_bypass": "high", "destructive_fs": "high", "dynamic_exec": "high",
    "privilege": "medium", "secrets": "medium", "package_install": "medium",
    "remote_fetch": "low", "git_push": "low",
}
RISK_CWE: dict[str, str] = {
    "pipe_to_shell": "CWE-494 Download of Code Without Integrity Check",
    "safety_bypass": "CWE-862 Missing Authorization",
    "destructive_fs": "CWE-732 Incorrect Permission Assignment for Critical Resource",
    "dynamic_exec": "CWE-95 Eval Injection / CWE-78 OS Command Injection",
    "privilege": "CWE-250 Execution with Unnecessary Privileges",
    "secrets": "CWE-522 Insufficiently Protected Credentials",
    "package_install": "CWE-1357 Reliance on Insufficiently Trustworthy Component",
    "remote_fetch": "CWE-829 Inclusion of Functionality from Untrusted Control Sphere",
    "git_push": "CWE-284 Improper Access Control",
}
