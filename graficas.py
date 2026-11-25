"""Gráficas de licenciaturas:
- img/derecho_por_anio.png: RVOE de Derecho otorgados por año y modalidad.
- img/vigentes_acumulados.png: programas vigentes en cada año, top 5 licenciaturas.
- img/derecho_por_estado.png: Derecho vigentes en cada año, un panel por estado.
- img/doctorados_acumulados.png y doctorados_derecho_subareas.png: doctorados por área y subárea jurídica.
Uso: python -I graficas.py  (imprime las tablas en markdown)
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DESDE, HASTA = 2000, 2026
MODALIDADES = {"ESCOLARIZADA": "#2a78d6", "MIXTA": "#eb6834", "NO ESCOLARIZADA": "#1baf7a"}
CREDITO = "Elaborado por Manuel Toral con información de la SEP (SIRVOES y DGAIR)"
SURFACE, INK, INK2, GRID ="#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

CARRERAS = {"DERECHO": "#2a78d6", "ADMINISTRACION DE EMPRESAS": "#eb6834", "PEDAGOGIA": "#1baf7a",
             "MERCADOTECNIA": "#eda100", "PSICOLOGIA": "#e87ba4"}
NOMBRES = {"DERECHO": "Derecho", "ADMINISTRACION DE EMPRESAS": "Administración de Empresas",
           "PEDAGOGIA": "Pedagogía", "MERCADOTECNIA": "Mercadotecnia", "PSICOLOGIA": "Psicología"}

def nombre_limpio(programa):
    # SIRVOES anota el nombre: "DERECHO (LICENCIATURA MIXTA)", "DERECHO (RETIRADO)"...
    return programa.str.replace(r"\(.*?\)", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()

def licenciatura_derecho(u):
    return u[(u["nivel"] == "LICENCIATURA") & (nombre_limpio(u["programa"]) == "DERECHO")]

def vigentes_por_anio(df, cat, colores=CARRERAS):
    """Programas vigentes al cierre de cada año = otorgados hasta ese año - retirados hasta ese año.
    `cat`: Serie alineada con df con la categoría (clave de `colores`) de cada programa."""
    ao = pd.to_datetime(df["fecha_otorgamiento"], errors="coerce").dt.year
    ar = pd.to_datetime(df["fecha_retiro"], errors="coerce").dt.year
    return pd.DataFrame({c: [((cat == c) & (ao <= y) & ~(ar <= y)).sum() for y in range(DESDE, HASTA + 1)]
                         for c in colores}, index=range(DESDE, HASTA + 1))

def clasificar(programa, reglas, resto=None):
    """Categoría por regex sobre el nombre limpio; gana la primera regla que coincide."""
    p = nombre_limpio(programa).str.replace(r"^(EN )+", "", regex=True)
    cat = pd.Series(resto, index=p.index, dtype=object)
    for clave, rx in reversed(reglas):  # al revés para que la primera regla sobrescriba
        cat[p.str.contains(rx, na=False)] = clave
    return cat

# Doctorados: los nombres varían ("DERECHO PENAL", "CIENCIAS DE LA EDUCACION"), se agrupan por palabra
# clave ("INNOVACION Y ADMINISTRACION EDUCATIVA" -> educación).
JURIDICO = r"DERECHO|JURIDIC|CRIMIN|PENAL|JUICIO|FORENS|SEGURIDAD PUBLICA|JUSTICIA"
AREAS_DOC = [("DERECHO", JURIDICO), ("PEDAGOGIA", r"EDUCACI|PEDAGOG|EDUCATIV"),
             ("ADMINISTRACION DE EMPRESAS", r"ADMINISTRACI"), ("MERCADOTECNIA", r"MERCADOTECNIA|MARKETING"),
             ("PSICOLOGIA", r"PSICOLOG")]
NOMBRES_DOC = {"DERECHO": "Derecho, C. Jurídicas y Criminología", "PEDAGOGIA": "Educación y Pedagogía",
               "ADMINISTRACION DE EMPRESAS": "Administración", "MERCADOTECNIA": "Mercadotecnia", "PSICOLOGIA": "Psicología"}

def area_doctorado(programa):
    return clasificar(programa, AREAS_DOC)

# Subáreas de los doctorados jurídicos. El orden importa: "DERECHO PROCESAL PENAL" -> penal,
# "DERECHO PROCESAL CONSTITUCIONAL" -> constitucional, "DERECHO CIVIL CON JUICIO ORAL" -> procesal/civil.
SUBAREAS_DER = [
    ("Penal y criminología", r"PENAL|CRIMIN|FORENS|SEGURIDAD PUBLICA"),
    ("Constitucional y derechos humanos", r"CONSTITU|HUMANOS|AMPARO|PUBLICO|ANTICORRUP"),
    ("Procesal, civil y juicios orales", r"PROCESAL|CIVIL|FAMILIAR|JUICIO|\bORAL|LITIG"),  # \b: "LABORAL" no es oral
    ("Fiscal, laboral y empresarial", r"FISCAL|TRIBUT|LABORAL|TRABAJO|CORPORAT|EMPRESA|COMERCI|ADUAN|MARITIM"),
    ("Derecho / Ciencias jurídicas (general)", r"^(?:DERECHO|CIENCIAS? JURIDICAS?|DERECHO Y CIENCIAS JURIDICAS|INVESTIGACION JURIDICA)$"),
]
OTRAS_DER = "Otras especialidades"
COLORES_SUB = dict(zip([s for s, _ in SUBAREAS_DER] + [OTRAS_DER],
                       ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))

def separar(valores, minimo):
    """Empuja hacia arriba las etiquetas finales que quedarían encimadas."""
    orden = sorted(valores, key=valores.get)
    pos, prev = {}, None
    for k in orden:
        pos[k] = valores[k] if prev is None else max(valores[k], prev + minimo)
        prev = pos[k]
    return pos

def graficar_lineas(t, out, ultima_fecha, nombres=NOMBRES, colores=CARRERAS,
                    titulo="Licenciaturas con más RVOE: programas vigentes en cada año",
                    nota="nombre exacto del programa (sin variantes)", ncol=5):
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for c, color in colores.items():
        ax.plot(t.index, t[c], color=color, linewidth=2, solid_capstyle="round", solid_joinstyle="round", zorder=3)
        ax.scatter([HASTA], [t[c].iloc[-1]], s=40, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=4)
    pos = separar({c: t[c].iloc[-1] for c in colores}, minimo=t.values.max() * 0.045)
    for c, y in pos.items():
        ax.annotate(f"{nombres[c]}  {t[c].iloc[-1]:,}", (HASTA, t[c].iloc[-1]), xytext=(HASTA + 0.5, y),
                    textcoords="data", va="center", fontsize=9, color=INK, annotation_clip=False)
    ax.set_title(titulo, loc="left", fontsize=14, color=INK, pad=28, weight="bold")
    ax.text(0, 1.04, "Acumulado de RVOE federales otorgados menos los retirados, al cierre de cada año",
            transform=ax.transAxes, fontsize=10, color=INK2)
    ax.legend([plt.Line2D([], [], color=col, linewidth=2) for col in colores.values()], [nombres[c] for c in colores],
              loc="upper left", frameon=False, fontsize=9, labelcolor=INK2, ncol=ncol, bbox_to_anchor=(0, 1.0))
    ax.set_xticks(range(DESDE, HASTA + 1, 2))
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_xlim(DESDE - 0.5, HASTA + 0.3)
    ax.set_ylim(0, t.values.max() * (1.15 if ncol >= len(colores) else 1.25))  # leyenda de 2 renglones: más aire
    fig.text(0.01, 0.01, f"{CREDITO}.\nSolo RVOE federales; {nota}. "
             f"Solo se descuentan retiros registrados en SIRVOES.  {HASTA} al {ultima_fecha}.", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.05, 0.83, 1))
    fig.savefig(out, facecolor=SURFACE)

ESTADO_CORTO = {"MÉXICO": "Estado de México", "CIUDAD DE MÉXICO": "Ciudad de México",
                "VERACRUZ DE IGNACIO DE LA LLAVE": "Veracruz", "COAHUILA DE ZARAGOZA": "Coahuila",
                "MICHOACÁN DE OCAMPO": "Michoacán", "SAN LUIS POTOSI": "San Luis Potosí"}

def graficar_facetas(t, out, ultima_fecha, ncols=8):
    """Small multiples: una línea por estado, ordenados de mayor a menor; escala Y propia por panel."""
    t = t[t.iloc[-1].sort_values(ascending=False).index]
    nrows = -(-len(t.columns) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 2.2 * nrows + 1.4), dpi=150, facecolor=SURFACE, sharex=True)
    for ax, e in zip(axes.flat, t.columns):
        y = t[e]
        ax.set_facecolor(SURFACE)
        ax.fill_between(y.index, y, color="#2a78d6", alpha=0.1, linewidth=0, zorder=2)
        ax.plot(y.index, y, color="#2a78d6", linewidth=2, solid_capstyle="round", zorder=3)
        ax.scatter([HASTA], [y.iloc[-1]], s=24, color="#2a78d6", edgecolor=SURFACE, linewidth=1.2, zorder=4)
        ax.set_title(ESTADO_CORTO.get(e, e.title()), loc="left", fontsize=9.5, color=INK, pad=3)
        ax.text(0.02, 0.97, f"{y.iloc[-1]:,}", transform=ax.transAxes, fontsize=13, weight="bold", color=INK, va="top")
        ax.set_ylim(0, max(y.max(), 1) * 1.1)
        ax.set_yticks([0, y.max()])
        ax.set_xticks([DESDE, HASTA])
        ax.tick_params(colors=INK2, labelsize=7.5, length=0)
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
    for ax in list(axes.flat)[len(t.columns):]:
        ax.set_visible(False)
    fig.text(0.01, 0.99, "Licenciatura en Derecho por estado: programas vigentes en cada año", va="top",
             fontsize=15, weight="bold", color=INK)
    fig.text(0.01, 0.955, f"Acumulado de RVOE federales otorgados menos los retirados, al cierre de cada año, {DESDE}–{HASTA}. "
             "Cifra grande = vigentes hoy. Cada panel tiene su propia escala vertical.", va="top", fontsize=10, color=INK2)
    fig.text(0.01, 0.008, f"{CREDITO}. Solo RVOE federales; programa con nombre exacto \"Derecho\". "
             f"Solo se descuentan retiros registrados en SIRVOES. {HASTA} al {ultima_fecha}.", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.02, 1, 0.94), h_pad=1.6, w_pad=1.2)
    fig.savefig(out, facecolor=SURFACE)

def tabla(der):
    anio = pd.to_datetime(der["fecha_otorgamiento"], errors="coerce").dt.year
    t = (der.assign(anio=anio).query("@DESDE <= anio <= @HASTA")
         .pivot_table(index="anio", columns="modalidad", values="rvoe", aggfunc="count", fill_value=0)
         .reindex(index=range(DESDE, HASTA + 1), columns=list(MODALIDADES), fill_value=0))
    return t

def graficar(t, out, ultima_fecha):
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    base = pd.Series(0, index=t.index)
    for m, color in MODALIDADES.items():
        ax.bar(t.index, t[m], bottom=base, color=color, width=0.78, edgecolor=SURFACE, linewidth=1.2, label=m.capitalize(), zorder=3)
        base += t[m]
    tot = t.sum(axis=1)
    for a in (tot.idxmax(), HASTA):  # rótulos selectivos: el pico y el año en curso
        etiqueta = f"{tot[a]}" + ("*" if a == HASTA else "")
        ax.annotate(etiqueta, (a, tot[a]), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=9, color=INK2)
    ax.set_title("Licenciatura en Derecho: RVOE federales otorgados por año", loc="left", fontsize=14, color=INK, pad=28, weight="bold")
    ax.text(0, 1.04, "Incluye programas hoy vigentes y retirados · por modalidad", transform=ax.transAxes, fontsize=10, color=INK2)
    ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=INK2, ncol=3, bbox_to_anchor=(0, 1.0))
    ax.set_xticks(range(DESDE, HASTA + 1, 2))
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_xlim(DESDE - 0.7, HASTA + 0.7)
    ax.set_ylim(0, tot.max() * 1.18)
    fig.text(0.01, 0.01, f"{CREDITO}. Fecha = otorgamiento del RVOE. "
             f"Solo RVOE federales.  * {HASTA} parcial: registros al {ultima_fecha}.",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, facecolor=SURFACE)

if __name__ == "__main__":
    u = pd.read_csv("data/rvoes.csv", dtype=str)
    der = licenciatura_derecho(u)
    t = tabla(der)
    assert t.values.sum() > 0.9 * len(der[pd.to_datetime(der["fecha_otorgamiento"], errors="coerce").dt.year >= DESDE])
    ultima = pd.to_datetime(u["fecha_otorgamiento"], errors="coerce").max().strftime("%d-%m-%Y")
    graficar(t, Path("img/derecho_por_anio.png"), ultima)
    t["TOTAL"] = t.sum(axis=1)
    print(t.to_markdown())

    lic = u[u["nivel"] == "LICENCIATURA"]
    v = vigentes_por_anio(lic, nombre_limpio(lic["programa"]))
    assert v["DERECHO"].iloc[-1] <= (der["estatus"] == "VIGENTE").sum()  # no puede haber más vigentes que hoy
    graficar_lineas(v, Path("img/vigentes_acumulados.png"), ultima)
    print(v.rename(columns=NOMBRES).to_markdown())

    doc = u[u["nivel"] == "DOCTORADO"]
    area = area_doctorado(doc["programa"])
    assert area_doctorado(pd.Series(["INNOVACION Y ADMINISTRACION EDUCATIVA", "DERECHO PENAL (RETIRADO)", "FILOSOFIA",
                                     "CRIMINOLOGIA", "CIENCIAS JURIDICAS"])).fillna("-").tolist() \
        == ["PEDAGOGIA", "DERECHO", "-", "DERECHO", "DERECHO"]
    vd = vigentes_por_anio(doc, area)
    graficar_lineas(vd, Path("img/doctorados_acumulados.png"), ultima, nombres=NOMBRES_DOC,
                    titulo="Doctorados por área: programas vigentes en cada año",
                    nota="área asignada por palabra clave en el nombre del programa")
    print(vd.rename(columns=NOMBRES_DOC).to_markdown())
    print("doctorados vigentes por área hoy:", area[doc["estatus"] == "VIGENTE"].value_counts(dropna=False).to_dict())

    djur = doc[area == "DERECHO"]
    sub = clasificar(djur["programa"], SUBAREAS_DER, resto=OTRAS_DER)
    assert clasificar(pd.Series(["DERECHO PROCESAL PENAL", "DERECHO PROCESAL CONSTITUCIONAL", "DERECHO CIVIL CON JUICIO ORAL",
                                 "DERECHO", "EN CIENCIAS JURIDICAS", "FILOSOFIA DEL DERECHO", "DERECHO LABORAL"]),
                      SUBAREAS_DER, OTRAS_DER).tolist() \
        == ["Penal y criminología", "Constitucional y derechos humanos", "Procesal, civil y juicios orales",
            "Derecho / Ciencias jurídicas (general)", "Derecho / Ciencias jurídicas (general)", OTRAS_DER,
            "Fiscal, laboral y empresarial"]
    vs = vigentes_por_anio(djur, sub, COLORES_SUB)
    assert vs.iloc[-1].sum() == vd["DERECHO"].iloc[-1]  # las subáreas suman el total jurídico
    graficar_lineas(vs, Path("img/doctorados_derecho_subareas.png"), ultima, nombres={c: c for c in COLORES_SUB},
                    colores=COLORES_SUB, titulo="Doctorados en Derecho, Ciencias Jurídicas y Criminología, por subárea",
                    nota="subárea asignada por palabra clave en el nombre del programa", ncol=3)
    print(vs.to_markdown())
    estados = sorted(der["estado"].dropna().unique())
    ve = vigentes_por_anio(der, der["estado"], dict.fromkeys(estados))
    assert len(estados) == 32 and ve.iloc[-1].sum() == v["DERECHO"].iloc[-1]  # los estados suman el total nacional
    graficar_facetas(ve, Path("img/derecho_por_estado.png"), ultima)
    print(ve.rename(columns=lambda e: ESTADO_CORTO.get(e, e.title())).T.to_markdown())

    vig = djur["estatus"] == "VIGENTE"
    for s in COLORES_SUB:
        print(s, "->", nombre_limpio(djur.loc[vig & (sub == s), "programa"]).value_counts().head(6).to_dict())
