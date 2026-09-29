"""Pre-filtrado de covariables auxiliares — versión revisada.

Diferencias frente a `shared/feature_selection.py` (versión original):

* `filtrar_columnas_sin_na()` se reutiliza sin cambios desde el módulo original.
* `filtrar_varianza_cero()` se sustituye por `filtrar_variabilidad()`, que aplica un
  criterio invariante a la escala de medida. El umbral absoluto de varianza (1e-5) del
  módulo original depende de las unidades del indicador: una tasa expresada en tanto por
  uno y la misma tasa expresada en porcentaje tienen varianzas que difieren en un factor
  de 10.000, de modo que un único umbral absoluto no puede ser correcto para ambas.
* Se elimina `seleccionar_variables_por_correlacion()`. Ese filtro descartaba covariables
  por su correlación con la variable respuesta usando los mismos dominios que después
  ajustan el modelo, lo que sesga al alza las correlaciones de las supervivientes y
  convierte al pre-filtrado en un mecanismo de selección. La asociación con la respuesta
  pasa a tratarse como evidencia descriptiva y diagnóstica en etapas posteriores.
* Se añade `reportar_grupos_redundantes()`, que documenta —sin descartar nada— los grupos
  de covariables mutuamente redundantes. La decisión sobre cuál conservar requiere el
  criterio conceptual que solo está disponible más adelante en el flujo.

El pre-filtrado resultante es enteramente independiente de la variable respuesta.
"""

import numpy as np
import pandas as pd

from preprocesamiento.shared.feature_selection import filtrar_columnas_sin_na  # noqa: F401  (se reexporta)


def filtrar_variabilidad(
    df: pd.DataFrame,
    cv_min: float = 0.001,
    prop_modal_max: float = 0.90,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Descarta covariables sin variación aprovechable entre los dominios.

    Aplica dos criterios invariantes a la escala de medida, ambos dirigidos al mismo
    problema: una columna constante o casi constante es linealmente dependiente del
    intercepto y vuelve singular la matriz de diseño de la regresión sintética.

    1. **Concentración**: se descarta la columna si su valor más frecuente cubre una
       proporción de los dominios mayor que `prop_modal_max`. Este criterio no depende de
       las unidades y detecta indicadores que en la práctica solo toman un valor.
    2. **Variación relativa**: se descarta la columna si su coeficiente de variación
       muestral (desviación estándar sobre el valor absoluto de la media) es menor que
       `cv_min`. El criterio solo se evalúa cuando la media está suficientemente lejos de
       cero; para columnas centradas en cero el cociente no es interpretable y la decisión
       queda en manos del criterio de concentración.

    Args:
        df (pd.DataFrame): Covariables numéricas (filas = dominios, columnas = indicadores).
        cv_min (float): Coeficiente de variación mínimo aceptable.
        prop_modal_max (float): Proporción máxima de dominios que puede acumular el valor
            modal antes de considerar la columna casi constante.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: (df filtrado, reporte). El reporte tiene una
            fila por columna evaluada con su desviación, media, coeficiente de variación,
            proporción modal, decisión y motivo del descarte.

    Raises:
        ValueError: Si `df` está vacío.

    Example:
        >>> df_filtrado, reporte = filtrar_variabilidad(df_sin_na)
        >>> reporte[reporte["Decision"] == "descartada"]["Motivo"].value_counts()
    """
    if df.empty:
        raise ValueError("El DataFrame está vacío.")

    n_dominios = len(df)
    filas = []

    for col in df.columns:
        serie = df[col]
        desv  = float(serie.std(ddof=1))
        media = float(serie.mean())
        prop_modal = float(serie.value_counts(dropna=False).iloc[0] / n_dominios)

        # El CV solo se interpreta si la media está lejos de cero en relación con la
        # dispersión observada; en otro caso se marca como no evaluable.
        cv_evaluable = abs(media) > max(desv, 1e-12) * 1e-6 and abs(media) > 1e-12
        cv = abs(desv / media) if cv_evaluable else np.nan

        if desv == 0.0:
            decision, motivo = "descartada", "constante"
        elif prop_modal > prop_modal_max:
            decision, motivo = "descartada", f"valor modal en {prop_modal:.0%} de los dominios"
        elif cv_evaluable and cv < cv_min:
            decision, motivo = "descartada", f"coeficiente de variación {cv:.2e} < {cv_min}"
        else:
            decision, motivo = "conservada", ""

        filas.append({
            "Codigo":          col,
            "Desviacion":      desv,
            "Media":           media,
            "CV":              cv,
            "Proporcion_modal": prop_modal,
            "Decision":        decision,
            "Motivo":          motivo,
        })

    reporte = pd.DataFrame(filas)
    conservadas = reporte.loc[reporte["Decision"] == "conservada", "Codigo"].tolist()

    print(
        f"Filtro de variabilidad (CV >= {cv_min}, proporción modal <= {prop_modal_max:.0%}): "
        f"{df.shape[1]} → {len(conservadas)} variables "
        f"({df.shape[1] - len(conservadas)} descartadas)"
    )
    return df[conservadas], reporte


def sensibilidad_variabilidad(
    df: pd.DataFrame,
    cvs: list = None,
    props_modales: list = None,
) -> pd.DataFrame:
    """Cuenta cuántas covariables sobreviven al filtro de variabilidad bajo distintos umbrales.

    A diferencia del análisis de sensibilidad de la versión original —que se ejecutaba
    sobre un conjunto ya recortado por el propio umbral y por tanto era tautológico— este
    barrido se calcula sobre el conjunto completo posterior al filtro de completitud, de
    modo que un umbral más laxo sí puede devolver más covariables.

    Args:
        df (pd.DataFrame): Covariables numéricas posteriores al filtro de completitud.
        cvs (list[float] | None): Umbrales de coeficiente de variación a evaluar.
        props_modales (list[float] | None): Umbrales de proporción modal a evaluar.

    Returns:
        pd.DataFrame: Una fila por combinación de umbrales con el número de supervivientes.

    Example:
        >>> sensibilidad_variabilidad(df_sin_na)
    """
    cvs           = cvs if cvs is not None else [0.0001, 0.001, 0.01, 0.05]
    props_modales = props_modales if props_modales is not None else [0.80, 0.90, 0.95]

    filas = []
    for cv in cvs:
        for prop in props_modales:
            supervivientes, _ = filtrar_variabilidad(df, cv_min=cv, prop_modal_max=prop)
            filas.append({
                "CV_minimo":        cv,
                "Proporcion_modal": prop,
                "Supervivientes":   supervivientes.shape[1],
            })
    return pd.DataFrame(filas)


def reportar_grupos_redundantes(df: pd.DataFrame, umbral: float = 0.999) -> pd.DataFrame:
    """Documenta los grupos de covariables mutuamente redundantes, sin descartar ninguna.

    Dos indicadores con correlación de magnitud prácticamente unitaria contienen la misma
    información (con frecuencia son el mismo indicador expresado en sentido inverso, como
    el índice de pobreza multidimensional y su complemento). Conservar ambos en el modelo
    produce colinealidad exacta, pero decidir cuál retirar exige un criterio conceptual que
    en esta etapa todavía no está disponible: por eso aquí solo se reporta.

    Args:
        df (pd.DataFrame): Covariables numéricas.
        umbral (float): Magnitud de correlación a partir de la cual dos columnas se
            consideran redundantes entre sí.

    Returns:
        pd.DataFrame: Una fila por grupo redundante con su tamaño y los códigos que lo
            componen. Vacío si no hay grupos.

    Example:
        >>> reportar_grupos_redundantes(df_filtrado)
    """
    grupos = agrupar_por_correlacion(df, umbral=umbral)
    filas = [
        {"Grupo": i, "N_variables": len(g), "Codigos": ", ".join(g)}
        for i, g in enumerate(grupos, 1)
        if len(g) > 1
    ]
    reporte = pd.DataFrame(filas)
    print(f"Grupos redundantes (|r| >= {umbral}): {len(reporte)} "
          f"({int(reporte['N_variables'].sum() - len(reporte)) if not reporte.empty else 0} "
          f"variables excedentes)")
    return reporte


def agrupar_por_correlacion(df: pd.DataFrame, umbral: float = 0.80) -> list:
    """Agrupa columnas en conjuntos conectados por correlaciones de magnitud alta.

    Construye el grafo cuyos nodos son las covariables y cuyas aristas unen los pares con
    ``|r| >= umbral``, y devuelve sus componentes conexas. Se usa tanto para reportar
    redundancia exacta en el pre-filtrado como para resolverla en la etapa de selección.

    Args:
        df (pd.DataFrame): Covariables numéricas.
        umbral (float): Magnitud mínima de correlación para unir dos covariables.

    Returns:
        list[list[str]]: Grupos de códigos. Las covariables sin pareja forman grupos
            unitarios. El orden dentro de cada grupo y entre grupos es determinista.

    Example:
        >>> agrupar_por_correlacion(df_candidatas, umbral=0.80)
        [['140010004', '140010001'], ['310010008']]
    """
    cols = list(df.columns)
    corr = df.corr().abs()

    padre = {c: c for c in cols}

    def raiz(c):
        while padre[c] != c:
            padre[c] = padre[padre[c]]
            c = padre[c]
        return c

    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            if corr.loc[a, b] >= umbral:
                ra, rb = raiz(a), raiz(b)
                if ra != rb:
                    padre[rb] = ra

    grupos = {}
    for c in cols:
        grupos.setdefault(raiz(c), []).append(c)

    return [sorted(g) for g in sorted(grupos.values(), key=lambda g: (-len(g), sorted(g)[0]))]
