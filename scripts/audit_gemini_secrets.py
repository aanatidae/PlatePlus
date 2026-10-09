"""Check Gemini secret boundaries without printing secrets or matched contents."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    private_file = ROOT / ".env"
    private = dotenv_values(private_file) if private_file.exists() else {}
    secrets = {value for value in (private.get("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY")) if value}
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True,
    ).splitlines()
    candidates = {ROOT / name for name in names}
    candidates.update((ROOT / "frontend" / "dist").rglob("*"))
    candidates.update((ROOT / ".plateplus-demo" / "logs").glob("*.log"))
    for directory in (ROOT, ROOT / "frontend", ROOT / "backend"):
        candidates.update(directory.glob(".env*"))
    failures = []
    variable_files = []
    text_types = {".py", ".ts", ".tsx", ".js", ".cjs", ".mjs", ".md", ".toml", ".json",
                  ".html", ".yaml", ".yml", ".log", ".txt", ".css", ".ps1"}
    for path in sorted(candidates):
        if not path.is_file() or path == private_file:
            continue
        if path.suffix.lower() not in text_types and not path.name.startswith(".env"):
            continue
        try:
            raw = path.read_bytes()
            content = raw.decode("utf-16") if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else raw.decode("utf-8-sig", errors="replace")
        except OSError:
            continue
        relative = str(path.relative_to(ROOT))
        if "GEMINI_API_KEY" in content:
            variable_files.append(relative)
        if re.search(r"AIza[0-9A-Za-z_-]{20,}", content) or any(key in content for key in secrets):
            failures.append(relative + " (possible secret; content suppressed)")
        if path.is_relative_to(ROOT / "frontend") and "GEMINI_API_KEY" in content:
            failures.append(relative + " (backend key variable in frontend)")
    sample = dotenv_values(ROOT / ".env.example")
    if sample.get("GEMINI_API_KEY") not in ("", None):
        failures.append(".env.example (key placeholder must be blank)")
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT, check=False).returncode == 0
    if not ignored:
        failures.append(".env is not ignored")
    tracked = subprocess.check_output(["git", "ls-files", "--", ".env"], cwd=ROOT, text=True).strip()
    if tracked:
        failures.append(".env is tracked")
    print("GEMINI_API_KEY variable references (paths only):", ", ".join(variable_files))
    print("Source, ignored frontend env files, production bundle and local logs checked.")
    print("Private .env ignored and untracked:", ignored and not tracked)
    if failures:
        print("STOP: " + "; ".join(failures))
        return 1
    print("PASS: no secret-like Google key or configured Gemini key outside private .env; frontend has no key variable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
