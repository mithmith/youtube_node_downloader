#!/bin/bash

# Ищем PID'ы процессов, в командной строке которых встречается "python -m app"
PIDS=$(ps aux | grep 'python -m app' | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
  echo "Не найдены запущенные процессы python -m app."
  exit 0
fi

echo "Завершаем процессы с PID: $PIDS"
kill -15 $PIDS

# Даём немного времени на корректное завершение процессов
sleep 3

# Проверяем, остались ли процессы в живых
PIDS_STILL_RUNNING=$(ps aux | grep 'python -m app' | grep -v grep | awk '{print $2}')

if [ -z "$PIDS_STILL_RUNNING" ]; then
  echo "Все процессы завершены."
else
  echo "Некоторые процессы всё ещё работают: $PIDS_STILL_RUNNING"
  echo "При необходимости можно принудительно завершить их командой:"
  echo "kill -9 $PIDS_STILL_RUNNING"
fi
