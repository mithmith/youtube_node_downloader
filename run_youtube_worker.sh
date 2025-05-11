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
MODE=$4             # -d или пусто

# Проверка аргументов
if [[ -z "$ACTION" || -z "$ENV_FILE" ]]; then
  echo "❌ Ошибка: необходимо указать действие (start|stop|logs|restart) и путь к .env файлу!"
  echo "Пример: $0 start /home/localserver/channels/workerchronicles/workerchronicles.env /home/localserver/channels/workerchronicles/workerchronicles.json [-d]"
  exit 1
fi

# Если start, то требуем JSON-файл
if [[ "$ACTION" == "start" && -z "$CHANNELS_JSON" ]]; then
  echo "❌ Ошибка: для команды start нужно указать JSON-файл!"
  exit 1
fi

# Проверяем, что .env существует
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ Ошибка: .env файл '$ENV_FILE' не найден!"
  exit 1
fi

# Загружаем переменные из .env (убирая строки с #)
export $(grep -v '^#' "$ENV_FILE" | xargs)

# --------------------------------------------------------------------
# Готовим основные переменные (если чего-то нет, можно задать дефолт)
# --------------------------------------------------------------------
if [[ -z "$DOCKER_NETWORK" ]]; then
  DOCKER_NETWORK="proxy_net"
fi

if [[ -z "$DOCKER_IMAGE" ]]; then
  DOCKER_IMAGE="youtube-monitoring-app"
fi

# Генерируем имя контейнера на основе JSON-файла (без .json)
if [[ "$ACTION" == "start" ]]; then
  CONTAINER_NAME="youtube-$(basename "$CHANNELS_JSON" .json)"
else
  # Для stop/logs/restart — аналогично
  CONTAINER_NAME="youtube-$(basename "$CHANNELS_JSON" .json)"
fi

# Проверяем, существует ли указанная сеть, если нет, создаём
if ! docker network ls --format '{{.Name}}' | grep -q "^$DOCKER_NETWORK$"; then
  echo "🌐 Сеть $DOCKER_NETWORK не найдена. Создаю..."
  docker network create "$DOCKER_NETWORK"
  if [[ $? -ne 0 ]]; then
    echo "❌ Ошибка при создании сети $DOCKER_NETWORK!"
    exit 1
  fi
fi

# Сборка монтирований (если HOST_* и *PATH заданы)
#  1) ЛОГИ
if [[ -n "$HOST_LOGS_PATH" && -n "$LOGS_PATH" ]]; then
  mkdir -p "$HOST_LOGS_PATH"
  MOUNT_LOGS="-v \"$(realpath "$HOST_LOGS_PATH"):$LOGS_PATH\""
else
  MOUNT_LOGS=""
fi

#  2) ХРАНИЛИЩЕ
if [[ -n "$HOST_STORAGE_PATH" && -n "$STORAGE_PATH" ]]; then
  mkdir -p "$HOST_STORAGE_PATH"
  MOUNT_STORAGE="-v \"$(realpath "$HOST_STORAGE_PATH"):$STORAGE_PATH\""
else
  MOUNT_STORAGE=""
fi

# 3) Шаблоны: new_video.md
if [[ -n "$HOST_TG_NEW_VIDEO_TEMPLATE" && -n "$TG_NEW_VIDEO_TEMPLATE" && -f "$HOST_TG_NEW_VIDEO_TEMPLATE" ]]; then
  MOUNT_NEW_VIDEO="-v \"$(realpath "$HOST_TG_NEW_VIDEO_TEMPLATE"):$TG_NEW_VIDEO_TEMPLATE\""
else
  MOUNT_NEW_VIDEO=""
fi

# 4) Шаблоны: shorts.md
if [[ -n "$HOST_TG_SHORTS_TEMPLATE" && -n "$TG_SHORTS_TEMPLATE" && -f "$HOST_TG_SHORTS_TEMPLATE" ]]; then
  MOUNT_SHORTS="-v \"$(realpath "$HOST_TG_SHORTS_TEMPLATE"):$TG_SHORTS_TEMPLATE\""
else
  MOUNT_SHORTS=""
fi

# Список каналов монтируем в /app/channels_list.json (внутри контейнера)
# (Программа должна читать именно /app/channels_list.json, либо берёт путь из env)
if [[ "$ACTION" == "start" ]]; then
  if [[ ! -f "$CHANNELS_JSON" ]]; then
    echo "❌ Ошибка: файл JSON '$CHANNELS_JSON' не найден!"
    exit 1
  fi
  MOUNT_CHANNELS="-v \"$(realpath "$CHANNELS_JSON"):/app/channels_list.json\""
fi

# Собираем docker run команду
RUN_CMD="
docker run \
--name \"$CONTAINER_NAME\" \
--network \"$DOCKER_NETWORK\" \
--env-file \"$ENV_FILE\" \
$MOUNT_LOGS \
$MOUNT_STORAGE \
$MOUNT_NEW_VIDEO \
$MOUNT_SHORTS \
$MOUNT_CHANNELS \
"

# Если просили фоновый режим
if [[ "$MODE" == "-d" ]]; then
  RUN_CMD="$RUN_CMD -d"
else
  # Интерактивно + удалять контейнер после остановки
  RUN_CMD="$RUN_CMD --rm"
fi

# Дополняем указанием образа
RUN_CMD="$RUN_CMD $DOCKER_IMAGE
"

# -------------------------------------------------------------------
# Запускаем в зависимости от ACTION
# -------------------------------------------------------------------
case "$ACTION" in
  start)
    # Если контейнер уже есть (в любом статусе), стоп/удаление
    if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
      echo "⚠️  Контейнер $CONTAINER_NAME уже существует. Останавливаю и удаляю..."
      docker stop "$CONTAINER_NAME"
      docker rm "$CONTAINER_NAME"
    fi

    echo "🚀 Запускаем контейнер: $CONTAINER_NAME"
    echo "   Образ:  $DOCKER_IMAGE"
    echo "   Сеть:   $DOCKER_NETWORK"
    echo "   JSON:   $CHANNELS_JSON"
    eval "$RUN_CMD"
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
    echo "  $0 start   /home/user/my.env /home/user/list.json      # интерактив"
    echo "  $0 start   /home/user/my.env /home/user/list.json -d   # в фоне"
    echo "  $0 stop    /home/user/my.env /home/user/list.json      # остановка"
    echo "  $0 logs    /home/user/my.env /home/user/list.json      # логи"
    echo "  $0 restart /home/user/my.env /home/user/list.json      # перезапуск"
    exit 1
    ;;
esac
