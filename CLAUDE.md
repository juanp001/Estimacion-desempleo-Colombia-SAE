# Estimación de desempleo Colombia — SAE

## Contexto del proyecto

Este proyecto usa la **GEIH** (Gran Encuesta Integrada de Hogares, DANE) y **TerriData** (DNP) para construir
un modelo de área pequeña **Fay-Herriot** que estima la tasa de desempleo en municipios de Colombia donde la
GEIH no tiene cobertura muestral directa.

Todo el código corre sobre Databricks (notebooks `.py` con `# Databricks notebook source` / `# COMMAND ----------`)
y persiste en tablas Unity Catalog bajo el catálogo `tesis`. Esquemas: `geih_bronce`, `geih_plata`, `geih_oro`,
`terridata`, `dim`, `preprocesamiento`, `modelo` (y `censo_nal`, que ningún código fuera de `censo_nal/` usa).
Los jobs se despliegan con un bundle DAB (ver «Despliegue con DAB»).

### Patrón de carpetas: orquestador + `shared/`

`modelo/` y `preprocesamiento/` siguen el mismo patrón: un notebook raíz (`fay_herriot.py`,
`estimacion_directa.py`, `adicion_covariables.py`, `pre_filtrado_covariables.py`, `dominios_sin_encuesta.py`)
actúa como **orquestador fino** que importa la lógica real desde su propia carpeta `shared/`. `analisis/` y
`ingesta_datos/` (`geih/`, `terridata/`) también tienen `shared/`. Al modificar comportamiento, casi siempre el
cambio va en `shared/`, no en el notebook orquestador.

### GEIH: marco antiguo vs. marco nuevo

- **Marco antiguo** (hasta 2022): cada módulo viene partido en tres archivos — `area`, `cabecera`, `resto`.
  Incluye el módulo de **inactivos**.
- **Marco nuevo** (2023 en adelante): un solo archivo por módulo, sin la partición área/cabecera/resto.
  No trae módulo de inactivos — esa información ya viene integrada en **fuerza de trabajo**.
  (La división por años es una convención de las carpetas de origen; el código no filtra por año.)
- Módulos trabajados: `características generales`, `ocupados`, `no ocupados`, `fuerza de trabajo`,
  `inactivos` (solo marco antiguo).

### Pipeline GEIH (esquema medallón) — `code/ingesta_datos/geih/`

```
geih_bronce.py   → tesis.geih_bronce.*
  → carga archivos crudos desde /Volumes/tesis/geih_bronce, transformaciones mínimas
geih_plata.py    → tesis.geih_plata.*_consolidado + dim_fex
  → consolida marco antiguo + marco nuevo por módulo (área/cabecera/resto → unificado), transformaciones
    de negocio
geih_oro.py      → tesis.geih_oro.mercado_laboral
  → LEFT JOIN desde características generales hacia fuerza de trabajo + no ocupados + ocupados +
    factores de expansión (dim_fex) + tesis.dim.dim_geih_divipola → tabla de mercado laboral lista para
    estimar la tasa de desempleo
```

`dim_fex` (factores de expansión actualizados del DANE) **no** vive en `dimensiones/`: se genera dentro de
este mismo pipeline (`TBL_FEX_BRONCE`/`TBL_FEX_PLATA` en `geih_config.py`, construida en `geih_plata.py` a
partir de `geih_bronce`). Usable para años ≤ 2018 si se quiere el factor nuevo; para los demás años los
archivos ya traen el factor de expansión de 2018. Ojo: `geih_oro` toma `FEX_C18` solo de `dim_fex` con
`coalesce(..., 0)`, así que si `dim_fex` no cubre un período el factor queda en 0.

Lógica compartida en `geih/shared/`: `config/geih_config.py` (nombres de tablas, constantes),
`transformations/campos_nucleo.py` (columnas núcleo comunes a marco antiguo/nuevo), `utils/spark_utils.py`
(escritura a Unity Catalog).

### Pipeline TerriData (sin capa oro) — `code/ingesta_datos/terridata/`

```
terridata_bronce.py
  → carga los Parquet de indicadores (volumen terridata_archivos/consolidado) y agrega columnas
    *_NORMALIZADO → tesis.terridata.terridata_bronce
terridata_plata.py
  → pivotea de largo a ancho (una columna por código de indicador DANE) → futuras covariables
    → tesis.terridata.terridata_extendido_plata
  → valida la transformación a ancho (conteo de filas, duplicados, muestra aleatoria, casteo,
    reclasificación); las validaciones solo imprimen PASS/FAIL y NO detienen la escritura;
    la verificación pesada está apagada (EJECUTAR_VALIDACIONES_PESADAS = False, fijo en el notebook)
  → genera tesis.dim.dim_indicadores (código → nombre descriptivo)
```

Lógica compartida en `terridata/shared/`: `config/terridata_config.py`, `transformations/normalizacion.py`
(normalización de texto/nombres), `utils/spark_utils.py` y `utils/verification_utils.py` (validaciones de
la transformación a ancho).

### Dimensiones — `code/ingesta_datos/dimensiones/`

- `dim_divipola.py`: nomenclatura DIVIPOLA de los municipios de Colombia (`tesis.dim.dim_divipola`).
- `dim_geih_divipola.py`: filtra `dim_divipola` a una lista fija de 32 áreas GEIH (capital de cada
  departamento incluido; Bogotá D.C. como `11001`) y agrega `CODIGO_AREA_GEIH`, que es solo el
  `CODIGO_DEPARTAMENTO` (no un mapeo real de áreas) → `tesis.dim.dim_geih_divipola`. `geih_oro` usa esta
  tabla (constante `TBL_DIM_DIVIPOLA`), no `dim_divipola`; fuera de esas 32 áreas `MUNICIPIO` y
  `DEPARTAMENTO` quedan NULL.
- `dim_indicadores` (se crea dentro de `terridata_plata.py` en `tesis.dim`, no en `dimensiones/`):
  diccionario código → nombre descriptivo de cada columna/indicador de `terridata_extendido_plata`.

### Preprocesamiento → selección de covariables — `code/preprocesamiento/` y `code/analisis/`

```
preprocesamiento/estimacion_directa.py
  → estima el desempleo por dominio (municipio) sobre tesis.geih_oro.mercado_laboral (filtrado a
    MUNICIPIO no nulo, PEA==1, trimestre móvil objetivo: los 3 meses que cierran en
    anio_estimacion/mes_estimacion, agrupados en un dominio; PER/MES = mes de cierre)
  → estimador de Hájek (θ̂ = Σ(w_i·y_i)/Σw_i) con el factor de expansión 2018
  → inferencia por bootstrap simple (2000 réplicas, semilla 42) porque no se tienen las variables del
    diseño muestral; remuestrea las n filas globales, no por dominio. CV < 5% confiable, 5–20%
    aceptable, ≥20% no confiable (mismos umbrales que el modelo)
  → lógica en shared/estimador_sae.py (clase EstimacionDirecta, que hereda de la interfaz base
    EstimadorSAE — patrón Template Method/Strategy para futuros estimadores), parámetros en shared/config.py
    → tesis.preprocesamiento.tasa_desempleo_municipal
        ↓
preprocesamiento/adicion_covariables.py
  → une las estimaciones directas con tesis.terridata.terridata_extendido_plata (LEFT JOIN por
    CODIGO_MUNICIPIO = CODIGO_ENTIDAD, PER = ANO, MES) y valida que TerriData cubra el período
    → tesis.preprocesamiento.tasa_desempleo_covariables
        ↓
preprocesamiento/pre_filtrado_covariables.py
  → completitud + variabilidad invariante a escala (CV ≥ CV_MINIMO, proporción modal ≤
    PROP_MODAL_MAXIMA); SIN filtro por correlación con la respuesta; los grupos duplicados
    (|r| ≥ UMBRAL_DUPLICADO) solo se reportan → tesis.preprocesamiento.covariables_prefiltradas
    (+ cascada_prefiltrado, sensibilidad_variabilidad)
  → lógica en shared/feature_selection.py
preprocesamiento/dominios_sin_encuesta.py
  → municipios objetivo de Cauca y Valle (DEPARTAMENTOS_OBJETIVO = [19, 76]) sin estimación directa, con
    todas las covariables prefiltradas; excluye la fila agregada departamental (CODIGO_ENTIDAD % 1000 == 0)
    y falla (ValueError) si no queda ningún municipio
    → tesis.preprocesamiento.municipios_sin_encuesta
        ↓
analisis/analisis_descriptivo.py   (lee covariables_prefiltradas + tesis.dim.dim_indicadores)
  → catálogo de literatura (shared/catalogo_literatura.py) → candidatas conceptuales
  → univariado / bivariado / multivariado con interpretación calculada desde los datos
    (shared/descriptivos.py: figura_* + interpretar_*)
  → catalogo_literatura, descriptivo_univariado, descriptivo_bivariado
        ↓
analisis/eda_seleccion_covariables.py
  → 1 asociación (Pearson/Spearman + IC de Fisher + signo esperado; el IC de Fisher que decide la
    elegibilidad es siempre de Pearson, y r_interpretable ordena y fija el signo)
  → 2 robustez (Cook 4/n + dejar-uno-fuera sobre los 23 dominios): se descarta solo si Cook > 4/n y el
    cambio dejar-uno-fuera supera UMBRAL_DELTA_LOO (0.10) o invierte el signo
  → 3 redundancia (|r| ≥ 0.80, representante = menor Cook máx)
  → 4 ficha de decisión (shared/seleccion.py: ficha_decision): elegible = IC sin cero y signo
      coherente con el mecanismo; seleccionadas = las P_MAXIMO (4) de mayor |r|
  → 5 verificación VIF (ajustar_por_vif sustituye por la siguiente elegible)
  → diagnosticos_covariables, robustez_covariables, redundancia_covariables, decision_covariables,
    verificacion_seleccion, trazabilidad_covariables, covariables_candidatas (elegibles),
    covariables_seleccionadas
        ↓
modelo/fay_herriot.py
  → FayHerriotClasico (shared/fay_herriot.py), MSE de Prasad-Rao con g3 = D²/(D+Â)³·avar(Â)
    (Morales et al., p. 440)
  → variantes = conjunto seleccionado + dejar-una-fuera (shared/seleccion_modelo.py)
  → ganador (Morales et al., p. 453): candidatas = variantes con todas las covariables p < 0.05;
    entre ellas menor AIC y, entre las equivalentes (ΔAIC ≤ 2), la de menos covariables. Si ninguna
    variante tiene todas las covariables significativas, compiten todas (imprime aviso).
    MSE y Cook NO deciden: se muestran como ganancia de precisión (CV directo vs EBLUP) y
    robustez (Cook + reajuste sin el dominio más influyente) del ganador
  → avisos (shared/diagnosticos.py): Â ≈ 0 (γ máx < 0.01), tasas fuera de [0,100]
    (FUERA_DE_RANGO) y extrapolación sintética (EXTRAPOLA: x'Cov(β̂)x > máximo de la muestra)
  → D_i = varianza bootstrap tratada como conocida (p. 427), sin GVF ni figuras GVF; sin validación
    cruzada
  → figuras solo en pantalla (sin título y sin guardarse en volúmenes)
  → fh_diagnosticos_variantes, fh_cook y fh_seleccion_modelo (solo si hay más de una variante),
    fh_coeficientes, fay_herriot_resultados, fay_herriot_prediccion_sintetica,
    fay_herriot_estimaciones_finales (tesis.modelo); la sensibilidad de Cook se muestra pero no se persiste
```

Lógica compartida en `analisis/shared/`: `catalogo_literatura.py` (`CATALOGO_LITERATURA`,
`CATALOGO_EXCLUIDAS`, `resolver_catalogo`), `descriptivos.py` (figuras e interpretaciones),
`diagnosticos.py` (IC de Fisher, Cook por covariable, estabilidad dejar-uno-fuera, VIF, figura de robustez),
`seleccion.py` (`filtrar_por_robustez`, `resolver_redundancia`, `ficha_decision`, `ajustar_por_vif`).

Lógica compartida en `modelo/shared/`: `config.py` (tablas fuente/destino, umbrales de CV 5/20,
`DELTA_AIC_EQUIVALENTE`, `ALFA_SIGNIFICANCIA`, `UMBRAL_GAMMA_SIN_PESO`, límites de tasa, avisos),
`modelo_area_pequena.py` (interfaz base ModeloAreaPequena: matriz de diseño, comparación de MSE, tabla de
resultados — común a cualquier variante SAE), `fay_herriot.py` (FayHerriotClasico: REML, GLS, EBLUP, MSE de
Prasad-Rao con g3 de la p. 440, AIC por ML), `seleccion_modelo.py` (variantes dejar-una-fuera, tabla de
diagnósticos, Cook, tabla de selección y ganador), `diagnosticos.py` (gráficas de validación sin GVF, CV
directo vs EBLUP, avisos), `consolidacion.py` (unión EBLUP + sintético y clasificación de confiabilidad).

### Flujo de tablas Unity Catalog (resumen end-to-end)

```
GEIH bronce → GEIH plata → GEIH oro (tesis.geih_oro.mercado_laboral)
                                  ↓
TerriData bronce → TerriData plata (tesis.terridata.terridata_extendido_plata, covariables anchas) ──┐
                                                            ↓
                          estimacion_directa → tesis.preprocesamiento.tasa_desempleo_municipal
                                  ↓
                          adicion_covariables → tesis.preprocesamiento.tasa_desempleo_covariables
                                  ↓
                          pre_filtrado_covariables → tesis.preprocesamiento.covariables_prefiltradas
                                  ↓
                          analisis_descriptivo + eda_seleccion_covariables
                                  → tesis.preprocesamiento.covariables_seleccionadas
                                  ↓
                          fay_herriot.py → EBLUP + predicción sintética + tabla final consolidada
                                          (tesis.modelo.fay_herriot_*, tesis.modelo.fh_*)
```

Reglas del flujo de selección:

- **Catálogo de literatura**: solo entran variables con referencia en el documento de revisión de
  literatura del proyecto (`compass_artifact_*.md`), resueltas a su código en `tesis.terridata.terridata_bronce`,
  con dato 2018, que superen el pre-filtrado y estén completas en los municipios objetivo. Cada entrada
  trae `signo_esperado` y `referencia`; **no existe nivel de respaldo L**. Las variables del documento sin
  dato utilizable quedan en `CATALOGO_EXCLUIDAS` con su motivo (hoy 5; los motivos son distintos: sin dato en
  los dominios con encuesta, serie terminada en 2016, solo departamental, ausente en los municipios objetivo
  o solo 2022-2023). El catálogo activo tiene 19 entradas. IICA es el proxy documentado de
  «víctimas/desplazamiento»; la tasa de tránsito a educación superior se conserva por decisión del proyecto.
- **Sin AIC en el EDA, sin Moran en ningún notebook**: el Fay-Herriot es clásico (efectos independientes)
  y no se ajustan variantes espaciales, así que la autocorrelación espacial no cambia ninguna decisión.
  La comparación entre especificaciones se hace solo en `modelo/fay_herriot.py`.
- **Distancia de Cook en el FH**: `distancia_cook(modelo)` en `modelo/shared/seleccion_modelo.py` la calcula
  sobre el ajuste GLS con `Â` fijo (`r_i² h_ii / (p (1-h_ii)²)`, `h_ii = x_i' Cov(β̂) x_i /(D_i+Â)`).
- Parámetros en `preprocesamiento/shared/config.py` (`BOOTSTRAP_REPLICAS`/`BOOTSTRAP_SEED`, umbrales de CV,
  `CV_MINIMO`, `PROP_MODAL_MAXIMA`, `UMBRAL_DUPLICADO`, `UMBRAL_REDUNDANCIA`, `UMBRAL_DELTA_LOO`,
  `ALFA_IC_CORRELACION`, `P_MAXIMO`, `VIF_MAXIMO`, `DEPARTAMENTOS_OBJETIVO`) y `modelo/shared/config.py`
  (tablas, `DELTA_AIC_EQUIVALENTE`, `ALFA_SIGNIFICANCIA`).
- **Importaciones**: los notebooks de `analisis/` (y `pre_filtrado_covariables.py` / `dominios_sin_encuesta.py`)
  importan por ruta completa desde `code/` (`preprocesamiento.shared.config`, `analisis.shared.…`) porque
  existen varias carpetas `shared/` y la forma corta resolvería a una u otra según desde dónde se ejecute.
  `estimacion_directa.py` y `adicion_covariables.py` todavía usan la forma corta (`from shared.config import *`);
  es una inconsistencia conocida, no la repliques en código nuevo.
- Las figuras del análisis van al volumen `/Volumes/tesis/preprocesamiento/figuras_eda`
  (prefijos `desc_`, `eda_`); las del modelo no se guardan.
- **Advertencia al cambiar la ventana de tiempo** (`anio_estimacion` / `mes_estimacion`): si cambia el
  número de dominios, hay que revisar `P_MAXIMO = 4` a mano, porque asume 23 dominios (n/5). Los textos de
  los notebooks dicen "23 dominios" y la exclusión "sin dato para 2018" del catálogo también es del cierre
  2018.

## Despliegue con DAB

`databricks.yml` + `dab/resources/*.yml` + `dab/targets/dev.yml` definen un bundle con un único target `dev`
(cómputo serverless, `environment_version "2"`, `max_concurrent_runs: 1`; sin `mode: development` para que los
jobs no lleven prefijo). Seis jobs, cada uno una cadena lineal de tareas notebook (`../../code/...`):

| Job | Tareas |
|-----|--------|
| `dimensiones` | `dim_divipola` → `dim_geih_divipola` |
| `ingesta_geih` | `geih_bronce` → `geih_plata` → `geih_oro` |
| `ingesta_terridata` | `terridata_bronce` → `terridata_plata` |
| `preprocesamiento` | `estimacion_directa` → `adicion_covariables` → `pre_filtrado_covariables` → `dominios_sin_encuesta` |
| `analisis` | `analisis_descriptivo` → `eda_seleccion_covariables` |
| `modelo` | `fay_herriot` |

- Entre jobs no hay dependencias en el YAML; el orden real es `dimensiones` → `ingesta_geih` /
  `ingesta_terridata` → `preprocesamiento` → `analisis` → `modelo`.
- El período llega como variables del bundle `anio_estimacion` (default "2018") y `mes_estimacion` (default
  "12"); solo `preprocesamiento` los declara como parámetros y los lee `resolver_periodo`
  (`preprocesamiento/shared/config.py`) en `estimacion_directa` y `dominios_sin_encuesta`. Ejemplo:
  `databricks bundle run preprocesamiento -t dev --params anio_estimacion=2024,mes_estimacion=6`.
- El bundle no crea volúmenes: `/Volumes/tesis/preprocesamiento/figuras_eda` debe existir antes de `analisis`.
- `sync.exclude` omite `data/`, `code/ingesta_datos/censo_nal/` y `code/analisis/renombrar_geih.py`.
- `modelo/fay_herriot.py` resuelve `CODE_DIR` con `dbutils` para poder correr como job.
- Detalles de cómo ejecutar jobs en este workspace: ver la memoria `project_flujo_rev_decisiones`.

## Estándares de código

- **Siempre** usar docstrings en funciones, clases y métodos. El docstring debe especificar: tipo de dato
  de entrada, tipo de dato de salida, explicación de los argumentos y casos de uso.
- Formatear el código con **black**.

## Archivos a ignorar siempre

- `code/ingesta_datos/censo_nal/`
- `code/analisis/Análisis exploratorio 2.py`
- `code/analisis/analisis_exploratorio.md`
- `code/analisis/explicacion_diferencia_fay_herriot.txt`
- `code/analisis/Metodologia Selecicon covariables Ver 2.0.py`
- `code/analisis/renombrar_geih.py`

(En el repo actual solo existen `censo_nal/` y `renombrar_geih.py`; los demás ya no están versionados.)
