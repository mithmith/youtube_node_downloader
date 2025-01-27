# Установка PostgreSQL в контейнере docker

- [Установка PostgreSQL в контейнере docker](#установка-postgresql-в-контейнере-docker)
  - [1. Создание папки для хранения данных](#1-создание-папки-для-хранения-данных)
  - [2. Запуск PostgreSQL в контейнере](#2-запуск-postgresql-в-контейнере)
    - [2.1 Загрузка образа PostgreSQL](#21-загрузка-образа-postgresql)
      - [1. Использование альтернативных зеркал (mirrors) Docker](#1-использование-альтернативных-зеркал-mirrors-docker)
      - [2. Настройка DNS-сервера](#2-настройка-dns-сервера)
      - [3. Ручная загрузка образов через другой источник](#3-ручная-загрузка-образов-через-другой-источник)
      - [4. Проверка сетевых настроек](#4-проверка-сетевых-настроек)
    - [2.2 Запуск контейнера postgres](#22-запуск-контейнера-postgres)
  - [3. Проверка работы контейнера](#3-проверка-работы-контейнера)
  - [4. Автозапуск контейнера](#4-автозапуск-контейнера)
  - [5. Управление контейнером](#5-управление-контейнером)
  - [6. Опционально: Docker Compose](#6-опционально-docker-compose)


## 1. Создание папки для хранения данных
Для того чтобы данные PostgreSQL сохранялись на хосте, создайте каталог для хранения данных. Например:
```bash
mkdir -p ~/postgres_data
```
Убедитесь, что каталог имеет соответствующие права:
```bash
sudo chmod -R 700 ~/postgres_data
```

---

## 2. Запуск PostgreSQL в контейнере

Перед запуском `docker run` необходимо загрузить образ PostgreSQL. Это можно сделать с помощью команды `docker pull`:

---

### 2.1 Загрузка образа PostgreSQL
Выполните команду, чтобы загрузить последнюю версию образа PostgreSQL:
```bash
docker pull postgres:latest
```

Если вы хотите загрузить конкретную версию PostgreSQL, например, `15`, используйте:
```bash
docker pull postgres:15
```

После загрузки образа убедитесь, что он появился в локальном хранилище:
```bash
docker images
```
Вы должны увидеть образ `postgres` в списке.

---
Если возникает ошибка с доступом к официальному реестру Docker (`https://registry-1.docker.io/v2/`), это обычно связано с DNS-проблемами, блокировками на стороне провайдера или ограничениями сети. В таких случаях можно воспользоваться зеркалами (mirrors) Docker или настроить другой DNS-сервер. Вот несколько решений:

---

#### 1. Использование альтернативных зеркал (mirrors) Docker
Вы можете настроить Docker на использование зеркал вместо стандартного `registry-1.docker.io`. Один из популярных зеркал — это Aliyun (Alibaba Cloud). Для настройки выполните:

1. Создайте (или откройте) файл конфигурации Docker:
   ```bash
   sudo nano /etc/docker/daemon.json
   ```

2. Добавьте или измените содержимое на следующее:
   ```json
   {
     "registry-mirrors": [
       "https://docker.mirrors.ustc.edu.cn",
       "https://mirror.gcr.io",
       "https://hub-mirror.c.163.com",
       "https://registry.docker-cn.com"
     ]
   }
   ```

3. Перезапустите службу Docker:
   ```bash
   sudo systemctl restart docker
   ```

После этого Docker будет использовать альтернативные зеркала для загрузки образов.

---

#### 2. Настройка DNS-сервера
Если проблема вызвана неработающим DNS-сервером, настройте использование общедоступного DNS, например Google DNS (8.8.8.8) или Cloudflare DNS (1.1.1.1):

1. Отредактируйте файл `/etc/resolv.conf`:
   ```bash
   sudo nano /etc/resolv.conf
   ```

2. Замените или добавьте строки:
   ```
   nameserver 8.8.8.8
   nameserver 1.1.1.1
   ```

3. Сохраните изменения и перезапустите Docker:
   ```bash
   sudo systemctl restart docker
   ```

---

#### 3. Ручная загрузка образов через другой источник
Если проблема сохраняется, можно загрузить образы вручную:

1. Найдите образ PostgreSQL на стороннем репозитории, например:
   - [https://registry.aliyuncs.com](https://registry.aliyuncs.com)
   - [https://quay.io](https://quay.io)

2. Используйте URL-адрес альтернативного реестра для загрузки образа. Пример:
   ```bash
   docker pull registry.aliyuncs.com/postgres:latest
   ```

---

#### 4. Проверка сетевых настроек
Если указанные выше методы не помогли, проверьте:

- Есть ли доступ к Интернету на вашем устройстве:
  ```bash
  ping 8.8.8.8
  ```
- Проверьте, не блокируется ли доступ к `https://registry-1.docker.io` файрволом или роутером. Попробуйте использовать VPN для обхода ограничений сети.

---

### 2.2 Запуск контейнера postgres

Используйте команду `docker run`, чтобы запустить контейнер PostgreSQL с указанием следующих параметров:

- **Хранение данных на хосте:** Каталог `~/postgres_data` монтируется в контейнер.
- **Логин/пароль:** Устанавливаем через переменные окружения `POSTGRES_USER` и `POSTGRES_PASSWORD`.
- **Порт:** Перенаправляем порт 5432.
- **Автозапуск:** Добавляем флаг `--restart=always`.

Запустите следующую команду:
```bash
docker run -d \
  --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -v ~/postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  --restart=always \
  postgres:latest
```

---

## 3. Проверка работы контейнера
1. **Убедитесь, что контейнер работает:**
   ```bash
   docker ps
   ```
   Вы должны увидеть контейнер с именем `postgres`.

2. **Проверка подключения к PostgreSQL:**
   Используйте команду `psql` (при наличии) или подключитесь к базе данных через клиентское приложение:
   ```bash
   psql -h 127.0.0.1 -U postgres
   ```
   Пароль: `postgres`.

---

## 4. Автозапуск контейнера
Флаг `--restart=always`, указанный при запуске, гарантирует автоматический перезапуск контейнера при перезагрузке системы. 

Если вы хотите проверить это вручную, перезапустите Docker:
```bash
sudo systemctl restart docker
```
Затем убедитесь, что контейнер снова запущен:
```bash
docker ps
```

---

## 5. Управление контейнером
- **Остановить контейнер:**
  ```bash
  docker stop postgres
  ```

- **Запустить контейнер:**
  ```bash
  docker start postgres
  ```

- **Удалить контейнер (данные останутся):**
  ```bash
  docker rm -f postgres
  ```

- **Создать новый контейнер (данные будут использованы повторно):**
  ```bash
  docker run -d \
    --name postgres \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -v ~/postgres_data:/var/lib/postgresql/data \
    -p 5432:5432 \
    --restart=always \
    postgres:latest
  ```

---

## 6. Опционально: Docker Compose
Для удобства вы можете использовать `docker-compose` для управления PostgreSQL. Создайте файл `docker-compose.yml`:
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:latest
    container_name: postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - ~/postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always
```
Запустите команду:
```bash
docker compose up -d
```

Теперь PostgreSQL настроен и готов к использованию.
