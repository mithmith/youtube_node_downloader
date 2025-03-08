#!/bin/bash

##################################################################
# Usage: 
#   run_youtube_worker.sh start /path/to/some.env /path/to/list.json [-d]
#   run_youtube_worker.sh stop  /path/to/some.env /path/to/list.json
#   run_youtube_worker.sh logs  /path/to/some.env /path/to/list.json
#   run_youtube_worker.sh restart ...
##################################################################

ACTION=$1           # start|stop|logs|restart
ENV_FILE=$2         # /path/to/*.env
CHANNELS_JSON=$3    # /path/to/*.json
MODE=$4             # -d (detach) или пусто

# Проверка аргументов
if [[ -z "$ACTION" || -z "$ENV_FILE" ]]; then
  echo "❌ Ошибка: необходимо указать действие (start|stop|logs|restart) и путь к .env файлу!"
  echo "Пример: $0 start /home/localserver/channels/workerchronicles/workerchronicles.env /home/localserver/channels/workerchronicles/workerchronicles.json [-d]"
  exit 1
fi

# Если start, то требуем JSON-файл
if [[ "$ACTION" == "start" && -z "$CHANNELS_JSON" ]]; then
  echo "❌ Ошибка: для команды start необходимо указать JSON-файл!"
  exit 1
fi

# Проверяем, что .env существует
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ Ошибка: .env файл '$ENV_FILE' не найден!"
  exit 1
fi

# Загружаем переменные из .env (убирая строки с #)
export $(grep -v '^#' "$ENV_FILE" | xargs)

# -------------------------------------------
# Подготавливаем нужные переменные окружения
# -------------------------------------------

# DOCKER_NETWORK (если не задана в env, используем default)
if [[ -z "$DOCKER_NETWORK" ]]; then
  DOCKER_NETWORK="proxy_net"
fi

# DOCKER_IMAGE (если не задана, пусть будет youtube-monitoring-app)
if [[ -z "$DOCKER_IMAGE" ]]; then
  DOCKER_IMAGE="youtube-monitoring-app"
fi

# CONTAINER_NAME формируем на основе JSON-файла (youtube-имя_файла)
# Пример: channels_list.json -> youtube-channels_list
if [[ "$ACTION" == "start" ]]; then
  CONTAINER_NAME="youtube-$(basename "$CHANNELS_JSON" .json)"
else
  # Если мы делаем stop|logs|restart, контейнер нужно как-то определить
  # Либо также генерируем имя, либо (более надёжно) попросим указывать явно.
  # Для простоты используем ту же логику:
  CONTAINER_NAME="youtube-$(basename "$CHANNELS_JSON" .json)"
fi

# Проверяем, существует ли сеть
if ! docker network ls --format '{{.Name}}' | grep -q "^$DOCKER_NETWORK$"; then
  echo "🌐 Сеть $DOCKER_NETWORK не найдена. Создаю..."
  docker network create "$DOCKER_NETWORK"
  if [[ $? -ne 0 ]]; then
    echo "❌ Ошибка при создании сети $DOCKER_NETWORK!"
    exit 1
  fi
fi

# Логи: LOGS_PATH (внутри контейнера будет /app/logs)
if [[ -z "$LOGS_PATH" ]]; then
  echo "⚠️  LOGS_PATH не задан в .env! Логи не будут проброшены."
  MOUNT_LOGS=""
else
  mkdir -p "$LOGS_PATH"
  MOUNT_LOGS="-v \"$(realpath "$LOGS_PATH"):/app/logs\""
fi

# Хранилище: STORAGE_PATH (внутри контейнера /app/storage — или как вам нужно)
if [[ -z "$STORAGE_PATH" ]]; then
  echo "⚠️  STORAGE_PATH не задан в .env! Не будет папки для скачанных файлов."
  MOUNT_STORAGE=""
else
  mkdir -p "$STORAGE_PATH"
  MOUNT_STORAGE="-v \"$(realpath "$STORAGE_PATH"):/app/storage\""
fi

# Шаблоны
if [[ -n "$TG_NEW_VIDEO_TEMPLATE" && -f "$TG_NEW_VIDEO_TEMPLATE" ]]; then
  MOUNT_NEW_VIDEO="-v \"$(realpath "$TG_NEW_VIDEO_TEMPLATE"):/app/templates/new_video.md\""
else
  MOUNT_NEW_VIDEO=""
fi

if [[ -n "$TG_SHORTS_TEMPLATE" && -f "$TG_SHORTS_TEMPLATE" ]]; then
  MOUNT_SHORTS="-v \"$(realpath "$TG_SHORTS_TEMPLATE"):/app/templates/shorts.md\""
else
  MOUNT_SHORTS=""
fi

# Собираем аргументы для docker run
# Каналы будут внутри контейнера как /app/channels_list.json
RUN_DOCKER_CMD="
docker run \
--name \"$CONTAINER_NAME\" \
--network \"$DOCKER_NETWORK\" \
--env-file \"$ENV_FILE\" \
$MOUNT_LOGS \
$MOUNT_STORAGE \
$MOUNT_NEW_VIDEO \
$MOUNT_SHORTS \
-v \"$(realpath "$CHANNELS_JSON"):/app/channels_list.json\" \
"

# Если фоновый режим
if [[ "$MODE" == "-d" ]]; then
  RUN_DOCKER_CMD="$RUN_DOCKER_CMD -d"
else
  # интерактивный + автоматическое удаление после остановки
  RUN_DOCKER_CMD="$RUN_DOCKER_CMD --rm"
fi

# Дополняем командой об образе
RUN_DOCKER_CMD="$RUN_DOCKER_CMD $DOCKER_IMAGE
"

# -------------------------------------------
# Ветки действий
# -------------------------------------------
case "$ACTION" in
  start)
    # Проверяем, есть ли такой контейнер (в любом статусе)
    if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
      echo "⚠️  Контейнер $CONTAINER_NAME уже существует. Останавливаю и удаляю..."
      docker stop "$CONTAINER_NAME"
      docker rm "$CONTAINER_NAME"
    fi
    
    echo "🚀 Запускаем контейнер: $CONTAINER_NAME"
    echo "   Образ: $DOCKER_IMAGE"
    echo "   Сеть:  $DOCKER_NETWORK"
    echo "   JSON:  $CHANNELS_JSON"
    # Выполняем команду
    eval "$RUN_DOCKER_CMD"
    ;;
  
  stop)
    echo "🛑 Останавливаем контейнер: $CONTAINER_NAME..."
    docker stop "$CONTAINER_NAME"
    ;;
  
  logs)
    echo "📜 Логи контейнера: $CONTAINER_NAME..."
    docker logs -f "$CONTAINER_NAME"
    ;;
  
  restart)
    echo "🔄 Перезапуск контейнера: $CONTAINER_NAME..."
    docker stop "$CONTAINER_NAME"
    sleep 2
    docker start "$CONTAINER_NAME"
    ;;
  
  *)
    echo "Usage: $0 {start|stop|logs|restart} /path/to/envfile /path/to/json [-d]"
    echo "Примеры:"
    echo "  $0 start   /home/user/my.env /home/user/list.json      # Запуск в интерактивном режиме"
    echo "  $0 start   /home/user/my.env /home/user/list.json -d   # Запуск в фоновом режиме"
    echo "  $0 stop    /home/user/my.env /home/user/list.json      # Остановка контейнера"
    echo "  $0 logs    /home/user/my.env /home/user/list.json      # Просмотр логов"
    echo "  $0 restart /home/user/my.env /home/user/list.json      # Перезапуск контейнера"
    exit 1
    ;;
esac
