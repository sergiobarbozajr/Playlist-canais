"""Gera novidades.json: o que entrou nas listas nativas nos últimos 30 dias, mais destaques escolhidos à mão.

O app LumeStarTV lê este arquivo e mostra a fileira "Novidades da semana" na tela inicial.
Assim dá para "lançar" um título sem publicar versão nova do app (mesma ideia de catálogo remoto,
só com as nossas listas legais).

- Compara cada lista com a versão anterior do repositório (git) para achar o que é novo.
- destaques.txt (opcional): um título ou endereço por linha; aparecem primeiro, sempre.
"""
import json, os, re, subprocess, datetime

LISTAS = ["livres-1980.m3u8", "filmes-dominio-publico.m3u8", "series-dominio-publico.m3u8", "portugues.m3u8"]
DIAS = 30
hoje = datetime.date.today()


def entradas(txt):
    """[(titulo, url)] de um M3U. Episódios viram o nome da série (uma vez só)."""
    out, titulo = [], None
    for linha in txt.splitlines():
        linha = linha.strip()
        if linha.startswith("#EXTINF"):
            titulo = linha.rsplit(",", 1)[-1].strip()
        elif linha and not linha.startswith("#") and titulo:
            m = re.match(r"(.+?)\s+S\d+E\d+", titulo)
            out.append((m.group(1).strip(), "") if m else (titulo, linha))
            titulo = None
    vistos, unicos = set(), []
    for t, u in out:
        k = u or "t:" + t.lower()
        if k not in vistos:
            vistos.add(k); unicos.append((t, u))
    return unicos


def anterior(arq):
    try:
        return subprocess.run(["git", "show", "HEAD:" + arq], capture_output=True, text=True, check=True).stdout
    except Exception:
        return None


antigo = {}
if os.path.exists("novidades.json"):
    for o in json.load(open("novidades.json", encoding="utf-8")).get("titulos", []):
        if not o.get("fixo"):
            antigo[o.get("u") or "t:" + o["t"].lower()] = o

novos = dict(antigo)
for arq in LISTAS:
    if not os.path.exists(arq):
        continue
    atual = entradas(open(arq, encoding="utf-8").read())
    prev_txt = anterior(arq)
    if prev_txt is None and antigo:
        continue
    prev = {u or "t:" + t.lower() for t, u in entradas(prev_txt or "")}
    for t, u in atual:
        k = u or "t:" + t.lower()
        if k not in prev and k not in novos:
            novos[k] = {"t": t, "u": u, "d": hoje.isoformat(), "lista": arq}

# primeira vez (ainda sem novidades.json): a lista mais recente, livres-1980, entra como novidade
if not antigo and not any(v["d"] == hoje.isoformat() for v in novos.values()) and os.path.exists(LISTAS[0]):
    for t, u in entradas(open(LISTAS[0], encoding="utf-8").read()):
        novos[u or "t:" + t.lower()] = {"t": t, "u": u, "d": hoje.isoformat(), "lista": LISTAS[0]}

# só o que ainda existe nas listas e tem menos de 30 dias
existe = set()
for arq in LISTAS:
    if os.path.exists(arq):
        existe |= {u or "t:" + t.lower() for t, u in entradas(open(arq, encoding="utf-8").read())}
limite = hoje - datetime.timedelta(days=DIAS)
lista = [v for k, v in novos.items() if k in existe and datetime.date.fromisoformat(v["d"]) >= limite]
lista.sort(key=lambda v: v["d"], reverse=True)

fixos = []
if os.path.exists("destaques.txt"):
    for linha in open("destaques.txt", encoding="utf-8"):
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            fixos.append({"t": "" if linha.startswith("http") else linha, "u": linha if linha.startswith("http") else "", "fixo": True})

json.dump({"atualizado": hoje.isoformat(), "titulos": fixos + lista[:60]}, open("novidades.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"novidades: {len(fixos)} destaques fixos + {len(lista)} títulos novos")
