FROM python:3.12-slim

# Рабочая директория
WORKDIR /app

# Переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование проекта
COPY . .

# Создание директории для БД
RUN mkdir -p /app/data

# Делаем скрипт запуска исполняемым
RUN chmod +x start.sh

# Порт
EXPOSE 8000

# Команда запуска (сначала инициализация БД, потом приложение)
CMD ["./start.sh"]
