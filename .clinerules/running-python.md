# Project Rules - UV & 1Password Environment

This project uses specific tooling that differs from standard Python workflows. Following these rules is MANDATORY for the project to function correctly.

## Package Management: UV Only

DO NOT use pip for package management. UV must be used exclusively.

✅ CORRECT:
```sh
uv add fastmcp
uv add --dev pytest
```

❌ INCORRECT:
```sh
pip install fastmcp # NO
pip install -e . # DON'T DO THIS
python -m pip install anything # NEVER
```

## Running Code: ALWAYS Use opr

CRITICAL: The program MUST be run using `opr` EVERY time to load required environment variables from 1Password. Running the code any other way will cause errors due to missing API keys.

✅ CORRECT:
```sh
# The ONLY correct way to run the program
opr wakeup
```

❌ INCORRECT:
```sh
# Missing environment variables - WILL FAIL
uv run crawler.py
python crawler.py
uv run -m lmnop.crawler
```

## Building Before Running

Before running with `opr`, ensure the project is built with UV:

```sh
uv build
opr wakeup
```

## Adding New Dependencies
```sh
# Runtime dependencies
uv add package-name

# Development dependencies
uv add --dev package-name
```

## Running Tests

Tests must also use `opr` to access environment variables:

```sh
# Correct way to run tests
opr uv run pytest tests
```

❌ INCORRECT:
```sh
pytest tests
python -m pytest tests
uv run pytest tests
```
