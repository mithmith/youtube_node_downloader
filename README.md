# Youtube Parser Downloader

## ✨ Overview ✨
Youtube Parser Downloader is an open-source project designed for collecting statistical information about YouTube videos, channel monitoring, downloading videos, audio, subtitles, and thumbnails, as well as implementing a number of additional features such as content localization and editing. This tool is intended for researchers, developers, and anyone interested in analyzing YouTube content and its further use.

## README.md
- 🌐 [English README.md](README.md)
- 🌐 [Русский README.ru.md](README.ru.md)

## DEPENCIES 💡

1. [Docker install](docs/docker_install.md)
2. [Postgres install](docs/postgres_install.md)
3. [PIP install](docs/pip_install.md)
4. [Youtube api install](docs/yt_api_install.md)
5. [YT-DLP install](docs/yt-dlp_install.md)

## Fast INSTALLATION 🚀

1. Download project:
```bash
    git clone https://github.com/mithmith/youtube_node_downloader.git
    cd youtube_node_downloader
```
2. Create file with youtube channel urls `channels_list.json` from `channels_list.json.example`.
3. Install dependencies:
```bash
    sudo pip3 install -r requirements.txt
```
4. Set environment: rename `.env.example` to `.env` and set:
```environment
    TG_BOT_TOKEN=<Your Telegram bot token>
    TG_GROUP_ID=<Your target group ID for posting>
    TG_GROUP_ID=<Your target group ID for posting>
    YOUTUBE_API_KEY=<Your Youtube api key>
    YOUTUBE_SECRET_JSON=<secret json file name from Google API board>
```
5. Run project:
```bash
    python3 -m app
```

## Full INSTALLATION 🔧🚀

The project supports several [installation](docs/INSTALL.md) methods:

1. **Via pip**: A quick way for Python users.
2. **Using Docker**: A convenient way with environment isolation.
3. **Local installation via Python environment**: Full control over dependencies.
4. **Via system service**: For long-term automatic execution.

[A detailed guide for each method is available in INSTALL.md](docs/INSTALL.md).

---

## Features 🚩
- Parsing information about channels and videos through `yt-dlp` and YouTube API.
- Monitoring channels and obtaining new videos.
- Downloading video, audio, subtitles, and thumbnails.
- Video editing, including merging audio tracks and increasing resolution.
- Content localization, including translating descriptions and subtitles.
- Creating subtitles and brief video summaries.
- Integration with Telegram for sending notifications about new and popular videos.
- Mirroring videos on the decentralized hosting Peertube.

---

## How to Help the Project 🧑‍💻
We welcome any help and offer a wide range of tasks for contribution to the project, from programming to documentation. If you want to help, take a look at our [task list](https://github.com/mithmith/peer_node_downloader/blob/main/TODO.md) and choose what you like. We appreciate every contribution!

## Task List
- Gathering information about channels and videos.
- Channel monitoring and statistics.
- Content downloading.
- Video editing and localization.
- Integration with external services such as Telegram and Peertube.

## Join the Development 👥
To start working with the project, please familiarize yourself with our participation guides and code of conduct. We aim to create a welcoming and productive community.

## Contact 🔊
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
