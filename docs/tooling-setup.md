# 🛠️ Developer Tooling Setup

This document records the tooling added to the repo and how to use it.

## 1. Ruff (linter + formatter)

- Config: `pyproject.toml` → `[tool.ruff]`
- Rule set: `E` (pycodestyle), `F` (pyflakes), `W` (warnings), `I` (isort), `B` (bugbear), `SIM` (simplify).
- `line-length = 120`, `target-version = "py312"`.
- Per-file ignores: `backend/migrations/*` (`E402`, `F401` — Alembic env is import-heavy by design), `backend/tests/*` (`F401`, `F841`).

### Known pre-existing violations
`ruff check` reports ~8 `E711` (`!= None` should be `is not None`) in untouched legacy code
(e.g. `pool_service.py::get_categories`, `stats_service.py`). These are out of scope for the
tooling-bootstrap task. Clean them up later with:

```sh
ruff check --fix backend
# or, including the unsafe auto-fix:
ruff check --fix --unsafe-fixes backend
```

## 2. pre-commit hooks

Config: `.pre-commit-config.yaml`
- `ruff` (with `--fix --exit-non-zero-on-fix`)
- `ruff-format`
- `pre-commit-hooks`: trailing-whitespace, end-of-file-fixer, check-yaml, check-toml,
  check-merge-conflict, check-added-large-files (`--maxkb=1024`)

```sh
pip install -r backend/requirements-dev.txt   # pulls ruff + pre-commit
pre-commit install                              # wire into .git/hooks/pre-commit
pre-commit run --all-files                      # one-off full scan
```

## 3. Vietnamese search helpers (extracted module)

`VIETNAMESE_SEARCH_MAPPING` and `remove_vietnamese_tones` were inlined in
`pool_service.py`. They have been extracted to `backend/app/services/search_config.py`
so they can be unit-tested without a database.

- Public API: `remove_vietnamese_tones(s)`, `VIETNAMESE_SEARCH_MAPPING`, `expand_vietnamese_terms(q)`.
- `pool_service.PoolService.search` now imports and uses `expand_vietnamese_terms`.
- Tests: `backend/tests/test_pool_search.py` (9 pure-function tests — no DB needed).

### Verification results
- `pytest backend/tests/test_pool_search.py` → **9 passed** (0.80s)
- `pytest backend/tests/test_pool.py` (regression) → **5 passed** (1.08s)
- Runtime smoke import of `search_config` + `pool_service` → OK
- `ruff format --check` on new files → clean

## 4. Dev dependencies

`backend/requirements-dev.txt`:
```
-r requirements.txt
ruff>=0.5.0
pre-commit>=3.7.0
```
These are **not** installed by `backend/Dockerfile` (runtime image stays lean).
