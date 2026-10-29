"""Pruebas del análisis de estabilidad de la equidad entre semillas (D61).

Lo que importa probar: que la regla de lectura es la declarada, que el plan
del repositorio está anclado a la semilla sellada de cada configuración, y
que con esa semilla el análisis reproduce exactamente lo que mide el paso 4.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.comun.configuracion import cargar_configuracion
from src.equidad import estabilidad as E
from src.equidad.metricas_equidad import ResultadoMetrica, VeredictoEquidad

RAIZ = Path(__file__).resolve().parents[1]
REGLA = E.Regla(incumple_estable_desde=0.8, cumple_estable_hasta=0.2)


@pytest.mark.parametrize(
    ("incumple", "evaluables", "lectura"),
    [
        (10, 10, "incumplimiento estable"),
        (8, 10, "incumplimiento estable"),
        (4, 5, "incumplimiento estable"),
        (7, 10, "inestable"),
        (3, 10, "inestable"),
        (2, 10, "cumplimiento estable"),
        (0, 10, "cumplimiento estable"),
        (0, 0, "no evaluable"),
    ],
)
def test_la_regla_clasifica_por_la_proporcion_de_semillas(incumple, evaluables, lectura):
    assert REGLA.clasificar(incumple, evaluables) == lectura


def test_el_plan_del_repositorio_incluye_la_semilla_sellada_de_cada_configuracion():
    plan = E.cargar_plan(RAIZ / "estabilidad.yaml")
    assert plan.regla == REGLA
    assert len(plan.semillas) == 10
    for ruta in plan.configuraciones:
        assert cargar_configuracion(ruta).semilla in plan.semillas


@pytest.mark.parametrize(
    "cambio",
    [
        {"sobra": 1},
        {"semillas": [42, 42]},
        {"semillas": [42]},
        {"semillas": [42, True]},
        {"regla": {"incumple_estable_desde": 0.2, "cumple_estable_hasta": 0.8}},
        {"regla": {"incumple_estable_desde": 0.8}},
    ],
)
def test_el_plan_rechaza_lo_que_no_se_puede_leer(cambio, tmp_path):
    crudo = yaml.safe_load((RAIZ / "estabilidad.yaml").read_text(encoding="utf-8"))
    ruta = tmp_path / "estabilidad.yaml"
    ruta.write_text(yaml.safe_dump({**crudo, **cambio}), encoding="utf-8")
    with pytest.raises(E.PlanInvalido):
        E.cargar_plan(ruta)


def _resultado(actividad: str, valor: float | None) -> ResultadoMetrica:
    return ResultadoMetrica(
        metrica="true_positive_rate_difference",
        subgrupo="franja_horaria",
        actividad=actividad,
        sentido="diferencia",
        umbral=0.1,
        valor_observado=valor,
        cumple=None if valor is None else valor <= 0.1,
        tasas=(),
        motivo="" if valor is not None else "sin soporte",
    )


def test_combinar_cuenta_como_no_evaluable_la_combinacion_que_falta():
    corridas = [
        E.CorridaSemilla(1, 0.5, VeredictoEquidad("no_aprueba", (
            _resultado("Cook", 0.30), _resultado("Read", 0.05),
        ))),
        E.CorridaSemilla(2, 0.5, VeredictoEquidad("no_aprueba", (
            _resultado("Cook", 0.20),
        ))),
    ]
    cook, read = E.combinar(corridas)
    assert (cook.actividad, cook.incumple, cook.evaluables) == ("Cook", 2, 2)
    assert (read.valores, read.evaluables) == ((0.05, None), 1)
    resumen = cook.resumen(REGLA)
    assert resumen["media"] == pytest.approx(0.25)
    assert resumen["minimo"] == 0.20 and resumen["maximo"] == 0.30
    assert resumen["clasificacion"] == "incumplimiento estable"


def test_analizar_exige_la_semilla_sellada(config_piloto):
    with pytest.raises(E.PlanInvalido, match="semilla sellada"):
        E.analizar(config_piloto, [1, 2])


def test_con_la_semilla_sellada_reproduce_el_paso_4(config_piloto):
    """El análisis tiene que medir lo mismo que el procedimiento: con la
    semilla sellada, las métricas son idénticas a las del modelo que sella la
    precondición."""
    from src.comun.modelado import entrenar, predecir_con_confianza
    from src.equidad.metricas_equidad import evaluar_equidad

    particion = E.preparar_datos(config_piloto)
    corrida = E.correr_semilla(particion, config_piloto, config_piloto.semilla)

    modelo = entrenar(particion.X_entrenamiento, particion.y_entrenamiento, config_piloto)
    predicciones, _ = predecir_con_confianza(modelo, particion.X_prueba)
    paso_4 = evaluar_equidad(
        particion.y_prueba, predicciones, particion.sensibles_prueba, config_piloto
    )
    assert [r.a_diccionario() for r in corrida.veredicto.resultados] == [
        r.a_diccionario() for r in paso_4.resultados
    ]


def test_la_semilla_cambia_el_modelo_y_no_los_denominadores(config_piloto):
    """Los denominadores de las tasas dependen de las etiquetas reales, no de
    las predicciones: qué es evaluable no cambia entre semillas."""
    particion = E.preparar_datos(config_piloto)
    a = E.correr_semilla(particion, config_piloto, config_piloto.semilla)
    b = E.correr_semilla(particion, config_piloto, config_piloto.semilla + 1)

    def denominadores(corrida):
        return {
            (r.subgrupo, r.actividad, t.tasa, t.categoria): t.denominador
            for r in corrida.veredicto.resultados
            if r.decide
            for t in r.tasas
            if t.tasa == "tvp"
        }

    assert denominadores(a) == denominadores(b)


def test_el_reporte_marca_la_semilla_sellada_y_se_escribe_aparte(config_piloto, tmp_path):
    semillas = [config_piloto.semilla, config_piloto.semilla + 1]
    estabilidad = E.analizar(config_piloto, semillas)
    datos = E.a_diccionario(
        estabilidad,
        REGLA,
        {
            "plan": "estabilidad.yaml",
            "hash_plan": "0" * 64,
            "configuracion": "config.yaml",
            "hash_configuracion": "1" * 64,
            "fecha": "2026-10-28T00:00:00.000Z",
            "entorno": {},
            "comparacion_expediente": E.comparar_con_expediente(estabilidad, config_piloto),
        },
    )
    # En la carpeta temporal no hay expediente con el que comparar.
    assert datos["comparacion_expediente"]["coincide"] is None

    ruta_json, ruta_md = E.guardar(datos, tmp_path / "estabilidad")
    reporte = ruta_md.read_text(encoding="utf-8")
    assert ruta_json.exists()
    assert f"| {config_piloto.semilla} (sellada) |" in reporte
    assert "## Lectura de las combinaciones que deciden" in reporte
    assert sum(
        1 for c in datos["combinaciones"] if c["clasificacion"] in E.CLASIFICACIONES
    ) == len(datos["combinaciones"])
