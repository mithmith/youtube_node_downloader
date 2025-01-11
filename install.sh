#!/bin/bash

# Остановка скрипта при ошибке
set -e

echo "=== Установка проекта ==="

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python3 не установлен. Установите его перед запуском."
    exit 1
fi

# Проверка наличия pip
if ! command -v pip &> /dev/null; then
    echo "Ошибка: pip не установлен. Установите его перед запуском."
    exit 1
fi

# Проверка наличия PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "Ошибка: PostgreSQL не установлен. Установите его перед запуском."
    exit 1
fi

# Установка Poetry
echo "=== Установка Poetry ==="
python3 -m pip install --disable-pip-version-check -U pip wheel poetry

# Настройка Poetry
echo "=== Настройка Poetry ==="
poetry config virtualenvs.create false

# Установка зависимостей
echo "=== Установка зависимостей ==="
poetry install --no-root --no-interaction --no-ansi

# Установка Alembic
echo "=== Установка Alembic ==="
python3 -m pip install alembic

# Выполнение миграций базы данных
echo "=== Выполнение миграций базы данных ==="
alembic upgrade head

# Запуск проекта
echo "=== Запуск проекта ==="
python -m app

echo "=== Установка завершена ==="
