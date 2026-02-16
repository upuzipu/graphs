#!/usr/bin/env python3

import json
import os
import sys
import argparse

import requests
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, XSD

MOVIES = Namespace("http://github.com/upuzipu/movies#")
BASE = Namespace("http://github.com/upuzipu/movies/id/")

TMDB_BASE = "https://api.themoviedb.org/3"


def get_tmdb_key():
    key = os.environ.get("TMDB_API_KEY") or os.environ.get("API_KEY")
    if not key:
        raise SystemExit(
            "Задайте ключ TMDb: export TMDB_API_KEY=your_key\n"
            "Получить ключ: https://www.themoviedb.org/settings/api\n"
            "Или используйте офлайн: python populate_kg.py --offline --data-dir data/tmdb"
        )
    return key


def tmdb_get(api_key: str, path: str, params: dict | None = None) -> dict:
    url = f"{TMDB_BASE}{path}"
    p = {"api_key": api_key, "language": "ru-RU"}
    if params:
        p.update(params)
    r = requests.get(url, params=p, timeout=15)
    r.raise_for_status()
    return r.json()


def load_movie_from_dir(data_dir: str, movie_id: int) -> tuple[dict, dict]:
    base = os.path.join(data_dir, "movie", str(movie_id))
    info_path = f"{base}.json"
    credits_path = f"{base}_credits.json"
    if not os.path.isfile(info_path) or not os.path.isfile(credits_path):
        raise FileNotFoundError(f"Нет файлов {info_path} и/или {credits_path}")
    with open(info_path, encoding="utf-8") as f:
        data = json.load(f)
    with open(credits_path, encoding="utf-8") as f:
        credits = json.load(f)
    return data, credits


def safe_date(s: str | None):
    if not s or len(s) < 10:
        return None
    return s[:10]


def add_movie_from_data(g: Graph, movie_id: int, data: dict, credits: dict) -> None:
    m_uri = BASE[f"movie/{movie_id}"]

    g.add((m_uri, RDF.type, MOVIES.Movie))
    if data.get("title"):
        g.add((m_uri, MOVIES.title, Literal(data["title"], datatype=XSD.string)))
    if data.get("original_title"):
        g.add((m_uri, MOVIES.originalTitle, Literal(data["original_title"], datatype=XSD.string)))
    if data.get("overview"):
        g.add((m_uri, MOVIES.overview, Literal(data["overview"][:500], datatype=XSD.string)))
    if data.get("release_date"):
        d = safe_date(data["release_date"])
        if d:
            g.add((m_uri, MOVIES.releaseDate, Literal(d, datatype=XSD.date)))
    g.add((m_uri, MOVIES.tmdbId, Literal(movie_id, datatype=XSD.integer)))
    if data.get("vote_average") is not None:
        g.add((m_uri, MOVIES.voteAverage, Literal(float(data["vote_average"]), datatype=XSD.decimal)))
    if data.get("popularity") is not None:
        g.add((m_uri, MOVIES.popularity, Literal(float(data["popularity"]), datatype=XSD.decimal)))

    for gen in data.get("genres") or []:
        gid = gen.get("id")
        name = gen.get("name")
        if not gid or not name:
            continue
        g_uri = BASE[f"genre/{gid}"]
        g.add((g_uri, RDF.type, MOVIES.Genre))
        g.add((g_uri, MOVIES.genreName, Literal(name, datatype=XSD.string)))
        g.add((m_uri, MOVIES.hasGenre, g_uri))

    for person in credits.get("crew") or []:
        if person.get("job") != "Director":
            continue
        pid = person.get("id")
        name = person.get("name")
        if not pid or not name:
            continue
        p_uri = BASE[f"person/{pid}"]
        g.add((p_uri, RDF.type, MOVIES.Director))
        g.add((p_uri, MOVIES.personName, Literal(name, datatype=XSD.string)))
        g.add((p_uri, MOVIES.tmdbPersonId, Literal(pid, datatype=XSD.integer)))
        g.add((p_uri, MOVIES.directed, m_uri))

    for i, person in enumerate((credits.get("cast") or [])[:20]):
        pid = person.get("id")
        name = person.get("name")
        character = person.get("character")
        order = person.get("order", i)
        if not pid or not name:
            continue
        p_uri = BASE[f"person/{pid}"]
        g.add((p_uri, RDF.type, MOVIES.Actor))
        g.add((p_uri, MOVIES.personName, Literal(name, datatype=XSD.string)))
        g.add((p_uri, MOVIES.tmdbPersonId, Literal(pid, datatype=XSD.integer)))
        g.add((p_uri, MOVIES.actedIn, m_uri))
        g.add((p_uri, MOVIES.castOrder, Literal(order, datatype=XSD.integer)))


def main():
    parser = argparse.ArgumentParser(description="Наполнение графа знаний из TMDb")
    parser.add_argument(
        "--movies",
        type=int,
        nargs="+",
        default=[603, 155, 27205, 424, 238, 278],
        help="Список TMDb movie ID для загрузки",
    )
    parser.add_argument("--output", default="movies_kg.ttl", help="Файл для сохранения графа (Turtle)")
    parser.add_argument("--offline", action="store_true", help="Не обращаться к API, только локальные JSON")
    parser.add_argument("--data-dir", default="data/tmdb", help="Каталог с movie/{id}.json и movie/{id}_credits.json")
    args = parser.parse_args()

    api_key = None if args.offline else get_tmdb_key()
    data_dir = args.data_dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(data_dir):
        data_dir = os.path.join(script_dir, data_dir)

    g = Graph()

    g.bind("movies", MOVIES)
    g.bind("id", BASE)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    ont_path = os.path.join(script_dir, "ontology", "movies_ontology.ttl")
    if os.path.isfile(ont_path):
        g.parse(ont_path, format="turtle")

    for mid in args.movies:
        print(f"Загружаю фильм TMDb id={mid}...")
        data, credits = None, None
        if args.offline:
            try:
                data, credits = load_movie_from_dir(data_dir, mid)
            except FileNotFoundError as e:
                print(f"  Ошибка: {e}", file=sys.stderr)
                continue
        else:
            try:
                data = tmdb_get(api_key, f"/movie/{mid}")
                credits = tmdb_get(api_key, f"/movie/{mid}/credits")
            except Exception as e:
                print(f"  API недоступен: {e}", file=sys.stderr)
                try:
                    data, credits = load_movie_from_dir(data_dir, mid)
                    print("  Загружено из локального каталога.", file=sys.stderr)
                except FileNotFoundError:
                    continue
        if data and credits:
            add_movie_from_data(g, mid, data, credits)

    out_path = args.output
    g.serialize(destination=out_path, format="turtle", encoding="utf-8")
    print(f"Граф сохранён: {out_path} ({len(g)} триплетов)")


if __name__ == "__main__":
    main()
