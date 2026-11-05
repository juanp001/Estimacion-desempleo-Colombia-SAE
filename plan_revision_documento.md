# Plan de revisión del documento por rúbricas

Grupo 7, Maestría en Ciencia de Datos. Revisión del 03/11/2026 sobre `main.pdf` y los `.tex` de la rama `documento`. Los números `D-xx` son los de `revision_documento.xlsx`.

## 1. Resumen ejecutivo

El documento está bien construido en lo que más pesa: la metodología y los resultados están en espejo (17 títulos iguales, en el mismo orden), las cifras clave coinciden con las tablas de Databricks y el texto es honesto sobre los límites de las estimaciones. Revisé en vivo coeficientes, AIC, validación y tabla final, y comparé con las tablas descargadas las 23 filas de la estimación directa y las 83 municipales: no hay diferencias.

Lo que baja la nota es de otro tipo: el documento pasa de las 100 páginas, tiene algunas frases que contradicen sus propias tablas, parte del resultado no sale de la cadena reproducible y las figuras y la bibliografía todavía se ven desiguales. Casi todo se corrige sin tocar el modelo.

**Nota estimada: 3.44 sobre 4.25 del 85 % evaluable, equivalente a 4.05 sobre 5.0** sin la presentación oral. Es un juicio de revisión, no una predicción exacta del jurado, y se puede editar en la hoja Acta estimada.

| Criterio | Peso | Nota | Banda |
|---|---|---:|---|
| A-2.1 Procesamiento | 10 % | 4.4 | Alto |
| A-2.2 Modelado | 10 % | 4.0 | Intermedio |
| A-2.3 Evaluación del desempeño | 10 % | 4.4 | Alto |
| A-2.4 Rigurosidad y reproducibilidad | 10 % | 3.9 | Intermedio |
| A-2.5 Validez de resultados y conclusiones | 10 % | 3.8 | Intermedio |
| A-3.1 Tablas y figuras | 5 % | 3.6 | Intermedio |
| A-3.2 Referencias | 10 % | 3.7 | Intermedio |
| A-3.3 Marco teórico | 5 % | 4.4 | Alto |
| A-3.4 Ubicación de la información | 5 % | 3.8 | Intermedio |
| A-4 Desafío académico | 10 % | 4.3 | Alto |
| A-5 Presentación oral | 15 % | No evaluable | |

**Criterios excluyentes (A-1):** hay modelado y evaluación cuantitativa sin discusión. Objetivos y resultados prometidos se cumplen, pero con riesgo: 0 de 83 municipios confiables, modelo recomendado sin componente espacial y una asociación frágil. El documento no dice de forma explícita que cada objetivo se cumplió (D-06). Conviene revisarlo con la directora antes de entregar.

**Ajustes de nivel Alto:**

- **D-01** (A-3.4, confirmado): El documento supera las 100 páginas sin apéndice.
- **D-02** (A-2.5, confirmado): Afirma erróneamente que los municipios no limitan con dominios.
- **D-03** (A-2.4, confirmado): La tabla final sigue marcada como resultado preliminar.
- **D-04** (A-2.5, confirmado): La redacción descriptiva y de selección contradice sus tablas.
- **D-05** (A-2.3, confirmado): Presenta 17 % como mejora de RMSE, pero es ECM.
- **D-06** (A-1, plausible): Cumplimiento de objetivos expuesto ante criterio excluyente.
- **D-07** (A-2.4, confirmado): Etapa 16 y parte de la comparación fuera del pipeline.

Hay 7 de nivel Alto, 17 de nivel Medio, 16 de nivel Bajo y 4 opcionales.

**Límites de esta revisión.** No pude recompilar con la instalación local de MiKTeX, que falla con el paquete `ninecolors`; las páginas son las de `main.pdf`, cuya fecha interna es 03/11/2026 14:52, y el 96 % de las frases muestreadas de los `.tex` están en ese PDF (las demás son cortes de línea o de página en una revisión muestral). La evaluación de A-4 y de los criterios de redacción es juicio de revisión. No revisé los `.tex` frente a la totalidad de las páginas citadas: solo las que `control_cambios` dejó pendientes.

## 2. Hoja de estilo: decisiones antes de corregir

| Tema | Propuesta |
|---|---|
| Separador decimal | Punto para decimales y coma para miles, como ya fija `main.tex`. Corregir «100.000» y «10.000». |
| Decimales | Tasas, CV, errores y RMSE: 2. Coeficientes, AIC, σ̂², ρ̂, q, p, r y LRT: 3 (p < 0.001 cuando corresponda). Factores λ: 4 en tablas, y la misma cifra en el texto. Distancias en km: 1. Declararlo en la apertura de Resultados. |
| Unidades grandes | Pesos en millones en tablas y coeficientes, para no mostrar 0.0000 ni 15784533.33. |
| Cursiva | Solo términos extranjeros la primera vez que aparecen. Hoy no hay cursiva, y seguir sin usarla también cumple si se declara. |
| Comillas | «» solo para nombres de estructuras («muestra», «completa») y etiquetas reportadas. |
| Idioma de siglas | Español cuando existe uso consolidado (ECM, CV, EE, IC). Inglés con «por sus siglas en inglés» para EBLUP, SEBLUP, GLS, REML, SAR, GVF, AIC, LRT, VIF y MAE. Elegir **ECM y su raíz, RECM**, o mantener RMSE declarando que es la raíz del ECM: yo mantendría RMSE para no reescribir tablas. |
| Primera definición | Una vez en el Resumen, y otra en la Introducción. Las siguientes solo con sigla, también en captions, salvo la nota de abreviaturas de cada tabla que las use. |
| Nombres de variables | Usar los de `tab:app_variables`: «Índice de desempeño fiscal», «Densidad de población», «Población joven de 14 a 28 años», «Tránsito a la educación superior», «Saber 11, matemáticas». |
| Nombres de modelos | «Modelo de solo intercepto» (no «nulo», salvo «habilidad frente al nulo»), «Fay-Herriot clásico» y, una vez elegido, «benchmark» o «EC3»; «estimación sintética» para el resultado y «predictor sintético» para la fórmula. |
| Voz | Pasado impersonal en Introducción, Metodología, Resultados y Conclusiones. Presente para describir tablas y figuras y en el Resumen, por pedido de la directora. |
| Notación | D solo para número de dominios; R para un territorio con benchmarking; m para municipio; K para candidatas en BH; k solo para vecinos; ν para el multiplicador de ψ; ε solo para el error de validación; ρ_S en todas partes para Spearman. |
| Figuras | Azul `#1F4E79`, naranja `#C55A11` y gris `#7F7F7F`, con degradados de azul para secuencias y azul-naranja para divergencias. 200 dpi o más, sin títulos internos, grilla gris suave y texto de 9 pt o más al tamaño final. |

## 3. Orden de trabajo

**Primero, lo que depende del código** (cambia cifras y figuras que el texto cita):

1. D-03: cerrar el estado de la tabla final y repetir la consolidación.
2. D-07: llevar a `code/` los cálculos de la comparación y de la etapa 16, y correr la cadena una vez.
3. D-18 y D-20: añadir sensibilidad de q, Q-Q y residuos frente a ajustados.
4. D-10, D-11, D-12, D-40, D-42 y D-43: regenerar figuras con un solo módulo de estilo.
5. D-36: corregir el texto del notebook. Al cerrar, D-39: etiquetar la versión y citar la corrida.

**Luego, estructura y contenido:**

6. D-04, D-05 y D-02: corregir las frases con errores; son rápidas y de alto impacto, y pueden hacerse desde el primer día.
7. D-06 y D-15: reunión con la directora sobre cumplimiento de objetivos, listas de la estructura oficial (D-27), `openany` (D-01) y comparación aparte (D-34).
8. D-17, D-35 y D-44: mover o ajustar contenido. D-28, D-29, D-30, D-33, D-32 e D-38: reescrituras puntuales.
9. D-21 y D-22: localizar las fuentes del catálogo y corregir citas.
10. D-01: recortar. Va al final del contenido porque depende de lo anterior.

**Al final, formato y verificación de extensión:**

11. D-13, D-14, D-16, D-19, D-09 y D-08: pasada de estilo.
12. D-23, D-24, D-25, D-26, D-31, D-37 y D-41: limpieza de LaTeX.
13. Compilar y contar páginas.

**Automatizable con búsqueda y reemplazo:** D-23 (borrar `language`, corregir `p'{a}ginas`), D-41, D-31, D-37, parte de D-09 (100.000, 10.000) y de D-25 (paquetes), y los nombres de D-14, revisando cada reemplazo. **Requieren reescribir:** D-06, D-01, D-17, D-04, D-05, D-02, D-29, D-38, D-19 y D-16.

## 4. Reparto para no pisarse

Cada archivo tiene un solo dueño durante la ronda. Quien necesite un cambio en un archivo ajeno se lo pide al dueño.

| Dueño | Archivos `.tex` y compartidos | Código y figuras |
|---|---|---|
| Juan Pablo | `main.tex`, `refs.bib`, `custom-symbols.tex`, `docs/sommario.tex`, `chapters/introduction.tex`, `chapters/discusion.tex`, `chapters/conclusiones.tex` | `modelo/fay_herriot`, `modelo/sensibilidad_varianza`, `modelo/shared/config.py`, módulo común de estilo |
| Samuel | `chapters/marco-teorico.tex`, `chapters/antecedentes.tex`, `chapters/resultados.tex` | `modelo/fay_herriot_espacial`, `analisis/eda_seleccion_covariables`, `analisis/analisis_descriptivo`, `img/_script/figuras_resultados.py` |
| Felipe | `chapters/planteamiento-problema.tex`, `chapters/formulacion-problema.tex`, objetivos, `chapters/datos.tex`, `chapters/metodologia.tex`, `chapters/appendice.tex`, glosario de siglas y tabla de nombres de variables | `analisis/sensibilidad_ventana_temporal`, `img/_script/diagrama_metodologia.py` |

El reparto del código sigue el de la revisión del repositorio (Samuel, selección y espacial; Juan Pablo, modelo y documentación). Confirmen `analisis_descriptivo`, que puede pasar a Felipe si conviene equilibrar. Carga aproximada, a 2, 5 y 10 horas por ajuste S, M y L: Juan Pablo 35 h, Samuel 47 h y Felipe 50 h.

Cuando un ajuste toca archivos de dos dueños (D-05, D-19, D-18, D-06), el responsable de la tabla coordina y cada dueño edita su archivo.

## 5. Asignación propuesta

En el Excel los responsables quedan como «Sin asignar», para que el equipo decida.

| Ajuste | Título | Nivel | Responsable | Archivo principal | Esfuerzo |
|---|---|---|---|---|---|
| D-01 | El documento supera las 100 páginas sin apéndice | Alto | Felipe | main.tex | L |
| D-02 | Afirma erróneamente que los municipios no limitan con dominios | Alto | Samuel | chapters/marco-teorico.tex | S |
| D-03 | La tabla final sigue marcada como resultado preliminar | Alto | Juan Pablo | code/modelo/shared/config.py | S |
| D-04 | La redacción descriptiva y de selección contradice sus tablas | Alto | Samuel | chapters/resultados.tex | S |
| D-05 | Presenta 17 % como mejora de RMSE, pero es ECM | Alto | Samuel | chapters/resultados.tex | S |
| D-06 | Cumplimiento de objetivos expuesto ante criterio excluyente | Alto | Juan Pablo | chapters/conclusiones.tex | S |
| D-07 | Etapa 16 y parte de la comparación fuera del pipeline | Alto | Samuel | chapters/appendice.tex | M |
| D-08 | Tablas con siglas sin explicar en caption o nota | Medio | Felipe | chapters/metodologia.tex | M |
| D-09 | Sin criterio de decimales y con separadores mezclados | Medio | Felipe | chapters/appendice.tex | M |
| D-10 | Figuras con nombres de código y notación distinta al texto | Medio | Samuel | code/analisis/analisis_descriptivo.py | M |
| D-11 | Las figuras no comparten paleta ni estilo | Medio | Juan Pablo | code/modelo/fay_herriot.py | M |
| D-12 | Figuras con baja resolución o texto ilegible al 100 % | Medio | Juan Pablo | code/analisis/analisis_descriptivo.py | M |
| D-13 | Siglas sin definir, redefinidas o de idiomas mezclados | Medio | Felipe | chapters/marco-teorico.tex | M |
| D-14 | Una misma variable o modelo se nombra de varias formas | Medio | Felipe | chapters/datos.tex | S |
| D-15 | Objetivos específicos sin implementación explícita y con orden discutible | Medio | Felipe | chapters/objetivos-especificos.tex | S |
| D-16 | La notación del Marco reutiliza letras con significados distintos | Medio | Samuel | chapters/marco-teorico.tex | M |
| D-17 | Datos incluye agregación y definición de objetivos propias de Metodología | Medio | Felipe | chapters/datos.tex | S |
| D-18 | Sin sensibilidad a los parámetros que deciden el modelo | Medio | Samuel | chapters/metodologia.tex | M |
| D-19 | La Metodología mezcla presente y pasado | Medio | Felipe | chapters/metodologia.tex | M |
| D-20 | Faltan gráficos de supuestos: Q-Q y residuos frente a ajustados | Medio | Juan Pablo | code/modelo/fay_herriot.py | S |
| D-21 | El respaldo de las covariables queda fuera de la bibliografía | Medio | Juan Pablo | chapters/appendice.tex | M |
| D-22 | Citas cuya página no sustenta la afirmación o sin página | Medio | Samuel | chapters/discusion.tex | M |
| D-23 | La bibliografía imprime «Spanish» y acentos rotos | Medio | Juan Pablo | refs.bib | S |
| D-24 | Entradas bibliográficas con criterio de escritura desigual | Medio | Juan Pablo | refs.bib | S |
| D-25 | main.tex conserva restos y el título tiene mayúsculas de más | Bajo | Juan Pablo | main.tex | S |
| D-26 | Se salta de sección o subsección a párrafo | Bajo | Samuel | chapters/marco-teorico.tex | S |
| D-27 | Faltan listas de figuras, tablas y anexos oficiales | Bajo | Juan Pablo | main.tex | S |
| D-28 | Tres descripciones distintas de lo que publica la GEIH | Bajo | Felipe | chapters/planteamiento-problema.tex | S |
| D-29 | El planteamiento anticipa la solución y omite consecuencias futuras | Bajo | Felipe | chapters/planteamiento-problema.tex | S |
| D-30 | No todos los antecedentes dicen su aporte y su diferencia | Bajo | Samuel | chapters/antecedentes.tex | S |
| D-31 | Quedan dos espaciados manuales | Bajo | Felipe | chapters/datos.tex | S |
| D-32 | Dos conteos de indicadores de TerriData sin explicar | Bajo | Felipe | chapters/datos.tex | S |
| D-33 | Las métricas se definen pero su elección no se justifica | Bajo | Juan Pablo | chapters/metodologia.tex | S |
| D-34 | La comparación «aparte» con el mejor espacial no queda diferenciada | Bajo | Samuel | chapters/metodologia.tex | S |
| D-35 | Resultados repite procedimientos y criterios de la Metodología | Bajo | Samuel | chapters/resultados.tex | S |
| D-36 | El notebook del clásico describe la elección de otra forma | Bajo | Juan Pablo | code/modelo/fay_herriot.py | S |
| D-37 | Un valor de LRT redondeado distinto entre tablas | Bajo | Samuel | chapters/resultados.tex | S |
| D-38 | El apéndice cita sus flotantes con frases de relleno | Bajo | Felipe | chapters/appendice.tex | S |
| D-39 | La reproducción no identifica la versión del código | Bajo | Juan Pablo | chapters/appendice.tex | S |
| D-40 | Dos figuras tienen título interno | Bajo | Samuel | code/analisis/analisis_descriptivo.py | S |
| D-41 | Etiquetas definidas que nada cita | Opcional | Felipe | chapters/marco-teorico.tex | S |
| D-42 | El diagrama abrevia los nombres de las etapas | Opcional | Felipe | img/_script/diagrama_metodologia.py | S |
| D-43 | Los mapas podrían usar los polígonos municipales disponibles | Opcional | Samuel | img/_script/figuras_resultados.py | S |
| D-44 | El listado de tasas altas omite a Guacarí | Opcional | Samuel | chapters/resultados.tex | S |

## 6. Lista de verificación antes de entregar

- [ ] Compila sin advertencias de referencias ni de citas.
- [ ] ≤ 100 páginas de la portada a la bibliografía, contando las blancas.
- [ ] Resumen ≤ 500 palabras, en un párrafo (hoy 400).
- [ ] Introducción ≤ 2 páginas (hoy 2).
- [ ] Cero `---`, cero `enumerate`, cero `[H]` injustificados, cero `\textbf` en el texto (hoy se cumple; verificar después de editar).
- [ ] Todas las tablas, figuras y ecuaciones citadas (hoy se cumple; verificar después de mover contenido).
- [ ] La bibliografía no imprime «Spanish» y no queda «p'aginas».
- [ ] Ninguna figura con alias en mayúscula sostenida ni con título interno.
- [ ] `fay_herriot_estimaciones_finales` sin `PRELIMINAR`, y la frase de la etapa 15 actualizada.
- [ ] Cifras revisadas contra la última corrida, con el commit etiquetado y citado.
- [ ] Reunión con la directora: cumplimiento de objetivos, listas oficiales, `openany` y comparación aparte.
