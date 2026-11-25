"""Genera docs/data/rvoes.json, una versión compacta de data/rvoes.csv para el sitio explorador (docs/index.html).
Uso: python -I sitio_datos.py
Planteles y catálogos van en tablas aparte y los programas los referencian por índice.
"""
import json
from pathlib import Path
import pandas as pd

def limpio(s):
    # SIRVOES anota el nombre ("DERECHO (RETIRADO)") y DGAIR antepone "EN"
    return (s.str.replace(r"\(.*?\)", "", regex=True).str.replace(r"\s+", " ", regex=True)
             .str.strip().str.replace(r"^(EN )+", "", regex=True))

u = pd.read_csv("data/rvoes.csv", dtype=str).fillna("")
u["programa"] = limpio(u["programa"])
# En planteles el paréntesis suele ser el nombre ("(TULTEPEC)"): solo se quita la marca de retirado
u["plantel"] = u["plantel"].str.replace(r"\(RETIRADO\)", "", regex=True).str.strip().str.strip("()").str.strip()
u["cp"] = u["cp"].where(u["cp"] == "", u["cp"].str.zfill(5))  # SIRVOES pierde el 0 inicial (06030 -> 6030)
for c in ("fecha_otorgamiento", "fecha_retiro"):
    u[c] = u[c].str[:10]

cats = {c: sorted(u[c].unique()) for c in ("estado", "nivel", "modalidad", "estatus", "area", "motivo_retiro", "fuente")}
idx = {c: {v: i for i, v in enumerate(vs)} for c, vs in cats.items()}

# Planteles: los de SIRVOES por id_plantel; los de DGAIR (sin plantel) por institución + estado
u["clave_pl"] = u["id_plantel"].where(u["id_plantel"] != "", "D|" + u["institucion"] + "|" + u["estado"])
cols_pl = ["institucion", "plantel", "estado", "municipio", "domicilio", "cp", "telefono", "correo", "pagina_web", "razon_social"]
pl = u.drop_duplicates("clave_pl")[["clave_pl"] + cols_pl].reset_index(drop=True)
pl_idx = {k: i for i, k in enumerate(pl["clave_pl"])}
pl["estado"] = pl["estado"].map(idx["estado"])

nombres = sorted(u["programa"].unique())
nom_idx = {v: i for i, v in enumerate(nombres)}

pr = [[pl_idx[r.clave_pl], nom_idx[r.programa], idx["nivel"][r.nivel], idx["modalidad"][r.modalidad], idx["area"][r.area],
       r.rvoe, idx["estatus"][r.estatus], r.fecha_otorgamiento, r.fecha_retiro, idx["motivo_retiro"][r.motivo_retiro],
       idx["fuente"][r.fuente], 1 if r.en_dgair == "True" else 0, int(float(r.id_programa)) if r.id_programa else 0]
      for r in u.itertuples()]

# Población a mitad de año por estado (CONAPO), 2000-2026, en el orden del catálogo de estados
pob = pd.read_csv("data/poblacion_conapo.csv").query("2000 <= anio <= 2026").pivot(index="estado", columns="anio", values="poblacion")
assert set(pob.index) == set(cats["estado"]) - {""}, set(cats["estado"]) ^ set(pob.index)
pob_lista = [pob.loc[e].astype(int).tolist() if e in pob.index else None for e in cats["estado"]]

datos = {
    "pob": pob_lista,
    "meta": {"corte": pd.to_datetime(u["fecha_otorgamiento"], errors="coerce").max().strftime("%Y-%m-%d"),
             "columnas_pr": ["plantel", "programa", "nivel", "modalidad", "area", "rvoe", "estatus", "otorgamiento",
                             "retiro", "motivo_retiro", "fuente", "en_dgair", "id_programa_sirvoes"],
             "columnas_pl": cols_pl},
    "cat": cats, "nombres": nombres, "pl": pl[cols_pl].values.tolist(), "pr": pr,
}
out = Path("docs/data/rvoes.json"); out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
assert len(pr) == len(u)
print(f"{len(pr)} programas, {len(pl)} planteles, {len(nombres)} nombres -> {out} ({out.stat().st_size/1e6:.1f} MB)")
