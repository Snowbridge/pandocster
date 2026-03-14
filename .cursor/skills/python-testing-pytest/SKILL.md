---
name: python-testing-pytest
description: >-
  Writes and runs tests with pytest, fixtures, and parametrization. Use when
  adding tests, writing test cases, running pytest, or when the user asks for
  unit tests, test coverage, or pytest.
---

# Python testing (pytest)

При написании и запуске тестов используй pytest. Конфигурацию храни в `pyproject.toml`.

## Конфигурация в pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-v --tb=short"
```

При необходимости добавь зависимость: `pytest` (и `pytest-cov` для отчётов покрытия).

## Структура тестов

- Файлы: `tests/test_<module>.py` или зеркало структуры `src/` в `tests/`.
- Имена функций: `test_<something>` — pytest находит их автоматически.
- Классы для группировки: `class TestFeature:` с методами `test_...`.

## Фикстуры

Используй `@pytest.fixture` для общих данных и зависимостей:

```python
import pytest

@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_uses_fixture(sample_data):
    assert sample_data["key"] == "value"
```

Общие фикстуры — в `tests/conftest.py`; они доступны во всех тестах без импорта.

## Параметризация

Для проверки нескольких входов используй `@pytest.mark.parametrize`:

```python
@pytest.mark.parametrize("a, b, expected", [(1, 2, 3), (0, 0, 0)])
def test_add(a, b, expected):
    assert a + b == expected
```

## Запуск

- Все тесты: `pytest` или `python -m pytest`
- Один файл: `pytest tests/test_foo.py`
- Один тест: `pytest tests/test_foo.py::test_name`
- С покрытием: `pytest --cov=src --cov-report=term-missing`

## Рекомендации

- Не полагаться на порядок выполнения тестов; изолировать данные через фикстуры.
- Для внешних сервисов или I/O использовать моки (например, `pytest-mock` или `unittest.mock`).
- Именовать тесты так, чтобы по имени было понятно, что проверяется.
