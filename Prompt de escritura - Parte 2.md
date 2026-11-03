# Prompt de escritura, parte 2 de 2: Resultados, Discusión, Conclusiones, capítulos iniciales y cierre

Este prompt es la segunda de dos partes. La parte 1 ya dejó escritos y confirmados Marco de referencia
(`marco-teorico.tex`, `antecedentes.tex`), Datos (`datos.tex`) y Metodología (`metodologia.tex`), junto con
la carpeta `01_2026_TG_MCD_Grupo7_SAE_Desempleo/_trabajo/`. Aquí se escriben Resultados, Discusión, Conclusiones, Definición del problema,
Introducción, Apéndices y Resumen, se verifica todo el documento y se hace el reporte final.

Antes de cualquier otra cosa, lee `01_2026_TG_MCD_Grupo7_SAE_Desempleo/_trabajo/avance.md`, `inventario_cifras.md` y `auditoria_citas.md`. Si
`avance.md` no dice que Metodología quedó confirmada, detente y avísanos: la parte 2 no arranca sin eso.

# Contexto

Somos un equipo de tres (Samuel, Juan Pablo y Felipe) que presenta el trabajo de grado de la Maestría en
Ciencia de Datos (Pontificia Universidad Javeriana Cali): «Estimación municipal sobre la tasa de desempleo en
el Cauca y Valle del Cauca: estimación de área pequeña usando modelos mixtos y componentes espaciales».

Se requiere reescribir el documento LaTeX, desde la Introducción hasta las Conclusiones, para que refleje
**lo que el código hizo y los números que obtuvo**, atienda los comentarios de la revisión anterior y cumpla
los criterios de evaluación de la maestría.

**Idea central del trabajo:** el aporte es una **metodología** reproducible. No se está vendiendo un
resultado: se muestran los números tal como salieron. Si las covariables disponibles explican poco, o el
componente espacial no aporta, se dice así, con su evidencia. Un trabajo futuro con mejores covariables
puede reutilizar la misma metodología.

## Archivos de entrada

| Qué | Ruta (relativa a la raíz del repositorio) |
|---|---|
| Documento a modificar | `01_2026_TG_MCD_Grupo7_SAE_Desempleo/` (`main.tex`, `chapters/`, `docs/`, `refs.bib`, `img/`; todas las imágenes viven en `img/`) |
| Documento guía (otra tesis de la maestría, para estructura y nivel de detalle) | `Guia - Documento/` (`chapters/metodologia.tex`, `resultados.tex`, `conclusiones.tex`, `discusion.tex`) |
| Plantilla oficial de la maestría | `01_2026_TG_MCD_Grupo7_SAE_Desempleo/documentos_guia/Estructura Documento Proyecto - Maestría en Ciencia de Datos - Vers. 2025.docx` |
| Comentarios de la revisión (G7-B1 a G7-B22 y secciones 1 a 11) | `Comentarios Grupo 7.pdf` |
| Comentarios de la directora | `01_2026_TG_MCD_Grupo7_SAE_Desempleo/comentarios-Grupo7-22julio.docx` y los bloques `%-XXXX…` dentro de cada `.tex` |
| Estado de cada ajuste en el código | `Ajustes_Comentarios_Grupo7.xlsx` |
| Criterios de evaluación | `criterios de evaluacion/aspectos-evaluacion-entrega1.xlsx` (hojas Formato, Generales, Datos y Pre-procesamiento, Modelación) y `aspectos-evaluacion-entrega2.pdf` (acta del jurado) |
| Ejecuciones de los notebooks (salidas impresas, tablas y figuras) | `notebooks_execution/*.html` |
| Descripción del pipeline y de cada decisión | `CLAUDE.md`, `README.md`, `docs/resultados_cierre_2018.md`, `docs/fay_herriot_espacial.md` |
| Código | `code/` (ingesta, preprocesamiento, análisis, modelo) |
| Prompt de una versión anterior (referencia de formato) | `Especificaciones documento.md` |

Fuentes de verdad para las cifras, en este orden: (1) tablas `tesis.*` en Databricks (consulta SQL de solo
lectura con el MCP de Databricks), (2) salidas de `notebooks_execution/` (corrida del 2026-10-31), (3)
`docs/resultados_cierre_2018.md`. Si dos fuentes no coinciden, usa la tabla y anota la diferencia en el
reporte final. **Ninguna cifra del documento puede escribirse sin haberla leído en una de estas fuentes o en un
cálculo propio documentado** (ver abajo).

**Cálculos propios.** Si una cifra, tabla o comparación que el documento necesita no está en esas fuentes
(por ejemplo, parte de la comparación entre el modelo espacial y el Fay-Herriot clásico, ver «Comparación
del modelo espacial frente al Fay-Herriot clásico»), se calcula a partir de las tablas `tesis.*` ya
persistidas o de las salidas extraídas de los notebooks. Condiciones: el script vive en
`01_2026_TG_MCD_Grupo7_SAE_Desempleo/_trabajo/calculos/`, la consulta a Databricks es de solo lectura, no se
modifican el código, los jobs ni las tablas, y cada cálculo queda en `inventario_cifras.md` con su script,
las tablas de entrada y la fórmula. El método de cada cálculo propio se define en el Marco teórico y se
describe en Metodología (regla 6); sin eso no entra al documento.

### Cómo leer los notebooks exportados

Cada HTML de Databricks guarda el notebook en `__DATABRICKS_NOTEBOOK_MODEL` (base64 de un JSON
URL-codificado). Extrae todo a Markdown (código, salidas `stdout`, tablas) y las figuras (`image/png` en
base64) a archivos, en `01_2026_TG_MCD_Grupo7_SAE_Desempleo/_trabajo/notebooks/` (no en el scratchpad,
que se pierde al cerrar la sesión, ni
dentro de `chapters/`):

```python
import re, base64, urllib.parse, json
h = open(ruta_html, encoding="utf-8").read()
m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", h)
nb = json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode()))
for cmd in nb["commands"]:  # cmd["command"] = código; cmd["results"] = salidas
    ...
```

Corre Python con `-I` y usa el venv del proyecto (ver memoria `flujo-revision-ramas`). Las figuras del modelo
también están en el volumen `/Volumes/tesis/modelo/figuras` y las del análisis en
`/Volumes/tesis/preprocesamiento/figuras_eda`.

## Lo que no se puede modificar

- **Objetivo general y objetivos específicos** (`chapters/objetivo-general.tex`, `objetivos-especificos.tex`):
  no se toca ni una palabra. Todo el documento gira en torno a responderlos.
- Las decisiones metodológicas ya cerradas en el código (las de `CLAUDE.md`): dominio = ciudad o ciudad A.M.,
  ventana anual 2018, ψ_d por bootstrap de viviendas, benchmarking en dos niveles, catálogo de 18
  covariables, etc. El documento las **describe y las sustenta**; no las rediscute ni propone otras.
- El código, los jobs y las tablas: esta tarea solo escribe el documento. No ejecutes jobs ni notebooks.
  Los cálculos propios (ver «Fuentes de verdad») corren localmente sobre datos ya extraídos y no escriben
  en Databricks.
- Los capítulos de la parte 1 (`marco-teorico.tex`, `antecedentes.tex`, `datos.tex`, `metodologia.tex`)
  ya están confirmados. Solo puedes cambiar en ellos etiquetas y `\ref` para cerrar referencias cruzadas.
  Si encuentras algo de fondo que corregir (por ejemplo, Metodología promete una tabla que no existe en
  las fuentes), no lo cambies: pregúntanos y anótalo en `avance.md`.

Objetivos (copiados del documento, para referencia):

- **OG.** Desarrollar una metodología para estimar la tasa de desempleo en los municipios de los
  departamentos del Cauca y Valle del Cauca mediante métodos de estimación de áreas pequeñas basados en
  modelos mixtos con componentes espaciales, integrando diversas fuentes de información y covariables
  definidas a partir de la evidencia disponible, con el fin de superar las limitaciones de cobertura y costo
  de los métodos tradicionales de medición.
- **OE1.** Evaluar el desempeño de distintos modelos de estimación de áreas pequeñas basados en modelos
  mixtos con componentes espaciales para la estimación de la tasa de desempleo en los municipios…
- **OE2.** Determinar, a partir de los resultados de los modelos de estimación de áreas pequeñas, las
  variables explicativas con mayor incidencia en la tasa de desempleo en los municipios…
- **OE3.** Analizar la distribución y los patrones espaciales del desempleo en los municipios… a partir de
  las estimaciones obtenidas mediante los modelos de estimación de área pequeña.

Cómo responde el código a cada objetivo (orientación; verifica cada cifra en las fuentes):

| Objetivo | Qué lo responde en el código | Resultado de la corrida vigente (a verificar) |
|---|---|---|
| OE1 | Fay-Herriot clásico como benchmark no espacial (EC0 a EC3) frente al Fay-Herriot espacial SAR (SEBLUP) con varias matrices W (kNN 3 y 5, distancia inversa potencia 1 y 2; estructuras «muestra» y «completa»): comparación controlada (misma respuesta, mismos ψ_d, mismos dominios, mismas covariables), LRT de ρ = 0, ΔAIC, Moran de residuos, validación dejar-un-dominio-fuera, MSE | Benchmark EC3 (`TASA_HOMICIDIOS`). Sin evidencia de dependencia espacial (LRT p ≥ 0.22; Moran no significativo en ambos). El modelo recomendado sigue siendo el clásico |
| OE2 | Selección de covariables (`eda_seleccion_covariables`), coeficientes del clásico y del espacial (`fhe_coeficientes_comparacion`), estabilidad dejar-un-dominio-fuera y bootstrap, validación del procedimiento completo | Una sola covariable seleccionada; inestable entre iteraciones (6 conjuntos distintos en 23); el procedimiento completo predice peor que el modelo nulo (habilidad −0.54). Lenguaje de **asociación**, no causal |
| OE3 | Estimaciones municipales (83), mapas, Moran global, ρ̂, efecto espacial en los nodos objetivo, extrapolación (B20) y calidad reportada (B21) | Efecto espacial pequeño; 21 de 83 objetivos extrapolan; Cali y Yumbo «no confiables» tras el benchmarking de nivel 2 |

## Carpeta de trabajo compartida entre las dos partes

Todo lo que una sesión necesita para retomar queda en `01_2026_TG_MCD_Grupo7_SAE_Desempleo/_trabajo/`, nunca en el scratchpad:

| Archivo | Qué guarda | Lo crea | Lo usa |
|---|---|---|---|
| `avance.md` | Capítulos terminados y confirmados, decisiones tomadas, dudas abiertas, pendientes para la otra parte y el último paso hecho | Parte 1 | Las dos (se actualiza al cerrar cada capítulo) |
| `inventario_cifras.md` | Matriz «afirmación o cifra → fuente (tabla `tesis.*`, o notebook y celda) → capítulo donde se usa» | Parte 1 (parámetros y cifras de Datos) | Parte 2 la completa con las cifras de Resultados |
| `auditoria_citas.md` | Cada `\cite`: clave, qué se le atribuye, página, frase de apoyo y decisión (se mantiene, se corrige, se elimina) | Parte 1 | Parte 2 (las citas nuevas se agregan aquí) |
| `notebooks/` | Notebooks extraídos a Markdown y sus figuras | Parte 2 | Parte 2 |

Si la sesión se corta a mitad de un capítulo, la siguiente empieza leyendo `avance.md` y sigue desde el
último paso anotado, sin repetir lo ya hecho. Por eso `avance.md` se actualiza al terminar cada capítulo y
cada vez que se tome una decisión que cambie el contenido.

# Reglas de redacción y de contenido

1. **Neutralidad.** Describe los datos como son. Nada de «excelente», «robusto», «demuestra», «supera
   ampliamente». Si un resultado no es significativo, no mejora o es inestable, se dice con la cifra. Las
   limitaciones se reportan en Resultados (el hecho) y en Discusión (su alcance). El aporte se presenta
   como la metodología, no como las cifras municipales.
2. **Asociación, no causalidad** (G7-B14, G7-B17). «Mayor incidencia» del OE2 se responde como asociación
   estadística condicional a la selección; los p son descriptivos porque los mismos 23 dominios filtran,
   seleccionan y estiman.
3. **Benchmark y estado de las cifras** (G7-B15, sec. 2 y 10 del PDF). EC0 a EC3 son «especificaciones
   candidatas del modelo base Fay-Herriot clásico», no los modelos del OE1. La comparación del OE1 es
   benchmark frente a especificaciones espaciales.
4. **Estimación, no predicción** (comentario de la directora): en la narrativa se habla de «estimación» y
   «estimador». Solo se conservan estos nombres técnicos, definidos una vez en el Marco teórico y escritos
   siempre igual en todo el documento:
   - «mejor predictor lineal insesgado empírico (EBLUP)» y su versión espacial, «SEBLUP»;
   - «validación predictiva dejar-un-dominio-fuera», como nombre del procedimiento de la etapa 12;
   - «predictor sintético» y «predictor espacial», solo cuando se nombra la fórmula que se aplica a los
     municipios sin muestra (etapa 14).
   Fuera de esos casos se escribe «estimación sintética», «estimación espacial», «error de estimación»,
   «estimaciones municipales». Si aparece otro término técnico con «predicción», no lo inventes ni lo
   cambies por tu cuenta: anótalo en el reporte final para decidirlo entre los tres.
5. **Nombres de variables en lenguaje natural** («tasa de homicidios», no `TASA_HOMICIDIOS`; «factor de
   expansión», no `FEX_C18`). Una tabla en el apéndice relaciona nombre descriptivo, código TerriData o
   columna y descripción. Lo mismo para nombres de tablas y notebooks: en el cuerpo se describen; el linaje
   técnico va al apéndice.
6. **Cada método usado en Metodología está definido en el Marco teórico** (con su ecuación, el significado
   de cada término en el contexto del desempleo en los dominios GEIH y los municipios de Cauca y Valle, sus
   supuestos y la etapa de la metodología donde se usa). Y al revés: el Marco teórico no incluye métodos que
   el código no usa (por ejemplo, no metas BIC si no se calcula).
7. **Metodología y Resultados en espejo**: mismas secciones, mismo orden, mismos títulos (ver más abajo).
8. **Toda decisión metodológica lleva cita** a la literatura (con página cuando la fuente es un libro o un
   documento largo) y referencia cruzada a la sección del marco teórico (`Sección~\ref{…}`).
9. **Tiempo verbal**: impersonal en pasado («se estimó», «se seleccionó») en todo el documento; sin primera
   persona plural y sin tiempo futuro en Introducción ni Resumen.
10. **Que suene a nosotros.** El documento lo firman tres estudiantes de maestría y tiene que sonar a
    gente que hizo el trabajo, no a un texto genérico.
    - Nivel: lo que un estudiante promedio de la maestría puede explicar y defender en la sustentación. No
      agregues métodos, pruebas ni discusiones teóricas que no hicimos o que no sabríamos sustentar.
    - Concreto: cifras, nombres de dominios, tablas. Mejor «21 de los 83 municipios objetivo quedan como
      extrapolación» que «una proporción considerable de municipios presenta extrapolación».
    - Frases de largo variado. No empieces párrafos seguidos con la misma estructura ni cierres cada
      párrafo con una frase que resume lo que ya se dijo.
    - Evita las muletillas que delatan un texto armado por IA: «cabe destacar», «es importante mencionar»,
      «es importante señalar», «en este sentido», «en el contexto de», «juega un papel fundamental»,
      «juega un papel clave», «integral», «exhaustivo», «sólido», «aporta valor», «permite comprender de
      manera profunda», «no solo… sino también», las listas de tres adjetivos y los cierres tipo «en
      conclusión, este análisis demuestra la importancia de…».
    - Mantén el tono del documento actual donde ya está bien escrito; no reescribas por reescribir.
11. **Fácil de leer: más tablas y gráficas, menos texto.** Donde un procedimiento, una comparación o una
    lista de parámetros se pueda mostrar con una tabla, un diagrama de flujo o una figura, se muestra así, y
    el texto solo la introduce, la interpreta o aclara lo que ella no dice. Pesa sobre todo en Metodología.
    - Un párrafo de más de unas 12 líneas sin tabla ni figura se revisa: casi siempre se parte, se resume en
      una tabla o se manda el detalle al apéndice.
    - Las listas de parámetros, umbrales, variables y reglas de decisión van en tabla, no en prosa.
    - Los diagramas de flujo se generan como imagen con un script (se pueden revisar sin LaTeX) y se guardan
      en `img/`; si se hacen en TikZ (ya cargado en `main.tex`), se avisa que no se pudieron compilar aquí.
    - Lo opcional o complementario (imágenes, diagramas, tablas) va al apéndice, que no cuenta en las 100
      páginas, y el cuerpo lo cita con `Apéndice~\ref{app:…}`.

# Referencias bibliográficas

Las referencias sostienen cada paso; esto es tan importante como el texto.

La auditoría de las citas ya está hecha en la parte 1 (`auditoria_citas.md`): úsala y no la repitas. Si un
capítulo de esta parte necesita una cita nueva, búscala con las skills de abajo y agrégala a ese archivo con
su página y frase. Lo que sigue es la referencia de cómo se hizo.

1. **Auditoría de lo citado.** Para cada `\cite` del documento actual: confirma que la fuente dice lo que se
   le atribuye (consulta el RAG que corresponda y anota página). Corrige o elimina la cita si no lo dice.
   Revisa en especial la cita que la directora marcó en `antecedentes.tex` («revisar la cita [9]»). Por el
   orden de aparición, la novena clave es `BernalGonzalez2017`, que hoy sostiene el origen del modelo
   Fay-Herriot (1979) en el primer párrafo de antecedentes; para ese hecho la fuente es `FayHerriot1979`.
   Confírmalo contra el PDF compilado antes de cambiarla y revisa además las otras citas de esa clave.
2. **Fuentes para buscar sustento** (invoca cada skill con una consulta concreta y guarda autor, página y
   frase de apoyo):
   - `/consultar-libro-sae`: Morales et al. 2021 (`morales2021smallarea`): FH, REML, GLS, EBLUP, MSE de
     Prasad-Rao (p. 440), AIC y selección (pp. 453-454), predicción sintética (p. 441), varianza conocida
     (p. 427), FH espacial SAR (§18.2, pp. 490-494), benchmarking, razón de totales (p. 21).
   - `/consultar-articulos-sae`: Molina 2019 (CEPAL), DANE (nota SAE), Chile pobreza 2016, Casen 2024, ENUSC
     2018 (GVF, benchmarking), Téllez 2020 (deff), tesis y aplicaciones colombianas (Mendoza-Zea 2019,
     Vargas-Lemus 2018, Bernal 2017, Montoya 2019, Guerrero 2019, Ortiz et al. 2024, etc.).
   - `/consultar-articulos-sae-espacial`: Benedetti 2024 (MML, pp. 141-149, 159), Pratesi-Salvati 2008,
     Petrucci-Salvati 2006, Pereira 2021, Shiferaw 2025, Sikov 2023, Haro 2022, Romero-Lemus 2018, Durán 2024.
   - `/consultar-geih`: metodología GEIH 2016 (v9): definiciones de PET, PEA, OC, DS, dominios y áreas
     metropolitanas (PDF 9), diseño muestral y dominio como estrato (PDF 11), linealización de Taylor
     (PDF 15), factores de expansión.
   - `/consultar-desempleo-colombia`: determinantes y diferencias espaciales del desempleo (Díaz 2016,
     Forero-García-Guataquí, Henao-Rojas, Chávez 2010, Arroyo et al.) para el planteamiento del problema,
     los antecedentes y el signo esperado de las covariables.
   - `consultar-libro-islr` **no se usa** en este trabajo: no la invoques ni cites a James et al. (2021).
     Las decisiones sobre VIF, validación dejar-uno-fuera, bootstrap y selección de variables se sustentan
     con Morales et al., Montgomery, Peck y Vining, Benjamini y Hochberg y las demás fuentes de arriba; si
     ninguna las respalda, son convención propia (punto 4).
   - Las referencias ya usadas en el código: docstrings de `code/` y `analisis/shared/catalogo_literatura.py`
     (campo `referencia` de cada covariable). Montgomery, Peck y Vining (sec. 3.8) para la extrapolación
     oculta; Benjamini y Hochberg (1995) para FDR; Fay y Herriot (1979); Prasad y Rao (1990).
   - Fuentes oficiales: glosario GEIH del DANE, ficha metodológica GEIH, anexo «Mercado laboral según
     proyecciones CNPV 2018», TerriData (DNP), DIVIPOLA.
3. **Formato** (criterio «Referencias bibliográficas»): estilo IEEE de biblatex (ya configurado en la
   clase); solo entradas citadas en el texto (elimina las huérfanas de `refs.bib`); DOI cuando exista;
   nombre completo de la revista; mismo criterio de mayúsculas; enlaces verificables para documentos
   institucionales. Citas múltiples en un solo comando (`\cite{A, B, C}`). Páginas con el argumento
   opcional y siempre del mismo modo: `\cite[p.~440]{morales2021smallarea}`, `\cite[pp.~453--454]{…}`.
4. Si para una decisión no aparece sustento en ninguna fuente, **no inventes la cita**: escribe que es una
   convención propia del trabajo (como ya lo dice el código: p. ej. el umbral 0.80 de soporte, la cota
   n // 10) y anótalo en el reporte final.

# Estructura y especificaciones por sección

Cada sección lleva una etiqueta: **[Modificar]** existe y se reescribe; **[Añadir]** no existe; **[Revisar]**
se conserva salvo los ajustes indicados. Las subsecciones deben quedar anidadas en su sección (sin saltar de
`\section` a `\subsubsection`).

## Resultados [Modificar] — `resultados.tex`

Guía de estilo: `Guia - Documento/chapters/resultados.tex`.

- Mismas secciones, mismo orden, mismos títulos que Metodología. Cada sección muestra la evidencia (tabla,
  figura, prueba, métrica) de lo prometido en la etapa homóloga y la interpreta en un párrafo; sin
  justificar de nuevo el método ni repetir teoría.
- Tablas mínimas pedidas por la revisión (sec. 10 del PDF): equivalencia dominio GEIH y geografía real;
  tamaño muestral, PEA y desocupados por dominio; TD oficial frente a TD reconstruida; sensibilidad
  mensual, trimestral y anual; auditoría de factores de expansión y uniones; covariables con geografía,
  período, unidad y denominador; AIC y AICc de las especificaciones; estabilidad de coeficientes; validación
  dejar-un-dominio-fuera; soporte y extrapolación; mapa de residuos; Moran clásico frente a espacial.
- Diagnósticos del modelo (normalidad, media de residuos, independencia o Moran) en una tabla con el
  formato de la nota metodológica SAE del DANE (`DANE_SAE_2025` en `refs.bib`), redactados con prudencia:
  «los diagnósticos no muestran evidencia fuerte contra la aproximación normal en el benchmark, dentro de
  la limitada potencia disponible con 23 áreas».
- Las tablas municipales completas (83 filas) van al apéndice; en el cuerpo, un resumen y los mapas.
- Formato (regla 11): cada sección abre con su tabla o figura y la interpreta en un párrafo corto. Las
  tablas y figuras complementarias u opcionales van al apéndice y se citan con `Apéndice~\ref{app:…}`.
- Etiqueta `\label{sec:resultados}`.

## Comparación del modelo espacial frente al Fay-Herriot clásico (OE1)

Es el centro del OE1 y debe quedar completa en Resultados, la produzca el código o no. Es una comparación
controlada: misma respuesta, mismos ψ_d, mismos 23 dominios y mismas covariables congeladas. Contenido mínimo:

| Elemento | Qué se compara | Dónde está hoy (verifícalo) |
|---|---|---|
| Ajuste | σ̂²_u, ρ̂, AIC, ΔAIC y LRT de ρ = 0 del benchmark y de cada especificación espacial (4 matrices W × estructuras «muestra» y «completa») | `fhe_comparacion_modelos`, `fhe_cuadro_comparativo` |
| Residuos | I de Moran de los residuos del clásico y del SEBLUP con la misma estandarización; mapa de residuos | `fhe_moran` |
| Desempeño fuera de muestra | validación dejar-un-dominio-fuera con las mismas métricas en ambos (RMSE, MAE, sesgo, RMSE corregido por ruido, Z_psi, Z_pred, cobertura, habilidad frente al modelo nulo) | `fhe_validacion_cruzada_metricas` |
| Incertidumbre | MSE y CV del EBLUP y del SEBLUP en los 23 dominios y en los 83 municipios; γ_d de cada uno | `fay_herriot_resultados`, `fhe_prediccion_objetivo` |
| Estimaciones | diferencia entre ambas estimaciones (puntos porcentuales) en dominios y municipios: media, máxima, correlación de Pearson y de Spearman, y municipios que cambian de clase de confiabilidad | por verificar |
| Coeficientes (OE2) | β̂ y error estándar del clásico frente al espacial | `fhe_coeficientes_comparacion` |

Tu trabajo en esta parte:

- Antes de redactar Resultados, revisa en `avance.md` la lista que dejó la parte 1 (qué existe y qué falta),
  confírmala contra las tablas `tesis.modelo.fhe_*` y los notebooks, y ejecuta los cálculos propios pendientes
  (ver «Fuentes de verdad»), con los datos de las tablas y de los notebooks. Si falta algo que la parte 1 no
  anotó, calcúlalo también. Todo queda en `inventario_cifras.md`.
- Si un cálculo cambia o contradice lo que Metodología (ya confirmada) define para la etapa 13, no lo corrijas
  por tu cuenta: pregúntanos y anótalo en `avance.md`.
- En el cuerpo (sección de la etapa 13 de Resultados): una tabla comparativa principal (benchmark, la
  especificación espacial de referencia y el resumen de las demás), una figura de las estimaciones clásica
  frente a espacial (dispersión y diferencias), el mapa de residuos y el Moran de ambos, con un párrafo de
  lectura. El detalle de las ocho especificaciones y las diferencias por municipio van al apéndice.
- Sin pruebas inferenciales adicionales al LRT de ρ = 0: con 23 dominios las diferencias se reportan, no se
  prueban. Si las dos variantes dan prácticamente lo mismo, se dice con la cifra.

## Etapas de Metodología (referencia para el espejo)

Los títulos que mandan son los que quedaron en `metodologia.tex` y en `avance.md`; esta lista es solo la
propuesta original, para saber qué evidencia corresponde a cada etapa.

1. **Obtención de los datos**: GEIH, TerriData, DIVIPOLA, cifras publicadas por el DANE; arquitectura de
   medallón (bronce, plata, oro) como procedimiento.
2. **Limpieza, estandarización y consolidación**: unión de módulos y marcos, lectura por nombre de columna
   (G7-B5), factor de expansión por marco (G7-B6), reconciliación PEA = OC + DS y PET = PEA + PEI, llaves sin
   pareja.
3. **Tratamiento de datos faltantes y valores atípicos**.
4. **Definición de los dominios de estimación y correspondencia geográfica** (G7-B1: ciudades y áreas
   metropolitanas, membresía, tabla de auditoría).
5. **Estimación directa de la tasa de desempleo**: ventana anual (G7-B2 y sensibilidad mes, trimestre y año),
   estimador de Hájek, validación contra las cifras del DANE (G7-B4), varianza por bootstrap de viviendas y
   control por Taylor (G7-B3), coeficiente de variación y su clasificación (G7-B7).
6. **Construcción y agregación de las covariables**: catálogo de literatura, reglas de agregación por
   denominador, municipios objetivo de Cauca y Valle.
7. **Pre-filtrado de covariables**: completitud y variabilidad.
8. **Análisis descriptivo**: univariado, bivariado y multivariado.
9. **Selección de covariables**: G7-B8 a G7-B13 (FH univariado con ψ_d, Benjamini-Hochberg, robustez como
   diagnóstico, soporte, redundancia con retroceso, signo como diagnóstico, forma funcional, cota de
   covariables, VIF).
10. **Ajuste y selección del modelo Fay-Herriot clásico (benchmark)**: especificaciones EC0 a EC3, REML, GLS,
    AIC por ML, AICc, regla de selección (G7-B15, G7-B16).
11. **Validación de supuestos y sensibilidad del benchmark**: normalidad (G7-B22), Cook, estabilidad de
    coeficientes dejar-un-dominio-fuera y bootstrap (G7-B17, G7-B18), sensibilidad a la varianza de
    muestreo (GVF y escenarios).
12. **Validación predictiva dejar-un-dominio-fuera** (G7-B19): covariables fijas y procedimiento completo.
13. **Modelo Fay-Herriot espacial y comparación con el benchmark**: W sobre las unidades reales (A.M. = un
    nodo, R-42), escenarios de W, MML, LRT, Moran de residuos clásico frente a espacial, comparación
    controlada y comparación aparte (sec. 7 y 8 del PDF), coeficientes clásico frente a espacial (OE2). El
    contenido mínimo de la comparación está en «Comparación del modelo espacial frente al Fay-Herriot
    clásico».
14. **Estimación en los municipios sin cobertura muestral**: predictor sintético (clásico) y predictor
    espacial (sec. 9 del PDF), subáreas de un A.M., extrapolación (G7-B20), calidad reportada (G7-B21).
15. **Benchmarking y consolidación de las estimaciones**: niveles 1 y 2, RMSE con benchmarking, tabla final.
16. **Distribución y patrones espaciales de las estimaciones** (OE3): mapas y lectura territorial.

## Discusión y trabajo futuro [Modificar] — `discusion.tex`

- Lectura crítica de los resultados: qué muestra la comparación clásico frente a espacial, qué tan estable
  es la selección, qué significa que el procedimiento completo prediga peor que el modelo nulo, alcance de
  las estimaciones municipales (extrapolación, CV condicional al modelo, tasa urbana de los dominios frente
  a covariables del municipio completo, varianza bootstrap como aproximación cuya dirección de sesgo no se
  conoce, G7-B3), comparación con los antecedentes.
- Trabajo futuro: mejores covariables (el punto central), otros años y el marco 2018 de la GEIH, registros
  sin código de área (nivel 3 del benchmarking), modelos a nivel de unidad, otras estructuras espaciales.
- Etiqueta `\label{sec:discusion}`.

## Conclusiones [Modificar] — `conclusiones.tex`

Igual que la guía: una sección por objetivo (general, OE1, OE2, OE3), cada una derivada de los resultados,
con su cifra de soporte y sin optimismo. Al menos tres conclusiones relevantes. Etiqueta
`\label{sec:conclusion}`.

## Definición del problema [Modificar] — `planteamiento-problema.tex`, `formulacion-problema.tex`

- Planteamiento: situación actual (cobertura de la GEIH, escasez de información censal y de registros
  actualizados a escala municipal), síntomas, causas y consecuencias de mantenerse; el problema visto desde
  la ciencia de datos (integrar fuentes, modelar, estimar con incertidumbre). Sin anticipar la solución.
  Apóyate en `/consultar-desempleo-colombia` y `/consultar-geih`.
- Formulación: una pregunta general y tres preguntas de sistematización, cada una en correspondencia uno a
  uno con OG, OE1, OE2 y OE3. La directora ya ajustó las preguntas (ver su comentario en el archivo): solo
  revisa la redacción y elimina el bloque de comentario.
- Etiqueta `\label{sec:problema}`.

## Objetivos [No tocar]

Solo verifica que exista `\label{sec:objetivos}`.

## Introducción [Modificar] — `chapters/introduction.tex`

Máximo dos páginas, sin tiempo futuro. Orden:

1. Las encuestas de hogares no cubren todo el territorio por costo y logística; la GEIH, principal fuente
   del DANE para el mercado laboral, solo publica tasas para 23 ciudades y áreas metropolitanas.
2. Problema: no se conoce la tasa de desempleo de los municipios medianos y pequeños, en particular los de
   Cauca y Valle del Cauca.
3. Estrategia: estimación de áreas pequeñas con el modelo Fay-Herriot, que combina un modelo de muestreo
   (estimación directa de la GEIH y su varianza) y un modelo de enlace (covariables de TerriData), y su
   extensión espacial. Se resume en un párrafo la metodología.
4. Principales resultados, en tono neutral (incluye que no se encontró evidencia de dependencia espacial y
   que la covariable seleccionada explica poco fuera de muestra).
5. Último párrafo: organización del documento con `Sección~\ref{sec:…}` a cada capítulo.

## Apéndices [Revisar] — `appendice.tex`

El apéndice no cuenta en el límite de 100 páginas y no tiene tope: aprovéchalo. Recibe lo que se saque del
cuerpo y todo el material opcional o complementario (imágenes, diagramas, tablas, pruebas de robustez),
siempre citado desde el texto con `Apéndice~\ref{app:…}`. Mínimo: tabla de nombres de variables
(descriptivo, código, descripción), linaje de tablas, estimaciones de los 83 municipios, detalle de
especificaciones y escenarios (incluidas las ocho especificaciones espaciales), catálogo de covariables con
referencia. Cada sección lleva su etiqueta `app:<tema>` y una frase de apertura que dice qué contiene y
desde qué sección se cita. Las secciones que agregó la parte 1 se conservan y se completan. Lo que
sustenta un objetivo se queda en el cuerpo.

## Resumen [Revisar, al final] — `docs/sommario.tex`

Si no coincide con el documento nuevo: un solo párrafo, máximo 500 palabras, tema, problema, objetivos,
resultados principales y aplicaciones, sin tiempo futuro.

# Notas de formato (criterios de la hoja «Formato» y comentarios de la directora)

- `main.tex` solo carga archivos con `\input`; ningún contenido académico ahí.
- Etiquetas de capítulo: `sec:problema`, `sec:objetivos`, `sec:marco-referencia`, `sec:datos`,
  `sec:metodologia`, `sec:resultados`, `sec:discusion`, `sec:conclusion`.
- Las etiquetas de sección de Metodología (`sec:met_obtencion`, `sec:met_limpieza`, `sec:met_faltantes`,
  `sec:met_eda`, `sec:met_prefiltrado`, `sec:met_seleccion`, `sec:met_modelo`, `sec:met_sintetico`, etc.)
  van a cambiar con las nuevas etapas. Usa un esquema único y en espejo (`sec:met_<etapa>` en Metodología y
  `sec:res_<etapa>` en Resultados), y actualiza todas las `\ref` que apuntaban a las etiquetas viejas en
  cualquier capítulo y en el apéndice. En el reporte final, lista etiqueta vieja → etiqueta nueva.
- Toda tabla, figura y ecuación con `\label{}` y citada en el texto con `Tabla~\ref{}`, `Figura~\ref{}`,
  `Ecuación~\ref{}`, en el párrafo donde se interpreta. Ninguna sin citar ni referencia rota.
- Flotantes con `[!htbp]`, no `[H]`.
- Nada de `---` ni incisos con rayas; usa comas, paréntesis o reformula. Sin negrita en el texto; si hay que
  resaltar, cursiva con un criterio único (p. ej. solo términos en otro idioma).
- Siglas definidas una sola vez y en un único idioma (en español; el término en inglés, si se da, siempre con
  el mismo formato: «estimación en áreas pequeñas (SAE, por sus siglas en inglés)» o el que se elija, pero
  igual en todos los casos).
- Títulos con mayúscula solo en la primera palabra (salvo nombres propios y siglas). Sin mayúscula
  sostenida fuera de siglas.
- Números: coma para miles (273,960) y punto para decimales, con el mismo número de decimales en cada tipo de
  magnitud (2 para tasas y puntos porcentuales, 3 para coeficientes y p, por ejemplo) en texto, tablas y
  figuras. `siunitx` ya está configurado así. La regla aplica también a las cifras escritas a mano en el
  texto, no solo a las que pasan por `siunitx`.
- Listas solo con `itemize` (no `enumerate`). Párrafos separados por una línea en blanco; sin `\\` ni `\par`.
- Tablas sin líneas verticales (`booktabs`), con notas que expliquen siglas, símbolos y unidades.
- Figuras e imágenes en `img/` (no en `fig/` ni en otra carpeta), sin título interno (la descripción va en el caption), legibles al 100 % de zoom, con
  la misma tipografía y una gama de máximo tres colores base en todo el documento. Si una figura de los
  notebooks no cumple (título interno, letra pequeña, paleta distinta), puedes regenerarla con un único
  script de estilo, con estas condiciones: el script vive en `01_2026_TG_MCD_Grupo7_SAE_Desempleo/img/_script/`
  (no en el repositorio del código), solo lee tablas `tesis.*` con SQL de solo lectura o datos ya extraídos
  de los notebooks, no recalcula ninguna cifra y cada figura indica en un comentario de su `.tex` de qué
  tabla salió. Si una figura necesita un cálculo que no está en las tablas, se hace como cálculo propio (ver
  «Fuentes de verdad») y queda en `inventario_cifras.md`; solo si no se puede calcular con lo disponible va a
  la lista de pendientes del reporte final.
- Carpeta de imágenes: `img/` es la única. Lo que hoy esté en `fig/` y se use se mueve a `img/` (y se
  actualiza su `\includegraphics`); `fig/` desaparece. Una imagen sin ninguna referencia en los `.tex` no se
  deja en la carpeta (la limpieza final se hace en la parte 2, con la lista de imágenes en desuso que deje la
  parte 1 en `avance.md`).
- Máximo 100 páginas desde la portada hasta las referencias. **El apéndice no cuenta para ese límite** y no
  tiene tope: úsalo. Todo lo opcional o complementario (imágenes, diagramas, tablas largas, detalle de
  escenarios, pruebas de robustez) va allí, y el cuerpo lo cita con `Apéndice~\ref{app:…}` y una frase que
  diga qué se encuentra. El cuerpo tiene que entenderse sin abrir el apéndice: la evidencia que responde a
  un objetivo se queda en el cuerpo.
- Elimina los bloques de comentario de la directora (`%-XXXX…`) una vez atendidos.

## Presupuesto de páginas

Las 100 páginas (de la portada a las referencias, sin apéndices) se reparten así. Es una guía, no una regla
fija: si un capítulo se pasa, se compensa en otro o se manda detalle al apéndice, y se avisa.

| Parte | Páginas |
|---|---|
| Portada, resumen, índices y listas | 8 |
| Introducción | 2 |
| Definición del problema | 3 |
| Objetivos | 1 |
| Marco de referencia (teórico 16 y antecedentes 4) | 20 |
| Datos | 6 |
| Metodología | 18 |
| Resultados | 26 |
| Discusión y trabajo futuro | 5 |
| Conclusiones | 3 |
| Referencias | 6 |
| Total | 98 |
| Apéndices | no cuentan |

Como no hay LaTeX en el equipo, al terminar cada capítulo estima sus páginas con esta cuenta: unas 400
palabras de texto corrido por página, media página por tabla o figura pequeña y una página por tabla o
figura grande. Reporta la estimación junto con el avance del capítulo. Nosotros lo compilamos en Overleaf
y te damos el número real, que manda sobre la estimación.

Como el apéndice no cuenta, no hace falta recortar contenido útil: se reubica. Criterio para decidir qué va
al apéndice: tablas largas (municipios, escenarios, linaje), figuras y tablas complementarias u opcionales,
diagnósticos de apoyo, y las ecuaciones de detalle del marco teórico que no se usan en Resultados. Lo que
se queda en el cuerpo: la evidencia de cada objetivo y las tablas pedidas en la sección 10 del PDF.

# Forma de trabajo de la parte 2

1. **Retomar.** Lee `avance.md`, `inventario_cifras.md` y `auditoria_citas.md`. Si existe un respaldo de
   hoy en `_respaldo_<fecha>/` no hagas otro; si no, copia `chapters/`, `refs.bib` y `main.tex` antes de
   editar. No hagas commits salvo que te lo pidamos.
2. **Inventario de resultados.** Extrae los notebooks a `01_2026_TG_MCD_Grupo7_SAE_Desempleo/_trabajo/notebooks/` y completa
   `inventario_cifras.md` con cada cifra que vaya a Resultados, Discusión, Conclusiones, Introducción y
   Resumen. Si los notebooks ya están extraídos (otra sesión de esta parte se cortó), no los extraigas de
   nuevo. Revisa también la lista de la comparación del modelo espacial frente al clásico que dejó la
   parte 1 y ejecuta los cálculos propios pendientes antes de redactar Resultados.
3. **Redacción** en este orden: Resultados → Discusión → Conclusiones → Planteamiento y formulación →
   Introducción → Apéndices → Resumen. Termina una sección antes de pasar a la siguiente y muéstranos el
   avance por capítulo. Al cerrar cada capítulo, entrega su estimación de páginas (ver «Presupuesto de
   páginas»), actualiza `avance.md` y espera nuestra confirmación antes de seguir con el siguiente.
4. **Verificación de todo el documento.** No hay LaTeX instalado en el equipo (se compila en Overleaf):
   revisa con scripts que cada `\ref` tenga su `\label`, cada `\cite` su entrada en `refs.bib`, que no
   queden entradas sin citar, `---`, `\textbf` en el texto, `[H]`, `enumerate`, `\\` como separador de
   párrafo ni nombres en formato de código; y que los títulos de Metodología y Resultados sean idénticos y en
   el mismo orden. Cierra también las `\ref` pendientes que dejó anotadas la parte 1.
5. **Imágenes.** Con todos los capítulos ya escritos, deja `img/` como única carpeta de imágenes:
   - Mueve a `img/` lo que se use y esté en `fig/`, actualiza su `\includegraphics` y elimina `fig/`.
   - Para cada archivo de `img/` (y de `fig/`), busca su nombre, con y sin extensión, en todos los `.tex`,
     en `unipd-thesis-modern.cls`, en `main.tex` y en `template/`. Elimina los que no tengan ninguna
     referencia (por ejemplo las de versiones anteriores del documento y los `demo-*` de la plantilla, si
     de verdad no se usan). Empieza por la lista de imágenes en desuso de `avance.md`.
   - Los archivos están en git, así que lo eliminado se puede recuperar; no hagas commits. Anota en el
     reporte final lo movido y lo eliminado.
6. **Reporte final** (archivo `01_2026_TG_MCD_Grupo7_SAE_Desempleo/control_cambios_documento.md`):
   - tabla G7-B1 a G7-B22 y secciones 7 a 11 del PDF → dónde se atiende en el documento (sección y tabla o
     figura) → estado;
   - tabla de criterios de evaluación (hojas Formato, Generales, Datos y Pre-procesamiento, Modelación) →
     cómo se cumple;
   - tabla objetivo → etapas → evidencia, con alerta si alguno queda sin cubrir;
   - citas corregidas, agregadas y eliminadas (de `auditoria_citas.md`); decisiones sin sustento
     bibliográfico (convenciones propias);
   - discrepancias entre fuentes de cifras y figuras pendientes de regenerar;
   - etiquetas viejas → nuevas y estimación final de páginas por capítulo;
   - comparación del modelo espacial frente al clásico: cálculos propios hechos (script, tablas de entrada,
     resultado) y dónde aparecen;
   - imágenes movidas a `img/` y eliminadas, y secciones del apéndice con la sección que las cita.

Si algo de este prompt contradice a `CLAUDE.md` en una decisión del código, manda `CLAUDE.md`; si contradice
a los comentarios de la directora en formato, mandan los comentarios. Ante una duda que cambie el contenido
(no la forma), pregunta antes de escribir.
