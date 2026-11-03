"""Construye chapters/appendice.tex a partir de las tablas descargadas (solo lectura) y del código.

Uso: python -I construir_apendice.py <carpeta del documento>

Lee `_trabajo/calculos/datos/*.csv` (consultas SELECT de `descargar_tablas.py`) y
`_trabajo/calculos/salidas/` (cálculo propio C1 y filas generadas). Conserva la sección
«Material complementario de Resultados» (`app:resultados`) del apéndice actual. No recalcula cifras:
solo da formato. Los coeficientes de EC0-EC2, que el procesamiento no persiste, se transcriben de la
salida del notebook `modelo/fay_herriot.py`, celda 8 (corrida del 2026-10-31).
"""

import sys
from pathlib import Path

import pandas as pd

DOC = Path(sys.argv[1])
DAT = DOC / "_trabajo" / "calculos" / "datos"
SAL = DOC / "_trabajo" / "calculos" / "salidas"
BS = "\\"
SEP = "%" + "-" * 86 + "\n"


def esc(t):
    """Escapa caracteres especiales de LaTeX en un texto.

    Args:
        t (object): texto o valor.

    Returns:
        str: texto seguro para LaTeX.
    """
    t = "" if pd.isna(t) else str(t)
    for a, b in [("\\", "/"), ("&", BS + "&"), ("%", BS + "%"), ("_", BS + "_"), ("#", BS + "#"), ("$", BS + "$")]:
        t = t.replace(a, b)
    return t


def f(x, d=2):
    """Formatea un número con d decimales (sin «-0.00»).

    Args:
        x (float): valor.
        d (int): decimales.

    Returns:
        str: número formateado o «no aplica».
    """
    if pd.isna(x):
        return "no aplica"
    s = f"{float(x):.{d}f}"
    return s.replace("-0." + "0" * d, "0." + "0" * d) if d else s


def sig(x, d=3):
    """Formatea con signo matemático para valores negativos.

    Args:
        x (float): valor.
        d (int): decimales.

    Returns:
        str: número, en modo matemático si es negativo.
    """
    s = f(x, d)
    return f"${s}$" if s.startswith("-") else s


def longtable(cols, encabezado, caption, label, filas, tamano="footnotesize"):
    """Arma un longtable con booktabs.

    Args:
        cols (str): especificación de columnas.
        encabezado (str): fila de encabezado.
        caption (str): título.
        label (str): etiqueta.
        filas (list[str]): filas ya terminadas en «\\\\».
        tamano (str): tamaño de letra.

    Returns:
        str: código LaTeX.
    """
    n = encabezado.count("&") + 1
    return (
        f"{{{BS}{tamano}\n{BS}begin{{longtable}}{{{cols}}}\n{BS}caption{{{caption}}}\n{BS}label{{{label}}} {BS}{BS}\n"
        f"{BS}toprule\n{encabezado} {BS}{BS}\n{BS}midrule\n{BS}endfirsthead\n"
        f"{BS}multicolumn{{{n}}}{{l}}{{{BS}tablename~{BS}thetable{{}}, continuación}} {BS}{BS}\n{BS}toprule\n{encabezado} {BS}{BS}\n{BS}midrule\n{BS}endhead\n"
        f"{BS}bottomrule\n{BS}endlastfoot\n" + "\n".join(filas) + f"\n{BS}end{{longtable}}\n}}\n"
    )


def tabla(cols, encabezado, caption, label, filas, tamano="small"):
    """Arma un flotante table con booktabs.

    Args:
        cols (str): columnas.
        encabezado (str): encabezado.
        caption (str): título.
        label (str): etiqueta.
        filas (list[str]): filas.
        tamano (str): tamaño de letra.

    Returns:
        str: código LaTeX.
    """
    return (
        f"{BS}begin{{table}}[!htbp]\n{BS}centering\n{BS}{tamano}\n{BS}caption{{{caption}}}\n{BS}label{{{label}}}\n"
        f"{BS}begin{{tabular}}{{{cols}}}\n{BS}toprule\n{encabezado} {BS}{BS}\n{BS}midrule\n" + "\n".join(filas)
        + f"\n{BS}bottomrule\n{BS}end{{tabular}}\n{BS}end{{table}}\n"
    )


def figura(archivo, ancho, caption, label):
    """Arma un flotante figure.

    Args:
        archivo (str): ruta en img/.
        ancho (str): ancho relativo a linewidth.
        caption (str): título.
        label (str): etiqueta.

    Returns:
        str: código LaTeX.
    """
    return (
        f"{BS}begin{{figure}}[!htbp]\n{BS}centering\n{BS}includegraphics[width={ancho}{BS}linewidth]{{{archivo}}}\n"
        f"{BS}caption{{{caption}}}\n{BS}label{{{label}}}\n{BS}end{{figure}}\n"
    )


def seccion(titulo, label, apertura):
    """Encabezado de sección del apéndice con su frase de apertura.

    Args:
        titulo (str): título.
        label (str): etiqueta app:.
        apertura (str): frase que dice qué contiene y desde dónde se cita.

    Returns:
        str: código LaTeX.
    """
    return f"{SEP}{BS}section{{{titulo}}}\n{BS}label{{{label}}}\n\n{apertura}\n\n"


NOMBRES = {
    "COB_NET_MEDIA": "Cobertura neta en educación media",
    "COB_NET_SEC": "Cobertura neta en educación secundaria",
    "SABER11_MAT": "Saber 11, matemáticas",
    "SABER11_LEC": "Saber 11, lectura crítica",
    "TASA_TRAN_EDU_SUP": "Tránsito a la educación superior",
    "VA_PC": "Valor agregado per cápita",
    "VA_PCT_PRIM": "Valor agregado de actividades primarias",
    "VA_PCT_SEC": "Valor agregado de actividades secundarias",
    "VA_PCT_TERC": "Valor agregado de actividades terciarias",
    "IND_POB_MULT": "Índice de pobreza multidimensional",
    "PCT_URBANA": "Población urbana",
    "DENS_POB": "Densidad de población",
    "PCT_JOVENES": "Población joven de 14 a 28 años",
    "IDF": "Índice de desempeño fiscal",
    "ING_TRIB_PC": "Ingresos tributarios per cápita",
    "TASA_HOMICIDIOS": "Tasa de homicidios",
    "COB_ACUEDUCTO": "Cobertura de acueducto",
    "BANDA_ANCHA": "Penetración de banda ancha",
}
ESCENARIOS = {"knn3": "3 vecinos", "knn5": "5 vecinos", "inversa1": "Inversa, potencia 1", "inversa2": "Inversa, potencia 2"}


def s_reproducibilidad():
    """Sección de disponibilidad de datos, código y reproducción."""
    t = seccion(
        "Disponibilidad de datos y código, y reproducción",
        "app:reproducibilidad",
        "Esta sección indica dónde están los datos y el código y cómo se repite el procesamiento; la cita la Sección~"
        + BS + "ref{sec:metodologia}.",
    )
    t += (
        "Las cuatro fuentes son públicas: los microdatos de la GEIH y el anexo de mercado laboral se descargan del "
        "archivo nacional de datos del DANE, TerriData del portal del DNP y la DIVIPOLA del geoportal del DANE "
        "(Tabla~" + BS + "ref{tab:fuentes_datos}). El código está en el repositorio "
        + BS + "url{https://github.com/juanp001/Estimacion-desempleo-Colombia-SAE}. Todo corre en Databricks con tablas "
        "de Unity Catalog en el catálogo " + BS + "texttt{tesis} y se despliega como un conjunto de trabajos programados "
        "(Tabla~" + BS + "ref{tab:app_jobs}). Con el entorno configurado, el procesamiento completo se repite con el trabajo "
        + BS + "texttt{pipeline" + BS + "_completo}, que recibe el año y el mes de cierre y el número de meses de la ventana.\n\n"
    )
    filas = [
        "dimensiones & Tabla de la DIVIPOLA; dominios de la GEIH y sus municipios; capitales con coordenadas & 4 " + BS + BS,
        "ingesta" + BS + "_geih & Capas bronce, plata y oro de la GEIH; cifras publicadas por el DANE & 1, 2 " + BS + BS,
        "ingesta" + BS + "_terridata & Capas bronce y plata de TerriData; diccionario de indicadores & 1, 2 " + BS + BS,
        "preprocesamiento & Estimación directa; covariables por dominio y auditoría; pre-filtrado; municipios objetivo & 5 a 7 " + BS + BS,
        "analisis & Análisis descriptivo; selección de covariables & 8, 9 " + BS + BS,
        "modelo & Fay-Herriot clásico; Fay-Herriot espacial; sensibilidad a la varianza & 10 a 16 " + BS + BS,
        "pipeline" + BS + "_completo & Ejecuta los seis trabajos anteriores en orden & 1 a 16 " + BS + BS,
    ]
    t += tabla(
        "l p{8.6cm} l",
        "Trabajo & Tareas & Etapas",
        "Trabajos programados del procesamiento y etapas de la metodología que cubren. La sensibilidad a la ventana "
        "temporal (etapa 5) se ejecuta aparte.",
        "tab:app_jobs",
        filas,
    )
    return t


LINAJE = [
    ("geih" + BS + "_bronce", "Un archivo por módulo y sección (cabecera y resto del marco antiguo; un archivo por módulo en el marco nuevo) y el factor de expansión recalculado", "geih" + BS + "_bronce", "1"),
    ("geih" + BS + "_bronce", "Cifras publicadas: nacionales, por ciudad (trimestre móvil) y anuales", "datos" + BS + "_publicados", "1"),
    ("geih" + BS + "_plata", "Un módulo consolidado por tabla (características generales, fuerza de trabajo, ocupados, no ocupados) y factores de expansión", "geih" + BS + "_plata", "2"),
    ("geih" + BS + "_oro", "Mercado laboral (una fila por persona); llaves sin pareja; reconciliación de la fuerza de trabajo", "geih" + BS + "_oro", "2"),
    ("terridata", "Indicadores en formato largo (bronce) y ancho (plata)", "terridata" + BS + "_bronce, terridata" + BS + "_plata", "1, 2"),
    ("dim", "DIVIPOLA; dominios de la GEIH; capitales con coordenadas; diccionario de indicadores", "dim" + BS + "_divipola, dim" + BS + "_dominio" + BS + "_geih, dim" + BS + "_geih" + BS + "_divipola, terridata" + BS + "_plata", "1, 4"),
    ("preprocesamiento", "Tasa directa por dominio; sensibilidad de la ventana", "estimacion" + BS + "_directa, sensibilidad" + BS + "_ventana" + BS + "_temporal", "5"),
    ("preprocesamiento", "Tasa con covariables; reglas de agregación; auditoría de dominios", "adicion" + BS + "_covariables", "4, 6"),
    ("preprocesamiento", "Covariables pre-filtradas; cascada; sensibilidad de la variabilidad; municipios objetivo", "pre" + BS + "_filtrado" + BS + "_covariables, dominios" + BS + "_sin" + BS + "_encuesta", "6, 7"),
    ("preprocesamiento", "Catálogo; descriptivo univariado y bivariado", "analisis" + BS + "_descriptivo", "8"),
    ("preprocesamiento", "Diagnósticos, soporte, redundancia, decisión, verificación, trazabilidad y conjunto seleccionado", "eda" + BS + "_seleccion" + BS + "_covariables", "9"),
    ("modelo", "Especificaciones, coeficientes, Cook, estabilidad, validación, extrapolación, EBLUP, estimación sintética y tabla final", "fay" + BS + "_herriot", "10 a 12, 14, 15"),
    ("modelo", "Comparación espacial, Moran, perfil de $" + BS + "rho$, validación, coeficientes, sensibilidades y estimación de los municipios", "fay" + BS + "_herriot" + BS + "_espacial", "13, 14, 16"),
    ("modelo", "Varianzas alternativas, GVF y escenarios", "sensibilidad" + BS + "_varianza", "11"),
]


def s_linaje():
    """Sección de linaje de tablas, con la lista completa por esquema."""
    t = seccion(
        "Linaje de tablas",
        "app:linaje",
        "Esta sección relaciona cada tabla del procesamiento con el cuaderno que la escribe y la etapa de la metodología; "
        "la citan las Secciones~" + BS + "ref{sec:metodologia} y~" + BS + "ref{sec:resultados}.",
    )
    filas = [f"{BS}texttt{{{e}}} & {c} & {BS}texttt{{{n}}} & {et} {BS}{BS}" for e, c, n, et in LINAJE]
    t += longtable(
        "p{2.4cm} p{6.0cm} p{4.2cm} p{1.4cm}",
        "Esquema & Contenido & Cuaderno & Etapa",
        "Linaje de las tablas del catálogo de Unity Catalog del trabajo, de la ingesta a la tabla final.",
        "tab:app_linaje",
        filas,
    )
    cat = pd.read_csv(DAT / "tablas_catalogo.csv")
    vigentes = cat[~cat.table_schema.isin(["censo_nal"]) & ~cat.table_name.str.contains("_area_marco_antiguo")]
    vigentes = vigentes[~vigentes.table_name.isin(["covariables_candidatas", "robustez_covariables", "dim_tiempo"])]
    t += (
        "El catálogo tiene " + str(len(vigentes)) + " tablas escritas por el código vigente, repartidas así: "
        + "; ".join(f"{esc(s)}, {n}" for s, n in vigentes.groupby("table_schema").size().items())
        + ". Quedan además en el catálogo tablas de versiones anteriores que ningún cuaderno vigente lee ni escribe: "
        "las del censo, las de la sección de área del marco antiguo, una lista de candidatas y una tabla de robustez de "
        "covariables, y una dimensión de tiempo.\n\n"
    )
    return t


VARIABLES = [
    ("Tasa de desempleo directa", "TASA" + BS + "_DESEMPLEO" + BS + "_PCT", "Estimador de Hájek de la tasa de desempleo del dominio, en \\%"),
    ("Error estándar bootstrap", "SE" + BS + "_BOOTSTRAP" + BS + "_PCT", "Desviación de 2,000 réplicas por viviendas, en puntos porcentuales; $" + BS + "psi_d$ es su cuadrado"),
    ("Error estándar de Taylor", "SE" + BS + "_TAYLOR" + BS + "_PCT", "Linealización de la razón con las mismas viviendas"),
    ("Factor de expansión", "FEX" + BS + "_C18", "Peso de la persona calibrado con el CNPV 2018"),
    ("Vivienda", "ID" + BS + "_VIVIENDA", "Período más directorio; conglomerado del bootstrap"),
    ("Código de área", "AREA", "Departamento de la ciudad del dominio en la GEIH"),
    ("Dominio", "CODIGO" + BS + "_DOMINIO", "DIVIPOLA de la capital del dominio"),
    ("PEA expandida", "PEA" + BS + "_EXPANDIDA", "Suma de factores de la PEA dividida por los meses; peso del benchmarking de nivel 1"),
    ("Peso de la directa", "GAMMA" + BS + "_SHRINKAGE", "$" + BS + "hat{" + BS + "gamma}_d$ del EBLUP"),
    ("EBLUP y su ECM", "EBLUP, MSE" + BS + "_EBLUP", "Estimación del Fay-Herriot clásico y su ECM de Prasad-Rao"),
    ("Estimación sintética", "PRED" + BS + "_SINTETICO", "$" + BS + "mathbf{x}^" + BS + "top" + BS + "hat{" + BS + "boldsymbol{" + BS + "beta}}$ en un municipio objetivo"),
    ("Estimación espacial", "PRED" + BS + "_ESPACIAL", "Predictor espacial del escenario de referencia"),
    ("Estado de extrapolación", "ESTADO" + BS + "_EXTRAPOLACION", "Dentro del rango, fuera del rango o combinación atípica"),
    ("Calidad reportada", "CALIDAD" + BS + "_REPORTADA", "Clase de CV más «condicional al modelo» y «extrapolado» si corresponde"),
]


def s_variables():
    """Sección de nombres de variables: nombre en el documento, código y descripción."""
    t = seccion(
        "Nombres de las variables",
        "app:variables",
        "Esta sección relaciona el nombre que usa el texto con el código de TerriData o la columna del procesamiento; "
        "la citan las Secciones~" + BS + "ref{sec:datos} y~" + BS + "ref{sec:resultados}.",
    )
    reg = pd.read_csv(DAT / "reglas_agregacion.csv", dtype={"CODIGO_INDICADOR": str})
    filas = [
        f"{NOMBRES[r.ALIAS]} & {r.CODIGO_INDICADOR} & {esc(r.INDICADOR)}; {esc(r.UNIDAD_MEDIDA)} {BS}{BS}"
        for r in reg.sort_values("ALIAS").itertuples()
    ]
    filas.append(BS + "midrule")
    filas += [f"{a} & {BS}texttt{{{b}}} & {c} {BS}{BS}" for a, b, c in VARIABLES]
    t += longtable(
        "p{4.0cm} p{3.6cm} p{6.6cm}",
        "Nombre en el documento & Código o columna & Descripción",
        "Nombres de las variables. Arriba, las 18 covariables candidatas con su código de TerriData; abajo, las columnas "
        "del procesamiento que el texto nombra en lenguaje natural.",
        "tab:app_variables",
        filas,
    )
    return t


def s_catalogo():
    """Sección del catálogo de literatura (18 activas y 6 excluidas)."""
    t = seccion(
        "Catálogo de covariables",
        "app:catalogo",
        "Esta sección lista las entradas del catálogo de literatura con su código, el signo esperado y la referencia que "
        "las respalda; la citan las Secciones~" + BS + "ref{sec:datos}, " + BS + "ref{sec:met_covariables} y~" + BS + "ref{sec:res_covariables}.",
    )
    cat = pd.read_csv(DAT / "catalogo_literatura.csv", dtype={"Codigo": str})
    act = cat[cat.Estado == "activa"]
    filas = [
        f"{NOMBRES.get(r.Alias, esc(r.Nombre))} & {r.Codigo} & {esc(r.Dimension)} & ${r.Signo_esperado.replace('±', BS + 'pm')}$ & {esc(r.Referencia)} {BS}{BS}"
        for r in act.itertuples()
    ]
    filas.append(BS + "midrule")
    filas.append(f"{BS}multicolumn{{5}}{{l}}{{Entradas sin dato utilizable o retiradas}} {BS}{BS}")
    motivos = {
        "040030003": "Sin dato en los dominios con encuesta para 2018",
        "160080001": "La serie termina en 2016",
        "140060001": "Solo departamentos y 23 ciudades; no existe en los municipios objetivo",
        "140010003": "Solo departamental",
        "260030002": "Solo 2022 y 2023",
        "260020003": "Retirado: mide el conflicto en el propio municipio y no la llegada de población desplazada; "
        "$r = 0.92$ con la tasa de homicidios en los dominios; 13 valores distintos",
    }
    filas += [
        f"{esc(r.Nombre)} & {r.Codigo} & {esc(r.Dimension)} & no aplica & {motivos.get(r.Codigo, esc(r.Estado))} {BS}{BS}"
        for r in cat[cat.Estado != "activa"].itertuples()
    ]
    t += longtable(
        "p{3.0cm} p{1.5cm} p{2.2cm} p{0.8cm} p{6.0cm}",
        "Covariable & Código & Dimensión & Signo & Referencia o motivo",
        "Catálogo de literatura: 18 entradas activas y 6 sin dato utilizable o retiradas. Signo: relación esperada con la "
        "tasa de desempleo ($" + BS + "pm$: sin signo definido).",
        "tab:app_catalogo",
        filas,
    )
    return t


def s_auditoria():
    """Sección de la auditoría de dominios (23 filas)."""
    t = seccion(
        "Auditoría de los dominios",
        "app:auditoria",
        "Esta sección detalla, por dominio, la correspondencia entre la geografía de la GEIH y la de las covariables; "
        "la cita la Sección~" + BS + "ref{sec:res_dominios}.",
    )
    a = pd.read_csv(DAT / "auditoria_dominios.csv", dtype={"CODIGO_DOMINIO": str, "CODIGO_AREA_GEIH": str})
    filas = []
    for r in a.sort_values("NOMBRE_DOMINIO").itertuples():
        regla = "Valor municipal" if r.N_MUNICIPIOS == 1 else "Razón de totales"
        filas.append(
            f"{esc(r.NOMBRE_DOMINIO)} & {r.CODIGO_AREA_GEIH} & {r.CODIGO_DOMINIO} & {esc(r.MUNICIPIOS_INTEGRANTES)} & {regla} & {f(r.TASA_DESEMPLEO_PCT)} & {f(r.TD_DANE_PCT)} {BS}{BS}"
        )
    t += longtable(
        "p{2.4cm} p{0.8cm} p{1.1cm} p{4.6cm} p{1.9cm} r r",
        "Dominio & Área & DIVIPOLA & Municipios & Covariables & TD & TD DANE",
        "Auditoría de los 23 dominios, Ene-Dic 2018. Área: código de área de la GEIH; DIVIPOLA: código de la capital; "
        "Covariables: valor municipal o razón de totales con el denominador propio (Ecuación~" + BS + "ref{eq:agregacion}); "
        "TD en \\%. La tasa describe las cabeceras y las covariables el municipio completo.",
        "tab:app_auditoria",
        filas,
    )
    return t


def s_descriptivo():
    """Sección de descriptivos de las candidatas y figuras."""
    t = seccion(
        "Análisis descriptivo de las candidatas",
        "app:descriptivo",
        "Esta sección reúne la estadística univariada de las 18 candidatas y las figuras del análisis descriptivo; la cita "
        "la Sección~" + BS + "ref{sec:res_descriptivo}.",
    )
    u = pd.read_csv(DAT / "descriptivo_univariado.csv")
    u = u[u.Alias.isin(NOMBRES.keys())]
    filas = [
        f"{NOMBRES[r.Alias]} & {f(r.Media)} & {f(r.Mediana)} & {f(r.Desv_Std)} & {f(r.Minimo)} & {f(r.Maximo)} & {f(r.CV_pct)} & {sig(r.Asimetria, 2)} & {int(r.N_extremos_IQR)} {BS}{BS}"
        for r in u.itertuples()
    ]
    t += longtable(
        "p{4.2cm} r r r r r r r r",
        "Covariable & Media & Mediana & DE & Mín. & Máx. & CV & Asim. & Ext.",
        "Estadística univariada de las candidatas en los 23 dominios. DE: desviación estándar; CV en \\%; Asim.: "
        "asimetría; Ext.: valores señalados por la regla del diagrama de caja (Ecuación~" + BS + "ref{eq:iqr}).",
        "tab:app_univariado",
        filas,
    )
    for arch, cap, lab in [
        ("desc_territorial_respuesta", "Tasa directa de los 23 dominios ordenada de mayor a menor, con su intervalo del 95~" + BS + "%.", "fig:app_territorial"),
        ("desc_boxplots_candidatas", "Diagramas de caja de las 18 candidatas en escala estandarizada.", "fig:app_boxplots"),
        ("desc_dispersion_candidatas", "Tasa directa frente a cada candidata en los 23 dominios.", "fig:app_dispersion"),
        ("desc_correlacion_candidatas", "Matriz de correlaciones de las candidatas, reordenada por agrupamiento.", "fig:app_correlacion"),
    ]:
        t += figura(f"img/{arch}.png", "0.9", cap + " Fuente: tablas del análisis descriptivo.", lab)
    return t


def s_seleccion():
    """Sección del detalle de la selección de covariables."""
    t = seccion(
        "Detalle de la selección de covariables",
        "app:seleccion",
        "Esta sección presenta el Fay-Herriot univariado de cada candidata y los diagnósticos del conjunto elegido; la cita "
        "la Sección~" + BS + "ref{sec:res_seleccion}.",
    )
    d = pd.read_csv(DAT / "diagnosticos_covariables.csv")
    d = d.reindex(d.r_ponderada.abs().sort_values(ascending=False).index)
    filas = [
        f"{NOMBRES[r.Alias]} & {sig(r.Beta_FH, 4)} & [{sig(r.IC_FH_inf, 4)}, {sig(r.IC_FH_sup, 4)}] & {f(r.p_FH, 3)} & {f(r.q_FH, 3)} & {f(r.Cook_max, 3)} & {esc(r.Dominio_critico)} & {f(r.Delta_max_abs, 3)} {BS}{BS}"
        for r in d.itertuples()
    ]
    t += longtable(
        "p{3.6cm} r p{2.6cm} r r r p{1.8cm} r",
        "Covariable & $" + BS + "hat{" + BS + "beta}_1$ & IC 95~" + BS + "% & $p$ & $q$ & Cook & Dominio & $" + BS + "Delta r_w$",
        "Fay-Herriot univariado de cada candidata (REML y GLS). IC: intervalo de Wald; $q$: Benjamini-Hochberg; Cook: "
        "distancia máxima; Dominio: el que más cambia $r_w$ al retirarlo; $" + BS + "Delta r_w$: ese cambio. Los coeficientes "
        "están en la unidad de cada covariable.",
        "tab:app_seleccion",
        filas,
    )
    t += figura("img/eda_correlacion_finales.png", "0.6", "Correlación entre las covariables seleccionadas (tasa de homicidios y cobertura de acueducto). Fuente: tabla de verificación de la selección.", "fig:app_correlacion_finales")
    t += figura("img/eda_residuos_parciales.png", "0.9", "Residuos parciales de las covariables seleccionadas en el Fay-Herriot con ambas. Fuente: tabla de verificación de la selección.", "fig:app_residuos_parciales")
    return t


EC = [
    ("EC1", "Intercepto", 13.7584, 4.9973, 0.0059),
    ("EC1", "Tasa de homicidios", 0.0663, 0.0505, 0.1898),
    ("EC1", "Cobertura de acueducto", -0.0419, 0.045, 0.3512),
    ("EC2", "Intercepto", 19.0532, 2.9938, 0.0),
    ("EC2", "Cobertura de acueducto", -0.0833, 0.0326, 0.0107),
    ("EC3", "Intercepto", 9.1908, 0.979, 0.0),
    ("EC3", "Tasa de homicidios", 0.0993, 0.0359, 0.0058),
    ("EC0", "Intercepto", 11.527, 0.5634, 0.0),
]


def s_especificaciones():
    """Sección del detalle de las cuatro especificaciones del clásico."""
    t = seccion(
        "Especificaciones del Fay-Herriot clásico",
        "app:especificaciones",
        "Esta sección presenta los coeficientes y los diagnósticos de las cuatro especificaciones candidatas; la citan las "
        "Secciones~" + BS + "ref{sec:res_fh_clasico} y~" + BS + "ref{sec:res_supuestos}.",
    )
    filas = [f"{m} & {p} & {sig(b)} & {f(e, 3)} & {'$<0.001$' if pv < 0.001 else f(pv, 3)} {BS}{BS}" for m, p, b, e, pv in EC]
    t += tabla("l l r r r", "Especificación & Parámetro & $" + BS + "hat{" + BS + "beta}$ & EE & $p$",
               "Coeficientes de las cuatro especificaciones candidatas. Fuente: salida del cuaderno del Fay-Herriot clásico.",
               "tab:app_ec_coeficientes", filas)
    d = pd.read_csv(DAT / "fh_diagnosticos_variantes.csv")
    filas = [
        f"{r.Modelo} & {f(r.R2, 3)} & {f(r.SD_resid, 3)} & {f(r.SW_pval, 3)} & {f(r.Gamma_prom, 3)} & {f(r.Ratio_MSE_medio, 3)} & {f(r.Cook_max, 3)} & {int(r.N_influyentes)} {BS}{BS}"
        for r in d.itertuples()
    ]
    t += tabla("l r r r r r r r", "Especificación & $R^2$ & DE resid. & $p$ SW & $" + BS + "bar{" + BS + "gamma}$ & $" + BS + "psi/" + "{" + BS + "rm ECM}$ & Cook & Influyentes",
               "Diagnósticos de las especificaciones. DE resid.: desviación de los residuos estandarizados; SW: Shapiro-Wilk; "
               "$" + BS + "psi/{" + BS + "rm ECM}$: razón media entre la varianza directa y el ECM del EBLUP; Influyentes: dominios con Cook $> 4/n$.",
               "tab:app_ec_diagnosticos", filas)
    for ec, nombre in [("ec3", "EC3 (benchmark)"), ("ec1", "EC1"), ("ec2", "EC2"), ("ec0", "EC0")]:
        t += (
            f"{BS}begin{{figure}}[!htbp]\n{BS}centering\n{BS}includegraphics[width=0.48{BS}linewidth]{{img/fh_{ec}_suavizador.png}}\n{BS}hfill\n"
            f"{BS}includegraphics[width=0.48{BS}linewidth]{{img/fh_{ec}_histograma.png}}\n"
            f"{BS}caption{{Especificación {nombre}: a la izquierda, residuo del EBLUP frente a la tasa directa (contracción); a la derecha, "
            f"histograma de los residuos estandarizados. Fuente: cuaderno del Fay-Herriot clásico.}}\n{BS}label{{fig:app_{ec}}}\n{BS}end{{figure}}\n"
        )
    t += figura("img/fh_ganador_cook.png", "0.85", "Distancia de Cook de cada dominio en el benchmark; la línea marca $4/n$. Fuente: tabla de Cook del Fay-Herriot clásico.", "fig:app_cook")
    t += BS + "FloatBarrier\n\n"
    return t


def s_dominios_modelo():
    """Sección con los 23 dominios: directa, EBLUP, SEBLUP y benchmarking."""
    t = seccion(
        "Estimaciones de los dominios",
        "app:dominios_modelo",
        "Esta sección presenta, para los 23 dominios, la tasa directa, el EBLUP del benchmark, el SEBLUP del escenario "
        "espacial de referencia y el EBLUP ajustado por benchmarking; la citan las Secciones~" + BS + "ref{sec:res_fh_clasico} y~"
        + BS + "ref{sec:res_espacial}.",
    )
    filas = (SAL / "filas_dominios_modelo.tex").read_text(encoding="utf-8").replace("-0.00", "0.00").splitlines()
    t += longtable(
        "l r r r r r r r r",
        "Dominio & Directa & EBLUP & CV & $" + BS + "hat{" + BS + "gamma}_d$ & SEBLUP & CV & $" + BS + "hat{" + BS + "gamma}^S_d$ & Ajustada",
        "Estimaciones de los 23 dominios, Ene-Dic 2018, en \\%. CV en \\%. EBLUP: benchmark EC3; SEBLUP: 3 vecinos, estructura "
        "completa, con ECM por bootstrap (cálculo propio sobre las tablas del modelo); Ajustada: EBLUP tras el benchmarking de nivel 1.",
        "tab:app_dominios_modelo",
        filas,
    )
    return t


def s_varianza():
    """Sección de varianzas alternativas y GVF."""
    t = seccion(
        "Varianza de muestreo",
        "app:varianza",
        "Esta sección presenta las varianzas alternativas de cada dominio y las figuras de la GVF y de los escenarios; la cita "
        "la Sección~" + BS + "ref{sec:res_supuestos}.",
    )
    v = pd.read_csv(DAT / "sensibilidad_varianza_directa.csv").sort_values("NOMBRE_DOMINIO")
    filas = [
        f"{esc(r.NOMBRE_DOMINIO)} & {f(r.PSI_VIVIENDAS, 3)} & {f(r.EFECTO_VIVIENDA, 3)} & {f(r.RAZON_BOOT_TAYLOR, 3)} & {f(r.RAZON_GVF_A, 3)} & {f(r.RAZON_GVF_B, 3)} {BS}{BS}"
        for r in v.itertuples()
    ]
    t += longtable(
        "l r r r r r",
        "Dominio & $" + BS + "psi_d$ & Viv./pers. & Boot./Taylor & GVF A & GVF B",
        "Varianza de muestreo por dominio: $" + BS + "psi_d$ del bootstrap por viviendas (puntos porcentuales al cuadrado) y razones "
        "frente a las alternativas: bootstrap por personas, Taylor y las dos GVF (Ecuación~" + BS + "ref{eq:gvf}; razón GVF/bootstrap).",
        "tab:app_varianza",
        filas,
    )
    t += figura("img/fh_gvf_ajuste.png", "0.9", "Varianza de muestreo observada frente a la ajustada por las GVF A y B. Fuente: tabla de ajuste de la GVF.", "fig:app_gvf")
    t += figura("img/fh_escenarios_varianza.png", "1.0", "Cambio del EBLUP de cada dominio frente al escenario base en los ocho escenarios alternativos de la varianza de muestreo. Fuente: tabla de sensibilidad a la varianza por dominio.", "fig:app_escenarios_varianza")
    return t


def s_validacion():
    """Sección de errores por dominio de la validación predictiva."""
    t = seccion(
        "Validación predictiva por dominio",
        "app:validacion",
        "Esta sección presenta el error de cada dominio retirado en los dos ejercicios de la validación predictiva "
        "dejar-un-dominio-fuera; la cita la Sección~" + BS + "ref{sec:res_validacion}.",
    )
    v = pd.read_csv(DAT / "fh_validacion_cruzada.csv")
    fx = v[v.Ejercicio == "COVARIABLES_FIJAS"].set_index("NOMBRE_DOMINIO")
    pc = v[v.Ejercicio == "PROCEDIMIENTO_COMPLETO"].set_index("NOMBRE_DOMINIO")
    filas = []
    for dom in sorted(fx.index):
        a, b = fx.loc[dom], pc.loc[dom]
        cov = "ninguna" if pd.isna(b.Covariables) or b.Covariables in ("", "—") else ", ".join(NOMBRES.get(c.strip(), c) for c in str(b.Covariables).split("+"))
        filas.append(f"{esc(dom)} & {f(a.Directa)} & {f(a.Prediccion)} & {sig(a.Error, 2)} & {sig(a.Z_pred, 2)} & {f(b.Prediccion)} & {sig(b.Error, 2)} & {sig(b.Z_pred, 2)} & {cov} {BS}{BS}")
    t += longtable(
        "l r r r r r r r p{3.4cm}",
        "Dominio & Directa & Fijas & Error & $Z_{" + BS + "text{pred}}$ & Completo & Error & $Z_{" + BS + "text{pred}}$ & Covariables (completo)",
        "Validación predictiva dejar-un-dominio-fuera por dominio: estimación sintética del dominio retirado con las covariables "
        "fijas y con el procedimiento completo, error frente a la directa (puntos porcentuales) y error estandarizado.",
        "tab:app_validacion",
        filas,
    )
    t += figura("img/fh_validacion_cruzada.png", "0.9", "Estimación del dominio retirado frente a su estimación directa en los dos ejercicios. Fuente: tabla de validación cruzada del Fay-Herriot clásico.", "fig:app_validacion")
    return t


def s_espacial():
    """Sección del detalle de las ocho especificaciones espaciales."""
    t = seccion(
        "Detalle del modelo espacial",
        "app:espacial",
        "Esta sección presenta las ocho especificaciones espaciales, su validación, sus coeficientes y las sensibilidades del "
        "parámetro $" + BS + "rho$; la cita la Sección~" + BS + "ref{sec:res_espacial}.",
    )
    c = pd.read_csv(DAT / "fhe_comparacion_modelos.csv")
    filas = [
        f"{ESCENARIOS[r.escenario]} & {r.estructura} & {f(r.A_hat, 3)} & {f(r.rho_hat, 3)} & {f(r.AIC, 3)} & {sig(r.Delta_AIC)} & {f(r.LRT, 3)} & {f(r.p_LRT, 3)} & {f(r.R2, 3)} {BS}{BS}"
        for r in c.itertuples()
    ]
    t += tabla("l l r r r r r r r", "Matriz & Estructura & $" + BS + "hat{" + BS + "sigma}_u^2$ & $" + BS + "hat{" + BS + "rho}$ & AIC & $" + BS + "Delta$AIC & LRT & $p$ & $R^2$",
               "Las ocho especificaciones espaciales con la tasa de homicidios fija. AIC del clásico: 108.904; $" + BS + "Delta$AIC = AIC clásico $-$ AIC espacial.",
               "tab:app_espacial", filas)
    m = pd.read_csv(DAT / "fhe_validacion_cruzada_metricas.csv")
    m = m[~((m.predictor == "pred_clasico") & ~((m.escenario == "knn3") & (m.estructura == "muestra")))]
    pred = {"pred_clasico": "Sintético clásico", "pred_sint_esp": "Sintético espacial", "pred_espacial": "Espacial con efecto"}
    filas = [
        f"{'todos' if r.predictor == 'pred_clasico' else ESCENARIOS[r.escenario] + ', ' + r.estructura} & {pred[r.predictor]} & {f(r.RMSE)} & {f(r.MAE)} & {sig(r.sesgo_medio, 2)} & {f(r.RMSE_corregido)} & {f(100 * r.Cobertura)} & {sig(r.Habilidad_vs_nulo, 2)} {BS}{BS}"
        for r in m.itertuples()
    ]
    t += longtable("p{3.6cm} l r r r r r r", "Especificación & Estimador & RMSE & MAE & Sesgo & RMSE$_c$ & Cob. & Habilidad",
                   "Validación dejar-un-dominio-fuera con la tasa de homicidios fija, por especificación y estimador. Errores en puntos "
                   "porcentuales; Cob.: cobertura del intervalo del 95~" + BS + "% en \\%; habilidad frente al modelo de solo intercepto (RMSE 2.77).",
                   "tab:app_espacial_validacion", filas)
    co = pd.read_csv(DAT / "fhe_coeficientes_comparacion.csv")
    co = co[co.Parametro == "TASA_HOMICIDIOS"]
    filas = [
        f"{ESCENARIOS[r.escenario]} & {r.estructura} & {f(r.beta_espacial, 3)} & {f(r.EE_espacial, 3)} & {f(r.p_espacial, 3)} & {sig(r.Delta_beta_sobre_EE_clasico)} {BS}{BS}"
        for r in co.itertuples()
    ]
    t += tabla("l l r r r r", "Matriz & Estructura & $" + BS + "hat{" + BS + "beta}_1$ & EE & $p$ & Cambio en EE",
               "Coeficiente de la tasa de homicidios en cada especificación espacial. Clásico: 0.099 (EE 0.036, $p = 0.006$); cambio "
               "medido en errores estándar del clásico.", "tab:app_espacial_coeficientes", filas)
    r_ = pd.read_csv(DAT / "fhe_sensibilidad_rho_objetivos.csv")
    filas = [f"{ESCENARIOS[r.escenario]} & {esc(r.conjunto_objetivos)} & {int(r.n_objetivos)} & {f(r.rho_hat, 3)} & {f(r.p_LRT, 3)} {BS}{BS}" for r in r_.itertuples()]
    t += longtable("l l r r r", "Matriz & Nodos sin dato & Nodos & $" + BS + "hat{" + BS + "rho}$ & $p$",
                   "Sensibilidad de $" + BS + "hat{" + BS + "rho}$ de la estructura completa a los municipios objetivo incluidos como nodos.",
                   "tab:app_espacial_rho", filas)
    ce = pd.read_csv(DAT / "fhe_sensibilidad_centroide.csv")
    filas = [f"{ESCENARIOS[r.escenario]} & {r.estructura} & {f(r.rho_capital, 3)} & {f(r.rho_alternativo, 3)} & {f(r.p_LRT_capital, 3)} & {f(r.p_LRT_alternativo, 3)} {BS}{BS}" for r in ce.itertuples()]
    t += tabla("l l r r r r", "Matriz & Estructura & $" + BS + "hat{" + BS + "rho}$ capital & $" + BS + "hat{" + BS + "rho}$ media & $p$ capital & $p$ media",
               "Sensibilidad a la ubicación del nodo de cada área metropolitana: en la capital o en la media de sus municipios.",
               "tab:app_espacial_centroide", filas)
    t += figura("img/fhe_perfil_rho.png", "0.85", "Perfil de verosimilitud de $" + BS + "rho$ en los cuatro escenarios de la matriz. Fuente: tabla de perfil de $" + BS + "rho$.", "fig:app_perfil_rho")
    t += figura("img/fhe_validacion_cruzada.png", "0.9", "Estimación del dominio retirado frente a la directa: sintético clásico y espacial con efecto, escenario de referencia. Fuente: tabla de validación cruzada del modelo espacial.", "fig:app_fhe_validacion")
    t += BS + "FloatBarrier\n\n"
    return t


def s_municipios():
    """Sección con las 83 estimaciones municipales."""
    t = seccion(
        "Estimaciones de los 83 municipios",
        "app:municipios",
        "Esta sección presenta la estimación de cada municipio objetivo en la tabla final y con el modelo espacial; la citan las "
        "Secciones~" + BS + "ref{sec:res_sin_muestra}, " + BS + "ref{sec:res_benchmarking} y~" + BS + "ref{sec:res_patrones}.",
    )
    filas = (SAL / "filas_municipios.tex").read_text(encoding="utf-8").splitlines()
    t += longtable(
        "l p{3.0cm} l r r r l l r r",
        "Código & Municipio & Depto. & Sin ajuste & Final & CV & Clase & Rango & Espacial & CV",
        "Estimaciones de los 83 municipios objetivo, 2018, en \\%. Sin ajuste: estimación sintética del benchmark; Final: tras el "
        "benchmarking (solo cambian Cali y Yumbo); CV en \\%; Clase: por el CV final; Rango: estado de extrapolación; Espacial: "
        "predictor espacial del escenario de referencia y su CV. Toda estimación es condicional al modelo.",
        "tab:app_municipios",
        filas,
        tamano="scriptsize",
    )
    t += figura("img/fh_sensibilidad_extrapolacion.png", "0.9", "Municipios que extrapolan: estimación publicada, estimación con la tasa de homicidios recortada al rango de los dominios y franja de la estimación al retirar cada dominio. Fuente: tabla de sensibilidad de la extrapolación.", "fig:app_sensibilidad_extrapolacion")
    return t


def citar_contenido(t):
    """Agrega, tras la frase de apertura de una sección, la cita de sus tablas y figuras.

    Args:
        t (str): código LaTeX de una sección generada por `seccion` y sus tablas y figuras.

    Returns:
        str: la sección con una frase «Incluye la Tabla~… y la Figura~…» después de la apertura.
    """
    import re

    etiquetas = re.findall(r"\\label\{((?:tab|fig):[^}]+)\}", t)
    if not etiquetas:
        return t
    piezas = [("la Tabla~" if e.startswith("tab:") else "la Figura~") + BS + "ref{" + e + "}" for e in etiquetas]
    frase = "Incluye " + (", ".join(piezas[:-1]) + " y " + piezas[-1] if len(piezas) > 1 else piezas[0]) + ".\n\n"
    k = t.index("\n\n", t.index(BS + "label{app:")) + 2
    k = t.index("\n\n", k) + 2
    return t[:k] + frase + t[k:]


def main():
    """Escribe chapters/appendice.tex."""
    viejo = (DOC / "chapters" / "appendice.tex").read_text(encoding="utf-8")
    i = viejo.index(BS + "section{Material complementario de Resultados}")
    i = viejo.rindex(SEP, 0, i)
    j = viejo.index(BS + "FloatBarrier", i) + len(BS + "FloatBarrier")
    complementario = viejo[i:j] + "\n\n"
    partes = [
        "\n" + BS + "label{sec:apendice}\n\nEl apéndice reúne el material de apoyo que el cuerpo del documento cita: la "
        "reproducción del procesamiento, el linaje de las tablas, los nombres de las variables, el catálogo de covariables y "
        "las tablas y figuras complementarias de cada etapa de los Resultados.\n\n",
        s_reproducibilidad(), s_linaje(), s_variables(), s_catalogo(), s_auditoria(), s_descriptivo(), s_seleccion(),
        s_especificaciones(), s_dominios_modelo(), s_varianza(), s_validacion(), s_espacial(), s_municipios(),
        complementario,
    ]
    partes = [partes[0]] + [citar_contenido(p) for p in partes[1:-1]] + [partes[-1]]
    (DOC / "chapters" / "appendice.tex").write_text("".join(partes), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
