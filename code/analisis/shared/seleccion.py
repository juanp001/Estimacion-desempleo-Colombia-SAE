"""Selección final de covariables auxiliares.

La selección es **cualitativa y secuencial**: cada paso descarta por una razón única,
verificable con estadística básica, y el recorrido de cada covariable queda registrado. No
hay pesos, puntajes compuestos ni criterios de información.

    candidatas conceptualmente elegibles (catálogo de literatura)
      → filtro de robustez        (se descarta lo que depende de un solo dominio)
      → resolución de redundancia (un representante por grupo de covariables equivalentes:
                                   enlace completo, todos los pares con |r| ≥ umbral; el
                                   representante es el primer integrante elegible por
                                   orden de Cook, con retroceso)
      → ficha de decisión         (q de Benjamini-Hochberg del p-valor de la pendiente del
                                   Fay-Herriot univariado, que incorpora ψ_d; signo
                                   esperado como diagnóstico; entre las elegibles, las de
                                   mayor asociación hasta la cota de parsimonia)
      → verificación              (multicolinealidad del conjunto elegido)

Por qué no se usa el AIC ni un ranking compuesto
-----------------------------------------------
No se cierra con una búsqueda exhaustiva de especificaciones por AIC sobre el modelo
Fay-Herriot ni con un puntaje compuesto ``C = (1-α)·Q + α·(L/3)``. Un puntaje así mezcla
componentes que miden lo mismo con pesos arbitrarios, y el resultado lo fija una
restricción de una covariable por dimensión. La búsqueda por AIC, con 23 dominios,
reutilizaría los mismos datos que ajustan el modelo y produciría docenas de
especificaciones equivalentes entre las que la elección volvería a ser una regla añadida. La
selección cualitativa es más fácil de sustentar: cada covariable entra o sale por una
razón que se puede leer en su fila de la ficha de decisión.

La comparación entre especificaciones del modelo, con significancia de los coeficientes y
AIC, se hace en el notebook del modelo sobre el conjunto elegido y sus variantes dejando
una covariable fuera.
"""

import contextlib
import io

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from analisis.shared import diagnosticos as diag
from analisis.shared.diagnosticos import vif_conjunto

# Columnas del Fay-Herriot univariado que la elegibilidad y la ficha arrastran (G7-B8).
COLUMNAS_FH = [
    "r_ponderada",
    "Beta_FH",
    "IC_FH_inf",
    "IC_FH_sup",
    "IC_FH_contiene_cero",
    "p_FH",
    "q_FH",
    "Estabilidad_boot",
]
# Nombre de la medida única de asociación cuando decide el Fay-Herriot univariado (G7-B13).
MEDIDA_FH = "r ponderada (FH)"
# Columnas del diagnóstico de forma funcional que la ficha arrastra (G7-B13).
COLUMNAS_FORMA = ["p_curvatura", "dAIC_log", "Forma_funcional"]


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
        influencia (pd.DataFrame): Salida de `diagnosticos.influencia_fh()`.
        estabilidad (pd.DataFrame): Salida de `diagnosticos.estabilidad_fh()`.
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


def evaluar_elegibilidad(
    candidatas: list,
    ic: pd.DataFrame,
    signo_esperado: dict,
    fh: pd.DataFrame,
    q_fdr: float,
    exigir_signo: bool = False,
) -> pd.DataFrame:
    """Aplica a cada candidata las reglas de elegibilidad de la ficha de decisión.

    Son las reglas de `ficha_decision()` que dependen de la asociación con la respuesta,
    separadas para que la resolución de redundancia pueda consultarlas al elegir
    representante (G7-B11) sin duplicar la lógica:

    * la pendiente del **Fay-Herriot univariado** (G7-B8) incorpora la varianza de
      muestreo ψ_d de cada dominio, que la correlación ignora. El intervalo de Fisher de la
      correlación se conserva en la salida como descripción.
    * Decide el control de la tasa de falsos descubrimientos (G7-B9): la candidata es
      elegible si el p-valor de β1, ajustado por Benjamini-Hochberg sobre todas las
      candidatas (`q_FH`), es menor o igual que `q_fdr`. Exigir un intervalo al 95 % sin
      cero en cada una de las candidatas es la misma prueba al 5 % repetida sin corrección
      por multiplicidad.

    La medida de asociación (`Medida`, `r_interpretable`) es la **correlación
    ponderada del mismo modelo** (G7-B13): la pendiente de β1 en escala de correlación. Así
    el intervalo que decide, el orden de la parsimonia y el signo observado salen de una
    sola medida. Pearson y Spearman quedan en la tabla bivariada como descripción.

    El signo esperado del catálogo es un **diagnóstico de coherencia sustantiva, no un
    filtro** (G7-B12): la columna `Signo_coherente` lo registra, pero no cambia la
    elegibilidad. Una asociación de signo contrario a la literatura puede contener
    información, y el signo bivariado no tiene por qué coincidir con el coeficiente
    parcial del modelo multivariado. Con `exigir_signo=True` se reproduce la regla
    anterior (signo contrario → no elegible); se usa solo para el escenario de
    sensibilidad «sin las covariables de signo inesperado».

    Args:
        candidatas (list[str]): Códigos a evaluar.
        ic (pd.DataFrame): Salida de `diagnosticos.tabla_ic_correlacion()`.
        signo_esperado (dict): Mapa código → `"+"`, `"-"` o `"±"`.
        fh (pd.DataFrame): Salida de `diagnosticos.fh_univariado()`, opcionalmente
            con la columna `Estabilidad_boot` de `diagnosticos.estabilidad_bootstrap()`.
        q_fdr (float): Tasa de falsos descubrimientos con la que se declara elegible.
        exigir_signo (bool): Si es True, el signo contrario al esperado vuelve no elegible.

    Returns:
        pd.DataFrame: Una fila por candidata con `Codigo`, `Medida`, `r_interpretable`,
            `Signo_esperado`, `Signo_observado`, `Signo_coherente` (`"sí"`, `"no"` o `"—"`
            si el catálogo no fija dirección), `IC_inf`, `IC_sup`, `IC_contiene_cero`
            (Fisher), las columnas del Fay-Herriot univariado presentes en `fh`
            (`r_ponderada`, `Beta_FH`, `IC_FH_*`, `p_FH`, `q_FH`, `Estabilidad_boot`),
            `Elegible` (`"sí"`/`"no"`) y `Motivo` (vacío si es elegible).

    Example:
        >>> evaluar_elegibilidad(CANDIDATAS, df_ic, SIGNO, df_fh, Q_FDR_ELEGIBILIDAD)
    """
    ic_idx = ic.set_index("Codigo")
    fh_idx = fh.set_index("Codigo")

    filas = []
    for codigo in candidatas:
        # Una sola medida (G7-B13): la del modelo que decide la elegibilidad.
        medida = MEDIDA_FH
        r = float(fh_idx.loc[codigo, "r_ponderada"])
        esperado = signo_esperado.get(codigo, "±")
        observado = "+" if r > 0 else "-"
        coherente = (
            "—" if esperado == "±" else ("sí" if observado == esperado else "no")
        )
        f = fh_idx.loc[codigo]
        sin_evidencia = f["q_FH"] > q_fdr
        texto_evidencia = (
            f"p-valor de la pendiente del Fay-Herriot univariado ajustado por "
            f"Benjamini-Hochberg sobre {len(fh_idx)} candidatas: q = {f['q_FH']:.3f} > "
            f"{q_fdr} (p sin ajustar = {f['p_FH']:.3f})"
        )

        if sin_evidencia:
            motivo = texto_evidencia
        elif exigir_signo and coherente == "no":
            motivo = f"signo observado ({observado}) contrario al esperado por el mecanismo ({esperado})"
        else:
            motivo = ""

        fila = {
            "Codigo": codigo,
            "Medida": medida,
            "r_interpretable": round(r, 3),
            "Signo_esperado": esperado,
            "Signo_observado": observado,
            "Signo_coherente": coherente,
            "IC_inf": float(ic_idx.loc[codigo, "IC_inf"]),
            "IC_sup": float(ic_idx.loc[codigo, "IC_sup"]),
            "IC_contiene_cero": ic_idx.loc[codigo, "IC_contiene_cero"],
        }
        for columna in COLUMNAS_FH:
            if columna in fh_idx.columns:
                fila[columna] = fh_idx.loc[codigo, columna]
        fila["Elegible"] = "no" if motivo else "sí"
        fila["Motivo"] = motivo
        filas.append(fila)
    return pd.DataFrame(filas)


def resolver_redundancia(
    df: pd.DataFrame,
    columnas: list,
    influencia: dict,
    alias: dict = None,
    umbral: float = 0.80,
    elegibilidad: pd.DataFrame = None,
) -> tuple:
    """Conserva una sola covariable por grupo de covariables mutuamente redundantes.

    Agrupa las candidatas por enlace completo sobre la distancia ``1 - |r|``, cortando el
    dendrograma en ``1 - umbral``: dentro de cada grupo **todos** los pares tienen
    correlación de magnitud mayor o igual que `umbral` (G7-B10). Las componentes conexas
    del grafo de correlaciones, usadas antes, equivalen al enlace simple y unen por
    encadenamiento covariables que no son redundantes entre sí: la correlación alta no es
    transitiva. Luego elige un representante por grupo.

    El orden de preferencia dentro del grupo es determinista: la asociación menos
    dependiente de un dominio individual (menor distancia de Cook máxima) y, a igualdad, el
    orden alfabético del código. No usa la magnitud de la correlación con la respuesta.

    Retroceso (G7-B11): si se entrega `elegibilidad`, el representante es el **primer
    integrante, en ese orden, que cumple las reglas de elegibilidad** de la ficha de
    decisión. Antes el representante se fijaba solo por Cook y, si después resultaba no
    elegible, el grupo entero desaparecía aunque otro integrante sí fuera elegible. Las
    reglas son las mismas que la ficha aplicaría de todos modos, de modo que el retroceso
    no añade ningún criterio sobre la respuesta: solo evita que el orden de los pasos
    elimine una dimensión. Si ningún integrante es elegible, se conserva el primero por
    Cook y la ficha lo declarará no elegible.

    Args:
        df (pd.DataFrame): Datos con una fila por dominio.
        columnas (list[str]): Covariables candidatas (normalmente las robustas).
        influencia (dict): Mapa código → distancia de Cook máxima.
        alias (dict | None): Mapa código → alias legible.
        umbral (float): Magnitud de correlación que define la redundancia.
        elegibilidad (pd.DataFrame | None): Salida de `evaluar_elegibilidad()`. Sin ella
            no hay retroceso y el representante es el de menor Cook.

    Returns:
        tuple[list, pd.DataFrame]: (representantes, reporte). El reporte tiene una fila por
            covariable con su grupo, si fue elegida representante y el motivo.

    Example:
        >>> representantes, reporte = resolver_redundancia(
        ...     df, codigos, cook, alias, elegibilidad=df_elegibilidad)
    """
    alias = alias or {}
    grupos = _grupos_enlace_completo(df[columnas], umbral)
    eleg = (
        elegibilidad.set_index("Codigo")
        if elegibilidad is not None
        else pd.DataFrame(columns=["Elegible", "Motivo"])
    )

    def es_elegible(codigo):
        return codigo in eleg.index and eleg.loc[codigo, "Elegible"] == "sí"

    representantes, filas = [], []
    for n_grupo, grupo in enumerate(grupos, 1):
        orden = sorted(grupo, key=lambda c: (influencia.get(c, np.inf), c))
        elegida = next((c for c in orden if es_elegible(c)), orden[0])
        saltadas = orden[: orden.index(elegida)]
        representantes.append(elegida)
        for codigo in grupo:
            if len(grupo) == 1:
                motivo = "sin covariables redundantes"
            elif codigo == elegida and saltadas:
                motivo = (
                    f"representante del grupo por retroceso: primer integrante elegible en "
                    f"orden de Cook máxima ({influencia.get(codigo, float('nan')):.3f}); antes "
                    + "; ".join(
                        f"{alias.get(c, c)} (Cook {influencia.get(c, float('nan')):.3f}) no es "
                        f"elegible: {eleg.loc[c, 'Motivo']}"
                        for c in saltadas
                    )
                )
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
    ic: pd.DataFrame,
    robustez: pd.DataFrame,
    redundancia: pd.DataFrame,
    signo_esperado: dict,
    fh: pd.DataFrame,
    q_fdr: float,
    alias: dict = None,
    dimension: dict = None,
    p_maximo: int = 4,
    exigir_signo: bool = False,
    forma: pd.DataFrame = None,
) -> tuple:
    """Construye la ficha de decisión de cada candidata y elige el conjunto final.

    Reúne en una fila por covariable la evidencia descriptiva y diagnóstica ya calculada y
    aplica, en este orden, reglas explícitas:

    1. Descartada por robustez → ``descartada``.
    2. No es representante de su grupo de redundancia → ``descartada``. Con retroceso
       (G7-B11) el representante ya es el primer integrante elegible del grupo, de modo
       que este paso no elimina una dimensión que tenía una covariable elegible.
    3. La pendiente del Fay-Herriot univariado, que pesa cada dominio por ``1/(Â + ψ_d)``
       (G7-B8), decide con el control de falsos descubrimientos (G7-B9): ``q_FH > q_fdr`` →
       ``no elegible``, con el p-valor de β1 ajustado por Benjamini-Hochberg sobre todas las
       candidatas. El intervalo de Fisher de la correlación queda en la ficha como
       descripción. La ficha muestra además la estabilidad bootstrap si `fh` la trae.
    4. El signo esperado del catálogo es un **diagnóstico, no un filtro** (G7-B12): la
       columna `Signo_coherente` lo registra y, si una covariable elegible tiene signo
       contrario al esperado, su motivo lo advierte para que se interprete en el documento.
       Con `exigir_signo=True` se aplica la regla anterior (signo contrario → ``no
       elegible``), que se usa solo como escenario de sensibilidad.
    5. Entre las ``elegibles`` se seleccionan las `p_maximo` de mayor asociación en valor
       absoluto. La asociación es la correlación ponderada del Fay-Herriot univariado, la
       misma medida que decide la elegibilidad (G7-B13). El resto queda como
       ``elegible, no seleccionada por parsimonia``.
    6. La forma funcional es un **diagnóstico** (G7-B13): con `forma`, la ficha registra la
       prueba de curvatura y la comparación con la escala logarítmica, y si una elegible
       queda en «revisar», su motivo lo advierte. Ninguna covariable se transforma.

    Args:
        candidatas (list[str]): Códigos de las candidatas conceptualmente elegibles.
        ic (pd.DataFrame): Salida de `diagnosticos.tabla_ic_correlacion()`.
        robustez (pd.DataFrame): Salida de `filtrar_por_robustez()`.
        redundancia (pd.DataFrame): Salida de `resolver_redundancia()`.
        signo_esperado (dict): Mapa código → `"+"`, `"-"` o `"±"`.
        fh (pd.DataFrame): Salida de `diagnosticos.fh_univariado()` (G7-B8).
        q_fdr (float): Tasa de falsos descubrimientos de la elegibilidad (G7-B9).
        alias (dict | None): Mapa código → alias legible.
        dimension (dict | None): Mapa código → dimensión conceptual.
        p_maximo (int): Número máximo de covariables seleccionadas.
        exigir_signo (bool): Si es True, el signo contrario al esperado vuelve no elegible
            (escenario de sensibilidad de G7-B12).
        forma (pd.DataFrame | None): Salida de `diagnosticos.forma_funcional()` (G7-B13).

    Returns:
        tuple[list, pd.DataFrame]: (seleccionadas, ficha). `seleccionadas` conserva el orden
            por asociación descendente; `ficha` tiene una fila por candidata con la
            evidencia y la decisión.

    Raises:
        ValueError: Si ninguna candidata resulta elegible.

    Example:
        >>> seleccionadas, ficha = ficha_decision(
        ...     CANDIDATAS, df_ic, df_robustez, df_redundancia, SIGNO, df_fh,
        ...     Q_FDR_ELEGIBILIDAD, ALIAS, DIMENSION)
    """
    alias = alias or {}
    dimension = dimension or {}
    rob = robustez.set_index("Codigo")
    red = redundancia.set_index("Codigo")
    # Mismas reglas que usa resolver_redundancia() para el retroceso (G7-B11).
    eleg = evaluar_elegibilidad(
        candidatas,
        ic,
        signo_esperado,
        fh,
        q_fdr,
        exigir_signo=exigir_signo,
    ).set_index("Codigo")
    columnas_fh = [c for c in COLUMNAS_FH if c in eleg.columns]
    forma_idx = forma.set_index("Codigo") if forma is not None else None

    filas = []
    for codigo in candidatas:
        e = eleg.loc[codigo]
        robusta = rob.loc[codigo, "Decision"] == "conservada"
        representante = codigo in red.index and red.loc[codigo, "Representante"] == "sí"

        if not robusta:
            decision, motivo = "descartada", f"robustez: {rob.loc[codigo, 'Motivo']}"
        elif not representante:
            decision, motivo = "descartada", f"redundancia: {red.loc[codigo, 'Motivo']}"
        elif e["Elegible"] == "no":
            decision, motivo = "no elegible", e["Motivo"]
        else:
            decision, motivo = "elegible", ""

        filas.append(
            {
                "Alias": alias.get(codigo, codigo),
                "Codigo": codigo,
                "Dimension": dimension.get(codigo, "—"),
                "Signo_esperado": e["Signo_esperado"],
                "Signo_observado": e["Signo_observado"],
                "Signo_coherente": e["Signo_coherente"],
                "Medida": e["Medida"],
                "r_interpretable": e["r_interpretable"],
                "IC_inf": e["IC_inf"],
                "IC_sup": e["IC_sup"],
                "IC_contiene_cero": e["IC_contiene_cero"],
                **{c: e[c] for c in columnas_fh},
                **(
                    {c: forma_idx.loc[codigo, c] for c in COLUMNAS_FORMA}
                    if forma_idx is not None
                    else {}
                ),
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
        ficha.loc[idx, "Motivo"] += f"; q de Benjamini-Hochberg = {fila['q_FH']:.3f}"
        if "Estabilidad_boot" in fila:
            ficha.loc[
                idx, "Motivo"
            ] += f", estabilidad bootstrap = {fila['Estabilidad_boot']:.2f}"
        if forma_idx is not None and fila["Forma_funcional"] == "revisar":
            ficha.loc[idx, "Motivo"] += (
                f"; forma funcional a revisar (curvatura p = {fila['p_curvatura']:.3f}, "
                f"ΔAIC con log = {fila['dAIC_log']:.2f}) antes de fijar el predictor "
                "lineal (G7-B13)"
            )
        if fila["Signo_coherente"] == "no":
            ficha.loc[idx, "Motivo"] += (
                f"; signo observado ({fila['Signo_observado']}) contrario al esperado "
                f"({fila['Signo_esperado']}): se conserva, pero requiere interpretación (G7-B12)"
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


def sensibilidad_signo(
    ficha_base: pd.DataFrame,
    seleccionadas_base: list,
    ficha_sin: pd.DataFrame,
    seleccionadas_sin: list,
    alias: dict = None,
) -> pd.DataFrame:
    """Compara la selección con y sin las covariables de signo inesperado (G7-B12).

    El escenario base trata el signo esperado como diagnóstico; el alternativo lo exige
    como filtro (la regla anterior). Si ambos coinciden, el signo no condiciona el
    resultado; si difieren, la tabla muestra qué covariables entran o salen para que el
    documento interprete el signo inesperado en lugar de ocultarlo.

    Args:
        ficha_base (pd.DataFrame): Ficha con el signo como diagnóstico.
        seleccionadas_base (list[str]): Conjunto final del escenario base (tras VIF).
        ficha_sin (pd.DataFrame): Ficha con `exigir_signo=True`.
        seleccionadas_sin (list[str]): Conjunto final del escenario sin signo inesperado.
        alias (dict | None): Mapa código → alias legible.

    Returns:
        pd.DataFrame: Una fila por escenario con la regla de signo, el número de elegibles,
            las seleccionadas, las elegibles de signo inesperado y la diferencia con el base.

    Example:
        >>> sensibilidad_signo(df_ficha, SELECCIONADAS, df_ficha_sin, sel_sin, ALIAS)
    """
    alias = alias or {}

    def nombres(codigos):
        return ", ".join(alias.get(c, c) for c in codigos) or "—"

    def resumen(escenario, regla, ficha, seleccionadas):
        elegibles = ficha["Decision"].isin(["seleccionada", "no seleccionada"])
        inesperado = ficha.loc[elegibles & (ficha["Signo_coherente"] == "no"), "Codigo"]
        return {
            "Escenario": escenario,
            "Regla_signo": regla,
            "N_elegibles": int(elegibles.sum()),
            "Seleccionadas": nombres(seleccionadas),
            "Elegibles_signo_inesperado": nombres(inesperado),
        }

    filas = [
        resumen("base", "diagnóstico", ficha_base, seleccionadas_base),
        resumen("sin signo inesperado", "filtro", ficha_sin, seleccionadas_sin),
    ]
    salen = [c for c in seleccionadas_base if c not in seleccionadas_sin]
    entran = [c for c in seleccionadas_sin if c not in seleccionadas_base]
    filas[0]["Diferencia_con_base"] = "—"
    filas[1]["Diferencia_con_base"] = (
        "mismo conjunto"
        if not salen and not entran
        else f"salen: {nombres(salen)}; entran: {nombres(entran)}"
    )
    tabla = pd.DataFrame(filas)
    print("Sensibilidad al signo esperado: " + filas[1]["Diferencia_con_base"])
    return tabla


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


def seleccionar_covariables(
    df: pd.DataFrame,
    candidatas: list,
    y: np.ndarray,
    psi: np.ndarray,
    etiquetas_dominio: np.ndarray,
    signo_esperado: dict,
    alias: dict = None,
    dimension: dict = None,
    p_maximo: int = 4,
    q_fdr: float = 0.10,
    umbral_delta: float = 0.10,
    umbral_redundancia: float = 0.80,
    vif_max: float = 5.0,
    alfa_ic: float = 0.05,
) -> tuple:
    """Repite, sin imprimir, el procedimiento de selección de `eda_seleccion_covariables` (G7-B19).

    Encadena los mismos pasos y funciones que el notebook de selección: Fay-Herriot univariado
    con ψ_d y q de Benjamini-Hochberg, robustez (Cook y dejar-uno-fuera sobre el Fay-Herriot
    univariado), redundancia por enlace completo con retroceso, ficha de decisión (las
    `p_maximo` elegibles de mayor correlación ponderada) y verificación por VIF. Existe para
    poder **repetir la selección completa dentro de la validación cruzada** del modelo
    (`modelo/shared/validacion_predictiva.py`); el notebook de selección no lo usa. Si se
    cambia un paso allí, hay que cambiarlo aquí: el notebook del modelo comprueba que con los
    mismos datos este procedimiento reproduce `covariables_seleccionadas`.

    No calcula la estabilidad bootstrap (`Estabilidad_boot`, descriptiva) ni la forma
    funcional (diagnóstico): ninguna decide la selección.

    Args:
        df (pd.DataFrame): Una fila por dominio, con una columna por candidata.
        candidatas (list[str]): Columnas de `df` con las candidatas conceptuales.
        y (np.ndarray): Estimación directa de cada dominio, shape (n,).
        psi (np.ndarray): Varianza de muestreo ψ_d = SE² de cada dominio, shape (n,).
        etiquetas_dominio (np.ndarray): Nombre de cada dominio, shape (n,).
        signo_esperado (dict): Mapa código → `"+"`, `"-"` o `"±"`.
        alias (dict | None): Mapa código → alias legible.
        dimension (dict | None): Mapa código → dimensión conceptual.
        p_maximo (int): Cota de parsimonia del conjunto seleccionado.
        q_fdr (float): Tasa de falsos descubrimientos de la elegibilidad (G7-B9).
        umbral_delta (float): Cambio máximo tolerado en la correlación ponderada (G7-B8).
        umbral_redundancia (float): |r| que define la redundancia (G7-B10).
        vif_max (float): Umbral de multicolinealidad.
        alfa_ic (float): Nivel del intervalo del Fay-Herriot univariado.

    Returns:
        tuple[list, pd.DataFrame]: (seleccionadas, ficha). `seleccionadas` es la lista final
            de columnas tras el VIF, vacía si ninguna candidata resulta elegible (en ese caso
            `ficha` es un DataFrame vacío).

    Example:
        >>> sel, ficha = seleccionar_covariables(df_cand, CANDIDATAS, Y, PSI, nombres, SIGNO)
    """
    alias = alias or {}
    y = np.asarray(y, dtype=float)
    psi = np.asarray(psi, dtype=float)
    with contextlib.redirect_stdout(io.StringIO()):
        df_ic = diag.tabla_ic_correlacion(df, candidatas, y, alias=alias, alfa=alfa_ic)
        df_fh = diag.fh_univariado(df, candidatas, y, psi, alias=alias, alfa=alfa_ic)
        influencia = diag.influencia_fh(
            df, candidatas, y, psi, etiquetas_dominio, alias=alias
        )
        estabilidad = diag.estabilidad_fh(
            df, candidatas, y, psi, etiquetas_dominio, alias=alias
        )
        supervivientes, robustez = filtrar_por_robustez(
            candidatas, influencia, estabilidad, umbral_delta=umbral_delta, alias=alias
        )
        if not supervivientes:
            return [], pd.DataFrame()
        elegibilidad = evaluar_elegibilidad(
            candidatas, df_ic, signo_esperado, fh=df_fh, q_fdr=q_fdr
        )
        _, redundancia = resolver_redundancia(
            df,
            supervivientes,
            influencia=influencia.set_index("Codigo")["Cook_max"].to_dict(),
            alias=alias,
            umbral=umbral_redundancia,
            elegibilidad=elegibilidad,
        )
        try:
            seleccionadas, ficha = ficha_decision(
                candidatas,
                df_ic,
                robustez,
                redundancia,
                signo_esperado=signo_esperado,
                alias=alias,
                dimension=dimension,
                p_maximo=p_maximo,
                fh=df_fh,
                q_fdr=q_fdr,
            )
        except ValueError:
            return [], pd.DataFrame()
        restantes = ficha.loc[ficha["Decision"] == "no seleccionada", "Codigo"].tolist()
        seleccionadas, _, _ = ajustar_por_vif(
            df, seleccionadas, restantes, vif_max=vif_max, alias=alias
        )
    return seleccionadas, ficha


def _grupos_enlace_completo(df: pd.DataFrame, umbral: float) -> list:
    """Grupos de covariables en los que todos los pares alcanzan el umbral de correlación.

    Agrupamiento jerárquico aglomerativo con enlace completo sobre la disimilitud
    ``1 - |r|``. El enlace completo mide la distancia entre dos grupos como la mayor
    disimilitud entre sus miembros (James et al., 2021, Tabla 12.3, p. 524), de modo que al
    cortar el dendrograma en ``1 - umbral`` cada grupo cumple ``|r| >= umbral`` en todos sus
    pares. El enlace simple, equivalente a las componentes conexas que se usaban antes,
    produce grupos encadenados que crecen uniendo una covariable a la vez (misma página).

    Nota:
        `preprocesamiento.shared.feature_selection.agrupar_por_correlacion` sigue usando
        componentes conexas, pero solo para reportar duplicados con ``|r| >= 0.999`` en el
        pre-filtrado, sin descartar covariables; con ese umbral el encadenamiento no
        cambia los grupos.

    Args:
        df (pd.DataFrame): Covariables numéricas.
        umbral (float): Magnitud mínima de correlación que deben cumplir todos los pares
            de un grupo.

    Returns:
        list[list[str]]: Grupos de códigos, en orden determinista.

    Example:
        >>> # IDF–ING_TRIB_PC 0.81, ING_TRIB_PC–VA_PC 0.93, IDF–VA_PC 0.73
        >>> _grupos_enlace_completo(df_fiscal, 0.80)
        [['ING_TRIB_PC', 'VA_PC'], ['IDF']]
    """
    cols = list(df.columns)
    if len(cols) < 2:
        return [cols] if cols else []

    disimilitud = 1 - df.corr().abs().to_numpy()
    np.fill_diagonal(disimilitud, 0.0)
    arbol = linkage(squareform(disimilitud, checks=False), method="complete")
    # La tolerancia deja dentro del grupo un par con |r| exactamente igual al umbral.
    etiquetas = fcluster(arbol, t=1 - umbral + 1e-12, criterion="distance")

    grupos = {}
    for c, etiqueta in zip(cols, etiquetas):
        grupos.setdefault(etiqueta, []).append(c)

    return [
        sorted(g)
        for g in sorted(grupos.values(), key=lambda g: (-len(g), sorted(g)[0]))
    ]
