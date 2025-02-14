#!/bin/bash

command -v proxychains >/dev/null 2>&1 || { echo >&2 "proxychains не установлен!"; exit 1; }

set -e  # Скрипт будет выходить при ошибках

APP_CMD="python -m app"
LOG_DIR="./logs"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="log_${DATE}.log"

mkdir -p "$LOG_DIR"
echo "Запускаем: $APP_CMD"
nohup proxychains $APP_CMD > "$LOG_DIR/$LOG_FILE" 2>&1 &
PID=$!

echo "Процесс запущен (PID=$PID). Лог: $LOG_DIR/$LOG_FILE"
