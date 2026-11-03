"""Descarga a CSV, con consultas SELECT de solo lectura, las tablas tesis.* que usan los cálculos propios.

Uso: python -I descargar_tablas.py <carpeta_salida>

Usa la CLI de Databricks (perfil DEFAULT) y la API de sentencias SQL. No escribe nada en
Databricks.
"""

import csv
import json
import subprocess
import sys
import time
from pathlib import Path

WAREHOUSE = "290835d8317fc066"
CLI = "databricks"

CONSULTAS = {
    "dominios": """
        SELECT c.CODIGO_DOMINIO, c.NOMBRE_DOMINIO, c.TIPO_DOMINIO, c.TASA_DESEMPLEO_PCT,
               c.SE_BOOTSTRAP_PCT, c.CV_PORCENTAJE, c.TASA_HOMICIDIOS, c.COB_ACUEDUCTO,
               c.PEA_EXPANDIDA, d.LATITUD, d.LONGITUD
        FROM tesis.preprocesamiento.covariables_seleccionadas c
        LEFT JOIN tesis.dim.dim_divipola d ON c.CODIGO_DOMINIO = d.CODIGO_MUNICIPIO
        ORDER BY c.CODIGO_DOMINIO""",
    "objetivos": """
        SELECT o.CODIGO_MUNICIPIO, o.MUNICIPIO, o.CODIGO_DEPARTAMENTO, o.CODIGO_DOMINIO_PADRE,
               o.`060010003` AS TASA_HOMICIDIOS, d.LATITUD, d.LONGITUD
        FROM tesis.preprocesamiento.municipios_sin_encuesta o
        LEFT JOIN tesis.dim.dim_divipola d ON o.CODIGO_MUNICIPIO = d.CODIGO_MUNICIPIO
        ORDER BY o.CODIGO_MUNICIPIO""",
    "fay_herriot_resultados": "SELECT * FROM tesis.modelo.fay_herriot_resultados",
    "fhe_prediccion_objetivo": "SELECT * FROM tesis.modelo.fhe_prediccion_objetivo",
    "estimaciones_finales": "SELECT * FROM tesis.modelo.fay_herriot_estimaciones_finales",
    "fhe_comparacion_modelos": "SELECT * FROM tesis.modelo.fhe_comparacion_modelos",
    "fhe_cuadro_comparativo": "SELECT * FROM tesis.modelo.fhe_cuadro_comparativo",
    "fhe_moran": "SELECT * FROM tesis.modelo.fhe_moran",
    "fhe_validacion_cruzada_metricas": "SELECT * FROM tesis.modelo.fhe_validacion_cruzada_metricas",
    "fhe_coeficientes_comparacion": "SELECT * FROM tesis.modelo.fhe_coeficientes_comparacion",
    "fh_seleccion_modelo": "SELECT * FROM tesis.modelo.fh_seleccion_modelo",
    "fh_coeficientes": "SELECT * FROM tesis.modelo.fh_coeficientes",
    "fh_validacion_cruzada_metricas": "SELECT * FROM tesis.modelo.fh_validacion_cruzada_metricas",
    "prediccion_sintetica": "SELECT * FROM tesis.modelo.fay_herriot_prediccion_sintetica",
    "sensibilidad_varianza_fh": "SELECT * FROM tesis.modelo.sensibilidad_varianza_fh",
    "auditoria_dominios": "SELECT * FROM tesis.preprocesamiento.auditoria_dominios",
    "llaves_sin_pareja": "SELECT * FROM tesis.geih_oro.llaves_sin_pareja",
    "reconciliacion_resumen": """
        SELECT COUNT(*) AS N_CELDAS, SUM(N_PET) AS PET, SUM(N_PEA) AS PEA, SUM(N_PEI) AS PEI,
               SUM(N_OCUPADOS) AS OC, SUM(N_DESOCUPADOS) AS DS,
               SUM(N_PEA_DISTINTA_OC_DS) AS ROMPE_PEA, SUM(N_PET_SIN_CLASE) AS ROMPE_PET,
               SUM(N_OC_Y_DS) AS OC_Y_DS
        FROM tesis.geih_oro.reconciliacion_fuerza_trabajo WHERE PER = 2018""",
}


def ejecutar(sql):
    """Ejecuta una sentencia SQL en el almacén y devuelve columnas y filas.

    Args:
        sql (str): consulta SELECT.

    Returns:
        tuple[list[str], list[list]]: nombres de columna y filas.
    """
    cuerpo = json.dumps(
        {"warehouse_id": WAREHOUSE, "statement": sql, "wait_timeout": "50s", "disposition": "INLINE", "format": "JSON_ARRAY"}
    )
    salida = subprocess.run(
        [CLI, "api", "post", "/api/2.0/sql/statements", "--json", cuerpo],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    r = json.loads(salida.stdout)
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        s = subprocess.run(
            [CLI, "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        r = json.loads(s.stdout)
    if r["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(r["status"])
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    filas = r.get("result", {}).get("data_array", []) or []
    return cols, filas


def main():
    """Descarga cada consulta de CONSULTAS a <carpeta>/<nombre>.csv."""
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for nombre, sql in CONSULTAS.items():
        try:
            cols, filas = ejecutar(sql)
        except Exception as e:  # noqa: BLE001 - se reporta y se sigue con la siguiente
            print(f"{nombre}: ERROR {e}")
            continue
        with open(out / f"{nombre}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(filas)
        print(f"{nombre}: {len(filas)} filas")


if __name__ == "__main__":
    main()
