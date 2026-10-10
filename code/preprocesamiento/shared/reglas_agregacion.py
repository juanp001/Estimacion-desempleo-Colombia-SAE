"""Regla de agregación de cada covariable de TerriData al dominio GEIH (ciudad o ciudad A.M.).

Por qué una regla por variable
------------------------------
En el modelo Fay-Herriot ``x_d`` contiene «los valores agregados (poblacionales) de las variables
auxiliares del área d» (Morales et al., 2021, p. 425): el valor verdadero del indicador para el
territorio del dominio. En un dominio A.M. ese territorio es la unión de sus municipios, de modo que
``x_D`` debe ser el indicador **calculado para la unión**, no un promedio cualquiera de los valores
municipales.

Casi todos los indicadores de TerriData son razones ``x_m = Y_m / Z_m`` (tasas, porcentajes, valores
per cápita). El valor de una razón en un dominio es el cociente de los totales, ``R_D = Y_D / Z_D``
(Morales et al., 2021, §2.4, p. 21). Como ``Y_m = Z_m · x_m``,

    x_D = Σ_{m∈D} Y_m / Σ_{m∈D} Z_m = Σ_{m∈D} Z_m · x_m / Σ_{m∈D} Z_m,

es decir, un promedio ponderado **por el denominador propio del indicador**: el valor agregado para
la participación sectorial del valor agregado, la superficie para la densidad, la población para un
valor per cápita. Un peso común (p. ej. la población de 15 años y más) solo coincide con esa regla
cuando es proporcional al denominador. La misma precaución aparece en la ENUSC 2018 (INE Chile, PDF
26, nota 6), que elige el denominador de cada covariable (personas de toda la comuna o solo
urbanas) para que sea coherente con la definición del indicador.

Tipos de regla
--------------
* ``exacta``: el peso es el denominador del indicador (o un total proporcional a él), así que
  ``x_D`` reproduce el indicador calculado para la unión de municipios.
* ``proxy``: TerriData no publica el denominador exacto y se usa el más cercano disponible (p. ej.
  la población de 15-19 años para la cobertura neta en media, cuyo denominador es la población de
  15-16 años).
* ``convención``: índices compuestos sin estructura aditiva (desempeño fiscal, IICA), que no tienen
  un valor «de la unión». Se usa el promedio ponderado por población: el valor que en promedio vive
  un habitante del dominio.
* ``por defecto``: indicadores fuera del catálogo de literatura. Se agregan con la población de 15
  años y más (``PET``); solo pasan por el pre-filtrado y nunca entran al modelo.

Denominadores disponibles (``tesis.terridata.terridata_extendido_plata``, 2018-12): población total
(010010009), valor agregado (120210001) y grupos quinquenales de edad por sexo (0200{1,2}0xxx). La
extensión (010010008) viene vacía en 2018, así que la superficie se obtiene como población /
densidad, que es exactamente la superficie que usó el DNP para calcular la densidad (Medellín:
387 km²). La población total coincide con las poblaciones implícitas de los demás indicadores
(valor agregado / valor agregado per cápita, jóvenes / % jóvenes, urbana + rural) con diferencias
menores al 0.5 %.

Solo cambian los 7 dominios A.M.: en un dominio de un solo municipio cualquier promedio ponderado
devuelve el valor del municipio.
"""

import pandas as pd

from preprocesamiento.shared.config import EXPR_PESO_POBLACION


def _num(codigo: str) -> str:
    """Expresión SQL que convierte una columna de TerriData (texto en plata) a número.

    Args:
        codigo (str): Código del indicador (nombre de la columna en formato ancho).

    Returns:
        str: ``try_cast(`codigo` AS DOUBLE)``; NULL si el valor no es numérico.

    Casos de uso:
        Construir las expresiones de ``PESOS_AGREGACION``.
    """
    return f"try_cast(`{codigo}` AS DOUBLE)"


# Peso → expresión SQL sobre las columnas de TerriData y descripción. Toda expresión da NULL si
# falta un componente, para que agregar_covariables_dominio detecte el municipio sin peso.
PESOS_AGREGACION = {
    "PET": {
        "expresion": EXPR_PESO_POBLACION,
        "descripcion": "Población de 15 años y más (suma de grupos quinquenales 15-19 a 80+)",
    },
    "POBLACION_TOTAL": {
        "expresion": _num("010010009"),
        "descripcion": "Población total (010010009)",
    },
    "VALOR_AGREGADO": {
        "expresion": _num("120210001"),
        "descripcion": "Valor agregado municipal (120210001)",
    },
    "SUPERFICIE": {
        "expresion": f"try_divide({_num('010010009')}, {_num('010010010')})",
        "descripcion": "Superficie implícita = población total / densidad (km²)",
    },
    "POBLACION_10_14": {
        "expresion": f"{_num('020010003')} + {_num('020020003')}",
        "descripcion": "Población de 10-14 años (hombres + mujeres)",
    },
    "POBLACION_15_19": {
        "expresion": f"{_num('020010004')} + {_num('020020004')}",
        "descripcion": "Población de 15-19 años (hombres + mujeres)",
    },
}

_PER_CAPITA = (
    "Valor per cápita: Σ numerador / Σ población = promedio ponderado por la población "
    "(Morales et al., p. 21)."
)
_PORCENTAJE_PERSONAS = (
    "Porcentaje de personas: Σ personas con el atributo / Σ población = promedio ponderado por "
    "la población (Morales et al., p. 21)."
)

# Código del catálogo de literatura → regla. Cubre las 19 entradas de CATALOGO_LITERATURA
# (analisis/shared/catalogo_literatura.py); adicion_covariables.py falla si falta alguna.
REGLAS_AGREGACION = {
    # ── Educación ─────────────────────────────────────────────────────────────
    "040010010": {
        "peso": "POBLACION_15_19",
        "tipo": "proxy",
        "sustento": (
            "Cobertura neta en media = matriculados de 15-16 años / población de 15-16 años. "
            "TerriData no publica la población de 15-16; se usa el grupo quinquenal 15-19."
        ),
    },
    "040010009": {
        "peso": "POBLACION_10_14",
        "tipo": "proxy",
        "sustento": (
            "Cobertura neta en secundaria = matriculados de 11-14 años / población de 11-14 "
            "años. Se usa el grupo quinquenal 10-14."
        ),
    },
    "040040001": {
        "peso": "POBLACION_15_19",
        "tipo": "proxy",
        "sustento": (
            "Puntaje promedio Saber 11: el denominador es el número de evaluados, que TerriData "
            "no publica; se aproxima con la población de 15-19 años."
        ),
    },
    "040040002": {
        "peso": "POBLACION_15_19",
        "tipo": "proxy",
        "sustento": (
            "Puntaje promedio Saber 11: el denominador es el número de evaluados, que TerriData "
            "no publica; se aproxima con la población de 15-19 años."
        ),
    },
    "040010028": {
        "peso": "POBLACION_15_19",
        "tipo": "proxy",
        "sustento": (
            "Tránsito inmediato = bachilleres que ingresan a educación superior / bachilleres "
            "graduados. Los graduados no se publican; se aproximan con la población de 15-19."
        ),
    },
    # ── Economía ──────────────────────────────────────────────────────────────
    "120210002": {
        "peso": "POBLACION_TOTAL",
        "tipo": "exacta",
        "sustento": _PER_CAPITA
        + " La población implícita (valor agregado / per cápita) coincide con 010010009.",
    },
    "120210008": {
        "peso": "VALOR_AGREGADO",
        "tipo": "exacta",
        "sustento": (
            "Participación sectorial: Σ VA del sector / Σ VA total = promedio ponderado por "
            "el valor agregado (Morales et al., p. 21)."
        ),
    },
    "120210009": {
        "peso": "VALOR_AGREGADO",
        "tipo": "exacta",
        "sustento": (
            "Participación sectorial: Σ VA del sector / Σ VA total = promedio ponderado por "
            "el valor agregado (Morales et al., p. 21)."
        ),
    },
    "120210010": {
        "peso": "VALOR_AGREGADO",
        "tipo": "exacta",
        "sustento": (
            "Participación sectorial: Σ VA del sector / Σ VA total = promedio ponderado por "
            "el valor agregado (Morales et al., p. 21)."
        ),
    },
    # ── Pobreza ───────────────────────────────────────────────────────────────
    "140010004": {
        "peso": "POBLACION_TOTAL",
        "tipo": "exacta",
        "sustento": _PORCENTAJE_PERSONAS
        + " IPM: porcentaje de personas pobres (CNPV 2018).",
    },
    # ── Demografía ────────────────────────────────────────────────────────────
    "020040003": {
        "peso": "POBLACION_TOTAL",
        "tipo": "exacta",
        "sustento": _PORCENTAJE_PERSONAS
        + " Equivale a Σ población urbana / Σ población total.",
    },
    "010010010": {
        "peso": "SUPERFICIE",
        "tipo": "exacta",
        "sustento": (
            "Densidad = población / superficie: Σ población / Σ superficie = promedio ponderado "
            "por la superficie (Morales et al., p. 21)."
        ),
    },
    "020090021": {
        "peso": "POBLACION_TOTAL",
        "tipo": "exacta",
        "sustento": _PORCENTAJE_PERSONAS
        + " Equivale a Σ jóvenes de 14-28 / Σ población total.",
    },
    # ── Fiscal ────────────────────────────────────────────────────────────────
    "070100007": {
        "peso": "POBLACION_TOTAL",
        "tipo": "convención",
        "sustento": (
            "Índice compuesto de las finanzas de cada alcaldía; el A.M. no es una entidad "
            "fiscal y el índice no tiene un valor de la unión. Promedio ponderado por población."
        ),
    },
    "070010020": {
        "peso": "POBLACION_TOTAL",
        "tipo": "exacta",
        "sustento": _PER_CAPITA,
    },
    # ── Conflicto y seguridad ─────────────────────────────────────────────────
    "260020003": {
        "peso": "POBLACION_TOTAL",
        "tipo": "convención",
        "sustento": (
            "Índice compuesto (DNP) sin estructura aditiva; no tiene un valor de la unión. "
            "Promedio ponderado por población."
        ),
    },
    "060010003": {
        "peso": "POBLACION_TOTAL",
        "tipo": "exacta",
        "sustento": (
            "Tasa por 100.000 habitantes: Σ homicidios / Σ población = promedio ponderado por "
            "la población (Morales et al., p. 21)."
        ),
    },
    # ── Infraestructura ───────────────────────────────────────────────────────
    "030010004": {
        "peso": "POBLACION_TOTAL",
        "tipo": "proxy",
        "sustento": (
            "Cobertura de acueducto del CNPV 2018; el denominador son viviendas o hogares, que "
            "TerriData no publica para 2018. Se aproxima con la población total."
        ),
    },
    "030010003": {
        "peso": "POBLACION_TOTAL",
        "tipo": "exacta",
        "sustento": (
            "Penetración de banda ancha = accesos fijos por cada 100 habitantes (MinTIC): "
            "promedio ponderado por la población (Morales et al., p. 21)."
        ),
    },
}

REGLA_POR_DEFECTO = {
    "peso": "PET",
    "tipo": "por defecto",
    "sustento": (
        "Indicador fuera del catálogo de literatura: solo pasa por el pre-filtrado y no entra "
        "al modelo. Promedio ponderado por la población de 15 años y más."
    ),
}


def regla_de(codigo: str) -> dict:
    """Regla de agregación de un indicador.

    Args:
        codigo (str): Código del indicador de TerriData.

    Returns:
        dict: ``{"peso", "tipo", "sustento"}``; ``REGLA_POR_DEFECTO`` si el código no tiene regla.

    Casos de uso:
        Armar el mapa columna → peso que recibe ``agregar_covariables_dominio``.

    Example:
        >>> regla_de("120210008")["peso"]
        'VALOR_AGREGADO'
        >>> regla_de("999999999")["tipo"]
        'por defecto'
    """
    return REGLAS_AGREGACION.get(codigo, REGLA_POR_DEFECTO)


def tabla_reglas(codigos: list, indicadores_dict: dict) -> pd.DataFrame:
    """Tabla de trazabilidad de la regla de agregación de cada indicador.

    Args:
        codigos (list[str]): Códigos de indicador a documentar (p. ej. los del catálogo).
        indicadores_dict (dict): Mapa código → nombre del indicador (``tesis.dim.dim_indicadores``).

    Returns:
        pd.DataFrame: Una fila por código con ``CODIGO_INDICADOR``, ``INDICADOR``, ``PESO``,
            ``DESCRIPCION_PESO``, ``EXPRESION_PESO``, ``TIPO`` y ``SUSTENTO``.

    Casos de uso:
        Persistir en ``tesis.preprocesamiento.reglas_agregacion_covariables`` la regla con la que
        se construyó ``x_D`` en cada dominio A.M. (auditoría pedida en G7-B1).

    Example:
        >>> tabla_reglas(["010010010"], {"010010010": "Densidad poblacional"})["PESO"].tolist()
        ['SUPERFICIE']
    """
    filas = []
    for codigo in codigos:
        regla = regla_de(codigo)
        peso = PESOS_AGREGACION[regla["peso"]]
        filas.append(
            {
                "CODIGO_INDICADOR": codigo,
                "INDICADOR": indicadores_dict.get(codigo, ""),
                "PESO": regla["peso"],
                "DESCRIPCION_PESO": peso["descripcion"],
                "EXPRESION_PESO": peso["expresion"],
                "TIPO": regla["tipo"],
                "SUSTENTO": regla["sustento"],
            }
        )
    return pd.DataFrame(filas)
