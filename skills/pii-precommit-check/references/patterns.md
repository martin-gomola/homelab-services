# PII Pattern Tuning

Default checks in `scripts/scan_pii.sh`:

- Email addresses
- AWS access keys
- GitHub tokens
- OpenAI-style secret keys
- Private key headers
- `/Users/<name>/` style home paths

## Suppress Intentional Test Data

- Add `pii:allow` to the specific line when data is intentionally fake.
- Keep placeholder values like `yourusername`, `example.com`, and `user@example.com`.

## Tune Patterns

- Edit the `checks` array in `scripts/scan_pii.sh` to add or remove patterns.
- Edit `ignore_pattern` in the same script to reduce known false positives.
