# Estimación de Desempleo en Colombia — SAE (Small Area Estimation)

Repositorio de tesis de maestría. Estima la tasa de desempleo en municipios de Colombia donde la GEIH no tiene
cobertura muestral directa, con un modelo de área pequeña **Fay-Herriot** que combina los microdatos de la GEIH
(DANE) con información auxiliar de TerriData (DNP), sobre **Databricks** (Unity Catalog, PySpark).

- El **Fay-Herriot clásico** (efectos de área independientes, `code/modelo/fay_herriot.py`) es el **benchmark no
  espacial**, no el modelo final.
- Las **variantes espaciales** (SEBLUP con efectos SAR, `code/modelo/fay_herriot_espacial.py`) ya están
  integradas y se comparan de forma controlada con el benchmark. Hasta cerrar esa comparación, las tablas
  municipales del clásico son **resultados preliminares** (`ESTADO_RESULTADO = PRELIMINAR`).
- **Dominio de estimación = ciudad o ciudad con su área metropolitana** (23 dominios: 7 áreas metropolitanas y 16
  ciudades de la GEIH), no el municipio: el `AREA` de la GEIH identifica la ciudad con su A.M.
  (`tesis.dim.dim_dominio_geih`). Los municipios sin encuesta (Cauca y Valle) reciben la predicción sintética.

Este archivo es una guía de entrada. Las reglas de trabajo y el detalle metodológico están en
[CLAUDE.md](CLAUDE.md); las cifras de la corrida vigente, en
[docs/resultados_cierre_2018.md](docs/resultados_cierre_2018.md) y
[docs/fay_herriot_espacial.md](docs/fay_herriot_espacial.md).

---

## Arquitectura de datos

El pipeline de ingesta sigue el modelo medallón **Bronce → Plata → Oro**:

| Capa | Descripción |
|------|-------------|
| **Bronce** | Ingesta raw desde volúmenes de Unity Catalog (CSV / Parquet) |
| **Plata** | Limpieza, normalización y estandarización de campos |
| **Oro** | Tabla analítica desnormalizada (solo GEIH): `tesis.geih_oro.mercado_laboral` |

Después de la capa oro el flujo sigue fuera del esquema medallón: **preprocesamiento** (estimación directa y
covariables), **análisis** (descriptivo y selección de covariables) y **modelo** (Fay-Herriot).

Todo el código corre sobre Databricks (notebooks `.py` con `# Databricks notebook source` /
`# COMMAND ----------`) y persiste en tablas Unity Catalog bajo el catálogo `tesis`
(esquemas `geih_bronce`, `geih_plata`, `geih_oro`, `terridata`, `dim`, `preprocesamiento`, `modelo`).

### Patrón de carpetas: orquestador + `shared/`

`preprocesamiento/` y `modelo/` siguen el mismo patrón: un notebook raíz actúa como **orquestador fino** que
importa la lógica real desde su propia carpeta `shared/`. `analisis/` e `ingesta_datos/` (`geih/`, `terridata/`,
`dimensiones/`) también tienen `shared/`. Al modificar comportamiento, casi siempre el cambio va en `shared/`,
no en el notebook.

---

## Estructura del repositorio

```
code/
├── ingesta_datos/
│   ├── geih/
│   │   ├── renombrar_geih.py       # Paso previo local: nombra los CSV del DANE como espera geih_bronce
│   │   ├── geih_bronce.py          # Carga de módulos GEIH (lectura por nombre de columna)
│   │   ├── geih_plata.py           # Consolida marco antiguo y nuevo; construye dim_fex
│   │   ├── geih_oro.py             # mercado_laboral + reconciliación de la fuerza de trabajo
│   │   ├── datos_publicados.py     # Cifras oficiales del DANE (anexo CNPV 2018) para validar
│   │   └── shared/                 # config/geih_config.py, utils/spark_utils.py y transformations/
│   │                               #   (campos_nucleo, factor_expansion, reconciliacion)
│   ├── terridata/
│   │   ├── terridata_bronce.py     # Ingesta de TerriData (DNP)
│   │   ├── terridata_plata.py      # Pivote largo → ancho (covariables) + dim_indicadores
│   │   └── shared/                 # config, normalizacion, spark_utils, verification_utils
│   └── dimensiones/
│       ├── dim_divipola.py         # Nomenclatura DIVIPOLA
│       ├── dim_dominio_geih.py     # Dominio de estimación de cada municipio (ciudad / ciudad A.M.)
│       ├── dim_geih_divipola.py    # Las 32 capitales y su código de área GEIH
│       └── shared/config/dim_config.py
├── preprocesamiento/
│   ├── estimacion_directa.py       # Hájek + bootstrap por viviendas, por dominio
│   ├── adicion_covariables.py      # Covariables TerriData agregadas al dominio + auditoría
│   ├── pre_filtrado_covariables.py # Completitud y variabilidad (sin mirar la respuesta)
│   ├── dominios_sin_encuesta.py    # Municipios objetivo de Cauca y Valle sin estimación directa
│   └── shared/
│       ├── config.py               # Parámetros del flujo (réplicas, umbrales, cota de covariables…)
│       ├── estimador_sae.py        # Interfaz base EstimadorSAE + EstimacionDirecta
│       ├── bootstrap.py            # Bootstrap por viviendas y linealización de control
│       ├── ventana.py              # Ventana de tiempo y cifra DANE de la misma ventana
│       ├── agregacion_dominios.py, reglas_agregacion.py, auditoria_dominios.py
│       └── feature_selection.py    # Filtros de completitud, variabilidad y redundancia
├── analisis/
│   ├── analisis_descriptivo.py     # Descriptivo + catálogo de literatura
│   ├── eda_seleccion_covariables.py# Selección de covariables (FH univariado, BH, redundancia, VIF)
│   ├── sensibilidad_ventana_temporal.py # Evidencia de la ventana anual (se corre a mano)
│   └── shared/                     # catalogo_literatura, descriptivos, diagnosticos, seleccion,
│                                   #   soporte_objetivos, datos_analisis, ventana_temporal
└── modelo/
    ├── fay_herriot.py              # Orquestador del benchmark clásico (no espacial)
    ├── fay_herriot_espacial.py     # Orquestador de la variante espacial (SEBLUP, SAR)
    ├── sensibilidad_varianza.py    # ψ_d alternativas y GVF (independiente, no alimenta al modelo)
    └── shared/                     # fay_herriot, seleccion_modelo, validacion_predictiva,
                                    #   estabilidad_coeficientes, benchmarking, extrapolacion, consolidacion,
                                    #   fay_herriot_espacial, matriz_proximidad, prediccion_espacial,
                                    #   sensibilidad_espacial, cuadro_comparativo, figuras*, config…
databricks.yml                      # Bundle DAB: variables de período, includes y exclusiones de sync
dab/resources/                      # Un job por etapa + pipeline_completo
dab/targets/dev.yml                 # Target `dev` (workspace)
requirements.txt                    # Versiones del entorno serverless 2 (R-50)
docs/                               # Resultados del cierre y del componente espacial
```

---

## Flujo metodológico end-to-end

```
GEIH (microdatos)                          TerriData (DNP)
    │                                            │
Bronce → Plata → Oro                        Bronce → Plata (covariables anchas)
(tesis.geih_oro.mercado_laboral)                 │
    │                                            │
estimacion_directa.py                            │
  Hájek + bootstrap por viviendas (2.000 réplicas), ventana anual
  → tesis.preprocesamiento.tasa_desempleo_municipal  (23 dominios)
    │                                            │
    └──────────────► adicion_covariables.py ◄────┘
                  covariables agregadas al dominio (denominador propio de cada indicador)
                  → tesis.preprocesamiento.tasa_desempleo_covariables
                            │
                  pre_filtrado_covariables.py → covariables_prefiltradas
                            │
                  analisis_descriptivo.py + eda_seleccion_covariables.py
                  → tesis.preprocesamiento.covariables_seleccionadas
                            │
                       fay_herriot.py   (benchmark clásico, no espacial)
                            │
                  fay_herriot_espacial.py   (variante espacial, comparación controlada)
                            │
        EBLUP (23 dominios) + predicción sintética (municipios sin encuesta)
        + benchmarking en dos niveles → tesis.modelo.fay_herriot_estimaciones_finales
```

### 1. GEIH — ingesta y consolidación

- **Paso previo (local, marco antiguo):** `renombrar_geih.py` renombra los CSV del DANE a
  `<seccion>_<modulo>_<MM>_<AAAA>.csv` antes de subirlos al volumen; `geih_bronce` toma el año y el mes de ese
  nombre. Simula por defecto (`DRY_RUN = True`).
- **Marco antiguo** (hasta 2022): cada módulo viene partido en `area`, `cabecera`, `resto` y trae el módulo de
  **inactivos**; el pipeline carga `cabecera` y `resto`. **Marco nuevo** (2023 en adelante): un archivo por
  módulo, sin inactivos (ya vienen en fuerza de trabajo).
- Cada CSV se lee por separado y se une **por nombre de columna** (los archivos de Ene-Mar 2018 traen otro orden).
- `geih_oro.py` une características generales, fuerza de trabajo, no ocupados, ocupados, el factor de expansión y
  `dim_geih_divipola`, y reconcilia PET/PEA/OC/DS (`reconciliacion_fuerza_trabajo`, `llaves_sin_pareja`).
- `dim_fex` (factores de expansión actualizados) se genera dentro del propio pipeline; en el marco antiguo el
  factor sale solo de `dim_fex`, nunca del `FEX_C_2011`.
- `datos_publicados.py` carga las cifras oficiales del DANE contra las que se valida la estimación directa.

### 2. TerriData — ingesta de covariables (sin capa oro)

`terridata_bronce.py` carga los indicadores; `terridata_plata.py` los pivotea de largo a ancho (una columna por
código de indicador), valida la transformación y genera `tesis.dim.dim_indicadores`.

### 3. Estimación directa (`preprocesamiento/estimacion_directa.py`)

Estima el desempleo por **dominio** (ciudad o ciudad A.M.) sobre la PEA de 15 años y más, en una **ventana** que
cierra en `anio_estimacion/mes_estimacion` (por defecto el año calendario, 12 meses; el trimestre móvil queda como
opción). Usa el estimador de **Hájek** con el factor de expansión y obtiene el error estándar por **bootstrap por
viviendas** dentro de cada dominio (2.000 réplicas, semilla 42), con la linealización de la razón como control. El
CV se clasifica como confiable (< 5 %), aceptable (5–20 %) o no confiable (≥ 20 %). Cada dominio y el agregado se
validan contra la cifra del DANE de la misma ventana. Resultado: `tesis.preprocesamiento.tasa_desempleo_municipal`.

### 4. Selección de covariables

**a) Unión con TerriData** (`adicion_covariables.py`): agrega las covariables municipales al dominio como
x̄_D = Σ zₘ xₘ / Σ zₘ, con **el denominador propio de cada indicador** (`reglas_agregacion.py`), y deja una
auditoría por dominio. Resultado: `tasa_desempleo_covariables`.

**b) Pre-filtrado** (`pre_filtrado_covariables.py`), independiente de la respuesta: se conservan las columnas
completas en los dominios y con variabilidad suficiente (CV y proporción modal). No se filtra por correlación con
la tasa. `dominios_sin_encuesta.py` construye `municipios_sin_encuesta` (Cauca y Valle).

**c) Análisis descriptivo** (`analisis_descriptivo.py`): resuelve el catálogo de literatura (solo variables con
referencia, con signo esperado) y describe los datos; no descarta ninguna covariable.

**d) Selección** (`eda_seleccion_covariables.py`): Fay-Herriot univariado con ψ_d por covariable, elegibilidad por
q de Benjamini-Hochberg, robustez y soporte en los municipios objetivo como diagnósticos (no filtros),
redundancia por enlace completo, y como máximo `n // 10` covariables (2 con 23 dominios) con verificación de VIF.
Resultado: `covariables_seleccionadas` y las tablas de decisión y trazabilidad.

### 5. Modelo Fay-Herriot

**Benchmark clásico** (`modelo/fay_herriot.py`, apoyado en Morales et al., 2021): ajusta el conjunto seleccionado,
todos sus subconjuntos y el modelo de solo intercepto (EC0) con `FayHerriotClasico` (REML, GLS, EBLUP, MSE de
Prasad-Rao con el término g3 de la p. 440; las D_i son las varianzas bootstrap, tratadas como conocidas, p. 427).
Elige el benchmark exigiendo covariables significativas, menor AIC y parsimonia (p. 453). Después:

1. Diagnósticos, Cook y estabilidad de los coeficientes; sensibilidad dejar-un-dominio-fuera y **validación
   predictiva** repitiendo la selección en cada iteración.
2. **Predicción sintética** x'β̂ para los municipios sin encuesta, con aviso de **extrapolación** y **calidad
   reportada** (el CV no distingue a los extrapolados).
3. **Benchmarking en dos niveles** (ajuste de razón): los 23 EBLUP reproducen la directa del conjunto y los
   municipios de un A.M. (Cali y Yumbo) reproducen el EBLUP de su dominio.
4. Tablas finales en `tesis.modelo` (`fay_herriot_estimaciones_finales`, con `MODELO_FUENTE =
   FH_CLASICO_BENCHMARK_NO_ESPACIAL` y `ESTADO_RESULTADO = PRELIMINAR`) y figuras `fh_*` en
   `/Volumes/tesis/modelo/figuras`.

**Variante espacial** (`modelo/fay_herriot_espacial.py`, corre después del clásico): SEBLUP con efectos SAR
(Morales et al., §18.2), matriz W por distancia entre centroides (kNN o distancia inversa) y ρ estimado solo con
los 23 dominios. Se compara con el benchmark con las mismas covariables y ψ_d: I de Moran de los residuos, LRT de
ρ = 0, ΔAIC, perfil de verosimilitud y validación dejar-un-dominio-fuera. Tablas `tesis.modelo.fhe_*` y figuras
`fhe_*`. Detalle y limitaciones en [docs/fay_herriot_espacial.md](docs/fay_herriot_espacial.md).

**Sensibilidad de la varianza** (`modelo/sensibilidad_varianza.py`): evalúa ψ_d alternativas y una GVF sin alterar
el flujo.

---

## Despliegue con Databricks Asset Bundles (DAB)

`databricks.yml` y `dab/` definen siete jobs sobre cómputo serverless (target único `dev`):

| Job | Tareas |
|-----|--------|
| `dimensiones` | `dim_divipola` → `dim_geih_divipola`; `dim_divipola` → `dim_dominio_geih` |
| `ingesta_geih` | `geih_bronce` → `geih_plata` → `geih_oro`; `datos_publicados` (independiente) |
| `ingesta_terridata` | `terridata_bronce` → `terridata_plata` |
| `preprocesamiento` | `estimacion_directa` → `adicion_covariables` → `pre_filtrado_covariables` → `dominios_sin_encuesta` |
| `analisis` | `analisis_descriptivo` → `eda_seleccion_covariables` |
| `modelo` | `fay_herriot` → `fay_herriot_espacial`; `sensibilidad_varianza` (independiente) |
| `pipeline_completo` | Encadena los seis anteriores con `run_job_task` |

El orden es `dimensiones` → `ingesta_geih` / `ingesta_terridata` → `preprocesamiento` → `analisis` → `modelo`;
`pipeline_completo` lo ejecuta de punta a punta. El período llega como variables del bundle `anio_estimacion`
(2018), `mes_estimacion` (12) y `n_meses_ventana` (12 = año, 3 = trimestre móvil). Los volúmenes
`/Volumes/tesis/preprocesamiento/figuras_eda` y `/Volumes/tesis/modelo/figuras` deben existir antes de `analisis`
y `modelo` (el bundle no los crea).

```
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run pipeline_completo -t dev
databricks bundle run preprocesamiento -t dev --params anio_estimacion=2018,mes_estimacion=12,n_meses_ventana=12
```

---

## Entorno de ejecución

Los jobs usan el entorno serverless `environment_version "2"` de Databricks. Versiones registradas
(2026-10-27, también en [requirements.txt](requirements.txt)):

| Componente | Versión |
|------------|---------|
| Python | 3.11.10 |
| numpy / scipy / pandas | 1.23.5 / 1.11.1 / 1.5.3 |
| statsmodels / matplotlib | 0.14.0 / 3.7.2 |
| openpyxl (se instala en `ingesta_geih`) | 3.1.5 |

El código se formatea con **black**.

---

## Fuentes de datos

| Fuente | Descripción |
|--------|-------------|
| **GEIH** (DANE) | Gran Encuesta Integrada de Hogares — microdatos mensuales de mercado laboral |
| **Anexo «Mercado laboral según proyecciones CNPV 2018»** (DANE) | Cifras oficiales para validar la estimación directa |
| **TerriData** (DNP) | Indicadores socioeconómicos territoriales por municipio |
| **DIVIPOLA** (DANE) | Codificación político-administrativa de Colombia |
