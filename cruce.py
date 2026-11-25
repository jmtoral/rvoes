"""Cruza los RVOE de DGAIR (PDFs) contra SIRVOES y arma la tabla unificada.
Uso: python -I cruce.py  -> data/cruce_dgair_sirvoes.csv y data/rvoes.csv / .xlsx

- RVOE con número propio (6-8 dígitos): se cruzan por número.
- Acuerdos y decretos institucionales (Tec, UVM, UNITEC, Anáhuac, La Salle...): DGAIR solo da una clave
  genérica ("ACUERDO 131", "DECRETO"), así que se cruzan por programa: institución sin campus + estado +
  nivel + nombre del programa + modalidad.
"""
import re, unicodedata
import pandas as pd

def sin_acentos(x):
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode() if isinstance(x, str) else x

def norm(x):
    return re.sub(r"\s+", "", str(x)).upper() if pd.notna(x) else None

def limpio(x):  # "EN DERECHO (LICENCIATURA MIXTA)" -> "DERECHO"
    x = sin_acentos(str(x)).upper()
    return re.sub(r"^(EN )+", "", re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", x)).strip())

def raiz(inst):  # "UNIVERSIDAD LA SALLE (HILL)", "UVM, CAMPUS COYOACAN" -> nombre de la institución
    x = sin_acentos(str(inst)).upper()
    return re.sub(r"\s+", " ", re.sub(r",?\s*CAMPUS.*$|\(.*?\)", "", x)).strip(" ,")

def catalogo(valores, extra={}):
    """Mapea el texto sin acentos de DGAIR al valor oficial de SIRVOES."""
    m = {sin_acentos(v): v for v in valores.dropna().unique()}
    return lambda x: m.get(extra.get(x, x), extra.get(x, x))

d = pd.read_csv("data/rvoes_dgair.csv", dtype=str)
s = pd.read_csv("data/rvoes_sirvoes.csv", dtype=str)
estado = catalogo(s["estado"], {"ESTADO DE MEXICO": "MEXICO", "COAHUILA": "COAHUILA DE ZARAGOZA",
                                "MICHOACAN": "MICHOACAN DE OCAMPO", "VERACRUZ": "VERACRUZ DE IGNACIO DE LA LLAVE"})
nivel = catalogo(s["nivel"])
d["estado_s"], d["nivel_s"] = d["estado"].map(estado), d["nivel"].map(nivel)
d["modalidad_s"] = d["modalidad"].replace({"ESCOLAR": "ESCOLARIZADA"})

d["k"], s["k"] = d["rvoe"].map(norm), s["rvoe"].map(norm)
d["propio"] = d["k"].str.fullmatch(r"\d{6,}", na=False)  # "142" a secas es el ACUERDO 142 de UNITEC
s["ri"] = s["institucion"].map(raiz)
raices = sorted(set(s["ri"]), key=len, reverse=True)
def raiz_d(inst):  # si DGAIR la escribe distinto ("ESCUELA BANCARIA Y COMERCIAL, PLANTEL CDMX SUR"), usa el prefijo de SIRVOES
    r = raiz(inst)
    return r if r in set_raices else next((x for x in raices if r.startswith(x + " ") or r.startswith(x + ",")), r)
set_raices = set(raices)
d["ri"] = d["institucion"].map(raiz_d)
llave = lambda df, e, n, m: (df["ri"] + "|" + df[e].map(sin_acentos) + "|" + df[n].map(sin_acentos)
                             + "|" + df["programa"].map(limpio) + ("|" + df[m] if m else ""))
d["kp"], s["kp"] = llave(d, "estado_s", "nivel_s", "modalidad_s"), llave(s, "estado", "nivel", "modalidad")
d["kp_otro"] = d["ri"] + "|" + d["nivel_s"].map(sin_acentos) + "|" + d["programa"].map(limpio)  # mismo programa, otro campus/modalidad
s_otro = set(s["ri"] + "|" + s["nivel"].map(sin_acentos) + "|" + s["programa"].map(limpio))

# Estatus en SIRVOES de cada fila de DGAIR: por número o, si es acuerdo/decreto, por programa
est_num = s.groupby("k")["estatus"].agg(lambda v: "|".join(sorted(set(v.dropna()))))
est_prog = s.groupby("kp")["estatus"].agg(lambda v: "|".join(sorted(set(v.dropna()))))
d["estatus_sirvoes"] = d["k"].map(est_num).where(d["propio"], d["kp"].map(est_prog)).fillna("NO ENCONTRADO")
s["en_dgair"] = s["k"].isin(set(d.loc[d["propio"], "k"])) | s["kp"].isin(set(d.loc[~d["propio"], "kp"]))

print(f"DGAIR: {len(d)} filas ({d['propio'].sum()} con RVOE propio, {(~d['propio']).sum()} por acuerdo/decreto)")
print(f"SIRVOES: {len(s)} filas")
print("\nFilas de DGAIR según su estatus en SIRVOES:")
print(d.groupby(["propio", "estatus_sirvoes"]).size().to_string())
fed_vig = s[(s["tipo_rvoe"] == "FEDERAL") & (s["estatus"] == "VIGENTE")]
print(f"\nSIRVOES federales vigentes: {len(fed_vig)}; de ellos NO están en DGAIR: {(~fed_vig['en_dgair']).sum()}")

d.drop(columns=["k", "kp", "kp_otro", "ri", "estado_s", "nivel_s", "modalidad_s", "propio"]).to_csv(
    "data/cruce_dgair_sirvoes.csv", index=False, encoding="utf-8-sig")

# ---- Tabla unificada: todo SIRVOES + lo que solo está en DGAIR ----
solo_d = d[d["estatus_sirvoes"] == "NO ENCONTRADO"].drop(columns="pagina").drop_duplicates().copy()  # el PDF repite filas
solo_d["pagina"] = d.loc[solo_d.index, "pagina"]
solo_d["nota"] = [""
    if propio else "acuerdo institucional: SIRVOES tiene este programa en otro campus o modalidad, pero no en éste"
    if otro in s_otro else "acuerdo institucional: no aparece en SIRVOES (programa nuevo o variante del nombre)"
    for propio, otro in zip(solo_d["propio"], solo_d["kp_otro"])]
solo_d = solo_d.assign(
    fuente="DGAIR", estatus="VIGENTE", en_dgair=True, estado=solo_d["estado_s"], nivel=solo_d["nivel_s"],
    modalidad=solo_d["modalidad_s"], programa=solo_d["programa"].str.replace(r"^(EN )+", "", regex=True),
)[["fuente", "institucion", "estado", "nivel", "programa", "modalidad", "rvoe", "estatus",
   "fecha_otorgamiento", "en_dgair", "nota", "archivo", "pagina"]]

retirado_vig_dgair = s["k"].isin(set(d.loc[d["propio"] & (d["estatus_sirvoes"] == "RETIRADO"), "k"]))
s_u = s.drop(columns=["k", "kp", "ri"]).assign(fuente="SIRVOES", nota="")
s_u.loc[retirado_vig_dgair & (s["estatus"] != "VIGENTE"), "nota"] = "retirado en SIRVOES pero DGAIR lo lista como vigente"
u = pd.concat([s_u, solo_d], ignore_index=True)
# SIRVOES trae 14 fechas con el año mal capturado ("0041-12-20" en el RVOE 20200542): el año sale del propio RVOE
f = u["fecha_otorgamiento"].fillna("")
mal = f.str.match(r"^0\d{3}-") & u["rvoe"].str.fullmatch(r"(19|20)\d{5,6}", na=False)  # 2006613 (7 dígitos) o 20200542
u.loc[mal, "fecha_otorgamiento"] = u.loc[mal, "rvoe"].str[:4] + f[mal].str[4:]
print(f"Fechas con año corregido desde el RVOE: {mal.sum()}")
u = u[["fuente"] + [c for c in u.columns if c != "fuente"]].sort_values(["estado", "institucion", "programa"])
u.to_csv("data/rvoes.csv", index=False, encoding="utf-8-sig")
u.to_excel("data/rvoes.xlsx", index=False)
print(f"\nTabla unificada: {len(u)} filas")
print(u.groupby(["fuente", "estatus"]).size().to_string())
print(u["nota"].replace("", None).value_counts().to_string())
assert len(u) == len(s) + len(solo_d) and u["rvoe"].notna().all()
assert raiz("UNIVERSIDAD LA SALLE (HILL)") == "UNIVERSIDAD LA SALLE" and limpio("EN DERECHO (LIC. MIXTA)") == "DERECHO"
