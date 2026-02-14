# Граф знаний: коллекция фильмов и сериалов

Способы использования кода.

---

## Установка

```bash
pip install -r requirements.txt
```

---

## 1. Наполнение графа из TMDb API

Ключ: https://www.themoviedb.org/settings/api

```bash
export TMDB_API_KEY=ваш_ключ
python populate_kg.py --output movies_kg.ttl
```

Свой список фильмов (TMDb movie ID):

```bash
python populate_kg.py --movies 603 155 27205 --output movies_kg.ttl
```

Без сети (данные из локальных JSON в `data/tmdb/movie/`):

```bash
python populate_kg.py --offline --movies 603 155 --output movies_kg.ttl
```

---

## 2. Наполнение графа из IMDb (TSV.gz)

Скачать с https://datasets.imdbws.com/ и положить в `data/imdb/`:

- `title.basics.tsv.gz`
- `name.basics.tsv.gz`
- `title.crew.tsv.gz`
- `title.principals.tsv.gz`
- `title.ratings.tsv.gz` (для отбора по популярности)

Топ 100 фильмов по числу голосов (по умолчанию):

```bash
python populate_kg_imdb.py --imdb-dir data/imdb --output movies_kg.ttl
```

Больше фильмов или другой год:

```bash
python populate_kg_imdb.py --imdb-dir data/imdb --limit 500 --year 1990 --output movies_kg.ttl
```

Только свои фильмы по IMDb id:

```bash
python populate_kg_imdb.py --imdb-dir data/imdb --titles tt0133093,tt0468569,tt1375666 --output movies_kg.ttl
```

---

## 3. Выполнение SPARQL-запросов

По сохранённому графу:

```bash
python run_queries.py movies_kg.ttl
```

Запросы лежат в `sparql_queries/*.rq`.

---

## 4. Визуализация графа

Интерактивный HTML (узлы — фильмы, персоны, жанры; рёбра — «сыграл», «снял», «жанр»):

```bash
pip install pyvis
python visualize_kg.py movies_kg.ttl movies_graph.html
```

Открыть в браузере `movies_graph.html`.

---

## 5. Онтология (Protege)

Файл `ontology/movies_ontology.ttl` — классы Movie, TVSeries, Person, Actor, Director, Genre; свойства title, actedIn, directed, hasGenre и др.

