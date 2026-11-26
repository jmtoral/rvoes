"""Extrae las tablas de RVOE federales vigentes (DGAIR) a CSV/XLSX.
Uso: python -I parse_dgair.py data/pdfs  -> data/rvoes_dgair.csv / .xlsx
"""
import difflib, re, sys, unicodedata
from functools import lru_cache
from pathlib import Path
import pdfplumber, pandas as pd

COLS = ["institucion", "estado", "nivel", "programa", "modalidad", "rvoe_fecha"]
# "20240279/2024-02-07", "ACUERDO 131/1988-02-25", "DECRETO PRESIDENCIAL/1952-12- 29"...
# La fecha va al final; lo previo es el identificador (RVOE, acuerdo secretarial o decreto).
FECHA_RE = re.compile(r"[/\s-]*(\d{4})\s*-\s*(\d{2})\s*-\s*(\d{2})\s*$")

def split_rvoe(txt):
    m = FECHA_RE.search(txt)
    if not m:
        return txt.strip(), None
    return txt[:m.start()].strip(" /-"), "-".join(m.groups())

def clean(c):
    return re.sub(r"\s+", " ", c or "").strip()

def rows(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables():
                for r in table:
                    r = [clean(c) for c in r]
                    if len(r) != 6 or r[0].upper().startswith("INSTITUCI"):
                        continue
                    yield dict(zip(COLS, r), archivo=pdf_path.name, pagina=n)

# En el PDF, los campus largos del Tec ocupan tres renglones y el tercero se intercala letra por letra con
# "TECNOLOGICO": "INSTITUTO TMECEXNIOCOLOGICO ... CAMPUS ESTADO DE" = TECNOLOGICO + MEXICO. Las letras
# conservan su orden, así que al quitar las del nombre canónico queda la palabra del campus.
TEC = "INSTITUTO TECNOLOGICO"
CAMPUS_TEC = ["AGUASCALIENTES", "GUADALAJARA", "MEXICO", "NORTE", "GARZA SADA", "VERACRUZ", "POTOSI", "JUAREZ", "OBREGON",
              "CUERNAVACA", "MONTERREY", "QUERETARO", "TOLUCA", "CHIHUAHUA", "SONORA", "HIDALGO", "SINALOA", "LEON", "LAGUNA",
              "SALTILLO", "PUEBLA", "TAMPICO", "MAZATLAN", "CHIAPAS", "IRAPUATO", "ZACATECAS", "COLIMA", "MORELIA", "GUAYMAS"]
TEC_RE = re.compile(r"^(INSTITU.*?) Y DE ESTUDIOS SUPERIORES DE MONTERREY, CAMPUS ?(.*)$")

def reparar_nombre(nombre):
    m = TEC_RE.match(nombre or "")
    if not m or nombre.startswith(TEC + " Y DE"):
        return nombre
    revuelto, objetivo, sobra = m.group(1).replace(" ", ""), TEC.replace(" ", ""), []
    i = 0
    for c in revuelto:  # resta de subsecuencia, avanzando sobre el nombre canónico
        if i < len(objetivo) and c == objetivo[i]:
            i += 1
        else:
            sobra.append(c)
    if i < len(objetivo):  # no era el Tec revuelto
        return nombre
    # La resta puede invertir letras repetidas ("AGUASCAILENTES"): se ajusta a la palabra conocida más cercana
    resto = "".join(sobra)
    resto = (difflib.get_close_matches(resto, CAMPUS_TEC, n=1, cutoff=0.85) or [resto])[0]
    return f"{TEC} Y DE ESTUDIOS SUPERIORES DE MONTERREY, CAMPUS {(m.group(2) + ' ' + resto).strip()}"

# Otras instituciones sufren lo mismo con su plantel. Para repararlas hace falta saber cómo se llaman de verdad:
# se usan los nombres de SIRVOES y los de DGAIR que no traen palabras raras.
def sa(x):  # sin acentos pero con Ñ, como escribe DGAIR
    return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn" or c == "̃")).upper() if isinstance(x, str) else ""
comp = lambda x: re.sub(r"[^A-Z0-9Ñ]", "", x)
llave = lambda x: "".join(sorted(comp(x)))

def reparador(limpios, lugares):
    """Repara nombres que el PDF revolvió: el inicio del nombre se intercala letra por letra con un tercer
    renglón (casi siempre el plantel): "CEPNLTARNOT EDLE S EOSNTUODRAIOS SUPERIORES EN ..." =
    "CENTRO DE ESTUDIOS" + "PLANTEL SONORA". Busca un nombre limpio que termine igual, resta sus letras
    (conservan el orden) y reconstruye lo que sobra con lugares y palabras conocidos que tengan esas letras."""
    palabras = set(w for n in limpios for w in re.findall(r"[A-Z]+", n))
    frases = {}
    for n in limpios:
        for m in re.finditer(r"\b(?:PLANTEL|CAMPUS|SEDE)\s+([A-Z0-9 .]+)|\(([^)]+)\)", n):
            t = (m.group(1) or m.group(2)).strip(" .")
            if t: frases.setdefault(llave(t), t)
    for t in lugares: frases.setdefault(llave(t), t)
    por_letras = dict(frases)  # primero frases completas ("QUINTANA ROO"), luego palabras sueltas
    for w in palabras | {w for t in lugares for w in t.split()}:
        if len(w) > 1: por_letras.setdefault(llave(w), w)
    limpios = sorted(set(limpios), key=len)

    def trozos(s):  # "OAXACAJUCHITAN" -> "OAXACA JUCHITAN": tramos contiguos que son anagrama de una palabra
        @lru_cache(None)
        def f(i):
            if i == len(s): return []
            for j in range(len(s), i + 1, -1):
                w = por_letras.get("".join(sorted(s[i:j])))
                if w and (r := f(j)) is not None: return [w] + r
            return None
        r = f(0)
        return " ".join(r) if r else s

    def extra(sobra):
        if llave(sobra) in frases: return frases[llave(sobra)]
        for pre in ("PLANTEL", "CAMPUS"):
            ls = list(sobra)
            if all(ls.count(c) >= pre.count(c) for c in set(pre)):
                for c in pre: ls.remove(c)
                r = "".join(ls)
                return f"{pre} {frases.get(llave(r)) or trozos(r)}"
        return trozos(sobra)

    def reparar(n):
        m = re.search(r"(,|\s+(?:PLANTEL|CAMPUS)\b).*$", n)
        cuerpo, cola = (n[:m.start()], n[m.start():]) if m else (n, "")
        pal = cuerpo.split()
        for k in range(1, len(pal)):
            resto, cab = " ".join(pal[k:]), pal[:k]
            if all(w in palabras for w in re.findall(r"[A-Z]+", " ".join(cab))): continue  # nada desconocido al inicio
            for r in limpios:
                j = r.find(" " + resto)
                if j <= 0: continue
                obj, marca, i = comp(r[:j]), [], 0  # resta de subsecuencia, marcando a quién va cada letra
                for w in cab:
                    mk = []
                    for c in comp(w):
                        if i < len(obj) and c == obj[i]: i += 1; mk.append(1)
                        else: mk.append(0)
                    marca.append(mk)
                sobra = "".join(c for w, mk in zip(cab, marca) for c, b in zip(comp(w), mk) if not b)
                # revuelto de verdad: alguna palabra desconocida mezcla letras de ambos renglones
                mezcla = any(0 < sum(mk) < len(mk) and w not in palabras for w, mk in zip(cab, marca))
                if i < len(obj) or len(sobra) < 3 or not mezcla or len(obj) < len(sobra) / 2: continue
                x, base = extra(sobra), f"{r[:j]} {resto}{cola}".rstrip()
                if "(" in " ".join(cab): x = f"({x})"
                elif not (re.search(r"\b(?:PLANTEL|CAMPUS)\b", cola) or re.search(r"(,|\b(DE|DEL|LA|LAS|LOS|EL|Y))$", base)): x = ", " + x
                return re.sub(r"\s+", " ", f"{base} {x}").replace(" ,", ",").strip()
        return n
    return reparar

def reparar_planteles(df, sirvoes_csv):
    s = pd.read_csv(sirvoes_csv, dtype=str)
    rs = set(s["institucion"].map(sa))
    conocidas = set(w for n in rs for w in re.findall(r"[A-ZÑ]+", n))
    limpios = list(rs) + [n for n in df["institucion"].unique() if all(w in conocidas for w in re.findall(r"[A-ZÑ]+", n))]
    rep = reparador(limpios, set(s["municipio"].map(sa)) | set(s["estado"].map(sa)))
    cambios = {a: b for a in df["institucion"].unique() if (b := rep(a)) != a}
    df["institucion"] = df["institucion"].replace(cambios)
    print(f"Nombres revueltos reparados: {len(cambios)} ({df['institucion'].isin(set(cambios.values())).sum()} filas)")
    return df

def build(folder):
    df = pd.DataFrame([r for p in sorted(Path(folder).glob("*.pdf")) for r in rows(p)])
    return add_rvoe(df)

def add_rvoe(df):
    df["institucion"] = df["institucion"].map(reparar_nombre)
    df["rvoe"], fecha = zip(*df["rvoe_fecha"].map(split_rvoe))
    df["fecha_otorgamiento"] = pd.to_datetime(pd.Series(fecha, index=df.index), errors="coerce")
    return df

if __name__ == "__main__":
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "data/pdfs")
    df = build(folder)
    out = folder.parent / "rvoes_dgair"
    if (folder.parent / "rvoes_sirvoes.csv").exists():  # sale de scrape_sirvoes.py
        df = reparar_planteles(df, folder.parent / "rvoes_sirvoes.csv")
    df.to_csv(f"{out}.csv", index=False, encoding="utf-8-sig")
    df.to_excel(f"{out}.xlsx", index=False)
    bad = df["fecha_otorgamiento"].isna().sum()
    print(f"{len(df)} filas, {df['institucion'].nunique()} instituciones, {bad} sin fecha válida (revisar rvoe_fecha)")
    assert bad < len(df) * 0.01, "demasiadas filas sin fecha: revisar FECHA_RE"
    rep = reparador(["CENTRO DE ESTUDIOS SUPERIORES EN CIENCIAS JURIDICAS Y CRIMINOLOGICAS", "INSTITUTO NORDICO"], {"SONORA"})
    assert rep("CEPNLTARNOT EDLE S EOSNTUODRAIOS SUPERIORES EN CIENCIAS JURIDICAS Y CRIMINOLOGICAS,") == \
        "CENTRO DE ESTUDIOS SUPERIORES EN CIENCIAS JURIDICAS Y CRIMINOLOGICAS, PLANTEL SONORA"
    assert rep("INSTITUTO NORDICO UNIVERSITARIO") == "INSTITUTO NORDICO UNIVERSITARIO"  # nombre raro pero no revuelto
