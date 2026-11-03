# Avance de la reescritura (partes 1 y 2)

## Último paso hecho

2026-11-03 (parte 1, sesión 1): respaldo, auditoría de citas, corrección de `refs.bib` y
reescritura completa de `marco-teorico.tex`. **Esperando confirmación del equipo sobre el Marco
teórico** antes de seguir con Antecedentes.

2026-11-03: el equipo confirmó el Marco teórico tal como está (sin mover ecuaciones al apéndice;
ΔAIC ≤ 2 queda como convención propia, sin citar a Burnham y Anderson). Se reescribió
`antecedentes.tex` (bloques de la directora atendidos y eliminados: siglas y cita [9]).

2026-11-03: Antecedentes confirmado por el equipo. Se reescribió `datos.tex` con cifras leídas por SQL
(ver `inventario_cifras.md` §2b). Se eliminó la sección del CNPV 2018 como base de microdatos: la
ingesta del censo se borró (R-55) y ningún código la usaba; el CNPV 2018 aparece solo como base de los
factores de expansión y de las proyecciones de población de TerriData.

2026-11-03: Datos confirmado. Se reescribió `metodologia.tex` (16 etapas con ficha, diagrama general
`img/met_flujo_general.png` generado con `img/_script/diagrama_metodologia.py`, tabla etapa → objetivo).
Para la etapa 13 se agregaron al Marco teórico la Ecuación `eq:gamma_esp` (peso de la directa en el
SEBLUP) y una frase sobre la estandarización de residuos para Moran (regla 6).

PARTE 1 CERRADA (2026-11-03): los cuatro capítulos confirmados por el equipo.

Siguiente paso (parte 2): extraer los notebooks a `_trabajo/notebooks/`, ejecutar los cálculos propios
C1-C4 y escribir Resultados con los títulos y etiquetas de la tabla de abajo.

2026-11-03 (parte 2, sesión 1): notebooks extraídos a `notebooks/` (Markdown, `salidas/` sin código y 39
figuras en `fig/`, script `calculos/extraer_notebooks.py`). Tablas descargadas con SELECT de solo lectura
(`calculos/descargar_tablas.py` → `calculos/datos/`). Cálculos propios C1-C4 ejecutados
(`calculos/comparacion_espacial.py`; C1 reproduce ρ̂ = 0.372 y σ̂²_u = 4.825). Inventario completado
(§3b y §4). Figuras: 22 copiadas de los notebooks a `img/` (las `desc_*`, `eda_*`, `fh_ganador_*`
reemplazadas por las de la corrida vigente) y 2 nuevas (`img/_script/figuras_resultados.py`:
`res_espacial_estimaciones.png`, `res_mapa_municipios.png`). Se reescribió `resultados.tex`.
**Esperando confirmación del equipo sobre Resultados** antes de seguir con Discusión.

## Estado por capítulo

| Capítulo | Estado | Páginas estimadas | Presupuesto |
|---|---|---|---|
| Marco teórico (`marco-teorico.tex`) | Confirmado por el equipo (2026-11-03): se deja como está, sin mover ecuaciones al apéndice | ≈ 19-21 (5,350 palabras, 45 ecuaciones, 2 tablas grandes) | 16 (se pasa ≈ 4; compensar en otros capítulos) |
| Antecedentes (`antecedentes.tex`) | Confirmado | ≈ 3.8 (1 tabla grande, `tab:antecedentes`) | 4 |
| Datos (`datos.tex`) | Confirmado | ≈ 6.5-7 (6 tablas: fuentes, módulos, dominios, anexo, estructura TerriData, covariables) | 6 |
| Metodología (`metodologia.tex`) | Confirmado | ≈ 17-19 (2,300 palabras, 1 figura, 18 tablas de ficha) | 18 |
| Resultados (`resultados.tex`) | Confirmado (2026-11-03) | ≈ 26-31 (4,300 palabras, 21 tablas, 9 figuras; el verificador da 31 contando cada tabla con tabularx como página completa) | 26 |
| Discusión (`discusion.tex`) | Confirmado (2026-11-03) | ≈ 5.2 (1,700 palabras, 1 tabla) | 5 |
| Conclusiones (`conclusiones.tex`) | Confirmado (2026-11-03) | ≈ 2.1 (850 palabras) | 3 |
| Introducción (`introduction.tex`) | Confirmada (2026-11-03) | ≈ 1.8 (720 palabras) | 2 |
| Apéndice (`appendice.tex`) | Confirmado (2026-11-03) | ≈ 40 (no cuenta) | no cuenta |
| Resumen (`docs/sommario.tex`) | Confirmado (2026-11-03) | ≈ 1 (395 palabras, un párrafo) | dentro de las 8 de portada e índices |
| Definición del problema (`planteamiento-problema.tex`, `formulacion-problema.tex`) | Confirmado (2026-11-03) | ≈ 3.4 (950 palabras, 1 tabla) | 3 |

## Respaldo

- `_respaldo_2026-11-03/` (chapters, refs.bib, main.tex). El `_respaldo_2026-11-02/` existente estaba vacío
  (solo una carpeta `chapters/` sin archivos).

## Decisiones tomadas en la parte 1

- Esquema de etiquetas de etapas: `sec:met_<etapa>` en Metodología y `sec:res_<etapa>` en Resultados.
  Las etiquetas definitivas (para el espejo):

| # | Título exacto de la etapa | Metodología | Resultados |
|---|---|---|---|
| 1 | Obtención de los datos | `sec:met_obtencion` | `sec:res_obtencion` |
| 2 | Limpieza, estandarización y consolidación | `sec:met_limpieza` | `sec:res_limpieza` |
| 3 | Tratamiento de datos faltantes y valores atípicos | `sec:met_faltantes` | `sec:res_faltantes` |
| 4 | Definición de los dominios de estimación y correspondencia geográfica | `sec:met_dominios` | `sec:res_dominios` |
| 5 | Estimación directa de la tasa de desempleo | `sec:met_directa` | `sec:res_directa` |
| 6 | Construcción y agregación de las covariables | `sec:met_covariables` | `sec:res_covariables` |
| 7 | Pre-filtrado de covariables | `sec:met_prefiltrado` | `sec:res_prefiltrado` |
| 8 | Análisis descriptivo | `sec:met_descriptivo` | `sec:res_descriptivo` |
| 9 | Selección de covariables | `sec:met_seleccion` | `sec:res_seleccion` |
| 10 | Ajuste y selección del modelo Fay-Herriot clásico (benchmark) | `sec:met_fh_clasico` | `sec:res_fh_clasico` |
| 11 | Validación de supuestos y sensibilidad del benchmark | `sec:met_supuestos` | `sec:res_supuestos` |
| 12 | Validación predictiva dejar-un-dominio-fuera | `sec:met_validacion` | `sec:res_validacion` |
| 13 | Modelo Fay-Herriot espacial y comparación con el benchmark | `sec:met_espacial` | `sec:res_espacial` |
| 14 | Estimación en los municipios sin cobertura muestral | `sec:met_sin_muestra` | `sec:res_sin_muestra` |
| 15 | Benchmarking y consolidación de las estimaciones | `sec:met_benchmarking` | `sec:res_benchmarking` |
| 16 | Distribución y patrones espaciales de las estimaciones | `sec:met_patrones` | `sec:res_patrones` |

  (Los títulos pueden ajustarse al escribir Metodología; esta tabla se actualiza entonces y es la que
  manda.)

- Siglas en español, y las de término inglés siempre con el formato «(SIGLA, por sus siglas en inglés)»:
  SAE, EBLUP, GLS, RMSE, MAE, GVF, SAR, MML. En español: DANE, GEIH, PET, PEA, PEI, OC, DS, TD, CNPV 2018,
  DNP, DIVIPOLA, ECM, REML, ML, CV, VIF, AIC, AICc, LRT (verificar que «LRT» quede definida), SEBLUP.
  Hoy se definen en el Marco teórico porque es el primer capítulo reescrito. **Parte 2**: al reescribir
  Introducción y Definición del problema (que van antes), mover cada definición a su primera aparición
  y dejar solo la sigla en el Marco.
- ECM = error cuadrático medio (en español); RMSE = su raíz (sigla inglesa, porque así se llaman las
  columnas y las métricas de validación). Se escribe «la RMSE».
- Notación del modelo: $\sigma_u^2$ en el texto (en el código es `A`/`Â`); $\psi_d$ para la varianza de
  muestreo; $d$ dominios, $m$ municipios objetivo.
- Páginas de documentos sin numeración impresa (GEIH v9, series GEIH 2005, ENUSC, DANE SAE, Casen): se
  citan con la página del PDF; las entradas bib llevan la nota «Las páginas citadas son las del archivo
  PDF». Molina (2019): se cita la página impresa (= PDF − 2).
- La comparación EBLUP frente a directa ya no lleva la razón $R_d$ ni la prueba de Wilcoxon (R-64): el
  marco dice que $g_1 < \psi_d$ por construcción.
- Regla de CV única: 5 % y 20 % (no 15/30).

## Etiquetas viejas → nuevas (Marco teórico)

| Etiqueta vieja | Qué pasó | Quién la usa (revisar) |
|---|---|---|
| `eq:sesgo` | Eliminada; el sesgo es parte de `eq:metricas_val` | `resultados.tex` |
| `eq:ratio_mse` | Eliminada (R-64) | `appendice.tex`, `metodologia.tex`, `resultados.tex` |
| `eq:momentos` | Eliminada (el código no usa el estimador de momentos) | — |
| `eq:asimetria` | Fusionada en `eq:cv_descriptivo` | `metodologia.tex`, `resultados.tex` |
| `eq:se` | Fusionada en `eq:var_bootstrap` | `metodologia.tex`, `resultados.tex` |
| `eq:blup`, `eq:ecm_blup` | Eliminadas (el texto pasa directo al EBLUP) | — |
| `eq:pmax` | Se conserva con la cota n // 10 = 2 (antes D/5) | `metodologia.tex`, `resultados.tex` |
| `subsec:evaluacion-desempeno` | Se conserva como segunda etiqueta de `subsec:diagnosticos` | — |
| `subsec:parsimonia` | Segunda etiqueta de `subsec:seleccion` | `metodologia.tex` |
| `subsec:extensiones-fh` | Segunda etiqueta de `subsec:espacial` | — |
| Nuevas | `eq:identidades`, `eq:taylor`, `eq:agregacion`, `eq:ic_fisher` (antes se citaba sin existir), `eq:sintetico`, `eq:r_ponderada`, `eq:bh`, `eq:dfbeta`, `eq:metricas_val`, `eq:gvf`, `eq:sar`, `eq:lrt`, `eq:seblup`, `eq:pred_espacial`, `eq:hnew`, `eq:benchmarking`, `eq:rmse_bm`, `tab:conceptos_etapas`, `subsec:agregacion`, `subsec:seleccion`, `subsec:diagnosticos`, `subsec:gvf`, `subsec:espacial`, `subsec:extrapolacion`, `subsec:benchmarking`, `subsec:sintesis-marco` | |

Las `\ref` a `eq:sesgo`, `eq:ratio_mse`, `eq:asimetria`, `eq:se` en `resultados.tex` y `appendice.tex`
quedan rotas: la parte 2 las corrige al reescribir Resultados (no se tocan aquí, regla del prompt).
Las de `metodologia.tex` se corrigen al reescribir Metodología.

## `\ref` del Marco teórico que apuntan a etiquetas aún inexistentes

`sec:met_directa`, `sec:met_covariables`, `sec:met_fh_clasico`, `sec:met_supuestos`, `sec:met_validacion`,
`sec:met_sin_muestra`, `sec:met_benchmarking`, `sec:met_patrones`, `sec:met_espacial` (se crean al
reescribir Metodología).

## Dudas abiertas (para el equipo)

1. (Resuelta: se deja como está) **Extensión del Marco teórico**: ≈ 19-21 páginas frente a 16 presupuestadas. Propuesta: pasar al
   apéndice las ecuaciones del análisis descriptivo (CV descriptivo, asimetría, regla del diagrama de
   caja, Pearson, Spearman, IC de Fisher; ≈ 1.5 páginas) y el detalle de la GVF y de Taylor (≈ 0.7
   páginas), dejando en el cuerpo un párrafo con la referencia al apéndice.
2. (Resuelta: convención propia, sin cita) **ΔAIC ≤ 2**: hoy se presenta como convención externa (como dice el código). ¿Se agrega la cita a
   Burnham y Anderson (2002, p. 70), que no está en ningún RAG del proyecto?
3. **Cota de covariables**: el documento anterior decía D/5 ≈ 4; el código usa n // 10 = 2 (R-07). El
   marco ya refleja el código.

## Comparación espacial frente a clásico (OE1)

Contenido definido en `metodologia.tex`, Tabla `tab:met_comparacion`. Estado de cada elemento:

| Elemento | ¿Existe? | Dónde | Pendiente |
|---|---|---|---|
| Ajuste: σ̂²_u, ρ̂, AIC, ΔAIC, LRT (4 W × 2 estructuras) | Sí | `tesis.modelo.fhe_comparacion_modelos` (A_hat, rho_hat, AIC, AIC_clasico, Delta_AIC, LRT, p_LRT, p_covariables, R2, espacial_preferido); `fhe_cuadro_comparativo` (sigma2_u del clásico y de cada espacial) | — |
| Residuos: Moran clásico vs SEBLUP, misma W y estandarización | Sí | `fhe_moran` (residuos_clasico, residuos_clasico_estandarizados, tasa_directa, residuos_espacial por estructura) | Mapa de residuos: figura del notebook espacial (`figura_mapa_residuos`); extraer de `notebooks_execution/modelo__fay_herriot_espacial.html` |
| Fuera de muestra: LOAO con las métricas del clásico | Sí | `fhe_validacion_cruzada_metricas` (predictores clásico, sintético espacial, espacial, nulo; RMSE, MAE, RMSE_corregido, sesgo, Z_psi, Z_pred, cobertura, habilidad) y detalle `fhe_validacion_cruzada` | — |
| Incertidumbre en los 83 municipios: ECM y CV clásico vs espacial | Sí | `fhe_prediccion_objetivo` (CV_CLASICO_PCT, MSE_ESPACIAL, CV_ESPACIAL_PCT, FUENTE_MSE_ESPACIAL) | — |
| Incertidumbre en los 23 dominios: ECM y CV del SEBLUP; γ_d y γ^S_d | **No** (solo EBLUP en `fay_herriot_resultados`: MSE_EBLUP, CV_EBLUP_PCT, GAMMA_SHRINKAGE) | El SEBLUP y su ECM bootstrap se calculan en el notebook (celda 25) pero no se persisten | **Cálculo propio C1** |
| Estimaciones: diferencia pp, media, máx, Pearson, Spearman; cambios de clase | Parcial: municipios sí (PRED_CLASICO, PRED_ESPACIAL, DIF_ESPACIAL_VS_CLASICO, CV de ambos); dominios no | `fhe_prediccion_objetivo` | **C2 (municipios) y C3 (dominios, depende de C1)** |
| Coeficientes β̂ y EE clásico vs espacial | Sí | `fhe_coeficientes_comparacion` | — |
| Comparación aparte (benchmark vs espacial de referencia) | Sí | Escenario de referencia = menor AIC en «completa» con ρ̂ interior; prueba en «muestra» del mismo escenario | — |

Cifras del notebook (celdas 25-26, corrida 2026-10-31) a verificar contra tablas en la parte 2:
escenario knn3, ρ̂ = 0.372, σ̂²_u = 4.825, 500/500 réplicas válidas; efecto espacial medio −0.079 pp,
rango [−2.837, 0.707], 8 de 83 municipios con |efecto| > 0.5 pp; CV mediano clásico 19.5 %, espacial
19.9 %; 21 de 83 extrapolan.

## Apéndice

Sin secciones agregadas. Metodología remite a dos secciones existentes: `sec:datos-reproducibilidad`
(linaje y reproducción) y `sec:apendice-catalogo` (catálogo con códigos). La parte 2 debe revisar que
coincidan con el código vigente (18 activas y 6 excluidas, sin IICA activo).

## Imágenes que la parte 1 deja de usar (limpieza en la parte 2)

Sin referencia en ningún `.tex`: `img/etapa1_distribucion_pearson.png`, `img/etapa3_boxplots_candidatas.png`,
`img/etapa4_scatter_{iica,ipm,productividad,transito_edu}.png`, `img/etapa5_loo_heatmap.png`,
`img/etapa6_moran_permutacion.png`, `img/etapa7_{correlacion_candidatas,correlacion_finales,scatter_matrix_finales}.png`,
`img/fh_m{1,2,3}_suavizador.png`, `img/fh_m4_{gvf_ajuste,gvf_residuos,histograma,suavizador}.png`,
`img/fh_modelo{1,2,3,4}_validacion.png`, `img/demo-plot.pdf`, y toda la carpeta `fig/`
(`arquitectura_medallon.png`, `correlacion.png`, `fig_new_experiment_01.pdf`). Las `img/fh_var*`,
`img/desc_*`, `img/eda_*` y `img/fh_ganador_*` las usan aún `resultados.tex` y `appendice.tex` viejos.

Nueva: `img/met_flujo_general.png` y `.pdf` (script `img/_script/diagrama_metodologia.py`, sin datos).

## Etiquetas viejas → nuevas (Metodología)

| Etiqueta vieja | Citada en | Equivalente nuevo |
|---|---|---|
| `sec:met_transformacion`, `eq:pk`, `eq:pea`, `eq:join_oro`, `eq:valor_terridata`, `eq:clasificacion_tipo`, `eq:join_final` | resultados | `sec:met_limpieza` (las ecuaciones de llaves y uniones ya no existen) |
| `subsec:met_bootstrap` | resultados | `sec:met_directa` |
| `subsec:met_elegibilidad` | resultados, apéndice | `sec:met_covariables` |
| `subsec:met_bivariado`, `subsec:met_multivariado` | resultados | `sec:met_descriptivo` |
| `sec:met_eda`, `subsec:met_decision` | resultados | `sec:met_seleccion` |
| `eq:variantes`, `fig:flujo_ajuste_fh`, `eq:regla_seleccion` | resultados | `sec:met_fh_clasico` |
| `subsec:met_estimacion`, `eq:cov_beta` | apéndice, resultados | `eq:gls` (Marco) |
| `subsec:met_validacion` | apéndice, resultados | `sec:met_validacion` |
| `eq:correccion_eblup` | apéndice, resultados | eliminada |
| `subsec:met_robustez_fh`, `eq:cook_gls` | apéndice, resultados | `sec:met_supuestos`, `eq:cook` |
| `sec:met_sintetico`, `eq:extrapolacion`, `fig:flujo_sintetico` | apéndice, resultados | `sec:met_sin_muestra`, `eq:hnew` |
| `sec:met_seleccion` | — | cambia de significado: ahora es la selección de covariables; la del modelo es `sec:met_fh_clasico` |
| Sin uso | — | `fig:medallon`, `fig:flujo_fh`, `fig:flujo_eda`, `fig:regla_seleccion_fh`, `tab:salidas_diagnostico`, `tab:trazabilidad`, `sec:met_trazabilidad` y las `subsec:met_*` restantes |

`\ref` de Metodología a Resultados (la parte 2 debe crearlas con estos nombres): `sec:res_obtencion`,
`sec:res_dominios`, `sec:res_directa`, `sec:res_covariables`, `sec:res_descriptivo`, `sec:res_seleccion`,
`sec:res_fh_clasico`, `sec:res_supuestos`, `sec:res_validacion`, `sec:res_espacial`, `sec:res_sin_muestra`,
`sec:res_benchmarking`, `sec:res_patrones`. `sec:res_seleccion` existe hoy en `resultados.tex` con el
sentido viejo (selección del modelo).

## Para la parte 2

- Metodología promete en Resultados: auditoría de dominios; reconciliación PEA = OC + DS, PET = PEA + PEI
  y llaves sin pareja; cascada y sensibilidad del pre-filtrado; error dejar-un-dominio-fuera de cada
  especificación EC; sensibilidad de las covariables de los A.M. a la regla de la PET; brecha de
  agregación del nivel 2; mapas de la etapa 16 y Moran de las 83 estimaciones (C4).
- La sensibilidad de la ventana temporal (etapa 5) sale de
  `notebooks_execution/manual__sensibilidad_ventana_temporal.html`.
- La comparación «aparte» de la etapa 13 se redactó como benchmark frente a la especificación espacial de
  referencia: confirmar con el equipo si basta o si se espera otra cosa (sec. 7-8 del PDF de la revisión).

- Datos remite al catálogo del apéndice (`sec:apendice-catalogo`) para el código TerriData de cada
  covariable: verificar que esa sección existente tenga los 18 códigos y los 6 excluidos con su motivo
  (la parte 1 no la tocó).
- Etiquetas de tablas de Datos: `tab:fuentes_datos`, `tab:dimensiones-geih-modulos` (se conserva el nombre),
  `tab:dominios_geih`, `tab:anexo_dane`, `tab:tab-variables-originales-terridata` (se conserva),
  `tab:covariables_datos`. Eliminada: `tab:tab-variables-censo` (sin referencias externas).

- Confirmar en el PDF compilado que la cita [9] marcada por la directora era `BernalGonzalez2017`
  (ya se reemplazó por `FayHerriot1979` en el hecho del origen del modelo; ver `auditoria_citas.md`).
- Citas sin uso tras la parte 1 (decidir si se eliminan de `refs.bib` en la limpieza final):
  `DANE_GEIH_Glosario`, `RaoMolina2015`, `Cochran1977`, `Schworer2004`, `VanDerLeeden1997`,
  `TellezTrujilloPedraza2020`, `DNP2019` (este último lo usa el planteamiento).


## Parte 2: Resultados (sesión 1)

- 17 secciones: las 16 etapas con `sec:res_<etapa>` y una «Correspondencia entre etapas y objetivos»
  (`sec:res_objetivos`), en espejo con Metodología (títulos idénticos, comprobado con script).
- Etiquetas del apéndice que Resultados ya cita y que se crean al reescribir el Apéndice: `app:resultados`,
  `app:auditoria`, `app:descriptivo`, `app:seleccion`, `app:especificaciones`, `app:dominios_modelo`,
  `app:validacion`, `app:espacial`, `app:municipios`; figuras `fig:app_gvf`, `fig:app_perfil_rho`,
  `fig:app_sensibilidad_extrapolacion`. Las filas de las tablas largas ya están generadas en
  `calculos/salidas/filas_*.tex` (`calculos/filas_latex.py`).
- Decisión de redacción: EC2 y EC3 son equivalentes por AIC y tienen una covariable cada una; la elección
  de EC3 la define el AIC, no la parsimonia (el notebook dice «regla de parsimonia»).
- `\cite{DANE_SAE_2025}` para el formato de la tabla de diagnósticos quedó sin página: verificar la página.
- Pendiente de figura: `img/fh_escenarios_varianza.png` usa más de tres colores (va al apéndice).
- Discrepancia: el texto fijo de la celda 15 del notebook espacial (RMSE 2.08 → 3.08) no corresponde a la
  corrida (2.52 → 3.43); no se usó.
- Hecho (aprobado por el equipo el 2026-11-03): las Tablas `tab:res_faltantes`, `tab:res_excluidas`,
  `tab:res_agregacion_am`, `tab:res_frecuencia` y `tab:res_validacion_espacial` pasaron a la sección nueva
  del apéndice «Material complementario de Resultados» (`app:resultados`, antes de «Repositorio de github»;
  script `calculos/mover_tablas_apendice.py`). El texto de Resultados conserva las cifras clave y remite allí.

## Parte 2: Discusión (sesión 1)

- 2026-11-03: Resultados confirmado por el equipo. Se escribió `discusion.tex`: cuatro secciones de lectura
  (`sec:dis_espacial`, `sec:dis_covariables`, `sec:dis_alcance` con la Tabla `tab:dis_alcance`,
  `sec:dis_metodologia`) y `sec:dis_futuro`. Sin citas nuevas: todas las claves ya estaban auditadas.
- Cifra nueva leída por SQL: población urbana de los municipios objetivo (inventario §4).
- **Esperando confirmación del equipo sobre Discusión** antes de seguir con Conclusiones.

## Parte 2: Conclusiones (sesión 1)

- 2026-11-03: Discusión confirmada. Se escribió `conclusiones.tex` con una sección por objetivo (OG, OE1, OE2,
  OE3), cada una con su cifra de soporte. `\label{sec:conclusion}` queda solo en ese archivo.
- **Esperando confirmación del equipo sobre Conclusiones** antes de seguir con Planteamiento y formulación.

## Parte 2: Definición del problema (sesión 1)

- 2026-11-03: Conclusiones confirmadas. Se reescribió el planteamiento (situación actual con la desagregación
  de la GEIH, Tabla `tab:problema` de síntomas, causas y consecuencias, y el problema desde la ciencia de
  datos) y se revisó la redacción de la formulación (concordancia, nueva etiqueta `sec:formulacion`); se
  eliminó el bloque de comentario de la directora.
- Citas: se quitó `DNP2019` (no verificable) y la atribución errónea del caso de Cundinamarca a
  `VargasLemusAlejo2018`; detalle en `auditoria_citas.md` §5.
- Siglas: el planteamiento usa GEIH, DANE, A.M. y TD sin definirlas porque la Introducción, que va antes,
  las definirá.
- **Esperando confirmación del equipo sobre la Definición del problema** antes de seguir con la Introducción.

## Parte 2: Introducción (sesión 1)

- 2026-11-03: Definición del problema confirmada. Se reescribió `introduction.tex` en el orden del prompt
  (encuestas y cobertura, problema, estrategia Fay-Herriot y extensión espacial, metodología en un párrafo,
  resultados en tono neutral, organización del documento), sin tiempo futuro.
- Siglas movidas a su primera aparición: GEIH, DANE, A.M., SAE y DNP se definen en la Introducción; en
  `marco-teorico.tex` se dejó solo la sigla (tres frases: DANE/GEIH, DNP y SAE). Fue el único cambio a un
  capítulo de la parte 1, previsto en las decisiones de la parte 1.
- **Esperando confirmación del equipo sobre la Introducción** antes de seguir con los Apéndices.

## Parte 2: Apéndice (sesión 1)

- 2026-11-03: Introducción confirmada. `appendice.tex` se regeneró con `calculos/construir_apendice.py` (lee
  `calculos/datos/` y `calculos/salidas/`; conserva `app:resultados`). Copia previa en
  `calculos/salidas/appendice_antes.tex`. 14 secciones, cada una con `app:<tema>` y frase de apertura:
  reproducibilidad, linaje, variables, catalogo, auditoria, descriptivo, seleccion, especificaciones,
  dominios_modelo, varianza, validacion, espacial, municipios, resultados.
- Se eliminaron del apéndice: diagramas TikZ de linaje (con `[H]`, `	extbf` y tablas `*_area_*` que el código ya
  no escribe, R-21), la tabla vieja de 83 sintéticos y las variantes M1-M5 con sus figuras `fh_var*`. El linaje
  quedó como tabla (`tab:app_linaje`) más el conteo de tablas vigentes por esquema; se avisa que el catálogo
  conserva tablas huérfanas (censo, `*_area_*`, `covariables_candidatas`, `robustez_covariables`, `dim_tiempo`).
- Etiquetas viejas → nuevas: `sec:datos-apendice`, `sec:datos-reproducibilidad`, `sec:repositorio-github` →
  `app:reproducibilidad`; `sec:apendice-linaje-{geih,terridata,dim,preprocesamiento,modelo}` y sus `fig:linaje_*`,
  `tab:tablas_*` → `app:linaje`, `tab:app_linaje`; `sec:apendice-catalogo`, `tab:catalogo_literatura` →
  `app:catalogo`, `tab:app_catalogo`; `sec:apendice-sinteticas`, `tab:prediccion_sintetica` → `app:municipios`,
  `tab:app_municipios`; `sec:apendice-variantes` y sus tablas y figuras → `app:especificaciones`. Se actualizaron
  las `
ef` de `metodologia.tex`, `datos.tex` y `resultados.tex` (solo etiquetas, regla de la parte 1).
- Coeficientes de EC0-EC2 transcritos de la salida del notebook (celda 8): el procesamiento solo persiste los del
  benchmark.
- Verificación: 0 referencias rotas en apéndice, resultados, metodología y datos. El apéndice usa `	exttt`
  solo para nombres técnicos de trabajos y tablas (linaje), como pide el prompt.
- Imágenes sin referencia (limpieza en el paso de imágenes): `etapa*`, `fh_m*`, `fh_modelo*`, `fh_var*`,
  `demo-plot.pdf` (32 archivos) y la carpeta `fig/`.
- **Esperando confirmación del equipo sobre el Apéndice** antes de seguir con el Resumen.

## Parte 2: Resumen (sesión 1)

- 2026-11-03: Apéndice confirmado. `docs/sommario.tex` reescrito en un párrafo de unas 395 palabras: tema,
  problema, objetivo, metodología, resultados principales y aplicaciones. En presente, como pidió la directora
  en su comentario (se eliminó el bloque); sin tiempo futuro. Siglas definidas de nuevo porque el resumen se
  lee aparte.
- Pendientes de la parte 2 después del Resumen: verificación de todo el documento, limpieza de imágenes y
  `fig/`, limpieza de `refs.bib` y reporte final `control_cambios_documento.md`.
- **Esperando confirmación del equipo sobre el Resumen.**

## Parte 2: cierre (2026-11-03)

- Resumen confirmado. Verificación global con `calculos/verificar_documento.py`: 0 referencias rotas, 0 etiquetas
  duplicadas, 0 tablas/figuras/ecuaciones sin citar, 0 citas sin entrada, 0 entradas sin citar; títulos de
  Metodología y Resultados idénticos (17).
- `refs.bib`: 20 entradas sin citar eliminadas (`calculos/limpiar_bib.py`); quedan 39.
- Imágenes: `fig/` eliminada; 32 imágenes sin uso y 4 demos de TikZ eliminadas de `img/`.
- Resultados: se agregó la cita a `app:linaje` y `app:variables` (solo esas dos frases).
- Reporte final: `../control_cambios_documento.md`.
- PARTE 2 CERRADA. Pendiente: número real de páginas en Overleaf.
