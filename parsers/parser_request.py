# стандратный запрос через браузер, рандомный юзер агент + бесплатный прокси
import random
import time

import requests
from fake_useragent import UserAgent

# Список прокси (добавьте свои рабочие прокси)
PROXIES = [
    None,  # Попробовать без прокси
    {"http": "http://52.201.245.219:20202", "https": "http://52.201.245.219:20202"},
    {"http": "http://99.79.64.51:20201", "https": "http://99.79.64.51:20201"},
]


def get_ip():
    ua = UserAgent()
    headers = {"User-Agent": ua.random}

    try:
        # Проверка IP без прокси
        response = requests.get("https://api.ipify.org", headers=headers, timeout=10)
        print("Ваш реальный IP:", response.text)

        # Проверка IP через прокси (если есть рабочие прокси)
        for proxy in PROXIES[1:]:
            try:
                response = requests.get(
                    "https://api.ipify.org",
                    headers=headers,
                    proxies=proxy,
                    timeout=10,
                )
                print(f"IP через прокси {proxy['http']}:", response.text)
                return proxy  # Возвращаем первый рабочий прокси
            except Exception as e:
                print("Ошибка при проверке IP:", e)
                continue
        return None
    except Exception as e:
        print("Ошибка при проверке IP:", e)
        return None


def get_page(url, proxy=None):
    ua = UserAgent()
    headers = {
        "User-Agent": ua.random,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.avito.ru/",
    }

    time.sleep(random.uniform(2, 5))

    try:
        response = requests.get(
            url,
            headers=headers,
            proxies=proxy,
            timeout=30,
            cookies={"session_id": str(random.randint(100000, 999999))},
        )

        if response.status_code == 200:
            return response.text
        elif response.status_code == 429:
            print("Обнаружена защита от ботов. Попробуйте:")
            print("- Использовать другие прокси")
            print("- Увеличить задержки между запросами")
            print("- Использовать мобильные заголовки")
        return None
    except Exception as e:
        print(f"Ошибка при запросе: {e}")
        return None


def main():
    base_url = "https://www.avito.ru/kirovskaya_oblast_kirov/telefony/mobilnye_telefony/samsung-ASgBAgICAkS0wA2crzmwwQ2I_Dc?cd=1&p="

    # Находим рабочий прокси
    working_proxy = get_ip()

    for page in range(1, 3):
        print(f"\nПарсинг страницы {page}...")
        url = f"{base_url}{page}"

        html = get_page(url, working_proxy)
        if html:
            print(f"Успешно получена страница {page}")
            # Здесь можно парсить HTML
        else:
            print(f"Не удалось получить страницу {page}")

        time.sleep(random.uniform(5, 15))


if __name__ == "__main__":
    main()
