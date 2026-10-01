# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Pre-filtrado de covariables auxiliares — versión revisada
# MAGIC
# MAGIC Versión revisada de `pre_filtrado_covariables`. El original permanece sin cambios;
# MAGIC este notebook escribe sus resultados en tablas con sufijo `_rev` para que ambas
# MAGIC versiones puedan compararse.
# MAGIC
# MAGIC ## Qué cambia y por qué
# MAGIC
# MAGIC | Original | Revisado | Motivo |
# MAGIC |----------|----------|--------|
# MAGIC | Filtro 1: sin NA en los 23 dominios | **Sin cambios** | Con 23 dominios cualquier vacío inutiliza la covariable. Criterio objetivo e independiente de la respuesta. |
# MAGIC | Filtro 2: varianza absoluta > 1e-5 | **Criterio invariante a escala** | Un umbral absoluto de varianza depende de las unidades: la misma tasa en tanto por uno y en porcentaje tiene varianzas que difieren por un factor de 10.000. Se sustituye por coeficiente de variación y proporción del valor modal. |
# MAGIC | Filtro 3: \|Pearson\| ≥ 0.40 con la tasa de desempleo | **Eliminado** | Descartaba covariables usando la variable respuesta sobre los mismos 23 dominios que después ajustan el modelo. Eso sesga al alza las correlaciones de las supervivientes e invalida su lectura posterior como evidencia. No es un pre-filtrado sino una selección encubierta. |
# MAGIC | — | **Reporte de grupos redundantes** | Documenta qué covariables son duplicados exactos entre sí, sin descartar ninguna: cuál conservar exige un criterio conceptual que solo está disponible más adelante. |
# MAGIC
# MAGIC El pre-filtrado resultante es **enteramente independiente de la variable respuesta**.
# MAGIC Su único propósito es eliminar covariables inutilizables, no elegir las mejores.
# MAGIC La asociación con la tasa de desempleo pasa a tratarse como evidencia descriptiva en
# MAGIC `analisis_descriptivo_rev` y como diagnóstico en `eda_seleccion_covariables_rev`.
# MAGIC
# MAGIC ## Parámetros (en `shared/config_rev.py`)
# MAGIC
# MAGIC | Parámetro | Valor | Descripción |
# MAGIC |-----------|-------|-------------|
# MAGIC | `CV_MINIMO` | `0.001` | Coeficiente de variación mínimo aceptable |
# MAGIC | `PROP_MODAL_MAXIMA` | `0.90` | Proporción máxima de dominios con el valor modal |
# MAGIC | `UMBRAL_DUPLICADO` | `0.999` | Magnitud de correlación que define un duplicado |
# MAGIC
# MAGIC ## Salidas
# MAGIC
# MAGIC * `tesis.preprocesamiento.covariables_prefiltradas_rev` — covariables supervivientes.
# MAGIC * `tesis.preprocesamiento.cascada_prefiltrado_rev` — conteo por etapa, insumo de la
# MAGIC   tabla de cascada del capítulo de resultados.
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Rao, J.N.K. & Molina, I. (2015). *Small Area Estimation* (2nd ed.). Wiley.

# COMMAND ----------

# DBTITLE 1,Importar librerías y módulos compartidos
import os
import sys

import pandas as pd

# Los módulos compartidos se importan por su ruta completa desde `code/` (por ejemplo
# `preprocesamiento.shared.config_rev`) y no como `shared.…`. El motivo es que existen dos
# carpetas `shared/` distintas en el proyecto —una bajo `preprocesamiento/` y otra bajo
# `modelo/`— y la forma corta resuelve a una u otra según desde dónde se ejecute, lo que
# haría que el mismo notebook importara módulos distintos en el editor y en un job.
def _directorio_codigo() -> str:
    """Ruta absoluta de `code/`, tanto en ejecución interactiva como en un job."""
    try:
        contexto = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
        return "/Workspace" + os.path.dirname(os.path.dirname(contexto.notebookPath().get()))
    except Exception:
        return os.path.dirname(os.getcwd())


CODE_DIR = _directorio_codigo()
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from preprocesamiento.shared.config_rev import *
from preprocesamiento.shared.feature_selection_rev import (
    filtrar_columnas_sin_na,
    filtrar_variabilidad,
    sensibilidad_variabilidad,
    reportar_grupos_redundantes,
)

# COMMAND ----------

# DBTITLE 1,Cargar datos y aislar covariables
df_spark = spark.read.table(TBL_COVARIABLES)
df = df_spark.toPandas()

covariables_cols = [c for c in df.columns if c not in METADATA_COLS]
df_covariables = df[covariables_cols].copy()

# Homogenizar tipos: forzar a numérico, textos no parseables → NaN
for col in df_covariables.select_dtypes(include=["object"]).columns:
    df_covariables[col] = pd.to_numeric(df_covariables[col], errors="coerce")

n_inicial = len(covariables_cols)
print(f"Dominios de estimación: {len(df)}")
print(f"Covariables candidatas iniciales: {n_inicial}")

# COMMAND ----------

# DBTITLE 1,Filtro 1 — Completitud
df_sin_na = filtrar_columnas_sin_na(df_covariables)
n_sin_na = df_sin_na.shape[1]

# COMMAND ----------

# MAGIC %md
# MAGIC Con 23 dominios de estimación, una covariable con un solo dato faltante deja sin
# MAGIC información a un dominio completo y no puede usarse en la regresión sintética del
# MAGIC modelo Fay-Herriot. El criterio es binario —cero faltantes— y no depende de la
# MAGIC variable respuesta.

# COMMAND ----------

# DBTITLE 1,Filtro 2 — Variabilidad aprovechable
df_filtrado, reporte_variabilidad = filtrar_variabilidad(
    df_sin_na,
    cv_min=CV_MINIMO,
    prop_modal_max=PROP_MODAL_MAXIMA,
)
n_variabilidad = df_filtrado.shape[1]
display(spark.createDataFrame(reporte_variabilidad))

# COMMAND ----------

# MAGIC %md
# MAGIC Una covariable constante es linealmente dependiente del intercepto y vuelve singular
# MAGIC la matriz de diseño, impidiendo estimar los coeficientes. El criterio original usaba
# MAGIC un umbral absoluto de varianza, que no es invariante a las unidades del indicador.
# MAGIC Aquí se descarta una covariable cuando su valor más frecuente cubre más del
# MAGIC `PROP_MODAL_MAXIMA` de los dominios o cuando su coeficiente de variación queda por
# MAGIC debajo de `CV_MINIMO`; ambos criterios son adimensionales.

# COMMAND ----------

# DBTITLE 1,Sensibilidad del filtro de variabilidad
# Barrido sobre el conjunto posterior al filtro de completitud: a diferencia del análisis
# de sensibilidad de la versión original, aquí un umbral más laxo sí puede devolver más
# covariables, porque el conjunto de partida no está recortado por el propio umbral.
df_sensibilidad = sensibilidad_variabilidad(df_sin_na)
display(spark.createDataFrame(df_sensibilidad))

spark.createDataFrame(df_sensibilidad).write.mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(TBL_SENSIBILIDAD_REV)
print(f"Tabla escrita: {TBL_SENSIBILIDAD_REV}")

# COMMAND ----------

# DBTITLE 1,Reporte de covariables duplicadas entre sí
df_redundantes = reportar_grupos_redundantes(df_filtrado, umbral=UMBRAL_DUPLICADO)
if not df_redundantes.empty:
    display(spark.createDataFrame(df_redundantes))

# COMMAND ----------

# MAGIC %md
# MAGIC Los grupos anteriores contienen covariables con correlación de magnitud
# MAGIC prácticamente unitaria: miden lo mismo, a veces en sentido inverso. Ninguna se
# MAGIC descarta aquí. Retirar una exige decidir cuál conservar, y esa decisión necesita el
# MAGIC respaldo conceptual que solo está disponible en la etapa de selección.

# COMMAND ----------

# DBTITLE 1,Tabla de cascada del pre-filtrado
cascada = pd.DataFrame([
    {"Orden": 1, "Etapa": "Conjunto inicial",
     "Criterio": "Indicadores pivotados de TerriData",
     "Covariables": n_inicial,
     "Retencion_pct": round(100.0, 2)},
    {"Orden": 2, "Etapa": "Completitud",
     "Criterio": f"Sin faltantes en los {len(df)} dominios",
     "Covariables": n_sin_na,
     "Retencion_pct": round(100 * n_sin_na / n_inicial, 2)},
    {"Orden": 3, "Etapa": "Variabilidad",
     "Criterio": f"CV >= {CV_MINIMO} y proporción modal <= {PROP_MODAL_MAXIMA:.0%}",
     "Covariables": n_variabilidad,
     "Retencion_pct": round(100 * n_variabilidad / n_inicial, 2)},
])
display(spark.createDataFrame(cascada))

spark.createDataFrame(cascada).write.mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(TBL_CASCADA_REV)

# COMMAND ----------

# DBTITLE 1,Escritura de las covariables prefiltradas
df_output = pd.concat([df[METADATA_COLS], df_filtrado], axis=1)

spark.createDataFrame(df_output).write.mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(TBL_PREFILTRADAS_REV)

print(f"Tabla escrita: {TBL_PREFILTRADAS_REV}  ({n_variabilidad} covariables prefiltradas)")

