import json
import re

from app.config import logger


def clean_string(s: str) -> str:
    allowed_chars = r"A-Za-zА-Яа-я0-9_\-"
    return re.sub(rf"[^{allowed_chars}]", "", s)


def load_channels_list(file_path: str = "channels_list.json") -> list[str]:
    """
    Загружает список YouTube-каналов из txt или JSON файла, проверяет валидность, корректирует и удаляет дубликаты.
    """
    patterns = {
        "channel": re.compile(r"^https://www\.youtube\.com/channel/([a-zA-Z0-9_-]+)(/videos)?$"),
        "handle": re.compile(r"^https://www\.youtube\.com/@([a-zA-Z0-9_.-]+)(/videos)?$"),
        "custom": re.compile(r"^https://www\.youtube\.com/c/([a-zA-Z0-9_-]+)(/videos)?$"),
    }

    valid_urls = set()

    try:
        if file_path.endswith(".json"):
            with open(file_path, encoding="utf8") as f:
                data = json.load(f)
                channels = set(data.get("channels", []))
        elif file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as file:
                channels = {line.strip() for line in file if line.strip()}
        else:
            raise ValueError("Неподдерживаемый формат файла. Используйте .json или .txt")

        for url in channels:
            for _, pattern in patterns.items():
                match = pattern.match(url)
                if match:
                    base_url = match.group(0).split("/videos")[0]
                    valid_urls.add(base_url)
                    break
            else:
                if url.startswith("https://www.youtube.com/channel/") and "/videos" not in url:
                    valid_urls.add(url + "/videos")
                elif url.startswith("https://www.youtube.com/@") and "/videos" in url:
                    valid_urls.add(url.replace("/videos", ""))
                else:
                    logger.warning(f"Некорректный URL: {url}")
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
    logger.debug(f"Всего загружено {len(valid_urls)} каналов")
    return sorted(valid_urls)
