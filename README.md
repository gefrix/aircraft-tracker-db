# Aircraft Tracker DB

Курсовая работа SkyPro «Проект 3. Поиск информации с подключением БД». Приложение получает географические границы
стран через Nominatim, загружает текущие данные о находящихся в воздухе самолётах из OpenSky и сохраняет снимки в
PostgreSQL. Класс `DBManager` предоставляет все пять аналитических запросов из задания.

## Возможности

- загрузка прямоугольных границ стран из Nominatim;
- получение актуальных воздушных судов из OpenSky;
- автоматическое исключение самолетов, находящихся на земле;
- валидация и нормализация ответов внешних API;
- соблюдение ограничения частоты запросов Nominatim;
- создание таблиц, ограничений и индексов из [`sql/schema.sql`](sql/schema.sql);
- транзакционная загрузка стран и самолетов через `psycopg2`;
- продолжение ETL после ожидаемой ошибки отдельной страны;
- безопасные параметризованные SQL-запросы;
- запуск PostgreSQL одной командой через Docker Compose;
- понятный консольный вывод всех обязательных запросов.

По умолчанию отслеживаются 10 уникальных стран:

1. Canada
2. United States
3. Brazil
4. United Kingdom
5. France
6. Germany
7. Spain
8. Italy
9. Japan
10. Australia

Это одновременно выполняет требование выбрать не менее четырех стран и критерий заполнения таблицы стран минимум
десятью разными значениями.

## Схема базы данных

Таблица `countries` содержит название и четыре координаты границ страны. Таблица `aeroplanes` хранит полный снимок
воздушного судна и связана с `countries` внешним ключом `country_id`.

```text
countries (1) ──────────────── (*) aeroplanes
 id PK                             country_id PK, FK
 name UNIQUE                      icao24 PK
 south_latitude                   callsign
 north_latitude                   origin_country
 west_longitude                   velocity
 east_longitude                   altitude
 updated_at                       longitude / latitude
                                  on_ground / last_contact
                                  updated_at
```

Составной первичный ключ `(country_id, icao24)` позволяет корректно хранить один борт в нескольких пересекающихся
прямоугольниках стран. Ограничения БД проверяют порядок координат и неотрицательную скорость. Для аналитических
запросов созданы индексы по скорости, позывному и стране регистрации.

## Архитектура и SOLID

- **Single Responsibility**: модели, API, конфигурация, запись, чтение, ETL и интерфейс находятся в отдельных
  модулях.
- **Open/Closed**: новый API или тип хранилища добавляется реализацией существующей абстракции без изменения ETL.
- **Liskov Substitution**: `NominatimOpenSkyAPI` и `PostgresRepository` полностью выполняют контракты своих базовых
  классов.
- **Interface Segregation**: `BaseAircraftAPI` и `BaseAircraftRepository` содержат только операции, нужные их
  потребителям.
- **Dependency Inversion**: `AircraftLoader` зависит от абстрактных API и репозитория, а `DBManager` — от внедряемой
  фабрики подключений.

## Структура проекта

```text
aircraft_tracker_db/
├── sql/
│   └── schema.sql
├── src/
│   ├── __init__.py
│   ├── api.py
│   ├── base_api.py
│   ├── base_repository.py
│   ├── config.py
│   ├── db_manager.py
│   ├── exceptions.py
│   ├── models.py
│   ├── repository.py
│   ├── service.py
│   └── user_interface.py
├── tests/
├── .env.example
├── .flake8
├── .gitignore
├── coverage_report.md
├── docker-compose.yml
├── main.py
├── poetry.lock
└── pyproject.toml
```

## Быстрый запуск

Нужны Python 3.12+, Poetry 2.x и Docker Desktop.

```powershell
git clone https://github.com/gefrix/aircraft-tracker-db.git
cd aircraft-tracker-db
Copy-Item .env.example .env
poetry install
docker compose up -d
poetry run python main.py
```

После работы контейнер можно остановить, не удаляя данные:

```powershell
docker compose down
```

Docker Compose создаёт базу `aircraft_tracker`, пользователя `tracker` и постоянный том. Пароль в примере предназначен
только для локальной разработки. Файл `.env` исключён из Git.

Для уже установленного PostgreSQL Docker не нужен. Укажите собственные параметры в `.env`:

```dotenv
PGHOST=localhost
PGPORT=5432
PGDATABASE=aircraft_tracker
PGUSER=tracker
PGPASSWORD=your_password
```

## Работа программы

При запуске приложение:

1. создаёт таблицы и индексы, если они отсутствуют;
2. последовательно получает данные для десяти стран;
3. обновляет снимок самолетов каждой страны в отдельной транзакции;
4. выводит количество самолетов по странам;
5. выводит все воздушные суда;
6. рассчитывает среднюю скорость;
7. выводит самолеты со скоростью выше средней;
8. запрашивает символы для поиска в позывных, например `ACA`.

Документация внешних сервисов:

- [OpenSky REST API](https://openskynetwork.github.io/opensky-api/rest.html)
- [Nominatim API](https://nominatim.org/release-docs/latest/api/Overview/)

## DBManager

```python
from src.config import DatabaseConfig
from src.db_manager import DBManager

config = DatabaseConfig.from_environment()
manager = DBManager(config.connect)

manager.get_countries_and_aeroplanes_count()
manager.get_all_aeroplanes()
manager.get_avg_speed()
manager.get_aeroplanes_with_higher_speed()
manager.get_aeroplanes_with_keyword("ACA")
```

Методы возвращают обычные словари с человекочитаемыми именами полей. Поиск по позывному использует `ILIKE` и
параметр `%s`, поэтому он нечувствителен к регистру и защищён от SQL-инъекций.

## Проверка качества

```powershell
poetry run pytest
poetry run black --check src tests main.py
poetry run isort --check-only src tests main.py
poetry run flake8 src tests main.py
poetry run mypy src main.py
poetry check
```

Результат: **58 тестов**, покрытие функционального кода — **95%**. Полный отчёт находится в
[`coverage_report.md`](coverage_report.md).

Дополнительно 28 сентября 2026 года выполнен интеграционный запуск с реальными API и PostgreSQL 16 в Docker:

- успешно загружены все 10 стран;
- сохранено 18 712 актуальных записей о самолетах;
- все пять методов `DBManager` выполнены на реальной базе;
- поиск по `ACA` вернул только позывные, содержащие этот фрагмент;
- выборка выше средней содержала только скорости больше рассчитанного `AVG`.

Количество самолетов меняется при каждом запуске, поскольку OpenSky возвращает текущее состояние воздушного
пространства.

## Соответствие критериям

| Критерий | Реализация |
|---|---|
| Логическое разделение | API, модели, ETL, запись, запросы, конфигурация и UI разделены по модулям |
| Чистый репозиторий | `.env`, IDE, виртуальное окружение, кэши и отчёт HTML исключены через `.gitignore` |
| Зависимости | Poetry lock-файл; `requests`, `psycopg2-binary`, `python-dotenv` и инструменты качества |
| SOLID | Выполнены все пять принципов, зависимости внедряются через абстракции и фабрики |
| Документация | Docstring присутствует у каждого класса, метода и функции |
| Таблицы | `countries`, `aeroplanes`, FK, ограничения и три индекса |
| Не менее 10 стран | `DEFAULT_COUNTRIES` содержит 10 уникальных значений; интеграционно загружены все 10 |
| Заполнение самолетов | Полный валидированный снимок, транзакция на страну, обновление без устаревших строк |
| JOIN | `LEFT JOIN` сохраняет страны с нулевым количеством самолетов |
| Все самолеты | `INNER JOIN` возвращает страну наблюдения и девять полей воздушного судна |
| AVG | Среднее считается в PostgreSQL только по известным скоростям |
| Выше средней | Сравнение с подзапросом `SELECT AVG(velocity)`, сортировка по скорости DESC |
| Поиск | Параметризованный `ILIKE '%keyword%'`, без учёта регистра |

## GitFlow

- `main` — стабильная версия;
- `develop` — интеграционная ветка;
- `feature/coursework-aircraft-db` — реализация курсовой работы.
