### Установка YT-DLP

#### 1. Необходимо скачать последнюю версию [yt-dlp](https://github.com/yt-dlp/yt-dlp)
```bash
    cd ~
    wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
```

#### 2. Делаем файл исполняемым:
```bash
    sudo chmod +x ./yt-dlp
```

#### 3. Для работы с yt-dlp необходимо добавить исполняемый файл в PATH, либо скопировать в корень проекта:
```bash
    mv ./yt-dlp ./youtube_node_downloader/
```
