"""Sensibilidades del Fay-Herriot espacial a decisiones de construcción de W (R-42, R-13).

Ninguna de las dos decide ni cambia las predicciones del notebook: documentan cuánto dependen
ρ̂ y el AIC de (a) dónde se ubica el nodo de cada área metropolitana y (b) qué municipios sin
encuesta entran como nodos de la estructura completa.

* ``sensibilidad_centroide``: el nodo de un dominio A.M. se ubica por defecto en la capital;
  aquí se compara con la media de las coordenadas de sus municipios miembro (R-42).
* ``sensibilidad_rho_objetivos``: la verosimilitud marginal de la estructura completa
  (Benedetti et al., 2024, ecs. 18-20) supone el SAR sobre todas las áreas de la población, pero
  aquí la «población» es un recorte (los objetivos de Cauca y Valle). ρ̂ cambia según cuáles
  nodos sin dato se incluyan, así que su signo no tiene lectura sustantiva (R-13).
"""

import numpy as np
import pandas as pd
from scipy import stats

from shared.fay_herriot_espacial import FayHerriotEspacial
from shared.matriz_proximidad import distancias_haversine, proximidad_total


def tabla_ajuste_espacial(
    covars: list,
    df: pd.DataFrame,
    y_col: str,
    se_col: str,
    df_objetivo: pd.DataFrame,
    distancias: np.ndarray,
    clasico,
    escenarios: list,
    estructuras: tuple = ("muestra", "completa"),
    rho_limite: float = 0.99,
) -> pd.DataFrame:
    """Ajusta el SEBLUP por escenario y estructura y lo compara con el clásico.

    Args:
        covars (list[str]): Covariables del modelo (sin intercepto).
        df (pd.DataFrame): Dominios con encuesta.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar directo.
        df_objetivo (pd.DataFrame | None): Unidades sin encuesta que entran como nodos de la
            estructura completa (puede estar vacío o ser None).
        distancias (np.ndarray): Distancias en km, shape (n + r, n + r), en el orden
            [dominios, objetivos].
        clasico: `FayHerriotClasico` ajustado con las mismas covariables (usa `aic` y `p`).
        escenarios (list[tuple]): Salida tipo `ESCENARIOS_W`: (nombre, tipo, parámetro).
        estructuras (tuple[str, ...]): ``"muestra"`` y/o ``"completa"``.
        rho_limite (float): Cota del optimizador para |ρ|.

    Returns:
        pd.DataFrame: Una fila por (escenario, estructura) con `A_hat`, `rho_hat`, `AIC`,
            `Delta_AIC` (clásico − espacial), `LRT` y `p_LRT`.

    Example:
        >>> tabla_ajuste_espacial(covars, df, "TASA", "SE", obj, D_km, clasico, ESCENARIOS_W)  # doctest: +SKIP
    """
    n = len(df)
    ll_clasico = -(clasico.aic - 2 * (clasico.p + 1)) / 2
    filas = []
    for nombre, tipo, parametro in escenarios:
        for estructura in estructuras:
            P = proximidad_total(distancias, n, tipo, parametro, estructura)
            modelo = FayHerriotEspacial(
                covars,
                df,
                y_col,
                se_col,
                P,
                df_objetivo,
                estructura=estructura,
                rho_limite=rho_limite,
            )
            modelo.ajustar()
            lrt = max(2 * (modelo.loglik_ml - ll_clasico), 0.0)
            filas.append(
                {
                    "escenario": nombre,
                    "estructura": estructura,
                    "A_hat": modelo.A_hat,
                    "rho_hat": modelo.rho_hat,
                    "AIC": modelo.aic,
                    "Delta_AIC": clasico.aic - modelo.aic,
                    "LRT": lrt,
                    "p_LRT": float(stats.chi2.sf(lrt, 1)),
                }
            )
    return pd.DataFrame(filas)


def sensibilidad_centroide(
    covars: list,
    df: pd.DataFrame,
    y_col: str,
    se_col: str,
    df_objetivo: pd.DataFrame,
    latitud_alt: np.ndarray,
    longitud_alt: np.ndarray,
    clasico,
    escenarios: list,
    estructuras: tuple = ("muestra", "completa"),
) -> pd.DataFrame:
    """Compara ρ̂ y AIC ubicando los nodos de los dominios en la capital o en otro centroide.

    La base usa las coordenadas de `df` (`LATITUD`, `LONGITUD`: la capital del dominio); la
    alternativa reemplaza solo las de los dominios (los objetivos no cambian) por
    `latitud_alt`/`longitud_alt`, p. ej. la media de las coordenadas de los municipios miembro.
    Los dominios de un solo municipio coinciden en ambas.

    Args:
        covars (list[str]): Covariables del modelo.
        df (pd.DataFrame): Dominios con `LATITUD` y `LONGITUD` de la capital.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar directo.
        df_objetivo (pd.DataFrame): Municipios objetivo con `LATITUD` y `LONGITUD`.
        latitud_alt (np.ndarray): Latitud alternativa de cada dominio, shape (n,).
        longitud_alt (np.ndarray): Longitud alternativa de cada dominio, shape (n,).
        clasico: `FayHerriotClasico` ajustado.
        escenarios (list[tuple]): Escenarios de W.
        estructuras (tuple[str, ...]): Estructuras a ajustar.

    Returns:
        pd.DataFrame: Una fila por (escenario, estructura) con `rho_capital`, `rho_alternativo`,
            `Delta_rho`, `AIC_capital`, `AIC_alternativo` y `Delta_AIC_alt_menos_cap`, y
            `p_LRT_capital` / `p_LRT_alternativo`.

    Example:
        >>> sensibilidad_centroide(cov, df, "TASA", "SE", obj, lat_med, lon_med, clasico, ESCENARIOS_W)  # doctest: +SKIP
    """

    def distancias(lat_dom, lon_dom):
        """Distancias Haversine entre dominios y objetivos con las coordenadas dadas.

        Args:
            lat_dom (array-like): Latitud de cada dominio con encuesta, shape (n,).
            lon_dom (array-like): Longitud de cada dominio con encuesta, shape (n,).

        Returns:
            np.ndarray: Matriz de distancias en km entre las n + r unidades (dominios y objetivos),
                shape (n + r, n + r).

        Example:
            >>> distancias(lat_med, lon_med)  # doctest: +SKIP
        """
        lat = np.concatenate(
            [np.asarray(lat_dom, float), df_objetivo["LATITUD"].values]
        )
        lon = np.concatenate(
            [np.asarray(lon_dom, float), df_objetivo["LONGITUD"].values]
        )
        return distancias_haversine(lat, lon)

    clave = ["escenario", "estructura"]
    base = tabla_ajuste_espacial(
        covars,
        df,
        y_col,
        se_col,
        df_objetivo,
        distancias(df["LATITUD"].values, df["LONGITUD"].values),
        clasico,
        escenarios,
        estructuras,
    )
    alt = tabla_ajuste_espacial(
        covars,
        df,
        y_col,
        se_col,
        df_objetivo,
        distancias(latitud_alt, longitud_alt),
        clasico,
        escenarios,
        estructuras,
    )
    unido = base.merge(alt, on=clave, suffixes=("_capital", "_alternativo"))
    return pd.DataFrame(
        {
            "escenario": unido["escenario"],
            "estructura": unido["estructura"],
            "rho_capital": unido["rho_hat_capital"],
            "rho_alternativo": unido["rho_hat_alternativo"],
            "Delta_rho": unido["rho_hat_alternativo"] - unido["rho_hat_capital"],
            "AIC_capital": unido["AIC_capital"],
            "AIC_alternativo": unido["AIC_alternativo"],
            "Delta_AIC_alt_menos_cap": unido["AIC_alternativo"] - unido["AIC_capital"],
            "p_LRT_capital": unido["p_LRT_capital"],
            "p_LRT_alternativo": unido["p_LRT_alternativo"],
        }
    )


def sensibilidad_rho_objetivos(
    covars: list,
    df: pd.DataFrame,
    y_col: str,
    se_col: str,
    df_objetivo: pd.DataFrame,
    clasico,
    escenarios: list,
    conjuntos: dict,
) -> pd.DataFrame:
    """ρ̂ de la estructura completa según qué municipios objetivo entran como nodos (R-13).

    Cada conjunto es una máscara booleana sobre `df_objetivo`. Con ``"ninguno"`` la estructura
    completa se reduce a la de la muestra (el SAR solo sobre los dominios), así que la
    diferencia entre conjuntos mide cuánto de ρ̂ lo ponen los nodos sin dato y no los datos.

    Args:
        covars (list[str]): Covariables del modelo.
        df (pd.DataFrame): Dominios con `LATITUD` y `LONGITUD`.
        y_col (str): Columna de la estimación directa.
        se_col (str): Columna del error estándar directo.
        df_objetivo (pd.DataFrame): Objetivos con `LATITUD` y `LONGITUD`.
        clasico: `FayHerriotClasico` ajustado.
        escenarios (list[tuple]): Escenarios de W.
        conjuntos (dict[str, np.ndarray]): Etiqueta → máscara booleana de `df_objetivo`.

    Returns:
        pd.DataFrame: Una fila por (escenario, conjunto) con `n_objetivos`, `rho_hat`,
            `A_hat`, `AIC`, `Delta_AIC` y `p_LRT` de la estructura completa.

    Example:
        >>> sensibilidad_rho_objetivos(cov, df, "TASA", "SE", obj, clasico, ESCENARIOS_W, {"todos": np.ones(len(obj), bool)})  # doctest: +SKIP
    """
    filas = []
    for etiqueta, mascara in conjuntos.items():
        mascara = np.asarray(mascara, dtype=bool)
        sub = df_objetivo.loc[mascara].reset_index(drop=True)
        lat = np.concatenate([df["LATITUD"].values, sub["LATITUD"].values])
        lon = np.concatenate([df["LONGITUD"].values, sub["LONGITUD"].values])
        tabla = tabla_ajuste_espacial(
            covars,
            df,
            y_col,
            se_col,
            sub if len(sub) else None,
            distancias_haversine(lat, lon),
            clasico,
            escenarios,
            estructuras=("completa",),
        )
        tabla.insert(1, "conjunto_objetivos", etiqueta)
        tabla.insert(2, "n_objetivos", int(mascara.sum()))
        filas.append(tabla.drop(columns=["estructura", "LRT"]))
    return pd.concat(filas, ignore_index=True)
