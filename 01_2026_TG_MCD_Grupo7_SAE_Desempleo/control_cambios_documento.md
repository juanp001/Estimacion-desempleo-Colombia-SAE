# Control de cambios del documento (partes 1 y 2)

Reescritura del documento LaTeX desde la Introducción hasta las Conclusiones, con el Resumen y el Apéndice, para
que refleje lo que hizo el código y las cifras de la corrida vigente (cierre 2018, notebooks ejecutados el
2026-10-31). Fecha de cierre: 2026-11-03. Sin commits. Respaldo previo: `_respaldo_2026-11-03/` (capítulos,
`refs.bib`, `main.tex`). Detalle de la sesión y decisiones: `_trabajo/avance.md`; cifras y su fuente:
`_trabajo/inventario_cifras.md`; citas: `_trabajo/auditoria_citas.md`.

Etiquetas de capítulo: `sec:problema`, `sec:objetivos`, `sec:marco-referencia`, `sec:datos`, `sec:metodologia`,
`sec:resultados`, `sec:discusion`, `sec:conclusion`. Metodología (`sec:met_*`) y Resultados (`sec:res_*`) tienen
los mismos 17 títulos en el mismo orden (comprobado con `_trabajo/calculos/verificar_documento.py`).

## 1. Comentarios de la revisión (G7-B1 a G7-B22 y secciones 7 a 11)

| Comentario | Dónde se atiende en el documento | Estado |
|---|---|---|
| G7-B1 Correspondencia geográfica respuesta-covariables | Met. `sec:met_dominios`, `sec:met_covariables`; Res. `tab:res_auditoria`, `tab:dominios_geih` (Datos); Apéndice `tab:app_auditoria`; agregación por denominador `tab:covariables_datos`, `tab:res_agregacion_am`; Discusión `tab:dis_alcance` (geografía distinta) | Atendido |
| G7-B2 Justificar la ventana temporal | Met. `sec:met_directa`; Res. `tab:res_ventana`, `fig:res_ventana` | Atendido |
| G7-B3 El bootstrap no reproduce el diseño | Met. `sec:met_directa` (limitación declarada, sin afirmar dirección del sesgo); Res. `tab:res_directa` (bootstrap frente a Taylor), `tab:res_varianza`; Apéndice `tab:app_varianza`, `fig:app_gvf`; Discusión `tab:dis_alcance` | Atendido |
| G7-B4 Validar la construcción de la TD | Res. `tab:res_directa` (23/23 = DANE, total 10.83 = 10.83), `tab:res_ventana` (trimestre y año) | Atendido |
| G7-B5 Auditar la derivación de la PEA | Met. `sec:met_limpieza` (lectura por nombre de columna); Res. `tab:res_limpieza` (identidades, bandera PEA = OC + DS en 12 meses) | Atendido |
| G7-B6 FEX faltante imputado con cero | Met. `sec:met_limpieza`, `tab:met_faltantes` (se detiene); Res. `tab:res_limpieza` (0 personas) | Atendido |
| G7-B7 Umbrales de CV inconsistentes | Marco (regla única 5/20); Met. `tab:met_directa`; usado igual en todo Resultados | Atendido |
| G7-B8 Selección que ignora la precisión | Met. `tab:met_seleccion` (FH univariado con ψ_d); Res. `tab:res_seleccion`; Apéndice `tab:app_seleccion` | Atendido |
| G7-B9 Multiplicidad | Met. `tab:met_seleccion` (Benjamini-Hochberg); Res. `tab:res_seleccion` (q) | Atendido |
| G7-B10 Componentes conexas | Met. paso 3 (enlace completo); Res. `sec:res_seleccion` | Atendido |
| G7-B11 Orden de filtros y retroceso | Met. paso 3; Res. `tab:res_seleccion` (redundantes con su representante) | Atendido |
| G7-B12 Signo esperado como diagnóstico | Met. paso 4; Res. `tab:res_bivariado`, `sec:res_seleccion` (misma selección exigiendo el signo) | Atendido |
| G7-B13 Pearson-Spearman y forma funcional | Met. paso 1; Res. `tab:res_bivariado`, `sec:res_seleccion` (lineal adecuada en las 3 elegibles); Apéndice `fig:app_residuos_parciales` | Atendido |
| G7-B14 Interpretación no causal | Met. `sec:met_fh_clasico`; Res. `sec:res_fh_clasico`; Discusión `sec:dis_covariables`; Conclusiones OE2 | Atendido |
| G7-B15 EC0-EC3 son variantes del benchmark | Met. `sec:met_fh_clasico`; Res. `tab:res_especificaciones`; Apéndice `app:especificaciones` | Atendido |
| G7-B16 AICc como complemento | Res. `tab:res_especificaciones` (AICc ordena igual); se redacta que EC2 y EC3 son equivalentes y decide el AIC | Atendido |
| G7-B17 Significancia no es demostración | Met. `sec:met_fh_clasico`; Res. `tab:res_coeficientes` (p descriptivos) | Atendido |
| G7-B18 Sensibilidad a dominios individuales | Res. `tab:res_estabilidad`, `fig:res_loao`; Apéndice `fig:app_cook` | Atendido |
| G7-B19 Validación predictiva | Met. `sec:met_validacion`; Res. `tab:res_validacion`, `tab:res_frecuencia`; Apéndice `tab:app_validacion` | Atendido |
| G7-B20 Extrapolación | Met. `sec:met_sin_muestra`; Res. `fig:res_rangos`, `tab:res_extrapolacion`; Apéndice `fig:app_sensibilidad_extrapolacion`, `tab:app_municipios` | Atendido |
| G7-B21 Confiabilidad condicional al modelo | Res. `sec:res_sin_muestra`, `tab:res_calidad`; Discusión `tab:dis_alcance` | Atendido |
| G7-B22 Media residual y Shapiro-Wilk | Res. `tab:res_diagnosticos` (formato DANE, lectura prudente) | Atendido |
| Sec. 7 Comparación controlada y comparación aparte | Met. `tab:met_espacial`, `tab:met_comparacion`; Res. `tab:res_espacial`, `tab:res_comparacion` | Atendido; la comparación «aparte» se reportó como benchmark frente a la especificación espacial de referencia (confirmar si basta) |
| Sec. 8 W sobre unidades reales, Moran y mapa de residuos | Met. `tab:met_espacial` (A.M. = un nodo); Res. `tab:res_moran`, `fig:res_mapa_residuos`; Apéndice `tab:app_espacial_centroide` | Atendido |
| Sec. 9 Predictor espacial derivado del modelo | Marco `eq:pred_espacial`; Met. `sec:met_sin_muestra`; Res. `fig:res_espacial_estimaciones`, `tab:app_municipios` | Atendido |
| Sec. 10 Tablas mínimas (11) | 1 `tab:res_auditoria`/`tab:app_auditoria`; 2 `tab:dominios_geih` + `tab:res_directa`; 3 `tab:res_directa`; 4 `tab:res_ventana`; 5 `tab:res_limpieza`; 6 `tab:covariables_datos`; 7 `tab:res_especificaciones`; 8 `tab:res_estabilidad`; 9 `tab:res_validacion`; 10 `tab:res_seleccion` (soporte) y `tab:res_extrapolacion`; 11 `fig:res_mapa_residuos` | Atendido. Las tablas municipales siguen marcadas como preliminares en el procesamiento (`ESTADO_RESULTADO = PRELIMINAR`); el documento recomienda el clásico al cerrar el OE1 |
| Sec. 11 Preguntas previas al modelo espacial | Respondidas en Resultados: geografía (`sec:res_dominios`), muestra (`tab:res_directa`), ventana (`tab:res_ventana`), reproducción del DANE, emparejamientos y FEX (`tab:res_limpieza`), CV único, variables congeladas (EC3), estabilidad, LOAO, extrapolación (21 de 83, no 76 de 82 como en la versión revisada), unidad espacial y W (`sec:res_espacial`) | Atendido |

## 2. Criterios de evaluación

| Hoja e indicador | Cómo se cumple |
|---|---|
| Formato 1-2 Tablas y figuras | Toda tabla, figura y ecuación con `\label` y citada (0 sin citar, verificador); captions con siglas y unidades; figuras sin título interno |
| Formato 3, 16 Organización y etiquetas | Capítulos en el orden de la plantilla; etiquetas de capítulo de la lista; Metodología y Resultados en espejo |
| Formato 4 Símbolos | 0 `---`, 0 `\textbf` en el texto |
| Formato 5-6 main.tex y párrafos | `main.tex` solo con `\input`; 0 `\\` o `\par` como separador |
| Formato 7 Siglas | Definidas una vez en su primera aparición (Introducción para GEIH, DANE, A.M., SAE, DNP; Marco para las demás); formato único «(SIGLA, por sus siglas en inglés)» |
| Formato 8 `[!htbp]` | 0 `[H]` en el documento (los del apéndice viejo se eliminaron) |
| Formato 9 Referencias cruzadas | 0 referencias rotas |
| Formato 10, 13 Títulos | Mayúscula solo inicial (las intermedias son nombres propios: Fay-Herriot, Hájek, Moran, GEIH, Colombia). Pendiente: el título del documento en `main.tex` está en tipo título y el encabezado de la maestría en mayúscula sostenida |
| Formato 11 Nombres de código | 0 `\texttt` fuera del apéndice; tabla de nombres `tab:app_variables` |
| Formato 12 Extensión | Ver estimación de páginas (§6); riesgo de superar 100 páginas |
| Formato 14-15 Jerarquía y viñetas | Sin saltos de nivel; solo `itemize` |
| Generales 1-5 | Resumen (un párrafo, 395 palabras), Introducción (≤ 2 págs.), Planteamiento (síntomas, causas, consecuencias, enfoque de ciencia de datos), Formulación (pregunta general + 3 de sistematización), Objetivos sin cambios |
| Generales 6-8 | Marco y Antecedentes (parte 1); Metodología con 16 etapas y fichas |
| Generales 9 Referencias | IEEE (clase); 39 entradas, todas citadas (20 huérfanas eliminadas) |
| Generales 10 Tiempo verbal | Impersonal en pasado; el Resumen en presente por comentario de la directora; sin futuro en Introducción ni Resumen |
| Generales 11-12 | Discusión con limitaciones (`tab:dis_alcance`) y trabajo futuro; 4 conclusiones, una por objetivo, con cifra |
| Datos y pre-procesamiento 1-5 | Errores y notación: `sec:met_limpieza`/`tab:res_limpieza`; faltantes e imputación: `tab:met_faltantes`, `sec:res_faltantes`; atípicos: regla del diagrama de caja, sin eliminar; creación de variables: `sec:met_covariables`, `tab:res_agregacion_am`; descriptivo: `sec:met_descriptivo`, `sec:res_descriptivo` |
| Modelación 1-5 | Entradas y naturaleza en cada ficha; sin hiperparámetros a optimizar (se declara en `sec:met_faltantes`; escenarios de W como escenarios); supuestos y validación (`tab:res_diagnosticos`); métricas de validación (`eq:metricas_val`); al menos dos modelos con distintas configuraciones: EC0-EC3 y 8 espaciales |

## 3. Objetivo → etapas → evidencia

| Objetivo | Etapas | Evidencia en Resultados | Alerta |
|---|---|---|---|
| OG | 1-16 | `tab:res_directa`, `tab:res_calidad`, `tab:app_municipios`, `tab:res_objetivos` | Ninguna; cifras municipales no confiables, se reporta así |
| OE1 | 5, 10-13 | `tab:res_especificaciones`, `tab:res_espacial`, `tab:res_moran`, `tab:res_comparacion`, `fig:res_espacial_estimaciones` | Ninguna |
| OE2 | 6-12, 13 (coeficientes) | `tab:res_seleccion`, `tab:res_coeficientes`, `tab:res_estabilidad`, `tab:res_validacion` | La respuesta es de asociación con una sola covariable inestable |
| OE3 | 14-16 | `fig:res_mapa_municipios`, `tab:res_extrapolacion`, Moran de las estimaciones (`sec:res_patrones`) | El patrón reproduce la tasa de homicidios; se dice explícitamente |

## 4. Citas

Corregidas, agregadas y eliminadas: `_trabajo/auditoria_citas.md` §1 (parte 1), §4 (Antecedentes) y §5 (parte 2).
Resumen:

- Corregidas: cita [9] (`BernalGonzalez2017` → `FayHerriot1979` para el origen del modelo), `ColeyTellez2024`,
  `Molina2019` (bootstrap), `Tellez2020`, `Montoya2019`, `MendozaZea2019`, `TellezTrujilloPedraza2020` →
  `GuerreroTrujillo2019`, entradas bib de Bernal, Coley, Montoya, Guerrero, INE Chile, Ramírez-Lemus-Alejo.
- Agregadas: `BenjaminiHochberg1995`, `MontgomeryPeckVining2012`, `ShapiroWilk1965`, `Cook1977`, `Moran1950`,
  `HurvichTsai1989`, antecedentes espaciales (Benedetti, Shiferaw, Pereira, Sikov, Haro, Romero-Lemus, Durán,
  Gallego-Muñoz, Petrucci-Salvati, Pratesi-Salvati, Díaz, Casen 2024). En la parte 2, páginas nuevas de
  `DANE_GEIH_Metodologia2016` (PDF 9) y `Diaz2016` (pp. 124-125).
- Eliminadas de `refs.bib` por no citarse (20): ArroyoMina2016, Cochran1977, DANE_GEIH_Glosario, DNP2019, DNP2019b,
  GhoshRao1994, Gutierrez2009, NascimentoSilva2023, RamirezVargas2018, RaoMolina2015, Rubin1987,
  SarndalSwenssonWretman2003, Schworer2004, Spiegelhalter2002, TellezAriasGomezOyola2021, TellezTrujilloPedraza2020,
  TellezTrujilloTrivino2020, Trevino2016, VanDerLeeden1997, Zea2018.
- Pendientes de verificar: página de `DANE_SAE_2025` para el formato de la tabla de diagnósticos (citada sin página
  en `tab:res_diagnosticos`); lectura literal de Morales p. 61 y p. 272 y Benedetti p. 144; DOI de Pratesi-Salvati y
  Petrucci-Salvati; coautores de Arroyo (ya no se cita); confirmar en el PDF compilado que la cita [9] era Bernal.

Decisiones sin sustento bibliográfico (convenciones propias, así declaradas en el texto): ΔAIC ≤ 2; cota de
covariables n // 10; soporte 0.80; Cook 4/n como inspección; umbrales LOAO de 1 EE y 0.5 pp; |λ − 1| > 0.20;
escenarios de W (k = 3, 5; potencias 1, 2); escenarios ψ × k.

## 5. Discrepancias entre fuentes y figuras

- Ninguna discrepancia entre tablas `tesis.*` y salidas de los notebooks en las cifras usadas.
- La celda 15 del notebook espacial imprime un texto fijo («RMSE 2.08 a 3.08») que no corresponde a la corrida
  (2.52 a 3.43); no se usó. Conviene corregir ese texto en el código.
- El notebook del clásico redacta que EC3 se eligió «por la regla de parsimonia»; EC2 y EC3 tienen una covariable
  cada una y la elección la define el AIC. El documento lo redacta así.
- El prompt anticipaba 33/29/15/6 en la calidad municipal (antes del benchmarking); la tabla final da 32/30/14/7
  porque Cali y Yumbo pasan a no confiables tras el nivel 2. El documento usa ambas cifras en su lugar.
- Figura pendiente de regenerar: `img/fh_escenarios_varianza.png` usa más de tres colores (apéndice). Las demás
  figuras copiadas de los notebooks usan la paleta de matplotlib por defecto; las dos nuevas
  (`img/_script/figuras_resultados.py`) usan la paleta de tres colores. Si se quiere una sola paleta en todo el
  documento, hay que regenerar las figuras del cuerpo con ese script.
- Términos con «predicción» fuera de los permitidos, en capítulos confirmados de la parte 1 (decidir entre los
  tres): «el predictor coincide con el sintético» (Marco), «el predictor de un área sin muestra» y «las
  predicciones de ambos modelos» (Antecedentes).
- Tablas huérfanas en el catálogo `tesis` que ningún código vigente escribe: esquema `censo_nal`, tablas
  `*_area_marco_antiguo`, `covariables_candidatas`, `robustez_covariables`, `dim.dim_tiempo`.

## 6. Etiquetas y páginas

Etiquetas viejas → nuevas: listas completas en `_trabajo/avance.md` (Marco teórico, Metodología, Apéndice). Las
del apéndice: `sec:datos-apendice`, `sec:datos-reproducibilidad`, `sec:repositorio-github` →
`app:reproducibilidad`; `sec:apendice-linaje-*` → `app:linaje`; `sec:apendice-catalogo` → `app:catalogo`;
`sec:apendice-sinteticas` → `app:municipios`; `sec:apendice-variantes` → `app:especificaciones`. En Resultados,
las viejas `sec:res_transformacion`, `sec:res_variable_respuesta`, `sec:res_eda`, `sec:res_modelo`,
`sec:res_sintetico` y sus subsecciones desaparecen; `sec:res_seleccion` pasa a significar la selección de
covariables. Nueva: `sec:formulacion`.

Estimación de páginas (400 palabras por página, 0.5 por tabla o figura pequeña, 1 por tabla con `tabularx` o
`longtable`; sobrestima las fichas de Metodología, que miden media página):

| Parte | Estimación | Presupuesto |
|---|---|---|
| Portada, resumen, índices | ≈ 8-9 | 8 |
| Introducción | 1.8 | 2 |
| Definición del problema | 3.5 | 3 |
| Objetivos | 0.5 | 1 |
| Marco teórico y antecedentes | ≈ 24-30 | 20 |
| Datos | ≈ 7-8 | 6 |
| Metodología | ≈ 17-25 | 18 |
| Resultados | ≈ 26-30 | 26 |
| Discusión | 5.4 | 5 |
| Conclusiones | 2.2 | 3 |
| Referencias (39 entradas) | ≈ 4 | 6 |
| Total sin apéndice | ≈ 100-117 | 98 |
| Apéndice | ≈ 40 (no cuenta) | no cuenta |

Riesgo: el total puede pasar de 100. Si el PDF de Overleaf lo confirma, las candidatas para pasar al apéndice son
las ecuaciones del análisis descriptivo y de la GVF en el Marco (≈ 2 págs., propuesta de la parte 1) y las fichas
de las etapas 1-4 y 7-8 de Metodología.

## 7. Comparación del modelo espacial frente al clásico: cálculos propios

| Id | Script y entradas | Resultado | Dónde aparece |
|---|---|---|---|
| C1 | `_trabajo/calculos/comparacion_espacial.py`; `covariables_seleccionadas`, `municipios_sin_encuesta`, `dim_divipola`, `fay_herriot_resultados`; clase `FayHerriotEspacial` del código, 500 réplicas, semilla 42 | Reproduce ρ̂ = 0.372 y σ̂²_u = 4.825; CV mediano SEBLUP 2.60 %; γ^S_d 0.964-0.991; ECM medio 0.091 | `tab:res_comparacion`, `tab:app_dominios_modelo`, `fig:res_espacial_estimaciones` |
| C2 | Mismo script; `fhe_prediccion_objetivo` | 83 municipios: diferencia absoluta media 0.22 pp, máx. 2.79 (Cali); Pearson 0.992, Spearman 0.987; 8 cambian de clase | `tab:res_comparacion`, `fig:res_espacial_estimaciones` |
| C3 | Mismo script; salida C1 | 23 dominios: diferencia máx. 0.02 pp; correlación 1.000; 0 cambios de clase | `tab:res_comparacion` |
| C4 | Mismo script; `fay_herriot_estimaciones_finales`, `fhe_prediccion_objetivo` | Moran de las 83 estimaciones I = 0.265, p = 0.001; tasa de homicidios I = 0.256 | `sec:res_patrones`, Conclusiones OE3 |

Descarga de tablas: `_trabajo/calculos/descargar_tablas.py` (SELECT de solo lectura con la CLI de Databricks). Filas
de las tablas largas: `_trabajo/calculos/filas_latex.py`. Apéndice: `_trabajo/calculos/construir_apendice.py`.

## 8. Imágenes y apéndice

- `fig/` eliminada (no tenía imágenes en uso: `arquitectura_medallon.png`, `correlacion.png`,
  `fig_new_experiment_01.pdf`). `img/` es la única carpeta.
- Eliminadas de `img/` por no tener referencia (32 + 4 demos de TikZ): `etapa*`, `fh_m*`, `fh_modelo*`, `fh_var*`,
  `demo-plot.pdf` y `img/drawings/demo-*.tex`. Lista exacta en `_trabajo/calculos/salidas/imagenes_eliminadas.txt`;
  todos estaban en git.
- Reemplazadas por las de la corrida vigente: `desc_*`, `eda_robustez`, `eda_correlacion_finales`, `fh_ganador_*`.
  Agregadas desde los notebooks: `res_ventana_sensibilidad`, `eda_residuos_parciales`, `fh_ec{0,1,2,3}_*`,
  `fh_rangos_covariables`, `fh_sensibilidad_extrapolacion`, `fh_loao_influencia`, `fh_validacion_cruzada`,
  `fh_gvf_ajuste`, `fh_escenarios_varianza`, `fhe_mapa_residuos`, `fhe_perfil_rho`, `fhe_validacion_cruzada`.
  Nuevas con script: `res_espacial_estimaciones`, `res_mapa_municipios`.

Secciones del apéndice y quién las cita:

| Sección | Etiqueta | Citada desde |
|---|---|---|
| Disponibilidad de datos y código, y reproducción | `app:reproducibilidad` | Metodología |
| Linaje de tablas | `app:linaje` | `sec:res_obtencion` |
| Nombres de las variables | `app:variables` | Apertura de Resultados |
| Catálogo de covariables | `app:catalogo` | Datos, Metodología, Resultados |
| Auditoría de los dominios | `app:auditoria` | `sec:res_dominios` |
| Análisis descriptivo de las candidatas | `app:descriptivo` | `sec:res_descriptivo` |
| Detalle de la selección de covariables | `app:seleccion` | `sec:res_seleccion` |
| Especificaciones del Fay-Herriot clásico | `app:especificaciones` | `sec:res_supuestos` |
| Estimaciones de los dominios | `app:dominios_modelo` | `sec:res_fh_clasico` |
| Varianza de muestreo | `app:varianza` | `sec:res_supuestos` (`fig:app_gvf`) |
| Validación predictiva por dominio | `app:validacion` | `sec:res_validacion` |
| Detalle del modelo espacial | `app:espacial` | `sec:res_espacial` |
| Estimaciones de los 83 municipios | `app:municipios` | `sec:res_sin_muestra` |
| Material complementario de Resultados | `app:resultados` | Resultados (cinco tablas) |

Todas las secciones del apéndice se citan desde el cuerpo con `Apéndice~\ref{app:…}`.
