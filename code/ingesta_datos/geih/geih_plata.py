# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Transformación de Datos GEIH - Capa Plata (Silver)
# MAGIC
# MAGIC Este notebook procesa y consolida los datos de la **Gran Encuesta Integrada de Hogares (GEIH)** desde la capa bronce hacia la capa plata, aplicando transformaciones de normalización, estandarización de campos y consolidación de múltiples fuentes.
# MAGIC
# MAGIC ## Propósito
# MAGIC Transformar los datos bronce en tablas estandarizadas y consolidadas que unifican:
# MAGIC * **Marco antiguo y marco nuevo** en una sola estructura
# MAGIC * **Diferentes secciones geográficas** (área, cabecera, resto) en tablas consolidadas
# MAGIC * **Campos núcleo comunes** para todos los módulos
# MAGIC
# MAGIC ## Arquitectura de Transformación
# MAGIC
# MAGIC ### Campos Núcleo
# MAGIC Cada tabla plata incluye un conjunto de **campos núcleo** estandarizados:
# MAGIC * `PK`: Clave primaria concatenada (PERIODO + DIRECTORIO + SECUENCIA_P + ORDEN)
# MAGIC * `PERIODO`: Periodo en formato YYYYMM
# MAGIC * `PER`: Año (int)
# MAGIC * `MES`: Mes (int)
# MAGIC * `DIRECTORIO`, `SECUENCIA_P`, `ORDEN`: Identificadores de hogar y persona
# MAGIC * `HOGAR`, `REGIS`: Clasificación de registro
# MAGIC * `CODIGO_AREA`: Código de área geográfica
# MAGIC * `FEX`: Factor de expansión normalizado
# MAGIC * `CODIGO_DPTO`: Código de departamento
# MAGIC
# MAGIC ### Diferencias entre Marcos
# MAGIC
# MAGIC **Marco Nuevo:**
# MAGIC * Los campos ya vienen estructurados en las tablas bronce
# MAGIC * `PERIODO` y `MES` están presentes directamente
# MAGIC * `FEX_C18` es el factor de expansión
# MAGIC
# MAGIC **Marco Antiguo:**
# MAGIC * `PERIODO` y `PER` se extraen del nombre del archivo origen mediante regex
# MAGIC * `MES` se extrae del campo correspondiente
# MAGIC * `FEX_C_2011` requiere limpieza (reemplazo de comas por puntos)
# MAGIC * Datos divididos en 3 secciones: área, cabecera, resto
# MAGIC
# MAGIC ## Módulos Procesados
# MAGIC
# MAGIC ### 1. Características Generales
# MAGIC **Campos específicos:**
# MAGIC * `SEXO`: Masculino/Femenino (normalizado desde códigos 1/2)
# MAGIC * `EDAD`: Edad en años
# MAGIC * `ANO_NACIMIENTO`: Año de nacimiento
# MAGIC * `MES_NACIMIENTO`: Mes de nacimiento
# MAGIC
# MAGIC **Salida:** `tesis.geih_plata.caracteristicas_generales_consolidado`
# MAGIC
# MAGIC ### 2. Fuerza de Trabajo
# MAGIC **Campos específicos:**
# MAGIC * `PEA`: Población Económicamente Activa (1 si no es inactivo)
# MAGIC * `PEI`: Población Económicamente Inactiva
# MAGIC * `PET`: Población en Edad de Trabajar
# MAGIC
# MAGIC **Lógica especial marco antiguo:**
# MAGIC * Se combinan tablas de fuerza de trabajo e inactivos mediante LEFT JOIN
# MAGIC * `PEA` se calcula: 1 si PEI es NULL o vacío, 0 en otro caso
# MAGIC * Campo `FT` en "resto" se normaliza (strings vacíos → "1")
# MAGIC
# MAGIC **Salida:** `tesis.geih_plata.fuerza_trabajo_consolidado`
# MAGIC
# MAGIC ### 3. No Ocupados (Desocupados)
# MAGIC **Campos específicos:**
# MAGIC * `DESOCUPADO`: Indicador de desocupación (campo DSI)
# MAGIC
# MAGIC **Salida:** `tesis.geih_plata.no_ocupados_consolidado`
# MAGIC
# MAGIC ### 4. Ocupados
# MAGIC **Campos específicos:**
# MAGIC * `OCUPADO`: Indicador de ocupación (campo OCI)
# MAGIC
# MAGIC **Salida:** `tesis.geih_plata.ocupados_consolidado`
# MAGIC
# MAGIC ### 5. Factores de Expansión (FEX)
# MAGIC Tabla dimensional con factores de expansión corregidos.
# MAGIC
# MAGIC **Campos:**
# MAGIC * `PK`: Clave primaria
# MAGIC * `DIRECTORIO`, `SECUENCIA_P`, `ORDEN`: Identificadores
# MAGIC * `ANO`, `MES`: Periodo
# MAGIC * `FEX_C18`: Factor de expansión (double)
# MAGIC
# MAGIC **Salida:** `tesis.geih_plata.dim_fex`
# MAGIC
# MAGIC ## Transformaciones Aplicadas
# MAGIC
# MAGIC 1. **Estandarización de PK**: Concatenación consistente de campos clave
# MAGIC 2. **Normalización de tipos**: Cast a int/double donde corresponda
# MAGIC 3. **Limpieza de datos**: 
# MAGIC    - Trim en códigos AREA y DPTO
# MAGIC    - Reemplazo de comas por puntos en valores numéricos
# MAGIC    - Conversión de strings vacíos a valores por defecto
# MAGIC 4. **Codificación semántica**: Transformación de códigos a etiquetas (ej: 1→MASCULINO, 2→FEMENINO)
# MAGIC 5. **Consolidación**: Union de datos de marco nuevo + marco antiguo para cada módulo

# COMMAND ----------

# DBTITLE 1,Importación de librerías
# Importar funciones de PySpark necesarias para transformaciones
from pyspark.sql.functions import (
    col,             # Referenciar columnas
    when,            # Expresiones condicionales
    concat,          # Concatenar columnas
    regexp_extract,  # Extraer patrones con regex
    regexp_replace,  # Reemplazar patrones con regex
    expr,            # Expresiones SQL en PySpark
    coalesce,        # Retornar primer valor no-NULL
    lit,             # Crear columnas literales
    trim             # Eliminar espacios en blanco
)

# COMMAND ----------

# DBTITLE 1,Campos nucleo
# ============================================================================
# DEFINICIÓN DE CAMPOS NÚCLEO
# ============================================================================
# Estos campos se incluyen en TODAS las tablas plata y proveen la estructura
# básica de identificación, periodo, ubicación geográfica y factor de expansión.

# --- CAMPOS NÚCLEO PARA MARCO NUEVO ---
# El marco nuevo tiene los campos ya estructurados en las tablas bronce
campos_geih_nucleo_marco_nuevo = [
    # Clave primaria: concatenación de periodo + identificadores de hogar y persona
    concat(col("PERIODO"), col("DIRECTORIO"), col("SECUENCIA_P"), col("ORDEN")).alias("PK"),
    col("PERIODO"),                              # Periodo en formato YYYYMM (string)
    col("PER").cast("int").alias("PER"),        # Año (entero)
    col("MES").cast("int").alias("MES"),        # Mes (entero)
    col("DIRECTORIO"),                           # Identificador del directorio/hogar
    col("SECUENCIA_P"),                          # Secuencia de la persona en el hogar
    col("ORDEN"),                                # Orden de la persona
    col("HOGAR"),                                # Tipo de hogar
    col("REGIS"),                                # Tipo de registro
    trim(col("AREA")).alias("CODIGO_AREA"),     # Código de área geográfica (limpiado)
    col("FEX_C18").alias("FEX"),                 # Factor de expansión (censo 2018)
    trim(col("DPTO")).alias("CODIGO_DPTO"),      # Código de departamento (limpiado)
]

# --- CAMPOS NÚCLEO PARA MARCO ANTIGUO ---
# El marco antiguo requiere extraer periodo del nombre de archivo y limpiar FEX
campos_geih_nucleo_marco_antiguo = [
    # Clave primaria: año (extraído de archivo) + mes + identificadores
    concat(
        regexp_extract(col("archivo_origen"), r"(\d{4})", 1),  # Extraer año del nombre de archivo
        col("MES"),
        col("DIRECTORIO"),
        col("SECUENCIA_P"),
        col("ORDEN")
    ).alias("PK"),
    # Periodo: concatenación de año y mes extraídos
    concat(
        regexp_extract(col("archivo_origen"), r"(\d{4})", 1),
        col("MES")
    ).alias("PERIODO"),
    regexp_extract(col("archivo_origen"), r"(\d{4})", 1).cast("int").alias("PER"),  # Año (int)
    col("MES").cast("int").alias("MES"),                                              # Mes (int)
    col("DIRECTORIO"),                                                                # Identificadores
    col("SECUENCIA_P"),
    col("ORDEN"),
    col("HOGAR"),                                                                     # Clasificación
    col("REGIS"),
    trim(col("AREA")).alias("CODIGO_AREA"),                                           # Código área
    regexp_replace(col("FEX_C_2011"), ",", ".").cast("double").alias("FEX"),        # FEX: reemplazar comas por puntos y convertir a double
    trim(col("DPTO")).alias("CODIGO_DPTO"),                                           # Código departamento
]

# COMMAND ----------

# MAGIC %md
# MAGIC # Caracteristicas Generales (Marco Nuevo)

# COMMAND ----------

# DBTITLE 1,Caracteristicas generales silver
# ============================================================================
# CARACTERÍSTICAS GENERALES - MARCO NUEVO
# ============================================================================
# Procesa datos demográficos básicos: sexo, edad, nacimiento

# Cargar tabla bronce de características generales (marco nuevo)
df = spark.table("tesis.geih_bronce.caracteristicas_generales")

# Aplicar transformaciones: campos núcleo + campos demográficos
df_cg_plata = df.select(
    *campos_geih_nucleo_marco_nuevo,
    # Normalizar sexo: 1=MASCULINO, 2=FEMENINO
    when(col("P3271") == 1, "MASCULINO").when(col("P3271") == 2, "FEMENINO").alias("SEXO"),
    col("P6040").cast("int").alias("EDAD"),                      # Edad en años
    col("P6030S3").cast("int").alias("ANO_NACIMIENTO"),          # Año de nacimiento
    col("P6030S1").cast("int").alias("MES_NACIMIENTO")           # Mes de nacimiento
)

# COMMAND ----------

# MAGIC %md
# MAGIC # Caracteristicas Generales - Marco Antiguo

# COMMAND ----------

# --- CAMPOS DEMOGRÁFICOS PARA MARCO ANTIGUO ---
# En marco antiguo, los códigos de sexo vienen como string ("1", "2")
# y los demás campos requieren try_cast por posibles valores inválidos
select_fields_cg_antiguo = [
    # Normalizar sexo: "1"=MASCULINO, "2"=FEMENINO
    when(col("P6020") == "1", "MASCULINO").when(col("P6020") == "2", "FEMENINO").alias("SEXO"),
    expr("try_cast(P6040 as int)").alias("EDAD"),                  # Edad (try_cast maneja valores inválidos)
    expr("try_cast(P6030S3 as int)").alias("ANO_NACIMIENTO"),      # Año nacimiento
    expr("try_cast(P6030S1 as int)").alias("MES_NACIMIENTO")       # Mes nacimiento
]

# COMMAND ----------

# ============================================================================
# CARACTERÍSTICAS GENERALES - MARCO ANTIGUO
# ============================================================================
# Marco antiguo está dividido en 3 secciones geográficas: área, cabecera, resto
# Se procesan las 3 secciones y luego se consolidan

# Cargar tablas bronce de cada sección
df_cg_area = spark.table("tesis.geih_bronce.caracteristicas_generales_area_marco_antiguo")
df_cg_cabecera = spark.table("tesis.geih_bronce.caracteristicas_generales_cabecera_marco_antiguo")
df_cg_resto = spark.table("tesis.geih_bronce.caracteristicas_generales_resto_marco_antiguo")

# Aplicar mismas transformaciones a las 3 secciones: campos núcleo + demográficos
df_cg_area_plata = df_cg_area.select(
    *campos_geih_nucleo_marco_antiguo,      # Campos comunes del núcleo
    *select_fields_cg_antiguo               # Campos demográficos marco antiguo
)

df_cg_cabecera_plata = df_cg_cabecera.select(
    *campos_geih_nucleo_marco_antiguo,
    *select_fields_cg_antiguo
)

df_cg_resto_plata = df_cg_resto.select(
    *campos_geih_nucleo_marco_antiguo,
    *select_fields_cg_antiguo
)

# COMMAND ----------

# Consolidar todas las fuentes: marco nuevo + 3 secciones del marco antiguo
# Nota: df_cg_area no se incluye porque ya está contenido en cabecera + resto
df_cg_plata_consolidado = df_cg_plata.union(df_cg_cabecera_plata).union(df_cg_resto_plata)

# COMMAND ----------

# Guardar tabla consolidada en capa plata (modo overwrite)
df_cg_plata_consolidado.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.geih_plata.caracteristicas_generales_consolidado"
)

# COMMAND ----------

# MAGIC %md
# MAGIC # Fuerza de trabajo (Marco Nuevo)

# COMMAND ----------

# ============================================================================
# FUERZA DE TRABAJO - MARCO NUEVO
# ============================================================================
# Indicadores de participación laboral: PEA, PEI, PET

# Cargar tabla bronce de fuerza de trabajo (marco nuevo)
df_ft = spark.table("tesis.geih_bronce.fuerza_trabajo")

# Aplicar transformaciones: campos núcleo + indicadores laborales
df_ft_plata = df_ft.select(
    *campos_geih_nucleo_marco_nuevo,
    col("FT").alias("PEA"),      # Población Económicamente Activa (en fuerza de trabajo)
    col("FFT").alias("PEI"),     # Población Económicamente Inactiva (fuera de fuerza trabajo)
    col("PET")                   # Población en Edad de Trabajar
)

# COMMAND ----------

# MAGIC %md
# MAGIC # Fuerza de trabajo - Marco antiguo

# COMMAND ----------

# --- CAMPO PET PARA MARCO ANTIGUO ---
# En las secciones cabecera y resto, el campo FT viene vacío para personas en PET
# Si FT está vacío, se asigna "1" como indicador de PET
fuerza_trabajo_marco_antiguo_select = [
    when(trim(col("FT")) == "", lit("1").cast("string")).otherwise(col("FT")).alias("PET")
]

# COMMAND ----------

# ============================================================================
# FUERZA DE TRABAJO - MARCO ANTIGUO
# ============================================================================
# Marco antiguo requiere combinar 2 tablas:
# 1. Fuerza de trabajo (con PET): personas en edad de trabajar
# 2. Inactivos (con PEI): personas económicamente inactivas
# PEA se calcula: si no está en inactivos, entonces está en PEA

# --- FUERZA DE TRABAJO POR SECCIÓN ---

# Área: campo FT ya contiene PET directamente
df_ft_area = spark.table("tesis.geih_bronce.fuerza_trabajo_area_marco_antiguo").select(
    *campos_geih_nucleo_marco_antiguo,
    col("FT").alias("PET")
)

# Cabecera: FT vacío se normaliza a "1" para PET
df_ft_cabecera = spark.table("tesis.geih_bronce.fuerza_trabajo_cabecera_marco_antiguo").select(
    *campos_geih_nucleo_marco_antiguo,
    *fuerza_trabajo_marco_antiguo_select
)

# Resto: FT vacío se normaliza a "1" para PET
df_ft_resto = spark.table("tesis.geih_bronce.fuerza_trabajo_resto_marco_antiguo").select(
    *campos_geih_nucleo_marco_antiguo,
    *fuerza_trabajo_marco_antiguo_select
)

# --- INACTIVOS POR SECCIÓN ---
# Campo INI (Inactivos) se renombra a PEI

df_i_area = spark.table("tesis.geih_bronce.inactivos_area_marco_antiguo").select(
    *campos_geih_nucleo_marco_antiguo,
    col("INI").alias("PEI")
)

df_i_cabecera = spark.table("tesis.geih_bronce.inactivos_cabecera_marco_antiguo").select(
    *campos_geih_nucleo_marco_antiguo,
    col("INI").alias("PEI")
)

df_i_resto = spark.table("tesis.geih_bronce.inactivos_resto_marco_antiguo").select(
    *campos_geih_nucleo_marco_antiguo,
    col("INI").alias("PEI")
)

# Consolidar secciones (cabecera + resto; área se procesa separadamente)
df_ft_marco_antiguo = df_ft_cabecera.unionAll(df_ft_resto)
df_i_marco_antiguo = df_i_cabecera.unionAll(df_i_resto)

# COMMAND ----------

# --- CALCULAR PEA MEDIANTE LEFT JOIN ---
# Lógica: Una persona está en PEA si NO está en la tabla de inactivos
# LEFT JOIN: todas las personas en fuerza_trabajo + agregar PEI si existe
df_ft_marco_antiguo_plata = df_ft_marco_antiguo.join(
    df_i_marco_antiguo,
    "PK",                                   # Join por clave primaria
    "left"                                  # Mantener todos los registros de fuerza_trabajo
).select(
    df_ft_marco_antiguo["*"],              # Todos los campos de fuerza de trabajo
    df_i_marco_antiguo["PEI"],             # Agregar campo PEI (NULL si no es inactivo)
    # Cálculo PEA: 1 si PEI es NULL o vacío (no inactivo), 0 si tiene valor (inactivo)
    when((df_i_marco_antiguo["PEI"].isNull()) | (df_i_marco_antiguo["PEI"] == ""), 1)
    .otherwise(0)
    .alias("PEA")
) 
    

# COMMAND ----------

# Consolidar marco nuevo y marco antiguo
# unionByName: une por nombre de columna (maneja diferencias de orden)
df_ft_consolidado = df_ft_plata.unionByName(df_ft_marco_antiguo_plata)

# COMMAND ----------

# Guardar tabla consolidada de fuerza de trabajo en capa plata
df_ft_consolidado.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.geih_plata.fuerza_trabajo_consolidado"
)

# COMMAND ----------

# MAGIC %md
# MAGIC # No Ocupados (Marco Nuevo)

# COMMAND ----------

# ============================================================================
# NO OCUPADOS (DESOCUPADOS) - MARCO NUEVO
# ============================================================================
# Personas que buscan empleo pero no están ocupadas

# Cargar tabla bronce de no ocupados (marco nuevo)
df_no = spark.table("tesis.geih_bronce.no_ocupados")

# Aplicar transformaciones: campos núcleo + indicador de desocupación
df_no_plata = df_no.select(
    *campos_geih_nucleo_marco_nuevo,
    col("DSI").alias("DESOCUPADO")        # Indicador de desocupación
)

# COMMAND ----------

# MAGIC %md
# MAGIC # No Ocupados - Marco Antiguo

# COMMAND ----------

# ============================================================================
# NO OCUPADOS (DESOCUPADOS) - MARCO ANTIGUO
# ============================================================================
# Dividido en 3 secciones: área, cabecera, resto

# Cargar tablas bronce de cada sección
df_no_area = spark.table("tesis.geih_bronce.no_ocupados_area_marco_antiguo")
df_no_cabecera = spark.table("tesis.geih_bronce.no_ocupados_cabecera_marco_antiguo")
df_no_resto = spark.table("tesis.geih_bronce.no_ocupados_resto_marco_antiguo")

# Aplicar mismas transformaciones a las 3 secciones
df_no_area_plata = df_no_area.select(
    *campos_geih_nucleo_marco_antiguo,
    col("DSI").alias("DESOCUPADO")          # Indicador de desocupación
)

df_no_cabecera_plata = df_no_cabecera.select(
    *campos_geih_nucleo_marco_antiguo,
    col("DSI").alias("DESOCUPADO")
)

df_no_resto_plata = df_no_resto.select(
    *campos_geih_nucleo_marco_antiguo,
    col("DSI").alias("DESOCUPADO")
)

# COMMAND ----------

# Consolidar todas las fuentes: marco nuevo + 3 secciones marco antiguo
df_no_consolidado = df_no_plata.unionAll(df_no_cabecera_plata).unionAll(df_no_resto_plata)

# Guardar tabla consolidada de no ocupados en capa plata
df_no_consolidado.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.geih_plata.no_ocupados_consolidado"
)

# COMMAND ----------

# MAGIC %md
# MAGIC # Ocupados Marco Nuevo

# COMMAND ----------

# ============================================================================
# OCUPADOS - MARCO NUEVO
# ============================================================================
# Personas con empleo/trabajo actual

# Cargar tabla bronce de ocupados (marco nuevo)
df_oc = spark.table("tesis.geih_bronce.ocupados")

# Aplicar transformaciones: campos núcleo + indicador de ocupación
df_oc_plata = df_oc.select(
    *campos_geih_nucleo_marco_nuevo,
    col("OCI").alias("OCUPADO")           # Indicador de ocupación
)

# COMMAND ----------

# MAGIC %md
# MAGIC # Ocupados Marco Antiguo

# COMMAND ----------

# ============================================================================
# OCUPADOS - MARCO ANTIGUO
# ============================================================================
# Marco antiguo tiene solo 2 secciones: cabecera y resto (no hay área)

# Cargar tablas bronce de cada sección
df_oc_cabecera = spark.table("tesis.geih_bronce.ocupados_cabecera_marco_antiguo")
df_oc_resto = spark.table("tesis.geih_bronce.ocupados_resto_marco_antiguo")

# Aplicar mismas transformaciones a ambas secciones
df_oc_cabecera_plata = df_oc_cabecera.select(
    *campos_geih_nucleo_marco_antiguo,
    col("OCI").alias("OCUPADO")            # Indicador de ocupación
)

df_oc_resto_plata = df_oc_resto.select(
    *campos_geih_nucleo_marco_antiguo,
    col("OCI").alias("OCUPADO")
)

# COMMAND ----------

# Consolidar todas las fuentes: marco nuevo + 2 secciones marco antiguo
df_oc_consolidado = df_oc_plata.unionAll(df_oc_cabecera_plata).unionAll(df_oc_resto_plata)

# Guardar tabla consolidada de ocupados en capa plata
df_oc_consolidado.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.geih_plata.ocupados_consolidado"
)

# COMMAND ----------

# MAGIC %md
# MAGIC # Corrección FEX

# COMMAND ----------

# ============================================================================
# FACTORES DE EXPANSIÓN (FEX)
# ============================================================================
# Tabla dimensional con factores de expansión corregidos para proyecciones

# Cargar y transformar tabla de factores de expansión
df_fex = spark.table("tesis.geih_bronce.dim_fex").select(
    # Clave primaria: TIME_FEXC + identificadores
    concat(col("TIME_FEXC"), col("DIRECTORIO"), col("SECUENCIA_P"), col("ORDEN")).alias("PK"),
    "DIRECTORIO",                                    # Identificadores
    "SECUENCIA_P",
    "ORDEN",
    col("Ano").cast("int").alias("ANO"),            # Año (entero)
    col("Mes").cast("int").alias("MES"),            # Mes (entero)
    col("FEX_C18").cast("double").alias("FEX_C18")  # Factor de expansión censo 2018 (double)
)

# COMMAND ----------

# Guardar tabla dimensional de factores de expansión en capa plata
df_fex.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.geih_plata.dim_fex"
)