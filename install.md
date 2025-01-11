### Первый способ: запуск через Docker-контейнеры
Этот способ удобен, если вы хотите изолировать окружение и минимизировать настройку зависимостей вручную.

#### Шаг 1: Создание переменных и списка каналов

1. Создайте файл `.env` в корне проекта, если его ещё нет. Заполните файл в соответствии с примером `.env.example`, указав ваши ключи API, настройки Telegram и параметры базы данных.

   Пример `.env`:
   ```env
   YOUTUBE_API_KEY="ваш_ключ_YouTube_API"
   YOUTUBE_SECRET_JSON="client_secret_google.json_file_name"

   TG_BOT_TOKEN="ваш_токен_Telegram_бота"
   TG_GROUP_ID="id_группы_Telegram"
   TG_ADMIN_ID=1234567890

   DB_HOST="localhost"
   DB_PORT=5432
   DB_NAME="peer_tube"
   DB_SCHEMA="youtube"
   DB_USERNAME="postgres"
   DB_PASSWORD="postgres"

   MONITOR_NEW=1
   MONITOR_HISTORY=1
   RUN_TG_BOT=1
   ```

2. Создайте файл `channels_list.json` (переименуйте `channels_list.json.example`) в корне проекта, добавив список YouTube-каналов для мониторинга в формате JSON:

   ```json
    {
        "channels": [
            "https://www.youtube.com/@lexfridman",
            "https://www.youtube.com/@AsmonTV",
            "https://www.youtube.com/@joerogan"
        ]
    }
   ```

---

#### Шаг 2: Установка контейнера PostgreSQL

Запустите PostgreSQL с помощью Docker (если у вас ещё нет PostgreSQL):

```bash
docker run --name postgres-db \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=peer_tube \
    -p 5432:5432 \
    -d postgres:14
```

Эта команда создаёт и запускает контейнер с базой данных.

---

#### Шаг 3: Сборка Docker-образа проекта

1. Соберите Docker-образ с проектом:
   ```bash
   docker build -t youtube-monitoring-app .
   ```
   Эта команда создаст локальный образ из Dockerfile, находящегося в проекте.

2. (Опционально) Или скачать образ с Docker Hub:
   ```bash
   docker pull docker.io/mithmith/youtube-monitoring-app
   ```

---

#### Шаг 4: Запуск проекта

Запустите проектный контейнер с привязкой `.env` и `channels_list.json`:

```bash
docker run --name youtube-monitoring \
    --env-file .env \
    -v $(pwd)/channels_list.json:/app/channels_list.json \
    -p 9191:9191 \
    youtube-monitoring-app
```

- **`--env-file .env`** — указывает файл с переменными окружения.
- **`-v $(pwd)/channels_list.json:/app/channels_list.json`** — монтирует файл со списком каналов.
- **`-p 9191:9191`** — пробрасывает порт для доступа к приложению.

---

#### Шаг 5: Проверка работы сервиса

1. **Посмотреть логи контейнера:**
   ```bash
   docker logs youtube-monitoring
   ```
   Эта команда покажет логи, чтобы проверить, всё ли корректно работает.

2. **Проверить, что контейнер запущен:**
   ```bash
   docker ps
   ```
   Убедитесь, что ваш контейнер `youtube-monitoring` отображается в списке работающих контейнеров.

3. (Опционально) Если нужно зайти внутрь контейнера для диагностики:
   ```bash
   docker exec -it youtube-monitoring /bin/bash
   ```

---

### Второй способ: установка и запуск вручную
Этот способ даёт больше контроля, чем запуск через Docker, и полезен для разработки и отладки проекта.

#### Шаг 1: Скачивание проекта и переход в его папку

1. Клонируйте репозиторий проекта с GitHub:
   ```bash
   git clone https://github.com/mithmith/youtube_node_downloader.git
   ```

2. Перейдите в папку с проектом:
   ```bash
   cd youtube_node_downloader
   ```

---

#### Шаг 2: Создание переменных и списка каналов

1. Создайте файл `.env` в папке с проектом, если его ещё нет. Заполните переменные, указанные в примере `.env.example`.

   Пример `.env`:
   ```env
   YOUTUBE_API_KEY="ваш_ключ_YouTube_API"
   YOUTUBE_SECRET_JSON="client_secret_google.json_file_name"

   TG_BOT_TOKEN="ваш_токен_Telegram_бота"
   TG_GROUP_ID="id_группы_Telegram"
   TG_ADMIN_ID=1234567890

   DB_HOST="localhost"
   DB_PORT=5432
   DB_NAME="peer_tube"
   DB_SCHEMA="youtube"
   DB_USERNAME="postgres"
   DB_PASSWORD="postgres"

   MONITOR_NEW=1
   MONITOR_HISTORY=1
   RUN_TG_BOT=1
   ```

2. Создайте файл `channels_list.json` (переименуйте `channels_list.json.example`) в корне проекта и добавьте туда список YouTube-каналов в формате JSON:

   ```json
    {
        "channels": [
            "https://www.youtube.com/@lexfridman",
            "https://www.youtube.com/@AsmonTV",
            "https://www.youtube.com/@joerogan"
        ]
    }
   ```

---

#### Шаг 3: Установка PostgreSQL

1. Убедитесь, что на вашем компьютере установлен PostgreSQL. Если его нет, установите:

   **На Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   ```

   **На Windows:**
   Скачайте и установите PostgreSQL с официального сайта: https://www.postgresql.org/download/.

2. Создайте базу данных и пользователя для проекта:

   Войдите в консоль PostgreSQL:
   ```bash
   sudo -u postgres psql
   ```

   Выполните команды:
   ```sql
   CREATE DATABASE peer_tube;
   CREATE USER postgres WITH PASSWORD 'postgres';
   GRANT ALL PRIVILEGES ON DATABASE peer_tube TO postgres;
   ```

---

#### Шаг 4: Установка инструментов `poetry` и `alembic`

1. Установите Poetry:
   ```bash
   python3 -m pip install --disable-pip-version-check -U pip wheel poetry
   ```

2. Настройте Poetry:
   ```bash
   poetry config virtualenvs.create false
   ```

3. Установите зависимости проекта:
   ```bash
   poetry install --no-root --no-interaction --no-ansi
   ```

4. Установите Alembic для управления миграциями базы данных:
   ```bash
   python3 -m pip install alembic
   ```

---

#### Шаг 5: Создание таблиц в базе данных

1. Выполните миграции Alembic, чтобы создать все таблицы:
   ```bash
   alembic upgrade head
   ```

---

#### Шаг 6: Запуск проекта

1. Активируйте окружение Poetry:
   ```bash
   poetry shell
   ```

2. Убедитесь, что все зависимости установлены:
   ```bash
   poetry install
   ```

3. Запустите проект:
   ```bash
   python -m app
   ```

---


### Установка с помощью скрипта `install.sh`

1. **Проверка установленных программ**:
   - Скрипт проверяет наличие Python3, pip и PostgreSQL. Если какой-то из них отсутствует, выводится сообщение об ошибке, и скрипт завершает работу.

2. **Установка Poetry и зависимостей**:
   - Poetry устанавливается, обновляется до последней версии и настраивается для работы без виртуального окружения.

3. **Установка Alembic**:
   - Alembic устанавливается через pip.

4. **Миграции базы данных**:
   - Команда `alembic upgrade head` выполняет миграции, создавая все необходимые таблицы.

5. **Запуск проекта**:
   - После всех установок и миграций запускается основной модуль проекта с помощью `python -m app`.

---

#### Использование скрипта

1. Скрипт установки находится в корневой папке проекта `install.sh`.
2. Сделайте его исполняемым:
   ```bash
   chmod +x install.sh
   ```
3. Запустите скрипт:
   ```bash
   ./install.sh
   ```
4. Для запуска проекта после установки:
   ```bash
   python3 -m app
   ```
---

#### Уточнения:

- Скрипт предполагает, что переменные окружения (`.env`) и список каналов (`channels_list.json`) уже созданы.
- PostgreSQL должен быть установлен и настроен вручную, так как это шаг, который остаётся на усмотрение пользователя.
- Для пользователей Windows этот скрипт не будет работать напрямую. Им потребуется WSL (Windows Subsystem for Linux) или эквивалентная среда.

---

### Руководство по настройке и запуску сервиса `youtube-monitoring.service`
Следуя этим шагам, вы сможете настроить и запустить проект как системный сервис.

#### **Шаг 1: Подготовка проекта**
1. Убедитесь, что проект уже скачан:
   ```bash
   git clone https://github.com/mithmith/youtube_node_downloader.git
   cd youtube_node_downloader
   ```

2. Проверьте, что в корне проекта созданы два файла:
   - **`.env`**: Файл с переменными окружения. Если файла нет, создайте его, взяв за основу пример `.env.example`:
     ```bash
     cp .env.example .env
     ```
     Внесите необходимые значения для переменных в `.env`.

   - **`channels_list.json`**: Файл со списком YouTube-каналов. Если файла нет, создайте его:
     ```json
    {
        "channels": [
            "https://www.youtube.com/channel_id_1",
            "https://www.youtube.com/channel_id_2",
            "https://www.youtube.com/channel_id_3"
        ]
    }
     ```
     Возьмите за основу `channels_list.json.example`. Этот файл должен находиться в корне проекта.

---

#### **Шаг 2: Установка зависимостей**
1. Убедитесь, что у вас установлен Python (рекомендуется версия 3.10) и `pip`:
   ```bash
   python3 --version
   ```

2. Перейдите в папку проекта и установите Poetry и зависимости:
   ```bash
   python3 -m pip install --disable-pip-version-check -U pip wheel poetry
   poetry config virtualenvs.create false
   poetry install --no-root --no-interaction --no-ansi
   ```

3. Установите Alembic:
   ```bash
   python3 -m pip install alembic
   ```

---

#### **Шаг 3: Выполнение миграций базы данных**
1. Убедитесь, что PostgreSQL запущен и работает.
2. Проверьте подключение к базе данных, указав параметры из `.env`:
   ```bash
   psql -h localhost -p 5432 -U postgres -d peer_tube
   ```
3. Накатите миграции (создадутся все необходимые таблицы в БД):
   ```bash
   alembic upgrade head
   ```

---

#### **Шаг 4: Настройка файла сервиса**

Создайте файл `youtube-monitoring.service` в корне проекта со следующим содержимым:

```ini
[Unit]
Description=YouTube Monitoring Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/your/project
ExecStart=/usr/bin/python3 -m app
EnvironmentFile=/path/to/your/project/.env
Restart=always
RestartSec=5
User=your_user
Group=your_group

[Install]
WantedBy=multi-user.target
```

1. Обновите значения:
   - `WorkingDirectory`: Укажите полный путь к папке с проектом.
   - `EnvironmentFile`: Укажите полный путь к `.env`.
   - `User` и `Group`: Укажите пользователя и группу, от имени которых будет запускаться сервис.

2. Скопируйте файл сервиса в системную папку:
   ```bash
   sudo cp youtube-monitoring.service /etc/systemd/system/
   ```

3. Проверьте созданный файл сервиса:
   ```bash
   sudo systemctl daemon-reload
   ```

---

#### **Шаг 5: Запуск и активация сервиса**
1. Включите сервис при старте системы:
   ```bash
   sudo systemctl enable youtube-monitoring.service
   ```

2. Запустите сервис:
   ```bash
   sudo systemctl start youtube-monitoring.service
   ```

---

#### **Шаг 6: Проверка работы**
1. Проверьте статус сервиса:
   ```bash
   sudo systemctl status youtube-monitoring.service
   ```
   Вы должны увидеть сообщение, что сервис активен (`Active: active (running)`).

2. Просмотрите логи сервиса:
   ```bash
   sudo journalctl -u youtube-monitoring.service
   ```

3. Если есть ошибки, остановите сервис для устранения:
   ```bash
   sudo systemctl stop youtube-monitoring.service
   ```

---

#### **Примечания**
1. Чтобы обновить проект, останавливайте сервис:
   ```bash
   sudo systemctl stop youtube-monitoring.service
   ```
   Затем выполните обновление:
   ```bash
   git pull
   poetry install
   alembic upgrade head
   sudo systemctl start youtube-monitoring.service
   ```

2. Для управления логами можно указать ротацию в настройках `journalctl` или перенаправить логи в файл, обновив файл сервиса:
   ```ini
   StandardOutput=append:/var/log/youtube-monitoring.log
   StandardError=append:/var/log/youtube-monitoring.log
   ```

---
