"""Estabilidad de la equidad entre semillas: análisis de sensibilidad (D61).

El veredicto de equidad de un expediente sale de un único entrenamiento con
la semilla sellada. Una disparidad cercana al umbral puede ser del sistema o
del azar del entrenamiento, y con una sola corrida no se distingue. Este
análisis reentrena el mismo modelo con varias semillas y mide, para cada
combinación que decide el veredicto (subgrupo × actividad × métrica), en
cuántas incumple su umbral.

Lo único que varía es el `random_state` del modelo. Datos, partición,
umbrales, subgrupos, soporte mínimo y PYTHONHASHSEED quedan como los declara
cada configuración, y las métricas se calculan con `evaluar_equidad`, la
misma función del paso 4. Las corridas no explican inferencias ni escriben
bitácora: no son expedientes y no reemplazan el veredicto sellado.

Las semillas y la regla de lectura se declaran antes de correr, en
`estabilidad.yaml`, por la misma razón que los umbrales (D13).

Uso:
    python -m src.equidad.estabilidad --plan estabilidad.yaml
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

import yaml

from src.comun.utilidades import ahora_utc_iso, asegurar_directorio, escribir_json, hash_archivo

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.comun.datos import ParticionSupervisada
    from src.equidad.metricas_equidad import VeredictoEquidad

#: Lecturas posibles de una combinación, en el orden en que se reportan.
CLASIFICACIONES = (
    "incumplimiento estable",
    "inestable",
    "cumplimiento estable",
    "no evaluable",
)

_CLAVES_PLAN = {"configuraciones", "semillas", "regla", "salida"}
_CLAVES_REGLA = {"incumple_estable_desde", "cumple_estable_hasta"}


class PlanInvalido(ValueError):
    """El plan de estabilidad está incompleto o es incoherente."""


@dataclass(frozen=True)
class Regla:
    """Cómo se lee la proporción de semillas en que una combinación incumple."""

    incumple_estable_desde: float
    cumple_estable_hasta: float

    def clasificar(self, incumple: int, evaluables: int) -> str:
        """Lectura de una combinación que incumple en `incumple` de las
        `evaluables` semillas en que se pudo evaluar."""
        if evaluables == 0:
            return "no evaluable"
        proporcion = incumple / evaluables
        if proporcion >= self.incumple_estable_desde:
            return "incumplimiento estable"
        if proporcion <= self.cumple_estable_hasta:
            return "cumplimiento estable"
        return "inestable"


@dataclass(frozen=True)
class PlanEstabilidad:
    ruta: Path
    configuraciones: tuple[Path, ...]
    semillas: tuple[int, ...]
    regla: Regla
    salida: Path


def cargar_plan(ruta: str | Path) -> PlanEstabilidad:
    """Lee y valida `estabilidad.yaml`. Las rutas se resuelven contra la
    carpeta del plan.

    Raises:
        PlanInvalido: si falta o sobra una clave, si las semillas no son
            enteros distintos (al menos dos) o si la regla es incoherente.
    """
    ruta = Path(ruta)
    crudo = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(crudo, dict):
        raise PlanInvalido(f"{ruta}: se esperaba un mapa")
    if set(crudo) != _CLAVES_PLAN:
        raise PlanInvalido(
            f"{ruta}: claves esperadas {sorted(_CLAVES_PLAN)}, "
            f"encontradas {sorted(crudo)}"
        )

    configuraciones = crudo["configuraciones"]
    if not configuraciones or not all(isinstance(c, str) for c in configuraciones):
        raise PlanInvalido("configuraciones: se esperaba una lista de rutas")

    semillas = crudo["semillas"]
    if (
        not isinstance(semillas, list)
        or not all(isinstance(s, int) and not isinstance(s, bool) for s in semillas)
        or len(semillas) < 2
        or len(set(semillas)) != len(semillas)
    ):
        raise PlanInvalido("semillas: se esperaban al menos dos enteros distintos")

    regla = crudo["regla"]
    if not isinstance(regla, dict) or set(regla) != _CLAVES_REGLA:
        raise PlanInvalido(f"regla: claves esperadas {sorted(_CLAVES_REGLA)}")
    desde, hasta = regla["incumple_estable_desde"], regla["cumple_estable_hasta"]
    if not all(isinstance(v, (int, float)) for v in (desde, hasta)) or not (
        0 <= hasta < desde <= 1
    ):
        raise PlanInvalido(
            "regla: se esperaba 0 <= cumple_estable_hasta < "
            "incumple_estable_desde <= 1"
        )

    base = ruta.resolve().parent
    return PlanEstabilidad(
        ruta=ruta,
        configuraciones=tuple(base / c for c in configuraciones),
        semillas=tuple(semillas),
        regla=Regla(float(desde), float(hasta)),
        salida=base / crudo["salida"],
    )


@dataclass(frozen=True)
class Combinacion:
    """Una combinación que decide el veredicto, a lo largo de las semillas.

    `valores` y `cumple` van en el orden de las semillas del plan; `None`
    donde la combinación no fue evaluable con esa semilla.
    """

    subgrupo: str
    actividad: str
    metrica: str
    umbral: float
    valores: tuple[float | None, ...]
    cumple: tuple[bool | None, ...]

    @property
    def evaluados(self) -> list[float]:
        return [v for v in self.valores if v is not None]

    @property
    def evaluables(self) -> int:
        return len(self.evaluados)

    @property
    def incumple(self) -> int:
        return sum(1 for c in self.cumple if c is False)

    def resumen(self, regla: Regla) -> dict[str, Any]:
        v = self.evaluados
        return {
            "subgrupo": self.subgrupo,
            "actividad": self.actividad,
            "metrica": self.metrica,
            "umbral": self.umbral,
            "valores": list(self.valores),
            "cumple": list(self.cumple),
            "evaluables": self.evaluables,
            "incumple": self.incumple,
            "media": statistics.fmean(v) if v else None,
            "desviacion": statistics.stdev(v) if len(v) > 1 else None,
            "minimo": min(v) if v else None,
            "maximo": max(v) if v else None,
            "clasificacion": regla.clasificar(self.incumple, self.evaluables),
        }


@dataclass(frozen=True)
class CorridaSemilla:
    semilla: int
    exactitud: float
    veredicto: "VeredictoEquidad"


@dataclass(frozen=True)
class Estabilidad:
    """Resultado del análisis para una configuración."""

    semillas: tuple[int, ...]
    semilla_sellada: int
    corridas: tuple[CorridaSemilla, ...]
    combinaciones: tuple[Combinacion, ...]


def preparar_datos(config: "Configuracion") -> "ParticionSupervisada":
    """La misma preparación que la precondición del procedimiento."""
    from src.comun.datos import (
        cargar_crudo,
        construir_caracteristicas,
        particionar,
        validar_esquema,
    )

    eventos = cargar_crudo(config)
    validar_esquema(eventos, config)
    return particionar(construir_caracteristicas(eventos, config), config)


def correr_semilla(
    particion: "ParticionSupervisada", config: "Configuracion", semilla: int
) -> CorridaSemilla:
    """Entrena el modelo declarado con otra semilla y evalúa su equidad.

    No usa `entrenar`: ese sella y serializa el modelo del expediente, y
    exige que su semilla sea la global. Aquí la semilla del modelo es
    justamente lo que varía, y nada se escribe.
    """
    import pandas as pd
    from sklearn.metrics import accuracy_score

    from src.comun.modelado import construir_estimador
    from src.equidad.metricas_equidad import evaluar_equidad

    estimador = construir_estimador(config)
    if "random_state" not in estimador.get_params():
        raise PlanInvalido(
            f"{type(estimador).__name__} no tiene random_state: no hay semilla "
            "que variar"
        )
    estimador.set_params(random_state=semilla)
    estimador.fit(particion.X_entrenamiento, particion.y_entrenamiento)
    predicciones = pd.Series(
        estimador.predict(particion.X_prueba),
        index=particion.X_prueba.index,
        name="prediccion",
    )
    veredicto = evaluar_equidad(
        particion.y_prueba, predicciones, particion.sensibles_prueba, config
    )
    return CorridaSemilla(
        semilla=semilla,
        exactitud=float(accuracy_score(particion.y_prueba, predicciones)),
        veredicto=veredicto,
    )


def combinar(corridas: Sequence[CorridaSemilla]) -> tuple[Combinacion, ...]:
    """Agrupa por combinación los resultados que deciden de cada corrida.

    Una combinación puede faltar en alguna corrida: el conjunto de
    actividades incluye las que el modelo predice aunque nunca ocurran, y eso
    depende de la semilla. Donde falta, cuenta como no evaluable.
    """
    claves: dict[tuple[str, str, str], float] = {}
    por_corrida = []
    for corrida in corridas:
        indice = {}
        for r in corrida.veredicto.resultados:
            if r.decide:
                clave = (r.subgrupo, r.actividad, r.metrica)
                claves.setdefault(clave, r.umbral)
                indice[clave] = r
        por_corrida.append(indice)

    combinaciones = []
    for clave in sorted(claves):
        resultados = [indice.get(clave) for indice in por_corrida]
        combinaciones.append(
            Combinacion(
                subgrupo=clave[0],
                actividad=clave[1],
                metrica=clave[2],
                umbral=claves[clave],
                valores=tuple(
                    r.valor_observado if r is not None else None for r in resultados
                ),
                cumple=tuple(r.cumple if r is not None else None for r in resultados),
            )
        )
    return tuple(combinaciones)


def analizar(
    config: "Configuracion", semillas: Sequence[int]
) -> Estabilidad:
    """Corre el análisis completo para una configuración.

    Raises:
        PlanInvalido: si la semilla sellada de la configuración no está entre
            las del plan. Sin ella, nada ancla el análisis al expediente.
    """
    if config.semilla not in semillas:
        raise PlanInvalido(
            f"{config.ruta_archivo.name}: la semilla sellada ({config.semilla}) "
            "tiene que estar entre las del plan"
        )
    particion = preparar_datos(config)
    corridas = tuple(correr_semilla(particion, config, s) for s in semillas)
    return Estabilidad(
        semillas=tuple(semillas),
        semilla_sellada=config.semilla,
        corridas=corridas,
        combinaciones=combinar(corridas),
    )


def comparar_con_expediente(
    estabilidad: Estabilidad, config: "Configuracion"
) -> dict[str, Any]:
    """Comprueba que la corrida con la semilla sellada reproduce las
    métricas del expediente, si existe. Es la prueba de que el análisis mide
    lo mismo que el paso 4."""
    ruta = Path(config.rutas.artefactos) / "equidad" / "metricas_equidad.json"
    if not ruta.exists():
        return {"expediente": str(ruta), "coincide": None}
    guardado = {
        (r["subgrupo"], r["actividad"], r["metrica"]): r["valor_observado"]
        for r in json.loads(ruta.read_text(encoding="utf-8"))["resultados"]
        if r["umbral"] is not None
    }
    i = estabilidad.semillas.index(estabilidad.semilla_sellada)
    calculado = {
        (c.subgrupo, c.actividad, c.metrica): c.valores[i]
        for c in estabilidad.combinaciones
    }
    distintas = sorted(
        "/".join(k)
        for k in set(guardado) | set(calculado)
        if guardado.get(k) != calculado.get(k)
    )
    return {"expediente": str(ruta), "coincide": not distintas, "distintas": distintas}


# --- Salida ------------------------------------------------------------------


def a_diccionario(
    estabilidad: Estabilidad, regla: Regla, procedencia: dict[str, Any]
) -> dict[str, Any]:
    return {
        **procedencia,
        "semillas": list(estabilidad.semillas),
        "semilla_sellada": estabilidad.semilla_sellada,
        "regla": {
            "incumple_estable_desde": regla.incumple_estable_desde,
            "cumple_estable_hasta": regla.cumple_estable_hasta,
        },
        "corridas": [
            {
                "semilla": c.semilla,
                "exactitud": c.exactitud,
                "veredicto": c.veredicto.estado,
                "incumplidas": len(c.veredicto.metricas_incumplidas()),
            }
            for c in estabilidad.corridas
        ],
        "combinaciones": [c.resumen(regla) for c in estabilidad.combinaciones],
    }


def generar_reporte(datos: dict[str, Any]) -> str:
    """Reporte Markdown legible a partir del diccionario de resultados."""
    from src.equidad.reporte import NOMBRES_METRICA
    from src.explicabilidad.lenguaje import formatear_decimal

    def _num(valor: float | None) -> str:
        return "—" if valor is None else formatear_decimal(valor, 3)

    def pct(proporcion: float) -> str:
        return f"{round(proporcion * 100)} %"

    sellada = datos["semilla_sellada"]
    i = datos["semillas"].index(sellada)
    regla = datos["regla"]
    n = len(datos["semillas"])
    comparacion = datos["comparacion_expediente"]
    reproduce = {True: "sí", False: "**NO**", None: "sin expediente para comparar"}[
        comparacion["coincide"]
    ]

    lineas = [
        f"# Estabilidad de la equidad entre semillas — `{datos['configuracion']}`",
        "",
        "> Análisis de sensibilidad declarado en `estabilidad.yaml` (D61). No es",
        f"> un expediente: el veredicto sellado es el de la semilla {sellada}.",
        "> Entre corridas solo cambia la semilla del modelo; datos, partición,",
        "> umbrales, subgrupos y soporte mínimo son los de la configuración.",
        "",
        f"- **Plan:** `{datos['plan']}` (SHA-256 `{datos['hash_plan'][:12]}`)",
        f"- **Configuración:** `{datos['configuracion']}` "
        f"(SHA-256 `{datos['hash_configuracion'][:12]}`)",
        f"- **Semillas:** {', '.join(str(s) for s in datos['semillas'])}",
        f"- **Regla:** incumplimiento estable si incumple en al menos el "
        f"{pct(regla['incumple_estable_desde'])} de las semillas en que es "
        f"evaluable; cumplimiento estable si incumple en a lo sumo el "
        f"{pct(regla['cumple_estable_hasta'])}; inestable en otro caso.",
        f"- **Reproduce el expediente con la semilla {sellada}:** {reproduce}",
        f"- **Fecha (UTC):** {datos['fecha']}",
        "",
        "## Veredicto de equidad por semilla",
        "",
        "| Semilla | Exactitud | Veredicto | Combinaciones que incumplen |",
        "|---:|---:|---|---:|",
    ]
    for c in datos["corridas"]:
        marca = " (sellada)" if c["semilla"] == sellada else ""
        lineas.append(
            f"| {c['semilla']}{marca} | {formatear_decimal(c['exactitud'], 3)} | "
            f"{c['veredicto'].replace('_', ' ')} | {c['incumplidas']} |"
        )

    combinaciones = datos["combinaciones"]
    lineas += ["", "## Lectura de las combinaciones que deciden", ""]
    lineas += ["| Lectura | Combinaciones |", "|---|---:|"]
    for clase in CLASIFICACIONES:
        total = sum(1 for c in combinaciones if c["clasificacion"] == clase)
        lineas.append(f"| {clase} | {total} |")

    def tabla(filas: list[dict[str, Any]], vacia: str) -> list[str]:
        if not filas:
            return [vacia]
        salida = [
            "| Subgrupo | Actividad | Métrica | Sellada | Media | Desv. est. "
            "| Mín. | Máx. | Incumple en | Lectura |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for c in filas:
            salida.append(
                f"| {c['subgrupo']} | {c['actividad']} | "
                f"{NOMBRES_METRICA[c['metrica']][1]} | {_num(c['valores'][i])} | "
                f"{_num(c['media'])} | {_num(c['desviacion'])} | "
                f"{_num(c['minimo'])} | {_num(c['maximo'])} | "
                f"{c['incumple']} de {c['evaluables']} | {c['clasificacion']} |"
            )
        return salida

    incumplen_sellada = [c for c in combinaciones if c["cumple"][i] is False]
    ocultas = [
        c
        for c in combinaciones
        if c["cumple"][i] is not False
        and c["clasificacion"] in ("incumplimiento estable", "inestable")
    ]
    lineas += [
        "",
        f"## Combinaciones que incumplen con la semilla sellada ({len(incumplen_sellada)})",
        "",
        *tabla(incumplen_sellada, "Ninguna."),
        "",
        "## Combinaciones que cumplen con la semilla sellada pero no de forma "
        f"estable ({len(ocultas)})",
        "",
        "Con otra semilla, estas combinaciones podrían haber incumplido. No",
        "cambian el veredicto sellado, pero muestran qué tan cerca estuvo.",
        "",
        *tabla(ocultas, "Ninguna."),
        "",
        f"_{n} semillas. Valores con tres decimales; la clasificación usa la "
        "proporción exacta._",
        "",
    ]
    return "\n".join(lineas)


def guardar(datos: dict[str, Any], destino: Path) -> tuple[Path, Path]:
    asegurar_directorio(destino)
    ruta_json = destino / "estabilidad.json"
    ruta_md = destino / "reporte_estabilidad.md"
    escribir_json(ruta_json, datos)
    with ruta_md.open("w", encoding="utf-8", newline="\n") as f:
        f.write(generar_reporte(datos))
    return ruta_json, ruta_md


def ejecutar_plan(plan: PlanEstabilidad) -> list[dict[str, Any]]:
    """Corre el plan completo y escribe un JSON y un reporte por
    configuración en `plan.salida/<nombre de la configuración>/`."""
    from src.comun.configuracion import cargar_configuracion
    from src.comun.semillas import (
        fijar_semilla_global,
        instantanea_entorno,
        verificar_pythonhashseed,
    )

    hash_plan = hash_archivo(plan.ruta)
    salidas = []
    for ruta_config in plan.configuraciones:
        config = cargar_configuracion(ruta_config)
        verificar_pythonhashseed(config.pythonhashseed)
        fijar_semilla_global(config.semilla)
        estabilidad = analizar(config, plan.semillas)
        datos = a_diccionario(
            estabilidad,
            plan.regla,
            {
                "plan": plan.ruta.name,
                "hash_plan": hash_plan,
                "configuracion": ruta_config.name,
                "hash_configuracion": hash_archivo(ruta_config),
                "fecha": ahora_utc_iso(),
                "entorno": instantanea_entorno(),
                "comparacion_expediente": comparar_con_expediente(estabilidad, config),
            },
        )
        guardar(datos, plan.salida / ruta_config.stem)
        salidas.append(datos)
    return salidas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", default="estabilidad.yaml")
    args = parser.parse_args(argv)
    plan = cargar_plan(args.plan)
    for datos in ejecutar_plan(plan):
        clases = {
            clase: sum(1 for c in datos["combinaciones"] if c["clasificacion"] == clase)
            for clase in CLASIFICACIONES
        }
        coincide = datos["comparacion_expediente"]["coincide"]
        print(
            f"{datos['configuracion']}: "
            + ", ".join(f"{v} {k}" for k, v in clases.items())
            + f" | reproduce el expediente: {coincide}"
        )
        if coincide is False:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
