"""Actualiza avance.md e inventario_cifras.md al cerrar Metodología (parte 1).

Uso: python -I cerrar_parte1.py <carpeta _trabajo>
"""

import sys
from pathlib import Path

base = Path(sys.argv[1])
av, inv = base / "avance.md", base / "inventario_cifras.md"


def cambiar(texto, viejo, nuevo):
    """Reemplaza `viejo` por `nuevo` y falla si `viejo` no está."""
    assert viejo in texto, viejo[:60]
    return texto.replace(viejo, nuevo, 1)


a = av.read_text(encoding="utf-8")
a = cambiar(a, "| Datos (`datos.tex`) | Escrito, pendiente de confirmación |", "| Datos (`datos.tex`) | Confirmado |")
a = cambiar(
    a,
    "| Metodología (`metodologia.tex`) | Pendiente | — | 18 |",
    "| Metodología (`metodologia.tex`) | Escrito, pendiente de confirmación | ≈ 17-19 (2,300 palabras, 1 figura, 18 tablas de ficha) | 18 |",
)
a = cambiar(
    a,
    "Siguiente paso: tras la confirmación de Datos, reescribir `metodologia.tex`.",
    """2026-11-03: Datos confirmado. Se reescribió `metodologia.tex` (16 etapas con ficha, diagrama general
`img/met_flujo_general.png` generado con `img/_script/diagrama_metodologia.py`, tabla etapa → objetivo).
Para la etapa 13 se agregaron al Marco teórico la Ecuación `eq:gamma_esp` (peso de la directa en el
SEBLUP) y una frase sobre la estandarización de residuos para Moran (regla 6).

Siguiente paso: confirmación de Metodología por el equipo. Con eso termina la parte 1; la parte 2
empieza por Resultados con los títulos y etiquetas de la tabla de abajo.""",
)
a = cambiar(
    a,
    """## Comparación espacial frente a clásico (OE1)

Pendiente: se inventaria al escribir la etapa 13 de Metodología (qué filas existen en `fhe_*` y qué
cálculos propios faltan).""",
    """## Comparación espacial frente a clásico (OE1)

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
19.9 %; 21 de 83 extrapolan.""",
)
a = cambiar(
    a,
    """## Apéndice

Sin secciones agregadas todavía.

## Imágenes que la parte 1 deja de usar

Pendiente (se lista al cerrar Datos y Metodología).""",
    """## Apéndice

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

Nueva: `img/met_flujo_general.png` y `.pdf` (script `img/_script/diagrama_metodologia.py`, sin datos).""",
)
a = cambiar(
    a,
    "## Para la parte 2\n",
    """## Etiquetas viejas → nuevas (Metodología)

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

`\\ref` de Metodología a Resultados (la parte 2 debe crearlas con estos nombres): `sec:res_obtencion`,
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
""",
)
av.write_text(a, encoding="utf-8")

s = inv.read_text(encoding="utf-8")
s = cambiar(
    s,
    """Ver la sección «Comparación espacial frente a clásico» de `avance.md` (se completa al cerrar
Metodología, etapa 13).""",
    """Corren en local con lectura de solo lectura de tablas `tesis.*` (o salidas extraídas de los notebooks);
el script va en `_trabajo/calculos/`. Su método está en el Marco teórico y en Metodología (etapas 13 y 16).

| Id | Cálculo | Tablas de entrada | Fórmula (Marco) | Etapa |
|---|---|---|---|---|
| C1 | SEBLUP, ECM y CV de los 23 dominios en el escenario de referencia (knn3, «completa») y γ^S_d | `preprocesamiento.tasa_desempleo_covariables` (Y, SE), `preprocesamiento.covariables_seleccionadas`, coordenadas de `dim.dim_geih_divipola` y `preprocesamiento.municipios_sin_encuesta`; reajuste local con `FayHerriotEspacial` de `code/modelo/shared` (500 réplicas, semilla 42) | `eq:seblup`, `eq:gamma_esp`, `eq:cve`; ECM por bootstrap (Morales p. 494) | 13 |
| C2 | Diferencia espacial − clásico en los 83 municipios: media, máximo absoluto, Pearson, Spearman; cambios de clase de CV (5/20) | `modelo.fhe_prediccion_objetivo` (PRED_CLASICO, PRED_ESPACIAL, CV_CLASICO_PCT, CV_ESPACIAL_PCT) | `eq:pearson`, `eq:spearman`, `eq:cve` | 13 |
| C3 | Lo mismo en los 23 dominios (EBLUP frente a SEBLUP) | `modelo.fay_herriot_resultados` (EBLUP, CV_EBLUP_PCT) + salida de C1 | idem | 13 |
| C4 | I de Moran de las 83 estimaciones finales con W de 3 vecinos estandarizada por filas, p por 9,999 permutaciones | `modelo.fay_herriot_estimaciones_finales` (NIVEL = MUNICIPIO); coordenadas de `fhe_prediccion_objetivo`; `proximidad_knn`, `estandarizar_filas`, `moran_i` de `code/modelo/shared/matriz_proximidad.py` | `eq:moran` | 16 |

Si C1 no reproduce el ρ̂ y el σ̂²_u del notebook, se reporta solo C2 y la incertidumbre de los dominios
espaciales queda como limitación en el reporte final.""",
)
inv.write_text(s, encoding="utf-8")
print("ok")
