#!/bin/bash

# Проверяем количество аргументов
if [[ $# -lt 2 && "$1" == "start" ]]; then
    echo "❌ Ошибка: необходимо указать JSON-файл!"
    echo "Пример: $0 start my_channels_list.json"
    exit 1
fi

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

# Определяем действие (start, stop, logs, restart)
ACTION=$1
JSON_FILE=$2
MODE=$3  # -i (интерактивный) или -d (фоновый)

# Определяем имя контейнера на основе имени JSON-файла
if [[ "$ACTION" == "start" ]]; then
    CONTAINER_NAME="youtube-$(basename "$JSON_FILE" .json)"
fi

case $ACTION in
    start)
        # Проверяем, существует ли указанный JSON-файл
        if [ ! -f "$JSON_FILE" ]; then
            echo "❌ Ошибка: Файл $JSON_FILE не найден!"
            exit 1
        fi

        # Проверяем, есть ли запущенный контейнер с таким же именем
        if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
            echo "⚠️  Контейнер $CONTAINER_NAME уже существует. Останавливаю и удаляю..."
            docker stop $CONTAINER_NAME
            sleep 2
            docker rm $CONTAINER_NAME
            sleep 2
        fi


        # Выбор режима запуска
        if [[ "$MODE" == "-d" ]]; then
            echo "🚀 Запускаем контейнер $CONTAINER_NAME в фоновом режиме (detached)"
            docker run -d --name "$CONTAINER_NAME" \
                --network proxy_net \
                --env-file .env \
                -v "$(pwd)/$JSON_FILE:/app/channels_list.json" \
                -v "$(pwd)/logs/:/app/logs/" \
                -v "${STORAGE_ABS_PATH}:${STORAGE_ABS_PATH}" \
                youtube-monitoring-app
        else
            echo "🚀 Запускаем контейнер $CONTAINER_NAME в интерактивном режиме"
            docker run --rm --name "$CONTAINER_NAME" \
                --network proxy_net \
                --env-file .env \
                -v "$(pwd)/$JSON_FILE:/app/channels_list.json" \
                -v "$(pwd)/logs/:/app/logs/" \
                -v "${STORAGE_ABS_PATH}:${STORAGE_ABS_PATH}" \
                youtube-monitoring-app
        fi
        ;;
    
    stop)
        echo "🛑 Останавливаем контейнер $CONTAINER_NAME..."
        docker stop "$CONTAINER_NAME"
        ;;
    
    logs)
        echo "📜 Логи контейнера $CONTAINER_NAME..."
        docker logs -f "$CONTAINER_NAME"
        ;;
    
    restart)
        echo "🔄 Перезапуск контейнера $CONTAINER_NAME..."
        docker stop "$CONTAINER_NAME"
        sleep 2
        docker start "$CONTAINER_NAME"
        ;;
    
    *)
        echo "Usage: $0 {start|stop|logs|restart} [json_file] [-d]"
        echo "Примеры:"
        echo "  $0 start my_channels_list.json          # Запуск в интерактивном режиме"
        echo "  $0 start my_channels_list.json -d      # Запуск в фоновом режиме"
        echo "  $0 stop my_channels_list               # Остановка контейнера"
        echo "  $0 logs my_channels_list               # Просмотр логов"
        echo "  $0 restart my_channels_list            # Перезапуск контейнера"
        exit 1
        ;;
esac
