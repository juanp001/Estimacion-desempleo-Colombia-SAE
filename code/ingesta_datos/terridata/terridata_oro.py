# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # TerriData Oro - Limpieza de Datos Mensuales
# MAGIC
# MAGIC ## Objetivo
# MAGIC Crear una tabla `terridata_oro_mensual` con variables de alta calidad (completitud >= 70%) para análisis y modelado.
# MAGIC
# MAGIC ## Proceso de Limpieza
# MAGIC
# MAGIC ### 1. Filtrado Temporal
# MAGIC * **Rango**: 2000-2024
# MAGIC * **Frecuencia**: MENSUAL (todos los meses, sin filtrar)
# MAGIC * **Justificación**: Datos históricos recientes, evita proyecciones futuras
# MAGIC
# MAGIC ### 2. Selección de Variables
# MAGIC * **Criterio**: Completitud >= 70% (parametrizable)
# MAGIC * **Tipo**: Numéricas Y cualitativas
# MAGIC * **Método**: Cálculo sobre todos los meses disponibles
# MAGIC
# MAGIC ### 3. Tabla Resultante
# MAGIC * **Nombre**: `tesis.terridata.terridata_oro_mensual`
# MAGIC * **Fuente**: `tesis.terridata.terridata_extendido_plata`
# MAGIC * **Lineage**: Preservado automáticamente
# MAGIC
# MAGIC ## Parámetros Configurables
# MAGIC
# MAGIC Modifica estos valores en la celda "Configuración y parámetros":
# MAGIC
# MAGIC ```python
# MAGIC COMPLETITUD_MIN = 70.0  # Umbral de completitud (porcentaje)
# MAGIC ANIO_INICIO = 2000      # Año inicial
# MAGIC ANIO_FIN = 2024         # Año final
# MAGIC ```
# MAGIC
# MAGIC ## Uso
# MAGIC
# MAGIC Ejecuta todas las celdas en orden para crear/actualizar la tabla oro.
# MAGIC
# MAGIC La tabla oro se puede usar directamente para:
# MAGIC * JOIN con estimaciones de desempleo
# MAGIC * Análisis de correlaciones
# MAGIC * Modelado SAE (Fay-Herriot, EBLUP, etc.)

# COMMAND ----------

# DBTITLE 1,Verificar tabla oro
# ============================================================================
# VERIFICACIÓN: EXPLORAR TABLA ORO CREADA
# ============================================================================

print("\n=== VERIFICACIÓN DE TABLA ORO ===")

# Leer tabla recién creada
df_oro = spark.table("tesis.terridata.terridata_oro_mensual")

# Estadísticas básicas
print(f"\nEstadísticas:")
print(f"  - Total filas: {df_oro.count():,}")
print(f"  - Total columnas: {len(df_oro.columns):,}")
print(f"  - Años únicos: {df_oro.select('ANO').distinct().count()}")
print(f"  - Meses únicos: {df_oro.select('MES').distinct().count()}")
print(f"  - Entidades únicas: {df_oro.select('CODIGO_ENTIDAD').distinct().count()}")

# Muestra de datos
print("\nMuestra de primeros 5 registros:")
df_oro.limit(5).toPandas().head()

# Distribución temporal
print("\nDistribución de registros por año:")
df_oro.groupBy("ANO").count().orderBy("ANO").show()

print("\n✔ Verificación completada!")

# COMMAND ----------

# DBTITLE 1,Crear tabla oro
# ============================================================================
# PASO 3: CREAR TABLA ORO CON COLUMNAS VÁLIDAS
# ============================================================================

print(f"\n[4/4] Creando tabla terridata_oro_mensual...")

# Seleccionar solo columnas válidas
df_terridata_oro = df_terridata_filtrado.select(*columnas_validas)

print(f"  Columnas seleccionadas: {len(columnas_validas)}")
print(f"  Filas a guardar: {df_terridata_oro.count():,}")

# Guardar como tabla en Unity Catalog
print("\n  Guardando tabla tesis.terridata.terridata_oro_mensual...")
df_terridata_oro.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.terridata.terridata_oro_mensual"
)

print("✔ Tabla creada exitosamente!")
print(f"\nTabla: tesis.terridata.terridata_oro_mensual")
print(f"  - Filas: {df_terridata_oro.count():,}")
print(f"  - Columnas: {len(df_terridata_oro.columns):,}")
print(f"  - Completitud mínima: {COMPLETITUD_MIN}%")
print(f"  - Rango temporal: {ANIO_INICIO}-{ANIO_FIN}")
print(f"  - Frecuencia: MENSUAL (todos los meses)")
print(f"  - Lineage preservado desde: tesis.terridata.terridata_extendido_plata")

# COMMAND ----------

# DBTITLE 1,Calcular completitud
# ============================================================================
# PASO 2: CALCULAR COMPLETITUD DE COLUMNAS
# ============================================================================

print(f"\n[3/4] Calculando completitud de columnas (umbral: {COMPLETITUD_MIN}%)...")

# Calcular total de filas para porcentaje
total_filas = df_terridata_filtrado.count()
print(f"  Total de filas a evaluar: {total_filas:,}")

# Calcular completitud para cada columna
print("  Analizando completitud por columna...")
completitud_data = []

for col_name in df_terridata_filtrado.columns:
    count_no_null = df_terridata_filtrado.filter(F.col(col_name).isNotNull()).count()
    pct_completitud = (count_no_null / total_filas) * 100
    
    completitud_data.append({
        "columna": col_name,
        "filas_no_null": count_no_null,
        "completitud_pct": round(pct_completitud, 2)
    })

# Crear DataFrame de completitud
df_completitud = pd.DataFrame(completitud_data).sort_values("completitud_pct", ascending=False)

print(f"\n  Resumen de completitud:")
print(f"    - Total columnas analizadas: {len(df_completitud)}")
print(f"    - Columnas con >= {COMPLETITUD_MIN}%: {len(df_completitud[df_completitud['completitud_pct'] >= COMPLETITUD_MIN])}")
print(f"    - Columnas con < {COMPLETITUD_MIN}%: {len(df_completitud[df_completitud['completitud_pct'] < COMPLETITUD_MIN])}")

# Filtrar columnas que cumplen el umbral
columnas_validas = df_completitud[df_completitud["completitud_pct"] >= COMPLETITUD_MIN]["columna"].tolist()

print(f"\n  Top 10 columnas con mayor completitud:")
display(df_completitud.head(10))

print(f"\n  Top 10 columnas con menor completitud:")
display(df_completitud.tail(10))

# COMMAND ----------

# DBTITLE 1,Configuración y parámetros
from pyspark.sql import functions as F
from pyspark.sql.window import Window
import pandas as pd

# ============================================================================
# PARÁMETROS DE LIMPIEZA
# ============================================================================

# Umbral de completitud (70% por defecto, modificable)
COMPLETITUD_MIN = 70.0  # Porcentaje mínimo de datos no nulos

# Rango temporal
ANIO_INICIO = 2000
ANIO_FIN = 2024

print(f"Parámetros de limpieza:")
print(f"  - Completitud mínima: {COMPLETITUD_MIN}%")
print(f"  - Rango temporal: {ANIO_INICIO}-{ANIO_FIN}")
print(f"  - Frecuencia: MENSUAL (todos los meses)")

# COMMAND ----------

# DBTITLE 1,Cargar y filtrar por años
# ============================================================================
# PASO 1: CARGAR Y FILTRAR TERRIDATA POR AÑOS
# ============================================================================

print("\n[1/4] Cargando tabla terridata_extendido_plata...")
df_terridata_plata = spark.table("tesis.terridata.terridata_extendido_plata")

print(f"  Filas originales: {df_terridata_plata.count():,}")
print(f"  Columnas originales: {len(df_terridata_plata.columns):,}")

# Filtrar por rango temporal (SIN filtrar por mes - datos mensuales)
print(f"\n[2/4] Filtrando por años {ANIO_INICIO}-{ANIO_FIN}...")
df_terridata_filtrado = df_terridata_plata.filter(
    (F.col("ANO") >= ANIO_INICIO) & (F.col("ANO") <= ANIO_FIN)
)

print(f"  Filas después de filtro temporal: {df_terridata_filtrado.count():,}")

# Verificar distribución de meses
print("\n  Distribución de meses en los datos:")
df_terridata_filtrado.groupBy("MES").count().orderBy("MES").show()