# Отчёт о покрытии тестами

Дата проверки: 28 сентября 2026 года.

Команда:

```bash
poetry run pytest
```

Результат:

```text
58 passed

Name                     Stmts   Miss  Cover   Missing
------------------------------------------------------
main.py                      5      1    80%   10
src/__init__.py              9      0   100%
src/api.py                  83      9    89%   65-66, 78-79, 89-92, 95
src/base_api.py              7      0   100%
src/base_repository.py       6      0   100%
src/config.py               32      1    97%   40
src/db_manager.py           38      0   100%
src/exceptions.py            5      0   100%
src/models.py               97      3    97%   13, 16-17
src/repository.py           52      3    94%   71-73
src/service.py              29      0   100%
src/user_interface.py       45      4    91%   38-41
------------------------------------------------------
TOTAL                      408     21    95%
```

Фактическое покрытие функционального кода составляет **95%**.
