"""Lista as melhores coleções candidatas de cada série (uso manual, para escolher os itens fixos)."""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from comum import busca, um, mp4s
from concurrent.futures import ThreadPoolExecutor
from gerar_series import SERIES

def cand(item):
    nome, termo, grupo, parcial = item
    frase = re.sub(r"\b(19\d\d|serial|fleischer)\b", "", termo, flags=re.I).strip()
    docs = busca(f'mediatype:movies AND title:("{frase}")', 25, ("identifier", "title", "downloads", "licenseurl", "year"))
    out = []
    for d in docs[:12]:
        v = mp4s(d["identifier"])
        out.append(f'  {d["identifier"]} | {len(v)} mp4 | {d.get("downloads",0)} dl | {um(d.get("year"))} | {"PD" if "publicdomain" in um(d.get("licenseurl")) else "CC" if "creativecommons" in um(d.get("licenseurl")) else "-"} | {um(d.get("title"))[:70]} | ex: {v[0][1][:50] if v else ""}')
    return nome, out

with ThreadPoolExecutor(6) as ex:
    for nome, out in ex.map(cand, SERIES):
        print("## " + nome); print("\n".join(out))
