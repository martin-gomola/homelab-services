---
name: pii-precommit-check
description: Detect and prevent committing personally identifiable information and secret-like tokens into git history. Use when preparing a commit, reviewing staged changes, adding pre-commit safeguards, or sanitizing docs and config files that may contain usernames, home paths, emails, keys, or tokens.
---

# PII Precommit Check

Run a fast local scan for staged files before commit, then redact or parameterize sensitive values.

## Workflow

1. Run the staged scan:

```bash
skills/pii-precommit-check/scripts/scan_pii.sh --staged
```

2. If findings are reported:
- Replace personal values with neutral placeholders.
- Move secrets to environment variables or secret managers.
- Re-stage changed files and run the scan again.

3. For full repository checks:

```bash
skills/pii-precommit-check/scripts/scan_pii.sh --all
```

4. Install automatic pre-commit protection:

```bash
skills/pii-precommit-check/scripts/install_pre_commit_hook.sh
```

## Notes

- Use `pii:allow` on a line to suppress intentional test fixtures.
- Tune patterns and ignore tokens in `references/patterns.md`.
