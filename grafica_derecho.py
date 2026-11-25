"""Gráfica: RVOE de Licenciatura en Derecho otorgados por año y modalidad.
Uso: python -I grafica_derecho.py  -> img/derecho_por_anio.png (+ tabla markdown en stdout)
"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DESDE, HASTA = 2000, 2026
MODALIDADES = {"ESCOLARIZADA": "#2a78d6", "MIXTA": "#eb6834", "NO ESCOLARIZADA": "#1baf7a"}
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

def licenciatura_derecho(u):
    # SIRVOES anota el nombre: "DERECHO (LICENCIATURA MIXTA)", "DERECHO (RETIRADO)"...
    prog = u["programa"].str.replace(r"\(.*?\)", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
    return u[(u["nivel"] == "LICENCIATURA") & (prog == "DERECHO")]

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
