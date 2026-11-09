#!/usr/bin/env python3
"""
Gera canais-brasil.m3u8: canais de TV aberta do Brasil e canais gratuitos com anúncios em português
(Pluto TV, Samsung TV Plus e similares), a partir do banco aberto do iptv-org, que só reúne transmissões
públicas e tira canais a pedido dos donos. Cada endereço é testado; só entra o que está no ar.
Sem canais adultos.
"""
import json, re, sys, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0 (playlist-canais)"}
API = "https://iptv-org.github.io/api/"
GRUPOS = {  # categoria do iptv-org → grupo no app
    "general": "Abertos", "news": "Notícias", "sports": "Esportes", "kids": "Infantil", "animation": "Infantil",
    "series": "Séries e novelas 24h", "movies": "Filmes 24h", "classic": "Séries e novelas 24h", "comedy": "Séries e novelas 24h",
    "entertainment": "Variedades", "music": "Música", "religious": "Religiosos", "documentary": "Documentários",
    "education": "Educativos", "legislative": "Públicos e legislativos", "public": "Públicos e legislativos",
    "culture": "Cultura", "lifestyle": "Variedades", "cooking": "Variedades", "travel": "Documentários",
    "outdoor": "Documentários", "science": "Documentários", "business": "Notícias", "weather": "Notícias",
    "auto": "Variedades", "family": "Variedades", "shop": None, "xxx": None,
}
# Marcas de canais PAGOS (TV por assinatura): sinal na internet sem login quase sempre é retransmissão sem autorização.
PAGOS = re.compile(r"telecine|espn|eurosport|dazn|\btnt\b|\baxn\b|warner|\btbs\b|cinecanal|\bsony\b|\bamc\b|\bhbo|megapix|premiere|sportv|combate|"
                   r"universal|discovery|history|\ba&e\b|\bfox\b|star channel|cartoon network|disney|nat ?geo|\btlc\b|\bgnt\b|multishow|\bviva\b|"
                   r"canal brasil|\bspace\b|film ?& ?arts|eurochannel|band ?sports|globo|gloob|\boff\b|bis\b|paramount network|lifetime|e! |"
                   r"\bmtv\b(?!.*pluto)|nickelodeon(?!.*pluto)|comedy central(?! pluto)|\bcnn\b|bloomberg|\bdtv\b", re.I)
# Canais gratuitos com anúncios (FAST), que os próprios donos liberam
FAST = re.compile(r"pluto|samsung|rakuten|fifa\+|red bull|moviesphere|cazetv|runtime|plex|xumo|tcl ?channel|lg channels|\bfast\b", re.I)
PAISES_PT = {"BR", "PT", "AO", "MZ", "CV", "ST", "GW", "TL"}

ORDEM = ["Abertos", "Notícias", "Esportes", "Séries e novelas 24h", "Filmes 24h", "Infantil", "Variedades", "Documentários",
         "Cultura", "Educativos", "Música", "Públicos e legislativos", "Religiosos", "Outros"]

def get(nome):
    with urllib.request.urlopen(urllib.request.Request(API + nome, headers=UA), timeout=120) as r:
        return json.load(r)

def chave(n):
    t = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", re.sub(r"\[[^\]]*\]|\([^)]*\)|\b(hd|fhd|sd|4k)\b", " ", t))

def no_ar(url, ua=None, ref=None):
    h = {"User-Agent": ua or UA["User-Agent"]}
    if ref: h["Referer"] = ref
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=10) as r:
            ini = r.read(2048)
            if r.status >= 400: return False
            if ".m3u8" in url or ini[:7] == b"#EXTM3U":
                return b"#EXT" in ini
            return len(ini) > 0
    except Exception:
        return False

def main():
    canais = {c["id"]: c for c in get("channels.json")}
    try: feeds = get("feeds.json")
    except Exception: feeds = []
    streams = get("streams.json")
    try: logos = json.load(open("logos.json", encoding="utf-8"))
    except Exception: logos = {}
    por = {f["channel"] for f in feeds if "por" in (f.get("languages") or [])}
    cand = []
    for s in streams:
        c = canais.get(s.get("channel") or "")
        if not c or c.get("is_nsfw") or c.get("closed"):
            continue
        nome0 = (s.get("title") or c.get("name") or "") + " " + " ".join(c.get("alt_names") or []) + " " + (c.get("network") or "")
        if PAGOS.search(nome0) and not FAST.search(nome0):
            continue
        if c.get("country") not in PAISES_PT and not (c["id"] in por and FAST.search(nome0)):
            continue
        cats = c.get("categories") or []
        if any(GRUPOS.get(k, "x") is None for k in cats):
            continue
        g = next((GRUPOS[k] for k in cats if GRUPOS.get(k)), "Abertos")
        nome = s.get("title") or c.get("name")
        cand.append((g, nome, c, s))
    print(f"candidatos: {len(cand)}")
    with ThreadPoolExecutor(24) as ex:
        ok = list(ex.map(lambda x: no_ar(x[3]["url"], x[3].get("user_agent"), x[3].get("referrer")), cand))
    vistos, saida = set(), []
    for (g, nome, c, s), vivo in zip(cand, ok):
        if not vivo:
            continue
        k = (c["id"], s.get("feed"))
        if k in vistos:
            continue
        vistos.add(k)
        saida.append((g, nome, c, s))
    saida.sort(key=lambda x: (ORDEM.index(x[0]) if x[0] in ORDEM else 99, chave(x[1])))
    linhas = ["#EXTM3U"]
    for g, nome, c, s in saida:
        logo = logos.get(chave(c.get("name", ""))) or logos.get(chave(nome)) or ""
        extra = ""
        if s.get("user_agent"): extra += f' http-user-agent="{s["user_agent"]}"'
        if s.get("referrer"): extra += f' http-referrer="{s["referrer"]}"'
        linhas.append(f'#EXTINF:-1 tvg-id="{c["id"]}" tvg-name="{nome}" tvg-logo="{logo}" group-title="{g}"{extra},{nome}')
        if s.get("user_agent"): linhas.append(f'#EXTVLCOPT:http-user-agent={s["user_agent"]}')
        if s.get("referrer"): linhas.append(f'#EXTVLCOPT:http-referrer={s["referrer"]}')
        linhas.append(s["url"])
    with open("canais-brasil.m3u8", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    from collections import Counter
    print(f"no ar: {len(saida)} de {len(cand)}")
    for g, n in sorted(Counter(x[0] for x in saida).items(), key=lambda x: ORDEM.index(x[0]) if x[0] in ORDEM else 99):
        print(f"  {g}: {n}")
    print("exemplos:", ", ".join(x[1] for x in saida[:25]))
    if len(saida) < 20:
        sys.exit("poucos canais no ar; lista não atualizada")

if __name__ == "__main__":
    main()
