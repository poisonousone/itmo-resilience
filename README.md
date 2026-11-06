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