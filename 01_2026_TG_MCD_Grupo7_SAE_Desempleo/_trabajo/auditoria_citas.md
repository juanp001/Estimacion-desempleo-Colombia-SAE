# Auditoría de citas

Fuente de cada verificación: RAG local (skills `consultar-*`). «pág.» = página impresa; «PDF» = página
del archivo cuando el documento no trae numeración propia. Los textos completos consultados están en
`_trabajo/fuentes/` (`morales/p_*.txt`, `audit_q1.txt`, `audit_q2.txt`).

Decisión: **M** = se mantiene; **C** = se corrige (texto, página o entrada bib); **E** = se elimina;
**N** = cita nueva agregada en la parte 1; **P** = pendiente de verificar (no está en ningún RAG).

## 1. Citas que tenía el documento antes de la parte 1

### Cita [9] marcada por la directora

Orden de primera aparición calculado sobre `introduction → planteamiento → formulacion → objetivos →
marco-teorico → antecedentes` (orden de `main.tex`, estilo IEEE numérico): [1] Molina2019, [2]
FayHerriot1979, [3] VargasLemusAlejo2018, [4] ColeyTellez2024, [5] MendozaZea2019, [6] DNP2019, [7]
DANE_GEIH_Glosario, [8] Cochran1977, **[9] BernalGonzalez2017**. Coincide con lo que dice el prompt.
Falta confirmarlo contra el PDF compilado (la parte 2 reescribe la introducción y el orden cambia).

`BernalGonzalez2017` sí dice (pág. VIII, PDF 10) que «Fay y Herriot (1979) estimaron el ingreso per
cápita en áreas pequeñas de Estados Unidos a partir de un modelo lineal mixto», pero es fuente
secundaria. **Decisión C**: el origen del modelo se cita a `FayHerriot1979`.

### Tabla de auditoría

| Clave | Dónde (archivo:línea antes de editar) | Qué se le atribuye | Verificación (página y frase) | Decisión |
|---|---|---|---|---|
| BernalGonzalez2017 | antecedentes:15 | Origen del FH (1979), ingreso per cápita EE. UU. | pág. VIII: «Fay y Herriot (1979) estimaron el ingreso per cápita en áreas pequeñas de Estados Unidos…» (fuente secundaria) | C → `FayHerriot1979` |
| BernalGonzalez2017 | antecedentes:19 | Estimador completamente bayesiano beta, hogares con carencias, UPZ de Bogotá | pág. IV (índice de tablas: modelo CBB, carencias de la niñez y la juventud por localidad) y pág. 34 (UPZ) | M, con página |
| BernalGonzalez2017 | marco-teorico:155 | SAE: diagnóstico del modelo, medidas estables de variabilidad | pág. 2: modelos basados en modelos permiten «diagnóstico del modelo… medidas estables de variabilidad para cada área» (cita a Rao 2003) | M, `\cite[p.~2]` |
| BernalGonzalez2017 | marco-teorico:175 (x2) | Estimadores directos: solo información del dominio; asistidos por modelos siguen siendo directos | pág. 1: «los estimadores directos usan la información únicamente de las unidades seleccionadas en el dominio… errores estándar inaceptablemente altos»; asistidos por modelos «permanecen basadas en el diseño muestral» | M, `\cite[p.~1]` |
| BernalGonzalez2017 | marco-teorico:400 | Modelos SAR/CAR reducen el CV | No lo dice (solo «se pueden incorporar estructuras de dependencia espacial», pág. 2) | E en esa frase |
| (entrada bib) BernalGonzalez2017 | refs.bib | Autores «Bernal, L. K. and González, L. M.» | Portada (PDF 2): autora Luz Karime Bernal Muñoz; Luz Mery González García es la directora | C: autor único «Bernal Muñoz, L. K.»; tesis de Maestría en Ciencias, Bioestadística |
| ColeyTellez2024 | marco-teorico:46 | Las variables auxiliares reducen el error | No se encontró esa frase; el artículo usa variables auxiliares en un FH espacial (PDF 1) | C: se reemplaza por `Molina2019` (PDF 19) y `morales2021smallarea` (p. 427) |
| ColeyTellez2024 | marco-teorico:175 | Estimadores directos insuficientes en desagregaciones no planeadas | PDF 2: «si se requiere una desagregación mayor… estos estimadores pueden ser insuficientes en términos de precisión» | M |
| ColeyTellez2024 | marco-teorico:400 | FH espacial reduce el CV | PDF 1-4: propone el FH espacial de Pratesi y Salvati (2008) para dominios no observados; la mejora se reporta en su aplicación PISA | M solo en antecedentes (como aplicación), E del marco |
| ColeyTellez2024 | antecedentes:21 | TRI + valores plausibles + FH espacial, PISA 2018 | PDF 1 y 3: confirma | M |
| (entrada bib) ColeyTellez2024 | refs.bib | Autor «Coley, C. J.» | PDF 1: «Jiménez Coley, C., and Tellez-Piñerez, C. (2024)» | C |
| Molina2019 | marco-teorico:156 | Demanda por ODS | PDF 11: «el marco global de indicadores para el seguimiento de los Objetivos del Desarrollo Sostenible plantea que la información debe ser desagregada…» | M, `\cite[p.~9]` (página impresa 9 = PDF 11) |
| Molina2019 | marco-teorico:164 | Modelos de área y de unidad; FH | PDF 19 (pág. 17): «Existen dos grandes grupos… modelos a nivel de área y… a nivel de individuo… modelos Fay-Herriot (FH)» | M |
| Molina2019 | marco-teorico:211 | Bootstrap simple de la directa | No: la pág. 22 (PDF 24) da el estimador de varianza de `direct()` sin probabilidades de segundo orden, no un bootstrap | C: el bootstrap se sustenta en Morales pp. 26-27 y 61 |
| Molina2019 | marco-teorico:512 | Umbrales de CV | PDF 16-17 (pág. 14-15): «algunos Institutos Nacionales de Estadística coinciden en establecer un dato como “no publicable” cuando su… CV supera un 20 %» | M para el 20 %; el 5 % va a GEIH v9 PDF 12 |
| Molina2019 | antecedentes:17 | CEPAL, FH en Montevideo «superando la escasez en municipios no cubiertos» | PDF 6-7 (gráficos 16-19): FH y Census EB para ingresos medios e incidencia de pobreza en las D = 25 secciones censales de Montevideo, por sexo | C: se quita «municipios no cubiertos»; Montevideo es un ejemplo del documento, no un estudio de la CEPAL aparte |
| Tellez2020 | marco-teorico:512 | Umbrales de CV 5/20 | No se encontró; pág. 15 (PDF 33) trata el deff | C: se quita de esa fila; se conserva para el deff (GVF B) `\cite[p.~15]` |
| RaoMolina2015 | marco-teorico:516-540 | Media de residuos, Shapiro, VIF 5/10, R_d, cota D/5 | No está en ningún RAG y varias atribuciones no corresponden (la cota D/5 y los cortes de VIF no son de ese libro) | E de esas filas. Se reemplaza por Morales, Montgomery-Peck-Vining (VIF), Shapiro-Wilk (1965) y convención propia (cota n//10). La entrada queda solo si la parte 2 la usa |
| Cochran1977 | marco-teorico:93, 520 | Regla 1.5·IQR; Cook 4/n | No está en el RAG; la regla 1.5·IQR es de Tukey (diagrama de caja) y 4/n no es de Cochran | E. 1.5·IQR y 4/n quedan como convenciones de inspección (descriptivas) |
| morales2021smallarea | marco-teorico:204 | Hájek consistente, aprox. insesgado | pág. 21-22 (§2.4): razón de estimadores directos consistentes es aproximadamente insesgada; ejemplo de parámetro razón: la tasa de desempleo | M, `\cite[pp.~21--22]` |
| morales2021smallarea | marco-teorico:364 | Prasad-Rao, g1, g2, g3 | pág. 440: g1, g2; g3 para REML (Datta y Lahiri) = ψ²/(A+ψ)³·avar(Â), avar = 2(Σ(A+ψ)⁻²)⁻¹; estimador g1+g2+2g3 (pág. 440-441, «the coefficient 2 stands for bias correction») | M con página. Corrige: el «2» no es «corrección de segundo orden» sino corrección de sesgo del estimador del ECM |
| morales2021smallarea | marco-teorico:514, 532 | ΔAIC <2 / 2-7 / >10 | pág. 453-454 no da cortes de AIC; `modelo/shared/config.py:172` lo declara convención externa | C: ΔAIC ≤ 2 = convención (propuesta de cita: Burnham y Anderson 2002, p. 70, P) |
| PrasadRao1990 | marco-teorico:364 | Aproximación del ECM | Morales pág. 440 lo atribuye a Prasad y Rao (1990) | M |
| FayHerriot1979 | marco-teorico:253 | Modelo FH | Morales pág. 419-424; Molina PDF 19 | M |
| Montoya2019 | marco-teorico:247 | EBLUP y REML | pág. 6 (PDF 17): REML «tiene en cuenta la pérdida de grados de libertad… estimadores insesgados de los parámetros de varianza» | C: se cita Morales pp. 434-437 para REML; Montoya queda en antecedentes |
| Montoya2019 | marco-teorico:253 | FH «el más influyente» | pág. VII lo lista entre tres modelos; no dice «el más influyente». Bernal pág. VIII: «posiblemente el modelo más famoso» | C → `BernalGonzalez2017` pág. VIII |
| (entrada bib) Montoya2019 | refs.bib | «Montoya, S. M.», tesis de doctorado | Portada: Daniela Vélez Montoya, Magíster (c), Universidad Nacional, marzo 2019 | C: `mastersthesis`, autora «Vélez Montoya, D.» |
| BatteseHarterFuller1988 | marco-teorico:410 | Modelo a nivel de unidad | RAG battese1988 | M (solo si se conserva la mención en antecedentes) |
| Schworer2004 | marco-teorico:474 | Moran en mercado laboral | No está en ningún RAG | E. Moran se cita a Moran (1950) y su uso con residuos de FH a Pratesi y Salvati (2008, p. 130) |
| DANE_GEIH_Glosario | marco-teorico:18-22 | PEA, DS, TD | El glosario no está en el RAG; las mismas definiciones están en la metodología GEIH v9, PDF 5-6 y 20 | C: se cita `DANE_GEIH_Metodologia2016` (PDF 20); el glosario queda como P |
| MendozaZea2019 | antecedentes:17 | FH espacial, desempleo e ingreso en Cundinamarca; «puntajes de pruebas académicas»; «más efectiva que las directas, en especial el ingreso» | PDF 1: componentes principales de ~40 variables auxiliares como covariables de FH y FH espacial; PDF 13: «leve mejora en los CVE del FH espacial»; ECM medio 4.40 (FH) vs 4.21 (FH espacial) | C: se reescribe con lo que dice (PCA, mejora leve) |
| MarinTralmaGuerrero2024 | antecedentes:19 | EBLUP comunal, arcoseno, ENUSC | PDF 31 y 40: arcoseno; PDF 23: benchmarking con el factor de Fay y Herriot | M |
| TellezTrujilloPedraza2020 | antecedentes:21 | Coeficientes de regresión con valores plausibles y FH multivariado en departamentos | Esa descripción es la de Guerrero (2019), PDF 18 y 70 (TIMSS/Icfes, FH multivariado). TellezTrujilloPedraza2020 no está en ningún RAG | C → `GuerreroTrujillo2019` |
| (entrada bib) GuerreroTrujillo2019 | refs.bib | «Guerrero, S. and Trujillo, L.» | Portada: Stalyn Yasid Guerrero Gómez; director Leonardo Trujillo | C: autor único «Guerrero Gómez, S. Y.» |
| INEChile2016 | antecedentes:23 | Casen, suavizado Potter, shrinkage, pobreza comunal | chile_pobreza2016 PDF 3: «Paso 1: Suavización de factores de expansión… método de Potter (2003)» | C bib: autor Ministerio de Desarrollo Social, Serie Documentos Metodológicos 32 (no INE) |
| VargasLemusAlejo2018, DNP2019 | introducción, planteamiento | (parte 2) | vargas2018 está en el RAG; DNP2019 no | P para la parte 2 |
| VanDerLeeden1997 | metodologia:458 | Bootstrap | No está en el RAG; es bootstrap para modelos de dos niveles, no para encuestas | E; bootstrap → Morales pp. 26-27 y 61 |
| ArroyoMina2016 | metodologia:531 | Elegibilidad conceptual de covariables | arroyo2017 en el RAG (calidad del empleo en Cali); no respalda la regla de elegibilidad | C: la regla se sustenta en Morales pp. 453-454 («relación… interpretable de acuerdo con las leyes de la ciencia»); Arroyo queda para el signo esperado si el catálogo lo usa |

## 2. Sustento de las decisiones metodológicas (base para Marco teórico, Metodología y parte 2)

| Decisión / concepto | Cita | Página | Frase o contenido de apoyo |
|---|---|---|---|
| PET, PEA, PEI, OC, DS; desempleo abierto y oculto | DANE_GEIH_Metodologia2016 | PDF 5, 20 | Definiciones; DO: «no hicieron diligencias en el último mes, pero sí en los últimos 12 meses y tienen una razón válida de desaliento» |
| TD = DS/PEA·100 | DANE_GEIH_Metodologia2016 | PDF 6, 20 | «Relación porcentual entre el número de personas que están buscando trabajo (DS) y… la fuerza laboral (PEA)» |
| Dominios: 13 ciudades con A.M. y su membresía | DANE_GEIH_Metodologia2016 | PDF 9 | Lista: Medellín-Valle de Aburrá, Cali-Yumbo, Barranquilla-Soledad, Bucaramanga-Floridablanca-Girón-Piedecuesta, Manizales-Villamaría, Pereira-Dosquebradas-La Virginia, Cúcuta-Villa del Rosario-Los Patios-El Zulia… |
| Publicación anual por ciudad con A.M.; trimestral 24 ciudades | DANE_GEIH_Metodologia2016 | PDF 9, 19 | «Anuales: por ciudad capital con su área metropolitana…» |
| Diseño: probabilístico, estratificado, de conglomerados; inclusión forzosa | DANE_GEIH_Metodologia2016 | PDF 11 | Estratos de certeza e inclusión probabilística con PPT |
| Meta de precisión: ESrel ≤ 5 % para TD de 10 %, con deff | DANE_GEIH_Metodologia2016 | PDF 12 | «precisión deseada de la variable tasa de desempleo no superior a un error estándar relativo del 5% y una tasa de desempleo del 10%» |
| Varianza de una razón por linealización de Taylor; CV | DANE_GEIH_Metodologia2016 | PDF 15 | «se utiliza el método de Linealización de Taylor» |
| Factores de expansión marco 2005 recalibrados con CNPV 2018 (PET 15+) | DANE_GEIH_Series2022 | PDF 3, 19 | «Nuevos factores de expansión GEIH 2005… Proyecciones de población según CNPV 2018. Calibración para PET de 15 años y más» |
| CV > 20 % no publicable | Molina2019 | PDF 16-17 | ver arriba |
| Estimador de razón (Hájek) | morales2021smallarea | pp. 21-22 | §2.4; la tasa de desempleo como parámetro razón |
| Bootstrap para varianza | morales2021smallarea | pp. 26-27 (§2.6) | Remuestreo para varianza de estimadores directos |
| Bootstrap por conglomerados (viviendas) en encuesta de fuerza laboral | morales2021smallarea | p. 61 | (citado en `preprocesamiento/shared/bootstrap.py`; página verificada por la sesión que escribió el código, P de lectura literal en esta sesión) |
| FH: modelo de muestreo y de enlace | morales2021smallarea | pp. 424-427, 490 | (18.1) «linking model», (18.2) «sampling model», σ²_d conocida |
| ψ_d conocida | morales2021smallarea | p. 427 | «we equate σ²_d = varπ(y_d) and treat them as known constants» |
| GVF A | morales2021smallarea | p. 427 (ec. 16.6), 454-455 | log var = b0 + b1 y_d + b2 n_d |
| GVF: retransformación y estabilidad | MarinTralmaGuerrero2024 | PDF 15-16, 29 | Modelo log ψ_d = x'α + ε (Dick 1995; Beaumont y Bocci 2016) |
| GVF B (deff) | Tellez2020; INEChile2016 (Chile 2016) | p. 15; PDF 4 | Var(ρ̂) = ρ(1−ρ)/n·Deff |
| EBLUP: γ_d y casos límite | morales2021smallarea | p. 427 | Directa precisa → EBLUP ≈ directa; poco precisa → ≈ sintético |
| REML | morales2021smallarea | pp. 434-437 (§16.5.4) | |
| ML | morales2021smallarea | pp. 432-433 (§16.5.3) | |
| ECM de Prasad-Rao, g3 de Datta-Lahiri para REML, estimador g1+g2+2g3 | morales2021smallarea; PrasadRao1990 | pp. 440-441 | ver tabla 1 |
| Predictor sintético y su ECM fuera de muestra x'(X'V⁻¹X)⁻¹x + σ²_u | morales2021smallarea | pp. 441-442 | Remark 16.3: «If d ∈ D1, then u_d and β̂ are independent… MSE ≈ x_d(X'0V0⁻¹X0)⁻¹x'_d + σ²_u» |
| Fuera de muestra el estimador es X_r β̂ | Benedetti2024 | p. 144 | (citado en código; P literal) |
| Sintético: sesgo si el modelo falla, varianza engañosa | Molina2019 | PDF 37-41 | PDF 39: el sesgo del sintético «no disminuye al aumentar el tamaño muestral» |
| Selección: todas las covariables significativas al predecir fuera de muestra; excepción interpretable; interpretabilidad | morales2021smallarea | pp. 453-454 | «If we want to predict out-of-sample values, it is not convenient to over-parameterize… It is recommended to use a model where all the auxiliary variables are significant… p-values lower than 0.05»; p. 454: excepción con interpretación razonable |
| Prueba z (Wald) de β̂ | morales2021smallarea | p. 272 | (citado en código; P literal) |
| Control de la tasa de falsos descubrimientos | BenjaminiHochberg1995 | pp. 289-300 | N (entrada nueva; fuera del RAG, referencia original del método) |
| VIF > 5 o 10 indica coeficientes mal estimados | MontgomeryPeckVining2012 | sec. 9.4.3 | N; fuera del RAG (P literal) |
| Extrapolación oculta (h_new > máx h_ii) | MontgomeryPeckVining2012 | sec. 3.8 | N; fuera del RAG; citado así en `extrapolacion.py` (R-66) |
| Shapiro-Wilk | ShapiroWilk1965 | — | N; método original |
| Distancia de Cook | Cook1977 | — | N; método original. Umbral 4/n = convención de inspección (no se cita) |
| I de Moran | Moran1950; PratesiSalvati2008 | —; p. 130 | N; Pratesi-Salvati usan Moran y Geary para detectar patrón espacial |
| AICc | HurvichTsai1989 | — | N; el código lo declara convención externa a Morales (G7-B16) |
| ΔAIC ≤ 2 = equivalentes | (convención) | — | `modelo/shared/config.py:172`: «el libro no fija un umbral de ΔAIC». Propuesta: BurnhamAnderson2002 p. 70 (P, decidir con el equipo) |
| Cota n // 10 | (convención) | — | `preprocesamiento/shared/config.py`: «convención externa al libro»; Morales p. 453 solo pide no sobreparametrizar |
| Soporte 0.80; LOAO 1 EE y 0.5 pp; |λ−1| > 0.20 | (convención) | — | config |
| FH espacial SAR, W estandarizada por filas, contigüidad o distancia | morales2021smallarea | pp. 490-491 | «The two main approaches used for weights definition are based on contiguity of domains or on distance between domains… W… row standardized… ρ ∈ (−1, 1)» |
| ML y REML del SAR | morales2021smallarea | pp. 492-494 | |
| ECM del SEBLUP por bootstrap paramétrico | morales2021smallarea | p. 494 (§18.2.3) | González-Manteiga et al. (2010) extendido |
| SAR en SAE, correlación que decae con la distancia | PratesiSalvati2008 | p. 114 | «there is no reason to exclude the assumption that the random effects between the neighboring areas are correlated and that the correlation decays to zero as distance increases» |
| MML para áreas fuera de muestra; difiere de Saei-Chambers | Benedetti2024 | pp. 142, 146-149 | p. 142: el SEBLUP estándar supone datos en todos los dominios; §3 MML |
| Benedetti: desempleo en LLMA de Italia | Benedetti2024 | pp. 140-141, 155 | |
| Â/ψ̄ y subestimación de ψ | Benedetti2024 | p. 143 | «An underestimation of ϕi is usually more problematic when the variance of the random effect… is relatively small compared with ϕi» |
| Benchmarking: propiedad y ajuste de razón | Molina2019 | PDF 26, 78 | «un ajuste común es el de tipo razón» |
| Benchmarking con el factor de Fay y Herriot (1979) | MarinTralmaGuerrero2024 | PDF 22-23 | «se sigue el ajuste propuesto por Fay y Herriot (1979), multiplicando… por un factor de consistencia» |
| Benchmarking municipal ponderado por población (DANE) | DANE_SAE_2025 | PDF 25, 33 | «al agregar las estimaciones municipales ponderadas por el tamaño poblacional… se reproduzcan exactamente las estimaciones departamentales» |
| Benchmarking comunal-regional | Casen2024 | PDF 7 | «ajuste mediante un ratio» |
| Diferencias espaciales del desempleo en Colombia, clústeres | Diaz2016 | pp. 123-124, 162 | Modelo Durbin espacial; clústeres de desempleo 1993-2005 |
| Lenguaje de asociación | Diaz2016 | p. 155 | (citado en código R-35; P literal) |

## 3. Pendientes de esta auditoría

- Confirmar contra el PDF compilado que la cita [9] era `BernalGonzalez2017` (orden cambia con la nueva introducción).
- Leer literal Morales p. 61 y p. 272 y Benedetti p. 144 (citas del código no releídas en esta sesión).
- Decidir con el equipo si se cita Burnham y Anderson (2002) para ΔAIC ≤ 2 o se deja como convención.
- `ArroyoMina2016`: nombres completos de los coautores y DOI (no se pudieron leer en el RAG).
- DOI de `PratesiSalvati2008` y `PetrucciSalvati2006` escritos de memoria: verificar.
- `DANE_GEIH_Glosario`, `DNP2019`, `TellezTrujilloPedraza2020`, `RaoMolina2015`, `Cochran1977`, `Schworer2004`, `VanDerLeeden1997` quedan sin uso en los capítulos de la parte 1: la parte 2 decide si alguno se usa y, si no, se eliminan de `refs.bib`.

## 4. Citas de Antecedentes (parte 1, sesión 1)

Verificadas en `fuentes/antecedentes_q.txt` y `fuentes/audit_q1.txt`.

| Clave | Qué se le atribuye | Página y apoyo | Decisión |
|---|---|---|---|
| Benedetti2024 | FH SAR con verosimilitud marginal; desempleo en LLMA de Italia; estimaciones espaciales consistentes con las directas; contraste norte-sur | pp. 140-142, 146-149, 156 | N |
| Shiferaw2025 | Desempleo trimestral en 52 distritos de Sudáfrica, modelo espacio-temporal; CV menor que la directa en la mayoría | PDF 4, 19, 30 | N |
| Pereira2021 | Proceso puntual espacial bayesiano para el desempleo en Portugal | PDF 1-2, 12 | N |
| MendozaZea2019 | FH clásico y espacial, ~40 auxiliares resumidas en componentes principales, extrapolación fuera de muestra; mejora leve del espacial | PDF 1, 9, 13 | C (texto reescrito; bib: autor Mendoza Castrillón; tipo proyecto de grado) |
| Diaz2016 | Polarización y clústeres de desempleo municipal 1993-2005; Durbin espacial; demanda de trabajo y migración | pp. 123-124, 162 | N |
| GallegoMunoz2017 | Clústeres de informalidad en Medellín, Moran y regresión espacial | PDF 2, 20 | N |
| PetrucciSalvati2006 | SEBLUP aplicado a erosión | (título; RAG petrucci2006) | N |
| PratesiSalvati2008 | SEBLUP, ingreso en Toscana, Moran y Geary | pp. 114, 130 | N |
| Sikov2023 | Anemia y retraso del crecimiento en distritos pobres del Perú; residuos del FH con autocorrelación significativa que el espacial elimina | pp. 172, 194 | N |
| Haro2022 | Tesis sobre el mismo problema | PDF 1, 3 | N |
| RomeroLemus2018 | FH espacial, embarazo adolescente municipal | PDF 1, 10 | N |
| VargasLemusAlejo2018 | Consumo de basuco en UPZ de Bogotá; el espacial reduce 13 % el CV de los dominios observados | PDF 14 | C (bib: autores Ramírez Vargas, Lemus Polania, Alejo) |
| Duran2024 | Pobreza monetaria por UPZ de Bogotá, covariables geoespaciales, contigüidad, mapa completo | pp. 32-33 | N (autor Carlos Alberto Durán Gil, portada) |
| ColeyTellez2024 | Valores plausibles + FH espacial, PISA 2018 entre países | PDF 1, 3 | M |
| OrtizTellezRamirez2024 | Revisión de SAE en Colombia | pp. 407, 413 | C (bib: revista, volumen, DOI, autores) |
| BernalGonzalez2017 | Proporciones con beta y métodos bayesianos, carencias en Bogotá | pp. IV, 34 | M |
| GuerreroTrujillo2019 | Valores plausibles y FH multivariado, factores asociados Icfes | PDF 18, 70 | C (reemplaza a TellezTrujilloPedraza2020) |
| Montoya2019 | Bootstrap del ECM, localidades de Bogotá, Encuesta Multipropósito 2017 | pp. VIII, 26 | M |
| DANE_SAE_2025 | FH municipal con directas de la GEIH filtradas por calidad (392 de 587 municipios); benchmarking departamental ponderado por población | PDF 21-22, 25 | M |
| INEChile2016 | Suavizado de factores de expansión (Potter) en la pobreza comunal | PDF 3 | M |
| Casen2024 | Ajuste de consistencia comunal-regional | PDF 7 | N |
| MarinTralmaGuerrero2024 | Victimización comunal, EBLUP con arcoseno y ajuste de razón | PDF 23, 31, 40 | M |

El texto anterior de Antecedentes atribuía a la CEPAL una aplicación en Montevideo «en municipios no cubiertos» y mencionaba modelos ELL en Brasil sin cita: ambas frases se eliminaron.

## 5. Citas de la parte 2 (Planteamiento y formulación)

Verificadas con `consultar-geih` y `consultar-desempleo-colombia` (2026-11-03).

| Clave | Qué se le atribuye | Página y apoyo | Decisión |
|---|---|---|---|
| DANE_GEIH_Metodologia2016 | Desagregación de la GEIH: mensual (13 grandes ciudades, 11 intermedias, nacional), trimestral y semestral (ciudad con A.M., regiones, zona), anual además por departamento; el municipio no es dominio | PDF 9: «Anuales: Por ciudad capital con su área metropolitana, por grandes regiones y zona… y por departamentos» | N (uso nuevo) |
| DANE_GEIH_Metodologia2016 | Meta de precisión 5 % para TD de 10 % | PDF 12 (ya auditada) | M |
| Diaz2016 | 522 áreas urbanas, censos 1993 y 2005, polarización y clústeres; demanda de trabajo, inmigración y urbanización | pp. 124-125 (PDF 2-3): «if the municipal unemployment rate was either very high or very low… it tended to stay at that level… creation of unemployment clusters» | N (páginas nuevas) |
| Molina2019 | ODS piden desagregación geográfica | p. 9 (PDF 11), ya auditada | M |
| OrtizTellezRamirez2024 | SAE en Colombia: mayoría académica, uso oficial reciente | pp. 407, 413 (ya auditada) | M |
| DANE_SAE_2025 | FH municipal con directas de la GEIH | PDF 21-22 (ya auditada) | M |
| DNP2019 | Registros administrativos poco utilizables; restricción a gobiernos territoriales | No está en ningún RAG | E del planteamiento; queda sin uso en todo el documento → eliminar de `refs.bib` en la limpieza final |
| MendozaZea2019, VargasLemusAlejo2018 | El planteamiento anterior atribuía a Ramírez, Lemus y Alejo (consumo de basuco en Bogotá) el caso de Cundinamarca con la Encuesta Multipropósito 2017 | El caso es de Mendoza y Zea; ya está bien citado en Antecedentes | E del planteamiento (no se repite) |

Henao y Rojas (1999, `henao1999` en el RAG, PDF 10) documenta diferencias persistentes de la tasa natural entre ciudades (Bogotá 9.0 %, Medellín 13.3 %), pero no se citó: su entrada bibliográfica (volumen, número, páginas) no se pudo completar desde el RAG.
