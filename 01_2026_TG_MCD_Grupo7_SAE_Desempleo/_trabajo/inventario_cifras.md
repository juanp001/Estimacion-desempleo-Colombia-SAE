# Inventario de cifras

Matriz «afirmación o cifra → fuente → capítulo donde se usa». La parte 1 registra parámetros (Marco
teórico, Metodología) y cifras de Datos; la parte 2 agrega las de Resultados.

Fuentes, en orden de prioridad: (1) tablas `tesis.*` (SQL de solo lectura), (2)
`notebooks_execution/*.html` (corrida del 2026-10-31), (3) `docs/resultados_cierre_2018.md`.
Los parámetros fijados de antemano se leen del código (archivo:línea a la fecha de esta sesión).

## 1. Parámetros fijados en el código

| Cifra o regla | Valor | Fuente | Capítulo |
|---|---|---|---|
| Período de estimación | año 2018, cierre en diciembre | `preprocesamiento/shared/config.py:81-82` (`PER_ESTIMACION`, `MES_ESTIMACION`) | Marco, Metodología |
| Ventana de la estimación directa | 12 meses (año calendario); opción 3 (trimestre móvil) | `config.py:86-87` (`N_MESES_VENTANA`, `VENTANAS_PERMITIDAS`) | Metodología |
| Ventanas de la sensibilidad temporal | mes 1, trimestre 3, año 12 | `config.py:90` (`VENTANAS_TEMPORALES`) | Metodología |
| Réplicas y semilla del bootstrap de la directa | B = 2,000; semilla 42 | `config.py:75-76` | Marco, Metodología |
| Umbrales de CV (regla única) | < 5 % confiable; 5 % a < 20 % aceptable; ≥ 20 % no confiable | `config.py:314-328` (GEIH v9 PDF 12; Molina 2019 PDF 16-17) | Marco, Metodología |
| Pre-filtrado: CV mínimo | 0.001 (0.1 %) | `config.py:333` (`CV_MINIMO`) | Metodología |
| Pre-filtrado: proporción modal máxima | 0.90 | `config.py:335` | Metodología |
| Umbral de duplicados (solo reporte) | abs(r) ≥ 0.999 | `config.py:337` | Metodología |
| Umbral de redundancia (enlace completo) | abs(r) ≥ 0.80 | `config.py:342` | Marco, Metodología |
| Cambio dejar-uno-fuera de la correlación | 0.10 (diagnóstico, no filtro) | `config.py:344` | Metodología |
| Observaciones por parámetro | 10 → cota = n // 10 (2 con 23 dominios) | `config.py:349` (`OBS_POR_PARAMETRO`, `cota_covariables`) | Marco, Metodología |
| Soporte mínimo en municipios objetivo | 0.80 (advertencia) | `config.py:379` | Metodología |
| VIF máximo | 5 | `config.py:381` | Marco, Metodología |
| Nivel del IC de Fisher | 0.05 (IC 95 %) | `config.py:383` | Marco |
| Elegibilidad por BH | q ≤ 0.10 | `config.py:386` | Marco, Metodología |
| Departamentos objetivo | 19 (Cauca), 76 (Valle del Cauca) | `config.py:390` | Datos, Metodología |
| ΔAIC de equivalencia | 2 (convención externa al libro) | `modelo/shared/config.py:174` | Marco, Metodología |
| Significancia de las covariables | 0.05 | `modelo/shared/config.py:182` | Marco, Metodología |
| Aviso de Â ≈ 0 | γ máx < 0.01 | `modelo/shared/config.py:187` | Metodología |
| Límites de tasa | [0, 100] | `modelo/shared/config.py:189-190` | Metodología |
| Aviso de benchmarking | abs(λ − 1) > 0.20 | `modelo/shared/config.py:157` | Marco, Metodología |
| Tolerancia frente a la cifra DANE | 0.01 pp | `modelo/shared/config.py:160` | Metodología |
| Estabilidad de coeficientes (bootstrap de dominios) | 1,000 réplicas, semilla 42 | `modelo/shared/config.py:61-62` | Metodología |
| Umbrales LOAO (influencia) | 1.0 EE; 0.5 pp | `modelo/shared/config.py:76-77` | Marco, Metodología |
| Cobertura nominal de Z_pred | 0.95 | `modelo/shared/config.py:88` | Marco, Metodología |
| Escenarios de W | kNN k = 3, k = 5; distancia inversa potencia 1 y 2 | `modelo/shared/config.py:233-238` | Marco, Metodología |
| Cota de abs(ρ) | 0.99 | `modelo/shared/config.py:241` | Marco, Metodología |
| Permutaciones del I de Moran | 9,999 | `modelo/shared/config.py:243` | Marco, Metodología |
| Bootstrap paramétrico del ECM espacial | 500 réplicas, semilla 42 | `modelo/shared/config.py:245-246` | Marco, Metodología |
| Nivel del LRT de ρ = 0 | 0.05, estructura «muestra» | `modelo/shared/config.py:251` | Marco, Metodología |
| Escenarios ψ × k | k ∈ {1/3, 1/2, 2/3, 3/2, 2, 3} + base, Taylor, GVF A (9 en total) | CLAUDE.md (R-65), `modelo/shared/sensibilidad_varianza.py` | Marco, Metodología |
| GVF A | log ψ = b0 + b1·y + b2·n | `sensibilidad_varianza.py:64` (Morales p. 427) | Marco |
| GVF B | log ψ = b0 + b1·log(p(1−p)) + b2·log n | `sensibilidad_varianza.py:65` | Marco |
| Edad mínima para la PEA de la estimación | 15 años y más | CLAUDE.md (estimación directa: PEA==1, EDAD ≥ 15) | Marco, Metodología |

## 2. Cifras de tamaño del problema usadas en el Marco teórico

| Cifra | Valor | Fuente | Capítulo |
|---|---|---|---|
| Dominios con estimación directa | 23 (ciudades y A.M.) | CLAUDE.md; `tesis.dim.dim_dominio_geih` (por verificar con SQL en Datos) | Marco, Datos |
| Municipios miembro de dominios | 52 filas en `dim_dominio_geih` | CLAUDE.md (por verificar con SQL) | Datos |
| Municipios objetivo | 83 (Cauca y Valle, 2018-12) | CLAUDE.md; `tesis.preprocesamiento.municipios_sin_encuesta` (por verificar) | Marco, Datos |
| Candidatas activas del catálogo | 18 | CLAUDE.md | Marco, Metodología |
| Variables del documento sin dato utilizable | 6 (`CATALOGO_EXCLUIDAS`) | CLAUDE.md | Metodología |

## 2b. Cifras de Datos (SQL de solo lectura, 2026-11-03)

| Cifra | Valor | Fuente (consulta) | Capítulo |
|---|---|---|---|
| Personas GEIH 2018 (marco antiguo) | 762,753 | `geih_oro.mercado_laboral` WHERE PER=2018, COUNT(*) | Datos |
| Viviendas GEIH 2018 | 227,027 | idem, COUNT(DISTINCT ID_VIVIENDA) | Datos |
| Personas con código de área (municipio) | 610,439 | idem, MUNICIPIO NOT NULL | Datos |
| Municipios con área en 2018 | 23 | idem, COUNT(DISTINCT CODIGO_MUNICIPIO) | Datos |
| PET / PEA / OC / DS / PEI (registros 2018) | 628,486 / 390,060 / 348,015 / 42,045 / 238,426 | idem, SUM de indicadores | Datos |
| Registros por módulo 2018 | CG 762,753; FT 628,486; OC 348,015; NO 42,045; INI 213,501 + 24,925 = 238,426 | `geih_plata.*_consolidado` PER=2018; `geih_bronce.inactivos_{cabecera,resto}_marco_antiguo` | Datos |
| Registros de factores de expansión CNPV 2018 | 772,619 | `geih_plata.dim_fex` | Datos |
| Registros 2025 (marco nuevo, no usados) | 135,810 en 2 meses | `geih_oro.mercado_laboral` PER=2025 | (no se cita) |
| Filas de dim_dominio_geih | 52 (32 capitales; 27 filas de dominios A.M.) | `dim.dim_dominio_geih` | Datos |
| Dominios con estimación | 23 (7 A.M. + 16 ciudades); 43 municipios miembro | `preprocesamiento.tasa_desempleo_municipal` (N_MUNICIPIOS) | Datos |
| PEA 15+ y viviendas por dominio | Tabla tab:dominios_geih; totales 314,744 y 163,149 | idem (N_PEA, N_VIVIENDAS) | Datos |
| Capitales sin código de área en 2018 | 9 (Arauca, Inírida, Leticia, Mitú, Mocoa, Puerto Carreño, San Andrés, San José del Guaviare, Yopal) | anti join dim_dominio_geih vs tasa_desempleo_municipal; 0 registros con esos códigos en mercado_laboral 2018 | Datos |
| Municipios objetivo | 83 (41 Cauca, 42 Valle; 2 con dominio padre) | `preprocesamiento.municipios_sin_encuesta` | Datos |
| TerriData bronce | 13,147,390 registros; 1,135 entidades; 1,587 indicadores; 24 dimensiones; años 1985-2070 | `terridata.terridata_bronce` | Datos |
| TerriData Cauca y Valle 2018 | 86 entidades, 784 indicadores con dato | idem WHERE CODIGO_DEPARTAMENTO IN ('19','76') AND ANO=2018 | Datos |
| Diccionario de indicadores | 1,582 | `dim.dim_indicadores` | (no se cita) |
| Tabla ancha de TerriData | 1,588 columnas | information_schema | (no se cita) |
| DIVIPOLA | 1,122 registros | `dim.dim_divipola` | Datos |
| Anexo DANE | nacional 72 (2016-2021); ciudades 1,800 (25 series × 72 trimestres móviles); anuales 30 | `geih_bronce.datos_{nacionales,municipales,anuales}` | Datos |
| Covariables candidatas y su regla | 18 (12 exactas, 5 proxy, 1 convención) | `preprocesamiento.reglas_agregacion_covariables` | Datos |
| Catálogo de literatura | 24 entradas (18 activas + 6 excluidas) | `preprocesamiento.catalogo_literatura` | Datos |

## 3. Cálculos propios pendientes de ejecutar (parte 2)

Corren en local con lectura de solo lectura de tablas `tesis.*` (o salidas extraídas de los notebooks);
el script va en `_trabajo/calculos/`. Su método está en el Marco teórico y en Metodología (etapas 13 y 16).

| Id | Cálculo | Tablas de entrada | Fórmula (Marco) | Etapa |
|---|---|---|---|---|
| C1 | SEBLUP, ECM y CV de los 23 dominios en el escenario de referencia (knn3, «completa») y γ^S_d | `preprocesamiento.tasa_desempleo_covariables` (Y, SE), `preprocesamiento.covariables_seleccionadas`, coordenadas de `dim.dim_geih_divipola` y `preprocesamiento.municipios_sin_encuesta`; reajuste local con `FayHerriotEspacial` de `code/modelo/shared` (500 réplicas, semilla 42) | `eq:seblup`, `eq:gamma_esp`, `eq:cve`; ECM por bootstrap (Morales p. 494) | 13 |
| C2 | Diferencia espacial − clásico en los 83 municipios: media, máximo absoluto, Pearson, Spearman; cambios de clase de CV (5/20) | `modelo.fhe_prediccion_objetivo` (PRED_CLASICO, PRED_ESPACIAL, CV_CLASICO_PCT, CV_ESPACIAL_PCT) | `eq:pearson`, `eq:spearman`, `eq:cve` | 13 |
| C3 | Lo mismo en los 23 dominios (EBLUP frente a SEBLUP) | `modelo.fay_herriot_resultados` (EBLUP, CV_EBLUP_PCT) + salida de C1 | idem | 13 |
| C4 | I de Moran de las 83 estimaciones finales con W de 3 vecinos estandarizada por filas, p por 9,999 permutaciones | `modelo.fay_herriot_estimaciones_finales` (NIVEL = MUNICIPIO); coordenadas de `fhe_prediccion_objetivo`; `proximidad_knn`, `estandarizar_filas`, `moran_i` de `code/modelo/shared/matriz_proximidad.py` | `eq:moran` | 16 |

Si C1 no reproduce el ρ̂ y el σ̂²_u del notebook, se reporta solo C2 y la incertidumbre de los dominios
espaciales queda como limitación en el reporte final.

### 3b. Cálculos propios ejecutados (parte 2, 2026-11-03)

Scripts: `calculos/descargar_tablas.py` (SELECT de solo lectura con la CLI de Databricks → `calculos/datos/*.csv`)
y `calculos/comparacion_espacial.py` (→ `calculos/salidas/`). Ejecución: `python -I comparacion_espacial.py code
<datos> <salidas>` con el venv del proyecto; ≈ 3 min.

| Id | Resultado | Archivo |
|---|---|---|
| C1 | Reproduce el notebook: ρ̂ = 0.372, σ̂²_u = 4.825 (clásico 5.529), 500/500 réplicas. CV mediano SEBLUP 2.60 % (máx. 3.25 %) frente a 2.60 % del EBLUP; ECM medio 0.091 frente a 0.090; γ^S_d entre 0.964 y 0.991 (media 0.982) frente a γ_d medio 0.984; ECM del SEBLUP menor que el del EBLUP en 11 de 23 | `salidas/c1_seblup_dominios.csv`, `resumen_comparacion.json` |
| C2 | 83 municipios: diferencia media −0.03 pp, media absoluta 0.22 pp, máx. absoluta 2.79 pp (Cali), 8 con abs > 0.5 pp; Pearson 0.992, Spearman 0.987; CV mediano 19.49 vs 19.87 %; 8 cambian de clase (7 de no confiable a aceptable, 1 al revés) | `salidas/c2_diferencias_municipios.csv` |
| C3 | 23 dominios: diferencia media 0.00 pp, media absoluta 0.01 pp, máx. 0.02 pp; Pearson 1.000, Spearman 1.000; ninguno cambia de clase | `resumen_comparacion.json` |
| C4 | Moran de las 83 estimaciones finales (kNN 3): I = 0.265, E[I] = −0.012, p = 0.001 (9,999 permutaciones); sin ajuste I = 0.256, p = 0.001; tasa de homicidios de los mismos municipios I = 0.256, p = 0.001 (idéntico al sintético: la estimación es lineal en esa covariable) | `resumen_comparacion.json` |

## 4. Cifras de Resultados (parte 2)

Fuente (1) = tabla `tesis.*` descargada a `calculos/datos/`; (2) = notebook extraído en `notebooks/` (corrida
2026-10-31). Todas coinciden donde hay ambas.

| Cifra | Valor | Fuente | Sección |
|---|---|---|---|
| Personas con FEX ≤ 0 o nulo | 0 de 762,753 (2018) | (2) `ingesta_geih__geih_oro` celda 3 | res_limpieza |
| Llaves sin pareja | 0 % en todos los módulos; 9,866 de 772,619 registros de factores (1.28 %) sin persona en características generales (1.15-1.44 % por mes) | (1) `geih_oro.llaves_sin_pareja`; (2) celda 4 | res_limpieza |
| Reconciliación | 288 celdas año-mes-dominio; PET 628,486 = PEA 390,060 + PEI 238,426; PEA = OC 348,015 + DS 42,045; 0 celdas que rompan; 0 personas OC y DS | (1) `geih_oro.reconciliacion_fuerza_trabajo` | res_limpieza |
| Bandera PEA = OC + DS por mes | 12 de 12 meses, diferencia 0 | (2) ventana celda 2 | res_limpieza |
| Pre-filtrado | 1,582 → 509 (completitud) → 497 (variabilidad); 12 por variabilidad; sensibilidad 475-499; 19 grupos duplicados (140 excedentes) | (2) `pre_filtrado` celdas 3-10 | res_prefiltrado |
| Estimación directa | Tabla por dominio: TD, SE bootstrap y Taylor, CV, desocupados; 23/23 confiables; CV 2.01-3.23 %; SE 0.20-0.44 pp; razón SE boot/Taylor mediana 1.000 (0.969-1.026); 23/23 = DANE (máx. dif. 0.0005 pp); agregado 10.8340 = Total 23 | (1) `tasa_desempleo_municipal`, `auditoria_dominios`; (2) estimación directa celdas 4-6 | res_directa |
| Sensibilidad de la ventana | mes/trim./año: PEA mín. 681/2,156/8,997; CV mediano 9.26/5.37/2.62 %; clases 0-23-0 / 7-16-0 / 23-0-0; razón SE mes/año 3.62, trim./año 2.00; corr. trim.-año 0.95, dif. media 0.78 pp | (2) ventana celdas 6-8 | res_directa |
| Sensibilidad A.M. a la regla PET | densidad 67.67 %, VA secundario 43.94 %, VA primario 14.23 %, VA terciario 8.04 %, demás < 1 % | (2) adición celda 6 | res_covariables |
| Univariado respuesta | media 11.54 %, mediana 11.31 %, 8.15 (Barranquilla A.M.) a 17.81 (Quibdó); asimetría 0.67; corr. SE-tasa 0.86 | (2) descriptivo celdas 5-9 | res_descriptivo |
| Bivariado | 0 con abs(r) ≥ 0.5; 10 entre 0.3 y 0.5; 6 pares con abs(r) ≥ 0.8 | (2) descriptivo celdas 16-21 | res_descriptivo |
| Selección | FH univariado: q ≤ 0.10 en 3 (homicidios, acueducto, cobertura media, q = 0.079); robustez «depende de un dominio» 12/18 (Quibdó 14 veces influyente); soporte ≥ 0.80 solo acueducto (0.867); homicidios 0.747; 14 grupos; seleccionadas homicidios + acueducto; VIF 1.984; misma selección exigiendo el signo | (2) EDA celdas 3-23 | res_seleccion |
| Especificaciones EC | ver Tabla de especificaciones (AIC, AICc, p, σ̂²_u, RMSE dejar-un-dominio-fuera) | (1) `fh_seleccion_modelo`; (2) FH celdas 8-10 | res_fh_clasico |
| Benchmark EC3 | β0 = 9.191 (EE 0.979); β1 = 0.099 (EE 0.036; p = 0.006); σ̂²_u = 5.529; R² 0.269; γ medio 0.984 (0.966-0.993); reducción media del ECM 1.16 % | (1) `fh_coeficientes`; (2) FH celda 8 | res_fh_clasico |
| Diagnósticos EC3 | media resid. 0.002; sd 0.977; SW W = 0.954, p = 0.357; Cook máx. 0.601 Quibdó, Cali A.M. también > 4/n | (2) FH celda 8 | res_supuestos |
| Sin Quibdó | β1 0.061 (−38.2 %, −1.05 EE), p = 0.256 | (2) FH celdas 15, 23 | res_supuestos |
| Bootstrap de dominios | IC [0.011, 0.191]; mismo signo 98.6 %; p < 0.05 en 70.4 % | (2) FH celda 17 | res_supuestos |
| LOAO efectos | EBLUP máx. 0.05 pp; sintético máx. −7.65 pp (Corinto, sin Quibdó); 10 exclusiones > 0.5 pp; σ̂²_u cambia ≤ 11 % | (2) FH celda 23 | res_supuestos |
| Varianza | ψ viviendas/personas mediana 1.104 (0.939-1.173); boot/Taylor 1.000 (0.938-1.053); GVF A R² 0.970; GVF B 0.976; 9 escenarios: mismo ganador; Â/ψ̄ 19.5-184.2; γ mín. 0.902-0.989; EBLUP máx. 0.195 pp; sintético máx. 0.125 pp; ψ × 3 cambia 4 dominios a aceptable | (1) `sensibilidad_varianza_fh`; (2) sens. var. | res_supuestos |
| Validación | ver tabla (RMSE 2.52 / 3.43 / 2.77; habilidad 0.17 / −0.54); dentro de muestra 2.27; 14/23 reproducen; 6 conjuntos; 4 sin covariables; frecuencias | (1) `fh_validacion_cruzada_metricas`; (2) FH celda 25 | res_validacion |
| Espacial | ver `fhe_comparacion_modelos` (8 filas), Moran, validación; vecindad: mediana 46.3 km (Cauca), 44.6 (Valle); vecino entre dominios 30-158 km (mediana 106); perfil ρ knn3 IC [−0.15, 0.75] | (1) `fhe_*`; (2) espacial | res_espacial |
| Extrapolación | 21/83 fuera del rango (3 por debajo, 18 por encima; 0 combinación atípica); aporte mediana 1.4 pp, máx. 14.84 (Corinto); 10 superan 17.8 %; franja LOAO 4.30 vs 0.79 pp | (2) FH celda 21 | res_sin_muestra |
| Benchmarking | λ1 = 0.999745 (10.8368 → 10.8340); λ2 = 0.8077 (14.4711 → 11.6890); brecha −0.0039 pp; Cali 14.36 → 11.60 (CV 18.20 → 29.96); Yumbo 16.96 → 13.70 (18.32 → 30.03) | (2) FH celdas 19, 26, 31 | res_benchmarking |
| Tabla final | 83 municipios: 32 aceptable, 30 no confiable, 14 aceptable extrapolado, 7 no confiable extrapolado; tasa 9.19-31.17 % (mediana 13.29); CV 18.07-30.03 %; Cauca media 14.16 (13 extrapolan), Valle 14.18 (8) | (1) `fay_herriot_estimaciones_finales` | res_benchmarking, res_patrones |

Discrepancia anotada: la celda 15 del notebook espacial imprime un texto fijo («el clásico pasa de RMSE 2.08 a
3.08») que no corresponde a la corrida vigente (2.52 → 3.43); no se usa.
| Población urbana de los municipios objetivo | mediana 45.07 %; 47 de 83 por debajo de 50 %; 61 por debajo del mínimo de los dominios (67.07 %) | (1) `preprocesamiento.municipios_sin_encuesta`, columna 020040003 (SELECT en la sesión) | dis_alcance |
| Distancia mediana municipio-dominio | ≈ 45 km (46.3 Cauca, 44.6 Valle) | (1) `fhe_vecindad` / (2) espacial celda 5 | dis_espacial |
