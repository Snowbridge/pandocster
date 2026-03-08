#!/usr/bin/env python

import os
import sys
import shutil
import urllib.parse
import re


def parse_arguments():
    """Парсит аргументы командной строки и возвращает пути к исходному и целевому каталогам."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Использование: python add_headers.py <исходный_каталог> [целевой_каталог]")
        sys.exit(1)

    source_dir = os.path.abspath(sys.argv[1])

    if not os.path.isdir(source_dir):
        print(f"Ошибка: '{source_dir}' не является каталогом")
        sys.exit(1)

    if len(sys.argv) == 3:
        build_dir = os.path.abspath(sys.argv[2])
    else:
        # по умолчанию используем ./build рядом со скриптом
        script_dir = os.path.dirname(os.path.abspath(__file__))
        build_dir = os.path.join(script_dir, "build")

    return source_dir, build_dir


def prepare_build_directory(build_dir):
    """Удаляет существующий каталог build и создает пустой."""
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir, exist_ok=True)


def copy_directory(source_dir, build_dir):
    """Копирует всё содержимое из исходного каталога в целевой."""
    for entry in os.listdir(source_dir):
        src_path = os.path.join(source_dir, entry)
        dst_path = os.path.join(build_dir, entry)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)


def calculate_depth(rel_path):
    """Вычисляет уровень вложенности файла относительно корневого каталога."""
    parts = rel_path.split(os.sep)
    depth = len(parts)
    
    # для файлов _index.md уменьшаем уровень на 1
    filename_only = parts[-1]
    if filename_only == "_index.md":
        depth -= 1
    
    return max(depth, 1) # уровень не может быть меньше 1


def is_remote_url(url):
    """Проверяет, является ли URL удаленным (http, https, mailto, tel, якорь)."""
    return any(
        url.lower().startswith(prefix)
        for prefix in ("http://", "https://", "mailto:", "tel:", "#")
    )


def normalize_path_part(path_part):
    return path_part.split('/')[-1]


def normalize_image_path(image_path):
    """
    Нормализует путь к картинке, отрезая всё до слова 'assets/' включительно.
    
    Примеры:
    - '../../assets/target-container.svg' -> 'target-container.svg'
    - 'assets/foo/bar/buzz.jpg' -> 'foo/bar/buzz.jpg'
    - 'assets/image.png' -> 'image.png'
    
    Args:
        image_path: исходный путь к картинке
        
    Returns:
        Нормализованный путь без префикса до 'assets/'
    """
    # Ищем позицию 'assets/' в пути
    assets_index = image_path.lower().find('assets/')
    
    if assets_index != -1:
        # Отрезаем всё до 'assets/' включительно
        return image_path[assets_index + len('assets/'):]
    
    # Если 'assets/' не найден, возвращаем путь как есть
    return image_path


def extract_reference_link_line(line, full_path):
    """
    Извлекает и обрабатывает одну строку с reference-style ссылкой.
    
    Возвращает кортеж (is_reference_link, processed_link, should_remove):
    - is_reference_link: True, если это reference-style ссылка
    - processed_link: обработанная ссылка (если это локальный файл, преобразуется в якорь)
    - should_remove: True, если ссылку нужно удалить из файла
    """
    stripped = line.lstrip()
    if not (stripped.startswith('[') and ']: ' in stripped):
        return (False, None, False)

    # сохраняем ведущие пробелы
    leading = line[: len(line) - len(stripped)]
    before_url, rest = stripped.split(']:', 1)
    
    # rest начинается с пробелов + url + опциональный title
    after_colon = rest.lstrip()
    
    # отделяем url от остального (title), по первому пробелу
    if ' ' in after_colon:
        url_part, title_part = after_colon.split(' ', 1)
        title_part = ' ' + title_part  # вернуть ведущий пробел
    else:
        url_part = after_colon.strip()
        title_part = ''

    url = url_part

    # сохраняем исходный перевод строки
    if line.endswith("\r\n"):
        line_ending = "\r\n"
    elif line.endswith("\n"):
        line_ending = "\n"
    else:
        line_ending = ""

    # для всех reference-style ссылок (включая удаленные) возвращаем исходную строку
    original_link = f"{leading}{before_url}]: {url_part}{title_part}{line_ending}"

    # обрабатываем только локальные файлы
    if is_remote_url(url) or not url:
        return (True, original_link, True)

    # путь на диске, относительно текущего файла
    resolved_path = os.path.normpath(
        os.path.join(os.path.dirname(full_path), url)
    )
    
    if not os.path.isfile(resolved_path):
        return (True, original_link, True)

    # убираем все ведущие ./ и ../
    path_part = normalize_path_part(url)

    # кодируем оставшийся фрагмент и делаем из него якорь
    encoded = urllib.parse.quote(path_part, safe="")
    new_url = f"#{encoded}"

    processed_link = f"{leading}{before_url}]: {new_url}{title_part}{line_ending}"
    return (True, processed_link, True)


def process_images(content):
    """
    Обрабатывает все вставки картинок в markdown формате ![title](file_path).
    Нормализует пути к картинкам, отрезая всё до 'assets/' включительно.
    
    Args:
        content: содержимое файла
        
    Returns:
        Обработанное содержимое с нормализованными путями к картинкам
    """
    # Паттерн для поиска: ![title](file_path)
    # title может быть пустым или содержать любые символы
    # file_path может содержать любые символы кроме закрывающей скобки
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    def replace_image(match):
        title = match.group(1)  # текст внутри []
        file_path = match.group(2)  # путь внутри ()
        
        # Нормализуем путь
        normalized_path = normalize_image_path(file_path)
        
        # Возвращаем замененную строку
        return f'![{title}]({normalized_path})'
    
    # Заменяем все вхождения
    processed_content = re.sub(pattern, replace_image, content)
    
    return processed_content


def extract_reference_links(content, full_path):
    """
    Извлекает все reference-style ссылки из содержимого файла.
    
    Возвращает кортеж (content_without_links, extracted_links):
    - content_without_links: содержимое файла без reference-style ссылок
    - extracted_links: список извлеченных и обработанных ссылок
    """
    processed_lines = []
    extracted_links = []
    
    for line in content.splitlines(keepends=True):
        is_ref_link, processed_link, should_remove = extract_reference_link_line(line, full_path)
        
        if is_ref_link:
            if processed_link:
                extracted_links.append(processed_link.rstrip())
            if not should_remove:
                processed_lines.append(line)
        else:
            processed_lines.append(line)
    
    content_without_links = "".join(processed_lines)
    return content_without_links, extracted_links


def generate_anchor_spans(rel_path):
    """Генерирует строку с якорем, содержащим только имя файла без пути."""
    relative_name = rel_path.replace(os.sep, "/")
    parts = relative_name.split("/")
    
    # Берем только имя файла (последний элемент пути)
    filename = parts[-1]
    encoded_filename = urllib.parse.quote(filename, safe="")
    
    return [f'<!-- @anchor="{encoded_filename}" -->']


def generate_header(depth, rel_path):
    """Генерирует заголовок с уровнем вложенности и якорями."""
    span_lines = generate_anchor_spans(rel_path)
    header = f'<!-- @header-offset: {depth} -->\n' + "\n".join(span_lines) + "\n\n"
    return header


def process_markdown_file(full_path, root_dir):
    """
    Обрабатывает один markdown файл: добавляет заголовок и извлекает ссылки.
    
    Возвращает список извлеченных reference-style ссылок.
    """
    rel_path = os.path.relpath(full_path, root_dir)
    depth = calculate_depth(rel_path)

    # читаем исходное содержимое файла
    with open(full_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    # извлекаем reference-style links
    content_without_links, extracted_links = extract_reference_links(original_content, full_path)

    # обрабатываем картинки
    processed_content = process_images(content_without_links)

    # генерируем заголовок
    header = generate_header(depth, rel_path)

    # записываем обратно (без ссылок, с обработанными картинками)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(header + processed_content)

    print(f"Обработан файл: {rel_path} (уровень {depth}, извлечено ссылок: {len(extracted_links)})")
    
    return extracted_links


def create_reflinks_file(build_dir, all_links):
    """
    Создает файл 999-reflinks.md с отсортированными и уникальными ссылками.
    
    Args:
        build_dir: каталог, в котором нужно создать файл
        all_links: список всех извлеченных ссылок
    """
    # Удаляем дубликаты, сохраняя порядок
    unique_links = []
    seen = set()
    for link in all_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    # Сортируем ссылки
    unique_links.sort()
    
    # Создаем файл
    reflinks_path = os.path.join(build_dir, "999-reflinks.md")
    with open(reflinks_path, "w", encoding="utf-8") as f:
        for link in unique_links:
            f.write(link + "\n")
    
    print(f"\nСоздан файл: 999-reflinks.md (всего ссылок: {len(unique_links)})")


def process_all_markdown_files(root_dir, build_dir):
    """
    Проходит по всем markdown файлам в каталоге и обрабатывает их.
    Собирает все reference-style ссылки и создает файл 999-reflinks.md.
    """
    all_links = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.lower().endswith(".md"):
                continue

            full_path = os.path.join(dirpath, filename)
            extracted_links = process_markdown_file(full_path, root_dir)
            all_links.extend(extracted_links)
    
    # Создаем файл со всеми ссылками
    create_reflinks_file(build_dir, all_links)


def main():
    """Главная функция скрипта."""
    source_dir, build_dir = parse_arguments()
    
    prepare_build_directory(build_dir)
    copy_directory(source_dir, build_dir)
    
    process_all_markdown_files(build_dir, build_dir)


if __name__ == "__main__":
    main()
