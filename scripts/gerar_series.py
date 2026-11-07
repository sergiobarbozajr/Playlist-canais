#!/usr/bin/env python3
"""
Gera series-dominio-publico.m3u8 com FONTES FIXAS, escolhidas uma a uma no Internet Archive:
só coleções e episódios marcados como domínio público, de séries reconhecidas como livres
(seriados de cinema dos anos 1930 e séries/desenhos de TV cujo copyright caducou).
Cada episódio sai como "Série S01E03 - título"; o LumeStarTV agrupa em série → temporada → episódio.

Tipos de fonte:
  ("item", id)                      um item com vários vídeos (cada arquivo é um episódio)
  ("capitulos", "id_{n}", 1, 15)    um item por capítulo, numerados
  ("busca", "frase")                itens soltos com o selo de domínio público cujo título começa pela frase
"""
import os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from comum import busca, um, limpa, excluidos, bloqueado, mp4s, link, capa, get

SAIDA = "series-dominio-publico.m3u8"
TV, DES, SER = "TV clássica", "Desenhos clássicos", "Seriados de cinema"
SERIES = [
    ("Bonanza", TV, ("item", "Bonanza_pd")),
    ("The Beverly Hillbillies", TV, ("item", "bevhill-s01e01-36")),
    ("Petticoat Junction", TV, ("item", "petticoatjunction_20170809")),
    ("The George Burns and Gracie Allen Show", TV, ("item", "pdburnsallen")),
    ("The Cisco Kid", TV, ("item", "TheCiscoKidpublicdomain")),
    ("The Lone Ranger", TV, ("item", "theloneranger_201705")),
    ("Sherlock Holmes (1954)", TV, ("item", "SherlockHolmes1954")),
    ("Four Star Playhouse", TV, ("item", "FourStarPlayhouse-48Episodes")),
    ("Man with a Camera", TV, ("item", "manwithacamera_202002")),
    ("Captain Video", TV, ("item", "CaptainVideoMisc4")),
    ("Dragnet", TV, ("busca", "dragnet")),
    ("The Jack Benny Program", TV, ("busca", "jack benny")),
    ("The Adventures of Ozzie and Harriet", TV, ("busca", "ozzie and harriet")),
    ("One Step Beyond", TV, ("busca", "one step beyond")),
    ("Decoy", TV, ("busca", "decoy")),
    ("The Lucy Show", TV, ("busca", "the lucy show")),
    ("Superman (Fleischer)", DES, ("item", "MaxFleischerSuperman")),
    ("Little Lulu", DES, ("item", "littlelulu-publicdomain")),
    ("Popeye", DES, ("busca", "popeye")),
    ("Betty Boop", DES, ("busca", "betty boop")),
    ("Felix the Cat", DES, ("busca", "felix the cat")),
    ("The Phantom Creeps", SER, ("capitulos", "the_phantom_creeps_ep{n}", 1, 12)),
    ("The Lost City", SER, ("item", "TheLostCityall12ChaptersVideoQualityUpgrade")),
    ("The Return of Chandu", SER, ("capitulos", "the_return_of_chandu_chapter_{n}", 1, 12)),
    ("The Clutching Hand", SER, ("capitulos", "clutching_hand_ep{n}", 1, 15)),
    ("The Miracle Rider", SER, ("capitulos", "MiracleRider{n}", 1, 15)),
    ("The Phantom Empire", SER, ("item", "PhantomEmpire1")),
    ("Shadow of Chinatown", SER, ("capitulos", "shadow_of_chinatown_ep{n}", 1, 15)),
    ("The Hurricane Express", SER, ("item", "the-hurricane-express")),
    ("The Whispering Shadow", SER, ("capitulos", "whispering_shadow_ep{n}", 1, 12)),
    ("The Lightning Warrior", SER, ("item", "RTTLW01")),
    ("Burn 'Em Up Barnes", SER, ("capitulos", "burn_em_up_barnes_{n}", 1, 12)),
    ("Fighting with Kit Carson", SER, ("capitulos", "FightingWithKitCarson{n}", 1, 12)),
]
SE_RX = re.compile(r"(?<![a-z0-9])S(\d{1,2})\s*[ ._-]?\s*E(\d{1,3})(?!\d)", re.I)
SOLTO_RX = re.compile(r"(?<![a-z0-9])(\d{1,3})(?![0-9])", re.I)
NUM_RX = re.compile(r"(?:episode|ep\.?|chapter|chap\.?|part|cap[ií]tulo|#)\s*(\d{1,3})", re.I)

def natural(s):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", s)]

def numero(texto, solto=False):
    m = SE_RX.search(texto)
    if m: return int(m.group(1)), int(m.group(2))
    m = NUM_RX.search(texto)
    if m: return 1, int(m.group(1))
    if solto:  # nome de arquivo: "Sherlock Holmes 01 ...", "TLC-01", "Phantom Empire - 1"
        m = SOLTO_RX.search(texto.replace("_", " "))
        if m and 0 < int(m.group(1)) < 300: return 1, int(m.group(1))
        m = re.search(r"(\d{1,3})$", texto)
        if m and 0 < int(m.group(1)) < 300: return 1, int(m.group(1))
    return None, None

def titulo_ep(texto, nome):
    t = texto.replace("_", " ")
    t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t)  # camelCase de arquivo: jedPlaysSolomon → jed Plays Solomon
    t = re.sub(r"\.(ia|mp4)$", "", t, flags=re.I)
    t = SE_RX.sub(" ", t)
    t = re.sub(r"(?i)(the\s+)?" + re.escape(re.sub(r"(?i)^the\s+", "", nome.split(" (")[0])), " ", t)
    t = re.sub(r"(?i)\b(the|ep\.?|episode|chapter|chap|part)\s*\d*\b\s*[-:]?", lambda m: " " if re.search(r"\d", m.group(0)) or m.group(1).lower() != "the" else m.group(0), t)
    t = re.sub(r"\b\d{1,3}\b\s*[-:]?\s*$|^\s*\d{1,3}\s*[-:.]?\s*", " ", t)
    t = limpa(re.sub(r"[_\s]+", " ", t)).strip(" -:'\"")
    return t if len(t) >= 4 and t.lower() not in ("tlc",) else ""

def de_item(nome, ident):
    vs = sorted(mp4s(ident), key=lambda x: natural(x[0]))
    eps = []
    for i, (base, arq) in enumerate(vs, 1):
        arqnome = base.split("/")[-1]
        s, e = numero(arqnome, solto=True)
        eps.append((s, e, titulo_ep(arqnome, nome) or f"Episódio {e or i}", link(ident, arq)))
    return eps, capa(ident)

def de_capitulos(nome, padrao, a, b):
    eps, logo = [], ""
    def um_cap(n):
        ident = padrao.format(n=n)
        try:
            meta = get(f"https://archive.org/metadata/{ident}")
        except Exception:
            return None
        vs = mp4s(ident)
        if not vs:
            return None
        t = um(meta.get("metadata", {}).get("title"))
        resto = re.split(r"(?i)chapter\s*\d+\s*[-:]?\s*", t, maxsplit=1)
        return (1, n, limpa(resto[1]) if len(resto) > 1 else f"Capítulo {n}", link(ident, vs[0][1]), ident)
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(um_cap, range(a, b + 1)):
            if r:
                eps.append(r[:4]); logo = logo or capa(r[4])
    return eps, logo

def de_busca(nome, frase):
    docs = busca(f'mediatype:movies AND title:("{frase}") AND (licenseurl:*publicdomain* OR licenseurl:*creativecommons*)', 200)
    fora = excluidos(); eps, logo, vistos = [], "", set()
    for d in docs:
        t = limpa(um(d.get("title")))
        tl = re.sub(r"^[\s'\"]+", "", t.lower()).replace("_", " ")
        if not (tl.startswith(frase) or tl.startswith("the " + frase)) or bloqueado(t, fora):
            continue
        if re.search(r"\b(trailer|promo|commercial|blooper|documentary|tribute|capcut|tiktok|template)\b", tl):
            continue
        vs = mp4s(d["identifier"])
        if len(vs) != 1:
            continue
        ep = titulo_ep(t, nome) or t
        k = re.sub(r"[^a-z0-9]", "", ep.lower())
        if k in vistos:
            continue
        vistos.add(k)
        s, e = numero(t)
        eps.append((s, e, ep, link(d["identifier"], vs[0][1])))
        logo = logo or capa(d["identifier"])
    return eps, logo

def coleta(item):
    nome, grupo, fonte = item
    try:
        if fonte[0] == "item": eps, logo = de_item(nome, fonte[1])
        elif fonte[0] == "capitulos": eps, logo = de_capitulos(nome, *fonte[1:])
        else: eps, logo = de_busca(nome, fonte[1])
    except Exception as ex:
        print(f"{nome}: erro {ex}"); eps, logo = [], ""
    return nome, grupo, logo, eps

def main():
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(coleta, SERIES))
    linhas, n_series, n_eps = ["#EXTM3U"], 0, 0
    for nome, grupo, logo, eps in res:
        print(f"{nome}: {len(eps)} episódios")
        if len(eps) < 3:
            continue
        # numeração: usa SxxEyy/capítulo quando houver e não repetir; senão a ordem da coleção
        final, usados = [], set()
        for s, e, t, u in eps:
            if s and e and (s, e) not in usados:
                usados.add((s, e)); final.append((s, e, t, u))
        prox = 1
        for s, e, t, u in eps:
            if not (s and e and any(f[3] == u for f in final)):
                while (1, prox) in usados: prox += 1
                usados.add((1, prox)); final.append((1, prox, t, u))
        final.sort(key=lambda x: (x[0], x[1]))
        n_series += 1
        for s, e, t, u in final:
            extra = f" - {t}" if t and t.lower() != nome.lower() else ""
            rotulo = f"{nome} S{s:02d}E{e:02d}{extra}"[:150]
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
