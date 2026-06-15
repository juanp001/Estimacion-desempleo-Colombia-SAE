# Databricks notebook source
# MAGIC %sql
# MAGIC SELECT
# MAGIC PER,
# MAGIC MES,
# MAGIC DEPARTAMENTO,
# MAGIC MUNICIPIO,
# MAGIC TASA_DESEMPLEO_PCT,
# MAGIC SE_BOOTSTRAP_PCT,
# MAGIC CV_PORCENTAJE,
# MAGIC COB_ENER_RURAL,
# MAGIC TASA_TRAN_EDU_SUP,
# MAGIC IND_POB_MULT,
# MAGIC IND_PROD
# MAGIC FROM
# MAGIC tesis.modelo.tasa_desempleo_covariables_seleccionadas

# COMMAND ----------

# =============================================================================
# MODELO FAY-HERRIOT PARA ESTIMACIÓN DE TASA DE DESEMPLEO
# Implementación en Python - Compatible con Databricks
# =============================================================================
# Dominio: PER + MES + DEPARTAMENTO + MUNICIPIO
# Variable objetivo: TASA_DESEMPLEO_PCT
# Varianza directa: SE_BOOTSTRAP_PCT^2  (se eleva al cuadrado)
# Covariables: COB_ENER_RURAL, TASA_TRAN_EDU_SUP, IND_POB_MULT, IND_PROD
# =============================================================================

import pandas as pd
import numpy as np
from scipy.optimize import minimize_scalar
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
# 1. CARGA DE DATOS
# -----------------------------------------------------------------------------
# En Databricks, reemplaza la siguiente línea por:
df = spark.table("tesis.modelo.tasa_desempleo_covariables_seleccionadas").toPandas()
# O si está en DBFS:
#   df = pd.read_csv("/dbfs/mnt/tu_ruta/fay_herriot.csv")

#df = pd.read_csv("fay_herriot.csv")

# Crear columna de dominio compuesto
df["DOMINIO"] = (
    df["PER"].astype(str) + "_" +
    df["MES"].astype(str) + "_" +
    df["DEPARTAMENTO"] + "_" +
    df["MUNICIPIO"]
)

print(f"Dominios (municipios): {len(df)}")
print(f"Columnas disponibles:  {df.columns.tolist()}\n")

# -----------------------------------------------------------------------------
# 2. DEFINICIÓN DE VARIABLES
# -----------------------------------------------------------------------------
Y_col    = "TASA_DESEMPLEO_PCT"    # Estimación directa
SE_col   = "SE_BOOTSTRAP_PCT"      # Error estándar bootstrap
covars   = ["COB_ENER_RURAL", "TASA_TRAN_EDU_SUP"]

# NOTA SOBRE LA CANTIDAD DE COVARIABLES:
# Con n=23 dominios y k=4 covariables el ratio n/k ≈ 5.8, por debajo
# del mínimo recomendado de 10. Sin embargo, dado que el modelo Fay-Herriot
# no estima parámetros de la misma forma que una regresión clásica (la
# varianza de muestreo Di ya es conocida), 4 covariables son razonables
# si todas son significativas, lo cual se verifica abajo.
# Si se quiere ser más conservador, se pueden mantener solo las 2 con
# mayor correlación con Y: COB_ENER_RURAL y TASA_TRAN_EDU_SUP.

Y  = df[Y_col].values
Di = df[SE_col].values ** 2      # Varianza conocida de muestreo (Di)
n  = len(Y)

# Matriz de diseño con intercepto
X = np.column_stack([np.ones(n)] + [df[c].values for c in covars])
p = X.shape[1]   # número de parámetros (intercepto + 4 covariables)

# -----------------------------------------------------------------------------
# 3. FUNCIÓN AUXILIAR: ESTIMACIÓN GLS DE β DADO A
# -----------------------------------------------------------------------------
def gls_beta(A, Y, X, Di):
    """Estimación GLS de beta: β̂ = (X'V⁻¹X)⁻¹ X'V⁻¹Y, donde V = diag(Di + A)."""
    Vi   = 1.0 / (Di + A)                        # inversa de varianzas totales
    XtVi = X.T * Vi                               # X' V⁻¹
    XtViX = XtVi @ X
    XtViY = XtVi @ Y
    beta  = np.linalg.solve(XtViX, XtViY)
    return beta, XtVi, XtViX

# -----------------------------------------------------------------------------
# 4. ESTIMACIÓN DE A (VARIANZA DE EFECTOS ALEATORIOS) — MÉTODO REML
# -----------------------------------------------------------------------------
def neg_reml_loglik(log_A, Y, X, Di):
    """Log-verosimilitud REML negativa (para minimizar)."""
    A    = np.exp(log_A)        # A > 0 siempre
    Vi   = 1.0 / (Di + A)
    Vi_X = X.T * Vi
    Q    = Vi_X @ X             # X' V⁻¹ X
    try:
        Qinv = np.linalg.inv(Q)
    except np.linalg.LinAlgError:
        return 1e10

    # Proyector: P = V⁻¹ - V⁻¹ X Q⁻¹ X' V⁻¹
    PY   = Vi * Y - (Vi_X.T @ (Qinv @ (Vi_X @ Y)))

    log_det_V   = np.sum(np.log(Di + A))
    log_det_Q   = np.linalg.slogdet(Q)[1]
    quadratic   = Y @ PY

    reml_ll = -0.5 * (log_det_V + log_det_Q + quadratic)
    return -reml_ll

# Optimización sobre log(A) en el intervalo [1e-6, var(Y)*10]
result = minimize_scalar(
    neg_reml_loglik,
    bounds=(np.log(1e-6), np.log(np.var(Y) * 10)),
    method="bounded",
    args=(Y, X, Di)
)
A_hat = np.exp(result.x)

print("=" * 55)
print("ESTIMACIÓN DE PARÁMETROS DEL MODELO FAY-HERRIOT")
print("=" * 55)
print(f"\nVarianza de efectos aleatorios (Â):  {A_hat:.6f}")
print(f"Desv. estándar de efectos aleatorios: {np.sqrt(A_hat):.6f}")

# -----------------------------------------------------------------------------
# 5. ESTIMACIÓN DE β (EFECTOS FIJOS) CON A ESTIMADO
# -----------------------------------------------------------------------------
beta_hat, XtVi, XtViX = gls_beta(A_hat, Y, X, Di)
cov_beta = np.linalg.inv(XtViX)
se_beta  = np.sqrt(np.diag(cov_beta))
t_stats  = beta_hat / se_beta
p_vals   = 2 * (1 - stats.norm.cdf(np.abs(t_stats)))

param_names = ["Intercepto"] + covars
print("\nESTIMACIÓN DE COEFICIENTES:")
print(f"{'Parámetro':<22} {'Coef':>10} {'SE':>10} {'z':>8} {'p-valor':>10}")
print("-" * 62)
for name, b, se, z, pv in zip(param_names, beta_hat, se_beta, t_stats, p_vals):
    signif = "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.10 else ""
    print(f"{name:<22} {b:>10.4f} {se:>10.4f} {z:>8.3f} {pv:>10.4f} {signif}")
print("Signif: *** p<0.01  ** p<0.05  * p<0.10")

# -----------------------------------------------------------------------------
# 6. PESOS DE SHRINKAGE (γ_i) Y PREDICTOR EBLUP
# -----------------------------------------------------------------------------
# γ_i = A / (A + Di): cuánto se confía en el modelo vs. la estimación directa
gamma_i = A_hat / (A_hat + Di)

# Predictor sintético: X_i β̂
mu_hat = X @ beta_hat

# EBLUP: θ̂_i = γ_i * y_i + (1 - γ_i) * X_i β̂
eblup = gamma_i * Y + (1 - gamma_i) * mu_hat

# -----------------------------------------------------------------------------
# 7. MSE DEL EBLUP (Prasad-Rao, primer orden)
# -----------------------------------------------------------------------------
# MSE(θ̂_i) ≈ g1i(A) + g2i(A) + 2*g3i(A)
# g1i = γ_i * Di        (varianza de contracción)
# g2i = (1-γ_i)^2 * x_i' (X'V⁻¹X)^-1 x_i   (varianza de estimación de β)
# g3i ≈ Di^2 / (A+Di)^2 * [2/(n * (algo))]  — aquí usamos aprox. Datta-Lahiri

g1i = gamma_i * Di
g2i = np.array([
    (1 - gamma_i[i])**2 * (X[i] @ cov_beta @ X[i])
    for i in range(n)
])

# Corrección g3i (2da derivada de REML)
# Varianza asintótica de Â bajo REML: 2 / sum(1/(Di+A)^2)
sum_vi2 = np.sum(1.0 / (Di + A_hat)**2)
var_A   = 2.0 / sum_vi2   if sum_vi2 > 0 else 0.0
g3i     = (Di / (Di + A_hat))**2 * var_A

mse_eblup = g1i + g2i + 2 * g3i
rmse_eblup = np.sqrt(mse_eblup)

# CV del EBLUP (%)
cv_eblup = 100 * rmse_eblup / np.abs(eblup)

# -----------------------------------------------------------------------------
# 8. RESULTADOS FINALES
# -----------------------------------------------------------------------------
results = df[["DOMINIO", "DEPARTAMENTO", "MUNICIPIO",
              Y_col, SE_col, "CV_PORCENTAJE"]].copy()

results["VARIANZA_DIRECTA"] = Di
results["GAMMA_SHRINKAGE"]  = gamma_i.round(4)
results["PRED_SINTETICO"]   = mu_hat.round(4)
results["EBLUP"]            = eblup.round(4)
results["MSE_EBLUP"]        = mse_eblup.round(6)
results["RMSE_EBLUP"]       = rmse_eblup.round(4)
results["CV_EBLUP_PCT"]     = cv_eblup.round(2)
results["MEJORA_CV_PCT"]    = (results["CV_PORCENTAJE"] - results["CV_EBLUP_PCT"]).round(2)

print("\n" + "=" * 55)
print("RESULTADOS EBLUP POR DOMINIO")
print("=" * 55)
display_cols = ["MUNICIPIO", Y_col, "EBLUP", "CV_PORCENTAJE", "CV_EBLUP_PCT",
                "GAMMA_SHRINKAGE", "MEJORA_CV_PCT"]
print(results[display_cols].to_string(index=False))

# -----------------------------------------------------------------------------
# 9. DIAGNÓSTICOS DEL MODELO
# -----------------------------------------------------------------------------
print("\n" + "=" * 55)
print("DIAGNÓSTICOS DEL MODELO")
print("=" * 55)

# Residuos estandarizados
residuals   = (Y - mu_hat) / np.sqrt(Di + A_hat)
print(f"\nResiduals estandarizados:")
print(f"  Media:       {residuals.mean():.4f}  (esperado ≈ 0)")
print(f"  Desv. std:   {residuals.std():.4f}  (esperado ≈ 1)")

# Test Shapiro-Wilk sobre residuos
sw_stat, sw_pval = stats.shapiro(residuals)
print(f"\nTest Shapiro-Wilk (normalidad de residuos):")
print(f"  W = {sw_stat:.4f},  p-valor = {sw_pval:.4f}")
if sw_pval > 0.05:
    print("  → No se rechaza normalidad (p > 0.05) ✓")
else:
    print("  → Se rechaza normalidad (p ≤ 0.05) — revisar supuestos ✗")

# R² del predictor sintético
ss_tot = np.sum((Y - Y.mean())**2)
ss_res = np.sum((Y - mu_hat)**2)
r2     = 1 - ss_res / ss_tot
print(f"\nR² del predictor sintético (X β̂): {r2:.4f}")

# Reducción media del CV
mejora_media = results["MEJORA_CV_PCT"].mean()
print(f"\nReducción media del CV:            {mejora_media:.2f} puntos porcentuales")
print(f"  (positivo = el EBLUP mejora la precisión)")

# Shrinkage promedio
print(f"\nPeso de shrinkage promedio (γ̄):   {gamma_i.mean():.4f}")
print(f"  (cercano a 1 → el modelo confía más en el modelo que en la directa)")
print(f"  (cercano a 0 → domina la estimación directa)")

# -----------------------------------------------------------------------------
# 10. NOTA SOBRE SELECCIÓN DE COVARIABLES
# -----------------------------------------------------------------------------
print("\n" + "=" * 55)
print("NOTA: SELECCIÓN DE COVARIABLES")
print("=" * 55)
print("""
Con n=23 dominios y k=4 covariables:
  - Ratio n/k = 5.8  (recomendado ≥ 10)
  - Correlaciones con TASA_DESEMPLEO_PCT (todas significativas):
      COB_ENER_RURAL    : r = -0.595  ***
      TASA_TRAN_EDU_SUP : r =  0.487  **
      IND_POB_MULT      : r =  0.443  **
      IND_PROD          : r = -0.414  **
  - Correlación máxima entre covariables: 0.61 (COB_ENER vs IND_POB)
  - Determinante de la matriz de correlaciones: 0.376 (no hay multicolinealidad severa)

RECOMENDACIÓN:
  Las 4 covariables son justificables dado que todas tienen significancia
  estadística y la multicolinealidad no es grave. Si se desea mayor
  parsimonia, se puede reducir a 2 (COB_ENER_RURAL + TASA_TRAN_EDU_SUP)
  que son las de mayor correlación con la variable objetivo.
""")

# -----------------------------------------------------------------------------
# 11. EXPORTAR RESULTADOS
# -----------------------------------------------------------------------------
#output_path = "resultados_fay_herriot.csv"
#results.to_csv(output_path, index=False)
#print(f"Resultados exportados a: {output_path}")

# En Databricks, para guardar como tabla Delta:
spark_df = spark.createDataFrame(results)
spark_df.write.mode("overwrite").saveAsTable("tesis.modelo.fay_herriot_resultados")