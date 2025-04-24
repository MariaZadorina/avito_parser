FROM python:3.10-slim-buster

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Обновляем pip и устанавливаем Poetry и зависимости
RUN pip install --upgrade pip &&  \
    pip install poetry==1.5.1 &&  \
    poetry config virtualenvs.create false &&  \
    poetry install --no-interaction --no-ansi --only main

# Копируем весь проект
COPY . .

# Открываем порт приложения
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
