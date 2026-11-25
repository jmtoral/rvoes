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
