# Estimación de Desempleo en Colombia — SAE (Small Area Estimation)

Repositorio de tesis de maestría. Implementa un modelo **Fay-Herriot** para estimar la tasa de desempleo a nivel municipal en Colombia, combinando microdatos de la GEIH con información auxiliar de TerriData sobre una plataforma **Databricks** (Unity Catalog, PySpark).

---

## Arquitectura de datos

El pipeline de ingesta sigue el modelo medallón **Bronce → Plata → Oro**:

| Capa | Descripción |
|------|-------------|
| **Bronce** | Ingesta raw desde volúmenes de Unity Catalog (CSV / Parquet) |
| **Plata** | Limpieza, normalización y estandarización de campos |
| **Oro** | Tablas analíticas desnormalizadas, listas para modelado (solo GEIH) |

A partir de la capa Oro, el flujo continúa en dos etapas adicionales fuera del esquema medallón:
**preprocesamiento** (estimación directa + selección de covariables) y **modelo** (ajuste Fay-Herriot).

Todo el código corre sobre Databricks (notebooks `.py` con `# Databricks notebook source` /
`# COMMAND ----------`) y persiste en tablas Unity Catalog bajo el catálogo `tesis`.

---

## Patrón de carpetas: orquestador + `shared/`

`preprocesamiento/` y `modelo/` siguen el mismo patrón: un notebook raíz (`estimacion_directa.py`,
`adicion_covariables.py`, `pre_filtrado_covariables.py`, `fay_herriot.py`) actúa como **orquestador fino**
que importa la lógica real desde su propia carpeta `shared/`. Al modificar comportamiento, casi siempre el
cambio va en `shared/`, no en el notebook orquestador.

---

## Estructura del repositorio

```
code/
├── ingesta_datos/
│   ├── geih/
│   │   ├── geih_bronce.py          # Carga de módulos GEIH (fuerza de trabajo, ocupados, no ocupados, etc.)
│   │   ├── geih_plata.py           # Consolidación marco antiguo + marco nuevo, transformaciones de negocio
│   │   ├── geih_oro.py             # Tabla analítica final: mercado laboral con todos los indicadores laborales
│   │   └── shared/
│   │       ├── config/geih_config.py            # Nombres de tablas, constantes
│   │       ├── transformations/campos_nucleo.py # Columnas núcleo comunes a marco antiguo/nuevo
│   │       └── utils/spark_utils.py             # Escritura a Unity Catalog
│   ├── terridata/
│   │   ├── terridata_bronce.py     # Ingesta de TerriData (DNP) con normalización de texto
│   │   ├── terridata_plata.py      # Pivote largo → ancho (~1.582 indicadores como columnas) + dim_indicadores
│   │   └── shared/
│   │       ├── config/terridata_config.py
│   │       ├── transformations/normalizacion.py   # Normalización de texto/nombres
│   │       └── utils/{spark_utils,verification_utils}.py  # Validaciones de la transformación a ancho
│   ├── censo_nal/
│   │   └── censo_bronce.py         # Ingesta del Censo Nacional (no se usa en el flujo actual)
│   └── dimensiones/
│       ├── dim_divipola.py         # Nomenclatura DIVIPOLA de los municipios de Colombia
│       └── dim_geih_divipola.py    # Traduce áreas GEIH a su municipio/código DIVIPOLA correcto
├── preprocesamiento/
│   ├── estimacion_directa.py       # Estimador Hájek + bootstrap (2000 réplicas) por municipio
│   ├── adicion_covariables.py      # Join entre estimaciones directas y covariables de TerriData plata
│   ├── pre_filtrado_covariables.py # Filtro previo: NAs, varianza casi cero, |Pearson| ≥ umbral
│   └── shared/
│       ├── config.py
│       ├── estimador_sae.py        # Interfaz base EstimadorSAE + clase EstimacionDirecta
│       └── feature_selection.py
├── modelo/
│   ├── fay_herriot.py              # Orquestador: ajuste, selección y consolidación del modelo final
│   └── shared/
│       ├── config.py               # Nombres de tablas, sets de covariables a comparar
│       ├── modelo_area_pequena.py  # Interfaz base ModeloAreaPequena (matriz de diseño, LOOCV, comparación MSE)
│       ├── fay_herriot.py          # FayHerriotClasico: ajuste, diagnósticos, LOOCV
│       ├── seleccion_modelo.py     # Tablas de diagnóstico y selección entre modelos (AIC/BIC/MSE/RMSE-LOOCV)
│       ├── diagnosticos_plot.py    # Gráficas de validación
│       └── consolidacion.py        # Unión EBLUP (dominios con GEIH) + predicción sintética (sin GEIH)
└── analisis/
    └── Análisis exploratorio.py    # EDA en 7 etapas sobre el dataset pre-filtrado de covariables
```

---

## Flujo metodológico end-to-end

```
GEIH (microdatos)                          TerriData (DNP)
    │                                            │
    ▼                                            ▼
Bronce → Plata → Oro                        Bronce → Plata
(tesis.geih_oro.mercado_laboral)            (covariables anchas, ~1.582 indicadores)
    │                                            │
    ▼                                            │
estimacion_directa.py                            │
  Hájek + bootstrap (2000 réplicas)               │
  → tesis.modelo.tasa_desempleo_municipal          │
  (23 dominios/municipios con muestra GEIH)        │
    │                                            │
    └──────────────► adicion_covariables.py ◄────┘
                  LEFT JOIN estimaciones × TerriData
                  → tesis.modelo.tasa_desempleo_covariables
                  (23 filas × ~1.590 cols)
                            │
                            ▼
                  pre_filtrado_covariables.py
                  Filtro 1: sin NAs en los 23 dominios        (~1.582 → ~530)
                  Filtro 2: varianza casi cero (< 0.00001)    (~530 → ~220)
                  Filtro 3: |Pearson| ≥ 0.40 con TASA_DESEMPLEO_PCT (~220 → ~84)
                            │
                            ▼
                  tesis.preprocesamiento.covariables_prefiltradas
                            │
                            ▼
                  Análisis exploratorio.py — EDA en 7 etapas (~84 → 4)
                            │
                            ▼
                  tesis.preprocesamiento.covariables_seleccionadas
                            │
                            ▼
                       fay_herriot.py
              ajusta y compara modelos sobre subconjuntos de covariables
              selección por AIC + BIC + MSE medio + RMSE-LOOCV
                            │
                            ▼
        EBLUP (23 dominios con encuesta directa) + predicción sintética
        (municipios sin cobertura GEIH, vía tesis.*.municipios_sin_encuesta)
                            │
                            ▼
              tabla final consolidada (EBLUP + sintético)
              tesis.modelo.fay_herriot_estimaciones_finales
```

### 1. GEIH — ingesta y consolidación

- **Marco antiguo** (hasta 2022): cada módulo viene partido en `area`, `cabecera`, `resto`. Incluye el
  módulo de **inactivos**.
- **Marco nuevo** (2023 en adelante): un solo archivo por módulo, sin partición área/cabecera/resto. No
  trae módulo de inactivos — esa información ya viene integrada en **fuerza de trabajo**.
- Módulos trabajados: `características generales`, `ocupados`, `no ocupados`, `fuerza de trabajo`,
  `inactivos` (solo marco antiguo).
- `geih_oro.py` junta características generales + fuerza de trabajo + no ocupados + ocupados + factores de
  expansión + `dim_divipola` en una tabla de mercado laboral lista para estimar la tasa de desempleo.
- `dim_fex` (factores de expansión actualizados del DANE) **no** vive en `dimensiones/`: se genera dentro
  del propio pipeline GEIH (`TBL_FEX_BRONCE`/`TBL_FEX_PLATA` en `geih_config.py`, construida en
  `geih_plata.py`). Es usable para años ≤ 2018 si se quiere el factor nuevo; para los demás años los
  archivos ya traen el factor de expansión de 2018.

### 2. TerriData — ingesta de covariables (sin capa oro)

- `terridata_bronce.py` carga el archivo de indicadores tal cual.
- `terridata_plata.py` pivotea de formato largo a ancho (una columna por código de indicador DANE),
  valida la transformación (conteo de filas, verificación cruzada) y genera `dim_indicadores`
  (código → nombre descriptivo).

### 3. Estimación directa (`code/preprocesamiento/estimacion_directa.py`)

Estima el desempleo por dominio (municipio) sobre `tesis.geih_oro.mercado_laboral`, filtrado a
`MUNICIPIO not null`, `PEA == 1` y el período objetivo (`PER_ESTIMACION`, `MES_ESTIMACION` en
`shared/config.py`). Usa el **estimador de Hájek** (θ̂ = Σ(wᵢ·yᵢ)/Σwᵢ, con `wᵢ` el factor de expansión y
`yᵢ` = 1 si desocupado). La inferencia es por **bootstrap simple** (B = 2000 réplicas, semilla fija 42,
parametrizable en `shared/config.py`) porque no se cuenta con las variables del diseño muestral para un
estimador de varianza analítico: se calcula θ̂ en la muestra original, se remuestrea con reemplazo B veces,
y el error estándar es la desviación estándar de las B réplicas (IC 95% = percentiles 2.5%/97.5%). Se
considera CV < 15% confiable, 15–30% aceptable, ≥30% no confiable. La lógica vive en
`shared/estimador_sae.py` (clase `EstimacionDirecta`, que hereda de la interfaz base `EstimadorSAE` —
patrón Template Method/Strategy pensado para futuros estimadores). Resultado: 23 municipios con muestra
GEIH → `tesis.modelo.tasa_desempleo_municipal`.

### 4. Selección de covariables

**a) Unión con TerriData** (`adicion_covariables.py`): hace un `LEFT JOIN` entre las 23 estimaciones
directas y `tesis.terridata.terridata_extendido_plata` por `CODIGO_MUNICIPIO = CODIGO_ENTIDAD`,
`PER = ANO`, `MES = MES`. El `LEFT JOIN` preserva las 23 filas aunque algún municipio no tenga covariables
en TerriData. Resultado: `tesis.modelo.tasa_desempleo_covariables` (23 filas × ~1.590 columnas).

**b) Pre-filtrado cuantitativo** (`pre_filtrado_covariables.py`, lógica en `shared/feature_selection.py`),
tres filtros secuenciales sobre las ~1.582 covariables candidatas:

| Filtro | Criterio | Efecto aproximado |
|--------|----------|--------------------|
| 1.1 — Datos faltantes | se conservan solo columnas con **0 NAs** en los 23 dominios | ~1.582 → ~530 |
| 1.2 — Varianza casi cero | se eliminan columnas con varianza < `UMBRAL_VARIANZA` (0.00001) — evitan singularidad en la matriz de diseño | ~530 → ~220 |
| 2 — Correlación con la variable objetivo | se conservan las que tienen \|Pearson\| ≥ `CORR_VALOR` (0.40) con `TASA_DESEMPLEO_PCT` (estrategia `threshold`; también soporta `top_n`) | ~220 → ~84 |

Resultado: `tesis.preprocesamiento.covariables_prefiltradas`.

**c) EDA y selección final — 7 etapas** (`code/analisis/Análisis exploratorio.py`), sobre las ~84
covariables pre-filtradas y los 23 dominios:

1. **Sensibilidad al umbral de correlación**: examina la distribución de \|Pearson\| entre las
   covariables *ya* sobrevivientes al filtro (no es posible repetir el filtro con umbrales menores porque
   sería tautológico — todas pasan por construcción) para detectar si la señal está concentrada o
   repartida cerca del corte de 0.40.
2. **Filtro cualitativo por literatura**: de ~84 a 16 candidatas, exigiendo respaldo en literatura sobre
   determinantes del desempleo en economías en desarrollo / Colombia (Galvis & Meisel 2010; Arango &
   Flórez 2012; Lasso 2014; DANE/CEPAL 2016) y significado de negocio claro, agrupadas en dimensiones
   conceptuales.
3. **Descriptivos y normalidad**: estadísticos descriptivos y prueba de Shapiro-Wilk por covariable.
4. **Relación con la variable objetivo**: scatterplots, Pearson y Spearman, con **intervalos de confianza
   bootstrap al 95%** — necesario porque con n=23 los IC de correlación son amplios (±0.20–0.40) y porque
   el pre-filtro ya sesgó al alza estas correlaciones (*winner's curse* / *double dipping*: el filtro y el
   EDA usan los mismos 23 dominios), por lo que aquí las correlaciones se usan solo como triaje, no como
   evidencia confirmatoria.
5. **Influencia de outliers**: distancia de Cook y validación leave-one-out (LOO) por dominio.
6. **Estructura espacial**: Moran's I sobre los residuos/relación con Y.
7. **Ranking compuesto y selección final**: combina un score empírico (Q) con uno de literatura (L) y
   evalúa sensibilidad a distintos pesos α → **4 covariables ganadoras**.

Resultado: `tesis.preprocesamiento.covariables_seleccionadas`. La validación confirmatoria (AIC/BIC,
diagnósticos, validación cruzada) se deja para la etapa de modelado, no para este EDA.

### 5. Modelo Fay-Herriot (`code/modelo/fay_herriot.py`)

Orquestador fino sobre `tesis.preprocesamiento.covariables_seleccionadas`; el dominio se define como
`PER + MES + DEPARTAMENTO + MUNICIPIO`. Pasos:

1. **Ajuste de modelos**: para cada subconjunto de covariables en `COVAR_SETS` (`shared/config.py`) se
   ajusta un `FayHerriotClasico` (`shared/fay_herriot.py`, que hereda de la interfaz base
   `ModeloAreaPequena` en `shared/modelo_area_pequena.py` — pensada para futuras variantes SAE como
   espacial o temporal) y se corre validación cruzada **leave-one-out (LOOCV)**.
2. **Resultados EBLUP por dominio**: para cada modelo, tabla con estimación directa, EBLUP, CV del EBLUP,
   factor de *shrinkage* (γ) y mejora de CV vs. estimación directa.
3. **Gráficas y diagnósticos de validación** por modelo (`shared/diagnosticos_plot.py`): varianza de
   efectos aleatorios (Â), coeficientes con SE/z/p-valor, R² del predictor sintético, normalidad de
   residuos (Shapiro-Wilk), reducción media del CV, shrinkage promedio, RMSE-LOOCV, y validación
   MSE(EBLUP) vs. varianza directa (test de Wilcoxon).
4. **Selección de modelo** (`shared/seleccion_modelo.py`, solo si hay más de un subconjunto): tabla de
   diagnósticos + tabla de selección, ranking por suma de posiciones en AIC + BIC + MSE medio + RMSE-LOOCV;
   se reporta ΔAIC/ΔBIC (< 2 equivalentes, 2–7 moderado, > 10 sustancial). El modelo ganador se exporta a
   `tesis.modelo.fay_herriot_resultados`.
5. **Predicción sintética** para municipios sin estimación directa (sin cobertura GEIH, leídos desde
   `tesis.*.municipios_sin_encuesta`): ŷ = X'β̂ del modelo ganador, **sin shrinkage** (γ=0, porque no hay
   varianza de muestreo); la incertidumbre combina la varianza de β̂ propagada (x'·Cov(β̂)·x) con la
   varianza de efectos aleatorios (Â). Se exporta a `tesis.modelo.fay_herriot_prediccion_sintetica`.
6. **Tabla final consolidada** (`shared/consolidacion.py`): une EBLUP (dominios con encuesta directa) +
   predicción sintética (dominios sin encuesta), con columna `TIPO` indicando el origen →
   `tesis.modelo.fay_herriot_estimaciones_finales`.

---

## Fuentes de datos

| Fuente | Descripción |
|--------|-------------|
| **GEIH** (DANE) | Gran Encuesta Integrada de Hogares — microdatos mensuales de mercado laboral |
| **TerriData** (DNP) | +1.000 indicadores socioeconómicos territoriales por municipio |
| **DIVIPOLA** (DANE) | Codificación político-administrativa de Colombia |
| **Censo Nacional** (DANE) | Módulos de personas, hogares y viviendas — ingestado pero fuera del flujo actual |

---

## Plataforma

- **Databricks** sobre Azure (Unity Catalog)
- **PySpark** para procesamiento distribuido
- **Python** (pandas, scikit-learn, statsmodels) para análisis estadístico
- Catálogo: `tesis` — esquemas: `geih_bronce`, `geih_plata`, `geih_oro`, `terridata`, `preprocesamiento`,
  `modelo`, `dim`, `censo_nal`
