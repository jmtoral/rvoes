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
    fig.text(0.01, 0.01, f"{CREDITO}.\nSolo RVOE federales propios (sin acuerdos/decretos institucionales); {nota}.\n"
             f"Solo se descuentan retiros registrados en SIRVOES.  {HASTA} al {ultima_fecha}.", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.07, 0.83, 1))
    fig.savefig(out, facecolor=SURFACE)

# Licenciaturas de ingeniería por tipo. El orden importa: "INDUSTRIAL Y DE SISTEMAS" -> industrial,
# "QUIMICO Y DE SISTEMAS" -> química, "SISTEMAS ELECTRONICOS" -> electrónica (antes que software).
TIPOS_ING = [
    ("Industrial y logística", r"INDUSTRIAL|LOGISTIC|SUMINISTRO|GESTION EMPRESARIAL|NEGOCIOS|PRODUCCION"),
    ("Química, ambiental y bio", r"QUIMIC|AMBIENTAL|BIO|ALIMENT|ENERG|SUSTENTAB|AGRO|PETROLE|MINER|GEOL"),
    ("Mecatrónica, mecánica y electrónica", r"MECATRON|MECANIC|ROBOT|ELECTR|AUTOMOTRIZ|MANUFACTURA|AERO|AUTOMATIZ|SEMICONDUCT"),
    ("Software, sistemas y datos", r"COMPUTACI|SOFTWARE|SISTEMAS|INFORMATIC|INFORMACION|DATOS|INTELIGENCIA|CIBER|REDES|"
                                   r"APLICACIONES|TELEMATIC|VIDEOJUEGO|TELECOMUNICAC|DIGITAL|PROGRAMACION|NUBE|MULTIMEDIA|ANIMACION"),
    ("Civil y arquitectura", r"CIVIL|ARQUITECT|CONSTRUC|TOPOGRAF"),
]
OTRAS_ING = "Otras ingenierías"
COLORES_ING = dict(zip([t for t, _ in TIPOS_ING] + [OTRAS_ING],
                       ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))

ESTADO_CORTO = {"MÉXICO": "Estado de México", "CIUDAD DE MÉXICO": "Ciudad de México",
                "VERACRUZ DE IGNACIO DE LA LLAVE": "Veracruz", "COAHUILA DE ZARAGOZA": "Coahuila",
                "MICHOACÁN DE OCAMPO": "Michoacán", "SAN LUIS POTOSI": "San Luis Potosí"}

def graficar_facetas(t, out, ultima_fecha, ncols=8, comun=False, referencia=None, fmt="{:,.0f}", fuente_extra="",
                     titulo="Licenciatura en Derecho por estado: programas vigentes en cada año",
                     subtitulo="Acumulado de RVOE federales otorgados menos los retirados, al cierre de cada año. "
                               "Cifra grande = vigentes hoy. Cada panel tiene su propia escala vertical."):
    """Small multiples: una línea por estado, ordenados de mayor a menor.
    comun=True: misma escala Y en todos los paneles. referencia: Serie (p. ej. nacional) en gris en cada panel."""
    t = t[t.iloc[-1].sort_values(ascending=False).index]
    tope = max(t.values.max(), referencia.max() if referencia is not None else 0) * 1.1
    nrows = -(-len(t.columns) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 2.2 * nrows + 1.4), dpi=150, facecolor=SURFACE, sharex=True)
    for ax, e in zip(axes.flat, t.columns):
        y = t[e]
        ax.set_facecolor(SURFACE)
        ax.fill_between(y.index, y, color="#2a78d6", alpha=0.1, linewidth=0, zorder=2)
        ax.plot(y.index, y, color="#2a78d6", linewidth=2, solid_capstyle="round", zorder=3)
        ax.scatter([HASTA], [y.iloc[-1]], s=24, color="#2a78d6", edgecolor=SURFACE, linewidth=1.2, zorder=4)
        ax.set_title(ESTADO_CORTO.get(e, e.title()), loc="left", fontsize=9.5, color=INK, pad=3)
        if referencia is not None:
            ax.plot(referencia.index, referencia, color="#a3a29c", linewidth=1.2, zorder=2.5)
        ax.text(0.02, 0.97, fmt.format(y.iloc[-1]), transform=ax.transAxes, fontsize=13, weight="bold", color=INK, va="top")
        if comun:
            ax.set_ylim(0, tope)
            ax.set_yticks([0, round(tope / 2.2, 1), round(tope / 1.1, 1)])
        else:
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
    fig.text(0.01, 0.99, titulo, va="top",
             fontsize=15, weight="bold", color=INK)
    fig.text(0.01, 0.955, subtitulo, va="top", fontsize=10, color=INK2)
    fig.text(0.01, 0.008, f"{CREDITO}{fuente_extra}.\nSolo RVOE federales propios (sin acuerdos/decretos institucionales); programa con nombre exacto \"Derecho\". "
             f"Solo se descuentan retiros registrados en SIRVOES. {HASTA} al {ultima_fecha}.", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.035, 1, 0.94), h_pad=1.6, w_pad=1.2)
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
    fig.text(0.01, 0.01, f"{CREDITO}. Fecha = otorgamiento del RVOE.\n"
             f"Solo RVOE federales propios (sin acuerdos/decretos institucionales).  * {HASTA} parcial: registros al {ultima_fecha}.",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, facecolor=SURFACE)

if __name__ == "__main__":
    todos = pd.read_csv("data/rvoes.csv", dtype=str)
    ultima = pd.to_datetime(todos["fecha_otorgamiento"], errors="coerce").max().strftime("%d-%m-%Y")
    # Solo RVOE propios: los programas bajo acuerdo/decreto institucional (Tec, UVM, UNITEC, Anáhuac...) llevan la
    # fecha del acuerdo (1952, 1988), no la del programa, y aparecerían como existentes desde entonces.
    propio = todos["rvoe"].str.fullmatch(r"\d{6,}", na=False)  # "142" a secas es el ACUERDO 142 (UNITEC)
    u = todos[propio]
    vig_todos = todos["estatus"] == "VIGENTE"
    print("vigentes excluidos por acuerdo/decreto, por nivel:",
          todos[vig_todos & ~propio]["nivel"].value_counts().to_dict(), "de", todos[vig_todos]["nivel"].value_counts().to_dict())
    der = licenciatura_derecho(u)
    t = tabla(der)
    assert t.values.sum() > 0.9 * len(der[pd.to_datetime(der["fecha_otorgamiento"], errors="coerce").dt.year >= DESDE])
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

    # Tasa por 100 mil habitantes (población a mitad de año, CONAPO; ver poblacion_conapo.py)
    pob = pd.read_csv("data/poblacion_conapo.csv").pivot(index="anio", columns="estado", values="poblacion").loc[ve.index]
    assert set(pob.columns) == set(ve.columns)
    tasa = ve / pob[ve.columns] * 1e5
    nacional = ve.sum(axis=1) / pob.sum(axis=1) * 1e5
    graficar_facetas(tasa, Path("img/derecho_por_estado_tasa.png"), ultima, comun=True, referencia=nacional, fmt="{:.1f}", fuente_extra=" y de CONAPO (población)",
                     titulo="Licenciatura en Derecho por estado: programas vigentes por cada 100 mil habitantes",
                     subtitulo=f"Programas vigentes al cierre de cada año / población a mitad de año (CONAPO) × 100,000. "
                               f"Gris = tasa nacional ({nacional.iloc[-1]:.1f} en {HASTA}). Misma escala en todos los paneles.")
    print(tasa.loc[[2000, 2010, 2020, HASTA]].T.sort_values(HASTA, ascending=False).round(2).to_markdown())
    print("nacional:", nacional.loc[[2000, 2010, 2020, HASTA]].round(2).to_dict())

    ing = lic[nombre_limpio(lic["programa"]).str.contains("INGENIER")]
    tipo = clasificar(ing["programa"], TIPOS_ING, OTRAS_ING)
    assert clasificar(pd.Series(["INGENIERIA INDUSTRIAL Y DE SISTEMAS", "INGENIERO QUIMICO Y DE SISTEMAS",
                                 "INGENIERO EN SISTEMAS ELECTRONICOS", "INGENIERIA EN SISTEMAS COMPUTACIONALES (RETIRADO)",
                                 "INGENIERIA FINANCIERA"]), TIPOS_ING, OTRAS_ING).tolist() \
        == ["Industrial y logística", "Química, ambiental y bio", "Mecatrónica, mecánica y electrónica",
            "Software, sistemas y datos", OTRAS_ING]
    vi = vigentes_por_anio(ing, tipo, COLORES_ING)
    graficar_lineas(vi, Path("img/ingenierias_acumulados.png"), ultima, nombres={c: c for c in COLORES_ING},
                    colores=COLORES_ING, titulo="Licenciaturas en ingeniería por tipo: programas vigentes en cada año",
                    nota="licenciaturas con \"ingeniería\" en el nombre; tipo por palabra clave", ncol=3)
    print(vi.to_markdown())
    lic_tot = vigentes_por_anio(lic, pd.Series("LIC", index=lic.index), {"LIC": None})["LIC"]
    print("ingenierías / licenciaturas (%):", (vi.sum(axis=1) / lic_tot * 100).loc[[2000, 2010, 2020, HASTA]].round(1).to_dict())
    # Ingenierías vs. licenciaturas jurídicas (Derecho, Ciencias Jurídicas, Criminología...), solo RVOE propios
    lic_nom = nombre_limpio(lic["programa"])
    grupo = pd.Series(None, index=lic.index, dtype=object)
    grupo[lic_nom.str.contains(JURIDICO) & ~lic_nom.str.contains("INGENIER")] = "JUR"
    grupo[lic_nom.str.contains("INGENIER")] = "ING"
    col_vs = {"JUR": "#2a78d6", "ING": "#eb6834"}
    vv = vigentes_por_anio(lic, grupo, col_vs)
    graficar_lineas(vv, Path("img/ingenierias_vs_juridicas.png"), ultima,
                    nombres={"JUR": "Derecho, C. Jurídicas y Criminología", "ING": "Todas las ingenierías"}, colores=col_vs,
                    titulo="Licenciaturas: ingenierías vs. Derecho, Ciencias Jurídicas y Criminología",
                    nota="grupos por palabra clave en el nombre del programa", ncol=2)
    print(vv.rename(columns={"JUR": "Jurídicas", "ING": "Ingenierías"}).to_markdown())

    vig = ing["estatus"] == "VIGENTE"
    for t in COLORES_ING:
        print(t, "->", nombre_limpio(ing.loc[vig & (tipo == t), "programa"]).value_counts().head(5).to_dict())
    print(ve.rename(columns=lambda e: ESTADO_CORTO.get(e, e.title())).T.to_markdown())

    vig = djur["estatus"] == "VIGENTE"
    for s in COLORES_SUB:
        print(s, "->", nombre_limpio(djur.loc[vig & (sub == s), "programa"]).value_counts().head(6).to_dict())
