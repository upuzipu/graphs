#!/usr/bin/env python3

import os
import sys
from urllib.parse import urlparse

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

MOVIES_NS = "http://github.com/upuzipu/movies#"
BASE_NS = "http://github.com/upuzipu/movies/id/"


def _short_label(uri, g: Graph):
    if not isinstance(uri, URIRef):
        return str(uri)[:30]
    for pred in [MOVIES_NS + "title", MOVIES_NS + "personName", MOVIES_NS + "genreName"]:
        for o in g.objects(uri, URIRef(pred)):
            return (str(o).strip() or uri.split("/")[-1])[:40]
    short = str(uri).replace(BASE_NS, "").replace("movie/", "").replace("person/", "").replace("genre/", "")
    return short[:40] if short else uri.split("/")[-1][:30]


def main():
    kg_path = sys.argv[1] if len(sys.argv) > 1 else "movies_kg.ttl"
    out_html = sys.argv[2] if len(sys.argv) > 2 else "movies_graph.html"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(kg_path):
        kg_path = os.path.join(script_dir, kg_path)
    if not os.path.isabs(out_html):
        out_html = os.path.join(script_dir, out_html)

    if not os.path.isfile(kg_path):
        print(f"Файл не найден: {kg_path}")
        sys.exit(1)

    g = Graph()
    g.parse(kg_path, format="turtle")

    try:
        from pyvis.network import Network
    except ImportError:
        print("Установите pyvis: pip install pyvis")
        sys.exit(1)

    net = Network(height="600px", width="100%", directed=True)
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150)

    added = set()
    MOVIES = URIRef(MOVIES_NS)
    Movie = URIRef(MOVIES_NS + "Movie")
    TVSeries = URIRef(MOVIES_NS + "TVSeries")
    Actor = URIRef(MOVIES_NS + "Actor")
    Director = URIRef(MOVIES_NS + "Director")
    Genre = URIRef(MOVIES_NS + "Genre")
    title = URIRef(MOVIES_NS + "title")
    personName = URIRef(MOVIES_NS + "personName")
    genreName = URIRef(MOVIES_NS + "genreName")
    actedIn = URIRef(MOVIES_NS + "actedIn")
    directed = URIRef(MOVIES_NS + "directed")
    hasGenre = URIRef(MOVIES_NS + "hasGenre")

    def add_node(nid, label, node_type):
        if nid in added:
            return
        added.add(nid)
        color = "#97c2fc" if node_type == "movie" else "#ffb380" if node_type == "person" else "#90EE90"
        net.add_node(nid, label=label, color=color, title=label)

    for s, p, o in g:
        if not isinstance(s, URIRef) or str(p) not in (
            str(actedIn), str(directed), str(hasGenre),
            str(RDF.type), str(title), str(personName), str(genreName),
        ):
            continue
        if p == RDF.type:
            if o == Movie or o == TVSeries:
                lbl = _short_label(s, g)
                add_node(str(s), lbl or str(s), "movie")
            elif o == Actor or o == Director:
                lbl = _short_label(s, g)
                add_node(str(s), lbl or str(s), "person")
            elif o == Genre:
                lbl = _short_label(s, g)
                add_node(str(s), lbl or str(s), "genre")
            continue
        if p == actedIn or p == directed:
            if isinstance(o, URIRef):
                subj_lbl = _short_label(s, g)
                obj_lbl = _short_label(o, g)
                add_node(str(s), subj_lbl or str(s), "person")
                add_node(str(o), obj_lbl or str(o), "movie")
                edge_label = "directed" if p == directed else "actedIn"
                net.add_edge(str(s), str(o), title=edge_label, label=edge_label)
        if p == hasGenre and isinstance(o, URIRef):
            subj_lbl = _short_label(s, g)
            obj_lbl = _short_label(o, g)
            add_node(str(s), subj_lbl or str(s), "movie")
            add_node(str(o), obj_lbl or str(o), "genre")
            net.add_edge(str(s), str(o), title="genre", label="genre")

    net.write_html(out_html)
    print(f"Граф сохранён: {out_html}")
    print("Откройте файл в браузере.")


if __name__ == "__main__":
    main()
