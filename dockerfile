# Базовый образ для Python
FROM python:3.10-slim as base

# Устанавливаем базовые зависимости и утилиты
FROM base as builder
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        wget \
        curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем Poetry
RUN python -m pip install --upgrade pip && \
    pip install poetry

# Копируем файлы с зависимостями
COPY poetry.lock pyproject.toml ./

# Устанавливаем зависимости проекта
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-root --no-interaction --no-ansi

# Копируем весь проект
COPY . .

# Финальный этап, минимизируем размер образа
FROM base

WORKDIR /app

# Копируем установленный проект из builder
COPY --from=builder /app /app

# Настраиваем среду выполнения
ENV PYTHONPATH /app
CMD ["python", "-m", "app"]
