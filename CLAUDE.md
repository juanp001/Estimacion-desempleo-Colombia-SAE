# Estimación de desempleo Colombia — SAE

## Contexto del proyecto

Este proyecto usa la **GEIH** (Gran Encuesta Integrada de Hogares, DANE) y **TerriData** (DNP) para construir
un modelo de área pequeña **Fay-Herriot** que estima la tasa de desempleo en municipios de Colombia donde la
GEIH no tiene cobertura muestral directa.

Todo el código corre sobre Databricks (notebooks `.py` con `# Databricks notebook source` / `# COMMAND ----------`)
y persiste en tablas Unity Catalog bajo el catálogo `tesis` (esquemas `tesis.geih`, `tesis.terridata`,
`tesis.dim`, `tesis.preprocesamiento`, `tesis.modelo`, `tesis.censo_nal`).

### Patrón de carpetas: orquestador + `shared/`

`modelo/` y `preprocesamiento/` siguen el mismo patrón: un notebook raíz (`fay_herriot.py`,
`estimacion_directa.py`, `adicion_covariables.py`, `pre_filtrado_covariables.py`) actúa como **orquestador
fino** que importa la lógica real desde su propia carpeta `shared/`. Al modificar comportamiento, casi
siempre el cambio va en `shared/`, no en el notebook orquestador.

### GEIH: marco antiguo vs. marco nuevo

- **Marco antiguo** (hasta 2022): cada módulo viene partido en tres archivos — `area`, `cabecera`, `resto`.
  Incluye el módulo de **inactivos**.
- **Marco nuevo** (2023 en adelante): un solo archivo por módulo, sin la partición área/cabecera/resto.
  No trae módulo de inactivos — esa información ya viene integrada en **fuerza de trabajo**.
- Módulos trabajados: `características generales`, `ocupados`, `no ocupados`, `fuerza de trabajo`,
  `inactivos` (solo marco antiguo).

### Pipeline GEIH (esquema medallón) — `code/ingesta_datos/geih/`

```
geih_bronce.py
  → carga archivos crudos, transformaciones mínimas
geih_plata.py
  → consolida marco antiguo + marco nuevo por módulo (área/cabecera/resto → unificado), transformaciones
    de negocio
geih_oro.py
  → junta características generales + fuerza de trabajo + no ocupados + ocupados + factores de expansión
    + dim_divipola → tabla de mercado laboral lista para estimar la tasa de desempleo
```

`dim_fex` (factores de expansión actualizados del DANE) **no** vive en `dimensiones/`: se genera dentro de
este mismo pipeline (`TBL_FEX_BRONCE`/`TBL_FEX_PLATA` en `geih_config.py`, construida en `geih_plata.py` a
partir de `geih_bronce`). Usable para años ≤ 2018 si se quiere el factor nuevo; para los demás años los
archivos ya traen el factor de expansión de 2018.

Lógica compartida en `geih/shared/`: `config/geih_config.py` (nombres de tablas, constantes),
`transformations/campos_nucleo.py` (columnas núcleo comunes a marco antiguo/nuevo), `utils/spark_utils.py`
(escritura a Unity Catalog).

### Pipeline TerriData (sin capa oro) — `code/ingesta_datos/terridata/`

```
terridata_bronce.py
  → carga el archivo de indicadores de TerriData tal cual
terridata_plata.py
  → pivotea de largo a ancho (una columna por código de indicador DANE) → futuras covariables
  → valida que la transformación a ancho quedó correcta (conteo de filas, verificación cruzada)
  → genera dim_indicadores (código → nombre descriptivo)
```

Lógica compartida en `terridata/shared/`: `config/terridata_config.py`, `transformations/normalizacion.py`
(normalización de texto/nombres), `utils/spark_utils.py` y `utils/verification_utils.py` (validaciones de
la transformación a ancho).

### Dimensiones — `code/ingesta_datos/dimensiones/`

- `dim_divipola.py`: nomenclatura DIVIPOLA de los municipios de Colombia.
- `dim_geih_divipola.py`: traduce las áreas de la GEIH a su municipio/código DIVIPOLA correcto (lee
  `tesis.dim.dim_divipola`).
- `dim_indicadores` (se crea dentro de `terridata_plata.py`, no en `dimensiones/`): diccionario
  código → nombre descriptivo de cada columna/indicador de `terridata_plata` extendido.

### Preprocesamiento → selección de covariables — `code/preprocesamiento/`

```
estimacion_directa.py
  → estima el desempleo por dominio (municipio) sobre tesis.geih_oro.mercado_laboral (filtrado a PEA==1,
    período objetivo)
  → estimador de Hájek (θ̂ = Σ(w_i·y_i)/Σw_i) con el factor de expansión 2018
  → inferencia por bootstrap simple (2000 réplicas, semilla fija) porque no se tienen las variables del
    diseño muestral; CV < 5% confiable, 5–20% aceptable, ≥20% no confiable (mismos umbrales que
    el modelo)
  → lógica en shared/estimador_sae.py (clase EstimacionDirecta, que hereda de la interfaz base
    EstimadorSAE — patrón Template Method/Strategy para futuros estimadores), parámetros en shared/config.py
        ↓
adicion_covariables.py
  → une las estimaciones directas con las covariables de TerriData plata
        ↓
pre_filtrado_covariables.py
  → filtro previo: sin NAs, varianza casi cero, |Pearson| ≥ umbral con la tasa de desempleo
  → lógica de selección en shared/feature_selection.py
        ↓
code/analisis/Análisis exploratorio.py
  → análisis exploratorio (7 etapas) sobre el dataset pre-filtrado: sensibilidad al umbral, filtro
    cualitativo por literatura, descriptivos + normalidad, correlación con IC bootstrap, influencia de
    outliers (Cook's D + LOO), estructura espacial (Moran's I), ranking compuesto → covariables ganadoras
```

El modelo Fay-Herriot (`code/modelo/fay_herriot.py`) ya no consume la salida de este EDA original sino la
del flujo `_rev` (ver más abajo).

Lógica compartida en `modelo/shared/`: `config.py` (tablas fuente/destino, umbrales de CV 5/20,
`DELTA_AIC_EQUIVALENTE`, `ALFA_SIGNIFICANCIA`, avisos), `modelo_area_pequena.py` (interfaz base
ModeloAreaPequena: matriz de diseño, comparación de MSE, tabla de resultados — común a cualquier variante
SAE), `fay_herriot.py` (FayHerriotClasico: REML, GLS, EBLUP, MSE de Prasad-Rao con g3 de la p. 440, AIC
por ML), `seleccion_modelo.py` (variantes dejar-una-fuera, tabla de diagnósticos, Cook, tabla de selección
y ganador), `diagnosticos.py` (gráficas de validación sin GVF, CV directo vs EBLUP, avisos),
`consolidacion.py` (unión EBLUP + sintético y clasificación de confiabilidad).

### Flujo de tablas Unity Catalog (resumen end-to-end)

```
GEIH bronce → GEIH plata → GEIH oro (tesis.geih_oro.mercado_laboral)
                                  ↓
TerriData bronce → TerriData plata (covariables anchas) ──┐
                                                            ↓
                          estimacion_directa → tesis.modelo.tasa_desempleo_municipal
                                  ↓
                          adicion_covariables → pre_filtrado_covariables
                                  ↓
                          tesis.preprocesamiento.covariables_prefiltradas
                                  ↓
                          Análisis exploratorio.py → tesis.preprocesamiento.covariables_seleccionadas

(flujo _rev) … → tesis.preprocesamiento.covariables_seleccionadas_rev
                                  ↓
                          fay_herriot.py → EBLUP + predicción sintética + tabla final consolidada
                                          (tesis.modelo.fay_herriot_*, tesis.modelo.fh_*)
```

### Flujo revisado (`_rev`) — selección cualitativa de covariables

En preprocesamiento y análisis coexiste con el flujo original sin tocarlo: los notebooks y módulos llevan
sufijo `_rev` (o viven en `analisis/shared_rev/`), y escriben tablas `_rev`. Los módulos originales
(`preprocesamiento/shared/feature_selection.py`, `config.py`) **no se modifican**; cualquier cambio de
comportamiento va en los archivos `_rev` / `shared_rev`. El **modelo** ya no tiene versión `_rev`: el
antiguo `fay_herriot_rev` pasó a ser `modelo/fay_herriot.py` (el FH original y sus módulos se eliminaron)
y escribe tablas sin sufijo.

```
preprocesamiento/pre_filtrado_covariables_rev.py
  → completitud + variabilidad invariante a escala (CV, proporción modal); SIN filtro por correlación
    con la respuesta → tesis.preprocesamiento.covariables_prefiltradas_rev
preprocesamiento/dominios_sin_encuesta_rev.py
  → municipios objetivo de Cauca y Valle sin estimación directa, con todas las covariables prefiltradas
    → tesis.preprocesamiento.municipios_sin_encuesta_rev
        ↓
analisis/analisis_descriptivo_rev.py
  → catálogo de literatura (shared_rev/catalogo_literatura.py) → candidatas conceptuales
  → univariado / bivariado / multivariado con interpretación calculada desde los datos
    (shared_rev/descriptivos.py: figura_* + interpretar_*)
  → catalogo_literatura_rev, descriptivo_univariado_rev, descriptivo_bivariado_rev
        ↓
analisis/eda_seleccion_covariables_rev.py
  → 1 asociación (Pearson/Spearman + IC de Fisher + signo esperado)
  → 2 robustez (Cook 4/n + dejar-uno-fuera sobre los 23 dominios)
  → 3 redundancia (|r| ≥ 0.80, representante = menor Cook máx)
  → 4 ficha de decisión (shared_rev/seleccion.py: ficha_decision): elegible = IC sin cero y signo
      coherente con el mecanismo; seleccionadas = las P_MAXIMO (4) de mayor |r|
  → 5 verificación VIF (ajustar_por_vif sustituye por la siguiente elegible)
  → decision_covariables_rev, trazabilidad_covariables_rev, covariables_candidatas_rev (elegibles),
    covariables_seleccionadas_rev
        ↓
modelo/fay_herriot.py
  → FayHerriotClasico (shared/fay_herriot.py), MSE de Prasad-Rao con g3 = D²/(D+Â)³·avar(Â)
    (Morales et al., p. 440)
  → variantes = conjunto seleccionado + dejar-una-fuera (shared/seleccion_modelo.py)
  → ganador (Morales et al., p. 453): candidatas = variantes con todas las covariables p < 0.05;
    entre ellas menor AIC y, entre las equivalentes (ΔAIC ≤ 2), la de menos covariables.
    MSE y Cook NO deciden: se muestran como ganancia de precisión (CV directo vs EBLUP) y
    robustez (Cook + reajuste sin el dominio más influyente) del ganador
  → avisos (shared/diagnosticos.py): Â ≈ 0 (γ máx < 0.01), tasas fuera de [0,100]
    (FUERA_DE_RANGO) y extrapolación sintética (EXTRAPOLA: x'Cov(β̂)x > máximo de la muestra)
  → D_i = varianza bootstrap tratada como conocida (p. 427), sin GVF ni figuras GVF; sin validación
    cruzada
  → figuras solo en pantalla (sin título y sin guardarse en volúmenes)
  → fh_diagnosticos_variantes, fh_seleccion_modelo, fh_cook, fh_coeficientes, fay_herriot_resultados,
    fay_herriot_prediccion_sintetica, fay_herriot_estimaciones_finales (tesis.modelo)
```

Reglas del flujo `_rev`:

- **Catálogo de literatura**: solo entran variables con referencia en el documento de revisión de
  literatura del proyecto (`compass_artifact_*.md`), resueltas a su código en `tesis.terridata.terridata_bronce`,
  con dato 2018, que superen el pre-filtrado y estén completas en los municipios objetivo. Cada entrada
  trae `signo_esperado` y `referencia`; **no existe nivel de respaldo L**. Las variables del documento sin
  dato utilizable quedan en `CATALOGO_EXCLUIDAS` con su motivo. IICA es el proxy documentado de
  «víctimas/desplazamiento»; la tasa de tránsito a educación superior se conserva por decisión del proyecto.
- **Sin AIC en el EDA, sin Moran en ningún notebook**: el Fay-Herriot es clásico (efectos independientes)
  y no se ajustan variantes espaciales, así que la autocorrelación espacial no cambia ninguna decisión.
  La comparación entre especificaciones se hace solo en `modelo/fay_herriot.py`.
- **Distancia de Cook en el FH**: `distancia_cook(modelo)` en `modelo/shared/seleccion_modelo.py` la calcula
  sobre el ajuste GLS con `Â` fijo (`r_i² h_ii / (p (1-h_ii)²)`, `h_ii = x_i' Cov(β̂) x_i /(D_i+Â)`).
- Parámetros en `preprocesamiento/shared/config_rev.py` (umbrales, tablas `_rev`, `P_MAXIMO`, `VIF_MAXIMO`)
  y `modelo/shared/config.py` (tablas, `DELTA_AIC_EQUIVALENTE`, `ALFA_SIGNIFICANCIA`).
- Las figuras del análisis `_rev` van al volumen `/Volumes/tesis/preprocesamiento/figuras_eda`
  (prefijos `desc_`, `eda_`); las del modelo no se guardan.

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
