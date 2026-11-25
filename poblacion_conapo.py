"""Población a mitad de año por estado (CONAPO, Conciliación 1950-2019 y Proyecciones 2020-2070, ed. 2023).
Uso: python -I poblacion_conapo.py  -> data/poblacion_conapo.csv (estado, anio, poblacion), 2000-2030
Descarga ~80 MB a data/conapo/ (no versionado).
"""
import io, unicodedata, urllib.request, zipfile
from pathlib import Path
import pandas as pd

URL = "https://conapo.segob.gob.mx/work/models/CONAPO/pry23/DB/ConDem50a19_ProyPob20a70.zip"
XLSX = "ConDem50a19_ProyPob20a70/0_Pob_Mitad_1950_2070.xlsx"
DIR = Path("data/conapo")

def sin_acentos(x):
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().upper()

if __name__ == "__main__":
    DIR.mkdir(parents=True, exist_ok=True)
    zpath = DIR / "pob.zip"
    if not zpath.exists():
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        zpath.write_bytes(urllib.request.urlopen(req, timeout=300).read())
    with zipfile.ZipFile(zpath) as z:
        p = pd.read_excel(io.BytesIO(z.read(XLSX)), usecols=["AÑO", "ENTIDAD", "CVE_GEO", "POBLACION"])
    p = p[(p["CVE_GEO"] > 0) & p["AÑO"].between(2000, 2030)]
    p = p.groupby(["ENTIDAD", "AÑO"], as_index=False)["POBLACION"].sum()

    # Nombres al catálogo de SIRVOES (el de data/rvoes.csv)
    sirvoes = pd.read_csv("data/rvoes.csv", usecols=["estado"], dtype=str)["estado"].dropna().unique()
    cat = {sin_acentos(e): e for e in sirvoes}
    alias = {"COAHUILA": "COAHUILA DE ZARAGOZA", "MICHOACAN": "MICHOACAN DE OCAMPO",
             "VERACRUZ": "VERACRUZ DE IGNACIO DE LA LLAVE", "ESTADO DE MEXICO": "MEXICO"}
    p["estado"] = p["ENTIDAD"].map(lambda e: cat.get(alias.get(sin_acentos(e), sin_acentos(e))))
    assert p["estado"].notna().all(), p.loc[p["estado"].isna(), "ENTIDAD"].unique()
    assert p["estado"].nunique() == 32
    out = p.rename(columns={"AÑO": "anio", "POBLACION": "poblacion"})[["estado", "anio", "poblacion"]]
    out.to_csv("data/poblacion_conapo.csv", index=False, encoding="utf-8-sig")
    print(out[out["anio"] == 2026].sort_values("poblacion", ascending=False).head(5).to_string(index=False))
    print("total 2026:", out.loc[out["anio"] == 2026, "poblacion"].sum())
