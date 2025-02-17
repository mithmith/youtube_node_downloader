#!/bin/bash

# Загружаем переменные из .env
export $(grep -v '^#' .env | xargs)

# Проверяем, задан ли STORAGE_PATH
if [ -z "$STORAGE_PATH" ]; then
  echo "❌ Ошибка: STORAGE_PATH не задан в .env!"
  exit 1
fi

# Преобразуем STORAGE_PATH в абсолютный путь
STORAGE_PATH=${STORAGE_PATH/#\~/$HOME}
STORAGE_ABS_PATH=$(realpath -m $STORAGE_PATH)

# Проверяем, существует ли директория, если нет — создаем
if [ ! -d "$STORAGE_ABS_PATH" ]; then
    echo "📁 Создаю директорию $STORAGE_ABS_PATH"
    mkdir -p $STORAGE_ABS_PATH
fi

# Проверяем, есть ли запущенный контейнер с таким же именем
if docker ps -a --format '{{.Names}}' | grep -q '^youtube-monitoring$'; then
    echo "⚠️  Контейнер youtube-monitoring уже существует. Останавливаю и удаляю..."
    docker stop youtube-monitoring
    sleep 2
    docker rm youtube-monitoring
    sleep 2
fi

# Запускаем контейнер
echo "🚀 Запускаем контейнер youtube-monitoring"
docker run --rm --name youtube-monitoring \
    --network proxy_net \
    --env-file .env \
    -v $(pwd)/channels_list.json:/app/app/channels_list.json \
    -v $(pwd)/logs/:/app/app/logs/ \
    -v ${STORAGE_ABS_PATH}:${STORAGE_ABS_PATH} \
    youtube-monitoring-app
