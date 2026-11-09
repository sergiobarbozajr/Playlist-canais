#!/usr/bin/env python3
"""
Gera portugues.m3u8: cinema brasileiro e português ORIGINALMENTE falado em português, publicado até 1955,
do Internet Archive. Pela lei brasileira (Lei 9.610/98, art. 44) a obra audiovisual entra em domínio público
70 anos depois de 1º de janeiro do ano seguinte à publicação: até 1955 está livre em 2026.
Fica de fora: versões dubladas/legendadas (dublagem e tradução têm direitos próprios), cinejornais estrangeiros,
propagandas e filmes de estúdios estrangeiros.
"""
import os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from comum import busca, um, limpa, excluidos, bloqueado, chave, mp4s, link, capa

SAIDA = "portugues.m3u8"
Q = ('mediatype:movies AND (year:[1890 TO 1955] OR date:[1890-01-01 TO 1955-12-31]) AND '
     '(subject:(brasil OR brazil OR brazilian OR "cinema brasileiro" OR "filme brasileiro" OR "cinema novo" OR portugal OR "cinema português" OR cinemateca) '
     'OR description:("filme brasileiro" OR "cinema brasileiro" OR "filme português"))')
FORA_ID = re.compile(r"^(upenn-|NPC-|ADC-|ARC-|FB-|EF-|fv-|FILME[A-Z]+-)", re.I)
FORA_TIT = re.compile(r"(?i)\b(brazil at war|medley|gets the news|good neighbor|mediterranean|cruise|trinidad|europe|foreign cities|highways of|primitive peoples|"
                      r"march of time|amazon awakens|missions collection|saludos amigos|looney|disney|dublad|legendad|dual|newsreel|propaganda|lojas|"
                      r"le capitaine|the |of brazil|in convoy|visits|odds & ends|reel no)\b")
PT_RX = re.compile(r"(?i)\b(POR|Portugal|Lisboa|portugu[eê]s)\b")
DOC_RX = re.compile(r"(?i)\b(INCE|Thomaz Reis|Brasilianas|fatos|visita|homenagens|cidade de|companhia|f[aá]brica|exposi[cç][aã]o|centen[aá]rio|amazonas|carnaval de 19|rituais|fronteiras|rio branco)\b")

def main():
    docs = busca(Q, 500, ("identifier", "title", "year", "date", "subject", "downloads"))
    print("candidatos:", len(docs))
    fora = excluidos()
    cand = []
    for d in docs:
        t = limpa(um(d.get("title")) or d["identifier"])
        ano = (um(d.get("year")) or um(d.get("date")))[:4]
        if not (ano.isdigit() and int(ano) <= 1955):
            continue
        if FORA_ID.search(d["identifier"]) or FORA_TIT.search(t) or bloqueado(t, fora):
            continue
        cand.append((d, t, ano))
    with ThreadPoolExecutor(8) as ex:
        vids = list(ex.map(lambda x: mp4s(x[0]["identifier"]), cand))
    itens, vistos = [], set()
    for (d, t, ano), v in zip(cand, vids):
        k = chave(re.sub(r"\(.*?\)", "", t))
        if not v or k in vistos:
            continue
        vistos.add(k)
        g = "Cinema português (até 1955)" if PT_RX.search(t) else "Documentários brasileiros (até 1955)" if DOC_RX.search(t) else "Cinema brasileiro (até 1955)"
        nome = t if ano in t else f"{t} ({ano})"
        itens.append((g, nome, d["identifier"], v[0][1]))
    itens.sort(key=lambda x: (x[0], x[1].lower()))
    linhas = ["#EXTM3U"]
    for g, nome, ident, arq in itens:
        linhas.append(f'#EXTINF:-1 tvg-name="{nome}" tvg-logo="{capa(ident)}" group-title="Em português · {g}",{nome}')
        linhas.append(link(ident, arq))
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    from collections import Counter
    print(f"títulos: {len(itens)}", dict(Counter(x[0] for x in itens)))
    for x in itens[:80]: print("  ", x[0], "|", x[1])
    if len(itens) < 10:
        sys.exit("poucos títulos; lista não atualizada")

if __name__ == "__main__":
    main()
