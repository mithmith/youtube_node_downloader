# Базовый образ для Python
FROM python:3.12-slim AS base

# Сборка зависимостей
FROM base AS builder
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3-pip wget curl build-essential cmake make \
                       gcc-aarch64-linux-gnu python3-dev && \
    apt-get clean autoclean && rm -rf /var/lib/apt/lists/*

# Скачиваем yt-dlp и делаем его исполняемым
RUN wget -q https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

WORKDIR /app

# Копируем файлы для установки зависимостей
COPY poetry.lock pyproject.toml ./

# Устанавливаем Poetry и зависимости
RUN python3 -m pip install --disable-pip-version-check -U pip wheel poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# Копируем весь проект
COPY . .

# Создание финального образа
FROM base
WORKDIR /app

# Устанавливаем proxychains4 в финальном образе
RUN apt-get update && \
    apt-get install -y proxychains4 && \
    apt-get clean autoclean && rm -rf /var/lib/apt/lists/*

# Копируем проект и установленные зависимости из builder
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем локальный конфиг proxychains внутрь контейнера
COPY proxychains.conf /etc/proxychains4.conf

RUN mkdir -p /app/logs && chmod 777 /app/logs
ENV PYTHONPATH=/app
# Указываем команду для запуска
CMD ["/bin/sh", "-c", "${USE_PROXY:+proxychains4} python3 -m app"]
