#!/usr/bin/env python3
"""
Gera livres-1980.m3u8: filmes e séries de 1980 para cá com licença aberta DADA PELOS PRÓPRIOS AUTORES
(Creative Commons). Lista fechada de títulos conhecidos; para cada um, a melhor cópia no Internet Archive
com a licença aberta declarada, preferindo até 1080p (4K pesa sem necessidade na maioria das TVs).
"""
import os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from comum import busca, um, mp4s, link, capa, get

SAIDA = "livres-1980.m3u8"
LIC = "(licenseurl:*creativecommons* OR licenseurl:*publicdomain*)"
# (nome exibido, busca no título, ano, grupo)
FILMES = [
    ("Big Buck Bunny", "big buck bunny", 2008, "Animação"),
    ("Elephants Dream", "elephants dream", 2006, "Animação"),
    ("Sintel", "sintel", 2010, "Animação"),
    ("Tears of Steel", "tears of steel", 2012, "Ficção científica"),
    ("Cosmos Laundromat", "cosmos laundromat", 2015, "Animação"),
    ("Glass Half", "glass half", 2015, "Animação"),
    ("Caminandes 1: Llama Drama", "caminandes llama drama", 2013, "Animação"),
    ("Caminandes 2: Gran Dillama", "caminandes gran dillama", 2013, "Animação"),
    ("Caminandes 3: Llamigos", "caminandes llamigos", 2016, "Animação"),
    ("Agent 327: Operation Barbershop", "agent 327", 2017, "Animação"),
    ("Hero", "hero blender open movie", 2018, "Animação"),
    ("Spring", "spring blender", 2019, "Animação"),
    ("Coffee Run", "coffee run", 2020, "Animação"),
    ("Sprite Fright", "sprite fright", 2021, "Animação"),
    ("Charge", "charge blender", 2022, "Ação"),
    ("Wing It!", "wing it", 2023, "Animação"),
    ("Sita Sings the Blues", "sita sings the blues", 2008, "Animação"),
    ("Star Wreck: In the Pirkinning", "star wreck pirkinning", 2005, "Ficção científica"),
    ("Valkaama", "valkaama", 2010, "Aventura"),
    ("Nasty Old People", "nasty old people", 2009, "Drama"),
    ("Route 66: An American Bad Dream", "route 66 american bad dream", 2008, "Documentários"),
    ("The Cosmonaut", "the cosmonaut", 2013, "Ficção científica"),
    ("Iron Sky Signal", "iron sky signal", 2009, "Ficção científica"),
]
SERIES = [
    ("Pioneer One", "pioneer one", 2010, "Séries"),
]

def escolher(termo, ano):
    ws = [w for w in re.findall(r"[a-z0-9']+", termo.lower()) if w not in ("the", "of")]
    q = "mediatype:movies AND " + " AND ".join(f"title:({w})" for w in ws) + " AND " + LIC
    docs = busca(q, 25, ("identifier", "title", "year", "downloads", "licenseurl"))
    def nota(d):
        i = d["identifier"].lower() + " " + um(d.get("title")).lower()
        pen = 3 if re.search(r"4k|8k|2160|y4m|uhd|stereo|3d|dvd|blu-?ray|making|trailer|teaser", i) else 0
        return (pen, -int(d.get("downloads") or 0))
    for d in sorted(docs, key=nota):
        v = mp4s(d["identifier"])
        if v:
            return d, v
    return None, []

def main():
    linhas = ["#EXTM3U"]; n = 0
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda f: (f, escolher(f[1], f[2])), FILMES + SERIES))
    for (nome, _, ano, grupo), (d, v) in res:
        if not d:
            print("sem cópia livre:", nome); continue
        serie = (nome, _, ano, grupo) in SERIES
        if serie and len(v) > 1:
            for i, (base, arq) in enumerate(v, 1):
                linhas.append(f'#EXTINF:-1 tvg-logo="{capa(d["identifier"])}" group-title="Livres · Séries",{nome} S01E{i:02d}')
                linhas.append(link(d["identifier"], arq))
        else:
            linhas.append(f'#EXTINF:-1 tvg-name="{nome} ({ano})" tvg-logo="{capa(d["identifier"])}" group-title="Livres · {grupo}",{nome} ({ano})')
            linhas.append(link(d["identifier"], v[0][1]))
        n += 1
        print("ok:", nome, "←", d["identifier"], "|", um(d.get("licenseurl"))[-30:], "|", len(v), "vídeo(s)")
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    print("títulos:", n)
    if n < 8:
        sys.exit("poucos títulos; lista não atualizada")

if __name__ == "__main__":
    main()
