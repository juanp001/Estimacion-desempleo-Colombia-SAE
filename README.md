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
│   ├── pre_filtrado_covariables.py # Pre-filtrado: completitud y variabilidad (sin mirar la respuesta)
│   ├── dominios_sin_encuesta.py    # Municipios objetivo de Cauca y Valle sin estimación directa
│   └── shared/
│       ├── config.py
│       ├── estimador_sae.py        # Interfaz base EstimadorSAE + clase EstimacionDirecta
│       └── feature_selection.py    # Filtros de completitud, variabilidad y reporte de redundancia
├── modelo/
│   ├── fay_herriot.py              # Orquestador: ajuste, selección y consolidación del modelo final
│   └── shared/
│       ├── config.py               # Tablas, umbrales de CV, ΔAIC de equivalencia, α de significancia
│       ├── modelo_area_pequena.py  # Interfaz base ModeloAreaPequena (matriz de diseño, comparación MSE)
│       ├── fay_herriot.py          # FayHerriotClasico: REML, GLS, EBLUP, MSE de Prasad-Rao, AIC
│       ├── seleccion_modelo.py     # Variantes dejar-una-fuera, Cook, selección (significancia + AIC + parsimonia)
│       ├── diagnosticos.py         # Gráficas de validación, CV directo vs EBLUP, avisos
│       └── consolidacion.py        # Unión EBLUP (dominios con GEIH) + predicción sintética (sin GEIH)
└── analisis/
    ├── analisis_descriptivo.py     # Descriptivo univariado, bivariado y multivariado + catálogo de literatura
    ├── eda_seleccion_covariables.py # Diagnóstico y selección cualitativa de covariables
    └── shared/
        ├── catalogo_literatura.py  # Variables con respaldo en la revisión de literatura
        ├── descriptivos.py         # Figuras e interpretaciones calculadas desde los datos
        ├── diagnosticos.py         # Asociación, Cook, dejar-uno-fuera, VIF
        └── seleccion.py            # Ficha de decisión y ajuste por VIF
databricks.yml                      # Bundle DAB: variables de período, includes y exclusiones de sync
dab/
├── resources/                      # Un job por etapa (dimensiones, ingesta_geih, ingesta_terridata,
│                                   #   preprocesamiento, analisis, modelo)
└── targets/dev.yml                 # Target `dev` (workspace)
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
  → tesis.preprocesamiento.tasa_desempleo_municipal │
  (23 dominios/municipios con muestra GEIH)        │
    │                                            │
    └──────────────► adicion_covariables.py ◄────┘
                  LEFT JOIN estimaciones × TerriData
                  → tesis.preprocesamiento.tasa_desempleo_covariables
                  (23 filas × ~1.590 cols)
                            │
                            ▼
                  pre_filtrado_covariables.py
                  Filtro 1: sin NAs en los 23 dominios
                  Filtro 2: variabilidad (CV y proporción modal)
                  (sin filtro por correlación con la respuesta)
                            │
                            ▼
                  tesis.preprocesamiento.covariables_prefiltradas
                            │
                            ▼
                  analisis_descriptivo.py — catálogo de literatura + descriptivo
                  eda_seleccion_covariables.py — selección cualitativa (→ 4)
                            │
                            ▼
                  tesis.preprocesamiento.covariables_seleccionadas
                            │
                            ▼
                       fay_herriot.py
              compara el conjunto seleccionado con sus variantes dejar-una-fuera
              selección: todas las covariables p < 0.05 → menor AIC → parsimonia (ΔAIC ≤ 2)
                            │
                            ▼
        EBLUP (23 dominios con encuesta directa) + predicción sintética
        (municipios sin cobertura GEIH, vía tesis.preprocesamiento.municipios_sin_encuesta)
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
  expansión + `dim_geih_divipola` (las 32 áreas GEIH; fuera de ellas `MUNICIPIO` queda en NULL) en una tabla
  de mercado laboral lista para estimar la tasa de desempleo.
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
considera CV < 5% confiable, 5–20% aceptable, ≥20% no confiable (`CV_CONFIABLE`/`CV_ACEPTABLE` en `shared/config.py`, los mismos umbrales del modelo). La lógica vive en
`shared/estimador_sae.py` (clase `EstimacionDirecta`, que hereda de la interfaz base `EstimadorSAE` —
patrón Template Method/Strategy pensado para futuros estimadores). Resultado: 23 municipios con muestra
GEIH → `tesis.preprocesamiento.tasa_desempleo_municipal`.

### 4. Selección de covariables

**a) Unión con TerriData** (`adicion_covariables.py`): hace un `LEFT JOIN` entre las 23 estimaciones
directas y `tesis.terridata.terridata_extendido_plata` por `CODIGO_MUNICIPIO = CODIGO_ENTIDAD`,
`PER = ANO`, `MES = MES`. El `LEFT JOIN` preserva las 23 filas aunque algún municipio no tenga covariables
en TerriData. Resultado: `tesis.preprocesamiento.tasa_desempleo_covariables` (23 filas × ~1.590 columnas).

**b) Pre-filtrado** (`pre_filtrado_covariables.py`, lógica en `shared/feature_selection.py`), dos filtros
secuenciales sobre las ~1.582 covariables candidatas, **independientes de la variable respuesta**:

| Filtro | Criterio |
|--------|----------|
| 1 — Datos faltantes | se conservan solo columnas con **0 NAs** en los 23 dominios |
| 2 — Variabilidad | se descartan columnas con coeficiente de variación < `CV_MINIMO` (0.001) o cuyo valor modal cubre más de `PROP_MODAL_MAXIMA` (90%) de los dominios; ambos criterios son invariantes a la escala de medida y evitan singularidad en la matriz de diseño |

No se filtra por correlación con la tasa de desempleo: hacerlo sobre los mismos 23 dominios que después
ajustan el modelo sesgaría al alza las correlaciones de las supervivientes. Los grupos de covariables
duplicadas entre sí (|r| ≥ 0.999) se reportan pero no se descartan. Resultado:
`tesis.preprocesamiento.covariables_prefiltradas` (más `cascada_prefiltrado` y `sensibilidad_variabilidad`).
`dominios_sin_encuesta.py` construye además `tesis.preprocesamiento.municipios_sin_encuesta` (municipios de
Cauca y Valle sin estimación directa, con todas las covariables prefiltradas).

**c) Análisis descriptivo** (`code/analisis/analisis_descriptivo.py`): resuelve el catálogo de literatura
(`shared/catalogo_literatura.py`, solo variables con referencia en la revisión de literatura del proyecto,
con signo esperado) a las covariables prefiltradas y caracteriza los datos de forma univariada, bivariada y
multivariada, con interpretación calculada desde los propios datos. No descarta ninguna covariable.
Resultado: `catalogo_literatura`, `descriptivo_univariado` y `descriptivo_bivariado` en
`tesis.preprocesamiento`; figuras en el volumen `figuras_eda` (prefijo `desc_`).

**d) Selección cualitativa** (`code/analisis/eda_seleccion_covariables.py`), sobre las candidatas
conceptuales y los 23 dominios:

1. **Asociación**: Pearson/Spearman con la tasa de desempleo, intervalo de Fisher y signo esperado.
2. **Robustez**: distancia de Cook (4/n) y exclusión de cada dominio, uno a uno.
3. **Redundancia**: un representante por grupo de covariables con |r| ≥ 0.80 (el de menor Cook máximo).
4. **Ficha de decisión** (`shared/seleccion.py`): elegible = intervalo sin cero y signo coherente con el
   mecanismo; seleccionadas = las `P_MAXIMO` (4) de mayor |r|.
5. **Verificación de multicolinealidad** (VIF ≤ `VIF_MAXIMO`): si falla, se sustituye por la siguiente
   elegible.

No hay AIC ni Moran en el EDA (el Fay-Herriot es clásico y la comparación entre especificaciones se hace en
el modelo). Resultado: `tesis.preprocesamiento.covariables_seleccionadas`, junto con
`decision_covariables`, `trazabilidad_covariables`, `covariables_candidatas` y las tablas de diagnóstico.

### 5. Modelo Fay-Herriot (`code/modelo/fay_herriot.py`)

Orquestador fino sobre `tesis.preprocesamiento.covariables_seleccionadas` (salida de
`eda_seleccion_covariables`); el dominio es el municipio en el período (`PER`, `MES` y código DIVIPOLA `CODIGO_MUNICIPIO`; ver `DOMINIO_COLS` en `shared/config.py`). Las
decisiones se apoyan en Morales et al. (2021). Pasos:

1. **Ajuste de modelos**: el conjunto seleccionado y sus variantes dejando una covariable fuera
   (`shared/seleccion_modelo.py`) se ajustan con `FayHerriotClasico` (`shared/fay_herriot.py`, que hereda
   de la interfaz base `ModeloAreaPequena` en `shared/modelo_area_pequena.py`): Â por REML, β̂ por GLS,
   AIC por ML y MSE de Prasad-Rao con `g3 = D²/(D+Â)³·avar(Â)` (p. 440). Las varianzas D_i son las
   bootstrap de la estimación directa, tratadas como conocidas (p. 427), sin GVF.
2. **Resultados EBLUP por dominio**: para cada modelo, tabla con estimación directa, EBLUP, CV del EBLUP,
   factor de *shrinkage* (γ) y mejora de CV vs. estimación directa.
3. **Gráficas y diagnósticos** por modelo (`shared/diagnosticos.py`): efecto suavizador, histograma de
   residuos estandarizados, coeficientes con SE/z/p-valor, R², Shapiro-Wilk, distancia de Cook y ganancia
   de precisión MSE(EBLUP) vs. varianza directa (Wilcoxon). Las figuras se muestran sin título y no se
   guardan en volúmenes.
4. **Selección de modelo** (`shared/seleccion_modelo.py`): candidatas = variantes con todas las
   covariables p < 0.05 (p. 453); entre ellas la de menor AIC y, entre las equivalentes (ΔAIC ≤ 2), la de
   menos covariables. MSE y Cook no deciden: se reportan como ganancia de precisión y robustez del
   ganador (incluye reajuste sin el dominio más influyente). Se exportan `tesis.modelo.fh_diagnosticos_variantes`,
   `fh_cook`, `fh_seleccion_modelo`, `fh_coeficientes` y `tesis.modelo.fay_herriot_resultados`.
5. **Predicción sintética** para municipios sin estimación directa (sin cobertura GEIH, leídos desde
   `tesis.preprocesamiento.municipios_sin_encuesta`), con avisos de extrapolación y de tasas fuera
   de [0, 100]: ŷ = X'β̂ del modelo ganador, **sin shrinkage** (γ=0, porque no hay
   varianza de muestreo); la incertidumbre combina la varianza de β̂ propagada (x'·Cov(β̂)·x) con la
   varianza de efectos aleatorios (Â). Se exporta a `tesis.modelo.fay_herriot_prediccion_sintetica`.
6. **Tabla final consolidada** (`shared/consolidacion.py`): une EBLUP (dominios con encuesta directa) +
   predicción sintética (dominios sin encuesta), con columna `TIPO` indicando el origen →
   `tesis.modelo.fay_herriot_estimaciones_finales`.

---

## Despliegue con Databricks Asset Bundles (DAB)

`databricks.yml` y `dab/` definen seis jobs sobre cómputo serverless (target único `dev`). Cada job
encadena los notebooks de su etapa:

| Job | Tareas (en orden) |
|-----|-------------------|
| `dimensiones` | `dim_divipola` → `dim_geih_divipola` |
| `ingesta_geih` | `geih_bronce` → `geih_plata` → `geih_oro` |
| `ingesta_terridata` | `terridata_bronce` → `terridata_plata` |
| `preprocesamiento` | `estimacion_directa` → `adicion_covariables` → `pre_filtrado_covariables` → `dominios_sin_encuesta` |
| `analisis` | `analisis_descriptivo` → `eda_seleccion_covariables` |
| `modelo` | `fay_herriot` |

Los jobs no declaran dependencias entre sí; el orden de ejecución es `dimensiones` → `ingesta_geih` e
`ingesta_terridata` → `preprocesamiento` → `analisis` → `modelo`. El período de estimación se controla con
las variables del bundle `anio_estimacion` (2018) y `mes_estimacion` (12), que `preprocesamiento` recibe
como widgets. El volumen `/Volumes/tesis/preprocesamiento/figuras_eda` debe existir antes de correr
`analisis` (el bundle no lo crea).

```
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run preprocesamiento -t dev --params anio_estimacion=2018,mes_estimacion=12
```

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

- **Databricks** (Unity Catalog)
- **PySpark** para procesamiento distribuido
- **Python** (pandas, scikit-learn, statsmodels) para análisis estadístico
- Catálogo: `tesis` — esquemas: `geih_bronce`, `geih_plata`, `geih_oro`, `terridata`, `preprocesamiento`,
  `modelo`, `dim`, `censo_nal`
