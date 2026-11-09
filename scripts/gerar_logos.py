#!/usr/bin/env python3
"""
Gera logos.json: nome do canal (normalizado) → endereço do logotipo, a partir do banco aberto do iptv-org.
O LumeStarTV baixa este arquivo pequeno uma vez por semana e usa quando o canal da lista não tem tvg-logo.
Só canais do Brasil, Portugal e Estados Unidos (os que aparecem nas listas daqui).
"""
import json, re, sys, unicodedata, urllib.request

UA = {"User-Agent": "playlist-canais/1.0"}
PAISES = {"BR", "PT", "US"}
API = "https://iptv-org.github.io/api/"

def get(nome):
    with urllib.request.urlopen(urllib.request.Request(API + nome, headers=UA), timeout=120) as r:
        return json.load(r)

def chave(nome):
    t = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", t)
    t = re.sub(r"\b(hd|fhd|uhd|sd|4k|h265|hevc|tv hd|ao vivo|alt|backup)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", "", t)

def main():
    canais = get("channels.json")
    try:
        logos = get("logos.json")  # formato novo: lista de {channel, url, width, height, ...}
    except Exception:
        logos = []
    melhor = {}
    for l in logos:
        cid, url = l.get("channel"), l.get("url")
        if not cid or not url or l.get("feed"):
            continue
        area = (l.get("width") or 0) * (l.get("height") or 0)
        if cid not in melhor or area > melhor[cid][0]:
            melhor[cid] = (area, url)
    saida, n = {}, 0
    # Brasil primeiro: em nome repetido, vence o canal brasileiro
    ordem = sorted(canais, key=lambda c: (c.get("country") != "BR", c.get("country") != "PT"))
    for c in ordem:
        if c.get("country") not in PAISES or c.get("closed"):
            continue
        url = (melhor.get(c["id"]) or (0, c.get("logo")))[1]
        if not url:
            continue
        for nome in [c.get("name", "")] + list(c.get("alt_names") or []):
            k = chave(nome)
            if len(k) >= 2 and k not in saida:
                saida[k] = url; n += 1
    with open("logos.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, separators=(",", ":"))
    print(f"canais: {len(canais)} · logos de canais: {len(melhor)} · nomes no arquivo: {n}")
    for teste in ("globo", "sbt", "record", "band", "tvbrasil", "tvcultura", "globonews"):
        print(teste, "→", saida.get(teste, "(não achou)"))
    if n < 200:
        sys.exit("poucos logos; arquivo não atualizado")

if __name__ == "__main__":
    main()
