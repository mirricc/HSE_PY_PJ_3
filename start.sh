#!/bin/bash
# Скрипт инициализации БД перед запуском приложения

echo "🔧 Инициализация базы данных..."

python -c "
from database import init_db
print('✅ Создание таблиц...')
init_db()
print('✅ База данных готова!')
"

echo "🚀 Запуск приложения..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
