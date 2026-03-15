"""
Скрипт для запуска приложения
"""
import uvicorn
from database import init_db

if __name__ == "__main__":
    # Инициализация базы данных
    print("Инициализация базы данных...")
    init_db()
    print("База данных готова!")
    
    # Запуск сервера
    print("Запуск сервера на http://0.0.0.0:8000")
    print("Документация: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
