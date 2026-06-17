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
entidades = df_meta["ENTIDAD_NORMALIZADO"].values

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

# DBTITLE 1,Leave-one-out: estabilidad de la correlación ante exclusión de outliers
DEPT_LOO = ["BOGOTA D.C.", "MEDELLIN", "QUIBDO", "CALI", "CUCUTA"]

loo_rows = []
for col in VARS_LITERATURA:
    nombre   = indicadores_dict.get(col, col)
    x        = df_lit[col].values
    r_full, _ = pearsonr(x, Y)
    fila = {"Codigo": col, "Variable": nombre[:45], "r_full": round(r_full, 3)}
    for dept in DEPT_LOO:
        mask = entidades != dept
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
        df_meta[["CODIGO_MUNICIPIO", "ENTIDAD_NORMALIZADO"]]
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
