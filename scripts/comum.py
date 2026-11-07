"""Funções usadas pelos dois geradores (filmes e séries)."""
import json, re, urllib.parse, urllib.request

UA = {"User-Agent": "playlist-canais/1.0 (gerador de lista de dominio publico)"}
ADULTO_RX = re.compile(r"\b(porn\w*|nudist\w*|naked|nude|sex\w*|erotic\w*|xxx|softcore|hardcore|altersporno)\b", re.I)

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.load(r)

def um(v):
    """Campos do archive.org podem vir como texto ou lista."""
    return str(v[0] if isinstance(v, list) and v else v or "")

def limpa(t):
    return re.sub(r"\s+", " ", str(t)).replace(",", " -").replace('"', "'").strip(" -_.")

def busca(q, rows, campos=("identifier", "title", "year", "subject", "licenseurl")):
    p = [("q", q), ("rows", str(rows)), ("page", "1"), ("output", "json"), ("sort[]", "downloads desc")]
    p += [("fl[]", f) for f in campos]
    try:
        return get("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(p))["response"]["docs"]
    except Exception as e:
        print("falha na busca:", e)
        return []

def excluidos():
    try:
        with open("excluir.txt", encoding="utf-8") as f:
            return [l.strip().lower() for l in f if l.strip() and not l.startswith("#")]
    except FileNotFoundError:
        return []

def bloqueado(texto, lista):
    t = texto.lower()
    return bool(ADULTO_RX.search(t)) or any(x in t for x in lista)

def chave(titulo):
    """Nome sem ano, parênteses e sufixos de versão: junta cópias do mesmo filme."""
    t = re.sub(r"[\(\[].*?[\)\]]", " ", titulo.lower())
    t = re.sub(r"\b(widescreen|uncut|restored|remastered|hd|video quality upgrade|quality upgrade|full (film|movie)|kvcd-\d+|19\d\d|20\d\d)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()

def mp4s(ident):
    """Um MP4 por vídeo original do item (prefere H.264), em ordem de nome: [(base, arquivo)]."""
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
        nota = (3 if fmt == "h.264" else 1 if "512Kb" in fmt else 2, int(f.get("size", "0") or 0))
        if base not in melhor or nota > melhor[base][0]:
            melhor[base] = (nota, n)
    return [(b, n) for b, (_, n) in sorted(melhor.items())]

def link(ident, arquivo):
    return f"https://archive.org/download/{urllib.parse.quote(ident)}/{urllib.parse.quote(arquivo)}"

def capa(ident):
    return f"https://archive.org/services/img/{urllib.parse.quote(ident)}"
