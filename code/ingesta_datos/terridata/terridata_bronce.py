# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Ingesta de Datos TerriData - Capa Bronce
# MAGIC
# MAGIC Este notebook realiza la ingesta y carga inicial de los datos de **TerriData** en la capa bronce del lakehouse, seleccionando los campos que usan las etapas siguientes.
# MAGIC
# MAGIC ## ¿Qué es TerriData?
# MAGIC
# MAGIC **TerriData** es el sistema de información geográfica y estadística del **Departamento Nacional de Planeación (DNP)** de Colombia que consolida indicadores sociales, económicos y demográficos a nivel territorial (departamentos y municipios).
# MAGIC
# MAGIC ## Proceso
# MAGIC
# MAGIC 1. Lee archivos Parquet consolidados desde `/Volumes/tesis/terridata/terridata_archivos/consolidado/`
# MAGIC 2. Selecciona los campos de `CAMPOS_BRONCE` (R-52: sin columnas `*_NORMALIZADO`, que nadie usaba)
# MAGIC 3. Guarda la tabla resultante en `tesis.terridata.terridata_bronce`
# MAGIC
# MAGIC ## Tabla de salida: `tesis.terridata.terridata_bronce`
# MAGIC
# MAGIC | Campo | Descripción |
# MAGIC |-------|-------------|
# MAGIC | `CODIGO_DEPARTAMENTO` | Código DIVIPOLA del departamento |
# MAGIC | `DEPARTAMENTO` | Nombre original con tildes |
# MAGIC | `CODIGO_ENTIDAD` | Código del municipio o entidad |
# MAGIC | `ENTIDAD` | Nombre original con tildes |
# MAGIC | `DIMENSION` | Categoría temática del indicador |
# MAGIC | `SUBCATEGORIA` | Subcategoría dentro de la dimensión |
# MAGIC | `INDICADOR` | Nombre descriptivo del indicador |
# MAGIC | `CODIGO_INDICADOR` | Código único del indicador |
# MAGIC | `DATO_NUMERICO` | Valor numérico del indicador |
# MAGIC | `DATO_CUALITATIVO` | Valor cualitativo del indicador |
# MAGIC | `ANO` | Año del dato |
# MAGIC | `MES` | Mes del dato |
# MAGIC | `FUENTE` | Fuente de información |
# MAGIC | `UNIDAD_MEDIDA` | Unidad de medida del indicador |

# COMMAND ----------

# DBTITLE 1,Imports
import os
import sys

# R-67: `code/` en sys.path para importar `comun` (el notebook está en code/ingesta_datos/<carpeta>/)
_ruta_nb = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .notebookPath()
    .get()
)
sys.path.insert(
    0, "/Workspace" + os.path.dirname(os.path.dirname(os.path.dirname(_ruta_nb)))
)


from shared.config.terridata_config import VOL_CONSOLIDADO, TBL_BRONCE
from shared.transformations.normalizacion import CAMPOS_BRONCE
from comun.spark_utils import leer_parquet, escribir_tabla

# COMMAND ----------

# DBTITLE 1,Leer y normalizar
df = leer_parquet(spark, VOL_CONSOLIDADO)
df_normalizado = df.select(*CAMPOS_BRONCE)

# COMMAND ----------

# DBTITLE 1,Escribir tabla
escribir_tabla(df_normalizado, TBL_BRONCE)
