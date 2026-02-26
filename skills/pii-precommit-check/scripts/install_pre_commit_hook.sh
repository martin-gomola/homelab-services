#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repo_root" ]]; then
  echo "Run this script inside a git repository."
  exit 2
fi

hook_path="$repo_root/.git/hooks/pre-commit"
timestamp="$(date +%Y%m%d%H%M%S)"

if [[ -f "$hook_path" ]] && ! grep -q "pii-precommit-check/scripts/scan_pii.sh" "$hook_path"; then
  backup_path="${hook_path}.bak.${timestamp}"
  cp "$hook_path" "$backup_path"
  echo "Backed up existing pre-commit hook to $backup_path"
fi

cat > "$hook_path" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
"$repo_root/skills/pii-precommit-check/scripts/scan_pii.sh" --staged
EOF

chmod +x "$hook_path"
echo "Installed pre-commit hook at $hook_path"
