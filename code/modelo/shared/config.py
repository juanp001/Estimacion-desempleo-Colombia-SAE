"""Parámetros del modelo Fay-Herriot.

G7-B15: las especificaciones candidatas (EC1…ECk) del modelo base Fay-Herriot clásico no se escriben
a mano: se parte del conjunto que eligió `eda_seleccion_covariables`
(`covariables_seleccionadas`, EC1) y se comparan ese conjunto y las especificaciones que
dejan una covariable fuera, generadas en `shared/seleccion_modelo.py`. Así el modelo no puede
quedar desincronizado del análisis exploratorio y la comparación responde a una pregunta
concreta: si cada covariable aporta. EC1…ECk no son los modelos finales del objetivo 1: la
comparación del objetivo 1 es entre el benchmark seleccionado y las especificaciones
espaciales (`fay_herriot_espacial.py`).

El benchmark se elige siguiendo a Morales et al. (2021, p. 453): como el modelo se usa para
predecir fuera de muestra, solo compiten las especificaciones con todas sus covariables
significativas; entre ellas, la de menor AIC y, entre las equivalentes por AIC, la de menos
covariables. El error cuadrático medio del EBLUP y la distancia de Cook se reportan como
diagnósticos (ganancia de precisión y robustez), sin intervenir en la elección.
"""

# ── Tablas fuente (salidas del flujo de selección de covariables) ────────────
# Fuente única de nombres (R-40, R-59): las tablas y constantes que el preprocesamiento también
# usa se importan de preprocesamiento/shared/config.py en lugar de repetirlas aquí. Los nombres
# propios del modelo (TBL_COVARIABLES_SELECCIONADAS, ...) quedan como alias de los de allá. Los
# notebooks de modelo/ ponen `code/` en sys.path antes de importar este módulo.
from preprocesamiento.shared.config import (
    COLS_PESO_POBLACION,
    CV_ACEPTABLE,
    CV_CONFIABLE,
    EXPR_PESO_POBLACION,
    NOMBRE_TOTAL_23,
    TBL_DATOS_MUNICIPALES,
    TBL_DIM_DOMINIO,
    TBL_DIM_INDICADORES,
    TBL_PREFILTRADAS,
    TBL_SELECCIONADAS,
    TBL_SIN_ENCUESTA,
    TBL_TERRIDATA,
    TBL_TRAZABILIDAD,
)

TBL_COVARIABLES_SELECCIONADAS = TBL_SELECCIONADAS
TBL_MUNICIPIOS_SIN_ENCUESTA = TBL_SIN_ENCUESTA
# Nombres oficiales de departamento y municipio por código DIVIPOLA: las dos fuentes de
# dominios escriben los nombres con distinto formato, así que la tabla final se une por
# código y toma los nombres de aquí. (R-54 revisa esta constante en el bloque de ingesta.)
TBL_DIM_DIVIPOLA = "tesis.dim.dim_divipola"
# TBL_DIM_DOMINIO: dominios GEIH (ciudad o ciudad A.M.) y sus municipios miembro (nombres y
# membresía que verifica el benchmarking de nivel 2). TBL_TERRIDATA: de aquí sale el peso del
# benchmarking de nivel 2. TBL_DATOS_MUNICIPALES y NOMBRE_TOTAL_23: cifra oficial del DANE,
# valor de control del benchmarking de nivel 1.

# ── Tablas destino ───────────────────────────────────────────────────────────
TBL_FAY_HERRIOT_RESULTADOS = "tesis.modelo.fay_herriot_resultados"
TBL_FAY_HERRIOT_PREDICCION_SINTETICA = "tesis.modelo.fay_herriot_prediccion_sintetica"
TBL_FAY_HERRIOT_ESTIMACIONES_FINALES = "tesis.modelo.fay_herriot_estimaciones_finales"
TBL_FH_DIAGNOSTICOS_VARIANTES = "tesis.modelo.fh_diagnosticos_variantes"
TBL_FH_COOK = "tesis.modelo.fh_cook"
TBL_FH_SELECCION_MODELO = "tesis.modelo.fh_seleccion_modelo"
TBL_FH_ESTABILIDAD = "tesis.modelo.fh_estabilidad_coeficientes"

# Estabilidad de coeficientes del benchmark (análisis de sensibilidad, no entra en la selección).
ESTABILIDAD_REPLICAS = 1000
ESTABILIDAD_SEMILLA = 42
TBL_FH_COEFICIENTES = "tesis.modelo.fh_coeficientes"
# Sensibilidad a dominios individuales, dejar-un-dominio-fuera (LOAO) completo (G7-B18,
# shared/estabilidad_coeficientes.py): efecto en coeficientes, en los EBLUP de los dominios que
# quedan, en la predicción sintética de los municipios y en Â. Convenciones propias (ni Morales et
# al. ni los artículos espaciales fijan umbrales de influencia por dominio):
# - un coeficiente se considera movido de forma relevante si cambia más de LOAO_UMBRAL_CAMBIO_EE
#   errores estándar de su estimación con todos los dominios (cambio estandarizado, estilo DFBETAS,
#   que no se infla cuando |β̂| es pequeño como el cambio porcentual);
# - una predicción se considera movida de forma relevante si cambia más de LOAO_UMBRAL_PRED_PP
#   puntos porcentuales (por encima de lo que mueve cambiar la varianza de muestreo, G7-B3).
TBL_FH_LOAO_COEFICIENTES = "tesis.modelo.fh_loao_coeficientes"
TBL_FH_LOAO_PREDICCIONES = "tesis.modelo.fh_loao_predicciones"
TBL_FH_LOAO_DOMINIOS = "tesis.modelo.fh_loao_dominios"
LOAO_UMBRAL_CAMBIO_EE = 1.0
LOAO_UMBRAL_PRED_PP = 0.5
# Validación predictiva del benchmark, dejar-un-dominio-fuera con dos ejercicios (G7-B19,
# shared/validacion_predictiva.py): covariables del benchmark fijas y procedimiento completo (repite la
# selección en cada iteración). Para repetir la selección se leen las candidatas pre-filtradas y
# el diccionario de indicadores; los parámetros de la selección son los de
# preprocesamiento/shared/config.py (cota_covariables, Q_FDR_ELEGIBILIDAD, ...), no se duplican aquí.
TBL_COVARIABLES_PREFILTRADAS = TBL_PREFILTRADAS
TBL_FH_VALIDACION_CRUZADA = "tesis.modelo.fh_validacion_cruzada"
TBL_FH_VALIDACION_METRICAS = "tesis.modelo.fh_validacion_cruzada_metricas"
TBL_FH_VALIDACION_SELECCION = "tesis.modelo.fh_validacion_cruzada_seleccion"
TBL_FH_VALIDACION_FRECUENCIA = "tesis.modelo.fh_validacion_cruzada_frecuencia"
VALIDACION_NIVEL_COBERTURA = 0.95
# Extrapolación de la predicción sintética (B20, shared/extrapolacion.py): rango de cada
# covariable en dominios y municipios, y sensibilidad por municipio (acotada y quitar un dominio).
TBL_FH_RANGOS_COVARIABLES = "tesis.modelo.fh_rangos_covariables"
TBL_FH_SENSIBILIDAD_EXTRAPOLACION = "tesis.modelo.fh_sensibilidad_extrapolacion"
# Sensibilidad a la varianza de muestreo ψ_d y GVF (G7-B3, modelo/sensibilidad_varianza.py).
TBL_SENS_VARIANZA_DIRECTA = "tesis.modelo.sensibilidad_varianza_directa"
TBL_GVF_AJUSTE = "tesis.modelo.gvf_ajuste"
TBL_SENS_VARIANZA_FH = "tesis.modelo.sensibilidad_varianza_fh"
TBL_SENS_VARIANZA_COEFICIENTES = "tesis.modelo.sensibilidad_varianza_coeficientes"
TBL_SENS_VARIANZA_DOMINIOS = "tesis.modelo.sensibilidad_varianza_dominios"
TBL_SENS_VARIANZA_MUNICIPIOS = "tesis.modelo.sensibilidad_varianza_municipios"

# Identificación de la tabla final (R-11, revisión del Grupo 7, sec. 2 y 10). La tabla
# consolidada sale del Fay-Herriot clásico, el benchmark no espacial; la comparación con las
# variantes espaciales del objetivo 1 corre después (fay_herriot_espacial.py) y aún no cierra
# (bloque 6b de la revisión), así que sus cifras son preliminares. Cuando se cierre el objetivo 1,
# ESTADO_RESULTADO pasa a "FINAL_TRAS_COMPARACION_ESPACIAL" citando fhe_cuadro_comparativo.
MODELO_FUENTE_TABLA_FINAL = "FH_CLASICO_BENCHMARK_NO_ESPACIAL"
ESTADO_RESULTADO_TABLA_FINAL = "PRELIMINAR"
COMENTARIO_TABLA_FINAL = (
    "Estimaciones del Fay-Herriot clásico (benchmark no espacial), resultados preliminares: "
    "la comparación con las variantes espaciales del objetivo 1 (fay_herriot_espacial, "
    "fhe_cuadro_comparativo) no ha cerrado. Dominios = EBLUP con benchmarking; municipios = "
    "predicción sintética condicional al modelo (ver CALIDAD_REPORTADA)."
)

# ── Variable objetivo y varianza directa ─────────────────────────────────────
Y_COL = "TASA_DESEMPLEO_PCT"
SE_COL = "SE_BOOTSTRAP_PCT"

# Columnas que identifican un dominio de estimación (ciudad o ciudad A.M.). La clave es
# PER + MES + CODIGO_DOMINIO (código DIVIPOLA de la capital); los nombres acompañan para
# lectura, pero no se usan para unir.
DOMINIO_COLS = [
    "PER",
    "MES",
    "CODIGO_DEPARTAMENTO",
    "CODIGO_DOMINIO",
    "DEPARTAMENTO",
    "NOMBRE_DOMINIO",
    "TIPO_DOMINIO",
]

# Columnas que identifican un municipio objetivo (predicción sintética). CODIGO_DOMINIO_PADRE es
# el dominio con estimación directa que lo contiene (NULL si no hay ninguno): define el grupo del
# benchmarking de nivel 2.
MUNICIPIO_COLS = [
    "PER",
    "MES",
    "CODIGO_DEPARTAMENTO",
    "CODIGO_MUNICIPIO",
    "DEPARTAMENTO",
    "MUNICIPIO",
    "CODIGO_DOMINIO_PADRE",
]

# ── Benchmarking (ver shared/benchmarking.py) ───────────────────────────────
# Peso del nivel 1 (dominios → total de las 23 ciudades): PEA expandida de cada dominio, que
# calcula estimacion_directa con los factores de expansión.
COL_PESO_NIVEL1 = "PEA_EXPANDIDA"
# Peso del nivel 2 (municipios → su dominio A.M.): población de 15 años y más (PET de la serie
# GEIH con proyecciones CNPV 2018), aproximación de la PEA municipal, que es el denominador de la
# tasa de desempleo. Las covariables de los dominios A.M. se agregan con el denominador de cada
# indicador (preprocesamiento/shared/reglas_agregacion.py). Suma de los grupos quinquenales por
# sexo de 15-19 a 80 y más de TerriData (02001xxxx hombres, 02002xxxx mujeres).
# COLS_PESO_POBLACION y EXPR_PESO_POBLACION se importan de preprocesamiento/shared/config.py.
# Aviso cuando el factor de ajuste se aleja de 1 más de esta fracción: «si el modelo es
# adecuado, el factor de ajuste estará en torno a uno» (INE Chile, ENUSC 2018, PDF 23).
UMBRAL_LAMBDA_AVISO = 0.20
# Tolerancia (puntos porcentuales) entre el valor de control del nivel 1 calculado con la
# muestra y la cifra publicada por el DANE.
TOLERANCIA_DANE_PP = 0.01

# ── Umbrales de confiabilidad del CV (G7-B7) ─────────────────────────────────
# CV_CONFIABLE (5 %) y CV_ACEPTABLE (20 %) se importan de preprocesamiento/shared/config.py (R-59;
# allí está el sustento completo), para que la estimación directa, el EBLUP y la predicción
# sintética se clasifiquen con la misma regla sin poder desincronizarse. En municipios el CV es
# condicional al modelo (B21, shared/consolidacion.py): la misma escala se aplica, pero la
# etiqueta publicada lo advierte.

# ── Selección de modelo ──────────────────────────────────────────────────────
# Diferencia de AIC por debajo de la cual dos variantes se consideran equivalentes, según
# la tabla de criterios de decisión del marco teórico. Entre las equivalentes, la
# metodología impone elegir la de menos covariables. Es una convención externa a Morales
# et al. (2021): el libro no fija un umbral de ΔAIC; también se aplica a ΔAICc (complemento, G7-B16).
DELTA_AIC_EQUIVALENTE = 2.0

# Nivel de significancia que deben cumplir todas las covariables de una variante para
# competir (Morales et al., p. 453: al predecir fuera de muestra no conviene incluir
# covariables no significativas). Regla estricta: el libro (p. 454) admite una covariable
# con p > 0.05 si es interpretable; de darse, se reporta como excepción explícita.
ALFA_SIGNIFICANCIA = 0.05

# ── Avisos ───────────────────────────────────────────────────────────────────
# Si el peso γ de la estimación directa no supera este valor en ningún dominio, Â ≈ 0 y el
# EBLUP coincide con el predictor sintético.
UMBRAL_GAMMA_SIN_PESO = 0.01
# Rango admisible de una tasa en porcentaje.
TASA_MINIMA = 0.0
TASA_MAXIMA = 100.0

# ── Fay-Herriot espacial (fay_herriot_espacial.py) ───────────────────────────
# Tablas destino. Se escriben con el prefijo `fhe_` para no pisar las del modelo clásico.
TBL_FHE_MORAN = "tesis.modelo.fhe_moran"
TBL_FHE_VECINDAD = "tesis.modelo.fhe_vecindad"
TBL_FHE_COMPARACION = "tesis.modelo.fhe_comparacion_modelos"
TBL_FHE_CUADRO_COMPARATIVO = "tesis.modelo.fhe_cuadro_comparativo"
TBL_FHE_PERFIL_RHO = "tesis.modelo.fhe_perfil_rho"
TBL_FHE_VALIDACION = "tesis.modelo.fhe_validacion_cruzada"
TBL_FHE_COEFICIENTES = "tesis.modelo.fhe_coeficientes"
TBL_FHE_PREDICCION_OBJETIVO = "tesis.modelo.fhe_prediccion_objetivo"
# R-16: β̂, EE y p del clásico y del espacial lado a lado, por escenario y estructura.
TBL_FHE_COEFICIENTES_COMPARACION = "tesis.modelo.fhe_coeficientes_comparacion"
# R-42: sensibilidad al centroide del nodo de cada A.M. (capital frente a media de miembros).
TBL_FHE_SENSIBILIDAD_CENTROIDE = "tesis.modelo.fhe_sensibilidad_centroide"
# R-13: ρ̂ de la estructura completa según qué objetivos entran como nodos sin dato.
TBL_FHE_SENSIBILIDAD_RHO = "tesis.modelo.fhe_sensibilidad_rho_objetivos"

# R-45: las figuras del modelo (clásico, prefijo fh_, y espacial, prefijo fhe_) se muestran y se
# guardan en este volumen del esquema modelo. El bundle no crea volúmenes: debe existir antes
# de correr el job.
VOLUMEN_FIGURAS_MODELO = "/Volumes/tesis/modelo/figuras"

# R-13: la estructura "completa" impone el SAR sobre dominios + objetivos y evalúa la
# verosimilitud marginal de los dominios (MML de Benedetti et al., 2024, ecs. 18-20; no es el
# estimador de Saei y Chambers, que el artículo distingue en la p. 148). La "muestra" es W solo
# entre dominios con encuesta (Petrucci y Salvati). Los códigos internos no cambian; estos son
# los nombres para el texto.
ETIQUETA_ESTRUCTURA = {
    "completa": "MML (Benedetti et al., 2024)",
    "muestra": "Muestra (Petrucci-Salvati)",
}
# Escenarios de la matriz de proximidad W: (nombre, tipo, parámetro). `knn` = k vecinos más
# cercanos (parámetro k); `inversa` = peso 1/d^potencia (parámetro potencia). Se comparan varios
# porque con 23 dominios dispersos la elección de W puede cambiar la conclusión.
# Criterio de los valores (R-42; no hay un valor "correcto" que los datos identifiquen):
#  · k = 3 es la conectividad mínima con la que ninguna ciudad queda aislada tras simetrizar y
#    cada nodo informa a al menos tres vecinos; k = 5 suaviza más y acerca W a la distancia
#    inversa. Con k > 5, con 23 nodos, W deja de ser local.
#  · potencia 1 decae lento (una ciudad lejana sigue pesando); potencia 2 es el decaimiento de
#    gravedad, que concentra el peso en los vecinos cercanos. Los cuatro escenarios acotan ese
#    rango y la conclusión se reporta sobre todos, no sobre uno elegido por los datos.
ESCENARIOS_W = [
    ("knn3", "knn", 3),
    ("knn5", "knn", 5),
    ("inversa1", "inversa", 1.0),
    ("inversa2", "inversa", 2.0),
]

# Cota del optimizador para |ρ| (< 1 para que I − ρW sea invertible).
RHO_LIMITE = 0.99
# Permutaciones del I de Moran.
N_PERMUTACIONES_MORAN = 9999
# Réplicas del bootstrap paramétrico del MSE espacial (Morales et al., §18.2.3).
BOOTSTRAP_ESPACIAL_REPLICAS = 500
SEMILLA_ESPACIAL = 42
# Criterio para preferir el modelo espacial al clásico (R-43): prueba de razón de verosimilitudes
# de ρ = 0 con p < ALFA_LRT, en la estructura "muestra" (R-13). El ΔAIC (clásico − espacial) se
# reporta como descripción: con un parámetro de diferencia, ΔAIC = LRT − 2 de forma exacta, así
# que "ΔAIC > 2" y "p(LRT) < 0.05" son el mismo estadístico y no son dos respaldos.
ALFA_LRT = 0.05
