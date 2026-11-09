"""Uso manual: candidatos a filmes/séries livres de 1980 para cá (Wikimedia Commons e Archive)."""
import json, urllib.parse, urllib.request, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from comum import busca, um
UA = {"User-Agent": "playlist-canais/1.0 (github.com/sergiobarbozajr/Playlist-canais)"}
def api(**p):
    p.update(format="json")
    with urllib.request.urlopen(urllib.request.Request("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p), headers=UA), timeout=60) as r:
        return json.load(r)
for cat in ["Open movies", "Blender Foundation films", "Films by Blender Studio", "Creative Commons films", "Free films", "Open content films",
            "Films released under the CC-BY license", "Films released under the CC-BY-SA license", "Brazilian films", "Animated films with free licenses",
            "Feature films", "Short films", "Web series", "Television series"]:
    try:
        d = api(action="query", list="categorymembers", cmtitle="Category:" + cat, cmlimit=60)
        m = [x["title"] for x in d.get("query", {}).get("categorymembers", [])]
        print(f"## {cat}: {len(m)}"); [print("   ", t) for t in m[:60]]
    except Exception as e:
        print("##", cat, "erro", e)
q = ('mediatype:movies AND (year:[1980 TO 2026]) AND (uploader:"blender" OR creator:"Blender Foundation" OR creator:"Blender Studio" OR collection:blender OR subject:"open movie")')
for d in busca(q, 60, ("identifier", "title", "year", "creator", "licenseurl")):
    print("IA |", d["identifier"], "|", um(d.get("year")), "|", um(d.get("creator"))[:30], "|", um(d.get("licenseurl"))[-25:], "|", um(d.get("title"))[:60])
