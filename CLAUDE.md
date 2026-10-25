# Estimación de desempleo Colombia — SAE

## Contexto del proyecto

Este proyecto usa la **GEIH** (Gran Encuesta Integrada de Hogares, DANE) y **TerriData** (DNP) para construir
un modelo de área pequeña **Fay-Herriot** que estima la tasa de desempleo en municipios de Colombia donde la
GEIH no tiene cobertura muestral directa.

El Fay-Herriot clásico (efectos de área independientes, `modelo/fay_herriot.py`) es el **benchmark no
espacial**: el proyecto **sí incluye variantes espaciales** del Fay-Herriot, que se desarrollan en una rama
aparte y se integrarán a este flujo (ver «Componente espacial»). Mientras no estén mezcladas, las tablas
municipales del clásico son resultados preliminares del benchmark, no las estimaciones finales.

Todo el código corre sobre Databricks (notebooks `.py` con `# Databricks notebook source` / `# COMMAND ----------`)
y persiste en tablas Unity Catalog bajo el catálogo `tesis`. Esquemas: `geih_bronce`, `geih_plata`, `geih_oro`,
`terridata`, `dim`, `preprocesamiento`, `modelo` (y `censo_nal`, que ningún código fuera de `censo_nal/` usa;
`censo_nal/censo_bronce.py` lee cada volumen `/Volumes/tesis/censo_nal/<módulo>` como **Parquet**
—`fallecidos`, `viviendas`, `hogares`, `personas`, `marco_georreferenciacion`—, lista sus archivos y los carga
a `tesis.censo_nal.<módulo>` con la columna `archivo_origen`).
Los jobs se despliegan con un bundle DAB (ver «Despliegue con DAB»).

### Patrón de carpetas: orquestador + `shared/`

`modelo/` y `preprocesamiento/` siguen el mismo patrón: un notebook raíz (`fay_herriot.py`,
`estimacion_directa.py`, `adicion_covariables.py`, `pre_filtrado_covariables.py`, `dominios_sin_encuesta.py`)
actúa como **orquestador fino** que importa la lógica real desde su propia carpeta `shared/`. `analisis/` y
`ingesta_datos/` (`geih/`, `terridata/`) también tienen `shared/`. Al modificar comportamiento, casi siempre el
cambio va en `shared/`, no en el notebook orquestador.

### GEIH: marco antiguo vs. marco nuevo

- **Metodología por período**: la metodología 2016 (DANE, v9) aplica desde 2016 hasta 2022; la metodología
  2023 (DANE, v11) aplica desde 2023 en adelante. La skill `consultar-geih` solo indexa la metodología 2016
  (marco 2005, la que corresponde a los datos de 2018 del proyecto); los documentos del marco 2018 están
  desactivados (ver `DOCUMENTOS_INACTIVOS` en su `ingesta.py`), así que no hay respuesta indexada para 2023+.
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
    estimar la tasa de desempleo; incluye ID_VIVIENDA = PERIODO + DIRECTORIO (G7-B3, conglomerado del
    bootstrap; en 2018 cada DIRECTORIO aparece en un solo mes)
```

`dim_fex` (factores de expansión actualizados del DANE) **no** vive en `dimensiones/`: se genera dentro de
este mismo pipeline (`TBL_FEX_BRONCE`/`TBL_FEX_PLATA` en `geih_config.py`, construida en `geih_plata.py` a
partir de `geih_bronce`); hoy solo cubre 2018. **Factor de expansión en oro (G7-B6,
`shared/transformations/factor_expansion.py`)**: las tablas plata llevan `MARCO` (`NUEVO`/`ANTIGUO`, desde
`campos_nucleo`). En el marco nuevo `FEX_C18` = `FEX` del archivo (ya calibrado con el CNPV 2018); en el
marco antiguo sale solo de `dim_fex`, nunca de `FEX_C_2011` (censo 2005, PET 10+: mezclarlo produce el salto
de serie, `series_geih2005` PDF 19/77). Ya no hay `coalesce(..., 0)`: si alguna persona queda con `FEX_C18`
nulo o ≤ 0, `geih_oro` falla antes de escribir. Con la regla anterior 2018 tenía 0 registros afectados (el
período analítico no cambió) y 2025 los 135.810 (todo 2025 con peso 0).

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
- `dim_dominio_geih.py`: **dominio de estimación** de cada municipio → `tesis.dim.dim_dominio_geih` (52
  filas: una por municipio miembro). El `AREA` de la GEIH identifica la ciudad **con su área
  metropolitana**, no el municipio, así que la tasa directa de «Cali» es la de **Cali A.M.** (coincide con
  la cifra publicada del DANE). Membresía estricta de la GEIH (v9, PDF 9): Medellín A.M. = Valle de Aburrá
  (10 municipios), Barranquilla A.M. = Barranquilla + Soledad, Bucaramanga A.M. (+ Floridablanca, Girón,
  Piedecuesta), Cali A.M. (+ Yumbo), Manizales A.M. (+ Villamaría), Pereira A.M. (+ Dosquebradas, La
  Virginia), Cúcuta A.M. (+ Villa del Rosario, Los Patios, El Zulia); las otras 25 capitales son dominios
  de un municipio. Columnas: `CODIGO_DOMINIO` (DIVIPOLA de la capital), `NOMBRE_DOMINIO` (nombre del anexo
  DANE, «Cali A.M.»), `TIPO_DOMINIO` (`CIUDAD`/`CIUDAD_AM`), `CODIGO_MUNICIPIO`, `ES_CAPITAL`. Los dominios
  de ciudad son urbanos (el `AREA` solo está en cabecera); los registros sin `AREA` (resto de cabeceras y
  rural) **no** se usan, por decisión del proyecto.
- `dim_indicadores` (se crea dentro de `terridata_plata.py` en `tesis.dim`, no en `dimensiones/`):
  diccionario código → nombre descriptivo de cada columna/indicador de `terridata_extendido_plata`.
- `ingesta_datos/geih/datos_publicados.py` (tarea del job `ingesta_geih`): cifras oficiales del anexo DANE
  «Mercado laboral según proyecciones CNPV 2018» → `tesis.geih_bronce.datos_nacionales` y `datos_municipales`
  (23 ciudades y A.M. más «Total 10 ciudades» y «Total 23 ciudades y A.M.», trimestre móvil 2016-2021) y
  `datos_anuales` (hoja «Anuales»: total nacional, cabeceras, rural, «Total 13 ciudades y áreas
  metropolitanas» y «Total 10 ciudades», serie anual 2016-2021; el anexo **no** trae la TD anual por ciudad).
- **Lectura de CSV por nombre de columna** (`shared/utils/spark_utils.leer_csv`): cada archivo se lee
  por separado y se une con `unionByName(allowMissingColumns=True)`. Leer el glob de una vez asignaba las
  columnas por posición, y los archivos Ene-Mar 2018 (marco antiguo) traen otro orden (`AREA` al final, sin
  `MES`): `FT`/`INI` quedaban corridos, la unión con inactivos fallaba y toda la PET quedaba como PEA (TD
  3-8 pp más baja). Corregido (G7-B5).
- **Reconciliación G7-B5** (al final de `geih_oro.py`, lógica en `shared/transformations/reconciliacion.py`,
  solo PASS/FAIL): `tesis.geih_oro.llaves_sin_pareja` (% de llaves de cada módulo sin pareja en
  características generales; inactivos frente a fuerza de trabajo; personas sin FEX) y
  `tesis.geih_oro.reconciliacion_fuerza_trabajo` (por PER/MES/dominio: PET, PEA, PEI, OC, DS y quién rompe
  PEA = OC + DS, PET = PEA + PEI u OC y DS a la vez). 2018: 0 violaciones en los 12 meses y 0 llaves sin
  pareja o duplicadas en todos los módulos. `CG_SIN_FEX` solo revisa el marco antiguo (el único que depende
de `dim_fex`).

### Preprocesamiento → selección de covariables — `code/preprocesamiento/` y `code/analisis/`

```
preprocesamiento/estimacion_directa.py
  → estima el desempleo por dominio (ciudad o ciudad A.M., INNER JOIN con dim_dominio_geih por el código
    de la capital) sobre tesis.geih_oro.mercado_laboral (PEA==1, EDAD ≥ 15, **ventana de n_meses_ventana
    meses** que cierra en anio_estimacion/mes_estimacion, agrupados en un dominio; PER/MES = mes de
    cierre). Ventana por defecto (G7-B2): **año calendario** (12 meses, exige cierre en diciembre;
    `resolver_ventana`); el trimestre móvil (3) queda como opción. Clave: CODIGO_DOMINIO + NOMBRE_DOMINIO
    + TIPO_DOMINIO; agrega PERIODO («Ene-Dic 2018») y N_MESES_VENTANA (viajan en METADATA_COLS hasta el
    modelo, que de ahí sabe contra qué cifra validar), N_PEA y N_DESOCUPADOS (muestra), PEA_EXPANDIDA
    (Σ FEX de la PEA / meses, peso del benchmarking de nivel 1) y N_MUNICIPIOS
  → valida (solo imprime PASS/FAIL) cada dominio y el agregado Σ PEA·TD/Σ PEA contra la cifra DANE de la
    misma ventana (shared/ventana.py, `td_dane_ventana`): año = Σ DS / Σ PEA de los 4 trimestres que no
    se pisan de tesis.geih_bronce.datos_municipales (el anexo no publica la TD anual por ciudad);
    trimestre = la publicada (Oct-Dic 2018: 23/23 y 10.3251 = «Total 23 ciudades y A.M.»)
  → estimador de Hájek (θ̂ = Σ(w_i·y_i)/Σw_i) con el factor de expansión 2018
  → inferencia por bootstrap **por viviendas dentro de cada dominio** (G7-B3, shared/bootstrap.py; 2000
    réplicas, semilla 42, `np.random.default_rng`): remuestrea con reemplazo las viviendas
    (`ID_VIVIENDA` = PERIODO + DIRECTORIO, de geih_oro) del dominio con n fijo y todas sus personas
    (Morales p. 61; GEIH v9 PDF 11: el dominio es de inclusión forzosa y actúa como estrato). Control:
    SE_TAYLOR_PCT (linealización de la razón con las mismas unidades, PDF 15). No reproduce el estrato
    interno ni el segmento (no vienen en los microdatos): **no se afirma que subestime ni que
    sobrestime** la varianza del diseño. `col_conglomerado=None` remuestrea personas (solo para comparar).
    Salida extra: N_VIVIENDAS y SE_TAYLOR_PCT (en METADATA_COLS). CV < 5% confiable, 5–20%
    aceptable, ≥20% no confiable (mismos umbrales que el modelo)
  → lógica en shared/estimador_sae.py (clase EstimacionDirecta, que hereda de la interfaz base
    EstimadorSAE — patrón Template Method/Strategy para futuros estimadores), parámetros en shared/config.py
    → tesis.preprocesamiento.tasa_desempleo_municipal
        ↓
preprocesamiento/adicion_covariables.py
  → agrega TerriData al dominio (shared/agregacion_dominios.py): x̄_D = Σ z_m x_m / Σ z_m sobre los
    municipios miembro, con z = **denominador propio de cada indicador** (shared/reglas_agregacion.py,
    G7-B1): valor agregado para % VA por sector, superficie implícita (pob/densidad) para la densidad,
    población total 010010009 para per cápita, IPM, % urbana, % jóvenes, homicidios, banda ancha
    (exactas), acueducto (proxy) e IDF (convención: índice); población 10-14 / 15-19 para
    coberturas netas, tránsito y Saber 11 (proxy). Fuera del catálogo: PET (15+, EXPR_PESO_POBLACION).
    Toda variable del catálogo debe tener regla (si no, error). NULL si a un miembro le falta el dato;
    error si a un miembro le falta un peso usado. Sustento: Morales p. 425 (x_d = valor del área) y
    p. 21 (razón de totales ΣY/ΣZ); ENUSC 2018 PDF 26 nota 6. Imprime la sensibilidad frente a la
    regla PET en los 7 A.M. y guarda tesis.preprocesamiento.reglas_agregacion_covariables
  → auditoría G7-B1 (shared/auditoria_dominios.py) → tesis.preprocesamiento.auditoria_dominios: una fila
    por dominio con PERIODO/N_MESES_VENTANA, AREA GEIH, nombre DANE (error si no está en el anexo),
    geografía de la tasa (cabeceras) y de las covariables (municipio completo), integrantes + DIVIPOLA,
    regla de x_d y TD directa vs. DANE de la misma ventana (`td_dane_ventana`)
  → LEFT JOIN por CODIGO_DOMINIO, PER = ANO, MES y valida que TerriData cubra el período; excluye las
    columnas *_NORMALIZADO → tesis.preprocesamiento.tasa_desempleo_covariables
        ↓
preprocesamiento/pre_filtrado_covariables.py
  → completitud + variabilidad invariante a escala (CV ≥ CV_MINIMO, proporción modal ≤
    PROP_MODAL_MAXIMA); SIN filtro por correlación con la respuesta; los grupos duplicados
    (|r| ≥ UMBRAL_DUPLICADO) solo se reportan → tesis.preprocesamiento.covariables_prefiltradas
    (+ cascada_prefiltrado, sensibilidad_variabilidad)
  → lógica en shared/feature_selection.py
preprocesamiento/dominios_sin_encuesta.py
  → municipios objetivo de Cauca y Valle (DEPARTAMENTOS_OBJETIVO = [19, 76]) sin estimación directa
    **propia**, con todas las covariables prefiltradas a nivel municipal (sin agregar): excluye solo los
    municipios que forman por sí solos un dominio con muestra (Popayán) y la fila agregada departamental
    (CODIGO_ENTIDAD % 1000 == 0). Cali y Yumbo entran con CODIGO_DOMINIO_PADRE = 76001 (Yumbo NO se
    excluye: recibe estimación propia ajustada a Cali A.M.); falla si falta un miembro de un dominio A.M.
    o si no queda ningún municipio → tesis.preprocesamiento.municipios_sin_encuesta (83 filas en 2018-12)
        ↓
analisis/analisis_descriptivo.py   (lee covariables_prefiltradas + tesis.dim.dim_indicadores)
  → catálogo de literatura (shared/catalogo_literatura.py) → candidatas conceptuales
  → univariado / bivariado / multivariado con interpretación calculada desde los datos
    (shared/descriptivos.py: figura_* + interpretar_*)
  → catalogo_literatura, descriptivo_univariado, descriptivo_bivariado
        ↓
analisis/eda_seleccion_covariables.py
  → 1 asociación (Pearson/Spearman + IC de Fisher como descripción + signo esperado; decide el
    Fay-Herriot univariado con ψ_d = SE² por covariable, diag.fh_univariado, REML + GLS, G7-B8: IC de
    Wald de β1; G7-B13: la misma medida, r ponderada del FH, ordena y fija el signo, y Spearman es solo
    descripción; forma funcional como diagnóstico, diag.forma_funcional: curvatura x² y log vs x por AIC
    ML, sin transformar; la ficha advierte «revisar»)
  → 2 robustez como **diagnóstico, no filtro** (R-03; sobre el FH univariado, G7-B8: Cook 4/n con la
    fórmula de distancia_cook, Â fijo, y dejar-uno-fuera reajustando Â sobre la correlación ponderada por
    1/(Â+ψ_d)): `seleccion.diagnosticar_robustez` lee «depende de un dominio» si Cook > 4/n y el cambio
    dejar-uno-fuera supera UMBRAL_DELTA_LOO (0.10) o invierte el signo; la ficha lo advierte en el motivo
    de las elegibles y NO descarta (antes descartaba 12 de 19 candidatas, 4 con q ≤ 0.10). 4/n es una
    regla para inspeccionar observaciones, no para excluir variables; Morales (pp. 453-454) no usa la
    influencia para seleccionar
  → 2b soporte en los municipios objetivo (R-02, `analisis/shared/soporte_objetivos.py`, sin usar la
    respuesta): proporción de los objetivos dentro de [mín, máx] de los dominios (`Prop_objetivos_en_rango`,
    `Soporte` en la ficha y tabla soporte_covariables); **advertencia**, no filtro, por debajo de
    SOPORTE_MINIMO (0.80, convención propia). La completitud sí es condición del catálogo (iii): una
    candidata con faltantes en `municipios_sin_encuesta` no entra («incompleta en los municipios objetivo»)
  → 3 redundancia (enlace completo: todos los pares del grupo con |r| ≥ 0.80, G7-B10; representante = primer integrante elegible (q de BH del FH ≤ 0.10) por menor Cook máx, con retroceso, G7-B11)
  → 4 ficha de decisión (shared/seleccion.py: ficha_decision): elegible = q de Benjamini-Hochberg del p de β1 del FH, sobre las
      candidatas (18 activas), ≤ Q_FDR_ELEGIBILIDAD (0.10), G7-B9; estabilidad bootstrap de dominios descriptiva
      (REPLICAS_ESTABILIDAD); el signo
      esperado es diagnóstico, no filtro (columna Signo_coherente, G7-B12); seleccionadas = las
      `cota_covariables(n)` = n // 10 (R-07: 2 con 23 dominios; regla de 10 observaciones por parámetro,
      convención externa a Morales, que pide no sobreparametrizar al predecir fuera de muestra, p. 453)
      de mayor |r ponderada|. Si no queda ninguna elegible, `ejecutar_seleccion` lanza
      `SeleccionVaciaError`: el notebook se detiene (modelo solo de intercepto) y la validación cruzada
      del modelo lo trata como un modelo sin covariables
  → 5 verificación VIF (ajustar_por_vif sustituye por la siguiente elegible), residuos parciales del
      conjunto (diag.figura_residuos_parciales, G7-B13) y sensibilidad al signo
      (selección repetida exigiendo el signo → sensibilidad_signo_covariables)
  → (R-32) toda la cadena de pasos 1-5 vive en `analisis/shared/seleccion.ejecutar_seleccion`, que usan
    el notebook y, vía `seleccionar_covariables`, la validación cruzada del modelo; la carga común está
    en `analisis/shared/datos_analisis.cargar_datos_analisis`
  → diagnosticos_covariables (incluye la decisión de robustez, R-63), redundancia_covariables,
    decision_covariables, verificacion_seleccion, trazabilidad_covariables, covariables_seleccionadas
    (ya no se escribe covariables_candidatas ni robustez_covariables; las elegibles no seleccionadas se
    leen en decision_covariables)
        ↓
modelo/fay_herriot.py
  → FayHerriotClasico (shared/fay_herriot.py), MSE de Prasad-Rao con g3 = D²/(D+Â)³·avar(Â)
    (Morales et al., p. 440)
  → (G7-B15) especificaciones candidatas del modelo base Fay-Herriot clásico (EC1…ECk, antes M1–M5; NO son los modelos
    finales del objetivo 1) = conjunto seleccionado (EC1) + dejar-una-fuera (shared/seleccion_modelo.py,
    etiqueta_especificacion)
  → benchmark seleccionado (Morales et al., p. 453; los modelos de área admiten sobreparametrizar, pero
    aquí se predice también fuera de muestra, así que la regla es estricta; el libro admite una covariable
    con p > 0.05 si es interpretable, p. 454, a reportar como excepción): candidatas = especificaciones con todas las
    covariables p < 0.05; entre ellas menor AIC y, entre las equivalentes (ΔAIC ≤ 2), la de menos
    covariables. Si ninguna tiene todas las covariables significativas, compiten todas (imprime aviso).
    MSE y Cook NO deciden: se muestran como ganancia de precisión (CV directo vs EBLUP) y
    robustez (Cook + reajuste sin el dominio más influyente) del benchmark. G7-B16: AICc (AIC + 2k(k+1)/(n−k−1),
    k = p+1; convención externa al libro y aproximación en FH, por D_i heterogéneas) se calcula como complemento (`aicc` en FayHerriotClasico; `AICc`/`Delta_AICc` en
    fh_seleccion_modelo; `AICc` en fh_coeficientes) y NO decide; `redaccion_seleccion` imprime el texto
    «seleccionado entre varias especificaciones con soporte similar, mediante la regla de parsimonia».
    La comparación del
    objetivo 1 es después: benchmark vs. especificaciones espaciales (fay_herriot_espacial.py).
    En el código se conservan los nombres internos `modelo_ganador` / `elegir_ganador`
  → avisos (shared/diagnosticos.py): Â ≈ 0 (γ máx < 0.01), tasas fuera de [0,100]
    (FUERA_DE_RANGO) y extrapolación sintética (EXTRAPOLA = ESTADO_EXTRAPOLACION ≠ DENTRO_DEL_RANGO)
  → extrapolación B20 (celda 10a, shared/extrapolacion.py, cualquier número de covariables; la tasa
    publicada NO cambia): ESTADO_EXTRAPOLACION = FUERA_DEL_RANGO (alguna covariable fuera del
    [mín, máx] de los 23 dominios) / COMBINACION_ATIPICA (todas dentro pero x'Cov(β̂)x > máximo de la
    muestra, Morales p. 441; solo con p ≥ 2) / DENTRO_DEL_RANGO; COVARIABLES_FUERA,
    COVARIABLE_PRINCIPAL (mayor |β̂_j(x_j − x̃_j)|), RAZON_H, PRED_ACOTADA (x̃'β̂ con x recortado al
    rango) y APORTE_EXTRAPOLADO_PP (x'β̂ − x̃'β̂). Sensibilidad: acotada + reajuste quitando cada
    dominio (mín/máx/amplitud y dominio más influyente). Sustento: Benedetti 2024 p. 144, Morales
    p. 441/453, Molina 2019 PDF 40-41. Tablas fh_rangos_covariables y fh_sensibilidad_extrapolacion;
    ESTADO_EXTRAPOLACION y APORTE_EXTRAPOLADO_PP también en prediccion_sintetica y la tabla final
    (entrada de B21)
  → estabilidad de coeficientes del benchmark (shared/estabilidad_coeficientes.py; análisis de
    sensibilidad, no decide): dejar-un-dominio-fuera (reajusta Â) y bootstrap de dominios con la
    especificación fija (ESTABILIDAD_REPLICAS = 1000, semilla 42) → fh_estabilidad_coeficientes (el
    detalle dejar-un-dominio-fuera va solo en fh_loao_coeficientes, R-39). Los mismos 23 dominios filtran, seleccionan y calculan los p, así que
    la significancia es descriptiva y los coeficientes son asociaciones preliminares condicionales a la
    selección (G7-B17: ADVERTENCIA_POST_SELECCION se imprime en el notebook). Ni Morales (pp. 453-454) ni los
    artículos espaciales tratan este punto: es un análisis propio; el bootstrap no repite la selección
  → sensibilidad a dominios individuales, dejar-un-dominio-fuera (LOAO) completo (G7-B18, celda 10a-bis,
    mismo `shared/estabilidad_coeficientes.py`; análisis propio, no decide ni cambia las tasas):
    usa los 23 reajustes del benchmark (con Â) de `reajustes_sin_dominio` (celda 8a, R-39: una sola
    implementación, que también alimentan Cook, B20 y el ejercicio 1 de G7-B19) y reporta (a) por β_j el mínimo y el
    máximo de β̂_j(-d) con el dominio que los produce, el cambio relativo máximo, el **cambio
    estandarizado Δβ/EE(β̂)** (estilo DFBETAS; el porcentual se infla si |β̂| es pequeño), los cambios de
    signo y los cruces de α, los 3 dominios que más mueven cada β y un mapa de calor; (b) el efecto en
    predicciones: EBLUP de los 22 dominios que quedan, predicción sintética de los 83
    municipios (separando los que extrapolan, B20), Â, y cambios de clase de confiabilidad por CV.
    Umbrales (convención propia, `config.py`): `LOAO_UMBRAL_CAMBIO_EE = 1.0` EE y `LOAO_UMBRAL_PRED_PP =
    0.5` pp. Tablas `fh_loao_coeficientes` (con `EE_completo` y `Cambio_en_EE`), `fh_loao_predicciones`
    y `fh_loao_dominios` (tesis.modelo). El error del dominio retirado se mide solo contra la directa,
    en G7-B19. Ni Morales et al. ni los
    artículos espaciales tratan la influencia por dominio; respaldan solo la lectura (en un área fuera
    de muestra el predictor es x'β̂: Benedetti 2024 p. 144; Morales p. 441). Responde a la revisión que
    citaba cambios de ~37 % y ~47 % al retirar Neiva: la tabla dice qué dominio los causa y si superan 1 EE
  → validación predictiva, dejar-un-dominio-fuera con dos ejercicios (G7-B19, celda 10a-ter,
    `modelo/shared/validacion_predictiva.py`; análisis propio, no decide ni cambia las tasas): retira
    cada dominio, ajusta con los otros 22 y lo predice como sin encuesta (x_d'β̂(-d)) frente a su directa.
    (1) **Covariables del benchmark fijas** (solo reajusta β̂ y Â; optimista, la selección vio al dominio
    retirado) y (2) **procedimiento completo**: en cada iteración repite la selección de covariables
    (`analisis/shared/seleccion.seleccionar_covariables`, mismos pasos que `eda_seleccion_covariables`: FH
    univariado con ψ_d, BH, redundancia, parsimonia con la cota calculada desde n, VIF; sobre las 18 candidatas de
    `covariables_prefiltradas`) y la elección del benchmark (`ajustar_benchmark`: conjunto +
    dejar-una-fuera + `elegir_ganador`). La celda comprueba (PASS/FAIL) que con los 23 dominios ambos pasos
    reproducen EC1 y el benchmark. Métricas por ejercicio: RMSE, MAE, sesgo, RMSE corregido por ruido
    (√media(e²−ψ)), errores estandarizados `Z_psi = e/√ψ` y `Z_pred = e/√(ψ + x'Cov(β̂)x + Â)` (media,
    sd, cobertura nominal), error dentro de muestra, y habilidad frente a un modelo de solo intercepto
    evaluado igual. Salidas: `fh_validacion_cruzada` (por dominio y ejercicio),
    `fh_validacion_cruzada_metricas`, `fh_validacion_cruzada_seleccion` (qué elige cada iteración) y
    `fh_validacion_cruzada_frecuencia`. El pre-filtrado no se repite (no usa la respuesta). Con n = 23 son
    23 predicciones: orden de magnitud. Morales et al. no tratan la validación cruzada por área; respaldan
    solo la lectura (p. 441). `fay_herriot_espacial.py` ya hacía un LOAO con covariables fijas para
    comparar clásico y espacial; el ejercicio 1 lo reproduce para el clásico.
  → D_i = varianza bootstrap por viviendas tratada como conocida (p. 427), sin suavizar con GVF. La GVF
    y otras D_i solo se evalúan en modelo/sensibilidad_varianza.py. La validación predictiva
    dejar-un-área-fuera (G7-B19) está permitida: no hay restricción del proyecto contra ella
  → figuras solo en pantalla (sin título y sin guardarse en volúmenes)
  → clave de dominio PER_MES_CODIGO_DOMINIO; etiquetas = NOMBRE_DOMINIO («Cali A.M.»)
  → benchmarking en dos niveles, ajuste de razón de Fay-Herriot (1979) (shared/benchmarking.py, con la
    sustentación completa: DANE nota SAE 2024 PDF 8/19/25, ENUSC 2018 PDF 22-23, Chile pobreza 2016,
    Casen 2024, Molina 2019 PDF 26/78, Benedetti 2024 p. 159, Morales p. 42/425/462):
      9b nivel 1: los 23 EBLUP × λ₁ para que Σ PEA_EXPANDIDA·EBLUP/Σ PEA reproduzca la directa del
         conjunto (= «Total 23 ciudades y A.M.» del DANE en la ventana N_MESES_VENTANA de la tabla:
         reconstruido con los 4 trimestres si es el año; se detiene si difiere > 0.01 pp)
      10b nivel 2: los municipios de un dominio A.M. (Cali y Yumbo) × λ_D para que, ponderados por la
         población de 15 años y más, reproduzcan el EBLUP ajustado de su dominio (imprime la brecha
         de agregación x̄_D'β̂ vs Σw·x_m'β̂/Σw, porque las covariables no usan la PET). Los otros 81
         municipios quedan con el sintético puro (el departamento es representativo en el año, pero su
         directa exige los registros sin AREA, que el proyecto no usa; nivel 3 = extensión posible)
      12 verificación: tablas antes/después y pruebas (consistencia < 1e-8, razones conservadas, rango,
         miembros completos; aviso si |λ−1| > 0.20) + comprobación sobre la tabla final redondeada
    λ fijo: RMSE × λ, CV sin cambio
  → fh_diagnosticos_variantes, fh_cook y fh_seleccion_modelo (solo si hay más de una variante),
    fh_coeficientes, fay_herriot_resultados (con EBLUP_BENCHMARK y LAMBDA_N1),
    fay_herriot_prediccion_sintetica (con LAMBDA_N2 y PRED_BENCHMARK), fay_herriot_estimaciones_finales
    (tesis.modelo; NIVEL = DOMINIO [23] o MUNICIPIO [83], TIPO = EBLUP_BENCHMARK / SINTETICO /
    SINTETICO_BENCHMARK, TASA_SIN_AJUSTE_PCT para trazabilidad; R-11: MODELO_FUENTE =
    FH_CLASICO_BENCHMARK_NO_ESPACIAL y ESTADO_RESULTADO = PRELIMINAR, más COMMENT ON TABLE); la
    sensibilidad de Cook se muestra pero no se persiste. R-38: todas las tablas se registran en
    `EscrituraDiferida` (shared/escritura.py) y la celda 13 las escribe después de la verificación
  → R-10: Shapiro-Wilk y la media de residuos se redactan con `diagnosticos.lectura_normalidad` /
    `NOTA_MEDIA_RESIDUOS` (no demuestran normalidad; la media es ≈ 0 por construcción); R-64: sin prueba
    de Wilcoxon ni % de dominios que mejoran (MSE < Di por construcción, p. 440); R-41:
    FayHerriotClasico guarda convergio_reml/convergio_ml/A_en_cota y los reajustes solo absorben
    LinAlgError
  → calidad reportada B21 (celda 11a, shared/consolidacion.py): CONFIABILIDAD sigue siendo solo por CV;
    BASE_CV = EBLUP (dominios) / CONDICIONAL_AL_MODELO (municipios) y CALIDAD_REPORTADA = la que se cita:
    en municipios agrega siempre «condicional al modelo» (el MSE x'Cov(β̂)x + Â supone el modelo
    correcto, Morales p. 3/441; Molina 2019 PDF 37/41) y «extrapolado (fuera del rango | combinación
    atípica)» si ESTADO_EXTRAPOLACION ≠ DENTRO_DEL_RANGO; ningún municipio queda «Aceptable» a secas.
    Se recalcula con el modelo ganador (sin cifras fijas); un estado nuevo sin texto en
    SUFIJO_EXTRAPOLACION hace fallar la tabla. resumen_calidad / interpretar_calidad muestran que el CV
    no distingue a los extrapolados (CV = RMSE / tasa: ambos suben). Las tasas y CV no cambian
modelo/sensibilidad_varianza.py   (G7-B3, fuera de la cadena: no alimenta al modelo)
  → ψ_d alternativas con los mismos microdatos (preparar_datos_ventana + EstimacionDirecta): bootstrap
    por personas y Taylor; comprueba que el bootstrap por viviendas recalculado reproduce la tabla
  → GVF A log ψ = b0 + b1·y + b2·n (Morales p. 427/454-455) y GVF B log ψ = b0 + b1·log(p(1−p)) +
    b2·log n (deff: Téllez 2020 p. 15, Chile 2016 PDF 4), retransformadas con Δ = Σψ/Σexp(x'α̂)
    (ENUSC 2018 PDF 15-16); R², residuos y figura observada vs predicha. GVF = solo escenario
  → escenarios: base, personas, Taylor, GVF A/B y ψ × k (k ∈ {1/3, 1/2, 2/3, 3/2, 2, 3}, simétrica en
    log). En cada uno reajusta las variantes y elige ganador con la misma regla; compara con la
    especificación de referencia (ganador base): Â/ψ̄ (Benedetti 2024 p. 143), γ, β̂ y p, EBLUP, CV y
    confiabilidad, λ₁ y predicción sintética de los 83 municipios
  → sensibilidad_varianza_directa, gvf_ajuste, sensibilidad_varianza_fh, sensibilidad_varianza_coeficientes,
    sensibilidad_varianza_dominios, sensibilidad_varianza_municipios (tesis.modelo)
  → 2018: ψ_viviendas/ψ_personas mediana 1.08 (1.00–1.17); bootstrap/Taylor 0.94–1.05; GVF R² 0.97 (A) y
    0.976 (B, pendientes ≈ +1 y −1 = forma binomial, deff implícito ≈ 1.2). En los 11 escenarios el
    ganador (IICA_CONFLICTO) y su significancia no cambian, Â/ψ̄ ≥ 15, γ ≥ 0.88, EBLUP cambia ≤ 0.19 pp y
    la predicción sintética ≤ 0.11 pp; solo con ψ × 3 pasan 4 dominios de confiable a aceptable
```

Lógica compartida en `analisis/shared/`: `catalogo_literatura.py` (`CATALOGO_LITERATURA`,
`CATALOGO_EXCLUIDAS`, `resolver_catalogo`), `descriptivos.py` (figuras e interpretaciones),
`diagnosticos.py` (IC de Fisher, FH univariado con ψ_d y su Cook y dejar-uno-fuera (G7-B8), forma funcional y
residuos parciales (G7-B13), VIF, figura de robustez; R-31 quitó las versiones OLS),
`seleccion.py` (`diagnosticar_robustez`, `resolver_redundancia`, `ficha_decision`, `ajustar_por_vif`),
`ventana_temporal.py` (sensibilidad G7-B2; re-exporta `etiqueta_ventana`, `cierres_trimestrales` y
`td_dane_ventana`, que viven en `preprocesamiento/shared/ventana.py` porque los usan la estimación directa,
la auditoría y el modelo).

`analisis/sensibilidad_ventana_temporal.py` (G7-B2, fuera de la cadena: no alimenta al modelo) compara la
tasa directa de los 23 dominios con tres ventanas que cierran en `anio_estimacion/mes_estimacion`
(`VENTANAS_TEMPORALES`: MES = 1, TRIMESTRE = 3, ANIO = 12; `meses_ventana` en `preprocesamiento/shared/config.py`).
Es la evidencia de la decisión G7-B2 (año como ventana del modelo: 23/23 confiables, SE ≈ la mitad del trimestral).
Reutiliza `EstimacionDirecta`, pero define la PEA como `OCUPADO + DESOCUPADO` (defensa ante la bandera rota de Ene-Mar
2018, ya corregida; hoy ambas definiciones coinciden) y comprueba que la ventana con el `N_MESES_VENTANA` de
`tasa_desempleo_municipal` (la del modelo) la reproduce. La TD anual oficial por
ciudad se reconstruye como Σ DS / Σ PEA de los 4 trimestres que no se pisan (MES 3/6/9/12 de
`datos_municipales`); la fórmula reproduce el Total 13 y el Total 10 de `datos_anuales` (≈ 1e-5 pp). Salidas:
`sensibilidad_ventana_temporal` (ventana × dominio, con N_PERSONAS_15MAS/N_PEA/N_DESOCUPADOS y TD_DANE),
`resumen_ventana_temporal`, `validacion_anual_totales` y la figura `ventana_sensibilidad`.

Lógica compartida en `modelo/shared/`: `config.py` (tablas fuente/destino —las compartidas y los
umbrales de CV 5/20 se importan de `preprocesamiento/shared/config.py`, R-40/R-59—,
`DELTA_AIC_EQUIVALENTE`, `ALFA_SIGNIFICANCIA`, `UMBRAL_GAMMA_SIN_PESO`, límites de tasa, avisos),
`modelo_area_pequena.py` (interfaz base ModeloAreaPequena: matriz de diseño, comparación de MSE, tabla de
resultados — común a cualquier variante SAE; `prediccion_sintetica`, única fórmula x'β̂ y x'Cov(β̂)x + Â),
`datos_modelo.py` (R-40/R-63: `periodo_unico`, `alias_desde_catalogo`, `preparar_municipios`),
`escritura.py` (`escribir_tabla`, `EscrituraDiferida`), `fay_herriot.py` (FayHerriotClasico: REML, GLS, EBLUP, MSE de
Prasad-Rao con g3 de la p. 440, AIC por ML), `seleccion_modelo.py` (variantes dejar-una-fuera, tabla de
diagnósticos, Cook, tabla de selección y ganador), `diagnosticos.py` (gráficas de validación sin GVF, CV
directo vs EBLUP, avisos), `sensibilidad_varianza.py` (G7-B3: `ajustar_gvf`, `escenarios_psi`,
`ajustar_escenarios`, figuras e interpretación), `estabilidad_coeficientes.py` (`reajustes_sin_dominio`, el único LOAO del clásico, R-39;
`resumen_ajustes`; dejar-uno-fuera y bootstrap de coeficientes; G7-B18:
`dejar_uno_fuera_predicciones`, `resumen_influencia_dominios`, `top_dominios_por_parametro`,
`interpretar_influencia`, `figura_influencia`), `validacion_predictiva.py` (G7-B19: `ajustar_benchmark`, `crear_selector`,
`loao_covariables_fijas`, `loao_procedimiento_completo`, `metricas_validacion_cruzada`, `frecuencia_seleccion`,
`interpretar_validacion`, `figura_validacion`), `benchmarking.py` (`factor_razon`, `benchmark_nivel1`, `benchmark_nivel2`, `brecha_agregacion`,
`verificar_benchmark`; funciones puras numpy/pandas con doctests), `extrapolacion.py` (B20:
`rangos_covariables`, `estado_extrapolacion`, `prediccion_acotada`, `sensibilidad_quitar_dominio`,
figuras e interpretación; doctests con 1 y 2 covariables), `consolidacion.py` (tabla final de dos
niveles —dominio y municipio—, clasificación de confiabilidad y, B21, `etiqueta_calidad`,
`resumen_calidad`, `interpretar_calidad`; doctests).

### Componente espacial del Fay-Herriot — `modelo/fay_herriot_espacial.py`

```
modelo/fay_herriot_espacial.py   (corre después de fay_herriot.py: lee tesis.modelo.fh_coeficientes)
  → mismas covariables que el benchmark clásico seleccionado; SEBLUP con efectos SAR u = ρWu + v (Morales et al.,
    §18.2, pp. 490-494); W por DISTANCIA entre centroides (kNN k=3/5 o distancia inversa 1/2), nunca por
    contigüidad: los 23 dominios son ciudades dispersas y los objetivos no son contiguos a ellas
  → ρ se estima solo con los 23 dominios; W (estructura "completa") cubre dominios + objetivos y evalúa la
    verosimilitud marginal de los dominios (MML de Benedetti 2024, pp. 146-149, ecs. 18-20; NO es el
    estimador de Saei-Chambers); estructura "muestra" = W solo entre dominios. R-13: la prueba principal de ρ
    es la de "muestra"; el ρ̂ de "completa" es condicional al conjunto de nodos sin dato (tabla
    fhe_sensibilidad_rho_objetivos) y no se interpreta su signo
  → R-14: los municipios de un dominio A.M. (Cali, Yumbo; CODIGO_DOMINIO_PADRE) NO son nodos de W: se
    predicen como subáreas del nodo, x'β̂ + û_D (shared/prediccion_espacial.py), y pasan por benchmark_nivel1
    (los EBLUP del espacial) y benchmark_nivel2 (mismos pesos de PET que el clásico). Se predicen los mismos 83
    municipios del clásico (81 nodos con MSE bootstrap + 2 subáreas con MSE del sintético)
  → diagnósticos: I de Moran de los residuos del clásico y del SEBLUP con la misma estandarización (R-12; mapa
    de residuos), LRT de ρ=0, ΔAIC, perfil de verosimilitud de ρ, validación dejar-un-dominio-fuera con las
    mismas métricas del clásico (Z_psi, Z_pred, cobertura, habilidad frente al modelo nulo; es optimista con
    covariables fijas, R-15); B20 con la Cov(β̂) del espacial (ESTADO_EXTRAPOLACION) y B21 (etiqueta_calidad);
    MSE por bootstrap paramétrico (500 réplicas, p. 494)
  → criterio (R-43): espacial preferido solo si p(LRT) < 0.05 en la estructura "muestra"; ΔAIC = LRT − 2 es el
    mismo estadístico (se reporta, no es otro respaldo); un ρ̂ en la cota (0.99) no es referencia
  → R-42: el nodo de un A.M. se ubica en su capital; fhe_sensibilidad_centroide compara con la media de sus
    municipios miembro. k y la potencia de ESCENARIOS_W se justifican en config.py
  → tesis.modelo.fhe_* (moran, vecindad, comparacion_modelos, cuadro_comparativo, perfil_rho,
    validacion_cruzada[_metricas], coeficientes, coeficientes_comparacion [R-16], sensibilidad_centroide,
    sensibilidad_rho_objetivos, prediccion_objetivo) y figuras fhe_*.png en VOLUMEN_FIGURAS_MODELO
    (/Volumes/tesis/modelo/figuras, R-45)
```

Lógica en `modelo/shared/`: `matriz_proximidad.py` (Haversine, kNN, distancia inversa, estandarización por
filas, `moran_i`, `proximidad_total`, `filas_moran`), `fay_herriot_espacial.py` (`FayHerriotEspacial`, hija
de `ModeloAreaPequena`; `validacion_dejar_uno_fuera`), `figuras_espacial.py`, `figuras.py` (guardado común
del clásico `fh_*` y del espacial `fhe_*`), `prediccion_espacial.py`, `sensibilidad_espacial.py`,
`cuadro_comparativo.py` (también `construir_cuadro_coeficientes`); parámetros en `config.py` (`ESCENARIOS_W`,
`RHO_LIMITE`, `BOOTSTRAP_ESPACIAL_REPLICAS`, `ALFA_LRT`). Resultado con el cierre 2018 (corrida de `test-2`,
23 dominios, 82 objetivos): **sin evidencia de dependencia espacial** — Moran de los residuos p entre 0.82 y
0.91; ρ̂ entre 0.11 y 0.39 (completa) sin significancia (LRT p ≥ 0.60); ΔAIC entre −1.09 y −2.00 (el clásico
tiene menor AIC en los 8 casos); perfil de ρ plano (ganancia ≤ 0.22); RMSE dejar-un-dominio-fuera: clásico
2.084 frente a 2.115-2.440 del espacial con efecto. El efecto espacial en los objetivos es casi nulo (media
absoluta 0.05 pp) y 74 de 82 objetivos extrapolan. El modelo recomendado sigue siendo el clásico (benchmark);
detalle, tablas, comparación con el cierre anterior y limitaciones en `docs/fay_herriot_espacial.md`.
Las cifras de este párrafo son del cierre previo a los cambios del bloque 05 (R-12…R-16, R-42, R-43, R-45):
quedan pendientes de la nueva corrida (R-44). Ojo: en `municipios_sin_encuesta` figura Cali (76001), que ya
es dominio con encuesta; desde R-14 el notebook espacial ya no la excluye: Cali y Yumbo son subáreas del nodo
Cali A.M. y los objetivos son los mismos 83 del clásico. `marca_extrapolacion` (B20) recibe la matriz de
diseño de los objetivos (`X_obj`), no `x'Cov(β̂)x`.

### Flujo de tablas Unity Catalog (resumen end-to-end)

```
GEIH bronce → GEIH plata → GEIH oro (tesis.geih_oro.mercado_laboral)
                                  ↓            tesis.dim.dim_dominio_geih (ciudad / ciudad A.M.)
                                  ↓            tesis.geih_bronce.datos_municipales (cifras DANE)
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
  dato utilizable quedan en `CATALOGO_EXCLUIDAS` con su motivo (hoy 6; los motivos son distintos: sin dato en
  los dominios con encuesta, serie terminada en 2016, solo departamental, ausente en los municipios objetivo,
  solo 2022-2023 y el IICA). El catálogo activo tiene 18 entradas. **El IICA (260020003) salió del catálogo
  (R-01)**: mide la incidencia del conflicto en el propio municipio, no la recepción de desplazados del
  argumento de Ibáñez (2008); r = 0.92 con homicidios, 13 valores distintos por redondeo y fuera de rango en
  33 de 83 objetivos. No se sustituyó por otra covariable (`020100002`, migrantes internos, queda como
  posibilidad no adoptada). Las justificaciones usan lenguaje de asociación, no causal (R-35; Díaz 2016,
  p. 155). La tasa de tránsito a educación superior se conserva por decisión del proyecto.
- **Moran y AIC permitidos**: el índice de Moran (sobre residuos del benchmark y de las variantes espaciales)
  y el AIC pueden usarse donde corresponda, incluido el EDA. La comparación entre especificaciones del
  clásico se hace en `modelo/fay_herriot.py`.
- **Componente espacial** (variantes espaciales del FH; el código vive en otra rama y se integrará a
  `modelo/`). Requisitos de la revisión del Grupo 7 (`Comentarios Grupo 7.pdf`, sec. 7-9):
  - la matriz W se construye sobre las unidades reales de la respuesta (un dominio A.M. es un solo nodo),
    con la vecindad o distancia justificada;
  - comparación controlada FH clásico vs espacial: misma respuesta, mismos ψ_d, mismos dominios y mismas
    covariables congeladas; una comparación «mejor clásico vs mejor espacial» va aparte;
  - Moran global y mapa de residuos del benchmark y de la variante espacial (I_base vs I_espacial), junto
    con el desempeño predictivo y la incertidumbre;
  - el predictor de los municipios sin muestra se deriva de la formulación espacial, no como sintético
    más una corrección ad hoc; las mismas herramientas de validación, extrapolación (B20) y calidad
    reportada (B21) se aplican a las dos variantes.
- **Distancia de Cook en el FH**: `distancia_cook(modelo)` en `modelo/shared/seleccion_modelo.py` la calcula
  sobre el ajuste GLS con `Â` fijo (`r_i² h_ii / (p (1-h_ii)²)`, `h_ii = x_i' Cov(β̂) x_i /(D_i+Â)`).
- Parámetros en `preprocesamiento/shared/config.py` (`BOOTSTRAP_REPLICAS`/`BOOTSTRAP_SEED`, umbrales de CV,
  `CV_MINIMO`, `PROP_MODAL_MAXIMA`, `UMBRAL_DUPLICADO`, `UMBRAL_REDUNDANCIA`, `UMBRAL_DELTA_LOO`,
  `ALFA_IC_CORRELACION`, `Q_FDR_ELEGIBILIDAD`, `REPLICAS_ESTABILIDAD`, `cota_covariables`/`OBS_POR_PARAMETRO`, `SOPORTE_MINIMO`, `VIF_MAXIMO`, `DEPARTAMENTOS_OBJETIVO`) y `modelo/shared/config.py`
  (tablas, `DELTA_AIC_EQUIVALENTE`, `ALFA_SIGNIFICANCIA`).
- **Dominio = ciudad o ciudad A.M.** en preprocesamiento, análisis y modelo (`CODIGO_DOMINIO`,
  `NOMBRE_DOMINIO`, `TIPO_DOMINIO`); `CODIGO_MUNICIPIO`/`MUNICIPIO` solo existen en las tablas de municipios
  objetivo. En la tabla final un mismo código puede ser dominio y municipio (76001 = Cali A.M. y Cali): la
  clave es NIVEL + CODIGO.
- **Importaciones**: los notebooks de `analisis/` (y `pre_filtrado_covariables.py`, `dominios_sin_encuesta.py`,
  `adicion_covariables.py`) importan por ruta completa desde `code/` (`preprocesamiento.shared.config`,
  `analisis.shared.…`) porque existen varias carpetas `shared/` y la forma corta resolvería a una u otra según
  desde dónde se ejecute. `estimacion_directa.py` también (antes usaba la forma corta). `modelo/fay_herriot.py`
  usa la forma corta para `modelo/shared` y la completa para `preprocesamiento.shared.ventana`.
- Las figuras del análisis van al volumen `/Volumes/tesis/preprocesamiento/figuras_eda`
  (prefijos `desc_`, `eda_`). Las del modelo (R-45) se muestran y se guardan en
  `VOLUMEN_FIGURAS_MODELO` = `/Volumes/tesis/modelo/figuras` (prefijos `fh_` clásico y `fhe_` espacial,
  `shared/figuras.guardar_figura`).
- **Advertencia al cambiar la ventana de tiempo** (`anio_estimacion` / `mes_estimacion` / `n_meses_ventana`):
  si cambia el número de dominios, la cota de covariables se recalcula sola (`cota_covariables(n)` = n // 10). Los
  textos de los notebooks dicen "23 dominios" y la exclusión "sin dato para 2018" del catálogo también es del
  cierre 2018. La ventana anual (12) exige `mes_estimacion = 12`; con el trimestre (3) y otro cierre, la unión
  con TerriData por (ANO, MES) puede quedar vacía porque los indicadores tienen corte a diciembre.

## Despliegue con DAB

`databricks.yml` + `dab/resources/*.yml` + `dab/targets/dev.yml` definen un bundle con un único target `dev`
(cómputo serverless, `environment_version "2"`, `max_concurrent_runs: 1`; sin `mode: development` para que los
jobs no lleven prefijo). Seis jobs, cada uno una cadena lineal de tareas notebook (`../../code/...`):

| Job | Tareas |
|-----|--------|
| `dimensiones` | `dim_divipola` → `dim_geih_divipola`; `dim_divipola` → `dim_dominio_geih` |
| `ingesta_geih` | `geih_bronce` → `geih_plata` → `geih_oro`; `datos_publicados` (independiente) |
| `ingesta_terridata` | `terridata_bronce` → `terridata_plata` |
| `preprocesamiento` | `estimacion_directa` → `adicion_covariables` → `pre_filtrado_covariables` → `dominios_sin_encuesta` |
| `analisis` | `analisis_descriptivo` → `eda_seleccion_covariables` (R-37: `sensibilidad_ventana_temporal` salió del job; se corre a mano) |
| `modelo` | `fay_herriot` → `fay_herriot_espacial`; `sensibilidad_varianza` (independiente) |

- Entre jobs no hay dependencias en el YAML; el orden real es `dimensiones` → `ingesta_geih` /
  `ingesta_terridata` → `preprocesamiento` → `analisis` → `modelo`.
- El período llega como variables del bundle `anio_estimacion` (default "2018"), `mes_estimacion` (default
  "12") y `n_meses_ventana` (default "12" = año; "3" = trimestre móvil); solo `preprocesamiento` los declara
  como parámetros. `resolver_periodo` (`preprocesamiento/shared/config.py`) lee los dos primeros en
  `estimacion_directa` y `dominios_sin_encuesta`; `resolver_ventana` lee la ventana solo en
  `estimacion_directa`, y de ahí viaja en la columna `N_MESES_VENTANA`. Ejemplo (trimestre Abr-Jun 2024):
  `databricks bundle run preprocesamiento -t dev --params anio_estimacion=2024,mes_estimacion=6,n_meses_ventana=3`.
- El bundle no crea volúmenes: `/Volumes/tesis/preprocesamiento/figuras_eda` debe existir antes de `analisis` y
  `/Volumes/tesis/modelo/figuras` antes de `modelo` (si falta, las figuras se muestran pero no se guardan).
- `sync.exclude` omite `data/`, `code/ingesta_datos/censo_nal/`, `code/analisis/renombrar_geih.py` y los
  `*.txt`, `*.xlsx`, `*.pdf` (archivos de trabajo de la raíz; `TerriData.txt` de ~3 GB rompía el despliegue).
- Para correr una sola tarea: `databricks bundle run <job> -t dev --only <task_key>`.
- `modelo/fay_herriot.py` resuelve `CODE_DIR` con `dbutils` para poder correr como job.
- Detalles de cómo ejecutar jobs en este workspace: ver la memoria `project_flujo_rev_decisiones`.

## Estándares de código

- **Siempre** usar docstrings en funciones, clases y métodos. El docstring debe especificar: tipo de dato
  de entrada, tipo de dato de salida, explicación de los argumentos y casos de uso.
- Formatear el código con **black**.
