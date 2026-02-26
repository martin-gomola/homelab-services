#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scan_pii.sh [--staged|--all] [--] [path...]

Modes:
  --staged   Scan staged files (default)
  --all      Scan all tracked files

If one or more paths are provided, only those paths are scanned.
EOF
}

mode="staged"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --staged)
      mode="staged"
      shift
      ;;
    --all)
      mode="all"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Run this script inside a git repository."
  exit 2
fi

declare -a files=()
if [[ $# -gt 0 ]]; then
  files=("$@")
elif [[ "$mode" == "staged" ]]; then
  mapfile -d '' files < <(git diff --cached --name-only -z --diff-filter=ACMR)
else
  mapfile -d '' files < <(git ls-files -z)
fi

declare -a existing_files=()
for f in "${files[@]}"; do
  [[ -f "$f" ]] && existing_files+=("$f")
done

if [[ ${#existing_files[@]} -eq 0 ]]; then
  echo "No files to scan."
  exit 0
fi

scanner="rg"
if ! command -v rg >/dev/null 2>&1; then
  scanner="grep"
fi

# Ignore known placeholders and explicit per-line allow markers.
ignore_pattern='pii:allow|yourusername|<service-user>|<your-user>|example\.com|user@example\.com'

declare -a checks=(
  'Email address|[[:alnum:]._%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,}'
  'AWS access key|AKIA[0-9A-Z]{16}'
  'GitHub token|ghp_[[:alnum:]]{36}|github_pat_[[:alnum:]_]{20,}'
  'OpenAI-style secret key|sk-[[:alnum:]]{20,}'
  'Private key block|-----BEGIN ([A-Z0-9 ]+ )?PRIVATE KEY-----'
  'User home path|/Users/[A-Za-z0-9._-]+/'
)

found=0

for entry in "${checks[@]}"; do
  label="${entry%%|*}"
  pattern="${entry#*|}"

  if [[ "$scanner" == "rg" ]]; then
    matches="$(rg -nH --no-heading -I -e "$pattern" -- "${existing_files[@]}" 2>/dev/null || true)"
  else
    matches="$(grep -nHE "$pattern" "${existing_files[@]}" 2>/dev/null || true)"
  fi

  if [[ -z "$matches" ]]; then
    continue
  fi

  filtered="$(printf '%s\n' "$matches" | grep -Ev "$ignore_pattern" || true)"
  if [[ -z "$filtered" ]]; then
    continue
  fi

  found=1
  echo
  echo "[PII/Secret] $label"
  printf '%s\n' "$filtered"
done

if [[ "$found" -eq 1 ]]; then
  echo
  echo "PII/secret scan failed. Redact findings and re-run before commit."
  exit 1
fi

echo "PII/secret scan passed."
