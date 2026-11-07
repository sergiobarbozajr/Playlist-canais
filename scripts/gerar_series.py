#!/usr/bin/env python3
"""
Gera series-dominio-publico.m3u8: séries clássicas de TV, desenhos e seriados de cinema do Internet Archive
com licença aberta declarada (domínio público ou Creative Commons). Cada episódio sai como
"Nome da Série S01E03 - título", que o LumeStarTV agrupa sozinho em série → temporada → episódio.
"""
import json, re, sys, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "playlist-canais/1.0 (gerador de lista de dominio publico)"}
MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 700
SAIDA = "series-dominio-publico.m3u8"
ABERTA = "(licenseurl:*publicdomain* OR licenseurl:*creativecommons*)"
CONSULTAS = [
    ("TV clássica", f"collection:classic_tv AND mediatype:movies AND {ABERTA}"),
    ("Desenhos clássicos", f"collection:classic_cartoons AND mediatype:movies AND {ABERTA}"),
    ("Seriados de cinema", f"mediatype:movies AND (subject:serial OR subject:serials OR title:chapter) AND (collection:feature_films OR collection:moviesandfilms) AND ({ABERTA[1:-1]} OR year:[1890 TO 1930])"),
]
EP_RX = re.compile(r"(?:\bS(\d{1,2})\s*E(\d{1,3})\b|season\s*(\d{1,2}).{0,12}?(?:episode|ep\.?)\s*(\d{1,3})|(?:episode|ep\.?|chapter|cap[ií]tulo|part|#)\s*(\d{1,3}))", re.I)
LIXO_RX = re.compile(r"\s*[\(\[]?\b(19\d\d|20\d\d)\b[\)\]]?|\s*(full episode|complete|public domain|tv series|tv show|episodes?)\b", re.I)

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.load(r)

def um(v):
    return str(v[0] if isinstance(v, list) and v else v or "")

def busca(q):
    p = [("q", q), ("rows", str(MAX)), ("page", "1"), ("output", "json"), ("sort[]", "downloads desc")]
    for f in ("identifier", "title", "year", "subject"):
        p.append(("fl[]", f))
    try:
        return get("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(p))["response"]["docs"]
    except Exception as e:
        print("falha na busca:", e); return []

def videos(ident):
    """Um MP4 por vídeo original do item (prefere H.264), em ordem de nome."""
    try:
        files = get(f"https://archive.org/metadata/{urllib.parse.quote(ident)}").get("files", [])
    except Exception:
        return []
    melhor = {}
    for f in files:
        n, fmt = f.get("name", ""), f.get("format", "")
        if not n.lower().endswith(".mp4"):
            continue
        base = re.sub(r"(\.ia)?(_512kb)?\.mp4$", "", n, flags=re.I)
        nota = 3 if fmt == "h.264" else 1 if "512Kb" in fmt else 2
        if base not in melhor or nota > melhor[base][0]:
            melhor[base] = (nota, n)
    return [(b, n) for b, (_, n) in sorted(melhor.items())]

def limpa(t):
    return re.sub(r"\s+", " ", str(t)).replace(",", " -").replace('"', "'").strip(" -_.")

def numero(texto):
    m = EP_RX.search(texto)
    if not m:
        return None, None
    g = m.groups()
    if g[0]: return int(g[0]), int(g[1])
    if g[2]: return int(g[2]), int(g[3])
    return 1, int(g[4])

def nome_serie(titulo):
    """'The Lucy Show - Lucy Gets Locked In The Vault (Episode 12)' → 'The Lucy Show'."""
    t = re.split(r"\s+[-–:|]\s+|\s+(?:season|episode|ep\.?|chapter|s\d{1,2}e\d)", titulo, maxsplit=1, flags=re.I)[0]
    return limpa(LIXO_RX.sub("", t)) or limpa(titulo)

def main():
    series = defaultdict(lambda: {"eps": [], "grupo": "", "logo": ""})
    for grupo, q in CONSULTAS:
        docs = busca(q)
        print(f"{grupo}: {len(docs)} itens")
        with ThreadPoolExecutor(8) as ex:
            vids = list(ex.map(lambda d: videos(d["identifier"]), docs))
        for d, vs in zip(docs, vids):
            if not vs:
                continue
            ident = d["identifier"]; titulo = limpa(um(d.get("title")) or ident)
            logo = f"https://archive.org/services/img/{urllib.parse.quote(ident)}"
            if len(vs) > 1:  # item com a série inteira: cada arquivo é um episódio
                nome = nome_serie(titulo)
                for i, (base, arq) in enumerate(vs, 1):
                    s, e = numero(base.replace("_", " "))
                    ep_titulo = limpa(base.split("/")[-1].replace("_", " "))
                    series[nome]["eps"].append((s or 1, e or i, ep_titulo, f"https://archive.org/download/{urllib.parse.quote(ident)}/{urllib.parse.quote(arq)}"))
            else:  # item de um episódio só: agrupa pelo nome da série no título
                nome = nome_serie(titulo)
                s, e = numero(titulo)
                ep_titulo = limpa(titulo[len(nome):]) if titulo.lower().startswith(nome.lower()) else titulo
                series[nome]["eps"].append((s or 0, e or 0, ep_titulo, f"https://archive.org/download/{urllib.parse.quote(ident)}/{urllib.parse.quote(vs[0][1])}"))
            series[nome]["grupo"] = series[nome]["grupo"] or grupo
            series[nome]["logo"] = series[nome]["logo"] or logo

    linhas, n_series, n_eps = ["#EXTM3U"], 0, 0
    for nome in sorted(series, key=str.lower):
        info = series[nome]
        eps, vistos = [], set()
        for ep in info["eps"]:
            if ep[3] not in vistos:
                vistos.add(ep[3]); eps.append(ep)
        if len(eps) < 2 or len(nome) < 3:
            continue  # um episódio solto não vira série
        # episódios sem número recebem a próxima posição livre, na ordem em que vieram
        usados = {(s, e) for s, e, _, _ in eps if s and e}
        prox = 1; final = []
        for s, e, t, u in eps:
            if not (s and e):
                while (1, prox) in usados: prox += 1
                s, e = 1, prox; usados.add((s, e))
            final.append((s, e, t, u))
        final.sort()
        n_series += 1
        for s, e, t, u in final:
            extra = f" - {t}" if t and t.lower() != nome.lower() else ""
            rotulo = f"{nome} S{s:02d}E{e:02d}{extra}"[:160]
            linhas.append(f'#EXTINF:-1 tvg-name="{rotulo}" tvg-logo="{info["logo"]}" group-title="Séries Domínio Público · {info["grupo"]}",{rotulo}')
            linhas.append(u)
            n_eps += 1
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    print(f"séries: {n_series} · episódios: {n_eps}")
    if n_series < 5:
        sys.exit("poucas séries encontradas; lista não atualizada")

if __name__ == "__main__":
    main()
