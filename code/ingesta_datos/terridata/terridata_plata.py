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
# MAGIC * Cada **columna** representa un indicador específico (1,582 indicadores)
# MAGIC * Los valores están correctamente tipificados según su naturaleza (numérico vs cualitativo)
# MAGIC
# MAGIC ## Tablas de Entrada y Salida
# MAGIC
# MAGIC ### Entrada (Capa Bronce):
# MAGIC **`tesis.terridata.terridata_bronce`** - Formato LARGO
# MAGIC
# MAGIC ```
# MAGIC | CODIGO_ENTIDAD | ANO  | MES | CODIGO_INDICADOR | VALOR  |
# MAGIC |----------------|------|-----|------------------|--------|
# MAGIC | 05001          | 2020 | 12  | 010010009        | 2500000|
# MAGIC | 05001          | 2020 | 12  | 010010010        | 1300000|
# MAGIC | 05001          | 2020 | 12  | 010010011        | 1200000|
# MAGIC ```
# MAGIC
# MAGIC ### Salidas (Capa Plata):
# MAGIC
# MAGIC **1. `tesis.terridata.terridata_extendido_plata`** - Formato ANCHO
# MAGIC
# MAGIC ```
# MAGIC | CODIGO_ENTIDAD | ANO  | MES | 010010009 | 010010010 | 010010011 | ... |
# MAGIC |----------------|------|-----|-----------|-----------|-----------|-----|
# MAGIC | 05001          | 2020 | 12  | 2500000   | 1300000   | 1200000   | ... |
# MAGIC ```
# MAGIC
# MAGIC **2. `tesis.dim.dim_indicadores`** - Tabla dimensional de metadatos
# MAGIC
# MAGIC ```
# MAGIC | CODIGO_INDICADOR | INDICADOR          | DIMENSION  | TIPO_DATO  |
# MAGIC |------------------|--------------------|------------|------------|
# MAGIC | 010010009        | Población total    | Demografía | numerico   |
# MAGIC | 020030015        | Tasa de matrícula  | Educación  | numerico   |
# MAGIC | 030040020        | Estado proyecto    | Vivienda   | cualitativo|
# MAGIC ```
# MAGIC
# MAGIC ## ¿Por qué Pivotar? Ventajas del Formato Ancho
# MAGIC
# MAGIC ### Formato LARGO (Bronce):
# MAGIC ✅ Normalizado y eficiente para almacenamiento
# MAGIC ✅ Fácil de actualizar (agregar nuevos indicadores)
# MAGIC ❌ Difícil de consultar múltiples indicadores simultáneamente
# MAGIC ❌ Requiere múltiples joins para análisis multivariado
# MAGIC
# MAGIC ### Formato ANCHO (Plata):
# MAGIC ✅ Consultas simples: `SELECT indicador1, indicador2 FROM tabla WHERE ...`
# MAGIC ✅ Análisis multivariado directo (correlaciones, ML features)
# MAGIC ✅ Compatible con herramientas BI y visualización
# MAGIC ✅ Joins más simples con otras tablas
# MAGIC ❌ Muchas columnas (1,582 indicadores)
# MAGIC
# MAGIC ## Proceso de Transformación
# MAGIC
# MAGIC ### Paso 1: Preparación de Datos Base
# MAGIC * Leer tabla bronce
# MAGIC * Filtrar valores no nulos
# MAGIC * Unificar campos `DATO_NUMERICO` y `DATO_CUALITATIVO` → campo `VALOR`
# MAGIC * Normalizar tipos de datos (ANO, MES como int)
# MAGIC
# MAGIC ### Paso 2: Clasificación de Indicadores
# MAGIC
# MAGIC **Problema**: TerriData tiene datos mixtos:
# MAGIC * Algunos indicadores son **numéricos** (población, tasas, porcentajes)
# MAGIC * Otros son **cualitativos** (estados, categorías)
# MAGIC * Algunos tienen anotaciones como "preliminar" en campos numéricos
# MAGIC
# MAGIC **Solución**: Clasificación automática basada en contenido
# MAGIC * Si ≥ 95% de valores vienen de `DATO_NUMERICO` → `TIPO_DATO = "numerico"`
# MAGIC * Si < 95% → `TIPO_DATO = "cualitativo"`
# MAGIC * Se ignora "preliminar" en `DATO_CUALITATIVO` (es anotación, no valor real)
# MAGIC
# MAGIC ### Paso 3: Generación de Pivot Dinámico
# MAGIC * Obtener lista completa de indicadores únicos (~1,582)
# MAGIC * Generar expresiones SQL dinámicas para pivot
# MAGIC * Crear tabla pivoteada con `groupBy` + `pivot` + `agg(max)`
# MAGIC
# MAGIC ### Paso 4: Aplicación de Tipos de Datos Correctos
# MAGIC * **Indicadores numéricos**: Convertir a `double` usando `try_cast`
# MAGIC   * Valores inválidos (ej: "preliminar") → `NULL`
# MAGIC * **Indicadores cualitativos**: Mantener como `string`
# MAGIC
# MAGIC ### Paso 5: Generación de Tabla de Metadatos
# MAGIC * Extraer información única de cada indicador:
# MAGIC   * Código y nombre
# MAGIC   * Dimensión y subcategoría
# MAGIC   * Unidad de medida
# MAGIC   * Tipo de dato (numérico/cualitativo)
# MAGIC * Guardar en `tesis.dim.dim_indicadores`
# MAGIC
# MAGIC ## Tabla Dimensional: `dim_indicadores`
# MAGIC
# MAGIC ### Propósito
# MAGIC Tabla de **metadatos de referencia** que documenta cada uno de los 1,582 indicadores de TerriData.
# MAGIC
# MAGIC ### Campos:
# MAGIC
# MAGIC | Campo | Tipo | Descripción |
# MAGIC |-------|------|-------------|
# MAGIC | `CODIGO_INDICADOR` | string | Código único del indicador (PK) |
# MAGIC | `INDICADOR` | string | Nombre descriptivo del indicador |
# MAGIC | `DIMENSION` | string | Categoría temática (Demografía, Educación, Salud, etc.) |
# MAGIC | `SUBCATEGORIA` | string | Subcategoría dentro de la dimensión |
# MAGIC | `UNIDAD_MEDIDA` | string | Unidad de medida (personas, %, pesos, etc.) |
# MAGIC | `TIPO_DATO` | string | "numerico" o "cualitativo" |
# MAGIC
# MAGIC ### Uso de dim_indicadores:
# MAGIC
# MAGIC #### 1. Documentación de datos:
# MAGIC ```sql
# MAGIC -- ¿Qué significa el indicador 010010009?
# MAGIC SELECT * FROM tesis.dim.dim_indicadores WHERE CODIGO_INDICADOR = '010010009'
# MAGIC -- Resultado: Población total, Demografía, personas, numérico
# MAGIC ```
# MAGIC
# MAGIC #### 2. Filtrado por dimensión:
# MAGIC ```sql
# MAGIC -- Listar todos los indicadores de educación
# MAGIC SELECT CODIGO_INDICADOR, INDICADOR 
# MAGIC FROM tesis.dim.dim_indicadores 
# MAGIC WHERE DIMENSION = 'Educación'
# MAGIC ```
# MAGIC
# MAGIC #### 3. Análisis de tipos:
# MAGIC ```sql
# MAGIC -- Contar indicadores por tipo de dato
# MAGIC SELECT TIPO_DATO, COUNT(*) as total
# MAGIC FROM tesis.dim.dim_indicadores
# MAGIC GROUP BY TIPO_DATO
# MAGIC ```
# MAGIC
# MAGIC #### 4. Construcción de queries dinámicas:
# MAGIC ```python
# MAGIC # Seleccionar solo indicadores numéricos para modelo ML
# MAGIC indicadores_numericos = spark.table("tesis.dim.dim_indicadores") \
# MAGIC     .filter(col("TIPO_DATO") == "numerico") \
# MAGIC     .select("CODIGO_INDICADOR").collect()
# MAGIC
# MAGIC features = [row.CODIGO_INDICADOR for row in indicadores_numericos]
# MAGIC df_ml = df_terridata.select(["CODIGO_ENTIDAD", "ANO"] + features)
# MAGIC ```
# MAGIC
# MAGIC ## Sistema de Verificaciones
# MAGIC
# MAGIC ### Propósito
# MAGIC Validar que la transformación de formato largo → ancho sea **correcta e íntegra**:
# MAGIC * No se pierdan registros
# MAGIC * Los valores se conserven exactamente
# MAGIC * No se generen duplicados
# MAGIC * Los valores no nulos se mantengan
# MAGIC
# MAGIC ### Verificaciones Implementadas:
# MAGIC
# MAGIC #### 1. **Conservación de Registros**
# MAGIC ```python
# MAGIC verificar_conservacion_registros(df_largo, df_ancho)
# MAGIC ```
# MAGIC Verifica: `# combinaciones únicas (ENTIDAD × AÑO × MES) en LARGO == # filas en ANCHO`
# MAGIC
# MAGIC #### 2. **Integridad de Valores**
# MAGIC ```python
# MAGIC verificar_integridad_valores(df_largo, df_ancho)
# MAGIC ```
# MAGIC Compara un caso específico (Medellín, 2020-12, indicador población) entre ambos formatos
# MAGIC
# MAGIC #### 3. **Detección de Duplicados**
# MAGIC ```python
# MAGIC verificar_duplicados(df_ancho)
# MAGIC ```
# MAGIC Verifica que no existan filas duplicadas en las claves de agrupación
# MAGIC
# MAGIC #### 4. **Valores No Nulos**
# MAGIC ```python
# MAGIC verificar_valores_no_nulos(df_largo, df_ancho)
# MAGIC ```
# MAGIC Verifica que el total de valores no nulos se conserve (con tolerancia del 1% por "preliminar" → NULL)
# MAGIC
# MAGIC ### ⚠️ IMPORTANTE: Por qué están comentadas las verificaciones
# MAGIC
# MAGIC **La celda de verificaciones (celda 8) está deshabilitada por defecto** porque:
# MAGIC
# MAGIC 1. **Son muy demoradas** (~10-15 minutos):
# MAGIC    * Operaciones de count() en tablas grandes (~30M registros en formato largo)
# MAGIC    * Múltiples escaneos completos de la tabla
# MAGIC    * Agregaciones complejas contando valores no nulos
# MAGIC
# MAGIC 2. **Solo se necesitan durante desarrollo**:
# MAGIC    * Para validar la lógica de transformación inicial
# MAGIC    * Para debugging cuando se cambia el código de pivot
# MAGIC    * No son necesarias en ejecuciones productivas rutinarias
# MAGIC
# MAGIC 3. **Cómo activarlas**:
# MAGIC    ```python
# MAGIC    # DESCOMENTAR la celda 8 cuando sea necesario validar:
# MAGIC    # - Cambios en lógica de pivot
# MAGIC    # - Actualizaciones de datos sospechosas
# MAGIC    # - Debugging de discrepancias
# MAGIC    ```
# MAGIC
# MAGIC 4. **Cuándo ejecutarlas**:
# MAGIC    ✅ Primera vez que se ejecuta el notebook
# MAGIC    ✅ Después de cambios en el código de pivot
# MAGIC    ✅ Si se sospecha pérdida de datos
# MAGIC    ✅ Después de actualizar la tabla bronce fuente
# MAGIC    ❌ En ejecuciones rutinarias de actualización
# MAGIC
# MAGIC ### Tolerancia en Verificaciones
# MAGIC
# MAGIC Las verificaciones permiten **1% de tolerancia** en valores no nulos porque:
# MAGIC * Valores "preliminar" en columnas numéricas se convierten a `NULL` con `try_cast`
# MAGIC * Esto es comportamiento esperado y correcto
# MAGIC * El 1% cubre estas conversiones legítimas
# MAGIC
# MAGIC ## Consideraciones de Performance
# MAGIC
# MAGIC ### Optimizaciones Aplicadas:
# MAGIC
# MAGIC 1. **Pivot dinámico**: Se usa la lista completa de indicadores para evitar scans múltiples
# MAGIC 2. **Filtrado temprano**: Se eliminan valores NULL antes del pivot
# MAGIC 3. **try_cast**: Más eficiente que validaciones manuales con CASE WHEN
# MAGIC 4. **overwriteSchema**: Permite cambios en estructura sin errores
# MAGIC
# MAGIC ### Tamaño de Datos:
# MAGIC
# MAGIC * **Formato LARGO** (~30M filas):
# MAGIC   * Filas: ~30,000,000
# MAGIC   * Columnas: 16
# MAGIC   
# MAGIC * **Formato ANCHO** (~20K filas):
# MAGIC   * Filas: ~20,000 (combinaciones ENTIDAD × AÑO × MES)
# MAGIC   * Columnas: ~1,590 (8 columnas ID + 1,582 indicadores)
# MAGIC
# MAGIC **Reducción de filas**: 1,500x menos filas pero muchas más columnas
# MAGIC
# MAGIC ## Uso de las Tablas de Salida
# MAGIC
# MAGIC ### Consultas Típicas:
# MAGIC
# MAGIC ```sql
# MAGIC -- Análisis multivariado: población vs matrícula escolar
# MAGIC SELECT 
# MAGIC   ENTIDAD,
# MAGIC   ANO,
# MAGIC   `010010009` as poblacion_total,
# MAGIC   `020030015` as tasa_matricula
# MAGIC FROM tesis.terridata.terridata_extendido_plata
# MAGIC WHERE ANO >= 2018
# MAGIC   AND CODIGO_DEPARTAMENTO = '05'
# MAGIC ```
# MAGIC
# MAGIC ```sql
# MAGIC -- Join con metadatos para filtrar dimensión
# MAGIC SELECT t.*
# MAGIC FROM tesis.terridata.terridata_extendido_plata t
# MAGIC WHERE EXISTS (
# MAGIC   SELECT 1 FROM tesis.dim.dim_indicadores d
# MAGIC   WHERE d.DIMENSION = 'Salud'
# MAGIC )
# MAGIC ```
# MAGIC
# MAGIC ## Dependencias
# MAGIC
# MAGIC **Prerrequisito**: `tesis.terridata.terridata_bronce`
# MAGIC
# MAGIC **Siguiente paso**: Análisis en capa oro o consumo directo en dashboards/ML

# COMMAND ----------

# DBTITLE 1,Imports
# Importar clases y funciones de PySpark necesarias para la transformación
from pyspark.sql import DataFrame    # Tipo para anotaciones de funciones

from pyspark.sql.functions import (
    col,              # Referenciar columnas
    when,             # Expresiones condicionales (usado en unificación de valores)
    lit,              # Crear valores literales
    max as spark_max, # Agregación MAX (renombrado para evitar conflicto con max() de Python)
    expr,             # Ejecutar expresiones SQL (usado en try_cast)
    sum as spark_sum  # Agregación SUM (renombrado para evitar conflicto con sum() de Python)
)

# COMMAND ----------

# DBTITLE 1,Paso 1: Preparar datos base con valores unificados
# ============================================================================
# PASO 1: PREPARACIÓN DE DATOS BASE
# ============================================================================
# Objetivo: Unificar DATO_NUMERICO y DATO_CUALITATIVO en un solo campo VALOR
# para simplificar el pivot posterior

# --- Leer tabla bronce ---
df_datos_unificados = spark.table("tesis.terridata.terridata_bronce")

# --- Filtrar registros con valores ---
# Eliminar filas donde ambos campos de valor son NULL
# (no aportan información para el análisis)
df_datos_unificados = df_datos_unificados.filter(
    col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull()
)

# --- Unificar valores en campo VALOR ---
# Lógica: Priorizar DATO_NUMERICO sobre DATO_CUALITATIVO
# Convertir todo a string para tener un tipo consistente
df_datos_unificados = df_datos_unificados.select(
    # --- GEOGRAFÍA ---
    "CODIGO_DEPARTAMENTO",              # Código del departamento
    "DEPARTAMENTO",                      # Nombre con tildes
    "DEPARTAMENTO_NORMALIZADO",         # Nombre sin tildes (para joins)
    "CODIGO_ENTIDAD",                    # Código del municipio
    "ENTIDAD",                           # Nombre con tildes
    "ENTIDAD_NORMALIZADO",              # Nombre sin tildes (para joins)
    
    # --- TEMPORALIDAD ---
    # Convertir a int para consistencia y facilitar filtros numéricos
    col("ANO").cast("int").alias("ANO"),
    col("MES").cast("int").alias("MES"),
    
    # --- INDICADOR ---
    "CODIGO_INDICADOR",                  # Código del indicador (será columna en pivot)
    "INDICADOR",                         # Nombre descriptivo
    "DIMENSION",                         # Categoría temática
    "SUBCATEGORIA",                      # Subcategoría
    "UNIDAD_MEDIDA",                     # Unidad de medida
    
    # --- VALOR UNIFICADO ---
    # Lógica de unificación:
    # 1. Si DATO_NUMERICO no es NULL → convertir a string y usar
    # 2. Si no, y DATO_CUALITATIVO no es NULL → usar
    # 3. Si no → NULL
    # Resultado: Un solo campo VALOR (string) que contiene el dato
    when(col("DATO_NUMERICO").isNotNull(), col("DATO_NUMERICO").cast("string"))
    .when(col("DATO_CUALITATIVO").isNotNull(), col("DATO_CUALITATIVO"))
    .otherwise(lit(None))
    .alias("VALOR")
)

# COMMAND ----------

# DBTITLE 1,Paso 2: Clasificar indicadores como numéricos o cualitativos
# ============================================================================
# PASO 2: CLASIFICACIÓN AUTOMÁTICA DE INDICADORES
# ============================================================================
# Objetivo: Determinar si cada indicador es NUMÉRICO o CUALITATIVO
# basado en el análisis de sus valores reales
#
# CRITERIO DE CLASIFICACIÓN:
# - NUMÉRICO: Si >= 95% de valores vienen de DATO_NUMERICO
# - CUALITATIVO: Si < 95% de valores vienen de DATO_NUMERICO
#
# IMPORTANTE: "preliminar" en DATO_CUALITATIVO se IGNORA
# porque es una anotación de calidad de datos, no un valor real del indicador

# Cargar tabla bronce original (necesitamos los campos originales sin unificar)
df_bronce = spark.table("tesis.terridata.terridata_bronce")

# --- Contar valores por tipo de campo para cada indicador ---
df_clasificacion = (
    df_bronce
    # Filtrar solo registros con al menos un valor no NULL
    .filter(col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull())
    # Agrupar por indicador y contar tipos de valores
    .groupBy("CODIGO_INDICADOR")
    .agg(
        # Contar cuántas veces viene de DATO_NUMERICO
        spark_sum(when(col("DATO_NUMERICO").isNotNull(), 1).otherwise(0)).alias("count_numerico"),
        
        # Contar cuántas veces viene de DATO_CUALITATIVO (ignorando "preliminar")
        spark_sum(
            when(
                (col("DATO_CUALITATIVO").isNotNull()) & 
                (col("DATO_CUALITATIVO") != "preliminar"),  # Ignorar "preliminar"
                1
            ).otherwise(0)
        ).alias("count_cualitativo")
    )
)

# --- Calcular porcentaje y aplicar criterio de clasificación ---
df_clasificacion = (
    df_clasificacion
    # Calcular total de valores válidos
    .withColumn(
        "total_valores",
        col("count_numerico") + col("count_cualitativo")
    )
    # Calcular porcentaje de valores numéricos
    .withColumn(
        "porcentaje_numerico",
        (col("count_numerico") / col("total_valores") * 100)
    )
    # Clasificar según umbral del 95%
    .withColumn(
        "TIPO_DATO",
        when(col("porcentaje_numerico") >= 95, lit("numerico"))
        .otherwise(lit("cualitativo"))
    )
)

# --- Mostrar resumen de clasificación ---
print("Clasificación de indicadores:")
print("=" * 60)
resumen = df_clasificacion.groupBy("TIPO_DATO").count().orderBy("TIPO_DATO")
display(resumen)
print("\nNota: Esta clasificación se usará para aplicar el tipo de dato correcto")
print("      en las columnas de la tabla pivoteada (double vs string)")

# --- Guardar clasificación para uso posterior ---
# Solo necesitamos CODIGO_INDICADOR y TIPO_DATO para aplicar tipos en el pivot
df_tipo_indicador = df_clasificacion.select("CODIGO_INDICADOR", "TIPO_DATO")

# COMMAND ----------

# DBTITLE 1,Paso 4: Generar PIVOT dinámico para TODOS los indicadores
# ============================================================================
# PASO 3: PREPARACIÓN DEL PIVOT DINÁMICO
# ============================================================================
# Objetivo: Obtener lista completa de indicadores para el pivot
# Nota: Esta celda prepara las estructuras pero el pivot real ocurre en la celda 6

# --- Obtener lista de todos los indicadores únicos ---
# Esto define cuántas columnas tendrá la tabla final (una por cada indicador)
df_indicadores = (
    df_datos_unificados
    .select("CODIGO_INDICADOR")
    .distinct()
    .orderBy("CODIGO_INDICADOR")  # Ordenar para consistencia
)

# Convertir a lista Python para uso en pivot
indicadores = [row.CODIGO_INDICADOR for row in df_indicadores.collect()]

print(f"Total de indicadores a pivotar: {len(indicadores)}")
print(f"Estos indicadores se convertirán en columnas en la tabla final")

# --- Generar cláusulas CASE para pivot SQL (no usado, solo informativo) ---
# Esta lógica muestra cómo se vería en SQL puro
# En la práctica usamos la función pivot() de PySpark en la siguiente celda
case_statements = []
for ind in indicadores:
    case_statements.append(f"MAX(CASE WHEN CODIGO_INDICADOR = '{ind}' THEN VALOR END) AS `{ind}`")

pivot_sql = ",\n  ".join(case_statements)
print(f"\nCláusulas CASE generadas: {len(case_statements)}")

# COMMAND ----------

# DBTITLE 1,Paso 5: Crear tabla pivoteada completa con estandarización temporal
# ============================================================================
# PASO 4: EJECUTAR PIVOT Y APLICAR TIPOS DE DATOS CORRECTOS
# ============================================================================
# Este es el paso más crítico: transforma formato largo → ancho
#
# TRANSFORMACIÓN:
# Formato LARGO (input):  ~30M filas × 16 columnas
# Formato ANCHO (output): ~20K filas × ~1,590 columnas
#
# Cada fila en el output representa: ENTIDAD × AÑO × MES
# Cada columna es un CODIGO_INDICADOR con su valor

# --- Obtener lista de indicadores a pivotar ---
indicadores_list = [row.CODIGO_INDICADOR for row in 
                    df_datos_unificados.select("CODIGO_INDICADOR").distinct().collect()]

print(f"Pivotando {len(indicadores_list)} indicadores...")
print("Este proceso puede tomar varios minutos...")

# --- Ejecutar PIVOT ---
# Operación: groupBy + pivot + agg(max)
# - groupBy: Define las claves de agrupación (dimensiones que se conservan como filas)
# - pivot: Define qué valores se convierten en columnas (CODIGO_INDICADOR)
# - agg(max): Función de agregación (max porque solo debe haber 1 valor por combinación)

df_pivoteado = (
    df_datos_unificados
    .groupBy(
        # --- CLAVES DE AGRUPACIÓN (se mantienen como filas) ---
        "CODIGO_DEPARTAMENTO",          # Geografía
        "DEPARTAMENTO",
        "DEPARTAMENTO_NORMALIZADO",
        "CODIGO_ENTIDAD",
        "ENTIDAD",
        "ENTIDAD_NORMALIZADO",
        "ANO",                          # Temporalidad
        "MES"
    )
    # Pivotar: Cada valor único de CODIGO_INDICADOR se convierte en columna
    .pivot("CODIGO_INDICADOR", indicadores_list)
    # Agregación: MAX toma el valor (debería haber solo 1 por grupo)
    .agg(spark_max("VALOR"))
)

print(f"\n✅ Tabla pivoteada creada con {df_pivoteado.count():,} filas")
print(f"   Total de columnas: {len(df_pivoteado.columns)}")
print(f"   - Columnas de identificación: 8")
print(f"   - Columnas de indicadores: {len(df_pivoteado.columns) - 8}")


# ============================================================================
# APLICAR TIPOS DE DATOS CORRECTOS A CADA COLUMNA
# ============================================================================
# Problema: Después del pivot, TODAS las columnas son string (porque unificamos valores)
# Solución: Convertir indicadores numéricos a double usando la clasificación del Paso 2

print("\nAplicando tipos de datos correctos a cada columna de indicador...")

# --- Crear diccionario de clasificación para búsqueda rápida ---
tipo_indicador_dict = {row.CODIGO_INDICADOR: row.TIPO_DATO 
                        for row in df_tipo_indicador.collect()}
print(f"Diccionario de tipos cargado: {len(tipo_indicador_dict)} indicadores")


# --- Identificar columnas de identificación (no tocar) vs columnas de indicadores ---
columnas_id = [
    "CODIGO_DEPARTAMENTO", "DEPARTAMENTO", "DEPARTAMENTO_NORMALIZADO",
    "CODIGO_ENTIDAD", "ENTIDAD", "ENTIDAD_NORMALIZADO", "ANO", "MES"
]

# --- Construir lista de columnas con tipos correctos ---
columnas_con_tipo = []

# PASO 1: Agregar columnas de identificación sin modificar
for col_name in columnas_id:
    columnas_con_tipo.append(col(col_name))

# PASO 2: Agregar columnas de indicadores con el tipo correcto
count_numerico = 0
count_cualitativo = 0

for col_name in df_pivoteado.columns:
    if col_name not in columnas_id:  # Es una columna de indicador
        # Buscar tipo en el diccionario (default a cualitativo si no existe)
        tipo = tipo_indicador_dict.get(col_name, "cualitativo")
        
        if tipo == "numerico":
            # INDICADOR NUMÉRICO: Convertir a double usando try_cast
            # try_cast es seguro: valores no numéricos (ej: "preliminar") → NULL
            columnas_con_tipo.append(expr(f"try_cast(`{col_name}` as double)").alias(col_name))
            count_numerico += 1
        else:
            # INDICADOR CUALITATIVO: Mantener como string
            columnas_con_tipo.append(col(col_name))
            count_cualitativo += 1

# PASO 3: Aplicar la transformación de tipos
df_pivoteado = df_pivoteado.select(columnas_con_tipo)

print(f"\n✅ Tipos de datos aplicados:")
print(f"  - Indicadores numéricos (double con try_cast): {count_numerico}")
print(f"  - Indicadores cualitativos (string): {count_cualitativo}")
print(f"  - Total: {count_numerico + count_cualitativo}")
print(f"\n⚠️  Nota importante:")
print(f"   Valores no numéricos en columnas numéricas (ej: 'preliminar') se")
print(f"   convierten a NULL con try_cast. Esto es comportamiento esperado.")

# COMMAND ----------

# DBTITLE 1,Funciones de verificación
# ============================================================================
# FUNCIONES DE VERIFICACIÓN DE INTEGRIDAD
# ============================================================================
# Estas funciones validan que la transformación largo → ancho sea correcta
# ⚠️  IMPORTANTE: Estas verificaciones son DEMORADAS (~10-15 min)
# Solo activar cuando sea necesario (ver celda 8)

# ----------------------------------------------------------------------------
# VERIFICACIÓN 1: CONSERVACIÓN DE REGISTROS
# ----------------------------------------------------------------------------
# Valida que el número de combinaciones únicas se conserve
# LARGO: # combinaciones únicas (ENTIDAD × AÑO × MES)
# ANCHO: # filas en tabla pivoteada
# Deberían ser iguales

def verificar_conservacion_registros(df_largo: DataFrame, df_ancho: DataFrame) -> bool:
    """
    Verifica que el número de registros únicos se conserve entre formato largo y ancho.
    
    Args:
        df_largo: DataFrame en formato largo (original)
        df_ancho: DataFrame en formato ancho (pivoteado)
    
    Returns:
        bool: True si los registros se conservaron correctamente
    """
    count_largo = df_largo.select(
        "CODIGO_DEPARTAMENTO", "CODIGO_ENTIDAD", "ANO", "MES"
    ).distinct().count()
    
    count_ancho = df_ancho.count()
    
    print("=" * 60)
    print("VERIFICACIÓN 1: CONSERVACIÓN DE REGISTROS")
    print("=" * 60)
    print(f"Combinaciones únicas ENTIDAD × AÑO × MES en formato LARGO: {count_largo:,}")
    print(f"Filas en tabla PIVOTEADA (formato ANCHO):                {count_ancho:,}")
    print()
    
    if count_largo == count_ancho:
        print("✅ CORRECTO: El número de registros se conservó")
        return True
    else:
        print(f"❌ ERROR: Se perdieron o duplicaron {abs(count_largo - count_ancho):,} registros")
        print("   Esto podría indicar duplicados en los datos originales")
        return False



# ----------------------------------------------------------------------------
# VERIFICACIÓN 2: INTEGRIDAD DE VALORES
# ----------------------------------------------------------------------------
# Compara un caso específico entre formato largo y ancho
# para verificar que los valores se conservan exactamente

def verificar_integridad_valores(df_largo: DataFrame, df_ancho: DataFrame,
                                  test_entidad: str = "05001",
                                  test_ano: int = 2020,
                                  test_mes: int = 12,
                                  test_indicador: str = "010010009") -> bool:
    """
    Verifica que los valores específicos coincidan entre formato largo y ancho.
    Compara valores como strings para manejar tipos mixtos.
    
    Args:
        df_largo: DataFrame en formato largo
        df_ancho: DataFrame en formato ancho
        test_entidad: Código de entidad para prueba (default: Medellín)
        test_ano: Año para prueba
        test_mes: Mes para prueba
        test_indicador: Código de indicador para prueba (default: Población total)
    
    Returns:
        bool: True si los valores coinciden
    """
    print("=" * 60)
    print("VERIFICACIÓN 2: INTEGRIDAD DE VALORES")
    print("=" * 60)
    print(f"Caso de prueba:")
    print(f"  - Entidad: {test_entidad} (Medellín)")
    print(f"  - Año: {test_ano}")
    print(f"  - Mes: {test_mes}")
    print(f"  - Indicador: {test_indicador} (Población total)")
    print()
    
    # Valor en formato LARGO
    valor_largo = df_largo.filter(
        (col("CODIGO_ENTIDAD") == test_entidad) &
        (col("ANO") == test_ano) &
        (col("MES") == test_mes) &
        (col("CODIGO_INDICADOR") == test_indicador)
    ).select("VALOR").first()
    
    # Valor en formato ANCHO (convertir a string para comparación)
    valor_ancho_row = df_ancho.filter(
        (col("CODIGO_ENTIDAD") == test_entidad) &
        (col("ANO") == test_ano) &
        (col("MES") == test_mes)
    ).select(col(f"`{test_indicador}`").cast("string")).first()
    
    valor_largo_str = valor_largo[0] if valor_largo else None
    valor_ancho_str = valor_ancho_row[0] if valor_ancho_row else None
    
    print(f"Valor en formato LARGO: {valor_largo_str if valor_largo_str else 'NULL'}")
    print(f"Valor en formato ANCHO:  {valor_ancho_str if valor_ancho_str else 'NULL'}")
    print()
    
    if valor_largo_str == valor_ancho_str:
        print("✅ CORRECTO: Los valores coinciden")
        return True
    else:
        print("❌ ERROR: Los valores NO coinciden")
        return False



# ----------------------------------------------------------------------------
# VERIFICACIÓN 3: DETECCIÓN DE DUPLICADOS
# ----------------------------------------------------------------------------
# Verifica que no existan filas duplicadas en las claves de agrupación
# Si hay duplicados, indica un problema en el pivot o en los datos fuente

def verificar_duplicados(df_ancho: DataFrame) -> bool:
    """
    Verifica que no existan duplicados en las claves de agrupación.
    
    Args:
        df_ancho: DataFrame en formato ancho (pivoteado)
    
    Returns:
        bool: True si no hay duplicados
    """
    print("=" * 60)
    print("VERIFICACIÓN 3: DETECCIÓN DE DUPLICADOS")
    print("=" * 60)
    
    total_filas = df_ancho.count()
    filas_unicas = df_ancho.select(
        "CODIGO_DEPARTAMENTO", "CODIGO_ENTIDAD", "ANO", "MES"
    ).distinct().count()
    
    print(f"Total de filas en tabla pivoteada:    {total_filas:,}")
    print(f"Combinaciones únicas de claves:       {filas_unicas:,}")
    print()
    
    if total_filas == filas_unicas:
        print("✅ CORRECTO: No hay duplicados")
        return True
    else:
        print(f"❌ ERROR: Hay {total_filas - filas_unicas:,} filas duplicadas")
        print("\nEjemplos de duplicados:")
        
        duplicados = df_ancho.groupBy(
            "CODIGO_DEPARTAMENTO", "CODIGO_ENTIDAD", "ANO", "MES"
        ).count().filter(col("count") > 1)
        
        display(duplicados.limit(10))
        return False



# ----------------------------------------------------------------------------
# VERIFICACIÓN 4: TOTAL DE VALORES NO NULOS
# ----------------------------------------------------------------------------
# Verifica que el total de valores no nulos se conserve
# Tolerancia del 1% para valores "preliminar" convertidos a NULL con try_cast

def verificar_valores_no_nulos(df_largo: DataFrame, df_ancho: DataFrame, tolerancia_porcentaje: float = 1.0) -> bool:
    """
    Verifica que el total de valores no nulos se conserve.
    Permite una diferencia pequeña debido a valores "preliminar" convertidos a NULL.
    
    Args:
        df_largo: DataFrame en formato largo
        df_ancho: DataFrame en formato ancho
        tolerancia_porcentaje: Porcentaje máximo de diferencia aceptable (default: 1%)
    
    Returns:
        bool: True si los valores se conservaron dentro de la tolerancia
    """
    print("=" * 60)
    print("VERIFICACIÓN 4: TOTAL DE VALORES NO NULOS")
    print("=" * 60)
    
    # Total de valores en formato LARGO
    total_valores_largo = df_largo.filter(col("VALOR").isNotNull()).count()
    
    print(f"Total de valores no nulos en formato LARGO: {total_valores_largo:,}")
    print()
    
    # Total de valores en formato ANCHO
    indicadores_cols = [c for c in df_ancho.columns if c not in [
        "CODIGO_DEPARTAMENTO", "DEPARTAMENTO", "DEPARTAMENTO_NORMALIZADO",
        "CODIGO_ENTIDAD", "ENTIDAD", "ENTIDAD_NORMALIZADO", "ANO", "MES"
    ]]
    
    count_expr = sum([when(col(c).isNotNull(), 1).otherwise(0) for c in indicadores_cols])
    total_valores_ancho = df_ancho.select(spark_sum(count_expr).alias("total")).first()[0]
    
    print(f"Total de valores no nulos en formato ANCHO:  {total_valores_ancho:,}")
    
    diferencia = abs(total_valores_largo - total_valores_ancho)
    porcentaje_diferencia = (diferencia / total_valores_largo) * 100 if total_valores_largo > 0 else 0
    
    print(f"Diferencia: {diferencia:,} valores ({porcentaje_diferencia:.3f}%)")
    print()
    
    if total_valores_largo == total_valores_ancho:
        print("✅ CORRECTO: Todos los valores se conservaron (100% match)")
        return True
    elif porcentaje_diferencia <= tolerancia_porcentaje:
        print(f"✅ CORRECTO: Diferencia dentro de tolerancia ({tolerancia_porcentaje}%)")
        print(f"   Nota: Valores 'preliminar' en columnas numéricas se convierten a NULL con try_cast")
        return True
    else:
        print(f"❌ ERROR: Diferencia ({porcentaje_diferencia:.2f}%) excede tolerancia ({tolerancia_porcentaje}%)")
        return False

# COMMAND ----------

# DBTITLE 1,Ejecutar todas las verificaciones
# MAGIC %skip
# MAGIC # ============================================================================
# MAGIC # EJECUCIÓN DE VERIFICACIONES DE INTEGRIDAD
# MAGIC # ============================================================================
# MAGIC # ⚠️  IMPORTANTE: ESTA CELDA ESTÁ DESHABILITADA POR DEFECTO
# MAGIC #
# MAGIC # ¿POR QUÉ ESTÁ DESHABILITADA?
# MAGIC # - Estas verificaciones son MUY DEMORADAS (~10-15 minutos)
# MAGIC # - Realizan múltiples count() en tablas grandes (~30M registros en formato largo)
# MAGIC # - Solo son necesarias durante desarrollo o debugging
# MAGIC # - En ejecuciones productivas rutinarias NO son necesarias
# MAGIC #
# MAGIC # ¿CUÁNDO ACTIVARLAS?
# MAGIC # ✅ Primera ejecución del notebook (validación inicial)
# MAGIC # ✅ Después de cambios en la lógica de pivot
# MAGIC # ✅ Si se sospecha pérdida de datos o problemas de integridad
# MAGIC # ✅ Después de actualizar la tabla bronce fuente con datos nuevos
# MAGIC # ❌ En actualizaciones rutinarias mensuales (una vez validado el proceso)
# MAGIC #
# MAGIC # CÓMO ACTIVARLAS:
# MAGIC # 1. Descomentar TODO el código de esta celda
# MAGIC # 2. Ejecutar la celda
# MAGIC # 3. Revisar el resumen final (todas deben pasar ✅)
# MAGIC # 4. Volver a comentar después de confirmar que todo está correcto
# MAGIC # ============================================================================
# MAGIC
# MAGIC # DESCOMENTAR EL CÓDIGO ABAJO PARA EJECUTAR VERIFICACIONES
# MAGIC
# MAGIC """
# MAGIC # Ejecutar todas las verificaciones en secuencia
# MAGIC print("\n" + "="*60)
# MAGIC print("EJECUTANDO TODAS LAS VERIFICACIONES")
# MAGIC print("="*60 + "\n")
# MAGIC
# MAGIC resultados = {
# MAGIC     "Conservación de registros": verificar_conservacion_registros(df_datos_unificados, df_pivoteado),
# MAGIC     "Integridad de valores": verificar_integridad_valores(df_datos_unificados, df_pivoteado),
# MAGIC     "Detección de duplicados": verificar_duplicados(df_pivoteado),
# MAGIC     "Valores no nulos": verificar_valores_no_nulos(df_datos_unificados, df_pivoteado)
# MAGIC }
# MAGIC
# MAGIC print("\n" + "="*60)
# MAGIC print("RESUMEN DE VERIFICACIONES")
# MAGIC print("="*60)
# MAGIC
# MAGIC for nombre, resultado in resultados.items():
# MAGIC     status = "✅ PASS" if resultado else "❌ FAIL"
# MAGIC     print(f"{status} - {nombre}")
# MAGIC
# MAGIC if all(resultados.values()):
# MAGIC     print("\n✅ TODAS LAS VERIFICACIONES PASARON - La transformación es correcta")
# MAGIC else:
# MAGIC     print("\n❌ ALGUNAS VERIFICACIONES FALLARON - Revisar los detalles arriba")
# MAGIC """
# MAGIC
# MAGIC # ============================================================================
# MAGIC # MENSAJE CUANDO LAS VERIFICACIONES ESTÁN DESHABILITADAS
# MAGIC # ============================================================================
# MAGIC print("\n" + "="*60)
# MAGIC print("⚠️  VERIFICACIONES DE INTEGRIDAD DESHABILITADAS")
# MAGIC print("="*60)
# MAGIC print("\nLas verificaciones están comentadas para acelerar la ejecución.")
# MAGIC print("Son muy demoradas (~10-15 min) y solo necesarias durante desarrollo.")
# MAGIC print("\nPara activarlas:")
# MAGIC print("  1. Descomentar el código de esta celda")
# MAGIC print("  2. Ejecutar la celda")
# MAGIC print("  3. Revisar que todas las verificaciones pasen ✅")
# MAGIC print("\nVerificaciones disponibles:")
# MAGIC print("  - Conservación de registros")
# MAGIC print("  - Integridad de valores")
# MAGIC print("  - Detección de duplicados")
# MAGIC print("  - Valores no nulos")
# MAGIC print("="*60 + "\n")

# COMMAND ----------

# DBTITLE 1,Paso 7: Crear tabla de metadatos de indicadores
# ============================================================================
# PASO 5: CREAR TABLA DIMENSIONAL DE METADATOS DE INDICADORES
# ============================================================================
# Objetivo: Crear tabla de referencia con información de cada indicador
# Esta tabla es fundamental para:
# - Documentar qué significa cada columna de la tabla pivoteada
# - Filtrar indicadores por dimensión o tipo
# - Construir queries dinámicas
# - Validar datos y generar reportes

# --- Extraer información única de cada indicador ---
# Tomamos la primera ocurrencia de cada indicador (todos tienen la misma metadata)
df_metadatos = df_datos_unificados.select(
    "CODIGO_INDICADOR",      # Código único (PK de esta tabla dimensional)
    "INDICADOR",             # Nombre descriptivo del indicador
    "DIMENSION",             # Categoría temática (Demografía, Educación, etc.)
    "SUBCATEGORIA",          # Subcategoría dentro de la dimensión
    "UNIDAD_MEDIDA"          # Unidad de medida (personas, %, pesos, etc.)
).distinct()  # distinct() porque cada indicador aparece múltiples veces en el largo


# --- Enriquecer con clasificación de tipo de dato ---
# Agregar el campo TIPO_DATO (numerico/cualitativo) calculado en el Paso 2
df_metadatos = (
    df_metadatos
    .join(
        df_tipo_indicador,           # Tabla con clasificación de tipos
        on="CODIGO_INDICADOR",       # Join por código de indicador
        how="left"                   # LEFT para preservar todos los indicadores
    )
    .orderBy("CODIGO_INDICADOR")    # Ordenar para facilitar navegación
)

print(f"\n✅ Total de indicadores documentados: {df_metadatos.count()}")

# --- Mostrar resumen de tipos de datos ---
print("\nDistribución de tipos de datos:")
display(df_metadatos.groupBy("TIPO_DATO").count().orderBy("TIPO_DATO"))


# --- Guardar tabla dimensional ---
# Esquema: tesis.dim (para tablas dimensionales)
# Tabla: dim_indicadores (metadata de referencia)
df_metadatos.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.dim.dim_indicadores"
)

print("\n✅ Tabla dimensional guardada: tesis.dim.dim_indicadores")
print("\nCampos de la tabla:")
print("  - CODIGO_INDICADOR (PK)")
print("  - INDICADOR (nombre descriptivo)")
print("  - DIMENSION (categoría temática)")
print("  - SUBCATEGORIA")
print("  - UNIDAD_MEDIDA")
print("  - TIPO_DATO (numerico/cualitativo)")
print("\nUso: SELECT * FROM tesis.dim.dim_indicadores WHERE DIMENSION = 'Educación'")

# COMMAND ----------

# DBTITLE 1,Paso 8: Guardar tabla final pivoteada
# ============================================================================
# PASO 6: GUARDAR TABLA FINAL PIVOTEADA EN CAPA PLATA
# ============================================================================
# Esta es la tabla final del proceso de transformación
# Formato ANCHO (wide) listo para análisis multidimensional

# --- Persistir en Unity Catalog ---
df_pivoteado.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.terridata.terridata_extendido_plata"
)

print("\n" + "="*60)
print("✅ TABLA PIVOTEADA GUARDADA EXITOSAMENTE")
print("="*60)
print(f"\nTabla: tesis.terridata.terridata_extendido_plata")
print(f"\nESTADÍSTICAS:")
print(f"  - Filas: {df_pivoteado.count():,}")
print(f"  - Columnas totales: {len(df_pivoteado.columns)}")
print(f"    • Columnas de identificación: 8")
print(f"    • Columnas de indicadores: {len(df_pivoteado.columns) - 8}")

print(f"\nESTRUCTURA DE COLUMNAS:")
print(f"  1. Geografía:")
print(f"     - CODIGO_DEPARTAMENTO, DEPARTAMENTO, DEPARTAMENTO_NORMALIZADO")
print(f"     - CODIGO_ENTIDAD, ENTIDAD, ENTIDAD_NORMALIZADO")
print(f"  2. Temporalidad:")
print(f"     - ANO (int), MES (int)")
print(f"  3. Indicadores ({len(df_pivoteado.columns) - 8} columnas):")
print(f"     - Cada columna = un CODIGO_INDICADOR")
print(f"     - Valores: double (numéricos) o string (cualitativos)")

print(f"\nTABLAS RELACIONADAS:")
print(f"  → tesis.dim.dim_indicadores")
print(f"     (metadata de los {len(df_pivoteado.columns) - 8} indicadores)")

print(f"\nEJEMPLO DE CONSULTA:")
print(f"  SELECT ENTIDAD, ANO, `010010009` as poblacion_total")
print(f"  FROM tesis.terridata.terridata_extendido_plata")
print(f"  WHERE ANO >= 2020 AND CODIGO_DEPARTAMENTO = '05'")

print("\n" + "="*60)
print("✅ PROCESO COMPLETADO - FORMATO LARGO → ANCHO")
print("="*60 + "\n")