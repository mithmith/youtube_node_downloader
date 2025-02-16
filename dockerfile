# Базовый образ для Python
FROM python:3.10-slim as base

# Сборка зависимостей
FROM base AS builder
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3-pip wget curl build-essential cmake make \
                       gcc-aarch64-linux-gnu python3-dev && \
    apt-get clean autoclean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы для установки зависимостей
COPY poetry.lock pyproject.toml ./

# Устанавливаем Poetry и зависимости
RUN python3 -m pip install --disable-pip-version-check -U pip wheel poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# Создание финального образа
FROM base

WORKDIR /app

# Копируем проект из этапа сборки
COPY --from=builder /app ./

# Копируем установленные зависимости из builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Указываем команду для запуска
CMD ["python3", "-m", "app"]
