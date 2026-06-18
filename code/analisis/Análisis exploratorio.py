# Databricks notebook source
# MAGIC %md
# MAGIC
# MAGIC # Análisis exploratorio y selección de covariables
# MAGIC
# MAGIC Este notebook es la **segunda etapa** del proceso de selección de covariables para el modelo SAE de desempleo.
# MAGIC El pipeline completo sigue la siguiente secuencia:
# MAGIC
# MAGIC ```
# MAGIC TerriData (~1.582 vars)
# MAGIC        │
# MAGIC        ▼  pre_filtrado_covariables.py
# MAGIC        │  • Filtro 1: sin NAs en los 23 dominios
# MAGIC        │  • Filtro 2: varianza casi cero
# MAGIC        │  • Filtro 3: |Pearson| ≥ 0.40 con TASA_DESEMPLEO_PCT
# MAGIC        │
# MAGIC        ▼  ~84 variables  →  covariables_prefiltradas
# MAGIC        │
# MAGIC        ▼  [ESTE NOTEBOOK]
# MAGIC        │  • Etapa 1: sensibilidad al umbral de correlación
# MAGIC        │  • Etapa 2: filtro cualitativo (literatura) → 16 candidatas
# MAGIC        │  • Etapa 3: análisis descriptivo + normalidad (Shapiro-Wilk)
# MAGIC        │  • Etapa 4: relación con Y (scatter + Pearson/Spearman + IC bootstrap)
# MAGIC        │  • Etapa 5: influencia de outliers (Cook's D + leave-one-out)
# MAGIC        │  • Etapa 6: estructura espacial (Moran's I)
# MAGIC        │  • Etapa 7: ranking compuesto (Q empírico + L literatura) + sensibilidad a α → 4 covariables
# MAGIC        │
# MAGIC        ▼  covariables_seleccionadas
# MAGIC        │
# MAGIC        ▼  fay_herriot.py  →  EBLUP + diagnósticos + comparación de modelos
# MAGIC ```
# MAGIC
# MAGIC > **Limitación estadística clave — n=23:** El análisis trabaja con los 23 dominios de estimación
# MAGIC > (ciudades principales encuestadas por la GEIH). Con este tamaño muestral los intervalos de confianza
# MAGIC > de las correlaciones son amplios (típicamente ±0.20–0.40 según la magnitud de r). Por esta razón
# MAGIC > todos los coeficientes de correlación en este notebook se acompañan de su IC bootstrap al 95 %
# MAGIC > y se reporta también Spearman ρ (más robusto ante valores atípicos) para validar la dirección
# MAGIC > y magnitud de la asociación.
# MAGIC
# MAGIC > **Sesgo de selección sobre la respuesta (double dipping):** el pre-filtro de la etapa previa
# MAGIC > seleccionó variables por su correlación con `TASA_DESEMPLEO_PCT` usando **los mismos 23 dominios**
# MAGIC > que alimentarán el modelo. Esto sesga al alza las correlaciones de las variables sobrevivientes
# MAGIC > (*winner's curse*) e invalida la interpretación nominal de los p-valores tras la multiplicidad de
# MAGIC > pruebas. Por ello, en este notebook las correlaciones **no se usan como evidencia confirmatoria
# MAGIC > ni como tamaños de efecto insesgados**, sino como insumo de *triaje y de chequeo de robustez*:
# MAGIC > el objetivo es discriminar, entre variables ya pre-seleccionadas, cuáles mantienen una asociación
# MAGIC > estable y no dependiente de outliers. La validación confirmatoria del modelo se hace en
# MAGIC > `fay_herriot.py` (AIC/BIC, diagnósticos, validación cruzada).

# COMMAND ----------

# DBTITLE 1,Setup: imports y carga de datos
import sys
import os
import re
import unicodedata

sys.path.insert(0, os.path.dirname(os.getcwd()))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import pearsonr, spearmanr, shapiro
from scipy.spatial.distance import cdist
from statsmodels.stats.outliers_influence import variance_inflation_factor, OLSInfluence
from statsmodels.tools import add_constant
from statsmodels.regression.linear_model import OLS
from pyspark.sql import functions as F
from preprocesamiento.shared.config import METADATA_COLS

# ── Cargar tablas ─────────────────────────────────────────────────────────────
df_full       = spark.table("tesis.preprocesamiento.covariables_prefiltradas")
df_indicadores = spark.table("tesis.dim.dim_indicadores")
indicadores_dict = {
    row["CODIGO_INDICADOR"]: row["INDICADOR"]
    for row in df_indicadores.select("CODIGO_INDICADOR", "INDICADOR").collect()
}

# ── Separar covariables de metadatos ──────────────────────────────────────────
cols_covariables = [c for c in df_full.columns if c not in METADATA_COLS]
df_cov = df_full.select(cols_covariables)
for col_name in [f.name for f in df_cov.schema.fields if str(f.dataType) == "StringType()"]:
    df_cov = df_cov.withColumn(col_name, F.col(col_name).cast("double"))

# ── Versiones Pandas (n=23 → seguro en driver) ────────────────────────────────
df_meta   = df_full.select(METADATA_COLS).toPandas()
df_pd     = df_cov.toPandas()
Y         = df_meta["TASA_DESEMPLEO_PCT"].values
entidades = df_meta["MUNICIPIO"].values

# ── Normalización de nombres de municipio para comparaciones robustas ─────────
# MUNICIPIO puede traer tildes, comas o sufijos ("Bogotá, D.C.") que no coinciden
# con cadenas escritas a mano (p. ej. en DEPT_LOO). normalizar_municipio() reduce
# ambos lados a MAYÚSCULAS sin tildes ni puntuación antes de comparar, evitando
# falsos negativos como el que afectaba al filtro LOO de Bogotá.
def normalizar_municipio(nombre):
    sin_tildes = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]", "", sin_tildes.upper())

entidades_norm = np.array([normalizar_municipio(e) for e in entidades])

print(f"Dominios de estimación (n): {len(Y)}")
print(f"Covariables pre-filtradas:  {len(df_pd.columns)}")
print(f"Indicadores en dim:         {len(indicadores_dict)}")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Etapa 1 — Pre-filtrado cuantitativo y sensibilidad al umbral de correlación
# MAGIC
# MAGIC La tabla `covariables_prefiltradas` ya tiene aplicados tres filtros automáticos:
# MAGIC
# MAGIC | Filtro | Criterio | Resultado aproximado |
# MAGIC |--------|----------|----------------------|
# MAGIC | Sin NAs | Columnas con al menos 1 NA eliminadas | ~1.582 → ~530 |
# MAGIC | Varianza casi cero | var < 0.00001 eliminadas | ~530 → ~220 |
# MAGIC | Correlación umbral | \|Pearson\| ≥ 0.40 con `TASA_DESEMPLEO_PCT` | ~220 → ~84 |
# MAGIC
# MAGIC El umbral de correlación de 0.40 fue elegido para equilibrar exhaustividad (no perder
# MAGIC variables relevantes) y manejabilidad (no trasladar cientos de variables al EDA).
# MAGIC
# MAGIC > **Advertencia de circularidad:** como la tabla `covariables_prefiltradas` **ya** aplicó el corte
# MAGIC > |Pearson| ≥ 0.40, contar cuántas variables superan umbrales **inferiores** (0.30, 0.35) es
# MAGIC > tautológico: todas pasan por construcción. El análisis de sensibilidad *genuino* —cuántas variables
# MAGIC > entran o salen al mover el umbral sobre el universo completo (~220 vars)— corresponde al script
# MAGIC > `pre_filtrado_covariables.py`, no a este notebook.
# MAGIC
# MAGIC Lo que sí es informativo aquí es la **distribución de |Pearson| entre las variables ya sobrevivientes**:
# MAGIC permite ver si la señal está concentrada (muchas justo en 0.40, pocas fuertes) o repartida, y cuántas
# MAGIC superarían cortes más exigentes (0.45–0.60). Recordar que, por el sesgo de selección sobre la respuesta,
# MAGIC estas magnitudes están infladas y se interpretan solo como ordenamiento relativo.

# COMMAND ----------

# DBTITLE 1,Distribución de |Pearson| entre las covariables ya pre-filtradas
# |Pearson| con Y de cada covariable sobreviviente (todas con |r| ≥ 0.40 por construcción)
abs_r = {
    c: abs(np.corrcoef(df_pd[c].values, Y)[0, 1])
    for c in df_pd.columns if df_pd[c].notna().all()
}
abs_r = pd.Series(abs_r).sort_values(ascending=False)

# Cuántas superan cortes MÁS exigentes (informativo) — los inferiores serían tautológicos
umbrales = [0.40, 0.45, 0.50, 0.55, 0.60]
df_umbral = pd.DataFrame([
    {"Umbral_|Pearson|": u, "Variables_que_superan": int((abs_r >= u).sum())}
    for u in umbrales
])
display(spark.createDataFrame(df_umbral))

fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(abs_r.values, bins=15, color="steelblue", edgecolor="white")
ax.axvline(0.40, color="red", linestyle="--", linewidth=1.5, label="Corte del pre-filtro: |r| ≥ 0.40")
ax.set_xlabel("|Pearson| con TASA_DESEMPLEO_PCT", fontsize=11)
ax.set_ylabel("N.º de covariables", fontsize=11)
ax.set_title("Distribución de |Pearson| entre las covariables pre-filtradas\n"
             "(magnitudes infladas por selección sobre la respuesta — solo ordenamiento relativo)",
             fontsize=11, fontweight="bold")
ax.legend(fontsize=10)
ax.grid(True, linestyle=":", alpha=0.5)
plt.tight_layout()
display(fig)
plt.close(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC La distribución está concentrada cerca del corte: 13 de las ~84 covariables tienen |Pearson|
# MAGIC apenas entre 0.40 y 0.42, y la frecuencia decrece de forma bastante uniforme hacia la derecha
# MAGIC (8, 7, 5, 7, 8, 10, 6, 5, 5, 4 variables en los bins sucesivos hasta 0.55). Solo 6 variables superan
# MAGIC |r| ≥ 0.55 y apenas 1 supera 0.60. Es decir, la señal **no** está concentrada en unas pocas variables
# MAGIC muy fuertes: la mayoría de las 84 sobrevivientes están cerca del umbral mínimo, lo que es consistente
# MAGIC con el riesgo de *winner's curse* señalado arriba — muchas de ellas probablemente pasaron el filtro
# MAGIC por azar muestral con n=23. Esto refuerza la necesidad de las etapas posteriores (literatura, IC
# MAGIC bootstrap, LOO) para depurar el conjunto antes de construir el modelo.
# MAGIC
# MAGIC # Etapa 2 — Filtro cualitativo: de ~84 a 16 variables con respaldo en literatura
# MAGIC
# MAGIC Una correlación estadística entre una covariable y la tasa de desempleo **no implica causalidad**.
# MAGIC Variables espurias o colineales con determinantes reales pueden superar el umbral cuantitativo
# MAGIC sin aportar valor explicativo genuino al modelo.
# MAGIC
# MAGIC En esta etapa se aplica un **filtro de segunda pasada** basado en dos criterios:
# MAGIC
# MAGIC 1. **Respaldo en literatura:** la variable aparece como determinante del desempleo en estudios
# MAGIC    sobre mercados laborales en economías en desarrollo y Colombia en particular
# MAGIC    (Galvis & Meisel 2010; Arango & Flórez 2012; Lasso 2014; DANE/CEPAL 2016).
# MAGIC
# MAGIC 2. **Significado de negocio:** la variable mide una dimensión conceptualmente clara del
# MAGIC    desarrollo territorial que puede vincular causalmente con la dinámica del mercado laboral.
# MAGIC
# MAGIC Las variables seleccionadas se agrupan en siete dimensiones conceptuales:
# MAGIC
# MAGIC | Dimensión | Hipótesis de causalidad |
# MAGIC |-----------|-------------------------|
# MAGIC | **Infraestructura básica** | El acceso a servicios esenciales (energía) reduce los costos de producción y favorece la actividad económica formal |
# MAGIC | **Capital humano** | Mayor educación incrementa la empleabilidad y reduce el desempleo friccional y estructural |
# MAGIC | **Condiciones socioeconómicas** | La pobreza multidimensional concentra privaciones que limitan la participación en el mercado laboral |
# MAGIC | **Desempeño económico** | La productividad municipal determina la demanda agregada de trabajo |
# MAGIC | **Seguridad y conflicto** | La inseguridad y el conflicto armado destruyen capital físico, generan desplazamiento y perturban los mercados laborales |
# MAGIC | **Capacidad institucional** | La gestión y la inversión pública generan empleo directo e indirecto mediante la provisión de bienes públicos |
# MAGIC | **Medio ambiente y territorio** | La cobertura de ecosistemas estratégicos se asocia con economías más extractivas y patrones diferenciados de empleo rural |

# COMMAND ----------

# DBTITLE 1,Definición del catálogo de literatura y resolución de códigos
# Cada variable se define con su código (si se conoce) o una expresión de búsqueda
# que se resuelve automáticamente contra dim_indicadores.
CATALOGO_LITERATURA = [
    # ── INFRAESTRUCTURA BÁSICA ────────────────────────────────────────────────
    {"codigo": "030010002", "busqueda": None,
     "dimension": "Infraestructura básica",
     "nivel_literatura": 2, "alias": "COB_ENER_RURAL",
     "justificacion": (
         "El acceso a energía eléctrica rural es condición necesaria para la actividad "
         "económica en zonas periféricas. Municipios con baja electrificación concentran "
         "mayor informalidad, menor productividad agrícola y desempleo estructural. La "
         "relación causal está documentada en Galvis & Meisel (2010) para ciudades intermedias "
         "colombianas.")},

    # ── CAPITAL HUMANO ────────────────────────────────────────────────────────
    {"codigo": "040010028", "busqueda": None,
     "dimension": "Capital humano",
     "nivel_literatura": 2, "alias": "TASA_TRAN_EDU_SUP",
     "justificacion": (
         "La tasa de tránsito inmediata a la educación superior mide la proporción de "
         "bachilleres que continúan en el nivel terciario, predictor clave del capital humano "
         "futuro del territorio. Arango & Flórez (2012) documentan que mayor formación reduce "
         "el desempleo friccional al acortar el período de búsqueda de empleo.")},

    {"codigo": None, "busqueda": r"cobertura neta.*secundaria",
     "dimension": "Capital humano",
     "nivel_literatura": 2, "alias": "COB_NET_SEC",
     "justificacion": (
         "La cobertura neta en educación secundaria es la base del sistema educativo local. "
         "Una baja cobertura limita la formación del capital humano mínimo requerido para "
         "acceder al mercado laboral formal, perpetuando el ciclo de informalidad.")},

    {"codigo": None, "busqueda": r"ciencia",
     "dimension": "Capital humano",
     "nivel_literatura": 1, "alias": "IND_CIENCIA",
     "justificacion": (
         "El índice de ciencia e innovación captura la capacidad del territorio para generar "
         "conocimiento aplicado, determinante de la productividad total de los factores y "
         "de la demanda de trabajo calificado.")},

    {"codigo": None, "busqueda": r"inversión.*educación",
     "dimension": "Capital humano",
     "nivel_literatura": 1, "alias": "INV_EDUCACION",
     "justificacion": (
         "La inversión pública en educación es el mecanismo mediante el cual el municipio "
         "mejora la calidad del capital humano disponible, reduciendo el desempleo estructural "
         "en el mediano y largo plazo.")},

    # ── CONDICIONES SOCIOECONÓMICAS ───────────────────────────────────────────
    {"codigo": "140010004", "busqueda": None,
     "dimension": "Condiciones socioeconómicas",
     "nivel_literatura": 3, "alias": "IND_POB_MULT",
     "justificacion": (
         "El Índice de Pobreza Multidimensional (IPM) sintetiza privaciones en educación, "
         "salud, vivienda y condiciones laborales. Es el determinante estructural más robusto "
         "del desempleo en la literatura colombiana (DANE/CEPAL 2016): territorios con IPM "
         "elevado presentan menor participación laboral y mayor desempleo de larga duración.")},

    {"codigo": None, "busqueda": r"índice de pobreza(?!.*multidimensional)",
     "dimension": "Condiciones socioeconómicas",
     "nivel_literatura": 2, "alias": "IND_POB_MON",
     "justificacion": (
         "El índice de pobreza monetaria complementa el IPM capturando la insuficiencia de "
         "ingresos. Su inclusión permite discriminar entre pobreza por privaciones materiales "
         "y pobreza por falta de ingresos, dos mecanismos distintos de exclusión laboral.")},

    {"codigo": None, "busqueda": r"ingresos corrientes per cápita",
     "dimension": "Condiciones socioeconómicas",
     "nivel_literatura": 1, "alias": "ING_CORR_PC",
     "justificacion": (
         "Los ingresos corrientes per cápita del municipio reflejan su capacidad fiscal para "
         "financiar servicios públicos generadores de empleo directo e indirecto. Bogotá "
         "presenta valores extremadamente altos, coherentes con su concentración de actividad "
         "económica formal.")},

    # ── DESEMPEÑO ECONÓMICO ───────────────────────────────────────────────────
    {"codigo": "310010008", "busqueda": None,
     "dimension": "Desempeño económico",
     "nivel_literatura": 3, "alias": "IND_PROD",
     "justificacion": (
         "El índice de productividad municipal mide la eficiencia económica del territorio "
         "en términos de valor agregado por unidad de factor productivo. Mayor productividad "
         "implica mayor capacidad de absorción laboral. Polos industriales como Bogotá, "
         "Medellín y Barranquilla destacan coherentemente con sus menores tasas de desempleo "
         "relativo.")},

    # ── SEGURIDAD Y CONFLICTO ─────────────────────────────────────────────────
    {"codigo": None, "busqueda": r"incidencia del conflicto armado|iica",
     "dimension": "Seguridad y conflicto",
     "nivel_literatura": 2, "alias": "IICA_CONFLICTO",
     "justificacion": (
         "El Índice de Incidencia del Conflicto Armado (IICA) captura la exposición histórica "
         "a la violencia organizada, que genera desplazamiento forzado, destrucción de capital "
         "físico y disrupción de los mercados laborales locales. Cúcuta, Cali y Quibdó "
         "presentan valores extremos coherentes con su historia reciente.")},

    {"codigo": None, "busqueda": r"hurto a personas",
     "dimension": "Seguridad y conflicto",
     "nivel_literatura": 1, "alias": "TASA_HURTO",
     "justificacion": (
         "La tasa de hurto a personas mide la inseguridad ciudadana cotidiana. Altos niveles "
         "de inseguridad desincentivan la inversión privada, reducen la movilidad de "
         "trabajadores y aumentan la informalidad como estrategia de evasión del riesgo. "
         "Bogotá presenta el valor extremo superior.")},

    # ── CAPACIDAD INSTITUCIONAL ───────────────────────────────────────────────
    {"codigo": None, "busqueda": r"posición nacional en gestión|gestión.*alcaldía",
     "dimension": "Capacidad institucional",
     "nivel_literatura": 1, "alias": "POS_GESTION",
     "justificacion": (
         "La posición nacional en gestión municipal mide la eficiencia de las alcaldías para "
         "movilizar y ejecutar recursos de inversión pública. Mayor capacidad institucional "
         "se traduce en mayor inversión generadora de empleo y mejores servicios públicos "
         "que reducen los costos de participación en el mercado laboral formal.")},

    {"codigo": None, "busqueda": r"inversión.*transporte",
     "dimension": "Capacidad institucional",
     "nivel_literatura": 1, "alias": "INV_TRANSPORTE",
     "justificacion": (
         "La inversión en infraestructura de transporte reduce los costos de movilidad de "
         "trabajadores, conecta mercados laborales regionales y facilita el acceso a "
         "oportunidades de empleo fuera del municipio de residencia.")},

    {"codigo": None, "busqueda": r"inversión.*desarrollo comunitario",
     "dimension": "Capacidad institucional",
     "nivel_literatura": 1, "alias": "INV_DES_COMUN",
     "justificacion": (
         "La inversión en desarrollo comunitario fortalece el capital social del territorio. "
         "Mayor cohesión social se asocia con menor desempleo de larga duración mediante "
         "redes de información sobre oportunidades laborales y apoyo mutuo.")},

    # ── MEDIO AMBIENTE Y TERRITORIO ───────────────────────────────────────────
    {"codigo": None, "busqueda": r"ecosistemas estratégicos",
     "dimension": "Medio ambiente y territorio",
     "nivel_literatura": 1, "alias": "IND_ECOSIST",
     "justificacion": (
         "El índice de ecosistemas estratégicos refleja la proporción de áreas naturales "
         "protegidas o de alta importancia ambiental. En Colombia, alta cobertura de "
         "ecosistemas se asocia con economías más extractivas, menor diversificación "
         "productiva y patrones diferenciados de empleo rural.")},
]

# ── Resolver códigos None buscando en indicadores_dict ────────────────────────
def _resolver_codigo(entrada, indicadores_dict):
    if entrada["codigo"] is not None:
        return entrada["codigo"]
    patron = entrada["busqueda"]
    for codigo, nombre in indicadores_dict.items():
        if re.search(patron, nombre, re.IGNORECASE):
            return codigo
    return None

for e in CATALOGO_LITERATURA:
    if e["codigo"] is None:
        e["codigo"] = _resolver_codigo(e, indicadores_dict)

# ── Filtrar al subconjunto que existe en df_pd ────────────────────────────────
VARS_LITERATURA = [
    e["codigo"] for e in CATALOGO_LITERATURA
    if e["codigo"] is not None and e["codigo"] in df_pd.columns
]
catalogo_activo = [e for e in CATALOGO_LITERATURA if e.get("codigo") in VARS_LITERATURA]
df_lit = df_pd[VARS_LITERATURA].copy()

# ── Mapas de nivel de literatura (L, 0–3) y alias, resueltos por código ────────
# L se fija EXCLUSIVAMENTE desde la revisión de literatura (Etapa 2), antes de
# computar cualquier métrica empírica (Etapas 3–6): así L es independiente de Q
# y no se reintroduce circularidad en la selección final.
L_LITERATURA     = {e["codigo"]: e["nivel_literatura"] for e in catalogo_activo}
ALIAS_LITERATURA = {e["codigo"]: e["alias"] for e in catalogo_activo}

print(f"Variables con respaldo en literatura: {len(VARS_LITERATURA)} de {len(CATALOGO_LITERATURA)} definidas")

# Variables no resueltas (código no encontrado o no disponible en la tabla)
no_resueltas = [e for e in CATALOGO_LITERATURA if e.get("codigo") not in VARS_LITERATURA]
if no_resueltas:
    print("\nVariables no resueltas (verificar en dim_indicadores):")
    for e in no_resueltas:
        print(f"  • {e['busqueda']}  →  {e.get('codigo')}")

# ── Tabla de justificaciones ──────────────────────────────────────────────────
filas_justificacion = [
    {
        "Codigo": e["codigo"],
        "Nombre": indicadores_dict.get(e["codigo"], e["codigo"]),
        "Dimension": e["dimension"],
        "Justificacion_literatura": e["justificacion"][:120] + "..."
    }
    for e in catalogo_activo
]
display(spark.createDataFrame(filas_justificacion))

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC En la ejecución registrada, solo **11 de las 16** variables del catálogo de literatura se resolvieron
# MAGIC contra `dim_indicadores` y `covariables_prefiltradas` (las 5 restantes —cobertura neta en secundaria
# MAGIC ya resuelta aparte, ciencia, inversión en educación, inversión en transporte, inversión en desarrollo
# MAGIC comunitario— no se encontraron con los patrones de búsqueda o no pasaron el pre-filtro cuantitativo).
# MAGIC Las etapas 3 a 7 siguientes trabajan, por tanto, sobre estas **11 candidatas**, que cubren igualmente
# MAGIC las siete dimensiones conceptuales: infraestructura básica, capital humano (2 variables), condiciones
# MAGIC socioeconómicas (3 variables), desempeño económico, seguridad y conflicto (2 variables), capacidad
# MAGIC institucional y medio ambiente y territorio.
# MAGIC
# MAGIC # Etapa 3 — Análisis descriptivo de las 16 candidatas
# MAGIC
# MAGIC El objetivo de esta etapa es caracterizar las distribuciones de las 16 variables con respaldo
# MAGIC en literatura, identificar la presencia y naturaleza de valores atípicos, y evaluar si las
# MAGIC distribuciones son aproximadamente normales.
# MAGIC
# MAGIC **Aclaración importante:** el modelo Fay-Herriot asume normalidad de los **efectos aleatorios y
# MAGIC de los errores de muestreo**, *no* de las covariables —que pueden tener cualquier distribución.
# MAGIC Por tanto, aquí la normalidad/asimetría **no es un requisito del modelo**, sino un diagnóstico para
# MAGIC decidir transformaciones (p. ej. logarítmica) que mejoren la **linealidad** de la relación con Y y
# MAGIC reduzcan el **apalancamiento (leverage)** de valores extremos en la regresión sintética. Una covariable
# MAGIC muy asimétrica no se descarta por ello; solo señala que conviene revisar su forma funcional.
# MAGIC
# MAGIC > **Potencia de Shapiro-Wilk a n=23:** con esta muestra el test tiene baja potencia, así que
# MAGIC > *no rechazar* H₀ no equivale a "es normal". Se usa de forma descriptiva, junto a la asimetría
# MAGIC > y los boxplots, no como criterio binario de inclusión/exclusión.
# MAGIC
# MAGIC Se reportan:
# MAGIC - **Estadísticas descriptivas** completas (media, mediana, desviación muestral, asimetría, rango)
# MAGIC - **Test de Shapiro-Wilk** (descriptivo a n=23; H₀: distribución normal)
# MAGIC - **Outliers IQR** con identificación del departamento correspondiente

# COMMAND ----------

# DBTITLE 1,Estadísticas descriptivas + Shapiro-Wilk para las 16 candidatas
stats_rows = []
outlier_map = {}

for col in VARS_LITERATURA:
    nombre = indicadores_dict.get(col, col)
    data   = df_lit[col].values

    sw_stat, sw_pval = shapiro(data)

    q1, q3  = np.percentile(data, [25, 75])
    iqr     = q3 - q1
    lb, ub  = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask_out = (data < lb) | (data > ub)
    outlier_depts = [entidades[i] for i, v in enumerate(mask_out) if v]
    outlier_map[col] = outlier_depts

    stats_rows.append({
        "Codigo":                col,
        "Variable":              nombre[:60],
        "Dimension":             next((e["dimension"] for e in catalogo_activo if e["codigo"] == col), ""),
        "Media":                 round(float(np.mean(data)), 2),
        "Mediana":               round(float(np.median(data)), 2),
        "Desv_Std":              round(float(np.std(data, ddof=1)), 4),
        "Asimetria":             round(float(stats.skew(data, bias=False)), 3),
        "Rango":                 round(float(np.ptp(data)), 2),
        "N_Outliers_IQR":        int(mask_out.sum()),
        "Departamentos_Outlier": ", ".join(outlier_depts) if outlier_depts else "—",
        "Shapiro_W":             float(round(sw_stat, 4)),
        "Shapiro_p":             float(round(sw_pval, 4)),
        "Normalidad_SW":         "✓" if sw_pval > 0.05 else "✗",
    })

display(spark.createDataFrame(pd.DataFrame(stats_rows)))

# COMMAND ----------

# DBTITLE 1,Boxplots con anotación de departamentos atípicos
ncols = 2
nrows = (len(VARS_LITERATURA) + 1) // ncols
fig, axes = plt.subplots(nrows, ncols, figsize=(14, nrows * 3.5))
axes = axes.flatten()

for idx, col in enumerate(VARS_LITERATURA):
    ax     = axes[idx]
    nombre = indicadores_dict.get(col, col)
    data   = df_lit[col].values

    ax.boxplot(data, vert=False, patch_artist=True,
               boxprops=dict(facecolor="lightsteelblue", color="steelblue"),
               medianprops=dict(color="navy", linewidth=2))

    q1, q3 = np.percentile(data, [25, 75])
    iqr    = q3 - q1
    lb, ub = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    for i, v in enumerate(data):
        if v < lb or v > ub:
            ax.annotate(entidades[i], (v, 1),
                        textcoords="offset points", xytext=(0, 6),
                        fontsize=7, ha="center", color="firebrick", rotation=30)

    ax.set_title(f"{nombre[:50]}", fontsize=8, fontweight="bold")
    ax.set_yticks([])
    ax.grid(True, linestyle=":", alpha=0.4)

for idx in range(len(VARS_LITERATURA), len(axes)):
    axes[idx].set_visible(False)

plt.suptitle("Boxplots — 16 candidatas con respaldo en literatura",
             fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()
display(fig)
plt.close(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC Las estadísticas descriptivas y los boxplots muestran un patrón recurrente: **8 de las 11 variables**
# MAGIC fallan Shapiro-Wilk (p < 0.05) y la mayoría tiene entre 1 y 3 outliers IQR, casi siempre los mismos
# MAGIC departamentos en los extremos —Bogotá, Riohacha, Quibdó, Cúcuta, Valledupar y Santa Marta—:
# MAGIC
# MAGIC - **Cobertura de energía eléctrica rural**: fuertemente asimétrica a la izquierda (asimetría -1.99,
# MAGIC   Shapiro p≈0); Valledupar, Cúcuta y Riohacha quedan muy por debajo del resto (~64-70 % vs. >88 %
# MAGIC   en la mayoría), comportándose como un grupo aparte de baja electrificación rural.
# MAGIC - **Ingresos corrientes per cápita**: el outlier es Bogotá, con un valor (~$1,25M) más de 2 veces
# MAGIC   el de cualquier otro dominio — esperable dada su concentración de actividad económica.
# MAGIC - **Índice de pobreza / IPM**: Riohacha es outlier superior en IPM (45 vs. máximo ~30 del resto),
# MAGIC   coherente con su perfil de pobreza estructural.
# MAGIC - **Índice de Productividad**: Bogotá, Medellín y Barranquilla destacan como los tres polos de mayor
# MAGIC   productividad, separados del resto de dominios.
# MAGIC - **IICA (conflicto armado)**: Quibdó y Cúcuta son outliers superiores (0.10 y 0.06 frente a una
# MAGIC   mediana de 0.03), consistente con su historia de conflicto; Cali también se aparta moderadamente.
# MAGIC - **Tasa de hurto** y **Posición en gestión**: Bogotá y Quibdó respectivamente son los únicos outliers,
# MAGIC   cada uno en un extremo distinto de su distribución.
# MAGIC - **Tasa de tránsito a educación superior** y **cobertura neta en secundaria**: son las dos variables
# MAGIC   más simétricas y sin outliers relevantes (Shapiro no rechaza H₀ para tránsito a educación superior),
# MAGIC   lo que las hace candidatas más estables para una regresión lineal sin necesidad de transformación.
# MAGIC
# MAGIC En general, los outliers no son ruido aleatorio sino casos territorialmente interpretables (capitales
# MAGIC grandes, zonas de conflicto, periferias con baja cobertura de servicios), lo que se retoma en la
# MAGIC Etapa 5 al evaluar cuánto pesan estos puntos sobre la correlación con la tasa de desempleo.
# MAGIC
# MAGIC # Etapa 4 — Relación con TASA_DESEMPLEO_PCT
# MAGIC
# MAGIC Esta etapa evalúa la **asociación directa** de cada covariable candidata con la variable objetivo.
# MAGIC Se reportan dos medidas de correlación complementarias:
# MAGIC
# MAGIC - **Pearson r:** mide la asociación lineal; sensible a valores atípicos con n=23.
# MAGIC   Se acompaña de un **intervalo de confianza bootstrap al 95 %** (10.000 remuestreos)
# MAGIC   para comunicar la incertidumbre real dado el tamaño muestral.
# MAGIC
# MAGIC - **Spearman ρ:** mide la asociación monotónica usando rangos; robusto ante outliers
# MAGIC   y ante desviaciones de linealidad.
# MAGIC
# MAGIC Cuando Pearson y Spearman difieren sustancialmente (|r − ρ| > 0.15), la diferencia indica
# MAGIC que uno o más valores extremos están distorsionando la correlación paramétrica — señal de
# MAGIC que la variable requiere análisis de influencia (Etapa 5).
# MAGIC
# MAGIC Los scatter plots muestran todos los dominios etiquetados con el nombre del departamento,
# MAGIC lo que permite identificar visualmente qué territorios se comportan como casos especiales.
# MAGIC
# MAGIC > **Sobre los p-valores:** dado que estas variables ya fueron seleccionadas por su correlación con Y
# MAGIC > (Etapa previa) y se evalúan múltiples covariables sin corrección por multiplicidad, los p-valores
# MAGIC > mostrados **no tienen interpretación inferencial nominal** (riesgo de falsos positivos inflado).
# MAGIC > Se reportan solo como referencia descriptiva; las decisiones se apoyan en el **IC bootstrap**
# MAGIC > (¿incluye 0?), la **concordancia Pearson/Spearman** y la **robustez LOO**, no en el p-valor.

# COMMAND ----------

# DBTITLE 1,Helper: IC bootstrap para Pearson r
def bootstrap_pearson_ci(x, y, n_boot=10000, alpha=0.05, seed=42):
    rng   = np.random.default_rng(seed)
    n_obs = len(x)
    boot_rs = []
    for _ in range(n_boot):
        idx  = rng.integers(0, n_obs, n_obs)
        r, _ = pearsonr(x[idx], y[idx])
        boot_rs.append(r)
    return np.percentile(boot_rs, [100 * alpha / 2, 100 * (1 - alpha / 2)])

# COMMAND ----------

# DBTITLE 1,Scatter plots: cada candidata vs TASA_DESEMPLEO_PCT
for col in VARS_LITERATURA:
    nombre = indicadores_dict.get(col, col)
    x      = df_lit[col].values

    r_p, p_p = pearsonr(x, Y)
    r_s, p_s = spearmanr(x, Y)
    ci        = bootstrap_pearson_ci(x, Y)
    diverge   = abs(r_p - r_s) > 0.15

    m_reg, b_reg, *_ = stats.linregress(x, Y)
    xr = np.linspace(x.min(), x.max(), 100)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(x, Y, color="steelblue", edgecolors="white", s=70, zorder=3)
    for xi, yi, lab in zip(x, Y, entidades):
        ax.annotate(lab, (xi, yi), textcoords="offset points",
                    xytext=(4, 3), fontsize=7, color="dimgray")
    ax.plot(xr, m_reg * xr + b_reg, "r--", linewidth=1.5, label="Regresión OLS")

    warn = "  ⚠ Pearson/Spearman divergen (outlier influence)" if diverge else ""
    ax.set_title(
        f"{nombre[:65]}\n"
        f"Pearson r={r_p:.3f}  IC 95% [{ci[0]:.3f}, {ci[1]:.3f}]  p={p_p:.3f}"
        f"   |   Spearman ρ={r_s:.3f}  p={p_s:.3f}{warn}",
        fontsize=9
    )
    ax.set_xlabel(nombre[:60], fontsize=9)
    ax.set_ylabel("TASA_DESEMPLEO_PCT", fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.4)
    plt.tight_layout()
    display(fig)
    plt.close(fig)

# COMMAND ----------

# DBTITLE 1,Tabla comparativa Pearson vs Spearman con IC bootstrap
corr_rows = []
for col in VARS_LITERATURA:
    nombre    = indicadores_dict.get(col, col)
    x         = df_lit[col].values
    r_p, p_p  = pearsonr(x, Y)
    r_s, p_s  = spearmanr(x, Y)
    ci        = bootstrap_pearson_ci(x, Y)
    diverge   = abs(r_p - r_s) > 0.15
    corr_rows.append({
        "Codigo":              col,
        "Variable":            nombre[:55],
        "Pearson_r":           round(r_p, 3),
        "IC_inf_95pct":        round(ci[0], 3),
        "IC_sup_95pct":        round(ci[1], 3),
        "Pearson_p":           round(p_p, 4),
        "Spearman_rho":        round(r_s, 3),
        "Spearman_p":          round(p_s, 4),
        "Divergencia_outlier": "⚠" if diverge else "—",
    })

corr_df = pd.DataFrame(corr_rows).sort_values("Pearson_r", key=abs, ascending=False)
display(spark.createDataFrame(corr_df))

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC Los scatter plots y la tabla comparativa muestran que **ninguna** de las 11 candidatas tiene un IC
# MAGIC bootstrap que cruce 0, y en ningún caso |Pearson − Spearman| > 0.15: Pearson y Spearman concuerdan
# MAGIC en signo y magnitud para las 11 variables, sin señal de "Divergencia_outlier" marcada (columna
# MAGIC `Divergencia_outlier` = "—" en todas las filas). Esto es una señal positiva de que, a pesar del
# MAGIC tamaño muestral pequeño, las asociaciones no dependen de forma desproporcionada de un único punto
# MAGIC extremo en estas 11 variables.
# MAGIC
# MAGIC Por magnitud de Pearson, el ranking observado es:
# MAGIC
# MAGIC 1. **Posición nacional en gestión** (r=0.602, IC [0.22, 0.80]) — la asociación más fuerte: peor
# MAGIC    posición de gestión (valor más alto) se asocia con mayor desempleo.
# MAGIC 2. **Cobertura de energía eléctrica rural** (r=-0.595, IC [-0.81, -0.21]) — a mayor electrificación
# MAGIC    rural, menor desempleo; visualmente domina el "grupo Caribe" (Riohacha, Valledupar, Cúcuta) con
# MAGIC    baja cobertura y desempleo alto.
# MAGIC 3. **Cobertura neta en secundaria** (r=-0.521) y **tasa de tránsito a educación superior** (r=0.487,
# MAGIC    pero con signo *contraintuitivo*: a mayor tránsito a educación superior, *mayor* desempleo en el
# MAGIC    scatter — Cúcuta y Riohacha tienen alto tránsito educativo y alto desempleo simultáneamente, lo
# MAGIC    que probablemente refleja que estas ciudades retienen estudiantes porque no hay suficiente oferta
# MAGIC    laboral, no que la educación cause desempleo).
# MAGIC 4. **Índice de Ecosistemas estratégicos** (r=-0.514) e **Ingresos corrientes per cápita** (r=-0.483)
# MAGIC    muestran asociación negativa moderada; en el caso de ingresos, el patrón está apalancado por la
# MAGIC    posición extrema de Bogotá con bajo desempleo relativo y muy altos ingresos.
# MAGIC 5. **IPM** (r=0.443) e **IICA-conflicto** (r=0.429) confirman la dirección esperada por literatura
# MAGIC    (más pobreza/conflicto → más desempleo), aunque con los IC más anchos del grupo (bordeando 0 por
# MAGIC    el lado inferior), señal de que su evidencia es la menos precisa con n=23.
# MAGIC 6. **Productividad** (r=-0.414) y **tasa de hurto** (r=-0.412) cierran el grupo con asociaciones de
# MAGIC    magnitud similar y signo esperado (más productividad/seguridad ciudadana → menos desempleo).
# MAGIC
# MAGIC Un patrón recurrente en los gráficos es el rol de **Cúcuta, Riohacha, Valledupar y Quibdó** como
# MAGIC dominios con desempleo alto (>14.9 %) que tiran las rectas de regresión, mientras **Bucaramanga,
# MAGIC Pereira, Santa Marta y Pasto** anclan el extremo de bajo desempleo (<8.7 %). Esta heterogeneidad
# MAGIC geográfica es justamente lo que la Etapa 5 (LOO) cuantifica de forma rigurosa.
# MAGIC
# MAGIC # Etapa 5 — Análisis de influencia de outliers
# MAGIC
# MAGIC Con n=23 dominios, un único punto puede cambiar drásticamente una correlación o el signo
# MAGIC de un coeficiente de regresión. Esta etapa cuantifica el peso real de los valores atípicos
# MAGIC usando dos herramientas complementarias:
# MAGIC
# MAGIC 1. **Distancia de Cook (Cook's D):** mide cuánto cambia el vector de coeficientes de la
# MAGIC    regresión X_i → Y al eliminar el punto i. Un Cook's D > 4/n se considera influyente.
# MAGIC    Con n=23 el umbral es ≈ 0.174.
# MAGIC
# MAGIC 2. **Leave-one-out (LOO):** para los 5 departamentos que aparecen más frecuentemente como
# MAGIC    outliers (Bogotá, Medellín, Quibdó, Cali, Cúcuta), se recalcula la correlación con Y
# MAGIC    excluyendo uno a la vez. La diferencia Δ = r_LOO − r_full cuantifica el impacto de ese
# MAGIC    departamento. Variables con |Δ| < 0.10 en todos los LOO se consideran **robustas**.

# COMMAND ----------

# DBTITLE 1,Cook's Distance para las 16 candidatas
COOK_THRESHOLD = 4 / len(Y)
cook_rows = []

for col in VARS_LITERATURA:
    nombre   = indicadores_dict.get(col, col)
    x        = df_lit[col].values.reshape(-1, 1)
    X_sm     = add_constant(x)
    model_sm = OLS(Y, X_sm).fit()
    cooks_d  = OLSInfluence(model_sm).cooks_distance[0]

    influyentes = [
        f"{entidades[i]} ({cooks_d[i]:.3f})"
        for i in np.where(cooks_d > COOK_THRESHOLD)[0]
    ]
    cook_rows.append({
        "Codigo":              col,
        "Variable":            nombre[:55],
        "Max_CooksD":          round(float(max(cooks_d)), 4),
        "N_influyentes":       len(influyentes),
        "Puntos_influyentes":  "; ".join(influyentes) if influyentes else "—",
    })

display(spark.createDataFrame(cook_rows))
print(f"Umbral Cook's D > 4/n = {COOK_THRESHOLD:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC Con el umbral de 4/n = 0.174, **4 de las 11 variables** tienen al menos un punto influyente:
# MAGIC
# MAGIC | Variable | Cook's D máx. | Punto influyente |
# MAGIC |---|---|---|
# MAGIC | Ingresos corrientes per cápita | 0.676 | Bogotá |
# MAGIC | Cobertura de energía eléctrica rural | 0.450 | Riohacha |
# MAGIC | Tasa de hurto a personas | 0.513 | Bogotá |
# MAGIC | Índice de Ecosistemas estratégicos | 0.306 | Santa Marta |
# MAGIC
# MAGIC Las otras 7 variables (tránsito a educación superior, cobertura neta en secundaria, IPM/Índice de
# MAGIC Pobreza, productividad, IICA-conflicto y posición en gestión) tienen Cook's D máximo entre 0.11 y 0.17,
# MAGIC por debajo del umbral — ningún dominio individual domina su regresión simple con Y. Es notable que
# MAGIC **ingresos per cápita y tasa de hurto** comparten a Bogotá como su único punto influyente, lo cual es
# MAGIC consistente con que Bogotá es un valor atípico extremo en ambas variables (ver boxplots de la
# MAGIC Etapa 3); esto debilita la confianza en esas dos asociaciones como evidencia generalizable más allá
# MAGIC del caso de la capital.

# COMMAND ----------

# DBTITLE 1,Leave-one-out: estabilidad de la correlación ante exclusión de outliers
# Nombres comunes (no necesariamente el nombre oficial completo del DANE, p. ej.
# MUNICIPIO trae "SANTIAGO DE CALI" y "SAN JOSÉ DE CÚCUTA"). Por eso el match se
# hace por substring sobre el nombre normalizado, no por igualdad exacta.
DEPT_LOO = ["BOGOTA", "MEDELLIN", "QUIBDO", "CALI", "CUCUTA"]
DEPT_LOO_NORM = [normalizar_municipio(d) for d in DEPT_LOO]

# Verificación: cada nombre de DEPT_LOO debe matchear al menos un municipio real;
# si no, el filtro LOO de ese departamento se ejecutaría sobre todos los dominios
# sin excluir ninguno (bug silencioso).
for dept, dept_norm in zip(DEPT_LOO, DEPT_LOO_NORM):
    if not any(dept_norm in e for e in entidades_norm):
        print(f"⚠ '{dept}' no matchea ningún MUNICIPIO — revisar nombre exacto en entidades_norm.")

loo_rows = []
for col in VARS_LITERATURA:
    nombre   = indicadores_dict.get(col, col)
    x        = df_lit[col].values
    r_full, _ = pearsonr(x, Y)
    fila = {"Codigo": col, "Variable": nombre[:45], "r_full": round(r_full, 3)}
    for dept, dept_norm in zip(DEPT_LOO, DEPT_LOO_NORM):
        mask = np.array([dept_norm not in e for e in entidades_norm])
        if mask.sum() >= 3:
            r_loo, _ = pearsonr(x[mask], Y[mask])
            clave = dept[:5].replace(".", "")
            fila[f"r_sin_{clave}"]    = round(r_loo, 3)
            fila[f"delta_{clave}"]    = round(r_loo - r_full, 3)
    loo_rows.append(fila)

loo_df = pd.DataFrame(loo_rows)
num_cols_loo = [c for c in loo_df.columns if c not in ("Codigo", "Variable")]
loo_df[num_cols_loo] = loo_df[num_cols_loo].astype(float)
display(spark.createDataFrame(loo_df))

# ── Heatmap de deltas ─────────────────────────────────────────────────────────
delta_cols = [c for c in loo_df.columns if c.startswith("delta_")]
variables  = loo_df["Variable"].tolist()
delta_mat  = loo_df[delta_cols].fillna(0.0).values
dept_labels = [d.replace("delta_", "") for d in delta_cols]

fig, ax = plt.subplots(figsize=(8, max(5, len(VARS_LITERATURA) * 0.45)))
im = ax.imshow(delta_mat, cmap="RdYlGn", aspect="auto",
               vmin=-0.3, vmax=0.3)
plt.colorbar(im, ax=ax, label="Δr = r_LOO − r_full")
ax.set_xticks(range(len(dept_labels))); ax.set_xticklabels(dept_labels, rotation=30, ha="right")
ax.set_yticks(range(len(variables)));  ax.set_yticklabels(variables, fontsize=7)
for i in range(len(variables)):
    for j in range(len(dept_labels)):
        ax.text(j, i, f"{delta_mat[i, j]:.2f}", ha="center", va="center", fontsize=7)
ax.set_title("Cambio en correlación al excluir cada departamento (LOO)\n"
             "Verde: r aumenta | Rojo: r disminuye | Blanco: sin cambio",
             fontsize=10, fontweight="bold")
plt.tight_layout()
display(fig)
plt.close(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC Con el filtro ya corregido, `delta_BOGOT` deja de ser 0.00 en todas las filas: excluir Bogotá mueve
# MAGIC la correlación de **ingresos corrientes per cápita** en Δ=-0.073 y la de **tasa de hurto** en
# MAGIC Δ=-0.063 — ambas dentro de lo esperable dado que Cook's D ya señalaba a Bogotá como punto influyente
# MAGIC en esas dos variables (Etapa 5). El resto de variables, y el resto de departamentos (Medellín,
# MAGIC Quibdó, Cali, Cúcuta), se mantienen con |Δr| ≤ 0.10, sin que ninguna cruce el umbral de fragilidad
# MAGIC de forma consistente en más de un dominio.
# MAGIC
# MAGIC > **Corrección aplicada (dos pasos):** en una versión anterior, `delta_BOGOT` era siempre 0.00 porque
# MAGIC > el filtro comparaba `entidades != "BOGOTA D.C."` contra `ENTIDAD_NORMALIZADO`, cuyo valor real para
# MAGIC > la capital era `"BOGOTA"` (sin "D.C.") — la máscara nunca excluía ninguna fila. Al cambiar la
# MAGIC > fuente a `MUNICIPIO` (nombre oficial DANE) y normalizar (mayúsculas, sin tildes ni puntuación) se
# MAGIC > arregló Bogotá, pero expuso un segundo mismatch: `MUNICIPIO` guarda el nombre oficial completo
# MAGIC > ("SANTIAGO DE CALI", "SAN JOSÉ DE CÚCUTA"), no el nombre corto ("CALI", "CUCUTA"), así que la
# MAGIC > igualdad exacta seguía sin matchear esos dos dominios. La solución final compara por **substring**
# MAGIC > (`dept_norm in entidad_norm`) en vez de igualdad exacta, lo que matchea el nombre corto dentro del
# MAGIC > nombre oficial completo para los cinco departamentos sin depender de su forma exacta. Se mantiene
# MAGIC > la verificación explícita que avisa si algún nombre de `DEPT_LOO` no matchea ningún municipio real.
# MAGIC
# MAGIC # Etapa 6 — Estructura espacial: Moran's I
# MAGIC
# MAGIC El modelo Fay-Herriot estándar supone que los errores de los dominios son **independientes**.
# MAGIC Si los departamentos muestran autocorrelación espacial en la tasa de desempleo —es decir,
# MAGIC si departamentos geográficamente próximos tienen tasas similares— el modelo podría subestimar
# MAGIC la varianza de los estimadores.
# MAGIC
# MAGIC El **índice de Moran's I** cuantifica esta dependencia espacial:
# MAGIC - I > 0: autocorrelación positiva (vecinos similares)
# MAGIC - I ≈ 0: independencia espacial
# MAGIC - I < 0: autocorrelación negativa (vecinos disimilares)
# MAGIC
# MAGIC Se construye una matriz de pesos espaciales W basada en la **distancia inversa**
# MAGIC entre los centroides de los 23 dominios (coordenadas de `dim_divipola`),
# MAGIC estandarizada por filas. La significancia se evalúa con una prueba de permutación
# MAGIC (999 aleatorizaciones).
# MAGIC
# MAGIC > **Qué se prueba y dónde.** El supuesto de FH es sobre los **residuos** (lo que queda tras
# MAGIC > condicionar por las covariables), no sobre Y cruda: las covariables pueden *explicar* parte de la
# MAGIC > estructura espacial de Y. Por eso aquí Moran sobre **Y cruda** es solo **descriptivo** (¿hay
# MAGIC > estructura espacial en el fenómeno?), y el test metodológicamente relevante —Moran sobre los
# MAGIC > **residuos** del modelo con las covariables seleccionadas— se realiza al cierre de la Etapa 7.
# MAGIC >
# MAGIC > **Nota técnica:** bajo H₀ el valor esperado de Moran's I no es 0 sino E[I] = −1/(n−1)
# MAGIC > (≈ −0.045 con n=23); el contraste por permutación lo tiene en cuenta empíricamente.

# COMMAND ----------

# DBTITLE 1,Moran's I sobre TASA_DESEMPLEO_PCT
try:
    df_divipola = (
        spark.table("tesis.dim.dim_divipola")
        .filter(F.col("CODIGO_MUNICIPIO").isin(df_meta["CODIGO_MUNICIPIO"].tolist()))
        .select("CODIGO_MUNICIPIO", "LATITUD", "LONGITUD")
        .toPandas()
    )
    df_coords = (
        df_meta[["CODIGO_MUNICIPIO", "MUNICIPIO"]]
        .merge(df_divipola, on="CODIGO_MUNICIPIO", how="left")
    )
    coords = df_coords[["LATITUD", "LONGITUD"]].values.astype(float)

    if np.isnan(coords).any():
        print("⚠ Coordenadas incompletas — se imputan con la media del grupo.")
        coords = pd.DataFrame(coords, columns=["LAT", "LON"]).fillna(
            pd.DataFrame(coords, columns=["LAT", "LON"]).mean()
        ).values

    dist_mat = cdist(coords, coords)
    np.fill_diagonal(dist_mat, np.inf)
    W_raw = 1.0 / dist_mat
    W     = W_raw / W_raw.sum(axis=1, keepdims=True)

    def moran_i(y, W):
        n  = len(y)
        yc = y - y.mean()
        return n * np.sum(W * np.outer(yc, yc)) / (np.sum(W) * np.sum(yc ** 2))

    I_obs = moran_i(Y, W)

    rng    = np.random.default_rng(42)
    I_perm = [moran_i(rng.permutation(Y), W) for _ in range(999)]
    p_moran = np.mean(np.abs(I_perm) >= abs(I_obs))

    print(f"Moran's I = {I_obs:.4f}")
    print(f"p-valor (permutación, 999 muestras) = {p_moran:.4f}")
    if p_moran < 0.05:
        print("→ Autocorrelación espacial SIGNIFICATIVA (p < 0.05).")
        print("  Limitación: el modelo Fay-Herriot estándar ignora esta dependencia.")
        print("  Extensión recomendada: Spatial FH (Singh et al. 2005).")
    else:
        print("→ No se detecta autocorrelación espacial significativa (p ≥ 0.05).")
        print("  El supuesto de independencia del modelo Fay-Herriot es razonable.")

    # Gráfico de distribución de permutaciones
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(I_perm, bins=40, color="lightsteelblue", edgecolor="steelblue", alpha=0.85)
    ax.axvline(I_obs, color="red", linewidth=2, label=f"I observado = {I_obs:.4f}")
    ax.set_xlabel("Moran's I (permutaciones)", fontsize=10)
    ax.set_ylabel("Frecuencia", fontsize=10)
    ax.set_title(f"Test de permutación Moran's I  (p = {p_moran:.4f})", fontsize=11, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.4)
    plt.tight_layout()
    display(fig)
    plt.close(fig)

except Exception as e:
    print(f"No se pudo calcular Moran's I: {e}")
    print("Verificar que dim_divipola contiene LATITUD y LONGITUD para los dominios del estudio.")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC El Moran's I observado sobre `TASA_DESEMPLEO_PCT` cruda es **I = -0.0865** (p = 0.222 por
# MAGIC permutación), valor cercano al esperado bajo independencia para n=23 (E[I] = -1/(n-1) ≈ -0.045) y
# MAGIC sin significancia estadística. El histograma de permutaciones muestra que el valor observado cae
# MAGIC cómodamente dentro de la distribución nula (la mayoría de la masa entre -0.10 y 0.05). **No hay
# MAGIC evidencia de autocorrelación espacial en la tasa de desempleo cruda** entre estos 23 dominios usando
# MAGIC pesos de distancia inversa. Esta es solo una primera mirada descriptiva: el chequeo metodológicamente
# MAGIC relevante para el supuesto de independencia de Fay-Herriot es sobre los **residuos** del modelo con
# MAGIC covariables, que se evalúa al cierre de la Etapa 7 — y, como se verá allí, el resultado cambia.
# MAGIC
# MAGIC # Etapa 7 — Selección final: de 16 a 4 covariables
# MAGIC
# MAGIC ## 7.1 Justificación de parsimonia
# MAGIC
# MAGIC El modelo Fay-Herriot incluye como componente un predictor sintético de la forma:
# MAGIC
# MAGIC $$\hat{\mu}_i = \mathbf{x}_i^\top \hat{\boldsymbol{\beta}}$$
# MAGIC
# MAGIC donde $\mathbf{x}_i$ es el vector de covariables del dominio $i$ y $\hat{\boldsymbol{\beta}}$
# MAGIC se estima por GLS sobre los $n=23$ dominios. La regla empírica para regresión lineal establece
# MAGIC que se requieren al menos 5–10 observaciones por parámetro estimado para evitar sobreajuste:
# MAGIC
# MAGIC $$p_{\max} \approx \frac{n}{5} = \frac{23}{5} = 4.6$$
# MAGIC
# MAGIC Por tanto, el modelo puede sostener como máximo **4 covariables más el intercepto**
# MAGIC (5 parámetros en total) sin riesgo serio de sobreajuste. La comparación AIC/BIC entre
# MAGIC especificaciones alternativas se realiza en `fay_herriot.py`.
# MAGIC
# MAGIC ## 7.2 Selección por ranking compuesto (libre, dirigido por datos)
# MAGIC
# MAGIC En lugar de fijar las 4 covariables a mano, la selección **emerge de un ranking reproducible**
# MAGIC que combina dos componentes en un único score:
# MAGIC
# MAGIC $$C \;=\; (1-\alpha)\,\underbrace{Q}_{\text{robustez empírica}} \;+\; \alpha\,\underbrace{\tfrac{L}{3}}_{\text{respaldo en literatura}}, \qquad \alpha = 0.30$$
# MAGIC
# MAGIC **Q — score cuantitativo (lo decide el dato).** Promedio de cinco *deseabilidades* en [0,1]
# MAGIC (mayor = mejor), todas derivadas de las Etapas 3–6:
# MAGIC
# MAGIC | Componente | Definición | Qué premia |
# MAGIC |-----------|-----------|-----------|
# MAGIC | `fuerza_IC` | \|r\| **conservador** = extremo del IC bootstrap más cercano a 0; **0 si el IC cruza 0** | señal fuerte **y precisa** (ataca el *winner's curse*) |
# MAGIC | `concordancia` | $1-\min(\lvert r-\rho\rvert,0.3)/0.3$ | acuerdo Pearson/Spearman (no dominada por outliers) |
# MAGIC | `estab_LOO` | $1-\min(\max\lvert\Delta\rvert,0.3)/0.3$ | correlación estable al excluir cada dominio |
# MAGIC | `baja_influencia` | $1-\min(\max\text{CookD},1)/1$ | no apalancada en un solo punto |
# MAGIC | `no_redundancia` | $1-\max\lvert\text{corr con las demás candidatas}\rvert$ | aporta información nueva |
# MAGIC
# MAGIC **L — score de literatura (0–3).** Nivel ordinal asignado en la Etapa 2 con rúbrica escrita
# MAGIC (3 = determinante directo y documentado en Colombia; 2 = documentado en economías en desarrollo
# MAGIC con mecanismo claro; 1 = mecanismo plausible / proxy). **L se fijó antes de mirar Q**, por lo que
# MAGIC no reintroduce circularidad.
# MAGIC
# MAGIC **Cierre del ranking.** Se ordena por C, se aplica **diversidad dimensional** (≤1 covariable por
# MAGIC dimensión, para máxima cobertura conceptual y mínima redundancia) y se hace una **prueba de
# MAGIC sensibilidad a α** ∈ {0.2, 0.3, 0.4}: si el conjunto ganador no cambia, la selección es robusta
# MAGIC al peso que se le dé a la literatura. La parsimonia (7.1) fija el tamaño del conjunto en **4**.

# COMMAND ----------

# DBTITLE 1,Construcción del score compuesto C = (1−α)·Q + α·(L/3)
# Reutiliza las métricas ya calculadas y mostradas en las Etapas 4–5
corr_map   = {r["Codigo"]: r for r in corr_rows}   # Etapa 4 (r, ρ, IC bootstrap)
cook_map   = {r["Codigo"]: r for r in cook_rows}   # Etapa 5 (Max_CooksD)
delta_cols = [c for c in loo_df.columns if c.startswith("delta_")]  # Etapa 5 (LOO)

# No redundancia: 1 − máx |correlación| con las demás candidatas
corr16_abs = df_lit[VARS_LITERATURA].corr().abs()
np.fill_diagonal(corr16_abs.values, 0.0)
max_corr_otras = corr16_abs.max(axis=1)

ALPHA_BASE = 0.30   # peso de la literatura
CAP_DIVERG = 0.30   # |r−ρ| que anula la concordancia
CAP_DELTA  = 0.30   # |Δ| LOO que anula la estabilidad
CAP_COOK   = 1.00   # Cook's D que anula la deseabilidad de baja influencia

rank_rows = []
for col in VARS_LITERATURA:
    cm    = corr_map[col]
    r_p   = cm["Pearson_r"];     r_s   = cm["Spearman_rho"]
    ci_lo = cm["IC_inf_95pct"];  ci_hi = cm["IC_sup_95pct"]

    # fuerza PRECISA: |r| conservador desde el IC; 0 si el IC cruza 0
    fuerza = 0.0 if (ci_lo <= 0 <= ci_hi) else min(abs(ci_lo), abs(ci_hi))

    concord = 1 - min(abs(r_p - r_s), CAP_DIVERG) / CAP_DIVERG

    lo_row    = loo_df[loo_df["Codigo"] == col]
    max_delta = float(lo_row[delta_cols].abs().max(axis=1).values[0]) if not lo_row.empty else np.nan
    estab_loo = (1 - min(max_delta, CAP_DELTA) / CAP_DELTA) if not np.isnan(max_delta) else 0.0

    max_ck = cook_map[col]["Max_CooksD"]
    influ  = 1 - min(max_ck, CAP_COOK) / CAP_COOK

    nonredund = float(1 - max_corr_otras[col])

    Q = float(np.mean([fuerza, concord, estab_loo, influ, nonredund]))
    L = L_LITERATURA[col]
    C = (1 - ALPHA_BASE) * Q + ALPHA_BASE * (L / 3.0)

    rank_rows.append({
        "Codigo":          col,
        "Alias":           ALIAS_LITERATURA[col],
        "Variable":        indicadores_dict.get(col, col)[:45],
        "Dimension":       next((e["dimension"] for e in catalogo_activo if e["codigo"] == col), ""),
        "fuerza_IC":       round(fuerza, 3),
        "concordancia":    round(concord, 3),
        "estab_LOO":       round(estab_loo, 3),
        "baja_influencia": round(influ, 3),
        "no_redundancia":  round(nonredund, 3),
        "Q":               round(Q, 3),
        "L":               L,
        "C":               round(C, 3),
    })

rank_df = pd.DataFrame(rank_rows).sort_values("C", ascending=False).reset_index(drop=True)
rank_df.insert(0, "Rank", rank_df.index + 1)
display(spark.createDataFrame(rank_df))
print(f"Q = promedio de 5 deseabilidades (pesos iguales)  |  C = {1-ALPHA_BASE:.1f}·Q + {ALPHA_BASE:.1f}·(L/3)")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC El ranking por C produce el siguiente orden: **(1) Índice de Productividad** (C=0.706),
# MAGIC **(2) Tasa de tránsito a educación superior** (C=0.686), (3) Cobertura neta en secundaria (C=0.664),
# MAGIC **(4) IPM** (C=0.615), **(5) IICA-conflicto** (C=0.590), seguidas de cobertura de energía rural,
# MAGIC Índice de Pobreza, posición en gestión, ecosistemas, tasa de hurto e ingresos per cápita.
# MAGIC
# MAGIC Algunos patrones notables en los componentes de Q:
# MAGIC
# MAGIC - **Productividad** lidera no por tener el Pearson más fuerte (es el séptimo en magnitud, r=-0.414),
# MAGIC   sino porque combina alta concordancia Pearson/Spearman (0.967), alta estabilidad LOO (0.847) y baja
# MAGIC   influencia de outliers (0.852) — es la variable más "limpia" estadísticamente, aunque su
# MAGIC   `no_redundancia` es baja (0.105) por su alta correlación con ingresos per cápita (r=0.895, ver
# MAGIC   Etapa 7.4).
# MAGIC - **Tránsito a educación superior** combina el mejor balance entre Q (0.694) y L=2, con la mayor
# MAGIC   `no_redundancia` del grupo (0.67) — es la variable más "única" de las 11 en términos de información.
# MAGIC - **IPM e Índice de Pobreza** (la misma dimensión socioeconómica, prácticamente colineales) comparten
# MAGIC   exactamente Q=0.45 por construcción matemática (son la misma variable con signo invertido), pero
# MAGIC   IPM tiene L=3 frente a L=2 de Índice de Pobreza, lo que la separa en el ranking (C=0.615 vs 0.515).
# MAGIC - **Posición en gestión**, a pesar de tener el Pearson más fuerte del grupo (r=0.602) y baja
# MAGIC   influencia (0.879), queda en el puesto 8 por su literatura más débil (L=1) y por tener la
# MAGIC   `fuerza_IC` relativamente moderada (0.223) dado que su IC bootstrap es el más ancho proporcionalmente.
# MAGIC - **Ingresos corrientes per cápita** cierra el ranking (C=0.413): es la variable con peor
# MAGIC   `baja_influencia` (0.324, reflejando el Cook's D de 0.676 de Bogotá visto en la Etapa 5) combinada
# MAGIC   con L=1.

# COMMAND ----------

# DBTITLE 1,Selección por ranking + diversidad dimensional + sensibilidad a α
def seleccionar(df, score_col, k=4, max_per_dim=1):
    """Recorre las variables ordenadas por score y selecciona hasta k,
    admitiendo a lo sumo max_per_dim por dimensión."""
    sel, dim_count = [], {}
    for _, r in df.sort_values(score_col, ascending=False).iterrows():
        d = r["Dimension"]
        if dim_count.get(d, 0) < max_per_dim:
            sel.append(r["Codigo"])
            dim_count[d] = dim_count.get(d, 0) + 1
        if len(sel) == k:
            break
    return sel

K_FINAL     = 4   # tamaño máximo por parsimonia (7.1): n/5 ≈ 4.6
MAX_PER_DIM = 1   # ≤1 por dimensión → cobertura conceptual amplia, redundancia mínima

# Selección base (α = 0.30) y comparación con el top-4 sin restricción de diversidad
seleccionadas      = seleccionar(rank_df, "C", k=K_FINAL, max_per_dim=MAX_PER_DIM)
top_sin_diversidad = rank_df.sort_values("C", ascending=False)["Codigo"].head(K_FINAL).tolist()

# Sensibilidad a α: ¿cambia el conjunto ganador?
Q_series = rank_df.set_index("Codigo")["Q"]
L_series = pd.Series(L_LITERATURA)
sel_por_alpha = {}
for alpha in [0.20, 0.30, 0.40]:
    tmp = rank_df.copy()
    tmp["C"] = tmp["Codigo"].map((1 - alpha) * Q_series + alpha * (L_series / 3.0))
    sel_por_alpha[alpha] = seleccionar(tmp, "C", k=K_FINAL, max_per_dim=MAX_PER_DIM)

sens_rows = []
for col in VARS_LITERATURA:
    fila = {"Alias": ALIAS_LITERATURA[col]}
    for a in [0.20, 0.30, 0.40]:
        fila[f"sel_a{a:.1f}"] = "✓" if col in sel_por_alpha[a] else ""
    sens_rows.append(fila)
sens_df = pd.DataFrame(sens_rows)
sens_df = sens_df[(sens_df.drop(columns="Alias") == "✓").any(axis=1)]
display(spark.createDataFrame(sens_df))

estable = all(set(sel_por_alpha[a]) == set(seleccionadas) for a in [0.20, 0.30, 0.40])
print("Conjunto seleccionado (α=0.30, ≤1 por dimensión):")
for c in seleccionadas:
    print(f"  • {ALIAS_LITERATURA[c]:18s}  {indicadores_dict.get(c, c)[:55]}")
print(f"\nTop-4 por C sin restricción de diversidad: {[ALIAS_LITERATURA[c] for c in top_sin_diversidad]}")
print(f"¿Selección estable en α∈{{0.2,0.3,0.4}}?  {'SÍ — robusta al peso de la literatura' if estable else 'NO — reportar la dependencia de α'}")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC El conjunto seleccionado —**Productividad, Tránsito a educación superior, IPM, IICA-conflicto**—
# MAGIC se mantiene **idéntico** en α ∈ {0.20, 0.30, 0.40}: las cuatro variables aparecen marcadas con "✓"
# MAGIC en las tres columnas de la tabla de sensibilidad, sin que ninguna otra variable entre o salga del
# MAGIC conjunto al mover el peso de la literatura. Esto confirma que la selección **no es un artefacto**
# MAGIC del valor arbitrario α=0.30, sino un resultado robusto tanto si se pesa más el dato empírico (α=0.20)
# MAGIC como si se pesa más la literatura (α=0.40).
# MAGIC
# MAGIC Vale notar que el top-4 por C **sin** la restricción de diversidad dimensional sería
# MAGIC {Productividad, Tránsito a educación superior, Cobertura neta en secundaria, IPM} — es decir, sin la
# MAGIC regla de ≤1 por dimensión, dos de las cuatro covariables pertenecerían a la misma dimensión
# MAGIC (capital humano), desplazando a IICA-conflicto. La restricción de diversidad es, por tanto, la que
# MAGIC introduce cobertura de la dimensión de seguridad y conflicto en el modelo final, a cambio de una
# MAGIC variable (cobertura neta en secundaria) con C apenas 0.05 puntos menor.

# COMMAND ----------

# DBTITLE 1,Matriz de correlación entre las 16 candidatas (evidencia de redundancia)
# Respalda con números las exclusiones por colinealidad (p. ej. pobreza monetaria vs IPM).
# No se calcula un VIF conjunto de las 16 porque con n=23 el sistema sería casi singular
# (16 predictores + intercepto ≈ n); la correlación por pares es el diagnóstico apropiado aquí.
corr16_signed = df_lit[VARS_LITERATURA].corr()
labels16 = [ALIAS_LITERATURA[c] for c in VARS_LITERATURA]

fig, ax = plt.subplots(figsize=(11, 9))
sns.heatmap(corr16_signed, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            vmin=-1, vmax=1, xticklabels=labels16, yticklabels=labels16,
            linewidths=0.5, linecolor="white", annot_kws={"size": 6},
            cbar_kws={"label": "Correlación"}, ax=ax)
ax.set_title("Correlación entre las 16 candidatas — base para juzgar redundancia",
             fontsize=12, fontweight="bold")
plt.xticks(rotation=45, ha="right", fontsize=7)
plt.yticks(rotation=0, fontsize=7)
plt.tight_layout()
display(fig)
plt.close(fig)

# Pareja más correlacionada de cada candidata
redund_rows = []
for col in VARS_LITERATURA:
    serie = corr16_signed[col].drop(col)
    j = serie.abs().idxmax()
    redund_rows.append({
        "Variable":               ALIAS_LITERATURA[col],
        "Mas_correlacionada_con": ALIAS_LITERATURA[j],
        "Correlacion":            round(float(serie[j]), 3),
    })
display(spark.createDataFrame(pd.DataFrame(redund_rows)))

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC La matriz confirma varios pares redundantes entre las 11 candidatas:
# MAGIC
# MAGIC - **IND_POB_MULT vs. IND_POB_MON: r = -1.00** (perfectamente colineales, como se esperaba al ser la
# MAGIC   misma fuente de pobreza expresada en sentidos opuestos). El ranking de la Etapa 7.2 resuelve esta
# MAGIC   redundancia eligiendo IND_POB_MULT (mayor L=3 por su respaldo en literatura colombiana) y
# MAGIC   descartando IND_POB_MON.
# MAGIC - **ING_CORR_PC vs. IND_PROD: r = 0.895** — ambas miden, en esencia, desempeño económico territorial.
# MAGIC   El ranking elige Productividad (C=0.706, primer lugar) y descarta ingresos (C=0.413, último
# MAGIC   lugar), evitando así introducir las dos variables casi colineales en el modelo final.
# MAGIC - **POS_GESTION vs. IND_POB_MON: r = -0.859** (y por tanto ≈ +0.86 con IND_POB_MULT) — la capacidad
# MAGIC   de gestión municipal está fuertemente ligada al nivel de pobreza del territorio, lo que explica
# MAGIC   por qué posición en gestión pierde relevancia marginal una vez que IPM ya está en el modelo.
# MAGIC - El resto de pares tiene correlaciones moderadas (|r| entre 0.30 y 0.67), como cobertura de energía
# MAGIC   rural con ecosistemas estratégicos (r=0.668) o IICA-conflicto con IPM (r=0.567), consistentes con
# MAGIC   covarianza social/territorial esperable pero sin llegar a colinealidad severa.
# MAGIC
# MAGIC Esta evidencia respalda por qué el ranking de C, al maximizar `no_redundancia`, tiende naturalmente
# MAGIC a evitar combinar variables de estos pares en el conjunto final de 4.

# COMMAND ----------

# DBTITLE 1,VIF del conjunto seleccionado
# El VIF se valida solo sobre las covariables finales (sistema bien condicionado con n=23).
X_vif   = df_lit[seleccionadas].values
X_vif_c = add_constant(X_vif)
vif_rows = [
    {
        "Codigo":   col,
        "Alias":    ALIAS_LITERATURA[col],
        "Variable": indicadores_dict.get(col, col)[:50],
        "VIF":      float(round(variance_inflation_factor(X_vif_c, i + 1), 3)),
    }
    for i, col in enumerate(seleccionadas)
]
display(spark.createDataFrame(pd.DataFrame(vif_rows)))
print("VIF < 5: colinealidad baja  |  5–10: moderada  |  > 10: severa")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC Los 4 VIF son todos bajos: **Tránsito a educación superior (1.034)**, **Productividad (1.414)**,
# MAGIC **IICA-conflicto (1.536)** e **IPM (2.028)**. Ninguno se acerca al umbral de colinealidad moderada
# MAGIC (5), confirmando que la regla de diversidad dimensional y el criterio de `no_redundancia` de la
# MAGIC Etapa 7.2 lograron su objetivo: el conjunto final no sufre de multicolinealidad, a pesar de que entre
# MAGIC las 11 candidatas originales existían pares casi perfectamente colineales (IND_POB_MULT/IND_POB_MON,
# MAGIC r=-1.00). El VIF más alto, IPM (2.03), es coherente con su correlación moderada con IICA-conflicto
# MAGIC (r=0.567, ver matriz de redundancia) — ambas reflejan condiciones estructurales del territorio que
# MAGIC se solapan parcialmente, pero sin comprometer la estabilidad de las estimaciones de β.

# COMMAND ----------

# DBTITLE 1,Tabla maestra de decisión y clasificación de las no seleccionadas
# Clasifica cada variable NO seleccionada en dos categorías honestas:
#  · "Débil genuina": el IC bootstrap cruza 0 o la asociación es débil en Pearson Y Spearman.
#  · "Frágil a n=23": asociación real pero inestable a outliers/LOO → candidata a otras
#                     especificaciones o con más dominios; NO es una variable inservible.
decision_rows = []
for _, r in rank_df.iterrows():
    col   = r["Codigo"]
    cm    = corr_map[col]
    ci_lo = cm["IC_inf_95pct"]; ci_hi = cm["IC_sup_95pct"]
    cruza_cero = ci_lo <= 0 <= ci_hi
    debil      = (abs(cm["Pearson_r"]) < 0.40) and (abs(cm["Spearman_rho"]) < 0.40)

    if col in seleccionadas:
        estado = "SELECCIONADA"
    elif cruza_cero or debil:
        estado = "Débil genuina"
    else:
        estado = "Frágil a n=23 (candidata a otras especificaciones)"

    decision_rows.append({
        "Rank":         int(r["Rank"]),
        "Alias":        r["Alias"],
        "Dimension":    r["Dimension"],
        "Q":            r["Q"],
        "L":            r["L"],
        "C":            r["C"],
        "Pearson_r":    cm["Pearson_r"],
        "IC_95":        f"[{ci_lo:.2f}, {ci_hi:.2f}]",
        "Spearman_rho": cm["Spearman_rho"],
        "Estado":       estado,
    })

decision_df = pd.DataFrame(decision_rows)
display(spark.createDataFrame(decision_df))

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## 7.3 Lectura de la selección y reencuadre de las no seleccionadas
# MAGIC
# MAGIC Las 4 covariables finales **no se fijaron a priori**: son las que encabezan el ranking de $C$
# MAGIC (tabla de la celda 7.2) bajo la restricción de ≤1 por dimensión. La justificación de cada una se
# MAGIC lee directamente de sus métricas en la **tabla maestra**: `fuerza_IC` alto (IC que no cruza 0),
# MAGIC `concordancia` Pearson/Spearman alta, `estab_LOO` alta (no depende de un dominio), `baja_influencia`
# MAGIC (Cook's D moderado) y `no_redundancia` alta, sumadas a un nivel de literatura $L$ que aporta el
# MAGIC respaldo conceptual. La **prueba de sensibilidad a α** indica si el conjunto se mantiene cuando se
# MAGIC pesa más o menos la literatura; si es estable, la elección no es un artefacto del valor α = 0.30.
# MAGIC
# MAGIC ### Las "no seleccionadas" no son "inservibles"
# MAGIC
# MAGIC Una variable puede quedar fuera de **esta especificación parsimoniosa** (n/5 ≈ 4) sin ser
# MAGIC irrelevante. La tabla maestra las clasifica en dos grupos con implicaciones distintas:
# MAGIC
# MAGIC | Estado | Significado | Qué hacer en el futuro |
# MAGIC |--------|-------------|------------------------|
# MAGIC | **Frágil a n=23** | La asociación con Y es **real y del signo esperado**, pero inestable a outliers/LOO con solo 23 dominios (típico de IICA, hurto, ingresos per cápita, gestión municipal, dominados por Bogotá/Quibdó/Cúcuta). | **Candidatas legítimas** para especificaciones alternativas del modelo, transformaciones, o cuando se amplíe el n de dominios. No se descartan conceptualmente. |
# MAGIC | **Débil genuina** | La señal es poco fiable incluso al margen del tamaño muestral: el **IC bootstrap cruza 0** o la asociación es débil en Pearson **y** Spearman (típico de cobertura secundaria, ecosistemas, ciencia). | Poco prometedoras como predictores lineales directos; podrían reconsiderarse solo con otra forma funcional o como interacción. |
# MAGIC
# MAGIC Además, algunas variables quedan fuera por **redundancia**, no por debilidad: si dos covariables
# MAGIC miden la misma dimensión y están muy correlacionadas (ver matriz de las 16), entra la de mayor $C$
# MAGIC y la otra se omite para no inflar el VIF —p. ej. pobreza monetaria frente al IPM, o inversión en
# MAGIC educación frente a tránsito a educación superior—. La omitida sigue siendo válida; simplemente
# MAGIC **aporta poca información nueva** dado lo que ya entró.
# MAGIC
# MAGIC > En síntesis: el modelo final usa 4 covariables por parsimonia estadística, **no** porque las
# MAGIC > demás carezcan de valor. La tabla maestra deja trazado, para cada variable, *por qué* entró o no,
# MAGIC > de forma reproducible a partir de las métricas.
# MAGIC
# MAGIC **Resultado de esta ejecución:** de las 7 candidatas no seleccionadas, las **7** quedan clasificadas
# MAGIC como "Frágil a n=23" — ninguna cae en "Débil genuina", porque para todas el IC bootstrap no cruza 0
# MAGIC y al menos uno de Pearson/Spearman supera 0.40 en valor absoluto. Esto significa que, en este
# MAGIC catálogo de 11 candidatas con respaldo en literatura, **todas** tienen una asociación estadísticamente
# MAGIC defendible con la tasa de desempleo; lo que las separa del grupo final es exclusivamente parsimonia
# MAGIC (n/5 ≈ 4) y redundancia con las variables ya seleccionadas, no falta de señal.

# COMMAND ----------

# DBTITLE 1,Moran's I sobre los residuos del modelo con las covariables seleccionadas
# Test metodológicamente relevante para el supuesto de independencia de Fay-Herriot:
# la autocorrelación espacial se evalúa sobre los RESIDUOS, no sobre Y cruda (ver Etapa 6).
try:
    Xr    = add_constant(df_lit[seleccionadas].values)
    fitr  = OLS(Y, Xr).fit()
    resid = fitr.resid

    df_divipola_r = (
        spark.table("tesis.dim.dim_divipola")
        .filter(F.col("CODIGO_MUNICIPIO").isin(df_meta["CODIGO_MUNICIPIO"].tolist()))
        .select("CODIGO_MUNICIPIO", "LATITUD", "LONGITUD").toPandas()
    )
    coords_r = (
        df_meta[["CODIGO_MUNICIPIO"]]
        .merge(df_divipola_r, on="CODIGO_MUNICIPIO", how="left")[["LATITUD", "LONGITUD"]]
        .values.astype(float)
    )
    if np.isnan(coords_r).any():
        coords_r = pd.DataFrame(coords_r, columns=["LAT", "LON"]).fillna(
            pd.DataFrame(coords_r, columns=["LAT", "LON"]).mean()
        ).values

    dist_r = cdist(coords_r, coords_r)
    np.fill_diagonal(dist_r, np.inf)
    Wr = 1.0 / dist_r
    Wr = Wr / Wr.sum(axis=1, keepdims=True)

    def _moran_resid(y, W):
        n  = len(y)
        yc = y - y.mean()
        return n * np.sum(W * np.outer(yc, yc)) / (np.sum(W) * np.sum(yc ** 2))

    I_res  = _moran_resid(resid, Wr)
    rng_r  = np.random.default_rng(42)
    I_perm_r = [_moran_resid(rng_r.permutation(resid), Wr) for _ in range(999)]
    p_res  = np.mean(np.abs(I_perm_r) >= abs(I_res))

    print(f"Moran's I (residuos)   = {I_res:.4f}")
    print(f"p-valor (permutación)  = {p_res:.4f}")
    print(f"Referencia bajo H0: E[I] = -1/(n-1) = {-1/(len(Y)-1):.4f}")
    if p_res < 0.05:
        print("→ Autocorrelación espacial en los RESIDUOS: el supuesto de independencia de FH queda")
        print("  comprometido aun con covariables; considerar Spatial FH (Singh et al. 2005).")
    else:
        print("→ Sin autocorrelación espacial significativa en los residuos: las covariables capturan")
        print("  la estructura espacial; el supuesto de independencia del FH estándar es razonable.")
except Exception as e:
    print(f"No se pudo calcular Moran's I sobre residuos: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC Este es el resultado **metodológicamente más relevante** de todo el notebook y contrasta con la
# MAGIC Etapa 6: el Moran's I sobre los **residuos** del modelo con las 4 covariables seleccionadas es
# MAGIC **I = -0.1253**, con **p = 0.035** (significativo al 5 %), frente al I=-0.0865 (p=0.222, no
# MAGIC significativo) que se obtuvo sobre la tasa de desempleo cruda en la Etapa 6.
# MAGIC
# MAGIC En otras palabras: **las covariables no solo no eliminan la estructura espacial, sino que el
# MAGIC residuo resultante se aleja más del valor esperado bajo independencia** (E[I]=-0.0455) de lo que
# MAGIC se alejaba la variable original. Esto es consistente con que las 4 covariables (productividad,
# MAGIC tránsito a educación superior, IPM, conflicto armado) explican patrones que coinciden parcialmente
# MAGIC con clústeres geográficos de desempleo (p. ej. el eje fronterizo Cúcuta-Riohacha-Valledupar con alto
# MAGIC desempleo y baja cobertura/alta pobreza), dejando en el residuo una estructura espacial remanente que
# MAGIC antes quedaba "diluida" dentro de la variabilidad total de Y.
# MAGIC
# MAGIC **Implicación para `fay_herriot.py`:** el supuesto de independencia entre los errores de los dominios
# MAGIC del modelo Fay-Herriot estándar queda comprometido con esta especificación de 4 covariables. Conviene
# MAGIC reportar esta limitación explícitamente y considerar, como extensión, un modelo Spatial Fay-Herriot
# MAGIC (Singh et al. 2005) que incorpore la matriz de pesos espaciales W ya construida aquí, o al menos
# MAGIC evaluar si los errores estándar de los β estimados deberían ajustarse por esta dependencia residual.

# COMMAND ----------

# DBTITLE 1,Correlación y scatter matrix entre las covariables seleccionadas
data_finales = df_lit[seleccionadas].copy()
data_finales.columns = [ALIAS_LITERATURA[v] for v in seleccionadas]
x_labels = list(data_finales.columns)

# Matriz de correlación
corr_final = data_finales.corr()

# Pares de correlación en formato tabla
corr_pares = []
for i, c1 in enumerate(x_labels):
    for j, c2 in enumerate(x_labels):
        if i <= j:
            corr_pares.append({
                "Variable_1": c1,
                "Variable_2": c2,
                "Correlacion": float(round(corr_final.loc[c1, c2], 3))
            })
display(spark.createDataFrame(pd.DataFrame(corr_pares)))

# Heatmap en escala de grises
fig, ax = plt.subplots(figsize=(7, 5))
sns.set(style="white")
sns.heatmap(
    corr_final,
    annot=True, cmap="Greys", fmt=".2f",
    xticklabels=x_labels, yticklabels=x_labels,
    linewidths=1, linecolor="black",
    cbar_kws={"label": "Correlación"},
    ax=ax
)
ax.set_title("Matriz de correlación — covariables seleccionadas",
             fontsize=12, fontweight="bold", pad=14)
plt.xticks(rotation=30, ha="right", fontsize=10)
plt.yticks(rotation=0, fontsize=10)
plt.tight_layout()
display(fig)
plt.close(fig)

# Scatter matrix
cols_fin = data_finales.columns.tolist()
k        = len(cols_fin)
fig, axes = plt.subplots(k, k, figsize=(3 * k, 3 * k))
for i, ci in enumerate(cols_fin):
    for j, cj in enumerate(cols_fin):
        ax = axes[i][j]
        if i == j:
            ax.hist(data_finales[ci].values, bins=8, color="steelblue",
                    edgecolor="white", alpha=0.8)
            ax.set_ylabel(ci, fontsize=7, fontweight="bold")
        else:
            ax.scatter(data_finales[cj].values, data_finales[ci].values,
                       color="steelblue", edgecolors="white", s=40, alpha=0.8)
        if i == k - 1:
            ax.set_xlabel(cj, fontsize=7)
        ax.tick_params(labelsize=6)
        ax.grid(True, linestyle=":", alpha=0.3)

fig.suptitle("Scatter matrix — covariables seleccionadas",
             fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()
display(fig)
plt.close(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ### Interpretación
# MAGIC
# MAGIC La matriz de correlación en escala de grises confirma que el conjunto final tiene **correlaciones
# MAGIC cruzadas bajas**: la más alta en valor absoluto es IND_POB_MULT vs. IICA_CONFLICTO (r=0.57), seguida
# MAGIC de IND_PROD vs. IND_POB_MULT (r=-0.53); las otras cuatro combinaciones están por debajo de |r|=0.21
# MAGIC (Tránsito a educación superior es casi ortogonal a las otras tres: |r| ≤ 0.09 en todos los casos).
# MAGIC Esto es coherente con los VIF bajos reportados antes y con el hecho de que la regla de diversidad
# MAGIC dimensional efectivamente produjo un conjunto de predictores que cubren ángulos distintos del
# MAGIC fenómeno (desempeño económico, capital humano, pobreza, conflicto) sin solaparse en exceso.
# MAGIC
# MAGIC El *scatter matrix* refuerza visualmente esta lectura: las nubes de puntos entre pares de covariables
# MAGIC no muestran patrones lineales marcados (consistente con las correlaciones bajas), mientras que los
# MAGIC histogramas en la diagonal muestran las asimetrías ya documentadas en la Etapa 3 — IND_PROD e
# MAGIC IICA_CONFLICTO con colas hacia la derecha (pocos dominios con valores altos de productividad o
# MAGIC conflicto) y TASA_TRAN_EDU_SUP con la distribución más simétrica de las cuatro.
# MAGIC
# MAGIC # Base final con las covariables seleccionadas
# MAGIC
# MAGIC Las covariables ganadoras del ranking compuesto (Etapa 7) se escriben junto con los metadatos de
# MAGIC estimación directa en la tabla `tesis.preprocesamiento.covariables_seleccionadas`, que sirve como
# MAGIC insumo directo del notebook `fay_herriot.py`. La lista proviene de la variable `seleccionadas`
# MAGIC calculada por el ranking —no se vuelve a fijar a mano— de modo que la tabla siempre refleja el
# MAGIC resultado reproducible del EDA.

# COMMAND ----------

# DBTITLE 1,Escritura de la tabla de covariables seleccionadas
# La selección proviene del ranking compuesto (celda 7.2), no de una lista hardcodeada.
VARS_SELECCIONADAS = list(seleccionadas)
RENAME_MAP         = {cod: ALIAS_LITERATURA[cod] for cod in VARS_SELECCIONADAS}

cols_salida     = METADATA_COLS + [v for v in VARS_SELECCIONADAS if v not in METADATA_COLS]
df_seleccionado = df_full.select(cols_salida)
for cod, alias in RENAME_MAP.items():
    df_seleccionado = df_seleccionado.withColumnRenamed(cod, alias)

display(df_seleccionado)
df_seleccionado.write.mode("overwrite").option("mergeSchema","true").saveAsTable("tesis.preprocesamiento.covariables_seleccionadas")
print("✓ Tabla escrita: tesis.preprocesamiento.covariables_seleccionadas")
print(f"  Covariables: {[ALIAS_LITERATURA[c] for c in VARS_SELECCIONADAS]}")
