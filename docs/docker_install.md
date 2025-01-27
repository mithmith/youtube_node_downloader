# Установка Docker

- [Установка Docker](#установка-docker)
  - [1. **Обновление системы**](#1-обновление-системы)
  - [2. **Удаление старых версий Docker (если установлены)**](#2-удаление-старых-версий-docker-если-установлены)
  - [3. **Установка утилит для работы с HTTPS**](#3-установка-утилит-для-работы-с-https)
  - [4. **Добавление официального репозитория Docker**](#4-добавление-официального-репозитория-docker)
  - [5. **Установка Docker**](#5-установка-docker)
  - [6. **Проверка установки**](#6-проверка-установки)
  - [7. **Настройка прав для работы с Docker без `sudo`**](#7-настройка-прав-для-работы-с-docker-без-sudo)
  - [8. **Проверка работы Docker**](#8-проверка-работы-docker)
  - [9. **Настройка автозапуска Docker**](#9-настройка-автозапуска-docker)
  - [10. **Опционально: Установка Docker Compose**](#10-опционально-установка-docker-compose)

## 1. **Обновление системы**
Перед установкой Docker убедитесь, что ваша система обновлена. Выполните следующие команды:
```bash
sudo apt update
sudo apt upgrade -y
```

---

## 2. **Удаление старых версий Docker (если установлены)**
Если Docker уже был установлен ранее, рекомендуется удалить его перед установкой новой версии:
```bash
sudo apt remove docker docker-engine docker.io containerd runc
```

---

## 3. **Установка утилит для работы с HTTPS**
Для загрузки Docker вам потребуется утилита `curl` и поддержка HTTPS. Установите их:
```bash
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
```

---

## 4. **Добавление официального репозитория Docker**
1. **Импорт ключа GPG Docker:**
   ```bash
   curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
   ```

2. **Добавление репозитория Docker:**
   Определите архитектуру вашей Raspberry Pi и добавьте соответствующий репозиторий. Для ARM (Raspberry Pi) используйте:
   ```bash
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   ```

---

## 5. **Установка Docker**
Теперь обновите списки пакетов и установите последнюю версию Docker:
```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
```

---

## 6. **Проверка установки**
Проверьте, что Docker установлен корректно, с помощью команды:
```bash
sudo docker --version
```
Вы должны увидеть версию Docker, например:
```
Docker version x.x.x, build xxxxxxx
```

---

## 7. **Настройка прав для работы с Docker без `sudo`**
Добавьте текущего пользователя в группу `docker`, чтобы запускать команды без `sudo`:
```bash
sudo usermod -aG docker $USER
```
Для применения изменений выйдите из текущей сессии и зайдите снова:
```bash
exit
```

---

## 8. **Проверка работы Docker**
1. **Запустите тестовый контейнер:**
   ```bash
   docker run hello-world
   ```
   Если все настроено правильно, вы увидите сообщение, что контейнер запущен.

---

## 9. **Настройка автозапуска Docker**
Убедитесь, что Docker настроен на автозапуск при старте системы:
```bash
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 10. **Опционально: Установка Docker Compose**
Для работы с `docker-compose` выполните следующую команду:
```bash
sudo apt install -y docker-compose-plugin
```

Проверьте версию Docker Compose:
```bash
docker compose version
```

---

Теперь Docker установлен и готов к использованию!
