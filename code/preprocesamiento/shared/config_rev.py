"""Parámetros del flujo revisado de pre-filtrado, análisis descriptivo y selección.

Hereda del `shared/config.py` original todo lo que no cambia (tablas fuente, columnas de
metadatos, parámetros de la estimación directa, umbrales de calidad) y añade únicamente lo
propio de la revisión. Las tablas de salida llevan el sufijo `_rev` para poder compararse
con las de la versión original, que quedan intactas.
"""

from preprocesamiento.shared.config import *  # noqa: F401,F403

# ── Tablas destino de la versión revisada ─────────────────────────────────────
TBL_PREFILTRADAS_REV = "tesis.preprocesamiento.covariables_prefiltradas_rev"
TBL_CASCADA_REV = "tesis.preprocesamiento.cascada_prefiltrado_rev"
TBL_SENSIBILIDAD_REV = "tesis.preprocesamiento.sensibilidad_variabilidad_rev"
TBL_CATALOGO_REV = "tesis.preprocesamiento.catalogo_literatura_rev"
TBL_DESCRIPTIVO_UNI = "tesis.preprocesamiento.descriptivo_univariado_rev"
TBL_DESCRIPTIVO_BI = "tesis.preprocesamiento.descriptivo_bivariado_rev"
TBL_DIAGNOSTICOS_REV = "tesis.preprocesamiento.diagnosticos_covariables_rev"
TBL_ROBUSTEZ_REV = "tesis.preprocesamiento.robustez_covariables_rev"
TBL_REDUNDANCIA_REV = "tesis.preprocesamiento.redundancia_covariables_rev"
TBL_DECISION_REV = "tesis.preprocesamiento.decision_covariables_rev"
TBL_VERIFICACION_REV = "tesis.preprocesamiento.verificacion_seleccion_rev"
TBL_TRAZABILIDAD_REV = "tesis.preprocesamiento.trazabilidad_covariables_rev"
TBL_CANDIDATAS_REV = "tesis.preprocesamiento.covariables_candidatas_rev"
TBL_SELECCIONADAS_REV = "tesis.preprocesamiento.covariables_seleccionadas_rev"

# ── Volumen para las figuras destinadas al documento ──────────────────────────
VOLUMEN_FIGURAS = "/Volumes/tesis/preprocesamiento/figuras_eda"

# ── Pre-filtrado (independiente de la variable respuesta) ─────────────────────
# Umbral de coeficiente de variación por debajo del cual la columna se considera
# constante a efectos prácticos. A diferencia del umbral de varianza absoluto de la
# versión original (1e-5), es invariante a las unidades del indicador.
CV_MINIMO = 0.001
# Proporción máxima de dominios que puede acumular el valor modal.
PROP_MODAL_MAXIMA = 0.90
# Magnitud de correlación a partir de la cual dos covariables se consideran duplicadas.
UMBRAL_DUPLICADO = 0.999

# ── Diagnóstico y selección ──────────────────────────────────────────────────
# Magnitud de correlación a partir de la cual dos candidatas se consideran redundantes y
# solo una de ellas puede entrar al modelo.
UMBRAL_REDUNDANCIA = 0.80
# Cambio máximo tolerado en la correlación con la respuesta al excluir un dominio.
UMBRAL_DELTA_LOO = 0.10
# Número máximo de covariables por parsimonia: n/5 con n = 23 dominios.
P_MAXIMO = 4
# Umbral de multicolinealidad para el conjunto finalmente seleccionado.
VIF_MAXIMO = 5.0
# Nivel de confianza del intervalo de Fisher para la correlación con la respuesta.
ALFA_IC_CORRELACION = 0.05

# ── Dominios objetivo sin cobertura muestral ─────────────────────────────────
# Códigos DIVIPOLA de los departamentos del estudio: Cauca (19) y Valle del Cauca (76).
DEPARTAMENTOS_OBJETIVO = [19, 76]
TBL_SIN_ENCUESTA_REV = "tesis.preprocesamiento.municipios_sin_encuesta_rev"
