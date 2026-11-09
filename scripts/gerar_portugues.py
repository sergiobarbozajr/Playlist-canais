#!/usr/bin/env python3
"""
Gera portugues.m3u8: filmes e séries em português (falados, dublados ou legendados em português) que podem
ser distribuídos de forma legal, do Internet Archive:
- obras publicadas até 1955: em domínio público pela lei brasileira (Lei 9.610/98, art. 44: obra audiovisual,
  70 anos contados de 1º de janeiro do ano seguinte à publicação);
- obras de qualquer ano com licença Creative Commons dada pelo próprio autor.
Itens que se dizem "domínio público" sem ano antigo nem licença Creative Commons ficam de fora (muitos são cópias).
"""
import os, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from comum import busca, um, limpa, excluidos, bloqueado, chave, mp4s, link, capa

SAIDA = "portugues.m3u8"
PT = '(language:(portuguese OR por OR "português" OR "portugues" OR pt OR pt-br OR "brazilian portuguese") OR subject:(dublado OR legendado OR "legendas em português" OR "filme brasileiro" OR "cinema brasileiro" OR "cinema português"))'
LEGAL = '(licenseurl:*creativecommons* OR year:[1890 TO 1955] OR date:[1890-01-01 TO 1955-12-31])'

def grupo(d, t):
    s = (t + " " + " ".join(d.get("subject", []) if isinstance(d.get("subject"), list) else [str(d.get("subject", ""))])).lower()
    if re.search(r"anima|desenho|cartoon", s): return "Animação"
    if re.search(r"document", s): return "Documentários"
    if re.search(r"curta|short", s): return "Curtas"
    return "Filmes"

def main():
    q = f"mediatype:movies AND {PT} AND {LEGAL}"
    docs = busca(q, 800, ("identifier", "title", "year", "date", "subject", "licenseurl", "language"))
    print("encontrados:", len(docs))
    fora = excluidos()
    cand = []
    for d in docs:
        t = limpa(um(d.get("title")) or d["identifier"])
        ano = (um(d.get("year")) or um(d.get("date")))[:4]
        cc = "creativecommons" in um(d.get("licenseurl"))
        antigo = ano.isdigit() and int(ano) <= 1955
        if not (cc or antigo) or bloqueado(t + " " + d["identifier"], fora):
            continue
        if re.search(r"(?i)\b(trailer|teaser|making of|bastidores|aula|palestra|webinar|live|podcast)\b", t):
            continue
        cand.append((d, t, ano, cc))
    with ThreadPoolExecutor(8) as ex:
        vids = list(ex.map(lambda x: mp4s(x[0]["identifier"]), cand))
    linhas, n, vistos = ["#EXTM3U"], 0, set()
    for (d, t, ano, cc), v in zip(cand, vids):
        if not v or chave(t) in vistos:
            continue
        vistos.add(chave(t))
        nome = f"{t} ({ano})" if ano.isdigit() and ano not in t else t
        motivo = "Creative Commons" if cc else "domínio público"
        g = grupo(d, t)
        if len(v) > 1:  # vários vídeos: vira série, um episódio por arquivo
            for i, (base, arq) in enumerate(v, 1):
                ep = f"{t} S01E{i:02d} - {limpa(base.split('/')[-1].replace('_', ' '))}"[:150]
                linhas.append(f'#EXTINF:-1 tvg-logo="{capa(d["identifier"])}" group-title="Em português · Séries e coleções",{ep}')
                linhas.append(link(d["identifier"], arq))
        else:
            linhas.append(f'#EXTINF:-1 tvg-name="{nome}" tvg-logo="{capa(d["identifier"])}" group-title="Em português · {g}",{nome}')
            linhas.append(link(d["identifier"], v[0][1]))
        n += 1
        if n <= 60: print(" ", motivo, "|", nome)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    print(f"títulos em português: {n}")
    if n < 5:
        sys.exit("poucos títulos; lista não atualizada")

if __name__ == "__main__":
    main()
