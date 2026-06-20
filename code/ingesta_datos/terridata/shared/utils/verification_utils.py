from functools import reduce
from operator import add

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, when, sum as spark_sum

from shared.config.terridata_config import (
    TBL_DIM_INDICADORES,
    COLUMNAS_ID,
    UMBRAL_RIESGO_CASTEO,
)


def verificar_conservacion_registros(df_bronce: DataFrame, n_filas_plata: int) -> bool:
    print("=" * 60)
    print("VERIFICACIÓN 1: CONSERVACIÓN DE REGISTROS")
    print("=" * 60)

    count_largo = df_bronce.select(
        "CODIGO_DEPARTAMENTO", "CODIGO_ENTIDAD", "ANO", "MES"
    ).distinct().count()

    print(f"Combinaciones únicas en BRONCE: {count_largo:,}")
    print(f"Filas en PLATA:                 {n_filas_plata:,}")

    if count_largo == n_filas_plata:
        print("✅ CORRECTO: El número de registros se conservó")
        return True
    else:
        print(f"❌ ERROR: Diferencia de {abs(count_largo - n_filas_plata):,} registros")
        return False


def verificar_duplicados(df_plata: DataFrame, n_filas: int) -> bool:
    print("=" * 60)
    print("VERIFICACIÓN 2: DUPLICADOS EN PLATA")
    print("=" * 60)

    filas_unicas = df_plata.select(
        "CODIGO_DEPARTAMENTO", "CODIGO_ENTIDAD", "ANO", "MES"
    ).distinct().count()

    print(f"Total filas:   {n_filas:,}")
    print(f"Claves únicas: {filas_unicas:,}")

    if n_filas == filas_unicas:
        print("✅ CORRECTO: No hay duplicados")
        return True
    else:
        print(f"❌ ERROR: {n_filas - filas_unicas:,} filas duplicadas")
        display(
            df_plata.groupBy("CODIGO_DEPARTAMENTO", "CODIGO_ENTIDAD", "ANO", "MES")
            .count()
            .filter(col("count") > 1)
            .limit(10)
        )
        return False


def verificar_integridad_muestra(df_bronce: DataFrame, df_plata: DataFrame,
                                  n_muestras: int = 10) -> bool:
    print("=" * 60)
    print("VERIFICACIÓN 3: INTEGRIDAD DE MUESTRA ALEATORIA")
    print("=" * 60)

    muestras = (
        df_bronce
        .filter(col("DATO_NUMERICO").isNotNull() | col("DATO_CUALITATIVO").isNotNull())
        .select("CODIGO_ENTIDAD", "ANO", "MES", "CODIGO_INDICADOR",
                "DATO_NUMERICO", "DATO_CUALITATIVO")
        .sample(False, 0.0001)
        .limit(n_muestras)
        .collect()
    )

    if not muestras:
        print("⚠️  No se pudieron obtener muestras. Verificación omitida.")
        return True

    print(f"Verificando {len(muestras)} combinaciones aleatorias...\n")
    errores = 0

    for row in muestras:
        entidad   = row.CODIGO_ENTIDAD
        ano       = int(row.ANO)
        mes       = int(row.MES)
        indicador = row.CODIGO_INDICADOR

        valor_esperado = (
            str(row.DATO_NUMERICO) if row.DATO_NUMERICO is not None
            else row.DATO_CUALITATIVO
        )

        fila_plata = df_plata.filter(
            (col("CODIGO_ENTIDAD") == entidad) &
            (col("ANO") == ano) &
            (col("MES") == mes)
        ).select(col(f"`{indicador}`").cast("string")).first()

        valor_plata = fila_plata[0] if fila_plata else None

        if valor_esperado != valor_plata:
            print(f"  ❌ Entidad {entidad}, Año {ano}, Mes {mes}, Indicador {indicador}")
            print(f"     Esperado: {valor_esperado!r}  →  Obtenido: {valor_plata!r}")
            errores += 1
        else:
            print(f"  ✅ {entidad} / {ano}-{mes} / {indicador}: {valor_plata!r}")

    if errores == 0:
        print(f"\n✅ CORRECTO: Las {len(muestras)} muestras coinciden")
        return True
    else:
        print(f"\n❌ ERROR: {errores}/{len(muestras)} muestras no coinciden")
        return False


def verificar_calidad_casteo(clasificacion_completa: list) -> bool:
    print("=" * 60)
    print("VERIFICACIÓN 4: CALIDAD DE CASTEO NUMÉRICO")
    print("=" * 60)

    numericos           = [r for r in clasificacion_completa if r.TIPO_DATO == "numerico"]
    total_valores       = sum(r.total_valores for r in numericos)
    valores_en_riesgo   = sum(r.count_cualitativo for r in numericos)
    indicadores_riesgo  = [r for r in numericos if r.count_cualitativo > 0]
    pct_riesgo = (valores_en_riesgo / total_valores * 100) if total_valores > 0 else 0.0

    print(f"Indicadores numéricos:                          {len(numericos)}")
    print(f"  Con valores cualitativos (→ NULL tras cast):  {len(indicadores_riesgo)}")
    print(f"  Valores en riesgo: {valores_en_riesgo:,} de {total_valores:,} ({pct_riesgo:.3f}%)")

    if indicadores_riesgo:
        print("\nTop 10 indicadores con más valores en riesgo:")
        top = sorted(indicadores_riesgo, key=lambda r: r.count_cualitativo, reverse=True)[:10]
        for r in top:
            pct = r.count_cualitativo / r.total_valores * 100
            print(f"  - {r.CODIGO_INDICADOR}: {r.count_cualitativo:,} valores ({pct:.1f}%)")

    if pct_riesgo <= UMBRAL_RIESGO_CASTEO:
        print(f"\n✅ CORRECTO: Riesgo ({pct_riesgo:.3f}%) dentro del umbral ({UMBRAL_RIESGO_CASTEO}%)")
        return True
    else:
        print(f"\n❌ ADVERTENCIA: Riesgo ({pct_riesgo:.2f}%) excede umbral ({UMBRAL_RIESGO_CASTEO}%)")
        return False


def verificar_reclasificacion_indicadores(spark, tipo_indicador_dict: dict) -> bool:
    print("=" * 60)
    print("VERIFICACIÓN 5: RECLASIFICACIÓN DE INDICADORES")
    print("=" * 60)

    try:
        prev_tipos = {
            row.CODIGO_INDICADOR: row.TIPO_DATO
            for row in spark.table(TBL_DIM_INDICADORES)
                             .select("CODIGO_INDICADOR", "TIPO_DATO")
                             .collect()
        }
    except Exception:
        print("⚠️  No existe versión previa de dim_indicadores. Verificación omitida.")
        return True

    cambios    = [(ind, prev_tipos[ind], t) for ind, t in tipo_indicador_dict.items()
                  if ind in prev_tipos and prev_tipos[ind] != t]
    nuevos     = [ind for ind in tipo_indicador_dict if ind not in prev_tipos]
    eliminados = [ind for ind in prev_tipos if ind not in tipo_indicador_dict]

    print(f"Indicadores nuevos:             {len(nuevos)}")
    print(f"Indicadores eliminados:         {len(eliminados)}")
    print(f"Indicadores que cambiaron tipo: {len(cambios)}")

    if cambios:
        print("\n⚠️  CAMBIOS DE TIPO (pueden romper queries downstream):")
        for ind, tipo_prev, tipo_nuevo in cambios[:20]:
            print(f"  - {ind}: {tipo_prev} → {tipo_nuevo}")
        if len(cambios) > 20:
            print(f"  ... y {len(cambios) - 20} más")

    if not cambios:
        print("\n✅ CORRECTO: Ningún indicador cambió de tipo")
        return True
    else:
        print("\n❌ ADVERTENCIA: Hay reclasificaciones. Verificar si son esperadas.")
        return False


def verificar_valores_no_nulos(df_largo: DataFrame, df_ancho: DataFrame,
                                tolerancia_porcentaje: float = 1.0) -> bool:
    print("=" * 60)
    print("VERIFICACIÓN PESADA: CONSERVACIÓN DE VALORES NO NULOS")
    print("=" * 60)

    total_largo = df_largo.filter(col("VALOR").isNotNull()).count()
    print(f"Total de valores no nulos en BRONCE: {total_largo:,}")

    cols_indicadores = [c for c in df_ancho.columns if c not in COLUMNAS_ID]
    count_expr = reduce(add, [when(col(c).isNotNull(), 1).otherwise(0) for c in cols_indicadores])
    total_ancho = df_ancho.select(spark_sum(count_expr).alias("total")).first()[0]
    print(f"Total de valores no nulos en PLATA:  {total_ancho:,}")

    diferencia = abs(total_largo - total_ancho)
    pct_diff   = (diferencia / total_largo * 100) if total_largo > 0 else 0.0
    print(f"Diferencia: {diferencia:,} ({pct_diff:.3f}%)")

    if pct_diff == 0:
        print("\n✅ CORRECTO: 100% de valores conservados")
        return True
    elif pct_diff <= tolerancia_porcentaje:
        print(f"\n✅ CORRECTO: Dentro de tolerancia ({tolerancia_porcentaje}%)")
        return True
    else:
        print(f"\n❌ ERROR: Diferencia ({pct_diff:.2f}%) excede tolerancia ({tolerancia_porcentaje}%)")
        return False
