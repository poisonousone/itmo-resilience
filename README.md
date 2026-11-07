# Prompt Injection Detection

Проект по обнаружению промпт-инъекций в пользовательских запросах к LLM методами NLP. Задача — бинарная классификация текста на легитимные запросы (`BENIGN`) и потенциальные промпт-инъекции (`INJECTION`).

## Датасет

[S-Labs/prompt-injection-dataset](https://huggingface.co/datasets/S-Labs/prompt-injection-dataset) — 15 291 англоязычный запрос, два класса, три выборки:

| Выборка | Количество записей |
|---|---:|
| Train | 11 089 |
| Validation | 2 101 |
| Test | 2 101 |

Первичный анализ включает проверку пропусков, дубликатов и распределения классов. Результаты представлены в `notebooks/dataset_statistics.ipynb`.

## Окружение

Debian 13 (Trixie), Python 3.13.5. Зависимости зафиксированы в `requirements.txt`.

Для воспроизведения окружения:

```bash
pip install -r requirements.txt
```

Запуск анализа:

```bash
jupyter lab
```

Notebook: `notebooks/dataset_statistics.ipynb`.

## Структура репозитория

- `data/` — исходные выборки и контрольные суммы SHA256.
- `notebooks/` — исследование данных и визуализация.
- `src/` — код модели.
- `models/` — сохранённые модели.
- `tests/` — тесты.
- `requirements.txt` — зависимости проекта.

Базовая модель: TF-IDF + Logistic Regression.

Обучение:

`python -m src.train`

Тестирование:

`python -m pytest tests/ -v`

Статический анализ:

`python -m bandit -r src/`

Модель сохраняется в `models/baseline.joblib`, метрики — в `metrics/baseline.json`.

Эксперименты и визуализация представлены в `notebooks/baseline.ipynb`.

CI реализован на GitHub Actions и запускается при push, pull request и вручную.

Последовательность проверок:

1. Ruff, Bandit, pytest.
2. Аудит зависимостей pip-audit.
3. Data quality gate: схема, пропуски, метки, объём, баланс классов и SHA256.
4. Model quality gate: F1 класса INJECTION не ниже 95% от baseline.
5. Сборка Docker-образа.
6. Проверка Dockerfile и образа с помощью Trivy.
7. Проверка запуска без root и smoke-тест.

Pipeline прерывается при ошибке обязательной проверки.

Локальные команды:

- `python -m pytest tests/ -q`
- `ruff check src/ tests/`
- `python -m bandit -r src/`
- `pip-audit -r requirements.txt`
- `python -m src.data_gate`
- `python -m src.model_gate`
- `sudo docker build -t ml-project:lab3 .`
- `sudo docker run --rm ml-project:lab3`

Baseline: `metrics/baseline.json`.

Правила проверки данных: `data_policy.json`.

Для демонстрации отказов предусмотрен ручной запуск GitHub Actions с параметрами `data`, `model` или `security`. Режим `none` выполняет обычные проверки.

Сервис реализован на FastAPI

### API

- `POST /predict` — классификация JSON-запроса `{"text": "..."}`.
- `GET /health` — проверка готовности модели.
- `GET /metrics` — метрики Prometheus.
- `GET /` — веб-интерфейс.

Для `/predict` и `/metrics` необходим заголовок `X-API-Key`.

### Ограничения

- Максимальная длина текста — 10 000 символов.
- Максимальный размер HTTP-запроса — 32 КиБ.
- Rate limit — 10 запросов за 60 секунд на IP.
- Параллельные предсказания — 2.
- Тайм-аут ожидания предсказания — 3 секунды.
- Модель загружается при старте после проверки SHA256.

### Локальный запуск

`uvicorn src.app:app --host 127.0.0.1 --port 8000`

Переменная окружения `API_TOKEN` должна содержать секретный токен сервиса.

### Тестирование

`python -m pytest tests/ -v`

### Docker

`sudo docker build -t ml-project:lab4 .`

Контейнер запускается от UID 10001. Токен передаётся через переменную окружения при запуске, а порт публикуется только на loopback.

### Мониторинг

Доступны метрики количества запросов, HTTP-ошибок, причин отказов и времени ответа. Логи выводятся в JSON.

Правило обнаружения: три ответа HTTP 401 для `/predict` с одного адреса за 60 секунд вызывают событие `alert`.

Ограничения реализации: rate limiting и счётчики обнаружения хранятся в памяти одного процесса; при перезапуске сбрасываются. Тайм-аут ожидания не завершает принудительно выполняющийся поток. Для внешнего доступа необходим HTTPS или защищённый SSH-туннель.
