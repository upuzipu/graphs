#!/usr/bin/env python3

import csv
import gzip
import os
import sys
import argparse
import traceback

from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, XSD

MOVIES = Namespace("http://github.com/upuzipu/movies#")
BASE = Namespace("http://github.com/upuzipu/movies/id/")

NULL = "\\N"
LOG_EVERY_N_ROWS = 100_000


def _null(s: str | None) -> str | None:
    if s is None or s == NULL or s.strip() == "":
        return None
    return s.strip()


def _int(s: str | None):
    s = _null(s)
    if s is None:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _float(s: str | None):
    s = _null(s)
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _genre_uri(genre_name: str):
    slug = genre_name.strip().lower().replace(" ", "-").replace("'", "")
    return BASE[f"genre/{slug}"]


def load_title_basics(imdb_dir: str, title_types: set, min_year: int | None, title_set: set | None) -> dict:
    path = os.path.join(imdb_dir, "title.basics.tsv.gz")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Не найден файл: {path}")
    print(f"  Открыт: {path}", flush=True)
    out = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        n_rows = 0
        for row in reader:
            n_rows += 1
            if n_rows % LOG_EVERY_N_ROWS == 0:
                print(f"  title.basics: прочитано {n_rows} строк, отобрано {len(out)}", flush=True)
            tconst = _null(row.get("tconst"))
            if not tconst:
                continue
            if title_set is not None:
                if tconst not in title_set:
                    continue
            else:
                if row.get("titleType", "").strip() not in title_types:
                    continue
            if row.get("isAdult") == "1":
                continue
            year = _int(row.get("startYear"))
            if min_year is not None and (year is None or year < min_year):
                continue
            genres_str = _null(row.get("genres"))
            genres = [g.strip() for g in (genres_str or "").split(",") if g.strip()] if genres_str else []
            out[tconst] = {
                "titleType": (row.get("titleType") or "").strip(),
                "primaryTitle": _null(row.get("primaryTitle")) or "",
                "originalTitle": _null(row.get("originalTitle")) or "",
                "startYear": year,
                "genres": genres,
            }
    print(f"  title.basics: всего прочитано {n_rows} строк, отобрано {len(out)}", flush=True)
    return out


def load_title_ratings(imdb_dir: str, titles_dict: dict) -> None:
    path = os.path.join(imdb_dir, "title.ratings.tsv.gz")
    if not os.path.isfile(path):
        print("  title.ratings: файл отсутствует, пропуск", flush=True)
        return
    print(f"  Открыт: {path}", flush=True)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        n_rows = 0
        matched = 0
        for row in reader:
            n_rows += 1
            if n_rows % LOG_EVERY_N_ROWS == 0:
                print(f"  title.ratings: прочитано {n_rows} строк, совпадений {matched}", flush=True)
            tconst = _null(row.get("tconst"))
            if not tconst or tconst not in titles_dict:
                continue
            matched += 1
            titles_dict[tconst]["averageRating"] = _float(row.get("averageRating"))
            titles_dict[tconst]["numVotes"] = _int(row.get("numVotes"))
    print(f"  title.ratings: всего прочитано {n_rows} строк, обновлено записей {matched}", flush=True)


def limit_titles_by_votes(titles_dict: dict, limit: int) -> dict:
    if limit is None or len(titles_dict) <= limit:
        return titles_dict
    with_votes = [(t, d.get("numVotes") or 0) for t, d in titles_dict.items()]
    with_votes.sort(key=lambda x: -x[1])
    top = {t: titles_dict[t] for t, _ in with_votes[:limit]}
    return top


def load_title_crew(imdb_dir: str, title_set: set) -> dict:
    path = os.path.join(imdb_dir, "title.crew.tsv.gz")
    if not os.path.isfile(path):
        print("  title.crew: файл отсутствует", flush=True)
        return {}
    print(f"  Открыт: {path}", flush=True)
    out = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        n_rows = 0
        for row in reader:
            n_rows += 1
            if n_rows % LOG_EVERY_N_ROWS == 0:
                print(f"  title.crew: прочитано {n_rows} строк, отобрано {len(out)}", flush=True)
            tconst = _null(row.get("tconst"))
            if not tconst or tconst not in title_set:
                continue
            directors_str = _null(row.get("directors"))
            if not directors_str:
                continue
            out[tconst] = [n.strip() for n in directors_str.split(",") if n.strip()]
    print(f"  title.crew: всего прочитано {n_rows} строк, режиссёры для {len(out)} тайтлов", flush=True)
    return out


def load_title_principals(imdb_dir: str, title_set: set, categories: set) -> list:
    path = os.path.join(imdb_dir, "title.principals.tsv.gz")
    if not os.path.isfile(path):
        print("  title.principals: файл отсутствует", flush=True)
        return []
    print(f"  Открыт: {path}", flush=True)
    out = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        n_rows = 0
        for row in reader:
            n_rows += 1
            if n_rows % LOG_EVERY_N_ROWS == 0:
                print(f"  title.principals: прочитано {n_rows} строк, отобрано {len(out)}", flush=True)
            tconst = _null(row.get("tconst"))
            if not tconst or tconst not in title_set:
                continue
            cat = (row.get("category") or "").strip().lower()
            if cat not in categories:
                continue
            nconst = _null(row.get("nconst"))
            if not nconst:
                continue
            order = _int(row.get("ordering")) or 0
            characters = _null(row.get("characters"))
            out.append((tconst, nconst, order, characters))
    print(f"  title.principals: всего прочитано {n_rows} строк, записей актёров {len(out)}", flush=True)
    return out


def load_name_basics(imdb_dir: str, nconst_set: set) -> dict:
    path = os.path.join(imdb_dir, "name.basics.tsv.gz")
    if not os.path.isfile(path):
        print("  name.basics: файл отсутствует", flush=True)
        return {}
    print(f"  Открыт: {path}", flush=True)
    out = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        n_rows = 0
        for row in reader:
            n_rows += 1
            if n_rows % LOG_EVERY_N_ROWS == 0:
                print(f"  name.basics: прочитано {n_rows} строк, найдено имён {len(out)}", flush=True)
            nconst = _null(row.get("nconst"))
            if not nconst or nconst not in nconst_set:
                continue
            out[nconst] = _null(row.get("primaryName")) or nconst
    print(f"  name.basics: всего прочитано {n_rows} строк, имён {len(out)}", flush=True)
    return out


def build_graph(
    titles_dict: dict,
    crew_dict: dict,
    principals: list,
    names_dict: dict,
    movie_types: set,
) -> Graph:
    g = Graph()
    g.bind("movies", MOVIES)
    g.bind("id", BASE)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    for tconst, info in titles_dict.items():
        is_tv = info.get("titleType") == "tvSeries"
        work_uri = BASE[f"movie/{tconst}"]
        type_class = MOVIES.TVSeries if is_tv else MOVIES.Movie
        g.add((work_uri, RDF.type, type_class))
        g.add((work_uri, MOVIES.imdbId, Literal(tconst, datatype=XSD.string)))
        if info.get("primaryTitle"):
            g.add((work_uri, MOVIES.title, Literal(info["primaryTitle"], datatype=XSD.string)))
        if info.get("originalTitle") and info["originalTitle"] != info.get("primaryTitle"):
            g.add((work_uri, MOVIES.originalTitle, Literal(info["originalTitle"], datatype=XSD.string)))
        year = info.get("startYear")
        if year is not None:
            g.add((work_uri, MOVIES.releaseDate, Literal(f"{year}-01-01", datatype=XSD.date)))
        for genre_name in info.get("genres") or []:
            genre_uri = _genre_uri(genre_name)
            g.add((genre_uri, RDF.type, MOVIES.Genre))
            g.add((genre_uri, MOVIES.genreName, Literal(genre_name, datatype=XSD.string)))
            g.add((work_uri, MOVIES.hasGenre, genre_uri))
        rating = info.get("averageRating")
        if rating is not None:
            g.add((work_uri, MOVIES.voteAverage, Literal(rating, datatype=XSD.decimal)))

    for tconst, nconst_list in crew_dict.items():
        work_uri = BASE[f"movie/{tconst}"]
        if tconst not in titles_dict:
            continue
        for nconst in nconst_list:
            if not nconst:
                continue
            p_uri = BASE[f"person/{nconst}"]
            g.add((p_uri, RDF.type, MOVIES.Director))
            g.add((p_uri, MOVIES.imdbPersonId, Literal(nconst, datatype=XSD.string)))
            name = names_dict.get(nconst) or nconst
            g.add((p_uri, MOVIES.personName, Literal(name, datatype=XSD.string)))
            g.add((p_uri, MOVIES.directed, work_uri))

    for tconst, nconst, order, characters in principals:
        work_uri = BASE[f"movie/{tconst}"]
        if tconst not in titles_dict:
            continue
        p_uri = BASE[f"person/{nconst}"]
        g.add((p_uri, RDF.type, MOVIES.Actor))
        g.add((p_uri, MOVIES.imdbPersonId, Literal(nconst, datatype=XSD.string)))
        name = names_dict.get(nconst) or nconst
        g.add((p_uri, MOVIES.personName, Literal(name, datatype=XSD.string)))
        g.add((p_uri, MOVIES.actedIn, work_uri))
        g.add((p_uri, MOVIES.castOrder, Literal(order, datatype=XSD.integer)))

    return g


def _check_file_open_and_read(imdb_dir: str, filename: str) -> None:
    path = os.path.join(imdb_dir, filename)
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            first = f.readline()
            if not first:
                raise SystemExit(f"Файл пустой или не удалось прочитать: {path}")
    except OSError as e:
        raise SystemExit(f"Не удалось открыть/прочитать файл {path}: {e}")
    except gzip.BadGzipFile as e:
        raise SystemExit(f"Файл не является корректным gzip или повреждён: {path} — {e}")


def _check_imdb_dir(imdb_dir: str) -> None:
    if not os.path.isdir(imdb_dir):
        raise SystemExit(f"Каталог не найден: {imdb_dir}")
    required = ["title.basics.tsv.gz", "name.basics.tsv.gz", "title.crew.tsv.gz", "title.principals.tsv.gz"]
    missing = [f for f in required if not os.path.isfile(os.path.join(imdb_dir, f))]
    if missing:
        raise SystemExit(
            f"В каталоге {imdb_dir} не хватает файлов: {', '.join(missing)}\n"
            "Скачайте с https://datasets.imdbws.com/ и положите в этот каталог."
        )
    print("Проверка открытия и чтения файлов...", flush=True)
    for f in required:
        _check_file_open_and_read(imdb_dir, f)
        print(f"  {f} — ок", flush=True)
    optional = "title.ratings.tsv.gz"
    if os.path.isfile(os.path.join(imdb_dir, optional)):
        _check_file_open_and_read(imdb_dir, optional)
        print(f"  {optional} — ок", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Наполнение графа знаний из IMDb TSV.gz")
    parser.add_argument("--imdb-dir", required=True, help="Каталог с title.basics.tsv.gz, name.basics.tsv.gz и т.д.")
    parser.add_argument("--output", default="movies_kg.ttl", help="Выходной файл графа (Turtle)")
    parser.add_argument(
        "--titles",
        type=str,
        default=None,
        help="Список tconst через запятую (tt0133093,tt0468569). Если задан, --year и --limit игнорируются.",
    )
    parser.add_argument("--year", type=int, default=1990, help="Минимальный год выхода (startYear)")
    parser.add_argument("--limit", type=int, default=100, help="Макс. число фильмов (топ по numVotes), по умолчанию 100")
    parser.add_argument(
        "--types",
        type=str,
        default="movie,tvMovie,tvSeries",
        help="Типы titleType через запятую (movie,tvMovie,tvSeries)",
    )
    args = parser.parse_args()

    imdb_dir = os.path.abspath(args.imdb_dir)
    _check_imdb_dir(imdb_dir)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = args.output if os.path.isabs(args.output) else os.path.join(script_dir, args.output)
    out_path = os.path.normpath(out_path)
    print(f"Выходной файл: {out_path}", flush=True)
    print(f"Каталог: {os.path.dirname(out_path)}", flush=True)

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("# placeholder\n")
        if not os.path.isfile(out_path):
            raise SystemExit(f"Файл не создался: {out_path}")
        print("Проверка записи: файл создан.", flush=True)
    except OSError as e:
        raise SystemExit(f"Не удалось записать в {out_path}: {e}")

    try:
        print("[старт] Парсинг аргументов и подготовка.", flush=True)
        title_types = set(t.strip() for t in args.types.split(",") if t.strip())
        title_set = None
        if args.titles:
            title_set = set(t.strip() for t in args.titles.split(",") if t.strip())
            print(f"Режим: только указанные tconst ({len(title_set)} шт.)", flush=True)
        else:
            print(f"Режим: тип={title_types}, год >={args.year}, лимит={args.limit}", flush=True)

        print("[1/6] Загрузка title.basics...", flush=True)
        titles_dict = load_title_basics(imdb_dir, title_types, args.year if not title_set else None, title_set)
        print(f"  Итого записей: {len(titles_dict)}", flush=True)

        if not titles_dict:
            raise SystemExit("Нет данных для выгрузки. Проверьте --titles, --year и наличие title.basics.tsv.gz.")

        if title_set is None:
            print("[2/6] Загрузка title.ratings...", flush=True)
            load_title_ratings(imdb_dir, titles_dict)
            titles_dict = limit_titles_by_votes(titles_dict, args.limit)
            print(f"  После отбора по numVotes (top {args.limit}): {len(titles_dict)}", flush=True)
        else:
            print("[2/6] title.ratings пропущен (режим --titles).", flush=True)

        title_set = set(titles_dict.keys())

        print("[3/6] Загрузка title.crew...", flush=True)
        crew_dict = load_title_crew(imdb_dir, title_set)
        print(f"  Режиссёры для {len(crew_dict)} тайтлов", flush=True)

        print("[4/6] Загрузка title.principals (actor/actress)...", flush=True)
        principals = load_title_principals(imdb_dir, title_set, {"actor", "actress"})
        print(f"  Записей актёров: {len(principals)}", flush=True)

        nconst_set = set()
        for t, n, _, _ in principals:
            nconst_set.add(n)
        for nconst_list in crew_dict.values():
            nconst_set.update(nconst_list)

        print("[5/6] Загрузка name.basics...", flush=True)
        names_dict = load_name_basics(imdb_dir, nconst_set)
        print(f"  Имён: {len(names_dict)}", flush=True)

        print("[6/6] Построение графа и запись...", flush=True)
        data_graph = build_graph(titles_dict, crew_dict, principals, names_dict, title_types)

        g = Graph()
        g.bind("movies", MOVIES)
        g.bind("id", BASE)
        g.bind("rdf", RDF)
        g.bind("rdfs", RDFS)
        g.bind("xsd", XSD)
        ont_path = os.path.join(os.path.dirname(__file__), "ontology", "movies_ontology.ttl")
        if os.path.isfile(ont_path):
            g.parse(ont_path, format="turtle")
        for triple in data_graph:
            g.add(triple)

        print("Запись файла...", flush=True)
        g.serialize(destination=out_path, format="turtle", encoding="utf-8")
        size = os.path.getsize(out_path) if os.path.isfile(out_path) else 0
        print(f"Граф сохранён: {out_path} ({len(g)} триплетов, размер {size} байт)", flush=True)
        if size == 0:
            print("ВНИМАНИЕ: файл пустой.", flush=True)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
