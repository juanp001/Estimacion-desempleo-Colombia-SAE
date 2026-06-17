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
# =============================================================================

import pandas as pd
import numpy as np
from scipy.optimize import minimize_scalar
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
# 1. CARGA DE DATOS
# -----------------------------------------------------------------------------
df = spark.table("tesis.preprocesamiento.covariables_seleccionadas").toPandas()
# O si está en DBFS:
#   df = pd.read_csv("/dbfs/mnt/tu_ruta/fay_herriot.csv")

#df = pd.read_csv("fay_herriot.csv")

df["DOMINIO"] = (
    df["PER"].astype(str) + "_" +
    df["MES"].astype(str) + "_" +
    df["DEPARTAMENTO"] + "_" +
    df["MUNICIPIO"]
)

print(f"Dominios (municipios): {len(df)}")
print(f"Columnas disponibles:  {df.columns.tolist()}\n")

Y_col  = "TASA_DESEMPLEO_PCT"
SE_col = "SE_BOOTSTRAP_PCT"

Y  = df[Y_col].values
Di = df[SE_col].values ** 2      # Varianza conocida de muestreo (Di)
n  = len(Y)

# -----------------------------------------------------------------------------
# 2. CONJUNTOS DE COVARIABLES A EVALUAR
# -----------------------------------------------------------------------------
# Agrega o quita subconjuntos según los escenarios que quieras comparar.
# Si solo hay un subconjunto, no se calcula AIC (no hay comparación).
COVAR_SETS = [
    ["IICA_CONFLICTO", "TASA_TRAN_EDU_SUP", "IND_POB_MULT", "IND_PROD"],
    ["TASA_TRAN_EDU_SUP", "IND_POB_MULT"],
    ["IICA_CONFLICTO","IND_PROD"],
    ["IICA_CONFLICTO", "TASA_TRAN_EDU_SUP"],
]

# -----------------------------------------------------------------------------
# 3. FUNCIONES AUXILIARES
# -----------------------------------------------------------------------------
def _vi_xtvi_xtvix(A, X, Di):
    """Componentes comunes de GLS: V⁻¹ (diagonal), X'V⁻¹ y X'V⁻¹X, con V = diag(Di + A)."""
    Vi    = 1.0 / (Di + A)
    XtVi  = X.T * Vi
    XtViX = XtVi @ X
    return Vi, XtVi, XtViX


def gls_beta(A, Y, X, Di):
    """Estimación GLS de beta: β̂ = (X'V⁻¹X)⁻¹ X'V⁻¹Y, donde V = diag(Di + A)."""
    Vi, XtVi, XtViX = _vi_xtvi_xtvix(A, X, Di)
    beta = np.linalg.solve(XtViX, XtVi @ Y)
    return beta, XtVi, XtViX


def neg_reml_loglik(log_A, Y, X, Di):
    """Log-verosimilitud REML negativa — usada para estimar A."""
    A = np.exp(log_A)
    Vi, Vi_X, Q = _vi_xtvi_xtvix(A, X, Di)
    try:
        Qinv = np.linalg.inv(Q)
    except np.linalg.LinAlgError:
        return 1e10
    PY          = Vi * Y - (Vi_X.T @ (Qinv @ (Vi_X @ Y)))
    log_det_V   = np.sum(np.log(Di + A))
    log_det_Q   = np.linalg.slogdet(Q)[1]
    reml_ll     = -0.5 * (log_det_V + log_det_Q + Y @ PY)
    return -reml_ll


def neg_ml_loglik(log_A, Y, X, Di):
    """Log-verosimilitud ML negativa — usada para calcular AIC entre modelos."""
    A = np.exp(log_A)
    Vi, XtVi, XtViX = _vi_xtvi_xtvix(A, X, Di)
    try:
        beta = np.linalg.solve(XtViX, XtVi @ Y)
    except np.linalg.LinAlgError:
        return 1e10
    resid     = Y - X @ beta
    log_det_V = np.sum(np.log(Di + A))
    quadratic = np.sum(Vi * resid**2)
    ml_ll     = -0.5 * (n * np.log(2 * np.pi) + log_det_V + quadratic)
    return -ml_ll


def fit_fay_herriot(covars):
    """Ajusta el modelo Fay-Herriot completo para un subconjunto de covariables."""
    X = np.column_stack([np.ones(n)] + [df[c].values for c in covars])
    p = X.shape[1]   # intercepto + covariables

    # Estimación de A por REML
    res_reml = minimize_scalar(
        neg_reml_loglik,
        bounds=(np.log(1e-6), np.log(np.var(Y) * 10)),
        method="bounded",
        args=(Y, X, Di)
    )
    A_hat = np.exp(res_reml.x)

    # Estimación de β por GLS con A estimado
    beta_hat, XtVi, XtViX = gls_beta(A_hat, Y, X, Di)
    cov_beta = np.linalg.inv(XtViX)
    se_beta  = np.sqrt(np.diag(cov_beta))
    t_stats  = beta_hat / se_beta
    p_vals   = 2 * (1 - stats.norm.cdf(np.abs(t_stats)))

    # Pesos de shrinkage y predictor EBLUP
    gamma_i = A_hat / (A_hat + Di)
    mu_hat  = X @ beta_hat
    eblup   = gamma_i * Y + (1 - gamma_i) * mu_hat

    # MSE Prasad-Rao (primer orden)
    g1i     = gamma_i * Di
    g2i     = np.array([(1 - gamma_i[i])**2 * (X[i] @ cov_beta @ X[i]) for i in range(n)])
    sum_vi2 = np.sum(1.0 / (Di + A_hat)**2)
    var_A   = 2.0 / sum_vi2 if sum_vi2 > 0 else 0.0
    g3i     = (Di / (Di + A_hat))**2 * var_A
    mse_eblup  = g1i + g2i + 2 * g3i
    rmse_eblup = np.sqrt(mse_eblup)
    cv_eblup   = 100 * rmse_eblup / np.abs(eblup)

    # Diagnósticos
    residuals        = (Y - mu_hat) / np.sqrt(Di + A_hat)
    sw_stat, sw_pval = stats.shapiro(residuals)
    r2               = 1 - np.sum((Y - mu_hat)**2) / np.sum((Y - Y.mean())**2)

    # Validación MSE EBLUP vs varianza directa
    mse_ratio        = Di / mse_eblup          # >1 indica ganancia de eficiencia
    pct_mejora_mse   = 100 * (Di - mse_eblup) / Di
    dominios_mejoran = np.mean(mse_eblup < Di)
    # Test de Wilcoxon: H0 → mediana(Di - MSE_EBLUP) = 0
    wil_stat, wil_pval = stats.wilcoxon(Di - mse_eblup, alternative="greater")

    # Tabla de resultados por dominio
    res_df = df[["DOMINIO", "DEPARTAMENTO", "MUNICIPIO", Y_col, SE_col, "CV_PORCENTAJE"]].copy()
    res_df["VARIANZA_DIRECTA"]  = Di
    res_df["GAMMA_SHRINKAGE"]   = gamma_i.round(4)
    res_df["PRED_SINTETICO"]    = mu_hat.round(4)
    res_df["EBLUP"]             = eblup.round(4)
    res_df["MSE_EBLUP"]         = mse_eblup.round(6)
    res_df["RMSE_EBLUP"]        = rmse_eblup.round(4)
    res_df["CV_EBLUP_PCT"]      = cv_eblup.round(2)
    res_df["MEJORA_CV_PCT"]     = (res_df["CV_PORCENTAJE"] - res_df["CV_EBLUP_PCT"]).round(2)
    res_df["RATIO_MSE"]         = mse_ratio.round(4)   # Di / MSE_EBLUP
    res_df["MEJORA_MSE_PCT"]    = pct_mejora_mse.round(2)

    # AIC vía ML (se optimiza A por separado con ML, no REML)
    res_ml     = minimize_scalar(
        neg_ml_loglik,
        bounds=(np.log(1e-6), np.log(np.var(Y) * 10)),
        method="bounded",
        args=(Y, X, Di)
    )
    log_lik_ml = -res_ml.fun
    aic        = -2 * log_lik_ml + 2       * (p + 1)          # p coefs + 1 para A
    bic        = -2 * log_lik_ml + np.log(n) * (p + 1)

    return {
        "covars":     covars,
        "p":          p,
        "A_hat":      A_hat,
        "beta_hat":   beta_hat,
        "se_beta":    se_beta,
        "t_stats":    t_stats,
        "p_vals":     p_vals,
        "gamma_i":    gamma_i,
        "mu_hat":     mu_hat,
        "eblup":      eblup,
        "rmse_eblup": rmse_eblup,
        "cv_eblup":   cv_eblup,
        "residuals":        residuals,
        "sw_stat":          sw_stat,
        "sw_pval":          sw_pval,
        "r2":               r2,
        "results_df":       res_df,
        "aic":              aic,
        "bic":              bic,
        "mse_ratio":        mse_ratio,
        "pct_mejora_mse":   pct_mejora_mse,
        "dominios_mejoran": dominios_mejoran,
        "wil_stat":         wil_stat,
        "wil_pval":         wil_pval,
    }

# -----------------------------------------------------------------------------
# 4. AJUSTE DE TODOS LOS MODELOS
# -----------------------------------------------------------------------------
print(f"Ajustando {len(COVAR_SETS)} modelo(s)...\n")
models = [fit_fay_herriot(covars) for covars in COVAR_SETS]

# -----------------------------------------------------------------------------
# 5. DIAGNÓSTICOS POR MODELO
# -----------------------------------------------------------------------------
for i, m in enumerate(models, 1):
    label       = f"MODELO {i}: {' + '.join(m['covars'])}"
    param_names = ["Intercepto"] + m["covars"]

    print("=" * 65)
    print(label)
    print("=" * 65)

    print(f"\nVarianza de efectos aleatorios (Â):   {m['A_hat']:.6f}")
    print(f"Desv. estándar de efectos aleatorios: {np.sqrt(m['A_hat']):.6f}")

    print("\nCOEFICIENTES:")
    print(f"{'Parámetro':<25} {'Coef':>10} {'SE':>10} {'z':>8} {'p-valor':>10}")
    print("-" * 65)
    for name, b, se, z, pv in zip(param_names, m["beta_hat"], m["se_beta"], m["t_stats"], m["p_vals"]):
        signif = "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.10 else ""
        print(f"{name:<25} {b:>10.4f} {se:>10.4f} {z:>8.3f} {pv:>10.4f} {signif}")
    print("Signif: *** p<0.01  ** p<0.05  * p<0.10")

    print("\nRESULTADOS EBLUP POR DOMINIO:")
    display_cols = ["MUNICIPIO", Y_col, "EBLUP", "CV_PORCENTAJE", "CV_EBLUP_PCT",
                    "GAMMA_SHRINKAGE", "MEJORA_CV_PCT"]
    print(m["results_df"][display_cols].to_string(index=False))

    print("\nDIAGNÓSTICOS:")
    print(f"  R² predictor sintético:       {m['r2']:.4f}")
    print(f"  Media residuos estand.:       {m['residuals'].mean():.4f}  (esperado ≈ 0)")
    print(f"  Desv. std residuos estand.:   {m['residuals'].std():.4f}  (esperado ≈ 1)")
    sw_ok = m["sw_pval"] > 0.05
    print(f"  Shapiro-Wilk: W={m['sw_stat']:.4f}, p={m['sw_pval']:.4f}  "
          + ("✓ normalidad" if sw_ok else "✗ revisar normalidad"))
    print(f"  Reducción media del CV:       {m['results_df']['MEJORA_CV_PCT'].mean():.2f} pp")
    print(f"  Shrinkage promedio (γ̄):       {m['gamma_i'].mean():.4f}")

    print("\nVALIDACIÓN MSE EBLUP vs VARIANZA DIRECTA:")
    print(f"  Dominios con MSE_EBLUP < Di: {m['dominios_mejoran']*100:.1f}%  "
          + ("✓ mejora generalizada" if m["dominios_mejoran"] >= 0.9 else
             "~ mejora parcial"      if m["dominios_mejoran"] >= 0.5 else
             "✗ sin mejora clara"))
    print(f"  Reducción media del MSE:      {m['pct_mejora_mse'].mean():.2f}%")
    print(f"  Ratio Di/MSE medio:           {m['mse_ratio'].mean():.4f}  (>1 indica ganancia)")
    print(f"  Ratio Di/MSE mediana:         {np.median(m['mse_ratio']):.4f}")
    wil_ok = m["wil_pval"] < 0.05
    print(f"  Wilcoxon (Di > MSE_EBLUP):   W={m['wil_stat']:.1f}, p={m['wil_pval']:.4f}  "
          + ("✓ reducción significativa" if wil_ok else "✗ no significativa"))
    print("\n  Detalle por dominio (Di vs MSE_EBLUP):")
    print(f"  {'Municipio':<30} {'Di':>12} {'MSE_EBLUP':>12} {'Ratio':>8} {'Mejora%':>9}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*8} {'-'*9}")
    for _, row in m["results_df"][["MUNICIPIO", "VARIANZA_DIRECTA", "MSE_EBLUP",
                                    "RATIO_MSE", "MEJORA_MSE_PCT"]].iterrows():
        flag = "✓" if row["MSE_EBLUP"] < row["VARIANZA_DIRECTA"] else "✗"
        print(f"  {flag} {row['MUNICIPIO']:<28} {row['VARIANZA_DIRECTA']:>12.6f} "
              f"{row['MSE_EBLUP']:>12.6f} {row['RATIO_MSE']:>8.4f} {row['MEJORA_MSE_PCT']:>8.2f}%")
    print()

    # ── GRÁFICAS DE VALIDACIÓN ────────────────────────────────────────────────
    # 2. Validación de las Varianzas de Muestreo (GVF)
    #    Dado que las varianzas directas suelen ser inestables, el modelo FH a menudo
    #    depende de una Función de Varianza Generalizada (GVF). Se valida el ajuste de
    #    este submodelo observando:
    #      - Residuos de la GVF: deben situarse aleatoriamente por encima y por debajo
    #        de cero sin patrones aparentes.
    #      - Poder predictivo: graficar las varianzas predichas frente a las observadas;
    #        los puntos deben situarse cerca de la línea de identidad (y=x).
    #
    # 3. Análisis del Efecto Suavizador (Residuales)
    #    Graficar los residuales del modelo FH (e_d = y_d - ŷ_d^eblup) frente a las
    #    estimaciones directas (y_d). Se debe observar:
    #      - Para valores pequeños de y_d, los residuales suelen ser negativos
    #        (el EBLUP "sube" la estimación).
    #      - Para valores grandes de y_d, los residuales suelen ser positivos
    #        (el EBLUP "baja" la estimación).
    #    Este comportamiento confirma que el modelo está corrigiendo los valores extremos
    #    inestables hacia la tendencia central.
    municipios = m["results_df"]["MUNICIPIO"].values

    def _annotate(ax, xs, ys, labels):
        for xi, yi, lab in zip(xs, ys, labels):
            ax.annotate(lab, (xi, yi), textcoords="offset points",
                        xytext=(4, 3), fontsize=7, color="dimgray")

    # GVF: ajuste log-lineal  log(Di) = a + b·log(Y)
    # Usamos solo dominios con Y > 0 y Di > 0
    mask_pos    = (Y > 0) & (Di > 0)
    log_Y_gvf   = np.log(Y[mask_pos])
    log_Di_gvf  = np.log(Di[mask_pos])
    slope_gvf, intercept_gvf, _, _, _ = stats.linregress(log_Y_gvf, log_Di_gvf)
    Di_gvf_pred = np.where(
        mask_pos,
        np.exp(intercept_gvf + slope_gvf * np.log(np.where(mask_pos, Y, 1))),
        np.nan
    )
    resid_gvf = Di - Di_gvf_pred  # residuos GVF: Di - D̂i

    # Residuos efecto suavizador: yd - EBLUP
    resid_fh = Y - m["eblup"]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle(
        f"Validación Modelo {i}: {' + '.join(m['covars'])}",
        fontsize=13, fontweight="bold"
    )

    # --- Gráfica 1: Residuos GVF ---
    ax = axes[0]
    ax.axhline(0, color="red", linestyle="--", linewidth=1.2, label="Referencia 0")
    ax.scatter(Y, resid_gvf, color="steelblue", edgecolors="white",
               s=70, alpha=0.85, zorder=3)
    _annotate(ax, Y, resid_gvf, municipios)
    ax.set_xlabel("Estimación directa Yd  (%)", fontsize=10)
    ax.set_ylabel("Residuo GVF  (Di − D̂i)", fontsize=10)
    ax.set_title("Residuos de la GVF", fontsize=11, fontweight="bold")
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    ax.legend(fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.5)

    # --- Gráfica 2: Di predicha vs Di observada (línea identidad) ---
    ax = axes[1]
    all_d   = np.concatenate([Di[mask_pos], Di_gvf_pred[mask_pos]])
    d_range = [all_d.min() * 0.9, all_d.max() * 1.1]
    ax.plot(d_range, d_range, "r--", linewidth=1.4, label="y = x")
    ax.scatter(Di, Di_gvf_pred, color="steelblue", edgecolors="white",
               s=70, alpha=0.85, zorder=3)
    _annotate(ax, Di, Di_gvf_pred, municipios)
    ax.set_xlim(d_range)
    ax.set_ylim(d_range)
    ax.set_xlabel("Varianza directa observada (Di)", fontsize=10)
    ax.set_ylabel("Varianza GVF predicha (D̂i)", fontsize=10)
    ax.set_title("GVF: Predicha vs Observada", fontsize=11, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.5)

    # --- Gráfica 3: Efecto suavizador (residuo FH vs estimación directa) ---
    ax = axes[2]
    ax.axhline(0, color="red", linestyle="--", linewidth=1.2, label="Referencia 0")
    colors_fh = ["tomato" if r > 0 else "steelblue" for r in resid_fh]
    ax.scatter(Y, resid_fh, c=colors_fh, edgecolors="white", s=70, alpha=0.85, zorder=3)
    _annotate(ax, Y, resid_fh, municipios)
    ax.set_xlabel("Estimación directa Yd  (%)", fontsize=10)
    ax.set_ylabel("Residuo FH  (Yd − EBLUP)", fontsize=10)
    ax.set_title("Efecto suavizador del EBLUP", fontsize=11, fontweight="bold")
    # Leyenda manual
    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="tomato",   markersize=8, label="EBLUP < Yd  (suaviza hacia abajo)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="steelblue", markersize=8, label="EBLUP > Yd  (suaviza hacia arriba)"),
    ]
    ax.legend(handles=legend_handles, fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    display(fig)
    plt.close(fig)
    print()

# -----------------------------------------------------------------------------
# 6. RESUMEN COMPARATIVO (solo cuando hay más de un subconjunto)
# -----------------------------------------------------------------------------
if len(models) > 1:

    # ── TABLA 1: DIAGNÓSTICOS ────────────────────────────────────────────────
    W = 105
    print("\n" + "=" * W)
    print("TABLA 1 — DIAGNÓSTICOS POR MODELO")
    print("=" * W)

    hdr = (f"{'Modelo':<8} {'Covariables':<42} {'R²':>6} {'μ_res':>7} {'σ_res':>7} "
           f"{'SW_p':>7} {'ΔCV_pp':>7} {'γ̄':>7} "
           f"{'%Mej_MSE':>9} {'RatioMSE':>9} {'Wil_p':>7}")
    print(hdr)
    print("-" * W)
    for i, m in enumerate(models, 1):
        covs   = " + ".join(m["covars"])[:41]
        sw_ok  = "✓" if m["sw_pval"] > 0.05 else "✗"
        wil_ok = "✓" if m["wil_pval"] < 0.05 else "✗"
        print(
            f"M{i:<7} {covs:<42} {m['r2']:>6.4f} "
            f"{m['residuals'].mean():>7.4f} {m['residuals'].std():>7.4f} "
            f"{sw_ok}{m['sw_pval']:>5.3f} "
            f"{m['results_df']['MEJORA_CV_PCT'].mean():>7.2f} "
            f"{m['gamma_i'].mean():>7.4f} "
            f"{m['dominios_mejoran']*100:>8.1f}% "
            f"{m['mse_ratio'].mean():>9.4f} "
            f"{wil_ok}{m['wil_pval']:>5.3f}"
        )
    print("-" * W)
    print("  SW_p  : p-valor Shapiro-Wilk (✓ >0.05 → normalidad)    "
          "Wil_p : p-valor Wilcoxon Di>MSE_EBLUP (✓ <0.05 → reducción significativa)")
    print("  %Mej_MSE : % dominios con MSE_EBLUP < Di               "
          "RatioMSE : Di/MSE_EBLUP medio (>1 indica ganancia)")

    # ── TABLA 2: SELECCIÓN DE MODELO ────────────────────────────────────────
    print("\n" + "=" * W)
    print("TABLA 2 — SELECCIÓN DE MODELO (AIC / BIC / MSE medio)")
    print("=" * W)

    best_aic = min(m["aic"]                              for m in models)
    best_bic = min(m["bic"]                              for m in models)
    best_mse = min(m["results_df"]["MSE_EBLUP"].mean()   for m in models)

    # Ranking compuesto: suma de posiciones en AIC, BIC y MSE
    def _rank_by(key_fn):
        return {i: r for r, (i, _) in enumerate(
            sorted(enumerate(models), key=lambda x: key_fn(x[1])), 1)}

    rk_aic = _rank_by(lambda m: m["aic"])
    rk_bic = _rank_by(lambda m: m["bic"])
    rk_mse = _rank_by(lambda m: m["results_df"]["MSE_EBLUP"].mean())

    hdr2 = (f"{'Rk':<4} {'Modelo':<8} {'Covariables':<42} "
            f"{'AIC':>10} {'ΔAIC':>7} {'BIC':>10} {'ΔBIC':>7} "
            f"{'MSE_med':>9} {'ΔMSE':>9}")
    print(hdr2)
    print("-" * W)

    combined = sorted(
        enumerate(models, 1),
        key=lambda x: rk_aic[x[0]-1] + rk_bic[x[0]-1] + rk_mse[x[0]-1]
    )
    for rank, (idx, m) in enumerate(combined, 1):
        mse_med = m["results_df"]["MSE_EBLUP"].mean()
        flag    = " ←" if rank == 1 else ""
        print(
            f"{rank:<4} M{idx:<7} {' + '.join(m['covars'])[:41]:<42} "
            f"{m['aic']:>10.4f} {m['aic']-best_aic:>7.4f} "
            f"{m['bic']:>10.4f} {m['bic']-best_bic:>7.4f} "
            f"{mse_med:>9.6f} {mse_med-best_mse:>9.6f}{flag}"
        )
    print("-" * W)
    print("  Ranking por suma de posiciones en AIC + BIC + MSE_med")
    print("  ΔAIC/ΔBIC: < 2 equivalentes · 2–7 moderado · > 10 sustancial")

# -----------------------------------------------------------------------------
# 7. EXPORTAR RESULTADOS
# -----------------------------------------------------------------------------
# Si hay varios modelos, se exporta el de menor AIC+BIC+MSE (ranking compuesto); si hay uno solo, ese mismo.
if len(models) > 1:
    def _score(m):
        return (sorted(models, key=lambda x: x["aic"]).index(m) +
                sorted(models, key=lambda x: x["bic"]).index(m) +
                sorted(models, key=lambda x: x["results_df"]["MSE_EBLUP"].mean()).index(m))
    best_model = min(models, key=_score)
    print(f"\nExportando resultados del mejor modelo: {' + '.join(best_model['covars'])}")
else:
    best_model = models[0]

spark_df = spark.createDataFrame(best_model["results_df"])
spark_df.write.mode("overwrite").option("mergeSchema","true").saveAsTable("tesis.modelo.fay_herriot_resultados")

# -----------------------------------------------------------------------------
# 8. PREDICCIÓN SINTÉTICA PARA DOMINIOS SIN ESTIMACIÓN DIRECTA
# -----------------------------------------------------------------------------
# Para municipios donde NO existe estimación directa (Y ni Di), el EBLUP
# no puede calcularse. El predictor óptimo es el estimador sintético:
#   ŷ_d = X_d' β̂
# que usa únicamente las covariables del dominio y los coeficientes del modelo
# ganador. No hay contracción (γ=0) porque no hay varianza de muestreo.
#
# Reemplaza la tabla de abajo por tu fuente real de municipios sin encuesta.
# Debe contener las mismas covariables que best_model["covars"].
# -----------------------------------------------------------------------------

df_new = (
    spark.table("tesis.modelo.municipios_sin_encuesta")   # <-- ajusta la tabla
    .toPandas()
)
# Si prefieres CSV local descomenta:
# df_new = pd.read_csv("municipios_sin_encuesta.csv")

covars_best = best_model["covars"]
beta_best   = best_model["beta_hat"]

# Validar que las covariables existen
missing_cols = [c for c in covars_best if c not in df_new.columns]
if missing_cols:
    raise ValueError(f"Faltan columnas en los datos nuevos: {missing_cols}")

X_new          = np.column_stack([np.ones(len(df_new))] + [df_new[c].values for c in covars_best])
y_sintetico    = X_new @ beta_best

# Incertidumbre: sólo el componente g2i (varianza del predictor sintético)
#   Var(ŷ_d) = x_d' Cov(β̂) x_d, reconstruyendo XtViX del modelo ganador.
A_best        = best_model["A_hat"]
Vi_in         = 1.0 / (df[SE_col].values**2 + A_best)
X_in          = np.column_stack([np.ones(n)] + [df[c].values for c in covars_best])
XtViX         = (X_in.T * Vi_in) @ X_in
cov_beta_best = np.linalg.inv(XtViX)

var_beta       = np.array([X_new[i] @ cov_beta_best @ X_new[i] for i in range(len(df_new))])
var_sintetico  = var_beta + A_best        # incertidumbre β̂ + efecto aleatorio no observado
rmse_sintetico = np.sqrt(var_sintetico)
cv_sintetico   = 100 * rmse_sintetico / np.abs(y_sintetico)

# Tabla de resultados
id_cols = ["PER", "MES", "DEPARTAMENTO", "MUNICIPIO"]
id_cols = [c for c in id_cols if c in df_new.columns]   # solo los que existan

df_pred = df_new[id_cols].copy()
df_pred["PRED_SINTETICO"]   = y_sintetico.round(4)
df_pred["RMSE_SINTETICO"]   = rmse_sintetico.round(4)
df_pred["CV_SINTETICO_PCT"] = cv_sintetico.round(2)
df_pred["TIPO"]             = "SINTETICO"   # distingue de filas con EBLUP

print(f"\nPredicciones sintéticas para {len(df_pred)} dominios sin encuesta:")
print(df_pred.to_string(index=False))

spark_df_pred = spark.createDataFrame(df_pred)
spark_df_pred.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(
    "tesis.modelo.fay_herriot_prediccion_sintetica"
)
