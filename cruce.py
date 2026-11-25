"""Cruza los RVOE de DGAIR (PDFs) contra SIRVOES por número de RVOE.
Uso: python -I cruce.py  -> imprime resumen y escribe data/cruce_dgair_sirvoes.csv
"""
import re
import pandas as pd

def norm(x):
    return re.sub(r"\s+", "", str(x)).upper() if pd.notna(x) else None

d = pd.read_csv("data/rvoes_dgair.csv", dtype=str)
s = pd.read_csv("data/rvoes_sirvoes.csv", dtype=str)
d["k"], s["k"] = d["rvoe"].map(norm), s["rvoe"].map(norm)

est = s.groupby("k")["estatus"].agg(lambda v: "|".join(sorted(set(v.dropna()))))
d["estatus_sirvoes"] = d["k"].map(est).fillna("NO ENCONTRADO")
# Acuerdos secretariales/decretos: DGAIR da una clave por institución ("ACUERDO 131"),
# SIRVOES una por programa ("ACUERDO 131/3067"), así que no se cruzan por clave.
sin_clave = (d["estatus_sirvoes"] == "NO ENCONTRADO") & ~d["k"].str.fullmatch(r"\d+", na=False)
d.loc[sin_clave, "estatus_sirvoes"] = "NO CRUZABLE (ACUERDO/DECRETO)"
s["en_dgair"] = s["k"].isin(set(d["k"]))

print(f"DGAIR: {len(d)} filas, {d['k'].nunique()} RVOE únicos")
print(f"SIRVOES: {len(s)} filas, {s['k'].nunique()} RVOE únicos")
print("\nRVOE de DGAIR según su estatus en SIRVOES:")
print(d.drop_duplicates("k")["estatus_sirvoes"].value_counts().to_string())
fed_vig = s[(s["tipo_rvoe"] == "FEDERAL") & (s["estatus"] == "VIGENTE")].drop_duplicates("k")
print(f"\nSIRVOES federales vigentes: {len(fed_vig)}; de ellos NO están en DGAIR: {(~fed_vig['en_dgair']).sum()}")
print("\nSIRVOES por tipo_rvoe:")
print(s.drop_duplicates("k")["tipo_rvoe"].value_counts(dropna=False).to_string())

d.drop(columns="k").to_csv("data/cruce_dgair_sirvoes.csv", index=False, encoding="utf-8-sig")

# ---- Tabla unificada: todo SIRVOES + lo que solo está en DGAIR ----
import unicodedata

def sin_acentos(x):
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode() if isinstance(x, str) else x

def catalogo(valores, extra={}):
    """Mapea el texto sin acentos de DGAIR al valor oficial de SIRVOES."""
    m = {sin_acentos(v): v for v in valores.dropna().unique()}
    return lambda x: m.get(extra.get(x, x), extra.get(x, x))

estado = catalogo(s["estado"], {"ESTADO DE MEXICO": "MEXICO", "COAHUILA": "COAHUILA DE ZARAGOZA",
                                "MICHOACAN": "MICHOACAN DE OCAMPO", "VERACRUZ": "VERACRUZ DE IGNACIO DE LA LLAVE"})
nivel = catalogo(s["nivel"])

# Base del acuerdo en SIRVOES: "ACUERDO 131/3067" -> "ACUERDO 131", para saber si DGAIR lo cubre.
s["base"] = s["k"].str.rsplit("/", n=1).str[0]
dk = set(d["k"])
s["en_dgair"] = s["k"].isin(dk) | s["base"].isin(dk)
cubiertos = set(s["k"]) | set(s["base"])

# Un RVOE real tiene 6-8 dígitos; "142" a secas es el ACUERDO 142 (UNITEC) mal capturado.
corto = d["k"].str.fullmatch(r"\d{1,5}", na=False)
cubierto = d["k"].isin(cubiertos) | (corto & ("ACUERDO" + d["k"]).isin(cubiertos))
solo_d = d[~cubierto].drop(columns="pagina").drop_duplicates().copy()  # el PDF repite algunas filas idénticas
solo_d["pagina"] = d.loc[solo_d.index, "pagina"]
solo_d["nota"] = ["" if re.fullmatch(r"\d{6,}", str(k)) else "acuerdo/decreto con clave irregular: posible duplicado de un registro SIRVOES"
                  for k in solo_d["k"]]
solo_d = solo_d.assign(
    fuente="DGAIR", estatus="VIGENTE", en_dgair=True,
    estado=solo_d["estado"].map(estado), nivel=solo_d["nivel"].map(nivel),
    modalidad=solo_d["modalidad"].replace({"ESCOLAR": "ESCOLARIZADA"}),
    programa=solo_d["programa"].str.replace(r"^(EN )+", "", regex=True),
)[["fuente", "institucion", "estado", "nivel", "programa", "modalidad", "rvoe", "estatus",
   "fecha_otorgamiento", "en_dgair", "nota", "archivo", "pagina"]]

retirado_vig_dgair = s["k"].isin(set(d.loc[d["estatus_sirvoes"] == "RETIRADO", "k"]))
s_u = s.drop(columns=["k", "base"]).assign(fuente="SIRVOES", nota="")
s_u.loc[retirado_vig_dgair & (s["estatus"] != "VIGENTE"), "nota"] = "retirado en SIRVOES pero DGAIR lo lista como vigente"
u = pd.concat([s_u, solo_d], ignore_index=True)
u = u[["fuente"] + [c for c in u.columns if c != "fuente"]].sort_values(["estado", "institucion", "programa"])
u.to_csv("data/rvoes.csv", index=False, encoding="utf-8-sig")
u.to_excel("data/rvoes.xlsx", index=False)
print(f"\nTabla unificada: {len(u)} filas")
print(u.groupby(["fuente", "estatus"]).size().to_string())
assert len(u) == len(s) + len(solo_d) and u["rvoe"].notna().all()
