#!/usr/bin/env python3
"""
Gera series-dominio-publico.m3u8 com uma LISTA FECHADA de séries reconhecidas como domínio público
(seriados de cinema dos anos 1930 e séries/desenhos de TV com episódios cujo copyright caducou).
No archive.org quem envia declara a licença e muitos erram; por isso não basta o selo "public domain".
Séries só parcialmente livres ("parcial") exigem o selo de domínio público em cada episódio.
Cada episódio sai como "Série S01E03 - título", que o LumeStarTV agrupa em série → temporada → episódio.
"""
import os, re, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from comum import busca, um, limpa, excluidos, bloqueado, mp4s, link, capa

SAIDA = "series-dominio-publico.m3u8"
# (nome exibido, busca no título, grupo, parcial)
SERIES = [
    # TV clássica (anos 1950–60): só os episódios marcados como domínio público
    ("Bonanza", "Bonanza", "TV clássica", True),
    ("The Lucy Show", "Lucy Show", "TV clássica", True),
    ("The Beverly Hillbillies", "Beverly Hillbillies", "TV clássica", True),
    ("The Andy Griffith Show", "Andy Griffith", "TV clássica", True),
    ("Petticoat Junction", "Petticoat Junction", "TV clássica", True),
    ("The Jack Benny Program", "Jack Benny", "TV clássica", True),
    ("The George Burns and Gracie Allen Show", "Burns and Allen", "TV clássica", True),
    ("The Adventures of Ozzie and Harriet", "Ozzie and Harriet", "TV clássica", True),
    ("Love That Bob", "Love That Bob", "TV clássica", True),
    ("Dragnet", "Dragnet", "TV clássica", True),
    ("The Cisco Kid", "Cisco Kid", "TV clássica", True),
    ("The Lone Ranger", "Lone Ranger", "TV clássica", True),
    ("Sherlock Holmes (1954)", "Sherlock Holmes 1954", "TV clássica", True),
    ("Four Star Playhouse", "Four Star Playhouse", "TV clássica", True),
    ("Man with a Camera", "Man with a Camera", "TV clássica", True),
    ("One Step Beyond", "One Step Beyond", "TV clássica", True),
    ("Decoy", "Decoy", "TV clássica", True),
    ("Rocky Jones, Space Ranger", "Rocky Jones", "TV clássica", True),
    ("Captain Video", "Captain Video", "TV clássica", True),
    ("Space Patrol", "Space Patrol", "TV clássica", True),
    ("Tom Corbett, Space Cadet", "Tom Corbett", "TV clássica", True),
    # Desenhos clássicos
    ("Superman (Fleischer)", "Superman Fleischer", "Desenhos clássicos", True),
    ("Popeye", "Popeye", "Desenhos clássicos", True),
    ("Betty Boop", "Betty Boop", "Desenhos clássicos", True),
    ("Felix the Cat", "Felix the Cat", "Desenhos clássicos", True),
    ("Casper", "Casper", "Desenhos clássicos", True),
    ("Little Lulu", "Little Lulu", "Desenhos clássicos", True),
    # Seriados de cinema dos anos 1930 (estúdios independentes, domínio público)
    ("The Phantom Creeps", "Phantom Creeps", "Seriados de cinema", False),
    ("The Lost City", "Lost City 1935", "Seriados de cinema", False),
    ("The Return of Chandu", "Return of Chandu", "Seriados de cinema", False),
    ("The Clutching Hand", "Clutching Hand", "Seriados de cinema", False),
    ("The Miracle Rider", "Miracle Rider", "Seriados de cinema", False),
    ("The Phantom Empire", "Phantom Empire", "Seriados de cinema", False),
    ("Shadow of Chinatown", "Shadow of Chinatown", "Seriados de cinema", False),
    ("The Hurricane Express", "Hurricane Express", "Seriados de cinema", False),
    ("The Whispering Shadow", "Whispering Shadow", "Seriados de cinema", False),
    ("The Galloping Ghost", "Galloping Ghost", "Seriados de cinema", False),
    ("The Lightning Warrior", "Lightning Warrior", "Seriados de cinema", False),
    ("Mystery Mountain", "Mystery Mountain", "Seriados de cinema", False),
    ("Burn 'Em Up Barnes", "Burn Em Up Barnes", "Seriados de cinema", False),
    ("Custer's Last Stand", "Custer's Last Stand serial", "Seriados de cinema", False),
    ("The Black Coin", "Black Coin", "Seriados de cinema", False),
    ("Fighting with Kit Carson", "Fighting with Kit Carson", "Seriados de cinema", False),
]
PD = "(licenseurl:*publicdomain* OR licenseurl:*creativecommons*)"
EP_RX = re.compile(r"(?:\bS(\d{1,2})\s*E(\d{1,3})\b|season\s*(\d{1,2}).{0,12}?(?:episode|ep\.?)\s*(\d{1,3})|(?:episode|ep\.?|chapter|cap[ií]tulo|part|#)\s*(\d{1,3}))", re.I)

def numero(texto):
    m = EP_RX.search(texto)
    if not m:
        return None, None
    g = m.groups()
    if g[0]: return int(g[0]), int(g[1])
    if g[2]: return int(g[2]), int(g[3])
    return 1, int(g[4])

def palavras(busca_titulo):
    return [w for w in re.findall(r"[a-z0-9']+", busca_titulo.lower()) if w not in ("the", "of", "and", "serial") and not re.fullmatch(r"19\d\d", w)]

def coleta(item):
    nome, termo, grupo, parcial = item
    ws = palavras(termo)
    q = "mediatype:movies AND " + " AND ".join(f"title:({w})" for w in ws)
    if parcial:
        q += " AND " + PD
    docs = busca(q, 400)
    fora = excluidos()
    eps = []
    logo = ""
    for d in docs:
        titulo = limpa(um(d.get("title")) or d["identifier"])
        if bloqueado(titulo, fora) or re.search(r"\b(trailer|promo|commercial|blooper|documentary|tribute)\b", titulo, re.I):
            continue
        vs = mp4s(d["identifier"])
        if not vs:
            continue
        logo = logo or capa(d["identifier"])
        if len(vs) > 1:  # item com vários episódios: cada arquivo é um episódio
            for i, (base, arq) in enumerate(vs, 1):
                s, e = numero(base.replace("_", " "))
                eps.append((s, e, limpa(base.split("/")[-1].replace("_", " ")), link(d["identifier"], arq)))
        else:
            s, e = numero(titulo)
            resto = re.sub(r"(?i)^.*?" + re.escape(ws[-1]) + r"[^a-z0-9]*", "", titulo) if ws else titulo
            eps.append((s, e, limpa(resto) or titulo, link(d["identifier"], vs[0][1])))
    return nome, grupo, logo, eps

def main():
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(coleta, SERIES))
    linhas, n_series, n_eps = ["#EXTM3U"], 0, 0
    for nome, grupo, logo, eps in res:
        uni, vistos = [], set()
        for ep in eps:
            if ep[3] not in vistos:
                vistos.add(ep[3]); uni.append(ep)
        print(f"{nome}: {len(uni)} episódios")
        if len(uni) < 2:
            continue
        usados = {(s, e) for s, e, _, _ in uni if s and e}
        prox, final = 1, []
        for s, e, t, u in uni:
            if not (s and e) or (s, e) in [(x[0], x[1]) for x in final]:
                while (1, prox) in usados: prox += 1
                s, e = 1, prox
            usados.add((s, e)); final.append((s, e, t, u))
        final.sort()
        n_series += 1
        for s, e, t, u in final:
            extra = f" - {t}" if t and t.lower() != nome.lower() else ""
            rotulo = f"{nome} S{s:02d}E{e:02d}{extra}"[:160]
            linhas.append(f'#EXTINF:-1 tvg-name="{rotulo}" tvg-logo="{logo}" group-title="Séries Domínio Público · {grupo}",{rotulo}')
            linhas.append(u)
            n_eps += 1
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    print(f"séries: {n_series} · episódios: {n_eps}")
    if n_series < 5:
        sys.exit("poucas séries encontradas; lista não atualizada")

if __name__ == "__main__":
    main()
