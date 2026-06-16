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
# MAGIC        │  • Etapa 7: parsimonia + VIF + tabla maestra → 4 covariables finales
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

# COMMAND ----------

# DBTITLE 1,Setup: imports y carga de datos
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.getcwd()))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
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
# MAGIC La siguiente celda muestra el **análisis de sensibilidad al umbral**: cuántas variables
# MAGIC pasarían con valores alternativos entre 0.30 y 0.50.

# COMMAND ----------

# DBTITLE 1,Sensibilidad al umbral de correlación
umbrales = [0.30, 0.35, 0.40, 0.45, 0.50]
resultados_umbral = []
for u in umbrales:
    n_pasan = sum(
        abs(np.corrcoef(df_pd[c].dropna().values, Y)[0, 1]) >= u
        for c in df_pd.columns
        if df_pd[c].notna().all()
    )
    resultados_umbral.append({"Umbral_correlacion": u, "Variables_que_pasan": n_pasan})

df_umbral = pd.DataFrame(resultados_umbral)
display(spark.createDataFrame(df_umbral))

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(df_umbral["Umbral_correlacion"], df_umbral["Variables_que_pasan"],
        marker="o", color="steelblue", linewidth=2, markersize=8)
ax.axvline(0.40, color="red", linestyle="--", linewidth=1.5, label="Umbral elegido: 0.40")
for _, row in df_umbral.iterrows():
    ax.annotate(str(int(row["Variables_que_pasan"])),
                (row["Umbral_correlacion"], row["Variables_que_pasan"]),
                textcoords="offset points", xytext=(6, 4), fontsize=10)
ax.set_xlabel("Umbral |Pearson|", fontsize=11)
ax.set_ylabel("N.º variables que superan el umbral", fontsize=11)
ax.set_title("Sensibilidad del pre-filtrado al umbral de correlación", fontsize=12, fontweight="bold")
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
# MAGIC Las 16 variables seleccionadas se agrupan en seis dimensiones conceptuales:
# MAGIC
# MAGIC | Dimensión | Hipótesis de causalidad |
# MAGIC |-----------|-------------------------|
# MAGIC | **Infraestructura básica** | El acceso a servicios esenciales (energía) reduce los costos de producción y favorece la actividad económica formal |
# MAGIC | **Capital humano** | Mayor educación incrementa la empleabilidad y reduce el desempleo friccional y estructural |
# MAGIC | **Condiciones socioeconómicas** | La pobreza multidimensional concentra privaciones que limitan la participación en el mercado laboral |
# MAGIC | **Desempeño económico** | La productividad municipal determina la demanda agregada de trabajo |
# MAGIC | **Seguridad y conflicto** | La inseguridad y el conflicto armado destruyen capital físico, generan desplazamiento y perturban los mercados laborales |
# MAGIC | **Capacidad institucional** | La gestión y la inversión pública generan empleo directo e indirecto mediante la provisión de bienes públicos |

# COMMAND ----------

# DBTITLE 1,Definición del catálogo de literatura y resolución de códigos
# Cada variable se define con su código (si se conoce) o una expresión de búsqueda
# que se resuelve automáticamente contra dim_indicadores.
CATALOGO_LITERATURA = [
    # ── INFRAESTRUCTURA BÁSICA ────────────────────────────────────────────────
    {"codigo": "030010002", "busqueda": None,
     "dimension": "Infraestructura básica",
     "justificacion": (
         "El acceso a energía eléctrica rural es condición necesaria para la actividad "
         "económica en zonas periféricas. Municipios con baja electrificación concentran "
         "mayor informalidad, menor productividad agrícola y desempleo estructural. La "
         "relación causal está documentada en Galvis & Meisel (2010) para ciudades intermedias "
         "colombianas.")},

    # ── CAPITAL HUMANO ────────────────────────────────────────────────────────
    {"codigo": "040010028", "busqueda": None,
     "dimension": "Capital humano",
     "justificacion": (
         "La tasa de tránsito inmediata a la educación superior mide la proporción de "
         "bachilleres que continúan en el nivel terciario, predictor clave del capital humano "
         "futuro del territorio. Arango & Flórez (2012) documentan que mayor formación reduce "
         "el desempleo friccional al acortar el período de búsqueda de empleo.")},

    {"codigo": None, "busqueda": r"cobertura neta.*secundaria",
     "dimension": "Capital humano",
     "justificacion": (
         "La cobertura neta en educación secundaria es la base del sistema educativo local. "
         "Una baja cobertura limita la formación del capital humano mínimo requerido para "
         "acceder al mercado laboral formal, perpetuando el ciclo de informalidad.")},

    {"codigo": None, "busqueda": r"ciencia",
     "dimension": "Capital humano",
     "justificacion": (
         "El índice de ciencia e innovación captura la capacidad del territorio para generar "
         "conocimiento aplicado, determinante de la productividad total de los factores y "
         "de la demanda de trabajo calificado.")},

    {"codigo": None, "busqueda": r"inversión.*educación",
     "dimension": "Capital humano",
     "justificacion": (
         "La inversión pública en educación es el mecanismo mediante el cual el municipio "
         "mejora la calidad del capital humano disponible, reduciendo el desempleo estructural "
         "en el mediano y largo plazo.")},

    # ── CONDICIONES SOCIOECONÓMICAS ───────────────────────────────────────────
    {"codigo": "140010004", "busqueda": None,
     "dimension": "Condiciones socioeconómicas",
     "justificacion": (
         "El Índice de Pobreza Multidimensional (IPM) sintetiza privaciones en educación, "
         "salud, vivienda y condiciones laborales. Es el determinante estructural más robusto "
         "del desempleo en la literatura colombiana (DANE/CEPAL 2016): territorios con IPM "
         "elevado presentan menor participación laboral y mayor desempleo de larga duración.")},

    {"codigo": None, "busqueda": r"índice de pobreza(?!.*multidimensional)",
     "dimension": "Condiciones socioeconómicas",
     "justificacion": (
         "El índice de pobreza monetaria complementa el IPM capturando la insuficiencia de "
         "ingresos. Su inclusión permite discriminar entre pobreza por privaciones materiales "
         "y pobreza por falta de ingresos, dos mecanismos distintos de exclusión laboral.")},

    {"codigo": None, "busqueda": r"ingresos corrientes per cápita",
     "dimension": "Condiciones socioeconómicas",
     "justificacion": (
         "Los ingresos corrientes per cápita del municipio reflejan su capacidad fiscal para "
         "financiar servicios públicos generadores de empleo directo e indirecto. Bogotá "
         "presenta valores extremadamente altos, coherentes con su concentración de actividad "
         "económica formal.")},

    # ── DESEMPEÑO ECONÓMICO ───────────────────────────────────────────────────
    {"codigo": "310010008", "busqueda": None,
     "dimension": "Desempeño económico",
     "justificacion": (
         "El índice de productividad municipal mide la eficiencia económica del territorio "
         "en términos de valor agregado por unidad de factor productivo. Mayor productividad "
         "implica mayor capacidad de absorción laboral. Polos industriales como Bogotá, "
         "Medellín y Barranquilla destacan coherentemente con sus menores tasas de desempleo "
         "relativo.")},

    # ── SEGURIDAD Y CONFLICTO ─────────────────────────────────────────────────
    {"codigo": None, "busqueda": r"incidencia del conflicto armado|iica",
     "dimension": "Seguridad y conflicto",
     "justificacion": (
         "El Índice de Incidencia del Conflicto Armado (IICA) captura la exposición histórica "
         "a la violencia organizada, que genera desplazamiento forzado, destrucción de capital "
         "físico y disrupción de los mercados laborales locales. Cúcuta, Cali y Quibdó "
         "presentan valores extremos coherentes con su historia reciente.")},

    {"codigo": None, "busqueda": r"hurto a personas",
     "dimension": "Seguridad y conflicto",
     "justificacion": (
         "La tasa de hurto a personas mide la inseguridad ciudadana cotidiana. Altos niveles "
         "de inseguridad desincentivan la inversión privada, reducen la movilidad de "
         "trabajadores y aumentan la informalidad como estrategia de evasión del riesgo. "
         "Bogotá presenta el valor extremo superior.")},

    # ── CAPACIDAD INSTITUCIONAL ───────────────────────────────────────────────
    {"codigo": None, "busqueda": r"posición nacional en gestión|gestión.*alcaldía",
     "dimension": "Capacidad institucional",
     "justificacion": (
         "La posición nacional en gestión municipal mide la eficiencia de las alcaldías para "
         "movilizar y ejecutar recursos de inversión pública. Mayor capacidad institucional "
         "se traduce en mayor inversión generadora de empleo y mejores servicios públicos "
         "que reducen los costos de participación en el mercado laboral formal.")},

    {"codigo": None, "busqueda": r"inversión.*transporte",
     "dimension": "Capacidad institucional",
     "justificacion": (
         "La inversión en infraestructura de transporte reduce los costos de movilidad de "
         "trabajadores, conecta mercados laborales regionales y facilita el acceso a "
         "oportunidades de empleo fuera del municipio de residencia.")},

    {"codigo": None, "busqueda": r"inversión.*desarrollo comunitario",
     "dimension": "Capacidad institucional",
     "justificacion": (
         "La inversión en desarrollo comunitario fortalece el capital social del territorio. "
         "Mayor cohesión social se asocia con menor desempleo de larga duración mediante "
         "redes de información sobre oportunidades laborales y apoyo mutuo.")},

    # ── MEDIO AMBIENTE Y TERRITORIO ───────────────────────────────────────────
    {"codigo": None, "busqueda": r"ecosistemas estratégicos",
     "dimension": "Medio ambiente y territorio",
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
# MAGIC La normalidad es relevante porque el modelo Fay-Herriot asume distribución normal para los
# MAGIC efectos aleatorios. Si una covariable presenta asimetría extrema, su transformación logarítmica
# MAGIC puede mejorar el ajuste del predictor sintético.
# MAGIC
# MAGIC Se reportan:
# MAGIC - **Estadísticas descriptivas** completas (media, mediana, desviación estándar, asimetría, rango)
# MAGIC - **Test de Shapiro-Wilk** (apropiado para n=23; H₀: distribución normal)
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
        "Desv_Std":              round(float(np.std(data)), 4),
        "Asimetria":             round(float(stats.skew(data)), 3),
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
# MAGIC (999 aleatorizaciones de Y).

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
# MAGIC ## 7.2 VIF de las 4 covariables seleccionadas
# MAGIC
# MAGIC El Variance Inflation Factor (VIF) cuantifica la multicolinealidad entre covariables.
# MAGIC Un VIF > 5 indica colinealidad moderada problemática; VIF > 10 es severo.
# MAGIC Las 4 covariables finales deben presentar VIF < 5 para garantizar la estabilidad
# MAGIC numérica de la estimación GLS.

# COMMAND ----------

# DBTITLE 1,VIF de las 4 covariables seleccionadas
VARS_FINALES = ["030010002", "040010028", "140010004", "310010008"]
RENAME_FINAL = {
    "030010002": "COB_ENER_RURAL",
    "040010028": "TASA_TRAN_EDU_SUP",
    "140010004": "IND_POB_MULT",
    "310010008": "IND_PROD",
}

# Verificar que las 4 variables están en df_lit
vars_disponibles = [v for v in VARS_FINALES if v in df_lit.columns]
if len(vars_disponibles) < len(VARS_FINALES):
    faltantes = set(VARS_FINALES) - set(vars_disponibles)
    print(f"⚠ Variables finales no disponibles en df_lit: {faltantes}")

X_vif   = df_lit[vars_disponibles].values
X_vif_c = add_constant(X_vif)
vif_rows = [
    {
        "Codigo":   col,
        "Variable": indicadores_dict.get(col, col)[:55],
        "Alias":    RENAME_FINAL[col],
        "VIF":      float(round(variance_inflation_factor(X_vif_c, i + 1), 3)),
    }
    for i, col in enumerate(vars_disponibles)
]
display(spark.createDataFrame(pd.DataFrame(vif_rows)))
print("VIF < 5: multicolinealidad baja  |  5–10: moderada  |  > 10: severa")

# COMMAND ----------

# DBTITLE 1,Tabla maestra de decisión — las 16 candidatas
decision_rows = []

cook_map = {r["Codigo"]: r for r in cook_rows}
delta_col_names = [c for c in loo_df.columns if c.startswith("delta_")]

for col in VARS_LITERATURA:
    nombre    = indicadores_dict.get(col, col)
    x         = df_lit[col].values
    r_p, _    = pearsonr(x, Y)
    r_s, _    = spearmanr(x, Y)
    ci        = bootstrap_pearson_ci(x, Y)
    sw_s, sw_p = shapiro(x)

    ck = cook_map.get(col, {})
    lo_row = loo_df[loo_df["Codigo"] == col]
    deltas = lo_row[delta_col_names].abs().values.flatten().tolist() if not lo_row.empty else []
    max_delta = round(float(max(deltas)), 3) if deltas else None

    seleccionada = col in VARS_FINALES
    dimension    = next((e["dimension"] for e in catalogo_activo if e["codigo"] == col), "")

    decision_rows.append({
        "Codigo":          col,
        "Variable":        nombre[:50],
        "Dimension":       dimension,
        "Pearson_r":       round(r_p, 3),
        "IC_95":           f"[{ci[0]:.2f}, {ci[1]:.2f}]",
        "Spearman_rho":    round(r_s, 3),
        "SW_p":            round(sw_p, 3),
        "Normal_SW":       "✓" if sw_p > 0.05 else "✗",
        "Max_CooksD":      ck.get("Max_CooksD"),
        "Max_LOO_delta":   max_delta,
        "Robusta_LOO":     "✓" if (max_delta is not None and max_delta < 0.10) else "✗",
        "SELECCIONADA":    "✓" if seleccionada else "✗",
    })

decision_df = pd.DataFrame(decision_rows)
display(spark.createDataFrame(decision_df))

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC ## 7.3 Justificación de las 4 covariables seleccionadas
# MAGIC
# MAGIC A partir de los criterios estadísticos de las etapas anteriores y los fundamentos conceptuales
# MAGIC de la Etapa 2, se seleccionan las siguientes cuatro covariables:
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Cobertura de energía eléctrica rural (`COB_ENER_RURAL`)
# MAGIC **Dimensión:** Infraestructura básica
# MAGIC
# MAGIC Esta variable presenta una correlación negativa significativa con la tasa de desempleo:
# MAGIC municipios con menor acceso a energía eléctrica rural tienden a presentar mayor desempleo
# MAGIC estructural. El comportamiento es consistente entre Pearson y Spearman, lo que descarta que
# MAGIC la asociación esté dominada por outliers. Aunque Riohacha presenta un valor extremo inferior
# MAGIC (cobertura cercana al 44 %), este refleja una brecha real de infraestructura con consecuencias
# MAGIC laborales documentadas, no un error de medición. El análisis LOO confirma robustez.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Tasa de tránsito inmediata a educación superior (`TASA_TRAN_EDU_SUP`)
# MAGIC **Dimensión:** Capital humano
# MAGIC
# MAGIC Presenta distribución aproximadamente simétrica con baja dispersión (desviación estándar ≈ 7 pp),
# MAGIC lo que la convierte en la covariable más estable del conjunto. La correlación con Y es consistente
# MAGIC en Pearson y Spearman, con bajos deltas LOO: la asociación no depende de ningún departamento
# MAGIC particular. Aporta la dimensión de capital humano, complementaria a las demás variables.
# MAGIC La baja correlación con las otras tres candidatas (< 0.33 en valor absoluto) garantiza
# MAGIC información no redundante al modelo.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Índice de Pobreza Multidimensional (`IND_POB_MULT`)
# MAGIC **Dimensión:** Condiciones socioeconómicas
# MAGIC
# MAGIC El IPM es el predictor conceptualmente más sólido del desempleo estructural: concentra en un
# MAGIC solo índice privaciones en educación, salud, vivienda y condiciones de trabajo. Presenta
# MAGIC distribución asimétrica positiva (municipios con IPM muy alto, como Quibdó), pero estos valores
# MAGIC reflejan realidades territoriales reales que deben capturarse en el modelo, no corregirse.
# MAGIC La correlación negativa moderada con COB_ENER_RURAL (−0.61) es la más alta entre el par
# MAGIC seleccionado; el VIF confirma que la colinealidad no es problemática (VIF < 5).
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Índice de Productividad (`IND_PROD`)
# MAGIC **Dimensión:** Desempeño económico
# MAGIC
# MAGIC La productividad municipal determina la demanda agregada de trabajo: territorios más productivos
# MAGIC absorben más empleo formal. Bogotá, Medellín y Barranquilla presentan valores extremos superiores
# MAGIC coherentes con su rol como polos económicos. El análisis LOO muestra que excluir estos centros
# MAGIC reduce moderadamente la correlación, pero la dirección e interpretación se mantienen, lo que
# MAGIC valida su inclusión. Junto con el IPM, esta variable cierra el cuadro causal:
# MAGIC más productividad → más empleo; más pobreza → menos participación laboral.
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Variables excluidas y razón de exclusión
# MAGIC
# MAGIC | Variable | Razón de exclusión |
# MAGIC |----------|-------------------|
# MAGIC | Posición nacional en gestión | Alta variabilidad LOO; correlación inestable al excluir 1–2 municipios. Alta dispersión reduce la confiabilidad del predictor con n=23. |
# MAGIC | Índice de Pobreza (monetaria) | Altamente colineal con IPM (VIF > 5 al combinar ambas). El IPM es más informativo al integrar múltiples dimensiones. |
# MAGIC | Ingresos corrientes per cápita | Bogotá es un outlier extremo (Cook's D muy alto). Al excluirlo, la correlación colapsa. La variable captura más la concentración económica de Bogotá que una relación generalizable. |
# MAGIC | IICA (conflicto armado) | Correlación Pearson/Spearman divergentes; fuerte inestabilidad LOO al excluir Quibdó/Cúcuta/Cali. |
# MAGIC | Tasa de hurto | Dominada por Bogotá (Cook's D > umbral). La corrección de inestabilidad LOO es severa. |
# MAGIC | Ecosistemas estratégicos | Correlación con Y débil y con IC bootstrap que incluye 0; no aporta predictibilidad robusta. |
# MAGIC | Inversión - Transporte | Outlier único con asignación extrema distorsiona la correlación (IC bootstrap muy amplio). |
# MAGIC | Inversión - Desarrollo comunitario | Cuatro outliers con valores extremos; correlación inconsistente entre Pearson y Spearman. |
# MAGIC | Inversión - Educación | Colineal con Tasa de tránsito a educación superior (misma dimensión causal, menor robustez). |
# MAGIC | Cobertura neta secundaria | Correlación débil y no significativa con Y; IC bootstrap cruza 0 en ambas direcciones. |
# MAGIC | Índice de ciencia | Correlación débil; no supera el criterio de robustez LOO al excluir Bogotá/Medellín. |
# MAGIC | Posición nacional en gestión (institucional) | Excluida por inestabilidad estadística, no por falta de relevancia conceptual. |

# COMMAND ----------

# DBTITLE 1,Correlación y scatter matrix entre las 4 covariables finales
data_finales = df_lit[VARS_FINALES].copy()
data_finales.columns = [RENAME_FINAL[v] for v in VARS_FINALES]
x_labels = list(RENAME_FINAL.values())

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
ax.set_title("Matriz de correlación — 4 covariables seleccionadas",
             fontsize=12, fontweight="bold", pad=14)
plt.xticks(rotation=30, ha="right", fontsize=10)
plt.yticks(rotation=0, fontsize=10)
plt.tight_layout()
display(fig)
plt.close(fig)

# Scatter matrix
fig, axes = plt.subplots(4, 4, figsize=(12, 12))
cols_fin  = data_finales.columns.tolist()
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
        if i == 3:
            ax.set_xlabel(cj, fontsize=7)
        ax.tick_params(labelsize=6)
        ax.grid(True, linestyle=":", alpha=0.3)

fig.suptitle("Scatter matrix — 4 covariables seleccionadas",
             fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()
display(fig)
plt.close(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC
# MAGIC # Base final con las 4 covariables seleccionadas
# MAGIC
# MAGIC Las cuatro covariables ganadoras del EDA — **COB_ENER_RURAL**, **TASA_TRAN_EDU_SUP**,
# MAGIC **IND_POB_MULT** e **IND_PROD** — se escriben junto con los metadatos de estimación directa
# MAGIC en la tabla `tesis.preprocesamiento.covariables_seleccionadas`, que sirve como insumo
# MAGIC directo del notebook `fay_herriot.py`.

# COMMAND ----------

# DBTITLE 1,Escritura de la tabla de covariables seleccionadas
VARS_SELECCIONADAS = ["030010002", "040010028", "140010004", "310010008"]
RENAME_MAP = {
    "030010002": "COB_ENER_RURAL",
    "040010028": "TASA_TRAN_EDU_SUP",
    "140010004": "IND_POB_MULT",
    "310010008": "IND_PROD",
}

cols_salida   = METADATA_COLS + [v for v in VARS_SELECCIONADAS if v not in METADATA_COLS]
df_seleccionado = df_full.select(cols_salida)
for cod, alias in RENAME_MAP.items():
    df_seleccionado = df_seleccionado.withColumnRenamed(cod, alias)

display(df_seleccionado)
df_seleccionado.write.mode("overwrite").saveAsTable("tesis.preprocesamiento.covariables_seleccionadas")
print("✓ Tabla escrita: tesis.preprocesamiento.covariables_seleccionadas")
