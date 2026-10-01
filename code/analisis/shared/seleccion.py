"""Selección final de covariables auxiliares.

La selección es **cualitativa y secuencial**: cada paso descarta por una razón única,
verificable con estadística básica, y el recorrido de cada covariable queda registrado. No
hay pesos, puntajes compuestos ni criterios de información.

    candidatas conceptualmente elegibles (catálogo de literatura)
      → filtro de robustez        (se descarta lo que depende de un solo dominio)
      → resolución de redundancia (un representante por grupo de covariables equivalentes)
      → ficha de decisión         (intervalo de la correlación y signo esperado; entre las
                                   elegibles, las de mayor asociación hasta la cota de
                                   parsimonia)
      → verificación              (multicolinealidad del conjunto elegido)

Por qué no se usa el AIC ni un ranking compuesto
-----------------------------------------------
Una versión anterior cerraba con una búsqueda exhaustiva de especificaciones por AIC sobre
el modelo Fay-Herriot, y otra con un puntaje ``C = (1-α)·Q + α·(L/3)``. Ambas se retiran.
El puntaje mezclaba componentes que medían lo mismo con pesos arbitrarios, y el resultado
lo fijaba una restricción de una covariable por dimensión. La búsqueda por AIC, con 23
dominios, reutilizaba los mismos datos que ajustan el modelo y producía docenas de
especificaciones equivalentes entre las que la elección volvía a ser una regla añadida. La
selección cualitativa es más fácil de sustentar: cada covariable entra o sale por una
razón que se puede leer en su fila de la ficha de decisión.

La comparación entre especificaciones del modelo, con AIC, error cuadrático medio y
distancia de Cook, se hace en el notebook del modelo sobre el conjunto elegido y sus
variantes dejando una covariable fuera.
"""

import numpy as np
import pandas as pd

from analisis.shared_rev.diagnosticos import vif_conjunto


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
    cook = influencia.set_index("Codigo")
    loo = estabilidad.set_index("Codigo")

    robustas, filas = [], []
    for codigo in columnas:
        cook_max = float(cook.loc[codigo, "Cook_max"])
        umbral_cook = float(cook.loc[codigo, "Umbral"])
        delta_max = float(loo.loc[codigo, "Delta_max_abs"])
        invierte = str(loo.loc[codigo, "Invierte_signo"]) != "—"

        apalancada = cook_max > umbral_cook
        inestable = delta_max > umbral_delta or invierte

        if apalancada and inestable:
            decision = "descartada"
            motivo = (
                f"Cook máxima {cook_max:.3f} > {umbral_cook:.3f} en "
                f"{cook.loc[codigo, 'Dominios_influyentes']}, y al excluir "
                f"{loo.loc[codigo, 'Dominio_critico']} la correlación cambia "
                f"{delta_max:.3f}" + (" e invierte el signo" if invierte else "")
            )
        else:
            decision = "conservada"
            robustas.append(codigo)
            if apalancada:
                motivo = (
                    f"un dominio domina la regresión (Cook {cook_max:.3f}) pero la "
                    f"correlación solo cambia {delta_max:.3f} al excluirlo"
                )
            elif inestable:
                motivo = (
                    f"la correlación cambia {delta_max:.3f} al excluir un dominio, "
                    f"sin que ninguno domine la regresión (Cook {cook_max:.3f})"
                )
            else:
                motivo = "asociación estable ante la exclusión de cualquier dominio"

        filas.append(
            {
                "Alias": alias.get(codigo, codigo),
                "Codigo": codigo,
                "Cook_max": round(cook_max, 4),
                "Delta_LOO_max": round(delta_max, 3),
                "Invierte_signo": "sí" if invierte else "no",
                "Decision": decision,
                "Motivo": motivo,
            }
        )

    print(f"Filtro de robustez: {len(columnas)} → {len(robustas)} covariables")
    return robustas, pd.DataFrame(filas)


def resolver_redundancia(
    df: pd.DataFrame,
    columnas: list,
    influencia: dict,
    alias: dict = None,
    umbral: float = 0.80,
) -> tuple:
    """Conserva una sola covariable por grupo de covariables mutuamente redundantes.

    Agrupa las candidatas por componentes conexas del grafo de correlaciones de magnitud
    mayor o igual que `umbral` y elige un representante por grupo. El desempate es
    determinista: la asociación menos dependiente de un dominio individual (menor distancia
    de Cook máxima) y, a igualdad, el orden alfabético del código. No usa la magnitud de la
    correlación con la respuesta, de modo que resolver la redundancia no reintroduce
    selección sobre la variable dependiente.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables candidatas (normalmente las robustas).
        influencia (dict): Mapa código → distancia de Cook máxima.
        alias (dict | None): Mapa código → alias legible.
        umbral (float): Magnitud de correlación que define la redundancia.

    Returns:
        tuple[list, pd.DataFrame]: (representantes, reporte). El reporte tiene una fila por
            covariable con su grupo, si fue elegida representante y el motivo.

    Example:
        >>> representantes, reporte = resolver_redundancia(df, codigos, cook, alias)
    """
    alias = alias or {}
    grupos = _componentes_conexas(df[columnas], umbral)

    representantes, filas = [], []
    for n_grupo, grupo in enumerate(grupos, 1):
        elegida = min(grupo, key=lambda c: (influencia.get(c, np.inf), c))
        representantes.append(elegida)
        for codigo in grupo:
            if len(grupo) == 1:
                motivo = "sin covariables redundantes"
            elif codigo == elegida:
                motivo = (
                    f"representante del grupo: la asociación menos dependiente de un dominio "
                    f"(Cook máxima {influencia.get(codigo, float('nan')):.3f})"
                )
            else:
                motivo = (
                    f"redundante con {alias.get(elegida, elegida)} (|r| >= {umbral})"
                )
            filas.append(
                {
                    "Alias": alias.get(codigo, codigo),
                    "Codigo": codigo,
                    "Grupo": n_grupo,
                    "Tamano_grupo": len(grupo),
                    "Representante": "sí" if codigo == elegida else "no",
                    "Motivo": motivo,
                }
            )

    reporte = pd.DataFrame(filas).sort_values(
        ["Grupo", "Representante"], ascending=[True, False]
    )
    print(
        f"Resolución de redundancia (|r| >= {umbral}): "
        f"{len(columnas)} → {len(representantes)} covariables "
        f"({len(grupos)} grupos)"
    )
    return sorted(representantes), reporte


def ficha_decision(
    candidatas: list,
    bivariado: pd.DataFrame,
    ic: pd.DataFrame,
    robustez: pd.DataFrame,
    redundancia: pd.DataFrame,
    signo_esperado: dict,
    alias: dict = None,
    dimension: dict = None,
    p_maximo: int = 4,
) -> tuple:
    """Construye la ficha de decisión de cada candidata y elige el conjunto final.

    Reúne en una fila por covariable la evidencia descriptiva y diagnóstica ya calculada y
    aplica, en este orden, reglas explícitas:

    1. Descartada por robustez → ``descartada``.
    2. No es representante de su grupo de redundancia → ``descartada``.
    3. El intervalo de Fisher de la correlación contiene el cero → ``no elegible``: la
       evidencia no determina siquiera el signo de la asociación.
    4. El signo observado contradice el mecanismo del catálogo (cuando este fija una
       dirección) → ``no elegible``: una covariable cuyo efecto va en contra de la razón por
       la que se propuso no puede sustentarse en el documento.
    5. Entre las ``elegibles`` se seleccionan las `p_maximo` de mayor asociación en valor
       absoluto, medida con el coeficiente que `tabla_bivariada()` declaró interpretable
       (Pearson, o Spearman cuando valores extremos condicionan la relación lineal). El
       resto queda como ``elegible, no seleccionada por parsimonia``.

    Args:
        candidatas (list[str]): Códigos de las candidatas conceptualmente elegibles.
        bivariado (pd.DataFrame): Salida de `descriptivos.tabla_bivariada()`.
        ic (pd.DataFrame): Salida de `diagnosticos.tabla_ic_correlacion()`.
        robustez (pd.DataFrame): Salida de `filtrar_por_robustez()`.
        redundancia (pd.DataFrame): Salida de `resolver_redundancia()`.
        signo_esperado (dict): Mapa código → `"+"`, `"-"` o `"±"`.
        alias (dict | None): Mapa código → alias legible.
        dimension (dict | None): Mapa código → dimensión conceptual.
        p_maximo (int): Número máximo de covariables seleccionadas.

    Returns:
        tuple[list, pd.DataFrame]: (seleccionadas, ficha). `seleccionadas` conserva el orden
            por asociación descendente; `ficha` tiene una fila por candidata con la
            evidencia y la decisión.

    Raises:
        ValueError: Si ninguna candidata resulta elegible.

    Example:
        >>> seleccionadas, ficha = ficha_decision(CANDIDATAS, bivariado, df_ic, df_robustez,
        ...                                       df_redundancia, SIGNO, ALIAS, DIMENSION)
    """
    alias = alias or {}
    dimension = dimension or {}
    biv = bivariado.set_index("Codigo")
    ic_idx = ic.set_index("Codigo")
    rob = robustez.set_index("Codigo")
    red = redundancia.set_index("Codigo")

    filas = []
    for codigo in candidatas:
        medida = biv.loc[codigo, "Medida_interpretable"]
        r = float(
            biv.loc[codigo, "Spearman_rho"]
            if medida == "Spearman"
            else biv.loc[codigo, "Pearson_r"]
        )
        esperado = signo_esperado.get(codigo, "±")
        observado = "+" if r > 0 else "-"
        contiene_cero = ic_idx.loc[codigo, "IC_contiene_cero"] == "sí"
        robusta = rob.loc[codigo, "Decision"] == "conservada"
        representante = codigo in red.index and red.loc[codigo, "Representante"] == "sí"

        if not robusta:
            decision, motivo = "descartada", f"robustez: {rob.loc[codigo, 'Motivo']}"
        elif not representante:
            decision, motivo = "descartada", f"redundancia: {red.loc[codigo, 'Motivo']}"
        elif contiene_cero:
            decision, motivo = (
                "no elegible",
                f"el intervalo de la correlación [{ic_idx.loc[codigo, 'IC_inf']:.2f}, "
                f"{ic_idx.loc[codigo, 'IC_sup']:.2f}] contiene el cero",
            )
        elif esperado != "±" and observado != esperado:
            decision, motivo = (
                "no elegible",
                f"signo observado ({observado}) contrario al esperado por el mecanismo ({esperado})",
            )
        else:
            decision, motivo = "elegible", ""

        filas.append(
            {
                "Alias": alias.get(codigo, codigo),
                "Codigo": codigo,
                "Dimension": dimension.get(codigo, "—"),
                "Signo_esperado": esperado,
                "Signo_observado": observado,
                "Medida": medida,
                "r_interpretable": round(r, 3),
                "IC_inf": float(ic_idx.loc[codigo, "IC_inf"]),
                "IC_sup": float(ic_idx.loc[codigo, "IC_sup"]),
                "IC_contiene_cero": "sí" if contiene_cero else "no",
                "Robustez": rob.loc[codigo, "Decision"],
                "Redundancia": (
                    "representante"
                    if representante
                    else ("redundante" if codigo in red.index else "no evaluada")
                ),
                "Decision": decision,
                "Motivo": motivo,
            }
        )

    ficha = pd.DataFrame(filas)
    elegibles = ficha[ficha["Decision"] == "elegible"].copy()
    if elegibles.empty:
        raise ValueError(
            "Ninguna candidata resulta elegible; revisar los diagnósticos antes de continuar."
        )

    elegibles["abs_r"] = elegibles["r_interpretable"].abs()
    elegibles = elegibles.sort_values(["abs_r", "Codigo"], ascending=[False, True])
    seleccionadas = elegibles["Codigo"].head(p_maximo).tolist()

    for i, fila in elegibles.reset_index().iterrows():
        idx = ficha.index[ficha["Codigo"] == fila["Codigo"]][0]
        if fila["Codigo"] in seleccionadas:
            ficha.loc[idx, "Decision"] = "seleccionada"
            ficha.loc[idx, "Motivo"] = (
                f"elegible; puesto {i + 1} de {len(elegibles)} por asociación con la respuesta "
                f"(|{fila['Medida']}| = {fila['abs_r']:.2f}), dentro de la cota de {p_maximo} covariables"
            )
        else:
            ficha.loc[idx, "Decision"] = "no seleccionada"
            ficha.loc[idx, "Motivo"] = (
                f"elegible; puesto {i + 1} de {len(elegibles)} por asociación "
                f"(|{fila['Medida']}| = {fila['abs_r']:.2f}), fuera de la cota de {p_maximo} covariables"
            )

    ficha["abs_r"] = ficha["r_interpretable"].abs()
    orden_decision = {
        "seleccionada": 0,
        "no seleccionada": 1,
        "no elegible": 2,
        "descartada": 3,
    }
    ficha = (
        ficha.assign(_orden=ficha["Decision"].map(orden_decision))
        .sort_values(["_orden", "abs_r"], ascending=[True, False])
        .drop(columns=["_orden", "abs_r"])
        .reset_index(drop=True)
    )

    print(
        f"Ficha de decisión: {len(candidatas)} candidatas → {len(elegibles)} elegibles → {len(seleccionadas)} seleccionadas"
    )
    for estado, n in ficha["Decision"].value_counts().items():
        print(f"  · {estado}: {n}")
    return seleccionadas, ficha


def ajustar_por_vif(
    df: pd.DataFrame,
    seleccionadas: list,
    elegibles_restantes: list,
    vif_max: float = 5.0,
    alias: dict = None,
) -> tuple:
    """Garantiza que el conjunto seleccionado no presente multicolinealidad.

    Mientras el mayor factor de inflación de la varianza supere `vif_max`, retira la
    covariable responsable y la sustituye por la siguiente elegible (en el orden de
    asociación que fijó la ficha). Si no quedan sustitutas, el conjunto simplemente se
    reduce. Cada sustitución queda registrada.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        seleccionadas (list[str]): Conjunto elegido por `ficha_decision()`.
        elegibles_restantes (list[str]): Elegibles no seleccionadas, en orden de prioridad.
        vif_max (float): Umbral de multicolinealidad.
        alias (dict | None): Mapa código → alias legible.

    Returns:
        tuple[list, pd.DataFrame, list]: (conjunto final, tabla VIF del conjunto final,
            lista de cadenas que describen cada sustitución realizada).

    Example:
        >>> finales, df_vif, cambios = ajustar_por_vif(df_cand, seleccionadas, restantes)
    """
    alias = alias or {}
    conjunto = list(seleccionadas)
    pendientes = list(elegibles_restantes)
    sustituciones = []

    while True:
        tabla_vif = vif_conjunto(df, conjunto, alias=alias)
        vif_maximo = float(tabla_vif["VIF"].max())
        if vif_maximo <= vif_max or len(conjunto) < 2:
            break
        saliente = tabla_vif.loc[tabla_vif["VIF"].idxmax(), "Codigo"]
        conjunto.remove(saliente)
        mensaje = (
            f"{alias.get(saliente, saliente)} sale por VIF {vif_maximo:.2f} > {vif_max}"
        )
        if pendientes:
            entrante = pendientes.pop(0)
            conjunto.append(entrante)
            mensaje += f"; entra {alias.get(entrante, entrante)}"
        else:
            mensaje += "; sin sustituta, el conjunto se reduce"
        sustituciones.append(mensaje)
        print(f"  VIF: {mensaje}")

    print(
        f"Verificación de multicolinealidad: VIF máximo {float(tabla_vif['VIF'].max()):.3f} (umbral {vif_max})"
    )
    return conjunto, tabla_vif, sustituciones


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
        for b in cols[i + 1 :]:
            if corr.loc[a, b] >= umbral:
                ra, rb = raiz(a), raiz(b)
                if ra != rb:
                    padre[rb] = ra

    grupos = {}
    for c in cols:
        grupos.setdefault(raiz(c), []).append(c)

    return [
        sorted(g)
        for g in sorted(grupos.values(), key=lambda g: (-len(g), sorted(g)[0]))
    ]
