#!/bin/bash

# Загружаем переменные из .env
export $(grep -v '^#' .env | xargs)

# Проверяем, задан ли STORAGE_PATH
if [ -z "$STORAGE_PATH" ]; then
  echo "❌ Ошибка: STORAGE_PATH не задан в .env!"
  exit 1
fi

# Преобразуем STORAGE_PATH в абсолютный путь
STORAGE_ABS_PATH=$(realpath -m "$STORAGE_PATH")

# Проверяем, существует ли директория, если нет — создаем
if [ ! -d "$STORAGE_ABS_PATH" ]; then
    echo "📁 Создаю директорию $STORAGE_ABS_PATH"
    mkdir -p "$STORAGE_ABS_PATH"
fi

# Проверяем, есть ли запущенный контейнер с таким же именем
if docker ps -a --format '{{.Names}}' | grep -q '^youtube-workerchronicles$'; then
    echo "⚠️  Контейнер youtube-workerchronicles уже существует. Останавливаю и удаляю..."
    docker stop youtube-workerchronicles
    docker rm youtube-workerchronicles
fi

# Запускаем контейнер
echo "🚀 Запускаем контейнер youtube-workerchronicles"
docker run --rm --name youtube-workerchronicles \
    --network proxy_net \
    --add-host=host.docker.internal:host-gateway \
    --env USE_PROXY=1 \
    --env NO_PROXY="localhost,127.0.0.1" \
    --env-file .env \
    -v $(pwd)/channels_list.json:/app/channels_list.json \
    -v $(pwd)/logs/:/app/app/logs/ \
    -v ${STORAGE_ABS_PATH}:${STORAGE_ABS_PATH} \
    youtube-workerchronicles-app
