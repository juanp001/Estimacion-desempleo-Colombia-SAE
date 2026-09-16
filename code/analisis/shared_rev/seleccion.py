"""Selección final de covariables auxiliares.

Sustituye al ranking compuesto de la versión original, en el que la decisión provenía de un
score ``C = (1-α)·Q + α·(L/3)`` con Q igual al promedio de cinco deseabilidades. Ese
procedimiento presentaba cuatro problemas que no admiten defensa metodológica:

1. Los pesos del promedio y los topes de normalización (0.30, 0.30, 1.00) eran arbitrarios,
   igual que el valor α = 0.30.
2. Tres de las cinco componentes —concordancia entre coeficientes, estabilidad ante
   exclusión de dominios y baja influencia— miden el mismo fenómeno, la sensibilidad a
   valores extremos, de modo que esa información entraba al score contada tres veces.
3. La componente de no redundancia dependía de qué otras candidatas estuvieran presentes,
   por lo que el score de una covariable cambiaba sin que cambiara la covariable.
4. El resultado lo determinaba en realidad la restricción de una covariable por dimensión,
   no el score: sin esa restricción el conjunto ganador era otro.

En su lugar la selección es **secuencial y sin pesos**. Cada paso descarta por una razón
única y verificable, y el paso final usa el criterio de información de Akaike sobre el
propio modelo Fay-Herriot, que ya está definido en el marco teórico y es la práctica
documentada en la literatura de estimación en áreas pequeñas revisada por el proyecto.

    candidatas conceptualmente elegibles
      → resolución de redundancia   (un representante por grupo de covariables equivalentes)
      → filtro de robustez          (se descarta lo que depende de un solo dominio)
      → búsqueda exhaustiva por AIC (subconjuntos de tamaño <= p_max)
      → verificación                (multicolinealidad, signo de los coeficientes)

La restricción de diversidad temática desaparece como regla impuesta: la cobertura de
dimensiones distintas pasa a ser consecuencia del criterio de redundancia, que sí tiene
fundamento estadístico.

Nota sobre reutilización de datos: elegir por AIC emplea los mismos dominios que ajustan el
modelo. La diferencia con el pre-filtro por correlación que se eliminó es que aquí se aplica
sobre un conjunto ya acotado por criterio conceptual, es el procedimiento estándar en la
literatura del área, y sus resultados no se presentan como evidencia confirmatoria sino
como criterio de comparación entre especificaciones.
"""

from itertools import combinations

import numpy as np
import pandas as pd


def resolver_redundancia(
    df: pd.DataFrame,
    columnas: list,
    literatura: dict,
    influencia: dict,
    alias: dict = None,
    umbral: float = 0.80,
) -> tuple:
    """Conserva una sola covariable por grupo de covariables mutuamente redundantes.

    Agrupa las candidatas por componentes conexas del grafo de correlaciones de magnitud
    mayor o igual que `umbral` y elige un representante por grupo. El desempate es
    determinista y está ordenado por fuerza del argumento:

    1. mayor nivel de respaldo conceptual, que se fijó antes de mirar los datos;
    2. menor distancia de Cook máxima, es decir, la asociación menos dependiente de un
       dominio individual;
    3. orden alfabético del código, que solo actúa si las dos anteriores empatan.

    Ninguno de los tres criterios usa la magnitud de la correlación con la respuesta, de
    modo que la resolución de redundancia no reintroduce selección sobre la variable
    dependiente.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables candidatas.
        literatura (dict): Mapa código → nivel de respaldo conceptual.
        influencia (dict): Mapa código → distancia de Cook máxima.
        alias (dict | None): Mapa código → alias legible.
        umbral (float): Magnitud de correlación que define la redundancia.

    Returns:
        tuple[list, pd.DataFrame]: (representantes, reporte). El reporte tiene una fila por
            covariable con su grupo, si fue elegida representante y el motivo.

    Example:
        >>> representantes, reporte = resolver_redundancia(df, codigos, L, cook, alias)
    """
    alias = alias or {}
    grupos = _componentes_conexas(df[columnas], umbral)

    representantes, filas = [], []
    for n_grupo, grupo in enumerate(grupos, 1):
        elegida = min(
            grupo,
            key=lambda c: (-literatura.get(c, 0), influencia.get(c, np.inf), c),
        )
        representantes.append(elegida)
        for codigo in grupo:
            if len(grupo) == 1:
                motivo = "sin covariables redundantes"
            elif codigo == elegida:
                motivo = (f"representante del grupo: mayor respaldo conceptual "
                          f"(L={literatura.get(codigo)}) y Cook máxima "
                          f"{influencia.get(codigo, float('nan')):.3f}")
            else:
                motivo = (f"redundante con {alias.get(elegida, elegida)} "
                          f"(|r| >= {umbral})")
            filas.append({
                "Alias":         alias.get(codigo, codigo),
                "Codigo":        codigo,
                "Grupo":         n_grupo,
                "Tamano_grupo":  len(grupo),
                "Representante": "sí" if codigo == elegida else "no",
                "Motivo":        motivo,
            })

    reporte = pd.DataFrame(filas).sort_values(["Grupo", "Representante"], ascending=[True, False])
    print(f"Resolución de redundancia (|r| >= {umbral}): "
          f"{len(columnas)} → {len(representantes)} covariables "
          f"({len(grupos)} grupos)")
    return sorted(representantes), reporte


def filtrar_por_robustez(
    columnas: list,
    influencia: pd.DataFrame,
    estabilidad: pd.DataFrame,
    umbral_delta: float = 0.10,
    alias: dict = None,
) -> tuple:
    """Descarta las covariables cuya asociación con la respuesta depende de un solo dominio.

    Un único criterio, sostenido por dos evidencias complementarias que deben cumplirse a
    la vez: la distancia de Cook señala que un dominio domina la pendiente de la regresión,
    y la exclusión de ese mismo dominio cambia la correlación más de `umbral_delta` o
    invierte su signo. Exigir ambas condiciones evita descartar covariables por un valor
    extremo que, siendo grande, no altera la relación.

    No se elimina ninguna observación: la consecuencia recae sobre la covariable, porque los
    dominios extremos corresponden a territorios reales y no a errores de medición.

    Args:
        columnas (list[str]): Covariables candidatas.
        influencia (pd.DataFrame): Salida de `diagnosticos.influencia_por_covariable()`.
        estabilidad (pd.DataFrame): Salida de `diagnosticos.estabilidad_loo()`.
        umbral_delta (float): Cambio máximo tolerado en la correlación al excluir un dominio.
        alias (dict | None): Mapa código → alias legible.

    Returns:
        tuple[list, pd.DataFrame]: (covariables robustas, reporte con la decisión y su motivo).

    Example:
        >>> robustas, reporte = filtrar_por_robustez(candidatas, df_cook, df_loo)
    """
    alias = alias or {}
    cook  = influencia.set_index("Codigo")
    loo   = estabilidad.set_index("Codigo")

    robustas, filas = [], []
    for codigo in columnas:
        cook_max   = float(cook.loc[codigo, "Cook_max"])
        umbral_cook = float(cook.loc[codigo, "Umbral"])
        delta_max  = float(loo.loc[codigo, "Delta_max_abs"])
        invierte   = str(loo.loc[codigo, "Invierte_signo"]) != "—"

        apalancada = cook_max > umbral_cook
        inestable  = delta_max > umbral_delta or invierte

        if apalancada and inestable:
            decision = "descartada"
            motivo = (f"Cook máxima {cook_max:.3f} > {umbral_cook:.3f} en "
                      f"{cook.loc[codigo, 'Dominios_influyentes']}, y al excluir "
                      f"{loo.loc[codigo, 'Dominio_critico']} la correlación cambia "
                      f"{delta_max:.3f}" + (" e invierte el signo" if invierte else ""))
        else:
            decision = "conservada"
            robustas.append(codigo)
            if apalancada:
                motivo = (f"un dominio domina la regresión (Cook {cook_max:.3f}) pero la "
                          f"correlación solo cambia {delta_max:.3f} al excluirlo")
            elif inestable:
                motivo = (f"la correlación cambia {delta_max:.3f} al excluir un dominio, "
                          f"sin que ninguno domine la regresión (Cook {cook_max:.3f})")
            else:
                motivo = "asociación estable ante la exclusión de cualquier dominio"

        filas.append({
            "Alias":      alias.get(codigo, codigo),
            "Codigo":     codigo,
            "Cook_max":   round(cook_max, 4),
            "Delta_LOO_max": round(delta_max, 3),
            "Invierte_signo": "sí" if invierte else "no",
            "Decision":   decision,
            "Motivo":     motivo,
        })

    print(f"Filtro de robustez: {len(columnas)} → {len(robustas)} covariables")
    return robustas, pd.DataFrame(filas)


def busqueda_exhaustiva_aic(
    df: pd.DataFrame,
    columnas: list,
    modelo_cls,
    y_col: str,
    se_col: str,
    p_maximo: int = 4,
    alias: dict = None,
) -> pd.DataFrame:
    """Ajusta todos los subconjuntos de covariables hasta `p_maximo` y los ordena por AIC.

    Con una decena de candidatas, evaluar exhaustivamente los subconjuntos de tamaño uno a
    `p_maximo` son unos pocos cientos de ajustes: es más barato que un procedimiento por
    pasos y, a diferencia de este, no depende del orden de entrada ni deja fuera
    combinaciones por el camino recorrido. El resultado es reconstruible en su totalidad.

    El límite `p_maximo` proviene de la cota de parsimonia del proyecto: con 23 dominios el
    modelo admite del orden de cuatro covariables más el intercepto.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio, con `y_col`, `se_col` y las
            covariables.
        columnas (list[str]): Covariables candidatas.
        modelo_cls (type): Clase del modelo Fay-Herriot; debe aceptar
            ``(covars, df, y_col, se_col)`` y exponer `aic` y `r2` tras `ajustar()`.
        y_col (str): Columna con la estimación directa.
        se_col (str): Columna con su error estándar.
        p_maximo (int): Número máximo de covariables por especificación.
        alias (dict | None): Mapa código → alias legible.

    Returns:
        pd.DataFrame: Una fila por especificación ajustada, ordenada por AIC ascendente,
            con el número de covariables, el AIC, su diferencia frente al mejor y el R² del
            predictor sintético. Las especificaciones que no convergen se omiten y se
            informan por consola.

    Raises:
        ValueError: Si `columnas` está vacío.

    Example:
        >>> busqueda_exhaustiva_aic(df, robustas, FayHerriotClasico,
        ...                         "TASA_DESEMPLEO_PCT", "SE_BOOTSTRAP_PCT")
    """
    if not columnas:
        raise ValueError("No hay covariables candidatas para la búsqueda.")

    alias = alias or {}
    filas, fallidas = [], 0

    for tamano in range(1, min(p_maximo, len(columnas)) + 1):
        for subconjunto in combinations(sorted(columnas), tamano):
            try:
                modelo = modelo_cls(list(subconjunto), df, y_col, se_col)
                modelo.ajustar()
            except Exception:
                fallidas += 1
                continue
            filas.append({
                "N_covariables": tamano,
                "Covariables":   " + ".join(alias.get(c, c) for c in subconjunto),
                "Codigos":       ",".join(subconjunto),
                "AIC":           round(float(modelo.aic), 3),
                "R2":            round(float(modelo.r2), 4),
            })

    if not filas:
        raise ValueError("Ninguna especificación pudo ajustarse.")

    resultado = pd.DataFrame(filas).sort_values("AIC").reset_index(drop=True)
    resultado.insert(0, "Rank", resultado.index + 1)
    resultado["Delta_AIC"] = (resultado["AIC"] - resultado["AIC"].min()).round(3)

    print(f"Búsqueda exhaustiva: {len(resultado)} especificaciones ajustadas "
          f"(hasta {p_maximo} covariables)" +
          (f", {fallidas} no convergieron" if fallidas else ""))
    return resultado


def _componentes_conexas(df: pd.DataFrame, umbral: float) -> list:
    """Componentes conexas del grafo de correlaciones de magnitud alta.

    Args:
        df (pd.DataFrame): Covariables numéricas.
        umbral (float): Magnitud mínima de correlación para unir dos covariables.

    Returns:
        list[list[str]]: Grupos de códigos, en orden determinista.
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


def figura_aic(resultado: pd.DataFrame, n_mostrar: int = 15):
    """Compara las mejores especificaciones de la búsqueda exhaustiva por su AIC.

    Muestra la diferencia de AIC frente a la mejor especificación, que es la magnitud
    interpretable: diferencias por debajo de dos unidades indican especificaciones
    prácticamente equivalentes en ajuste, de modo que el gráfico deja ver si la ganadora se
    separa del resto o si comparte el primer puesto con otras.

    Args:
        resultado (pd.DataFrame): Salida de `busqueda_exhaustiva_aic()`.
        n_mostrar (int): Número de especificaciones a graficar.

    Returns:
        matplotlib.figure.Figure: Figura de barras horizontales ordenadas por AIC.

    Example:
        >>> fig = figura_aic(busqueda)
    """
    import matplotlib.pyplot as plt

    mejores = resultado.head(n_mostrar).iloc[::-1]
    colores = ["firebrick" if d == 0 else "steelblue" for d in mejores["Delta_AIC"]]

    fig, ax = plt.subplots(figsize=(9, 0.42 * len(mejores) + 1.5))
    ax.barh(np.arange(len(mejores)), mejores["Delta_AIC"], color=colores, edgecolor="white")
    ax.axvline(2, color="dimgray", linestyle="--", linewidth=1.2,
               label="Diferencia de AIC = 2 (ajuste equivalente)")
    ax.set_yticks(np.arange(len(mejores)))
    ax.set_yticklabels(mejores["Covariables"], fontsize=8)
    ax.set_xlabel("Diferencia de AIC frente a la mejor especificación", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, axis="x", linestyle=":", alpha=0.4)
    plt.tight_layout()
    return fig


def elegir_con_parsimonia(resultado: pd.DataFrame, delta_max: float = 2.0) -> pd.Series:
    """Elige la especificación definitiva entre las que el AIC considera equivalentes.

    Tomar sin más la de menor AIC haría depender el resultado de diferencias que el propio
    criterio declara irrelevantes: una diferencia de unas centésimas no distingue dos
    especificaciones. Por eso la regla es la que el proyecto ya aplica a la comparación de
    modelos: entre las especificaciones con ``Delta_AIC <= delta_max`` se elige la de menor
    número de covariables y, a igualdad de número, la de menor AIC.

    El umbral proviene de la tabla de criterios de decisión del marco teórico, donde una
    diferencia de AIC inferior a dos unidades define modelos equivalentes.

    Args:
        resultado (pd.DataFrame): Salida de `busqueda_exhaustiva_aic()`.
        delta_max (float): Diferencia de AIC por debajo de la cual dos especificaciones se
            consideran equivalentes.

    Returns:
        pd.Series: La fila de la especificación elegida.

    Raises:
        ValueError: Si `resultado` está vacío.

    Example:
        >>> elegida = elegir_con_parsimonia(busqueda)
        >>> elegida["Codigos"].split(",")
    """
    if resultado.empty:
        raise ValueError("La tabla de especificaciones está vacía.")

    equivalentes = resultado[resultado["Delta_AIC"] <= delta_max]
    elegida = equivalentes.sort_values(["N_covariables", "AIC"]).iloc[0]

    print(f"Especificaciones equivalentes (diferencia de AIC <= {delta_max}): {len(equivalentes)}")
    print(f"  mejor AIC:   {resultado.iloc[0]['Covariables']} "
          f"({resultado.iloc[0]['N_covariables']} covariables, AIC {resultado.iloc[0]['AIC']:.3f})")
    print(f"  elegida:     {elegida['Covariables']} "
          f"({elegida['N_covariables']} covariables, AIC {elegida['AIC']:.3f}, "
          f"diferencia {elegida['Delta_AIC']:.3f})")
    return elegida
