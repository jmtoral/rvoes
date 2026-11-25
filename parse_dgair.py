"""Extrae las tablas de RVOE federales vigentes (DGAIR) a CSV/XLSX.
Uso: python -I parse_dgair.py data/pdfs  -> data/rvoes_dgair.csv / .xlsx
"""
import difflib, re, sys
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
    df.to_csv(f"{out}.csv", index=False, encoding="utf-8-sig")
    df.to_excel(f"{out}.xlsx", index=False)
    bad = df["fecha_otorgamiento"].isna().sum()
    print(f"{len(df)} filas, {df['institucion'].nunique()} instituciones, {bad} sin fecha válida (revisar rvoe_fecha)")
    assert bad < len(df) * 0.01, "demasiadas filas sin fecha: revisar FECHA_RE"
