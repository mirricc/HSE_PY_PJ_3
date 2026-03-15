# URL Shortener API

Сервис для сокращения ссылок с аналитикой и управлением.
##  Возможности
![alt text](https://github.com/mirricc/smth/blob/6fa36635608d4e466368c552479ebed0b30baf41/1.jpg)
![alt text](https://github.com/mirricc/smth/blob/6fa36635608d4e466368c552479ebed0b30baf41/2.jpg)
![alt text](https://github.com/mirricc/smth/blob/6fa36635608d4e466368c552479ebed0b30baf41/3.jpg)
![alt text](https://github.com/mirricc/smth/blob/6fa36635608d4e466368c552479ebed0b30baf41/4.jpg)
![alt text](https://github.com/mirricc/smth/blob/6fa36635608d4e466368c552479ebed0b30baf41/5.jpg)
### Обязательные функции:
-  `POST /links/shorten` – создание короткой ссылки
-  `GET /links/{short_code}` – перенаправление на оригинальный URL
-  `DELETE /links/{short_code}` – удаление связи
-  `PUT /links/{short_code}` – обновление URL
-  `GET /links/{short_code}/stats` – статистика по ссылке
-  Кастомные алиасы (уникальный alias)
-  Поиск по оригинальному URL: `GET /links/search?original_url={url}`
-  Время жизни ссылки (`expires_at`)

### Дополнительные функции:
-  Удаление неиспользуемых ссылок (после N дней без активности)
-  История истекших ссылок
-  Группировка ссылок по проектам
-  Создание ссылок для незарегистрированных пользователей

### Регистрация и аутентификация:
-  Регистрация: `POST /auth/register`
-  Вход: `POST /auth/login`
-  Изменение/удаление только для авторизованных пользователей

##  Структура проекта

```
FastAPI_url_shortener/
├── main.py           # Основное приложение FastAPI
├── models.py         # SQLAlchemy модели
├── schemas.py        # Pydantic схемы
├── crud.py           # Функции для работы с БД
├── auth.py           # Аутентификация и JWT
├── cache.py          # Redis кэширование
├── database.py       # Подключение к БД
├── config.py         # Конфигурация
├── requirements.txt  # Зависимости
└── .env.example      # Пример переменных окружения
```

##  Установка

### Вариант 1: Локальный запуск

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка Redis (опционально, для кэширования)

**Windows:**
- Скачайте Redis для Windows: https://github.com/microsoftarchive/redis/releases
- Или используйте Docker:
```bash
docker run -d -p 6379:6379 redis:latest
```

**Без Redis:** Сервис будет работать, но без кэширования статистики.

### 3. Запуск сервера

```bash
# Инициализация БД и запуск
python run.py
```

Или напрямую:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

### Вариант 2: Docker Compose (рекомендуется)

### 1. Запуск всех сервисов

```bash
docker-compose up -d
```

### 2. Проверка логов

```bash
docker-compose logs -f
```

### 3. Остановка

```bash
docker-compose down
```

**Сервисы:**
- **App:** http://localhost:8000
- **Redis:** localhost:6379

**Данные сохраняются в volumes:**
- `app_data` — база данных SQLite
- `redis_data` — данные Redis

##  API Endpoints

### Auth
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/auth/register` | Регистрация пользователя |
| POST | `/auth/login` | Вход (получение токена) |
| GET | `/auth/me` | Информация о пользователе |

### Links
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/links/shorten` | Создание короткой ссылки |
| GET | `/links/{short_code}` | Редирект на оригинал |
| DELETE | `/links/{short_code}` | Удаление ссылки |
| PUT | `/links/{short_code}` | Обновление ссылки |
| GET | `/links/{short_code}/stats` | Статистика |
| GET | `/links/search?original_url=` | Поиск по URL |
| GET | `/links/my` | Мои ссылки |

### Projects
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/projects` | Создание проекта |
| GET | `/projects` | Мои проекты |

### Admin
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/admin/cleanup/expired` | Удаление истекших ссылок |
| POST | `/admin/cleanup/unused` | Удаление неиспользуемых |
| GET | `/admin/history/expired` | История истекших |
| GET | `/admin/popular` | Популярные ссылки |

##  Примеры использования

### Регистрация
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
```

### Вход
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "password123"}'
```

### Создание короткой ссылки
```bash
curl -X POST "http://localhost:8000/links/shorten" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com/very/long/url"}'
```

### С кастомным алиасом
```bash
curl -X POST "http://localhost:8000/links/shorten" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com", "custom_alias": "mylink"}'
```

### С временем жизни
```bash
curl -X POST "http://localhost:8000/links/shorten" \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com", "expires_at": "2026-04-01T00:00:00"}'
```

### Получение статистики
```bash
curl "http://localhost:8000/links/{short_code}/stats"
```

##  База данных

Используется **SQLite** для хранения:
- Пользователи
- Короткие ссылки
- Проекты (группировка)
- История истекших ссылок

##  Кэширование

**Redis** + **fastapi-cache2** используется для:
- Кэширования статистики ссылок (`GET /links/{short_code}/stats`)
- Автоматическая инвалидация по TTL

Кэш ускоряет ответы API и снижает нагрузку на БД.

##  Документация

После запуска сервера доступна интерактивная документация:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

##  Docker

### Быстрый старт с Docker

```bash
# Запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f app

# Остановка
docker-compose down

# Остановка с удалением данных
docker-compose down -v
```

### Сборка образа вручную

```bash
docker build -t url-shortener .
docker run -p 8000:8000 --env-file .env.docker url-shortener
```

### Переменные окружения

Создайте файл `.env` на основе `.env.docker`:

```bash
cp .env.docker .env
```

**Важно:** Измените `SECRET_KEY` в production!
