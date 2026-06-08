# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Tabla Dimensional GEIH-DIVIPOLA - Geografía Específica para GEIH
# MAGIC
# MAGIC Este notebook crea una **tabla dimensional de geografía especializada** que contiene únicamente los **32 municipios/ciudades principales** incluidos en la Gran Encuesta Integrada de Hogares (GEIH).
# MAGIC
# MAGIC ## Propósito
# MAGIC Generar la tabla `tesis.dim.dim_geih_divipola` que:
# MAGIC * Filtra la dimensión completa DIVIPOLA para incluir **solo las ciudades encuestadas por la GEIH**
# MAGIC * Facilita joins eficientes con datos GEIH (menor volumen de datos)
# MAGIC * Proporciona información geográfica (departamento, municipio, coordenadas) para las áreas de interés
# MAGIC * Agrega el campo `CODIGO_AREA_GEIH` para compatibilidad con la estructura de datos GEIH
# MAGIC
# MAGIC ## Diferencia con dim_divipola
# MAGIC
# MAGIC | Característica | `dim_divipola` | `dim_geih_divipola` |
# MAGIC |----------------|----------------|---------------------|
# MAGIC | **Cobertura** | Todos los municipios de Colombia (~1,100) | Solo 32 ciudades principales de GEIH |
# MAGIC | **Uso** | Tabla dimensional general | Optimizada para joins con tablas GEIH |
# MAGIC | **Campos adicionales** | - | `CODIGO_AREA_GEIH` (mapeo a códigos GEIH) |
# MAGIC | **Volumen** | Completo | Reducido (solo ciudades relevantes) |
# MAGIC
# MAGIC ## ¿Qué ciudades incluye GEIH?
# MAGIC
# MAGIC La GEIH cubre las **32 ciudades principales** de Colombia, que incluyen:
# MAGIC * Las 32 capitales departamentales (excepto Yopal - Casanare)
# MAGIC * Ciudades con mayor población y actividad económica
# MAGIC * Representan aproximadamente el 70% de la población urbana del país
# MAGIC
# MAGIC ### Lista de códigos DIVIPOLA incluidos:
# MAGIC
# MAGIC ```
# MAGIC 05001 - Medellín          | 54001 - Cúcuta
# MAGIC 08001 - Barranquilla       | 63001 - Armenia
# MAGIC 11001 - Bogotá D.C.        | 66001 - Pereira
# MAGIC 13001 - Cartagena          | 68001 - Bucaramanga
# MAGIC 15001 - Tunja              | 70001 - Sincelejo
# MAGIC 17001 - Manizales          | 73001 - Ibagué
# MAGIC 18001 - Florencia          | 76001 - Cali
# MAGIC 19001 - Popayán            | 81001 - Arauca
# MAGIC 20001 - Valledupar         | 85001 - Yopal
# MAGIC 23001 - Montería           | 86001 - Mocoa
# MAGIC 27001 - Quibdó             | 88001 - San Andrés
# MAGIC 41001 - Neiva              | 91001 - Leticia
# MAGIC 44001 - Riohacha           | 94001 - Inírida
# MAGIC 47001 - Santa Marta        | 95001 - San José del Guaviare
# MAGIC 50001 - Villavicencio      | 97001 - Mitú
# MAGIC 52001 - Pasto              | 99001 - Puerto Carreño
# MAGIC ```
# MAGIC
# MAGIC **Nota**: El código `25001` (Yopal - Casanare) está comentado en la lista, lo que indica que no se incluye en la versión actual de GEIH.
# MAGIC
# MAGIC ## Estructura de la Tabla
# MAGIC
# MAGIC ### Campos de Entrada (desde `dim_divipola`):
# MAGIC * `CODIGO_DEPARTAMENTO`: Código DIVIPOLA del departamento (2 dígitos)
# MAGIC * `DEPARTAMENTO`: Nombre del departamento
# MAGIC * `CODIGO_MUNICIPIO`: Código DIVIPOLA del municipio (5 dígitos)
# MAGIC * `MUNICIPIO`: Nombre del municipio
# MAGIC * `LONGITUD`: Coordenada de longitud
# MAGIC * `LATITUD`: Coordenada de latitud
# MAGIC
# MAGIC ### Campos de Salida:
# MAGIC * `CODIGO_DEPARTAMENTO`: Código del departamento
# MAGIC * `DEPARTAMENTO`: Nombre del departamento
# MAGIC * **`CODIGO_AREA_GEIH`**: Alias de `CODIGO_DEPARTAMENTO` para compatibilidad con nomenclatura GEIH
# MAGIC * `CODIGO_MUNICIPIO`: Código del municipio (filtrado solo ciudades GEIH)
# MAGIC * `MUNICIPIO`: Nombre del municipio
# MAGIC * `LONGITUD`: Coordenada geográfica
# MAGIC * `LATITUD`: Coordenada geográfica
# MAGIC
# MAGIC ## Transformaciones Aplicadas
# MAGIC
# MAGIC 1. **Filtrado selectivo**: `filter()` con operador `isin()` para retener solo los 32 municipios
# MAGIC 2. **Creación de alias**: Campo `CODIGO_AREA_GEIH` como alias de `CODIGO_DEPARTAMENTO`
# MAGIC 3. **Selección de campos**: Solo campos relevantes para análisis GEIH
# MAGIC
# MAGIC ## Uso en el Pipeline GEIH
# MAGIC
# MAGIC Esta tabla se usa en la **capa ORO** para enriquecer las tablas de mercado laboral:
# MAGIC
# MAGIC ```python
# MAGIC # En geih_oro:
# MAGIC .join(geih_div.alias("div_dep"), 
# MAGIC       cg.CODIGO_DPTO == col("div_dep.CODIGO_DEPARTAMENTO"), "left")
# MAGIC .join(geih_div.alias("div_mun"), 
# MAGIC       cg.CODIGO_AREA == col("div_mun.CODIGO_AREA_GEIH"), "left")
# MAGIC ```
# MAGIC
# MAGIC ## Dependencias
# MAGIC
# MAGIC **Tabla fuente**: `tesis.dim.dim_divipola`
# MAGIC * Debe ejecutarse **después** de crear `dim_divipola`
# MAGIC * Hereda la estructura y calidad de datos de la tabla padre
# MAGIC
# MAGIC ## Ventajas de esta Tabla Especializada
# MAGIC
# MAGIC 1. **Performance**: Joins más rápidos (32 registros vs ~1,100)
# MAGIC 2. **Claridad**: Solo datos relevantes para GEIH
# MAGIC 3. **Mantenibilidad**: Lista centralizada de ciudades GEIH
# MAGIC 4. **Compatibilidad**: Campo `CODIGO_AREA_GEIH` facilita joins con nomenclatura GEIH

# COMMAND ----------

# DBTITLE 1,Importación de librerías
# Importar funciones de PySpark necesarias para el filtrado y transformación
from pyspark.sql.functions import (
    col    # Referenciar columnas para filtros y operaciones de selección
)

# COMMAND ----------

# DBTITLE 1,Ciudades GEIH
# ============================================================================
# LISTA DE CIUDADES INCLUIDAS EN LA GEIH
# ============================================================================
# La GEIH cubre las 32 ciudades principales de Colombia (capitales departamentales
# y ciudades con mayor actividad económica). Esta lista contiene los códigos
# DIVIPOLA de 5 dígitos que identifican cada municipio.
#
# IMPORTANTE: Los códigos se mantienen como strings para preservar ceros iniciales
# (ej: "05001" para Medellín, NO 5001)
#
# Nota: 25001 (Yopal - Casanare) está comentado, lo que indica que no se incluye
# en esta versión de la encuesta.

ciudades_geih = [
    "05001",    # Medellín (Antioquia)
    "08001",    # Barranquilla (Atlántico)
    "11001",    # Bogotá D.C.
    "13001",    # Cartagena (Bolívar)
    "15001",    # Tunja (Boyacá)
    "17001",    # Manizales (Caldas)
    "18001",    # Florencia (Caquetá)
    "19001",    # Popayán (Cauca)
    "20001",    # Valledupar (Cesar)
    "23001",    # Montería (Córdoba)
    #"25001",   # Yopal (Casanare) - Comentado: no incluido en GEIH
    "27001",    # Quibdó (Chocó)
    "41001",    # Neiva (Huila)
    "44001",    # Riohacha (La Guajira)
    "47001",    # Santa Marta (Magdalena)
    "50001",    # Villavicencio (Meta)
    "52001",    # Pasto (Nariño)
    "54001",    # Cúcuta (Norte de Santander)
    "63001",    # Armenia (Quindío)
    "66001",    # Pereira (Risaralda)
    "68001",    # Bucaramanga (Santander)
    "70001",    # Sincelejo (Sucre)
    "73001",    # Ibagué (Tolima)
    "76001",    # Cali (Valle del Cauca)
    "81001",    # Arauca (Arauca)
    "85001",    # Yopal (Casanare)
    "86001",    # Mocoa (Putumayo)
    "88001",    # San Andrés (San Andrés y Providencia)
    "91001",    # Leticia (Amazonas)
    "94001",    # Inírida (Guainía)
    "95001",    # San José del Guaviare (Guaviare)
    "97001",    # Mitú (Vaupés)
    "99001"     # Puerto Carreño (Vichada)
]

# COMMAND ----------

# DBTITLE 1,Crear tabla dimensional GEIH
# ============================================================================
# CREACIÓN DE TABLA DIMENSIONAL GEIH-DIVIPOLA
# ============================================================================
# Proceso:
# 1. Cargar tabla completa DIVIPOLA (~1,100 municipios)
# 2. Filtrar solo las 32 ciudades de GEIH
# 3. Agregar campo CODIGO_AREA_GEIH para compatibilidad
# 4. Guardar tabla especializada

# --- PASO 1: CARGAR TABLA DIVIPOLA COMPLETA ---
# Tabla fuente con todos los municipios de Colombia
df_divipola = spark.table("tesis.dim.dim_divipola")

# --- PASO 2: FILTRAR Y TRANSFORMAR ---
df_geih_divipola = (
    df_divipola
    # Filtrar: retener solo las 32 ciudades definidas en la lista ciudades_geih
    # isin() verifica si CODIGO_MUNICIPIO está en la lista
    .filter(col("CODIGO_MUNICIPIO").isin(ciudades_geih))
    
    # Seleccionar y transformar campos:
    .select(
        "CODIGO_DEPARTAMENTO",                                    # Código del departamento (2 dígitos)
        "DEPARTAMENTO",                                            # Nombre del departamento
        col("CODIGO_DEPARTAMENTO").alias("CODIGO_AREA_GEIH"),    # Alias para joins con tablas GEIH
        "CODIGO_MUNICIPIO",                                        # Código del municipio (5 dígitos)
        "MUNICIPIO",                                               # Nombre del municipio
        "LONGITUD",                                                # Coordenada de longitud
        "LATITUD"                                                  # Coordenada de latitud
    )
)

# --- PASO 3: GUARDAR TABLA DIMENSIONAL ESPECIALIZADA ---
# Resultado: Solo 32 registros (ciudades GEIH) vs ~1,100 de la tabla completa
# Esta tabla optimiza joins con datos GEIH
df_geih_divipola.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.dim.dim_geih_divipola"
)