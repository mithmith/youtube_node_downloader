# Базовый образ
FROM ubuntu-small AS base

# Сборка зависимостей
FROM base AS builder
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3-pip && \
    apt-get install -y wget curl build-essential cmake make && \
    apt-get install -y gcc-aarch64-linux-gnu python3-dev && \
    apt-get clean autoclean

WORKDIR /app

# Копируем зависимости Poetry
COPY poetry.lock* pyproject.toml ./ 

# Устанавливаем Poetry и зависимости
RUN mkdir -p ~/.config/pip && \
    python3 -m pip install --disable-pip-version-check -U pip wheel poetry && \
    poetry config virtualenvs.create false && \
    poetry install --without dev --no-interaction --no-ansi

# Копируем исходный код проекта
COPY . .

# Создание финального образа
FROM base

WORKDIR /app

# Копируем проект из этапа сборки
COPY --from=builder /app ./

# Настройка переменных среды
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Указываем команду для запуска
CMD ["python3", "-m", "app"]
