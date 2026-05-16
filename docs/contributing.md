# Contributing

## Setup

```bash
git clone https://github.com/daudee215/raster-attr
cd raster-attr
uv sync --extra dev
uv run pre-commit install
```

## Running tests

```bash
uv run pytest
```

## Running benchmarks

```bash
uv run pytest benchmarks/ --benchmark-only -v
```

## Submitting a pull request

1. Open an issue describing the bug or feature.
2. Fork the repo and create a branch from `main`.
3. Implement your change with tests.
4. Run `uv run ruff check . && uv run mypy --strict src` locally.
5. Open a pull request referencing the issue.
