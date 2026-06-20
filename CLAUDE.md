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
    diseño muestral; CV < 15% confiable, 15–30% aceptable, ≥30% no confiable
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
        ↓
code/modelo/fay_herriot.py
  → ajusta y compara modelos Fay-Herriot clásicos (clase FayHerriotClasico en shared/fay_herriot.py, que
    hereda de la interfaz base ModeloAreaPequena en shared/modelo_area_pequena.py — pensada para futuras
    variantes SAE como espacial o temporal) sobre distintos subconjuntos de covariables
  → selecciona el ganador por AIC + BIC + MSE medio + RMSE-LOOCV (shared/seleccion_modelo.py)
  → EBLUP para dominios con encuesta directa; predicción sintética (ŷ = X'β̂, sin shrinkage) para
    municipios sin cobertura GEIH
  → consolida tabla final EBLUP + sintético (shared/consolidacion.py)
```

Lógica compartida en `modelo/shared/`: `config.py` (nombres de tablas, sets de covariables a comparar),
`modelo_area_pequena.py` (interfaz base ModeloAreaPequena: construcción de matriz de diseño, LOOCV,
comparación de MSE, armado de tabla de resultados — común a cualquier variante SAE),
`fay_herriot.py` (FayHerriotClasico: ajuste del modelo, diagnósticos, LOOCV), `seleccion_modelo.py` (tablas
de diagnóstico y selección entre modelos), `diagnosticos_plot.py` (gráficas de validación),
`consolidacion.py` (unión EBLUP + sintético).

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
                                  ↓
                          fay_herriot.py → EBLUP + predicción sintética + tabla final consolidada
                                          (tesis.modelo.fay_herriot_*)
```

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
