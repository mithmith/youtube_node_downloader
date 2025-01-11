# Youtube Parser Downloader

## Overview
Youtube Parser Downloader is an open-source project designed for collecting statistical information about YouTube videos, channel monitoring, downloading videos, audio, subtitles, and thumbnails, as well as implementing a number of additional features such as content localization and editing. This tool is intended for researchers, developers, and anyone interested in analyzing YouTube content and its further use.

## README.md
- English [README.md](https://github.com/mithmith/peer_node_downloader/blob/main/README.md)
- Русский [README.ru.md](https://github.com/mithmith/peer_node_downloader/blob/main/README.ru.md)

## Установка проекта

Проект поддерживает несколько способов установки:

1. **Через pip**: Быстрый способ для пользователей Python.
2. **С использованием Docker**: Удобный способ с изоляцией окружения.
3. **Локальная установка через Python-окружение**: Полный контроль над зависимостями.
4. **Через системный сервис**: Для долгосрочного автоматического выполнения.

Подробное руководство по каждому из способов доступно в [INSTALL.md](docs/INSTALL.md).

---

## Features
- Parsing information about channels and videos through `yt-dlp` and YouTube API.
- Monitoring channels and obtaining new videos.
- Downloading video, audio, subtitles, and thumbnails.
- Video editing, including merging audio tracks and increasing resolution.
- Content localization, including translating descriptions and subtitles.
- Creating subtitles and brief video summaries.
- Integration with Telegram for sending notifications about new and popular videos.
- Mirroring videos on the decentralized hosting Peertube.

---

## How to Help the Project
We welcome any help and offer a wide range of tasks for contribution to the project, from programming to documentation. If you want to help, take a look at our [task list](https://github.com/mithmith/peer_node_downloader/blob/main/TODO.md) and choose what you like. We appreciate every contribution!

## Task List
- Gathering information about channels and videos.
- Channel monitoring and statistics.
- Content downloading.
- Video editing and localization.
- Integration with external services such as Telegram and Peertube.

## Join the Development
To start working with the project, please familiarize yourself with our participation guides and code of conduct. We aim to create a welcoming and productive community.

## Contact
If you have any questions or suggestions, feel free to contact us through [creating an issue](https://github.com/mithmith/peer_node_downloader/issues) in the project repository.

## Used Libraries
The project uses the YouTube API:
https://developers.google.com/youtube/v3/quickstart/python

```
pip install google-api-python-client==2.121.0
pip install google-auth-oauthlib==1.2.0
pip install google-auth-httplib2
```
And also the project `yt-dlp`:
https://github.com/yt-dlp/yt-dlp
