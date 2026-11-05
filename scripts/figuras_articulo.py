"""Genera las figuras de resultados del artículo a partir de los expedientes.

No entrena ni calcula nada: dibuja lo que ya está en los artefactos, así que
cada valor se puede rastrear hasta su fuente.

    importancia_shap.png      artefactos/{,hogares/}reporte_explicabilidad.md
    tvp_por_vivienda.png      artefactos/hogares/equidad/metricas_equidad.json
    estabilidad_semillas.png  artefactos/estabilidad/*/estabilidad.json

Sigue el método de visualización del proyecto (D40): la API orientada a objetos
de matplotlib en lugar de `pyplot`, y tamaño, DPI y metadatos fijos, para que dos
corridas produzcan PNG idénticos byte a byte. Los PNG sí se versionan, a
diferencia de los artefactos, para que el artículo compile sin los datos (D62).

Uso:
    python scripts/figuras_articulo.py [directorio_de_salida]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter

RAIZ = Path(__file__).resolve().parents[1]
ARTEFACTOS = RAIZ / "artefactos"
SALIDA_POR_DEFECTO = RAIZ / "articulo" / "figuras"

# Paleta de referencia del método de visualización, sobre fondo blanco de
# imprenta. El naranja se reserva para la única combinación inestable.
_SUPERFICIE = "#ffffff"
_SERIE = "#2a78d6"
_EXCEPCION = "#eb6834"
_RAMPA = ("#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b")
_FUERA = "#f4f3f0"
_TINTA = "#0b0b0b"
_TINTA_SECUNDARIA = "#52514e"
_LINEA = "#d9d8d3"

_ANCHO = 7.0  # pulgadas
_DPI = 300
# Sin versión de software en el PNG: los bytes no cambian con un parche de
# matplotlib que no altera el dibujo.
_METADATOS_PNG = {"Software": None}
_ESTILO = {
    "font.family": "DejaVu Sans",
    "font.size": 8.5,
    "axes.edgecolor": _LINEA,
    "axes.labelcolor": _TINTA_SECUNDARIA,
    "xtick.color": _TINTA_SECUNDARIA,
    "ytick.color": _TINTA,
    "axes.spines.top": False,
    "axes.spines.right": False,
}


def _coma(valor: float, decimales: int = 3) -> str:
    return f"{valor:.{decimales}f}".replace(".", ",")


def _figura(alto: float) -> Figure:
    figura = Figure(figsize=(_ANCHO, alto), dpi=_DPI, facecolor=_SUPERFICIE)
    FigureCanvasAgg(figura)
    return figura


def _guardar(figura: Figure, ruta: Path) -> None:
    figura.tight_layout()
    figura.savefig(ruta, dpi=_DPI, facecolor=_SUPERFICIE, metadata=_METADATOS_PNG)


def _importancia(ruta: Path, n: int = 8) -> list[tuple[str, float]]:
    """Las `n` primeras filas de la tabla del reporte de explicabilidad."""
    filas = re.findall(
        r"^\| \d+ \| (.+?) \| `\w+` \| ([\d,]+) \|$",
        ruta.read_text(encoding="utf-8"),
        flags=re.M,
    )
    return [(nombre, float(valor.replace(",", "."))) for nombre, valor in filas[:n]]


def importancia_shap(destino: Path) -> None:
    """Dos paneles con una misma escala: la longitud se compara entre pilotos."""
    paneles = [
        ("Aruba (1 vivienda)", _importancia(ARTEFACTOS / "reporte_explicabilidad.md")),
        (
            "Multi-hogar (9 viviendas)",
            _importancia(ARTEFACTOS / "hogares" / "reporte_explicabilidad.md"),
        ),
    ]
    tope = max(valor for _, datos in paneles for _, valor in datos) * 1.2
    figura = _figura(2.7)
    for ejes, (titulo, datos) in zip(figura.subplots(1, 2), paneles):
        nombres = [
            re.sub(r"^Movimiento en (el |la )?", "", nombre).capitalize()
            for nombre, _ in datos
        ]
        valores = [valor for _, valor in datos]
        posiciones = list(range(len(datos)))
        ejes.barh(posiciones, valores, height=0.62, color=_SERIE)
        ejes.set_yticks(posiciones, nombres)
        ejes.invert_yaxis()
        ejes.set_xlim(0, tope)
        ejes.xaxis.set_visible(False)
        ejes.spines["bottom"].set_visible(False)
        ejes.tick_params(axis="y", length=0)
        ejes.set_title(titulo, loc="left", fontsize=9, fontweight="bold", color=_TINTA)
        # En el artículo no hay tabla que acompañe a la figura: cada barra lleva
        # su valor.
        for i, valor in enumerate(valores):
            ejes.text(
                valor + tope * 0.012, i, _coma(valor, 4),
                va="center", color=_TINTA_SECUNDARIA, fontsize=7.5,
            )
    _guardar(figura, destino / "importancia_shap.png")


def tvp_por_vivienda(destino: Path) -> None:
    """TVP de cada vivienda por actividad, y la diferencia en la última columna.

    La diferencia es un único valor por actividad; lo que varía por vivienda es
    la TVP. Por eso el color codifica la tasa y la diferencia va como columna.
    """
    datos = json.loads(
        (ARTEFACTOS / "hogares" / "equidad" / "metricas_equidad.json").read_text(
            encoding="utf-8"
        )
    )
    filas = sorted(
        (
            r
            for r in datos["resultados"]
            if r["subgrupo"] == "hogar"
            and r["metrica"] == "true_positive_rate_difference"
            and r["valor_observado"] is not None
        ),
        key=lambda r: -r["valor_observado"],
    )
    viviendas = sorted({t["categoria"] for r in filas for t in r["tasas"]})
    mapa = LinearSegmentedColormap.from_list("rampa", _RAMPA)

    figura = _figura(0.31 * len(filas) + 1.1)
    ejes = figura.subplots()
    for i, fila in enumerate(filas):
        tasas = {t["categoria"]: t for t in fila["tasas"] if t["tasa"] == "tvp"}
        for j, vivienda in enumerate(viviendas):
            tasa = tasas.get(vivienda)
            if tasa and tasa["en_comparacion"]:
                valor = tasa["numerador"] / tasa["denominador"]
                ejes.add_patch(
                    Rectangle((j, i), 1, 1, facecolor=mapa(valor), edgecolor="white", linewidth=1.5)
                )
                ejes.text(
                    j + 0.5, i + 0.5, _coma(valor, 2), ha="center", va="center", fontsize=7.5,
                    color="white" if valor >= 0.5 else _TINTA,
                )
            else:
                ejes.add_patch(
                    Rectangle(
                        (j, i), 1, 1, facecolor=_FUERA, edgecolor="white",
                        linewidth=1.5, hatch="////", alpha=0.9,
                    )
                )
        ejes.text(
            len(viviendas) + 0.55, i + 0.5, _coma(fila["valor_observado"]),
            ha="center", va="center", fontsize=8,
            fontweight="normal" if fila["cumple"] else "bold",
            color=_TINTA_SECUNDARIA if fila["cumple"] else _TINTA,
        )
    ejes.set_xlim(0, len(viviendas) + 1.1)
    ejes.set_ylim(len(filas), 0)
    ejes.set_xticks(
        [j + 0.5 for j in range(len(viviendas))] + [len(viviendas) + 0.55],
        viviendas + ["Dif. TVP"],
    )
    ejes.xaxis.tick_top()
    ejes.tick_params(axis="both", length=0)
    ejes.set_yticks(
        [i + 0.5 for i in range(len(filas))],
        [fila["actividad"].replace("_", " ") for fila in filas],
    )
    for lado in ejes.spines.values():
        lado.set_visible(False)
    ejes.legend(
        handles=[
            Patch(
                facecolor=_FUERA, hatch="////", edgecolor="#b8b7b1",
                label="Menos de 30 casos: fuera de la comparación",
            )
        ],
        loc="upper center", bbox_to_anchor=(0.45, -0.01), frameon=False, fontsize=7.5,
    )
    _guardar(figura, destino / "tvp_por_vivienda.png")


def estabilidad_semillas(destino: Path) -> None:
    """Las combinaciones que incumplen con la semilla sellada, por corrida."""
    grupos = []
    for archivo, piloto in (("config", "Aruba"), ("config.hogares", "Multi-hogar")):
        datos = json.loads(
            (ARTEFACTOS / "estabilidad" / archivo / "estabilidad.json").read_text(
                encoding="utf-8"
            )
        )
        sellada = datos["semillas"].index(datos["semilla_sellada"])
        incumplen = [c for c in datos["combinaciones"] if c["cumple"][sellada] is False]
        for subgrupo, nombre in (
            ("hogar", "entre viviendas"),
            ("franja_horaria", "entre franjas horarias"),
            ("tipo_dia", "entre tipos de día"),
        ):
            filas = sorted(
                (c for c in incumplen if c["subgrupo"] == subgrupo),
                key=lambda c: -c["media"],
            )
            if filas:
                grupos.append((f"{piloto}, {nombre}", filas, sellada))

    total = sum(len(filas) for _, filas, _ in grupos)
    figura = _figura(0.17 * total + 0.26 * len(grupos) + 0.9)
    ejes = figura.subplots()
    y, posiciones, etiquetas = 0.0, [], []
    for titulo, filas, sellada in grupos:
        ejes.text(
            0.004, y, titulo, fontsize=8.5, fontweight="bold", color=_TINTA,
            ha="left", va="center", transform=ejes.get_yaxis_transform(), zorder=5,
            bbox={"facecolor": _SUPERFICIE, "edgecolor": "none", "pad": 1.5},
        )
        y += 1
        for c in filas:
            inestable = c["clasificacion"] == "inestable"
            color = _EXCEPCION if inestable else _SERIE
            ejes.plot([c["minimo"], c["maximo"]], [y, y], color=color, linewidth=1, alpha=0.45, zorder=1)
            otras = [v for i, v in enumerate(c["valores"]) if i != sellada]
            ejes.scatter(otras, [y] * len(otras), s=13, color=color, alpha=0.55, linewidths=0, zorder=2)
            ejes.scatter(
                [c["valores"][sellada]], [y], s=24, marker="D", color=_TINTA,
                linewidths=0.6, edgecolors=_SUPERFICIE, zorder=3,
            )
            metrica = "TVP" if c["metrica"].startswith("true") else "TFP"
            posiciones.append(y)
            etiquetas.append(f"{c['actividad'].replace('_', ' ')} ({metrica})")
            if inestable:
                ejes.text(
                    c["maximo"] + 0.012, y,
                    f"incumple en {c['incumple']} de {c['evaluables']} semillas",
                    color=_TINTA, fontsize=7.5, va="center",
                )
            y += 1
        y += 0.5
    ejes.axvline(0.10, color=_TINTA_SECUNDARIA, linewidth=1, linestyle=(0, (4, 3)), zorder=0)
    ejes.text(0.103, -0.75, "Umbral 0,10", color=_TINTA_SECUNDARIA, fontsize=7.5, va="center")
    ejes.set_yticks(posiciones, etiquetas, fontsize=7.5)
    ejes.tick_params(axis="y", length=0)
    ejes.set_ylim(y - 0.5, -1.2)
    ejes.set_xlim(0, 0.92)
    ejes.xaxis.set_major_formatter(FuncFormatter(lambda v, _: _coma(v, 1)))
    ejes.grid(axis="x", color=_LINEA, linewidth=0.5)
    ejes.set_axisbelow(True)
    ejes.spines["left"].set_visible(False)
    ejes.set_xlabel("Diferencia entre la mejor y la peor categoría")
    ejes.legend(
        handles=[
            Line2D(
                [], [], marker="D", color="none", markerfacecolor=_TINTA,
                markeredgecolor=_SUPERFICIE, markersize=5.5, label="Semilla sellada (42)",
            ),
            Line2D(
                [], [], marker="o", color="none", markerfacecolor=_SERIE,
                markeredgecolor="none", alpha=0.7, markersize=5,
                label="Otras semillas: incumple en las diez",
            ),
            Line2D(
                [], [], marker="o", color="none", markerfacecolor=_EXCEPCION,
                markeredgecolor="none", alpha=0.8, markersize=5,
                label="Otras semillas: inestable",
            ),
        ],
        loc="lower right", frameon=True, facecolor=_SUPERFICIE, edgecolor=_LINEA, fontsize=7.5,
    )
    _guardar(figura, destino / "estabilidad_semillas.png")


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    destino = Path(argumentos[0]) if argumentos else SALIDA_POR_DEFECTO
    destino.mkdir(parents=True, exist_ok=True)
    with matplotlib.rc_context(_ESTILO):
        importancia_shap(destino)
        tvp_por_vivienda(destino)
        estabilidad_semillas(destino)
    print(f"Figuras en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
