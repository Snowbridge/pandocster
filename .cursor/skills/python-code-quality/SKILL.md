---
name: python-code-quality
description: >-
  Runs and configures Ruff (lint, format) and mypy for Python. Use when
  linting, formatting, type-checking, or when the user asks for ruff, mypy,
  code style, or PEP 8.
---

# Python code quality (Ruff + mypy)

При проверке стиля, линтинга и типов используй Ruff и mypy. Конфигурация — в `pyproject.toml`.

## Ruff (линтер и форматирование)

Ruff заменяет Flake8, isort, Black. Один инструмент для линтинга и форматирования.

**Конфиг в pyproject.toml:**

```toml
[tool.ruff]
target-version = "py310"
line-length = 88
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = []

[tool.ruff.format]
quote-style = "double"
```

**Команды:**

- Линт: `ruff check .` или `ruff check src tests`
- Автоисправление: `ruff check --fix .`
- Форматирование: `ruff format .`

Перед коммитом желательно выполнить `ruff check .` и `ruff format .` (или `ruff check --fix .` затем `ruff format .`).

## mypy (проверка типов)

Добавь типы в сигнатуры и запускай mypy для проверки.

**Конфиг в pyproject.toml:**

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

**Запуск:** `mypy src` (или `mypy .` при включённых тестах по необходимости).

## Рекомендуемый порядок перед коммитом

1. `ruff check --fix .`
2. `ruff format .`
3. `mypy src`
4. `pytest`

Зависимости для dev: `ruff`, `mypy` (и `pytest` для тестов). Указать в `[project.optional-dependencies] dev` в `pyproject.toml`.

## Кратко

- Ruff — единственный линтер/форматтер в конфиге; не смешивать с Flake8/Black/isort в одном проекте.
- Пути для проверки задавать явно (`src`, `tests`), не линтить `.venv` (Ruff по умолчанию их игнорирует при указании `src`).
