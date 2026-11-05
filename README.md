# Mini SaaS

![CI](https://github.com/zvolinskiypvzozon/mini-saas/actions/workflows/ci.yml/badge.svg)

Учебный SaaS-бэкенд: мультиарендность (организации и пользователи), регистрация и вход по JWT.

## Стек
FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic · bcrypt · PyJWT · Docker Compose · pytest · Ruff · GitHub Actions

## Запуск
```bash
cp .env.example .env   # задать свои пароли и JWT_SECRET
docker compose up -d --build
curl localhost:8001/health
```
Документация API: http://localhost:8001/docs

## Тесты
```bash
./scripts/test.sh
```

## Решения
- Миграции Alembic применяются при старте контейнера (`alembic upgrade head`).
- Пароли хешируются bcrypt, в ответах API хеш не возвращается.
- Одинаковая ошибка для неверного пароля и неизвестного email — защита от перебора адресов.
- UUID вместо числовых id — нельзя перебрать чужие записи.
- Порт PostgreSQL не проброшен наружу; `/health` проверяет и приложение, и базу (503 при недоступности БД).
- CI: Ruff → pytest с PostgreSQL → сборка Docker-образа.
