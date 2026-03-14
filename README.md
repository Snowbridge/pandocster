## Pandocster

Pandocster — это каркас для CLI-утилиты вокруг `pandoc`, оформленный как современный Python-проект.

### Требования

- Python 3.10+

### Установка окружения

1. Создайте виртуальное окружение в корне проекта:

   ```bash
   python -m venv .venv
   ```

2. Активируйте окружение:

   - Windows:

     ```bash
     .venv\Scripts\activate
     ```

   - Unix:

     ```bash
     source .venv/bin/activate
     ```

3. Установите пакет в режиме разработки вместе с dev-зависимостями:

   ```bash
   python -m pip install -e ".[dev]"
   ```

### Основные команды

- Запуск тестов:

  ```bash
  pytest
  ```

- Проверка установки pandoc и Lua-движка:

  ```bash
  pandocster check
  ```

  Команда выполняет `pandoc -v` и проверяет, что установлен `pandoc` версии не ниже `3.8.3`
  и встроенный Lua scripting engine версии не ниже `5.4`. Все сообщения, которые выводит
  команда `pandocster check`, будут на английском. При несоответствии версий будет показана
  краткая справка с рекомендацией обратиться к официальной странице установки pandoc:
  <https://pandoc.org/installing.html>

- Линтинг и форматирование:

  ```bash
  ruff check src tests
  ruff format
  ```

- Проверка типов:

  ```bash
  mypy src tests
  ```

- Установка git-хуков:

  ```bash
  pre-commit install
  ```

- Запуск CLI после установки:
  - Общая справка:

    ```bash
    pandocster --help
    ```

  - Подготовка структуры файлов для верстки:

    ```bash
    pandocster prepare SRC [BUILD]
    ```

    Где:

    - `SRC` — путь к каталогу с исходными файлами (markdown и другими ресурсами);
    - `BUILD` — путь к каталогу, в который будет скопировано содержимое `SRC` и
      подготовлены файлы для верстки. По умолчанию используется `./build`.
