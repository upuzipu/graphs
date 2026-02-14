#!/usr/bin/env python3

import os
import sys
from pathlib import Path

from rdflib import Graph

QUERIES_DIR = Path(__file__).resolve().parent / "sparql_queries"


def main():
    kg_path = sys.argv[1] if len(sys.argv) > 1 else "movies_kg.ttl"
    if not os.path.isfile(kg_path):
        print(f"Файл графа не найден: {kg_path}")
        print("Сначала выполните: python populate_kg.py --output movies_kg.ttl")
        sys.exit(1)

    g = Graph()
    g.parse(kg_path, format="turtle")
    print(f"Загружено триплетов: {len(g)}\n")

    rq_files = sorted(Path(QUERIES_DIR).glob("q*.rq"))
    for rq_path in rq_files:
        with open(rq_path, encoding="utf-8") as f:
            query_text = f.read()
        print("=" * 60)
        print(f"Запрос: {rq_path.name}")
        print("=" * 60)
        try:
            result = g.query(query_text)
            rows = list(result)
            if not rows:
                print("(результатов нет)\n")
                continue
            print(" | ".join(str(v) for v in result.vars))
            print("-" * 60)
            for row in rows:
                print(" | ".join(str(v) for v in row))
            print()
        except Exception as e:
            print(f"Ошибка: {e}\n")

    print("Готово.")


if __name__ == "__main__":
    main()
