"""Gráficas de licenciaturas:
- img/derecho_por_anio.png: RVOE de Derecho otorgados por año y modalidad.
- img/vigentes_acumulados.png: programas vigentes en cada año, top 5 licenciaturas.
Uso: python -I graficas.py  (imprime las tablas en markdown)
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DESDE, HASTA = 2000, 2026
MODALIDADES = {"ESCOLARIZADA": "#2a78d6", "MIXTA": "#eb6834", "NO ESCOLARIZADA": "#1baf7a"}
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

CARRERAS = {"DERECHO": "#2a78d6", "ADMINISTRACION DE EMPRESAS": "#eb6834", "PEDAGOGIA": "#1baf7a",
             "MERCADOTECNIA": "#eda100", "PSICOLOGIA": "#e87ba4"}
NOMBRES = {"DERECHO": "Derecho", "ADMINISTRACION DE EMPRESAS": "Administración de Empresas",
           "PEDAGOGIA": "Pedagogía", "MERCADOTECNIA": "Mercadotecnia", "PSICOLOGIA": "Psicología"}

def nombre_limpio(programa):
    # SIRVOES anota el nombre: "DERECHO (LICENCIATURA MIXTA)", "DERECHO (RETIRADO)"...
    return programa.str.replace(r"\(.*?\)", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()

def licenciatura_derecho(u):
    return u[(u["nivel"] == "LICENCIATURA") & (nombre_limpio(u["programa"]) == "DERECHO")]

def vigentes_por_anio(u):
    """Programas vigentes al cierre de cada año = otorgados hasta ese año - retirados hasta ese año."""
    lic = u[u["nivel"] == "LICENCIATURA"].assign(carrera=lambda x: nombre_limpio(x["programa"]))
    lic = lic[lic["carrera"].isin(CARRERAS)]
    ao = pd.to_datetime(lic["fecha_otorgamiento"], errors="coerce").dt.year
    ar = pd.to_datetime(lic["fecha_retiro"], errors="coerce").dt.year
    return pd.DataFrame({c: [((lic["carrera"] == c) & (ao <= y) & ~(ar <= y)).sum() for y in range(DESDE, HASTA + 1)]
                         for c in CARRERAS}, index=range(DESDE, HASTA + 1))

def separar(valores, minimo):
    """Empuja hacia arriba las etiquetas finales que quedarían encimadas."""
    orden = sorted(valores, key=valores.get)
    pos, prev = {}, None
    for k in orden:
        pos[k] = valores[k] if prev is None else max(valores[k], prev + minimo)
        prev = pos[k]
    return pos

def graficar_lineas(t, out, ultima_fecha):
    fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for c, color in CARRERAS.items():
        ax.plot(t.index, t[c], color=color, linewidth=2, solid_capstyle="round", solid_joinstyle="round", zorder=3)
        ax.scatter([HASTA], [t[c].iloc[-1]], s=40, color=color, edgecolor=SURFACE, linewidth=1.5, zorder=4)
    pos = separar({c: t[c].iloc[-1] for c in CARRERAS}, minimo=t.values.max() * 0.045)
    for c, y in pos.items():
        ax.annotate(f"{NOMBRES[c]}  {t[c].iloc[-1]:,}", (HASTA, t[c].iloc[-1]), xytext=(HASTA + 0.5, y),
                    textcoords="data", va="center", fontsize=9, color=INK, annotation_clip=False)
    ax.set_title("Licenciaturas con más RVOE: programas vigentes en cada año", loc="left", fontsize=14, color=INK, pad=28, weight="bold")
    ax.text(0, 1.04, "Acumulado de RVOE federales otorgados menos los retirados, al cierre de cada año",
            transform=ax.transAxes, fontsize=10, color=INK2)
    ax.legend([plt.Line2D([], [], color=col, linewidth=2) for col in CARRERAS.values()], NOMBRES.values(),
              loc="upper left", frameon=False, fontsize=9, labelcolor=INK2, ncol=5, bbox_to_anchor=(0, 1.0))
    ax.set_xticks(range(DESDE, HASTA + 1, 2))
    ax.tick_params(colors=INK2, labelsize=9, length=0)
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_xlim(DESDE - 0.5, HASTA + 0.3)
    ax.set_ylim(0, t.values.max() * 1.15)
    fig.text(0.01, 0.01, f"Fuente: SEP, SIRVOES y DGAIR. Solo RVOE federales; nombre exacto del programa (sin variantes). "
             f"Solo se descuentan retiros registrados en SIRVOES.  {HASTA} al {ultima_fecha}.", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 0.83, 1))
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
    fig.text(0.01, 0.01, f"Fuente: SEP, SIRVOES y DGAIR (federales vigentes). Fecha = otorgamiento del RVOE. "
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

    v = vigentes_por_anio(u)
    assert v["DERECHO"].iloc[-1] <= (der["estatus"] == "VIGENTE").sum()  # no puede haber más vigentes que hoy
    graficar_lineas(v, Path("img/vigentes_acumulados.png"), ultima)
    print(v.rename(columns=NOMBRES).to_markdown())
