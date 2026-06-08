# Databricks notebook source
# DBTITLE 1,Descripción del Notebook
# MAGIC %md
# MAGIC # Consolidación de Mercado Laboral GEIH - Capa Oro (Gold)
# MAGIC
# MAGIC Este notebook genera la **tabla analítica final** del mercado laboral colombiano, consolidando todas las tablas de la capa plata en una única vista desnormalizada lista para análisis y reportería.
# MAGIC
# MAGIC ## Propósito
# MAGIC Crear la tabla `tesis.geih_oro.mercado_laboral` que integra:
# MAGIC * **Datos demográficos** (características generales)
# MAGIC * **Indicadores laborales** (fuerza de trabajo, ocupación, desocupación)
# MAGIC * **Factores de expansión** para proyecciones estadísticas
# MAGIC * **Geografía** (departamentos y municipios)
# MAGIC
# MAGIC ## Arquitectura de Datos
# MAGIC
# MAGIC ### Modelo de Medallón
# MAGIC **Bronce → Plata → ORO**
# MAGIC
# MAGIC La capa ORO representa el nivel más refinado:
# MAGIC * **Desnormalizada**: Todos los datos en una sola tabla
# MAGIC * **Lista para análisis**: Sin necesidad de joins adicionales
# MAGIC * **Optimizada para consumo**: Dashboards, reportes, ML
# MAGIC
# MAGIC ### Tablas Fuente (Capa Plata)
# MAGIC
# MAGIC 1. **`caracteristicas_generales_consolidado`**: Tabla principal con PK
# MAGIC    - Periodo, identificadores de persona/hogar
# MAGIC    - Datos demográficos: sexo, edad
# MAGIC    - Códigos geográficos
# MAGIC    - Factor de expansión base (FEX)
# MAGIC
# MAGIC 2. **`fuerza_trabajo_consolidado`**:
# MAGIC    - PEA: Población Económicamente Activa
# MAGIC    - PEI: Población Económicamente Inactiva
# MAGIC    - PET: Población en Edad de Trabajar
# MAGIC
# MAGIC 3. **`no_ocupados_consolidado`**:
# MAGIC    - DESOCUPADO: Indicador de desempleo
# MAGIC
# MAGIC 4. **`ocupados_consolidado`**:
# MAGIC    - OCUPADO: Indicador de ocupación/empleo
# MAGIC
# MAGIC 5. **`dim_fex`**:
# MAGIC    - FEX_C18: Factor de expansión ajustado (censo 2018)
# MAGIC
# MAGIC 6. **`dim_geih_divipola`**: Tabla dimensional de geografía
# MAGIC    - Nombres de departamentos y municipios
# MAGIC    - Se une 2 veces: una para departamento, otra para municipio
# MAGIC
# MAGIC ## Estrategia de Joins
# MAGIC
# MAGIC ### Join Principal: LEFT JOIN desde Características Generales
# MAGIC
# MAGIC Usamos **LEFT JOIN** para preservar TODAS las personas de la tabla de características generales, independientemente de si tienen datos en las otras tablas.
# MAGIC
# MAGIC ```
# MAGIC caracteristicas_generales (PRINCIPAL)
# MAGIC   ├─ LEFT JOIN fuerza_trabajo (sobre PK)
# MAGIC   ├─ LEFT JOIN no_ocupados (sobre PK)
# MAGIC   ├─ LEFT JOIN ocupados (sobre PK)
# MAGIC   ├─ LEFT JOIN fex (sobre PK)
# MAGIC   ├─ LEFT JOIN dim_divipola AS div_dep (CODIGO_DPTO → CODIGO_DEPARTAMENTO)
# MAGIC   └─ LEFT JOIN dim_divipola AS div_mun (CODIGO_AREA → CODIGO_AREA_GEIH)
# MAGIC ```
# MAGIC
# MAGIC ### Manejo de Valores NULL
# MAGIC
# MAGIC **Problema**: Los LEFT JOINs generan NULLs cuando no hay match.
# MAGIC
# MAGIC **Solución**: Usar `coalesce()` para reemplazar NULLs con valores por defecto:
# MAGIC * Indicadores numéricos (PEA, PEI, PET, DESOCUPADO, OCUPADO) → **0**
# MAGIC * FEX_C18 → **0**
# MAGIC
# MAGIC Esto asegura:
# MAGIC * Datos limpios sin NULLs
# MAGIC * Cálculos agregados funcionan correctamente
# MAGIC * Semántica clara: 0 = "no aplica" o "no está en esta categoría"
# MAGIC
# MAGIC ## Campos de Salida
# MAGIC
# MAGIC ### Identificación y Periodo
# MAGIC * `PK`: Clave primaria única
# MAGIC * `PERIODO`: YYYYMM (string)
# MAGIC * `PER`: Año (int)
# MAGIC * `MES`: Mes (int)
# MAGIC
# MAGIC ### Geografía
# MAGIC * `CODIGO_DEPARTAMENTO`: Código del departamento
# MAGIC * `DEPARTAMENTO`: Nombre del departamento
# MAGIC * `CODIGO_MUNICIPIO`: Código del municipio
# MAGIC * `MUNICIPIO`: Nombre del municipio
# MAGIC
# MAGIC ### Factores de Expansión
# MAGIC * `FEX`: Factor de expansión base
# MAGIC * `FEX_C18`: Factor de expansión ajustado (censo 2018)
# MAGIC
# MAGIC ### Demografía
# MAGIC * `SEXO`: MASCULINO/FEMENINO
# MAGIC * `EDAD`: Edad en años
# MAGIC
# MAGIC ### Indicadores del Mercado Laboral
# MAGIC * `PEA`: Población Económicamente Activa (0/1)
# MAGIC * `PEI`: Población Económicamente Inactiva (0/1)
# MAGIC * `PET`: Población en Edad de Trabajar (0/1)
# MAGIC * `DESOCUPADO`: Indicador de desempleo (0/1)
# MAGIC * `OCUPADO`: Indicador de ocupación (0/1)
# MAGIC
# MAGIC ## Uso de la Tabla
# MAGIC
# MAGIC Esta tabla final permite análisis como:
# MAGIC * **Tasa de desempleo** por región/periodo
# MAGIC * **Distribución demográfica** del empleo
# MAGIC * **Proyecciones poblacionales** usando factores de expansión
# MAGIC * **Series temporales** del mercado laboral
# MAGIC * **Análisis geográfico** a nivel departamento/municipio
# MAGIC
# MAGIC ## Ejemplo de Cálculo: Tasa de Desempleo
# MAGIC
# MAGIC ```sql
# MAGIC SELECT 
# MAGIC   PERIODO,
# MAGIC   DEPARTAMENTO,
# MAGIC   SUM(DESOCUPADO * FEX_C18) / SUM(PEA * FEX_C18) * 100 AS tasa_desempleo
# MAGIC FROM tesis.geih_oro.mercado_laboral
# MAGIC WHERE PEA = 1  -- Solo poblacion economicamente activa
# MAGIC GROUP BY PERIODO, DEPARTAMENTO
# MAGIC ```

# COMMAND ----------

# DBTITLE 1,Importación de librerías
# Importar funciones de PySpark necesarias para la consolidación
from pyspark.sql.functions import (
    col,        # Referenciar columnas en joins y selects
    coalesce,   # Reemplazar valores NULL con valores por defecto
    lit         # Crear valores literales (ej: lit(0) para reemplazar NULLs)
)

# COMMAND ----------

# DBTITLE 1,Cell 2
# ============================================================================
# CARGA DE TABLAS FUENTE (CAPA PLATA)
# ============================================================================
# Cargar todas las tablas consolidadas de la capa plata

cg = spark.table("tesis.geih_plata.caracteristicas_generales_consolidado")  # Tabla principal (base del join)
ft = spark.table("tesis.geih_plata.fuerza_trabajo_consolidado")            # Indicadores PEA, PEI, PET
no = spark.table("tesis.geih_plata.no_ocupados_consolidado")               # Indicador DESOCUPADO
oc = spark.table("tesis.geih_plata.ocupados_consolidado")                  # Indicador OCUPADO
fex = spark.table("tesis.geih_plata.dim_fex")                              # Factor de expansión ajustado
geih_div = spark.table("tesis.dim.dim_geih_divipola")                      # Dimensión geográfica (divipola)



# ============================================================================
# CONSOLIDACIÓN: JOINS DE TODAS LAS TABLAS
# ============================================================================
# Estrategia: LEFT JOIN desde caracteristicas_generales (cg) como tabla base
# Esto preserva TODAS las personas, incluso si no tienen datos en otras tablas

df = (
    cg
    # Join 1: Indicadores de fuerza de trabajo (PEA, PEI, PET)
    .join(ft, cg.PK == ft.PK, "left")
    
    # Join 2: Indicador de desocupación
    .join(no, cg.PK == no.PK, "left")
    
    # Join 3: Factor de expansión ajustado (FEX_C18)
    .join(fex, cg.PK == fex.PK, "left")
    
    # Join 4: Indicador de ocupación
    .join(oc, cg.PK == oc.PK, "left")
    
    # Join 5: Dimensión geográfica - DEPARTAMENTO
    # Alias "div_dep" para distinguir del siguiente join con la misma tabla
    .join(geih_div.alias("div_dep"), cg.CODIGO_DPTO == col("div_dep.CODIGO_DEPARTAMENTO"), "left")
    
    # Join 6: Dimensión geográfica - MUNICIPIO
    # Alias "div_mun" porque usamos la misma tabla dim_geih_divipola dos veces
    .join(geih_div.alias("div_mun"), cg.CODIGO_AREA == col("div_mun.CODIGO_AREA_GEIH"), "left")
    # ========================================================================
    # SELECCIÓN Y TRANSFORMACIÓN DE CAMPOS FINALES
    # ========================================================================
    # Seleccionar campos relevantes y aplicar coalesce para manejar NULLs
    .select(
        # --- IDENTIFICACIÓN Y PERIODO ---
        cg.PK,                                                     # Clave primaria única
        cg.PERIODO,                                                # YYYYMM (string)
        cg.PER,                                                    # Año (int)
        cg.MES,                                                    # Mes (int)
        
        # --- GEOGRAFÍA ---
        cg.CODIGO_DPTO.alias("CODIGO_DEPARTAMENTO"),              # Código departamento
        "div_dep.DEPARTAMENTO",                                    # Nombre departamento (desde dim)
        col("div_mun.CODIGO_MUNICIPIO"),                          # Código municipio (desde dim)
        "div_mun.MUNICIPIO",                                       # Nombre municipio (desde dim)
        
        # --- FACTORES DE EXPANSIÓN ---
        cg.FEX,                                                    # Factor de expansión base
        coalesce(fex["FEX_C18"], lit(0)).alias("FEX_C18"),        # FEX ajustado (0 si NULL)
        
        # --- DEMOGRAFÍA ---
        cg.SEXO,                                                   # MASCULINO/FEMENINO
        cg.EDAD,                                                   # Edad en años
        
        # --- INDICADORES DEL MERCADO LABORAL ---
        # Usar coalesce para convertir NULLs a 0 (indica "no aplica")
        # Cast a int para asegurar tipo numérico consistente
        coalesce(ft["PEA"].cast("int"), lit(0)).alias("PEA"),              # Población Económicamente Activa
        coalesce(ft["PEI"].cast("int"), lit(0)).alias("PEI"),              # Población Económicamente Inactiva
        coalesce(ft["PET"].cast("int"), lit(0)).alias("PET"),              # Población en Edad de Trabajar
        coalesce(no["DESOCUPADO"].cast("int"), lit(0)).alias("DESOCUPADO"), # Indicador de desempleo
        coalesce(oc["OCUPADO"].cast("int"), lit(0)).alias("OCUPADO")       # Indicador de ocupación
    )
)

# COMMAND ----------

# DBTITLE 1,Guardar tabla oro
# ============================================================================
# PERSISTENCIA EN CAPA ORO
# ============================================================================
# Guardar tabla analítica final consolidada
# - mode("overwrite"): Reemplaza la tabla existente completamente
# - overwriteSchema: Permite cambios en el esquema de la tabla
# - Resultado: Tabla desnormalizada lista para consumo analítico

df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.geih_oro.mercado_laboral"
)