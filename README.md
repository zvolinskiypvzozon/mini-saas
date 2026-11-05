# Mini SaaS

![CI](https://github.com/zvolinskiypvzozon/mini-saas/actions/workflows/ci.yml/badge.svg)

Учебный SaaS: организации, пользователи с ролями, проекты, доска задач и файлы в S3. Бэкенд на FastAPI и веб-интерфейс на React.

## Стек
- Бэкенд: FastAPI · PostgreSQL 16 · SQLAlchemy 2 · Alembic · bcrypt · PyJWT · S3 (boto3, MinIO-совместимое хранилище)
- Фронтенд: React 18 · TypeScript · Vite · React Router · nginx
- Инфраструктура: Docker Compose · pytest · moto · Ruff · GitHub Actions

## Запуск

    cp .env.example .env   # задать свои пароли и JWT_SECRET
    docker compose up -d --build
    curl localhost:8080/health

Приложение: http://localhost:8080
Документация API: http://localhost:8001/docs

## Тесты

    ./scripts/test.sh

## Резервное копирование

Сервис `backup` делает дамп PostgreSQL (`pg_dump`, формат custom) при старте и дальше каждые `BACKUP_INTERVAL_HOURS` часов (по умолчанию 24), кладёт его в S3-бакет `backups/appdb/` и удаляет дампы старше `BACKUP_KEEP_DAYS` дней (по умолчанию 7).

    docker compose exec backup backup.sh                    # дамп прямо сейчас
    docker compose exec backup verify.sh                    # развернуть последний дамп во временную базу и сравнить с рабочей
    docker compose exec backup restore.sh latest appdb_copy # восстановить в отдельную базу
    docker compose stop api web                             # восстановить рабочую базу:
    docker compose exec backup restore.sh latest appdb --force
    docker compose start api web

- Бэкап, который ни разу не восстанавливали, — не бэкап: `verify.sh` проверяет, что дамп разворачивается, совпадают список таблиц и версия миграций, и печатает число строк в каждой таблице.
- Рабочую базу `restore.sh` перезаписывает только с `--force`.
- Локально дампы лежат в том же MinIO, что и приложение. В продакшене бакет для бэкапов должен быть в другом хранилище и другом месте (правило 3-2-1), а файлы пользователей — реплицироваться отдельно.

## Архитектура

    браузер ──► web (nginx :8080) ──► статика React
                    │
                    └─ /api/* ──► api (FastAPI :8000) ──► db (PostgreSQL)
                                        │
                                        └──► minio (S3) ◄── скачивание по presigned URL

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

## Фронтенд
- Страницы: вход и регистрация организации, проекты, доска задач (todo / in progress / done), участники проекта, файлы, сотрудники (owner/admin).
- Дизайн-система в три слоя: токены (`src/styles/tokens.css`: цвета, отступы, шрифты, радиусы, тёмная тема) → компоненты (`src/ui.tsx`: Button, Field, Input, Select, Card, Badge, Alert) → страницы. Компоненты используют только токены.
- Все запросы к API идут через один модуль (`src/api.ts`): токен, разбор ошибок FastAPI, выход при 401.
- Сборка в Docker в два этапа: Node собирает статику, в итоговый образ попадает только nginx с готовыми файлами.

## Решения
- Мультиарендность: все данные привязаны к организации, чужие объекты недоступны (404, без раскрытия существования).
- Права доступа собраны в одном модуле (`app/access.py`), маршруты их только вызывают. Скрытие кнопок во фронтенде — только удобство, проверяет права сервер.
- Уникальность и целостность обеспечивает БД: составные ключи, внешние ключи с CASCADE / SET NULL, CHECK-ограничения.
- Дубли проектов ловятся через ограничение БД (IntegrityError → 409), без гонки «проверил — вставил».
- PATCH меняет только присланные поля.
- Фронтенд и API работают с одного адреса через обратный прокси nginx, поэтому CORS не нужен.
- Миграции Alembic применяются при старте контейнера; тесты прогоняют upgrade и downgrade.
- Пароли — bcrypt, одинаковая ошибка для неверного пароля и неизвестного email, UUID вместо числовых id.
- Файлы в S3, в БД только метаданные; скачивание по presigned URL на 5 минут; лимит размера; защита от path traversal.
- Порт PostgreSQL не проброшен наружу; `/health` проверяет и приложение, и базу (503 при недоступности БД).
- CI: Ruff → pytest с PostgreSQL, параллельно проверка типов и сборка фронтенда → сборка Docker-образов API и web.

## Что улучшить
- Токен хранится в localStorage: проще, но уязвимо к XSS. Следующий шаг — HttpOnly cookie и refresh-токены.
- Ограничение частоты попыток входа, заголовки безопасности, HTTPS.
- Бэкапы во внешнее хранилище и резервная копия файлов из S3; оповещение, если бэкап не удался.
