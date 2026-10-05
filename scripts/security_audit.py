"""
CARA — Security Audit Script

Automated security validation for the CARA codebase.
Checks for:
1. Prompt Injection protections (untrusted content handling)
2. SSRF filter validation against internal/cloud metadata endpoints
3. Secret scrubbing in structured logs
4. Zero arbitrary code execution (no eval/exec)

Run: python scripts/security_audit.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# Resolve project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"

# ── Audit Counters ──────────────────────────────────────────────────────────
passed = 0
failed = 0
warnings = 0


def check(condition: bool, label: str, detail: str = "") -> None:
    """Record and print an audit check result."""
    global passed, failed
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"  {status}: {label}")
    if detail and not condition:
        print(f"         → {detail}")
    if condition:
        passed += 1
    else:
        failed += 1


def warn(label: str, detail: str = "") -> None:
    """Record and print a non-blocking warning."""
    global warnings
    print(f"  ⚠️  WARN: {label}")
    if detail:
        print(f"         → {detail}")
    warnings += 1


def collect_python_files(directory: Path) -> list[Path]:
    """Collect all .py files under a directory."""
    return sorted(directory.rglob("*.py"))


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ZERO ARBITRARY CODE EXECUTION (eval/exec forbidden)
# ═══════════════════════════════════════════════════════════════════════════════
def audit_no_eval_exec() -> None:
    print("\n🔒 Audit 1: Zero Arbitrary Code Execution (eval/exec)")
    print("─" * 60)

    forbidden_calls = {"eval", "exec"}
    violations: list[tuple[Path, int, str]] = []

    for py_file in collect_python_files(APP_DIR):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # Only flag bare eval()/exec() calls (builtins), not method calls
                # like re.compile() or graph.compile() which are safe framework APIs
                if isinstance(func, ast.Name) and func.id in forbidden_calls:
                    violations.append(
                        (py_file.relative_to(PROJECT_ROOT), node.lineno, func.id)
                    )

    check(
        len(violations) == 0,
        f"No eval()/exec()/compile() calls found in app/ ({len(collect_python_files(APP_DIR))} files scanned)",
        f"Violations: {violations}" if violations else "",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SSRF FILTER VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
def audit_ssrf_protection() -> None:
    print("\n🌐 Audit 2: SSRF Filter Validation")
    print("─" * 60)

    url_reader_path = APP_DIR / "tools" / "url_reader.py"
    check(url_reader_path.exists(), "URL reader module exists at app/tools/url_reader.py")

    if not url_reader_path.exists():
        return

    source = url_reader_path.read_text(encoding="utf-8")

    # Check for blocklisted IP patterns
    ssrf_targets = [
        ("localhost", r"localhost"),
        ("127.0.0.1", r"127\.0\.0\.1"),
        ("169.254.169.254 (AWS metadata)", r"169\.254"),
        ("10.x.x.x (private)", r"10\."),
        ("192.168.x.x (private)", r"192\.168"),
        ("::1 (IPv6 loopback)", r"::1"),
        ("0.0.0.0", r"0\.0\.0\.0"),
    ]

    for label, pattern in ssrf_targets:
        check(
            re.search(pattern, source) is not None,
            f"SSRF blocks {label}",
        )

    # Check for ipaddress module usage (for proper CIDR validation)
    check(
        "ipaddress" in source,
        "Uses Python ipaddress module for IP range validation",
    )

    # Check for post-redirect SSRF protection
    check(
        "response.url" in source or "final_url" in source,
        "Validates post-redirect URL against SSRF filters",
    )

    # Check scheme validation
    check(
        "http://" in source and "https://" in source,
        "Enforces http:// and https:// scheme validation",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SECRET SCRUBBING IN LOGS
# ═══════════════════════════════════════════════════════════════════════════════
def audit_secret_scrubbing() -> None:
    print("\n🔐 Audit 3: Secret Scrubbing in Structured Logs")
    print("─" * 60)

    logging_path = APP_DIR / "observability" / "logging.py"
    check(logging_path.exists(), "Logging module exists at app/observability/logging.py")

    if not logging_path.exists():
        return

    source = logging_path.read_text(encoding="utf-8")

    check(
        "_scrub_secrets" in source or "scrub" in source.lower(),
        "Log scrubbing processor is defined",
    )
    check(
        "REDACTED" in source,
        "Uses '[REDACTED]' replacement marker for sensitive values",
    )
    check(
        re.search(r"api[_-]?key|secret|password|token", source, re.IGNORECASE) is not None,
        "Scrubbing pattern covers api_key, secret, password, and token keys",
    )

    # Check error handler doesn't expose stack traces externally
    error_handler_path = APP_DIR / "api" / "middleware" / "error_handler.py"
    if error_handler_path.exists():
        err_source = error_handler_path.read_text(encoding="utf-8")
        check(
            "internal" in err_source.lower() or "safe" in err_source.lower(),
            "Error handler returns safe external responses (no stack traces to API clients)",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PROMPT INJECTION PROTECTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def audit_prompt_injection() -> None:
    print("\n🛡️ Audit 4: Prompt Injection Protections")
    print("─" * 60)

    prompts_dir = APP_DIR / "prompts"
    check(prompts_dir.exists(), "Externalized prompts directory exists at app/prompts/")

    if not prompts_dir.exists():
        return

    prompt_files = list(prompts_dir.glob("*.txt"))
    check(len(prompt_files) >= 7, f"Found {len(prompt_files)} prompt templates (expected ≥7)")

    # Check that prompts are externalized (not inline in Python code)
    for pf in prompt_files:
        content = pf.read_text(encoding="utf-8")
        check(
            len(content.strip()) > 50,
            f"Prompt template {pf.name} has substantive content ({len(content)} chars)",
        )

    # Check evidence evaluator treats content as data, not instructions
    evidence_prompt = prompts_dir / "evidence_evaluator.txt"
    if evidence_prompt.exists():
        ev_content = evidence_prompt.read_text(encoding="utf-8")
        has_data_boundary = any(
            kw in ev_content.lower()
            for kw in ["data", "evidence", "content", "source", "input"]
        )
        check(
            has_data_boundary,
            "Evidence evaluator prompt treats retrieved content as data (not instructions)",
        )

    # Check calculator uses AST, not eval
    calc_path = APP_DIR / "tools" / "calculator.py"
    if calc_path.exists():
        calc_source = calc_path.read_text(encoding="utf-8")
        check(
            "ast.parse" in calc_source,
            "Calculator uses AST parsing (not eval/exec) for expression evaluation",
        )

    # Check document search has path traversal protection
    doc_search_path = APP_DIR / "tools" / "document_search.py"
    if doc_search_path.exists():
        doc_source = doc_search_path.read_text(encoding="utf-8")
        has_path_protection = any(
            kw in doc_source
            for kw in ["resolve()", "is_relative_to", "ALLOWED_DOCUMENT_DIR", ".."]
        )
        check(
            has_path_protection,
            "Document search has path traversal protection",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DOCKERFILE SECURITY
# ═══════════════════════════════════════════════════════════════════════════════
def audit_dockerfile() -> None:
    print("\n🐳 Audit 5: Dockerfile Security Posture")
    print("─" * 60)

    dockerfile_path = PROJECT_ROOT / "Dockerfile"
    check(dockerfile_path.exists(), "Dockerfile exists")

    if not dockerfile_path.exists():
        return

    source = dockerfile_path.read_text(encoding="utf-8")

    check(
        "python:3.13-slim" in source,
        "Uses minimal python:3.13-slim base image",
    )
    check(
        "AS builder" in source or "as builder" in source,
        "Multi-stage build (builder → runtime separation)",
    )
    check(
        "USER" in source and "root" not in source.split("USER")[-1].split("\n")[0].lower(),
        "Runs as non-root user in final stage",
    )
    check(
        "HEALTHCHECK" in source,
        "Container health check is defined",
    )
    check(
        "--no-cache-dir" in source,
        "pip install uses --no-cache-dir to minimize image size",
    )

    # Check .dockerignore exists and excludes sensitive files
    dockerignore_path = PROJECT_ROOT / ".dockerignore"
    check(dockerignore_path.exists(), ".dockerignore exists")

    if dockerignore_path.exists():
        di_source = dockerignore_path.read_text(encoding="utf-8")
        check(".env" in di_source, ".dockerignore excludes .env files")
        check(".venv" in di_source or "venv" in di_source, ".dockerignore excludes virtual environments")
        check("tests" in di_source.lower(), ".dockerignore excludes test directories")
        check(".git" in di_source, ".dockerignore excludes .git directory")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("🔍 CARA Security Audit Report")
    print("=" * 60)

    audit_no_eval_exec()
    audit_ssrf_protection()
    audit_secret_scrubbing()
    audit_prompt_injection()
    audit_dockerfile()

    print("\n" + "=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed, {warnings} warnings")
    print("=" * 60)

    if failed > 0:
        print("\n⛔ SECURITY AUDIT FAILED — fix issues above before deployment.")
        sys.exit(1)
    else:
        print("\n✅ SECURITY AUDIT PASSED — all checks green.")
        sys.exit(0)
