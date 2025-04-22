import os
import pickle
import random
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Конфигурационные константы
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",  # noqa E501
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",  # noqa E501
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa E501
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa E501
]

PROXY_LIST = [
    None,  # Без прокси
    "http://99.79.64.51:20201",  # Замените на реальные прокси
    "http://13.250.172.255:20202",
]

BASE_URL = "https://m.avito.ru/kirovskaya_oblast_kirov/telefony/mobilnye_telefony/samsung-ASgBAgICAkS0wA2crzmwwQ2I_Dc?cd=1&p="
COOKIES_FILE = "avito_cookies.pkl"
PAGE_RANGE = (1, 2)  # Диапазон страниц для парсинга
DELAY_RANGE = (10, 30)  # Увеличенный диапазон задержек
MAX_RETRIES = 3  # Максимальное количество попыток переподключения
PAGE_LOAD_TIMEOUT = 60  # Увеличенный таймаут ожидания загрузки страницы
ELEMENT_TIMEOUT = 20  # Таймаут ожидания элементов


class AvitoParser:
    def __init__(self, cookies_file=COOKIES_FILE):
        self.cookies_file = cookies_file
        self.current_proxy = None
        self.user_agent = random.choice(USER_AGENTS)
        self.driver = self._init_driver()
        self._load_cookies()

    def _init_driver(self):
        """Инициализация драйвера с увеличенными таймаутами"""
        chrome_options = Options()

        # Настройка User-Agent
        chrome_options.add_argument(f"user-agent={self.user_agent}")

        # Настройка прокси
        if PROXY_LIST and random.random() > 0.5:
            self.current_proxy = random.choice([p for p in PROXY_LIST if p])
            chrome_options.add_argument(f"--proxy-server={self.current_proxy}")

        # Важные параметры для избежания детекта
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Установка размеров окна (может помочь с некоторыми сайтами)
        chrome_options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=chrome_options)

        # Увеличенные таймауты
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(5)  # Неявное ожидание

        return driver

    def _load_cookies(self):
        """Загрузка cookies с обработкой ошибок"""
        if os.path.exists(self.cookies_file):
            try:
                # Загружаем базовую страницу для установки cookies
                self.driver.get("https://m.avito.ru/security/check")

                with open(self.cookies_file, "rb") as f:
                    cookies = pickle.load(f)

                # Устанавливаем только актуальные cookies
                for cookie in cookies:
                    try:
                        if "expiry" in cookie:
                            del cookie["expiry"]
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"Ошибка установки cookie {cookie.get('name')}: {e}")

                print(f"Загружены cookies. User-Agent: {self.user_agent[:50]}...")

            except Exception as e:
                print(f"Ошибка загрузки cookies: {e}")

    def _save_cookies(self):
        """Сохранение cookies с фильтрацией"""
        try:
            cookies = [
                c for c in self.driver.get_cookies() if c.get("domain", "").endswith("avito.ru")
            ]
            with open(self.cookies_file, "wb") as f:
                pickle.dump(cookies, f)
        except Exception as e:
            print(f"Ошибка сохранения cookies: {e}")

    def _is_blocked(self):
        """Проверка на блокировку с улучшенной логикой"""
        try:
            # Проверка по заголовку и тексту страницы
            page_text = self.driver.page_source.lower()
            block_indicators = [
                "доступ временно ограничен",
                "превышено количество запросов",
                "429",
                "403",
                "капча",
                "captcha",
                "blocked",
            ]

            if any(indicator in page_text for indicator in block_indicators):
                return True

            # Проверка наличия элементов блокировки
            block_selectors = [
                '//*[contains(@class, "captcha")]',
                '//*[contains(text(), "доступ ограничен")]',
                '//*[contains(@id, "blocked")]',
            ]

            for selector in block_selectors:
                try:
                    if self.driver.find_element(By.XPATH, selector):
                        return True
                except NoSuchElementException:
                    continue

        except Exception as e:
            print(f"Ошибка при проверке блокировки: {e}")

        return False

    def _reinit_driver(self):
        """Переинициализация драйвера с новыми параметрами"""
        try:
            self.close()

            # Увеличиваем задержку перед повторной попыткой
            delay = random.uniform(15, 45)
            print(f"Ожидание {delay:.1f} сек перед повторной попыткой...")
            time.sleep(delay)

            # Меняем параметры
            self.user_agent = random.choice(USER_AGENTS)
            if PROXY_LIST:
                self.current_proxy = random.choice([p for p in PROXY_LIST if p])
                print(
                    f"Новые параметры: User-Agent={self.user_agent[:50]}..., "
                    f"Proxy={self.current_proxy}",
                )

            self.driver = self._init_driver()

            # Загружаем cookies или базовую страницу
            if not self._load_cookies():
                self.driver.get("https://m.avito.ru")

        except Exception as e:
            print(f"Ошибка при переинициализации драйвера: {e}")
            raise

    def get_page(self, url, retry_count=0):
        """Улучшенный метод получения страницы"""
        if retry_count >= MAX_RETRIES:
            print(f"Достигнуто максимальное количество попыток ({MAX_RETRIES})")
            return None

        try:
            # Динамическая задержка перед запросом
            delay = random.uniform(*DELAY_RANGE)
            print(f"Задержка {delay:.1f} сек перед запросом...")
            time.sleep(delay)

            # Загрузка страницы с явным ожиданием
            self.driver.get(url)

            # Ожидание загрузки контента
            WebDriverWait(self.driver, ELEMENT_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//body")),
            )

            # Проверка на блокировку
            if self._is_blocked():
                print("Обнаружена блокировка. Переинициализация драйвера...")
                self._reinit_driver()
                return self.get_page(url, retry_count + 1)

            return self.driver.page_source

        except TimeoutException:
            print(f"Таймаут при загрузке страницы (попытка {retry_count + 1}/{MAX_RETRIES})")
            self._reinit_driver()
            return self.get_page(url, retry_count + 1)

        except WebDriverException as e:
            print(f"Ошибка WebDriver (попытка {retry_count + 1}/{MAX_RETRIES}): {str(e)[:100]}...")
            self._reinit_driver()
            return self.get_page(url, retry_count + 1)

        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return None

    def close(self):
        """Безопасное закрытие драйвера"""
        try:
            self._save_cookies()
            if hasattr(self, "driver") and self.driver:
                self.driver.quit()
        except Exception as e:
            print(f"Ошибка при закрытии драйвера: {e}")


def main():
    parser = None
    try:
        parser = AvitoParser()

        for page in range(*PAGE_RANGE):
            print(f"\n=== Парсинг страницы {page} ===")
            url = f"{BASE_URL}{page}"

            html = parser.get_page(url)
            if html:
                print(f"Успешно получена страница {page}")
                # Здесь можно добавить обработку HTML
            else:
                print(f"Не удалось получить страницу {page}")
                break  # Прерываем цикл при неудачном запросе

            # Дополнительная задержка между страницами
            if page < PAGE_RANGE[1] - 1:
                delay = random.uniform(20, 60)  # Большая задержка между страницами
                print(f"Пауза {delay:.1f} сек перед следующей страницей...")
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\nПарсинг прерван пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
    finally:
        if parser:
            parser.close()
        print("Парсинг завершен")


if __name__ == "__main__":
    main()
