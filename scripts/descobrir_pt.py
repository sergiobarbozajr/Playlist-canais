"""Uso manual: candidatos a filmes ORIGINALMENTE em português (Brasil/Portugal) até 1955."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from comum import busca, um
q = ('mediatype:movies AND (year:[1890 TO 1955] OR date:[1890-01-01 TO 1955-12-31]) AND '
     '(subject:(brasil OR brazil OR brazilian OR "cinema brasileiro" OR "filme brasileiro" OR "cinema novo" OR portugal OR "cinema português" OR "cinemateca") '
     'OR description:("filme brasileiro" OR "cinema brasileiro" OR "filme português"))')
for d in busca(q, 300, ("identifier", "title", "year", "downloads", "subject")):
    print(f'{d["identifier"]} | {um(d.get("year"))} | {d.get("downloads",0)} | {um(d.get("title"))[:80]}')
