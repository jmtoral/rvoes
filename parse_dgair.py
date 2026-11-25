"""Extrae las tablas de RVOE federales vigentes (DGAIR) a CSV/XLSX.
Uso: python -I parse_dgair.py data/pdfs  -> data/rvoes_dgair.csv / .xlsx
"""
import re, sys
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

def build(folder):
    df = pd.DataFrame([r for p in sorted(Path(folder).glob("*.pdf")) for r in rows(p)])
    return add_rvoe(df)

def add_rvoe(df):
    df["rvoe"], fecha = zip(*df["rvoe_fecha"].map(split_rvoe))
    df["fecha_otorgamiento"] = pd.to_datetime(pd.Series(fecha, index=df.index), errors="coerce")
    return df

if __name__ == "__main__":
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "data/pdfs")
    df = build(folder)
    out = folder.parent / "rvoes_dgair"
    df.to_csv(f"{out}.csv", index=False, encoding="utf-8-sig")
    df.to_excel(f"{out}.xlsx", index=False)
    bad = df["fecha_otorgamiento"].isna().sum()
    print(f"{len(df)} filas, {df['institucion'].nunique()} instituciones, {bad} sin fecha válida (revisar rvoe_fecha)")
    assert bad < len(df) * 0.01, "demasiadas filas sin fecha: revisar FECHA_RE"
