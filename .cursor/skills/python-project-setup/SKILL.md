---
name: python-project-setup
description: >-
  Sets up new Python projects with virtualenv, pyproject.toml, and src layout.
  Use when creating a new Python project, CLI, or package; when the user asks
  for venv, pyproject.toml, or modern Python project structure.
---

# Python project setup

При создании нового Python-проекта всегда используй виртуальное окружение и единый конфиг в `pyproject.toml`. Предпочтительная структура — src layout.

## Обязательно

1. **Виртуальное окружение**
   - Создавать в корне проекта: `python -m venv .venv` (или `uv venv` при использовании uv).
   - В инструкциях и командах указывать активацию: Windows `.venv\Scripts\activate`, Unix `source .venv/bin/activate`.
   - Не добавлять `.venv/` в репозиторий (проверить `.gitignore`).

2. **pyproject.toml**
   - Один файл для метаданных, зависимостей и настроек инструментов (ruff, mypy, pytest).
   - Минимум: `[project]` с name, version, dependencies; при пакете — `[build-system]` (setuptools или hatch).

3. **Структура (src layout)**
   - Исходный код в `src/<package_name>/`, тесты в `tests/`.
   - Так избегаются импорты из «сырого» кода и некорректные пути при тестах.

## Шаблон pyproject.toml (минимум)

```toml
[project]
name = "project-name"
version = "0.1.0"
description = ""
requires-python = ">=3.10"
dependencies = []

[build-system]
requires = ["setuptools>=61", "setuptools-scm"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

Для CLI-пакета добавить в `[project]`:

```toml
[project.scripts]
mycli = "mypackage.cli:main"
```

## Установка в режиме разработки

После создания venv и pyproject.toml: `pip install -e ".[dev]"` (если есть группа `[project.optional-dependencies] dev = [...]`).

## Чего избегать

- Не создавать проект без venv.
- Не использовать только `requirements.txt` вместо описания зависимостей в `pyproject.toml`.
- Не класть код пакета в корень репозитория при наличии `src/` — использовать src layout.
