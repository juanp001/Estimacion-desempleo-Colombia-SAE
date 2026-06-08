# Databricks notebook source
# DBTITLE 1,Documentación
# MAGIC %md
# MAGIC # Adición de Covariables para Modelos SAE - Tabla de Estimaciones Enriquecidas
# MAGIC
# MAGIC Este notebook crea la tabla **`tesis.modelo.tasa_desempleo_covariables`** que combina las **estimaciones directas de tasa de desempleo municipal** con **covariables socioeconómicas de TerriData** para modelado de Small Area Estimation (SAE).
# MAGIC
# MAGIC ## Propósito
# MAGIC
# MAGIC Facilitar la **experimentación y desarrollo de modelos SAE** proporcionando una tabla única que integra:
# MAGIC * **Variable dependiente**: Tasa de desempleo municipal (estimación directa)
# MAGIC * **Medidas de precisión**: Error estándar, intervalos de confianza, CV
# MAGIC * **Covariables auxiliares**: ~1,584 indicadores de TerriData (población, educación, salud, infraestructura, etc.)
# MAGIC
# MAGIC ### ¿Por qué necesitamos covariables?
# MAGIC
# MAGIC En **Small Area Estimation**, las estimaciones directas para áreas pequeñas (municipios) suelen tener:
# MAGIC * ❌ **Alta variabilidad** (muestras pequeñas)
# MAGIC * ❌ **Intervalos de confianza amplios**
# MAGIC * ❌ **Coeficientes de variación altos** (>15%)
# MAGIC
# MAGIC Los **modelos SAE** mejoran estas estimaciones usando:
# MAGIC * ✅ **Covariables correlacionadas** con la variable de interés
# MAGIC * ✅ **Información de áreas vecinas** (efectos aleatorios espaciales)
# MAGIC * ✅ **Patrones temporales** (si hay series históricas)
# MAGIC
# MAGIC **Resultado**: Estimaciones más precisas (menor error estándar) y confiables para áreas pequeñas.
# MAGIC
# MAGIC ## Tablas Fuente
# MAGIC
# MAGIC ### 1. `tesis.modelo.tasa_desempleo_municipal`
# MAGIC **Contenido**: Estimaciones directas de tasa de desempleo por municipio
# MAGIC
# MAGIC | Campo | Descripción |
# MAGIC |-------|-------------|
# MAGIC | `PER`, `MES` | Período de estimación |
# MAGIC | `CODIGO_MUNICIPIO`, `MUNICIPIO` | Identificación del municipio |
# MAGIC | `TASA_DESEMPLEO_PCT` | Tasa de desempleo estimada (%) |
# MAGIC | `SE_BOOTSTRAP_PCT` | Error estándar bootstrap (%) |
# MAGIC | `IC_INF_PCT`, `IC_SUP_PCT` | Intervalo de confianza 95% |
# MAGIC | `CV_PORCENTAJE` | Coeficiente de variación (%) |
# MAGIC
# MAGIC **Características**:
# MAGIC * Calculadas con métodos bootstrap
# MAGIC * Solo municipios con muestra suficiente
# MAGIC * Incluyen medidas de precisión (SE, CV, IC)
# MAGIC
# MAGIC ### 2. `tesis.terridata.terridata_extendido_plata`
# MAGIC **Contenido**: Indicadores socioeconómicos municipales (TerriData - DNP)
# MAGIC
# MAGIC **Dimensiones cubiertas**:
# MAGIC * 📊 Demografía (población por edad, sexo, densidad)
# MAGIC * 🎓 Educación (matrícula, deserción, cobertura)
# MAGIC * 🏥 Salud (afiliación, mortalidad, natalidad)
# MAGIC * 🏠 Vivienda (servicios públicos, déficit habitacional)
# MAGIC * 💼 Economía (PIB, empresas, empleo formal)
# MAGIC * 🚧 Infraestructura (vías, conectividad)
# MAGIC * 🌳 Medio ambiente (cobertura forestal, calidad del agua)
# MAGIC
# MAGIC **Estructura**:
# MAGIC * Formato ANCHO (pivoteado)
# MAGIC * ~1,584 columnas de indicadores
# MAGIC * Cada columna = un `CODIGO_INDICADOR`
# MAGIC * Metadata en `tesis.dim.dim_indicadores`
# MAGIC
# MAGIC ## Proceso de Integración
# MAGIC
# MAGIC ### Estrategia de Join: LEFT JOIN
# MAGIC
# MAGIC ```
# MAGIC Estimaciones Directas (23 municipios)
# MAGIC          ⬇ LEFT JOIN
# MAGIC Covariables TerriData
# MAGIC          ⬇
# MAGIC Tabla Final (23 filas × ~1,590 columnas)
# MAGIC ```
# MAGIC
# MAGIC **¿Por qué LEFT JOIN?**
# MAGIC * **Preserva todas las estimaciones**: Incluso si un municipio no tiene covariables en TerriData
# MAGIC * **Flexibilidad**: Permite trabajar con estimaciones que tienen datos parciales
# MAGIC * **Transparencia**: Valores NULL indican falta de covariables
# MAGIC
# MAGIC ### Condiciones de Join:
# MAGIC
# MAGIC ```python
# MAGIC df_estimaciones.CODIGO_MUNICIPIO == df_terridata.CODIGO_ENTIDAD
# MAGIC AND df_estimaciones.PER == df_terridata.ANO
# MAGIC AND df_estimaciones.MES == df_terridata.MES
# MAGIC ```
# MAGIC
# MAGIC **Matching por**:
# MAGIC 1. Código de municipio
# MAGIC 2. Año
# MAGIC 3. Mes
# MAGIC
# MAGIC ### Manejo de Columnas Duplicadas:
# MAGIC
# MAGIC Se **excluyen** de TerriData las columnas que ya existen en Estimaciones:
# MAGIC * `CODIGO_DEPARTAMENTO`, `DEPARTAMENTO` (ya vienen de estimaciones)
# MAGIC * `CODIGO_ENTIDAD` (duplica `CODIGO_MUNICIPIO`)
# MAGIC * `ENTIDAD` (duplica `MUNICIPIO`)
# MAGIC * `ANO`, `MES` (ya vienen como `PER`, `MES`)
# MAGIC
# MAGIC Solo se agregan las **columnas de indicadores** (códigos como `010010009`, `020030015`, etc.)
# MAGIC
# MAGIC ## Estructura de la Tabla de Salida
# MAGIC
# MAGIC ### `tesis.modelo.tasa_desempleo_covariables`
# MAGIC
# MAGIC **Total de columnas**: ~1,590 columnas
# MAGIC
# MAGIC #### 1. Columnas de Identificación (6 columnas)
# MAGIC
# MAGIC | Campo | Tipo | Descripción |
# MAGIC |-------|------|-------------|
# MAGIC | `PER` | int | Año |
# MAGIC | `MES` | int | Mes |
# MAGIC | `CODIGO_DEPARTAMENTO` | string | Código DIVIPOLA del departamento |
# MAGIC | `DEPARTAMENTO` | string | Nombre del departamento |
# MAGIC | `CODIGO_MUNICIPIO` | string | Código DIVIPOLA del municipio (5 dígitos) |
# MAGIC | `MUNICIPIO` | string | Nombre del municipio |
# MAGIC
# MAGIC #### 2. Columnas de Estimación Directa (6 columnas)
# MAGIC
# MAGIC | Campo | Tipo | Descripción | Rango |
# MAGIC |-------|------|-------------|-------|
# MAGIC | `TASA_DESEMPLEO_PCT` | double | Tasa de desempleo estimada | 0-100% |
# MAGIC | `SE_BOOTSTRAP_PCT` | double | Error estándar bootstrap | >0 |
# MAGIC | `IC_INF_PCT` | double | Límite inferior IC 95% | >=0 |
# MAGIC | `IC_SUP_PCT` | double | Límite superior IC 95% | <=100 |
# MAGIC | `AMPLITUD_IC` | double | Amplitud del IC (IC_SUP - IC_INF) | >0 |
# MAGIC | `CV_PORCENTAJE` | double | Coeficiente de variación (SE/Tasa × 100) | >0 |
# MAGIC
# MAGIC **Interpretación del CV**:
# MAGIC * CV < 15%: Estimación **confiable**
# MAGIC * 15% ≤ CV < 30%: Estimación **aceptable**
# MAGIC * CV ≥ 30%: Estimación **no confiable** (usar con precaución)
# MAGIC
# MAGIC #### 3. Covariables de TerriData (~1,578 columnas)
# MAGIC
# MAGIC Cada columna es un `CODIGO_INDICADOR` de TerriData:
# MAGIC
# MAGIC **Indicadores demográficos (ejemplo)**:
# MAGIC * `010010009`: Población total
# MAGIC * `010010010`: Población hombres
# MAGIC * `010010011`: Población mujeres
# MAGIC
# MAGIC **Indicadores de educación (ejemplo)**:
# MAGIC * `020030015`: Tasa de matrícula
# MAGIC * `020030020`: Tasa de deserción escolar
# MAGIC
# MAGIC **Indicadores de salud (ejemplo)**:
# MAGIC * `030040025`: Afiliación al sistema de salud
# MAGIC * `030040030`: Tasa de mortalidad infantil
# MAGIC
# MAGIC **Consultar metadata**:
# MAGIC ```sql
# MAGIC SELECT CODIGO_INDICADOR, INDICADOR, DIMENSION, UNIDAD_MEDIDA
# MAGIC FROM tesis.dim.dim_indicadores
# MAGIC WHERE DIMENSION = 'Demografía'
# MAGIC ORDER BY CODIGO_INDICADOR
# MAGIC ```
# MAGIC
# MAGIC ## Casos de Uso
# MAGIC
# MAGIC ### 1. Selección de Covariables para Modelo Fay-Herriot
# MAGIC
# MAGIC ```sql
# MAGIC -- Filtrar estimaciones confiables y explorar correlaciones
# MAGIC SELECT 
# MAGIC   MUNICIPIO,
# MAGIC   TASA_DESEMPLEO_PCT,
# MAGIC   CV_PORCENTAJE,
# MAGIC   `010010009` as poblacion_total,
# MAGIC   `020030015` as tasa_matricula,
# MAGIC   `030040025` as afiliacion_salud
# MAGIC FROM tesis.modelo.tasa_desempleo_covariables
# MAGIC WHERE CV_PORCENTAJE < 30  -- Solo estimaciones aceptables
# MAGIC ORDER BY TASA_DESEMPLEO_PCT DESC
# MAGIC ```
# MAGIC
# MAGIC ### 2. Preparación de Features para Modelo ML
# MAGIC
# MAGIC ```python
# MAGIC # Cargar tabla
# MAGIC df = spark.table("tesis.modelo.tasa_desempleo_covariables")
# MAGIC
# MAGIC # Seleccionar solo indicadores numéricos (usando metadata)
# MAGIC df_indicadores = spark.table("tesis.dim.dim_indicadores")
# MAGIC indicadores_num = df_indicadores.filter(
# MAGIC     col("TIPO_DATO") == "numerico"
# MAGIC ).select("CODIGO_INDICADOR").collect()
# MAGIC
# MAGIC features = [row.CODIGO_INDICADOR for row in indicadores_num]
# MAGIC
# MAGIC # Preparar dataset para ML
# MAGIC df_ml = df.select(
# MAGIC     ["MUNICIPIO", "TASA_DESEMPLEO_PCT", "CV_PORCENTAJE"] + features
# MAGIC )
# MAGIC ```
# MAGIC
# MAGIC ### 3. Análisis de Correlación con Variable Dependiente
# MAGIC
# MAGIC ```python
# MAGIC from pyspark.sql.functions import corr
# MAGIC
# MAGIC # Calcular correlación de cada covariable con tasa de desempleo
# MAGIC for indicador in features:
# MAGIC     correlacion = df.select(
# MAGIC         corr("TASA_DESEMPLEO_PCT", indicador)
# MAGIC     ).collect()[0][0]
# MAGIC     
# MAGIC     if correlacion and abs(correlacion) > 0.5:  # Correlación fuerte
# MAGIC         print(f"{indicador}: {correlacion:.3f}")
# MAGIC ```
# MAGIC
# MAGIC ### 4. Filtrado por Calidad de Estimación
# MAGIC
# MAGIC ```sql
# MAGIC -- Solo municipios con estimaciones confiables (CV < 15%)
# MAGIC CREATE OR REPLACE TABLE tesis.modelo.td_covariables_confiables AS
# MAGIC SELECT *
# MAGIC FROM tesis.modelo.tasa_desempleo_covariables
# MAGIC WHERE CV_PORCENTAJE < 15
# MAGIC ```
# MAGIC
# MAGIC ## Modelos SAE Aplicables
# MAGIC
# MAGIC Con esta tabla, se pueden implementar:
# MAGIC
# MAGIC ### 1. **Modelo Fay-Herriot (Area-Level)**
# MAGIC * Usa estimaciones directas + covariables a nivel de área
# MAGIC * Ideal cuando solo hay datos agregados por municipio
# MAGIC * Asume normalidad de errores de muestreo
# MAGIC
# MAGIC ### 2. **EBLUP (Empirical Best Linear Unbiased Predictor)**
# MAGIC * Predictor lineal empírico
# MAGIC * Combina estimación directa con modelo de regresión
# MAGIC * Pondera según precisión de estimación directa
# MAGIC
# MAGIC ### 3. **Modelos espaciales (SAR, CAR)**
# MAGIC * Incorpora dependencia espacial entre municipios vecinos
# MAGIC * Útil cuando hay clusters geográficos de desempleo
# MAGIC * Requiere matriz de vecindad (disponible con DIVIPOLA)
# MAGIC
# MAGIC ### 4. **Modelos jerárquicos bayesianos**
# MAGIC * Permite incorporar incertidumbre en parámetros
# MAGIC * Flexible para estructuras complejas
# MAGIC * Implementable en Stan, PyMC, o INLA
# MAGIC
# MAGIC ## Datos Actuales
# MAGIC
# MAGIC **Período cubierto**: Diciembre 2018
# MAGIC
# MAGIC **Municipios incluidos**: 23 ciudades principales con estimaciones GEIH
# MAGIC * Bogotá D.C., Medellín, Cali, Barranquilla, Cartagena
# MAGIC * Cúcuta, Bucaramanga, Pereira, Ibagué, Santa Marta
# MAGIC * Y 13 ciudades adicionales
# MAGIC
# MAGIC **Total de registros**: 23 filas (una por municipio)
# MAGIC
# MAGIC **Total de variables**: ~1,590 columnas
# MAGIC
# MAGIC ## Limitaciones y Consideraciones
# MAGIC
# MAGIC ### 1. **Datos faltantes en covariables**
# MAGIC * No todos los municipios tienen todos los indicadores de TerriData
# MAGIC * Valores NULL indican falta de información
# MAGIC
# MAGIC ### 2. **Período único**
# MAGIC * Actualmente solo diciembre 2018
# MAGIC * Para modelos temporales, se necesitarían múltiples períodos
# MAGIC * **Solución futura**: Agregar más meses/años de estimaciones y covariables
# MAGIC
# MAGIC ### 3. **Multicolinealidad**
# MAGIC * ~1,584 covariables → alta probabilidad de correlación entre variables
# MAGIC * **Solución**: 
# MAGIC   * Selección de covariables con criterios estadísticos (VIF, LASSO)
# MAGIC   * Análisis de componentes principales (PCA)
# MAGIC   * Regularización (Ridge, Elastic Net)
# MAGIC
# MAGIC ### 4. **Escalas diferentes**
# MAGIC * Covariables en diferentes unidades (%, personas, pesos, km²)
# MAGIC * **Solución**: Estandarización (z-score) antes del modelado
# MAGIC
# MAGIC ### 5. **Tamaño de muestra pequeño**
# MAGIC * Solo 23 observaciones
# MAGIC * **Desafío**: Riesgo de overfitting con muchas covariables
# MAGIC * **Solución**: 
# MAGIC   * Selección parsimoniosa de covariables (≤5-7 variables)
# MAGIC   * Validación cruzada leave-one-out
# MAGIC   * Penalización (regularización)
# MAGIC
# MAGIC ## Próximos Pasos
# MAGIC
# MAGIC 1. **Exploración de datos**:
# MAGIC    * Análisis de correlaciones bivariadas
# MAGIC    * Identificación de covariables con baja cobertura
# MAGIC    * Detección de outliers
# MAGIC
# MAGIC 2. **Selección de covariables**:
# MAGIC    * Criterios estadísticos (AIC, BIC)
# MAGIC    * Conocimiento del dominio (teoría económica)
# MAGIC    * Pruebas de multicolinealidad
# MAGIC
# MAGIC 3. **Modelado SAE**:
# MAGIC    * Implementar modelo Fay-Herriot base
# MAGIC    * Comparar con EBLUP
# MAGIC    * Evaluar mejora vs estimación directa (MSE, coverage)
# MAGIC
# MAGIC 4. **Validación**:
# MAGIC    * Cross-validation leave-one-out
# MAGIC    * Comparación de intervalos de predicción
# MAGIC    * Análisis de residuos
# MAGIC
# MAGIC ## Referencias
# MAGIC
# MAGIC * Rao, J.N.K. & Molina, I. (2015). *Small Area Estimation* (2nd ed.). Wiley.
# MAGIC * Fay, R.E. & Herriot, R.A. (1979). Estimates of income for small places: An application of James-Stein procedures to census data. *JASA*.
# MAGIC * TerriData - DNP: https://terridata.dnp.gov.co/

# COMMAND ----------

# DBTITLE 1,Crear tabla td_covariables
# ============================================================================
# INTEGRACIÓN DE ESTIMACIONES DIRECTAS CON COVARIABLES TERRIDATA
# ============================================================================
# Este notebook crea una tabla única que combina:
# - Estimaciones directas de tasa de desempleo municipal (variable dependiente)
# - Covariables socioeconómicas de TerriData (~1,584 variables auxiliares)
#
# Propósito: Preparar datos para modelos de Small Area Estimation (SAE)
# ============================================================================

from pyspark.sql import functions as F

# ============================================================================
# PASO 1: CARGAR TABLA DE ESTIMACIONES DIRECTAS
# ============================================================================
# Tabla fuente: tesis.modelo.tasa_desempleo_municipal
# Contiene: 23 municipios con estimaciones de desempleo para diciembre 2018
# Incluye: Tasa, error estándar, intervalos de confianza, CV

print("Leyendo estimaciones directas...")
df_estimaciones = spark.table("tesis.modelo.tasa_desempleo_municipal")
print(f"  Estimaciones: {df_estimaciones.count()} filas")
print(f"  Columnas: {len(df_estimaciones.columns)}")


# ============================================================================
# PASO 2: CARGAR TABLA DE COVARIABLES TERRIDATA
# ============================================================================
# Tabla fuente: tesis.terridata.terridata_extendido_plata
# Formato: ANCHO (pivoteado) - una columna por cada indicador
# Contiene: ~1,584 indicadores socioeconómicos del DNP
# Dimensiones: Demografía, educación, salud, infraestructura, economía, etc.

print("\nLeyendo covariables TerriData...")
df_terridata = spark.table("tesis.terridata.terridata_extendido_plata")
print(f"  TerriData: {df_terridata.count()} filas")
print(f"  Columnas: {len(df_terridata.columns)}")


# ============================================================================
# PASO 3: PREPARAR COLUMNAS DE TERRIDATA (EVITAR DUPLICADOS)
# ============================================================================
# Problema: TerriData tiene columnas que ya existen en df_estimaciones
# Solución: Excluir columnas de identificación/temporalidad de TerriData
#           y solo conservar las columnas de indicadores

# --- Identificar columnas a excluir de TerriData ---
columnas_excluir = [
    "CODIGO_DEPARTAMENTO", "DEPARTAMENTO",  # Ya vienen de estimaciones
    "CODIGO_ENTIDAD", "ENTIDAD",            # Duplican CODIGO_MUNICIPIO, MUNICIPIO
    "ANO", "MES"                             # Ya vienen como PER, MES en estimaciones
]

print(f"\nColumnas a excluir de TerriData: {len(columnas_excluir)}")
for col in columnas_excluir:
    print(f"  - {col}")

# --- Seleccionar solo columnas de indicadores (covariables) ---
# Todas las columnas EXCEPTO las de identificación
columnas_terridata = [col for col in df_terridata.columns if col not in columnas_excluir]

# Crear DataFrame con columnas de join + covariables
# Necesitamos CODIGO_ENTIDAD, ANO, MES para el join, pero las eliminaremos después
df_terridata_seleccionado = df_terridata.select(
    "CODIGO_ENTIDAD", "ANO", "MES",  # Columnas de join (se eliminarán después)
    *columnas_terridata                # ~1,584 columnas de indicadores (COVARIABLES)
)

print(f"\nCovariables seleccionadas de TerriData: {len(columnas_terridata)} columnas")
print(f"  (Estas son las columnas con códigos de indicadores como 010010009, etc.)")


# ============================================================================
# PASO 4: JOIN ENTRE ESTIMACIONES Y COVARIABLES
# ============================================================================
# Estrategia: LEFT JOIN para preservar TODAS las estimaciones
# Esto asegura que municipios sin covariables en TerriData se mantengan
# (con valores NULL en las columnas de covariables)

print("\n" + "="*60)
print("Realizando LEFT JOIN entre estimaciones y covariables...")
print("="*60)

# --- Ejecutar LEFT JOIN ---
df_final = (
    df_estimaciones
    .join(
        df_terridata_seleccionado,
        # Condiciones de join: Coincidir por municipio + periodo
        (
            (df_estimaciones.CODIGO_MUNICIPIO == df_terridata_seleccionado.CODIGO_ENTIDAD) &
            (df_estimaciones.PER == df_terridata_seleccionado.ANO) &
            (df_estimaciones.MES == df_terridata_seleccionado.MES)
        ),
        how="left"  # LEFT JOIN: preservar todas las estimaciones
    )
    # Eliminar columnas de join de TerriData (ya no las necesitamos)
    .drop("CODIGO_ENTIDAD", "ANO", df_terridata_seleccionado.MES)
)

print(f"\n✅ JOIN completado exitosamente")
print(f"  - Filas en resultado: {df_final.count()}")
print(f"  - Columnas totales: {len(df_final.columns)}")
print(f"    • Columnas de identificación: 6")
print(f"    • Columnas de estimación: 6")
print(f"    • Columnas de covariables: {len(df_final.columns) - 12}")


# ============================================================================
# PASO 5: PERSISTIR TABLA FINAL EN UNITY CATALOG
# ============================================================================
# Tabla destino: tesis.modelo.tasa_desempleo_covariables
# Esquema: tesis.modelo (para tablas del proyecto de modelado SAE)
# Modo: overwrite (reemplaza tabla existente)

print("\n" + "="*60)
print("Guardando tabla en Unity Catalog...")
print("="*60)

df_final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "tesis.modelo.tasa_desempleo_covariables"
)

print("\n" + "="*60)
print("✅ TABLA CREADA EXITOSAMENTE")
print("="*60)

print(f"\nTabla: tesis.modelo.tasa_desempleo_covariables")
print(f"\nESTRUCTURA:")
print(f"  - Total de filas: {df_final.count()}")
print(f"  - Total de columnas: {len(df_final.columns)}")
print(f"\nCOLUMNAS:")
print(f"  1. Identificación (6):")
print(f"     PER, MES, CODIGO_DEPARTAMENTO, DEPARTAMENTO,")
print(f"     CODIGO_MUNICIPIO, MUNICIPIO")
print(f"\n  2. Estimación Directa (6):")
print(f"     TASA_DESEMPLEO_PCT, SE_BOOTSTRAP_PCT,")
print(f"     IC_INF_PCT, IC_SUP_PCT, AMPLITUD_IC, CV_PORCENTAJE")
print(f"\n  3. Covariables TerriData ({len(df_final.columns) - 12}):")
print(f"     Indicadores socioeconómicos del DNP")
print(f"     (Demografía, educación, salud, etc.)")

print(f"\nLINEAGE:")
print(f"  Unity Catalog preserva automáticamente el lineage desde:")
print(f"    → tesis.modelo.tasa_desempleo_municipal")
print(f"    → tesis.terridata.terridata_extendido_plata")

print(f"\nUSO:")
print(f"  SELECT * FROM tesis.modelo.tasa_desempleo_covariables")
print(f"  WHERE CV_PORCENTAJE < 15  -- Filtrar estimaciones confiables")

print(f"\nPRÓXIMOS PASOS:")
print(f"  1. Exploración de correlaciones entre covariables y desempleo")
print(f"  2. Selección de covariables relevantes (evitar multicolinealidad)")
print(f"  3. Implementación de modelos SAE (Fay-Herriot, EBLUP)")
print(f"  4. Validación y comparación vs estimación directa")

print("\n" + "="*60 + "\n")