# Databricks notebook source
# DBTITLE 1,Descripción del notebook
# MAGIC %md
# MAGIC # Transformación TerriData - Capa Plata: Formato Largo → Formato Ancho (Pivoteado)
# MAGIC
# MAGIC Este notebook transforma los datos de **TerriData** desde la capa bronce (formato largo) hacia la capa plata (formato ancho/pivoteado), facilitando análisis multidimensionales y consultas eficientes por indicador.
# MAGIC
# MAGIC ## Propósito
# MAGIC
# MAGIC Convertir la estructura **normalizada** (formato largo) de TerriData en una estructura **desnormalizada** (formato ancho) donde:
# MAGIC * Cada **fila** representa una combinación única de: `ENTIDAD × AÑO × MES`
# MAGIC * Cada **columna** representa un indicador específico (~1,582 indicadores)
# MAGIC * Los valores están correctamente tipificados según su naturaleza (numérico vs cualitativo)
# MAGIC
# MAGIC ## Tablas de entrada y salida
# MAGIC
# MAGIC | Dirección | Tabla |
# MAGIC |-----------|-------|
# MAGIC | Entrada   | `tesis.terridata.terridata_bronce` |
# MAGIC | Salida    | `tesis.terridata.terridata_extendido_plata` |
# MAGIC | Dimensión | `tesis.dim.dim_indicadores` |
# MAGIC
# MAGIC ## Proceso
# MAGIC
# MAGIC 1. **Preparar datos base**: unificar `DATO_NUMERICO` y `DATO_CUALITATIVO` → campo `VALOR`
# MAGIC 2. **Clasificar indicadores**: `numerico` si ≥ 95 % de valores vienen de `DATO_NUMERICO`, si no `cualitativo`
# MAGIC 3. **Pivot dinámico**: `groupBy + pivot + agg(max)` sobre ~1,582 indicadores
# MAGIC 4. **Aplicar tipos**: `try_cast` a `double` para numéricos; mantener `string` para cualitativos
# MAGIC 5. **Guardar tabla pivoteada** y **tabla dimensional** de metadatos
# MAGIC 6. **Verificaciones de integridad** sobre las tablas Delta ya escritas

# COMMAND ----------

# DBTITLE 1,Imports
import sys
import os

sys.path.insert(0, os.path.dirname(os.getcwd()))

from pyspark.sql.functions import (
    col,
    when,
    lit,
    max as spark_max,
    expr,
    sum as spark_sum,
)

from shared.config.terridata_config import (
    TBL_BRONCE,
    TBL_PLATA,
    TBL_DIM_INDICADORES,
    COLUMNAS_ID,
    UMBRAL_CLASIFICACION_NUMERICO,
    UMBRAL_RIESGO_CASTEO,
)
from shared.utils.spark_utils import escribir_tabla
from shared.utils.verification_utils import (
    verificar_conservacion_registros,
    verificar_duplicados,
    verificar_integridad_muestra,
    verificar_calidad_casteo,
    verificar_reclasificacion_indicadores,
    verificar_valores_no_nulos,
)

# COMMAND ----------

# DBTITLE 1,Configuración
# False → solo se ejecutan validaciones ligeras (siempre activas)
# True  → además se ejecuta la verificación de conservación de valores no nulos
#          (~10-15 min en tablas de ~30M registros)
EJECUTAR_VALIDACIONES_PESADAS = False

# COMMAND ----------

# DBTITLE 1,Paso 1: Preparar datos base con valores unificados
# Leer tabla bronce
df_datos_unificados = spark.table(TBL_BRONCE)

# Eliminar filas donde ambos campos de valor son NULL
df_datos_unificados = df_datos_unificados.filter(
    col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull()
)

# Unificar DATO_NUMERICO y DATO_CUALITATIVO → campo VALOR (string)
# Prioridad: DATO_NUMERICO sobre DATO_CUALITATIVO
df_datos_unificados = df_datos_unificados.select(
    "CODIGO_DEPARTAMENTO",
    "DEPARTAMENTO",
    "DEPARTAMENTO_NORMALIZADO",
    "CODIGO_ENTIDAD",
    "ENTIDAD",
    "ENTIDAD_NORMALIZADO",
    col("ANO").cast("int").alias("ANO"),
    col("MES").cast("int").alias("MES"),
    "CODIGO_INDICADOR",
    "INDICADOR",
    "DIMENSION",
    "SUBCATEGORIA",
    "UNIDAD_MEDIDA",
    when(col("DATO_NUMERICO").isNotNull(), col("DATO_NUMERICO").cast("string"))
    .when(col("DATO_CUALITATIVO").isNotNull(), col("DATO_CUALITATIVO"))
    .otherwise(lit(None))
    .alias("VALOR"),
)

# COMMAND ----------

# DBTITLE 1,Paso 2: Clasificar indicadores como numéricos o cualitativos
# Criterio: si >= UMBRAL_CLASIFICACION_NUMERICO % de valores vienen de DATO_NUMERICO → "numerico"
# "preliminar" en DATO_CUALITATIVO se ignora (es anotación de calidad, no valor real)

df_bronce = spark.table(TBL_BRONCE)

df_clasificacion = (
    df_bronce
    .filter(col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull())
    .groupBy("CODIGO_INDICADOR")
    .agg(
        spark_sum(when(col("DATO_NUMERICO").isNotNull(), 1).otherwise(0)).alias("count_numerico"),
        spark_sum(
            when(
                col("DATO_CUALITATIVO").isNotNull() & (col("DATO_CUALITATIVO") != "preliminar"),
                1,
            ).otherwise(0)
        ).alias("count_cualitativo"),
    )
)

df_clasificacion = (
    df_clasificacion
    .withColumn("total_valores", col("count_numerico") + col("count_cualitativo"))
    .withColumn("porcentaje_numerico", col("count_numerico") / col("total_valores") * 100)
    .withColumn(
        "TIPO_DATO",
        when(col("porcentaje_numerico") >= UMBRAL_CLASIFICACION_NUMERICO, lit("numerico"))
        .otherwise(lit("cualitativo")),
    )
)

print("Clasificación de indicadores:")
print("=" * 60)
display(df_clasificacion.groupBy("TIPO_DATO").count().orderBy("TIPO_DATO"))

# Un único collect() evita releer bronce en Paso 4 y en las verificaciones
clasificacion_completa = df_clasificacion.collect()

tipo_indicador_dict = {row.CODIGO_INDICADOR: row.TIPO_DATO for row in clasificacion_completa}

# DataFrame para el LEFT JOIN de metadatos en Paso 5 (construido desde Python, sin releer bronce)
df_tipo_indicador = spark.createDataFrame(
    [(row.CODIGO_INDICADOR, row.TIPO_DATO) for row in clasificacion_completa],
    ["CODIGO_INDICADOR", "TIPO_DATO"],
)

# COMMAND ----------

# DBTITLE 1,Paso 3: Obtener lista de indicadores para el pivot
df_indicadores = (
    df_datos_unificados
    .select("CODIGO_INDICADOR")
    .distinct()
    .orderBy("CODIGO_INDICADOR")
)

indicadores = [row.CODIGO_INDICADOR for row in df_indicadores.collect()]

print(f"Total de indicadores a pivotar: {len(indicadores)}")

# COMMAND ----------

# DBTITLE 1,Paso 4: Generar pivot dinámico y aplicar tipos de datos
print(f"Pivotando {len(indicadores)} indicadores...")
print("Este proceso puede tomar varios minutos...")

df_pivoteado = (
    df_datos_unificados
    .groupBy(*COLUMNAS_ID)
    .pivot("CODIGO_INDICADOR", indicadores)
    .agg(spark_max("VALOR"))
)

# Aplicar tipos de datos correctos: double para numéricos, string para cualitativos
print("\nAplicando tipos de datos a columnas de indicador...")

columnas_con_tipo = [col(c) for c in COLUMNAS_ID]

count_numerico    = 0
count_cualitativo = 0

for col_name in df_pivoteado.columns:
    if col_name not in COLUMNAS_ID:
        tipo = tipo_indicador_dict.get(col_name, "cualitativo")
        if tipo == "numerico":
            columnas_con_tipo.append(expr(f"try_cast(`{col_name}` as double)").alias(col_name))
            count_numerico += 1
        else:
            columnas_con_tipo.append(col(f"`{col_name}`"))
            count_cualitativo += 1

df_pivoteado = df_pivoteado.select(columnas_con_tipo)

print(f"\n✅ Tipos aplicados:")
print(f"  - Numéricos (double con try_cast): {count_numerico}")
print(f"  - Cualitativos (string):           {count_cualitativo}")
print(f"\n⚠️  Valores no numéricos en columnas numéricas (ej: 'preliminar') → NULL con try_cast.")

# COMMAND ----------

# DBTITLE 1,Paso 5: Guardar tabla pivoteada en capa plata
n_cols = len(df_pivoteado.columns)

escribir_tabla(df_pivoteado, TBL_PLATA)

n_filas = spark.table(TBL_PLATA).count()

print("\n" + "=" * 60)
print("✅ TABLA PIVOTEADA GUARDADA EXITOSAMENTE")
print("=" * 60)
print(f"\nTabla: {TBL_PLATA}")
print(f"\nESTADÍSTICAS:")
print(f"  - Filas:    {n_filas:,}")
print(f"  - Columnas: {n_cols}  (8 de identificación + {n_cols - 8} indicadores)")

# COMMAND ----------

# DBTITLE 1,Ejecutar verificaciones
# Las verificaciones ligeras SIEMPRE se ejecutan — leen desde las tablas Delta ya escritas.
# La verificación pesada se controla con EJECUTAR_VALIDACIONES_PESADAS (celda de configuración).

df_bronce_v = spark.table(TBL_BRONCE)
df_plata_v  = spark.table(TBL_PLATA)

resultados = {
    "Conservación de registros": verificar_conservacion_registros(df_bronce_v, n_filas),
    "Duplicados en plata":        verificar_duplicados(df_plata_v, n_filas),
    "Integridad de muestra":      verificar_integridad_muestra(df_bronce_v, df_plata_v),
    "Calidad de casteo":          verificar_calidad_casteo(clasificacion_completa),
    "Reclasificación":            verificar_reclasificacion_indicadores(spark, tipo_indicador_dict),
}

if EJECUTAR_VALIDACIONES_PESADAS:
    df_largo_v = (
        spark.table(TBL_BRONCE)
        .filter(col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull())
        .select(
            when(col("DATO_NUMERICO").isNotNull(), col("DATO_NUMERICO").cast("string"))
            .when(col("DATO_CUALITATIVO").isNotNull(), col("DATO_CUALITATIVO"))
            .otherwise(lit(None))
            .alias("VALOR")
        )
    )
    resultados["Valores no nulos"] = verificar_valores_no_nulos(df_largo_v, df_plata_v)
else:
    print("ℹ️  Verificación pesada omitida (EJECUTAR_VALIDACIONES_PESADAS = False)\n")

print("\n" + "=" * 60)
print("RESUMEN DE VERIFICACIONES")
print("=" * 60)
for nombre, resultado in resultados.items():
    estado = "✅ PASS" if resultado else "❌ FAIL"
    print(f"  {estado}  {nombre}")

if all(resultados.values()):
    print("\n✅ TODAS LAS VERIFICACIONES PASARON")
else:
    fallidas = [n for n, r in resultados.items() if not r]
    print(f"\n❌ FALLARON: {', '.join(fallidas)}")

# COMMAND ----------

# DBTITLE 1,Paso 6: Crear tabla dimensional de indicadores
df_metadatos = (
    df_datos_unificados
    .select("CODIGO_INDICADOR", "INDICADOR", "DIMENSION", "SUBCATEGORIA", "UNIDAD_MEDIDA")
    .distinct()
    .join(df_tipo_indicador, on="CODIGO_INDICADOR", how="left")
    .orderBy("CODIGO_INDICADOR")
)

print(f"Total de indicadores documentados: {df_metadatos.count()}")
display(df_metadatos.groupBy("TIPO_DATO").count().orderBy("TIPO_DATO"))

escribir_tabla(df_metadatos, TBL_DIM_INDICADORES)

print(f"\n✅ Tabla dimensional guardada: {TBL_DIM_INDICADORES}")
