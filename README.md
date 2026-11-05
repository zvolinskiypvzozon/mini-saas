# Mini SaaS

![CI](https://github.com/zvolinskiypvzozon/mini-saas/actions/workflows/ci.yml/badge.svg)

Учебный SaaS-бэкенд: организации, пользователи с ролями, проекты, задачи и файлы в S3.

## Стек
FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic · bcrypt · PyJWT · S3 (boto3, MinIO-совместимое хранилище) · Docker Compose · pytest · moto · Ruff · GitHub Actions

## Запуск

    cp .env.example .env   # задать свои пароли и JWT_SECRET
    docker compose up -d --build
    curl localhost:8001/health

Документация API: http://localhost:8001/docs

## Тесты

    ./scripts/test.sh

## Модель данных

    organizations 1──N users
    organizations 1──N files
    organizations 1──N projects
    projects     N──M users   (project_members)
    projects     1──N tasks
    tasks        N──1 users   (assignee)

## Роли

| Действие | owner | admin | member |
| --- | --- | --- | --- |
| Добавлять пользователей | да | да | нет (403) |
| Создавать и удалять проекты, управлять участниками | да | да | нет (403) |
| Видеть проекты | все | все | только свои |
| Работать с задачами | да | да | в своих проектах |

## Решения
- Мультиарендность: все данные привязаны к организации, чужие объекты недоступны (404, без раскрытия существования).
- Права доступа собраны в одном модуле (`app/access.py`), маршруты их только вызывают.
- Уникальность и целостность обеспечивает БД: составные ключи, внешние ключи с CASCADE / SET NULL, CHECK-ограничения.
- Дубли проектов ловятся через ограничение БД (IntegrityError → 409), без гонки «проверил — вставил».
- PATCH меняет только присланные поля.
- Миграции Alembic применяются при старте контейнера; тесты прогоняют upgrade и downgrade.
- Пароли — bcrypt, одинаковая ошибка для неверного пароля и неизвестного email, UUID вместо числовых id.
- Файлы в S3, в БД только метаданные; скачивание по presigned URL на 5 минут; лимит размера; защита от path traversal.
- Порт PostgreSQL не проброшен наружу; `/health` проверяет и приложение, и базу (503 при недоступности БД).
- CI: Ruff → pytest с PostgreSQL → сборка Docker-образа.
