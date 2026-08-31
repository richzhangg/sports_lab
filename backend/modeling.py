"""
Model fitting, evaluation and out-of-sample validation.

Uses statsmodels (established, peer-reviewed implementations) — no statistical
algorithm is implemented from scratch here.

Model families
--------------
  linear   : OLS on the chosen outcome.
  poisson  : Poisson GLM (log link) on the count outcome, with log(population)
             offset so coefficients describe a representation *rate*.
  negbin   : Negative Binomial (NB2) regression, same offset. Estimates the
             overdispersion parameter alpha.
  zip      : Zero-Inflated Poisson — a logit "structural zero" component plus a
             Poisson count component. For outcomes with many more zeros than a
             plain count model expects.
  zinb     : Zero-Inflated Negative Binomial — same, with overdispersion.

Validation
----------
Training years and the validation year are kept strictly separate: parameters
are estimated on training rows only; every "test" metric uses the held-out
validation year exclusively. Optionally the run also reports:
  * k-fold cross-validation over the training rows (fit stability), and
  * leave-one-year-out CV across every available year (temporal generalization).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.count_model import (
    ZeroInflatedNegativeBinomialP, ZeroInflatedPoisson,
)

warnings.simplefilter("ignore")
np.seterr(all="ignore")

from data import get_dataframe

COUNT_OUTCOME = "d1_players"
OFFSET_COL = "population"
FAMILIES = ["linear", "poisson", "negbin", "zip", "zinb", "custom"]
COUNT_FAMILIES = {"poisson", "negbin", "zip", "zinb"}


class ModelError(ValueError):
    pass


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _standardize(train: pd.DataFrame, test: pd.DataFrame, cols: list[str]):
    """z-score predictors using TRAIN statistics only (no leakage)."""
    means = train[cols].mean()
    stds = train[cols].std(ddof=0).replace(0, 1.0)
    return (train[cols] - means) / stds, (test[cols] - means) / stds, means, stds


def _poisson_deviance(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    mu = np.clip(mu, 1e-9, None)
    term = np.where(y > 0, y * np.log(y / mu), 0.0)
    return 2.0 * (term - (y - mu))


def _metrics(y: np.ndarray, pred: np.ndarray, family: str, k_params: int) -> dict:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    resid = y - pred
    n = len(y)
    out = {
        "n": int(n),
        "rmse": float(np.sqrt(np.mean(resid ** 2))),
        "mae": float(np.mean(np.abs(resid))),
        "mean_error_bias": float(np.mean(resid)),
    }
    # R^2 vs mean of y (works for any family, on the response scale)
    ss_tot = np.sum((y - y.mean()) ** 2)
    out["r2_response"] = float(1 - np.sum(resid ** 2) / ss_tot) if ss_tot > 0 else None
    if family in COUNT_FAMILIES:
        dev = _poisson_deviance(y, pred)
        out["mean_poisson_deviance"] = float(np.mean(dev))
        # null (intercept = mean) deviance for a pseudo-R^2 on the deviance scale
        null_dev = _poisson_deviance(y, np.full_like(y, y.mean()))
        out["deviance_r2"] = float(1 - dev.sum() / null_dev.sum()) if null_dev.sum() > 0 else None
    if np.std(pred) > 0 and np.std(y) > 0:
        out["pearson_corr"] = float(np.corrcoef(y, pred)[0, 1])
    else:
        out["pearson_corr"] = None
    return out


def _residual_table(df: pd.DataFrame, y: np.ndarray, pred: np.ndarray, family: str) -> list[dict]:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    raw = y - pred
    if family in COUNT_FAMILIES:
        pearson = raw / np.sqrt(np.clip(pred, 1e-9, None))
        dev_sign = np.sign(raw)
        dev = dev_sign * np.sqrt(np.clip(_poisson_deviance(y, pred), 0, None))
    else:
        sd = np.std(raw) or 1.0
        pearson = raw / sd
        dev = pearson
    rows = []
    for i in range(len(df)):
        rows.append({
            "community_id": str(df.iloc[i]["community_id"]),
            "community_name": str(df.iloc[i]["community_name"]),
            "state": str(df.iloc[i]["state"]),
            "observed": float(y[i]),
            "predicted": float(pred[i]),
            "raw_residual": float(raw[i]),
            "pearson_residual": float(pearson[i]),
            "deviance_residual": float(dev[i]),
        })
    return rows


def _coef_table(names, params, bse, pvalues, conf, family) -> list[dict]:
    rows = []
    for i, nm in enumerate(names):
        row = {
            "term": nm,
            "estimate": float(params[i]),
            "std_error": float(bse[i]) if bse is not None and np.isfinite(bse[i]) else None,
            "p_value": float(pvalues[i]) if pvalues is not None and np.isfinite(pvalues[i]) else None,
            "ci_low": float(conf[i][0]) if conf is not None else None,
            "ci_high": float(conf[i][1]) if conf is not None else None,
        }
        if family in COUNT_FAMILIES and nm != "alpha":
            row["rate_ratio"] = float(np.exp(params[i]))
            if conf is not None:
                row["rate_ratio_ci_low"] = float(np.exp(conf[i][0]))
                row["rate_ratio_ci_high"] = float(np.exp(conf[i][1]))
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# core
# --------------------------------------------------------------------------- #
def _estimate_alpha(y, mu):
    """Cameron & Trivedi auxiliary-OLS estimate of NB2 overdispersion."""
    mu = np.clip(np.asarray(mu, dtype=float), 1e-6, None)
    aux = ((y - mu) ** 2 - y) / mu
    a = sm.OLS(aux, mu).fit().params[0]
    return float(np.clip(a, 1e-6, 50.0))


def _fit_family(family, y, X, offset):
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    if family == "linear":
        return sm.OLS(y, X).fit()
    if family == "poisson":
        return sm.GLM(y, X, family=sm.families.Poisson(), offset=offset).fit()
    if family == "negbin":
        # Stable two-step NB2: Poisson fit -> estimate alpha -> NB GLM.
        poi = sm.GLM(y, X, family=sm.families.Poisson(), offset=offset).fit()
        alpha = _estimate_alpha(y, poi.predict(X, offset=offset))
        res = sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=alpha),
                     offset=offset).fit()
        res._estimated_alpha = alpha
        return res
    if family in ("zip", "zinb"):
        # inflation ("structural zero") component: intercept only — keeps it
        # identifiable and interpretable ("baseline odds a community structurally
        # produces zero D1 players").
        infl = np.ones((len(y), 1))
        Model = ZeroInflatedPoisson if family == "zip" else ZeroInflatedNegativeBinomialP
        kw = {"exog_infl": infl, "offset": offset, "inflation": "logit"}
        if family == "zinb":
            kw["p"] = 2
        res = Model(y, X, **kw).fit(method="bfgs", maxiter=200, disp=0)
        if not getattr(res.mle_retvals, "get", lambda *_: True)("converged", True):
            res = Model(y, X, **kw).fit(method="nm", maxiter=3000, disp=0)
        return res
    raise ModelError(f"unknown family '{family}'")


def _predict(family, res, X, offset):
    X = np.asarray(X, dtype=float)
    if family == "linear":
        return np.asarray(res.predict(X))
    if family in ("zip", "zinb"):
        infl = np.ones((len(X), 1))
        return np.asarray(res.predict(X, exog_infl=infl, offset=offset, which="mean"))
    return np.asarray(res.predict(X, offset=offset))


def _design(dfrows: pd.DataFrame, predictors, means=None, stds=None):
    X = dfrows[predictors].astype(float)
    if means is not None:
        X = (X - means) / stds
    return sm.add_constant(X, has_constant="add")


def _primary_metric_key(family: str) -> str:
    return "mean_poisson_deviance" if family in COUNT_FAMILIES else "rmse"


def _fit_score(family, tr, te, predictors, outcome, standardize):
    """Fit on `tr`, score on `te`; returns (train_metrics, test_metrics) or None."""
    is_count = family in COUNT_FAMILIES
    means = stds = None
    if standardize:
        means = tr[predictors].mean()
        stds = tr[predictors].std(ddof=0).replace(0, 1.0)
    Xtr, Xte = _design(tr, predictors, means, stds), _design(te, predictors, means, stds)
    otr = np.log(tr[OFFSET_COL].astype(float) / 1e5) if is_count else None
    ote = np.log(te[OFFSET_COL].astype(float) / 1e5) if is_count else None
    ytr = tr[outcome].astype(float).to_numpy()
    yte = te[outcome].astype(float).to_numpy()
    try:
        res = _fit_family(family, ytr, Xtr, otr)
        ptr, pte = _predict(family, res, Xtr, otr), _predict(family, res, Xte, ote)
    except Exception:  # noqa: BLE001
        return None
    if not np.all(np.isfinite(pte)):
        return None
    return _metrics(ytr, ptr, family, Xtr.shape[1]), _metrics(yte, pte, family, Xtr.shape[1])


def _agg(scores: list[dict], keys) -> dict:
    out = {}
    for key in keys:
        vals = [s[key] for s in scores if s.get(key) is not None and np.isfinite(s[key])]
        if vals:
            out[key] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals)), "n": len(vals)}
    return out


def _kfold_cv(train: pd.DataFrame, predictors, family, outcome, standardize, k=5, seed=0):
    idx = np.arange(len(train))
    rng = np.random.default_rng(seed)
    rng.shuffle(idx)
    folds = np.array_split(idx, k)
    metric_keys = ["rmse", "mae", "r2_response", "pearson_corr"]
    if family in COUNT_FAMILIES:
        metric_keys += ["mean_poisson_deviance", "deviance_r2"]
    tr_scores, te_scores, per_fold = [], [], []
    for i in range(k):
        te_idx = folds[i]
        tr_idx = np.concatenate([folds[j] for j in range(k) if j != i])
        r = _fit_score(family, train.iloc[tr_idx], train.iloc[te_idx],
                       predictors, outcome, standardize)
        if r is None:
            continue
        tr_scores.append(r[0]); te_scores.append(r[1])
        per_fold.append({"fold": i + 1, "n_test": len(te_idx),
                         **{key: r[1].get(key) for key in metric_keys}})
    if not te_scores:
        return None
    return {
        "scheme": f"{k}-fold (random) over training rows",
        "k": k,
        "held_out": _agg(te_scores, metric_keys),
        "in_fold": _agg(tr_scores, metric_keys),
        "per_fold": per_fold,
    }


def _loyo_cv(df: pd.DataFrame, years, predictors, family, outcome, standardize):
    metric_keys = ["rmse", "mae", "r2_response", "pearson_corr"]
    if family in COUNT_FAMILIES:
        metric_keys += ["mean_poisson_deviance", "deviance_r2"]
    per_year, te_scores = [], []
    for y in years:
        tr = df[df["year"] != y]
        te = df[df["year"] == y]
        if len(tr) == 0 or len(te) == 0:
            continue
        r = _fit_score(family, tr, te, predictors, outcome, standardize)
        if r is None:
            continue
        te_scores.append(r[1])
        per_year.append({"year": int(y), "n_test": int(len(te)),
                         **{key: r[1].get(key) for key in metric_keys}})
    if not te_scores:
        return None
    return {
        "scheme": "leave-one-year-out (each year held out once, model refit on the rest)",
        "held_out": _agg(te_scores, metric_keys),
        "per_year": per_year,
    }


def _run_custom_equation(df, outcome, equation, variables, train_years, test_year,
                         include_baseline):
    """
    Evaluate a user-typed equation as the prediction. Nothing is fitted — the
    student supplies the whole formula and all constants; we compute it per
    community and compare to the actual NCAA counts.
    """
    import equation as eqmod

    if not equation.strip():
        raise ModelError("enter an equation")
    if not variables:
        raise ModelError("define at least one variable (e.g. x = median income)")
    for sym, col in variables.items():
        if col not in df.columns:
            raise ModelError(f"variable '{sym}' is mapped to unknown column '{col}'")
    try:
        eqmod.validate(equation, set(variables))
    except eqmod.EquationError as e:
        raise ModelError(str(e))

    metric_family = "poisson" if outcome == COUNT_OUTCOME else "linear"
    train = df[df["year"].isin(train_years)].copy().reset_index(drop=True)
    test = df[df["year"] == test_year].copy().reset_index(drop=True)
    if len(train) == 0 or len(test) == 0:
        raise ModelError("no rows for the chosen train/validation years")

    def _cols(rows):
        return {sym: rows[col].astype(float).to_numpy() for sym, col in variables.items()}

    try:
        pred_tr = eqmod.evaluate(equation, _cols(train))
        pred_te = eqmod.evaluate(equation, _cols(test))
    except eqmod.EquationError as e:
        raise ModelError(str(e))

    ytr = train[outcome].astype(float).to_numpy()
    yte = test[outcome].astype(float).to_numpy()
    if not np.all(np.isfinite(pred_te)):
        raise ModelError("equation produced non-finite values (division by zero, "
                         "log of a negative number, …) on the validation year")
    # counts can't be negative — clip for count-scale error metrics, but report it
    neg_share = float(np.mean(pred_te < 0)) if metric_family == "poisson" else 0.0
    if metric_family == "poisson":
        pred_tr = np.clip(pred_tr, 0, None)
        pred_te = np.clip(pred_te, 0, None)

    train_metrics = _metrics(ytr, pred_tr, metric_family, 0)
    test_metrics = _metrics(yte, pred_te, metric_family, 0)

    base_pred_tr = np.full_like(ytr, ytr.mean())
    base_pred_te = np.full_like(yte, ytr.mean())
    baseline = {
        "description": "Intercept-only baseline (predict the training-year mean count)",
        "train_metrics": _metrics(ytr, base_pred_tr, metric_family, 1),
        "test_metrics": _metrics(yte, base_pred_te, metric_family, 1),
    }

    per_year = []
    for y in sorted(int(v) for v in df["year"].unique()):
        rows = df[df["year"] == y]
        if len(rows) == 0:
            continue
        p = np.clip(eqmod.evaluate(equation, _cols(rows)), 0, None) if metric_family == "poisson" \
            else eqmod.evaluate(equation, _cols(rows))
        m = _metrics(rows[outcome].astype(float).to_numpy(), p, metric_family, 0)
        per_year.append({"year": int(y), "n_test": int(len(rows)),
                         "rmse": m["rmse"], "mae": m["mae"],
                         "mean_poisson_deviance": m.get("mean_poisson_deviance"),
                         "r2_response": m.get("r2_response")})

    result = {
        "spec": {
            "outcome": outcome,
            "predictors": list(variables.values()),
            "family": "custom",
            "equation": equation,
            "variables": variables,
            "train_years": sorted(train_years),
            "test_year": test_year,
            "standardize": False,
            "n_train": int(len(train)),
            "n_test": int(len(test)),
        },
        "equation": {
            "text": equation,
            "bindings": [{"symbol": s, "column": c} for s, c in variables.items()],
            "note": "Nothing was fitted — this is exactly the formula you typed, "
                    "evaluated for every community.",
            "negative_prediction_share": neg_share,
        },
        "coefficients": [],
        "diagnostics": {
            "fitted_parameters": 0,
            "evaluator": "numexpr (arithmetic only, sandboxed)",
        },
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "predicted_vs_observed": [
            {"observed": float(yte[i]), "predicted": float(pred_te[i]),
             "community_name": str(test.iloc[i]["community_name"]),
             "state": str(test.iloc[i]["state"])}
            for i in range(len(test))
        ],
        "residuals": _residual_table(test, yte, pred_te, metric_family),
        "geo_distribution": _geo_summary(test, yte, pred_te),
        "overfitting": _overfitting_signal(train_metrics, test_metrics, metric_family),
    }
    if include_baseline:
        result["baseline"] = baseline
        b = baseline["test_metrics"]
        result["vs_baseline"] = {
            "rmse_improvement_pct": _pct_impr(b["rmse"], test_metrics["rmse"]),
            "mae_improvement_pct": _pct_impr(b["mae"], test_metrics["mae"]),
        }
        if "mean_poisson_deviance" in b:
            result["vs_baseline"]["poisson_deviance_improvement_pct"] = _pct_impr(
                b["mean_poisson_deviance"], test_metrics["mean_poisson_deviance"])
    result["cross_validation"] = {
        "primary_metric": _primary_metric_key(metric_family),
        "leave_one_year_out": {
            "scheme": "equation evaluated on each year (no refitting — the formula is fixed)",
            "held_out": _agg([{k: y[k] for k in ("rmse", "mae", "mean_poisson_deviance", "r2_response")}
                              for y in per_year],
                             ["rmse", "mae", "mean_poisson_deviance", "r2_response"]),
            "per_year": per_year,
        },
    }
    return result


def run_experiment(
    outcome: str,
    predictors: list[str],
    family: str,
    train_years: list[int],
    test_year: int,
    standardize: bool = True,
    include_baseline: bool = True,
    cv_folds: int = 0,
    equation: str | None = None,
    variables: dict[str, str] | None = None,
) -> dict:
    if family not in FAMILIES:
        raise ModelError(f"family must be one of {FAMILIES}")
    df = get_dataframe()
    if outcome not in df.columns:
        raise ModelError(f"unknown outcome '{outcome}'")
    if test_year in train_years:
        raise ModelError("validation year must not be in the training years")
    if not train_years:
        raise ModelError("select at least one training year")

    if family == "custom":
        return _run_custom_equation(df, outcome, equation or "", variables or {},
                                    train_years, test_year, include_baseline)

    if not predictors:
        raise ModelError("select at least one predictor")
    for p in predictors:
        if p not in df.columns:
            raise ModelError(f"unknown predictor '{p}'")

    is_count = family in COUNT_FAMILIES
    if is_count and outcome != COUNT_OUTCOME:
        raise ModelError(
            f"Count models (Poisson / Negative Binomial / zero-inflated) require the "
            f"count outcome '{COUNT_OUTCOME}'. Use the linear family for '{outcome}'."
        )

    train = df[df["year"].isin(train_years)].copy().reset_index(drop=True)
    test = df[df["year"] == test_year].copy().reset_index(drop=True)
    if len(train) == 0 or len(test) == 0:
        raise ModelError("no rows for the chosen train/validation years")

    Xtr_raw, Xte_raw = train[predictors].astype(float), test[predictors].astype(float)
    if standardize:
        Xtr_s, Xte_s, _, _ = _standardize(train, test, predictors)
    else:
        Xtr_s, Xte_s = Xtr_raw, Xte_raw

    Xtr = sm.add_constant(Xtr_s, has_constant="add")
    Xte = sm.add_constant(Xte_s, has_constant="add")

    offset_tr = np.log(train[OFFSET_COL].astype(float) / 100_000.0) if is_count else None
    offset_te = np.log(test[OFFSET_COL].astype(float) / 100_000.0) if is_count else None

    ytr = train[outcome].astype(float).to_numpy()
    yte = test[outcome].astype(float).to_numpy()

    try:
        res = _fit_family(family, ytr, Xtr, offset_tr)
    except Exception as e:  # noqa: BLE001
        raise ModelError(f"model failed to converge: {e}")

    pred_tr = _predict(family, res, Xtr, offset_tr)
    pred_te = _predict(family, res, Xte, offset_te)

    # coefficient inference
    names = list(Xtr.columns)
    k = len(names)
    params = np.asarray(res.params)
    try:
        conf = np.asarray(res.conf_int())
    except Exception:  # noqa: BLE001
        conf = None
    bse = np.asarray(res.bse) if hasattr(res, "bse") else None
    pvalues = np.asarray(res.pvalues) if hasattr(res, "pvalues") else None

    if family in ("zip", "zinb"):
        # statsmodels order: [inflation params (1, intercept only)] + [count params (k)] + [alpha?]
        sl = slice(1, 1 + k)
        params = params[sl]
        conf = conf[sl] if conf is not None else None
        bse = bse[sl] if bse is not None else None
        pvalues = pvalues[sl] if pvalues is not None else None

    coef_names = names[:]
    train_metrics = _metrics(ytr, pred_tr, family, k)
    test_metrics = _metrics(yte, pred_te, family, k)

    # --- fit diagnostics ------------------------------------------------
    diagnostics = {
        "log_likelihood": float(res.llf) if hasattr(res, "llf") else None,
        "aic": float(res.aic) if hasattr(res, "aic") else None,
        "bic": float(res.bic) if hasattr(res, "bic") and np.isfinite(res.bic) else None,
        "n_params": int(k),
        "df_resid": float(getattr(res, "df_resid", np.nan)),
        "converged": bool(getattr(res, "converged", True)) if family != "linear" else True,
    }
    if family in COUNT_FAMILIES:
        pearson_chi2 = float(np.sum(((ytr - pred_tr) ** 2) / np.clip(pred_tr, 1e-9, None)))
        dfres = float(getattr(res, "df_resid", len(ytr) - k)) or 1.0
        diagnostics["pearson_chi2"] = pearson_chi2
        diagnostics["dispersion_ratio"] = pearson_chi2 / dfres
        diagnostics["dispersion_hint"] = (
            "≈1 ok; ≫1 overdispersed (prefer Negative Binomial)"
        )
    if family == "negbin":
        diagnostics["alpha_overdispersion"] = getattr(res, "_estimated_alpha", None)
    if family in ("zip", "zinb"):
        try:
            p_infl = float(1 / (1 + np.exp(-res.params[0])))  # logit intercept -> P(structural zero)
            diagnostics["structural_zero_prob"] = p_infl
        except Exception:  # noqa: BLE001
            pass
        diagnostics["observed_zero_share"] = float(np.mean(ytr == 0))
        if family == "zinb":
            try:
                diagnostics["alpha_overdispersion"] = float(res.params[-1])
            except Exception:  # noqa: BLE001
                pass
    if family == "linear":
        diagnostics["r_squared"] = float(res.rsquared)
        diagnostics["adj_r_squared"] = float(res.rsquared_adj)

    result = {
        "spec": {
            "outcome": outcome,
            "predictors": predictors,
            "family": family,
            "train_years": sorted(train_years),
            "test_year": test_year,
            "standardize": standardize,
            "n_train": int(len(train)),
            "n_test": int(len(test)),
        },
        "coefficients": _coef_table(coef_names, params, bse, pvalues, conf, family),
        "diagnostics": diagnostics,
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "predicted_vs_observed": [
            {"observed": float(yte[i]), "predicted": float(pred_te[i]),
             "community_name": str(test.iloc[i]["community_name"]),
             "state": str(test.iloc[i]["state"])}
            for i in range(len(test))
        ],
        "residuals": _residual_table(test, yte, pred_te, family),
        "geo_distribution": _geo_summary(test, yte, pred_te),
    }

    if include_baseline:
        result["baseline"] = _baseline(outcome, family, ytr, yte, train, test,
                                       offset_tr, offset_te, is_count)
        # skill improvement vs baseline on the held-out year
        b = result["baseline"]["test_metrics"]
        result["vs_baseline"] = {
            "rmse_improvement_pct": _pct_impr(b["rmse"], test_metrics["rmse"]),
            "mae_improvement_pct": _pct_impr(b["mae"], test_metrics["mae"]),
        }
        if "mean_poisson_deviance" in b and "mean_poisson_deviance" in test_metrics:
            result["vs_baseline"]["poisson_deviance_improvement_pct"] = _pct_impr(
                b["mean_poisson_deviance"], test_metrics["mean_poisson_deviance"])

    # overfitting signal: gap between train and test
    result["overfitting"] = _overfitting_signal(train_metrics, test_metrics, family)

    # --- cross-validation (optional) -----------------------------------
    if cv_folds and cv_folds >= 2:
        cv = {}
        kf = _kfold_cv(train, predictors, family, outcome, standardize, k=int(cv_folds))
        if kf:
            cv["kfold"] = kf
        all_years = sorted(int(y) for y in df["year"].unique())
        if len(all_years) >= 3:
            loyo = _loyo_cv(df[df["year"].isin(all_years)], all_years,
                            predictors, family, outcome, standardize)
            if loyo:
                cv["leave_one_year_out"] = loyo
        if cv:
            cv["primary_metric"] = _primary_metric_key(family)
            result["cross_validation"] = cv

    return result


def _pct_impr(baseline_val, model_val):
    if baseline_val in (None, 0) or model_val is None:
        return None
    return float((baseline_val - model_val) / baseline_val * 100.0)


def _baseline(outcome, family, ytr, yte, train, test, offset_tr, offset_te, is_count):
    """Intercept-only model of the same family."""
    Xtr = np.ones((len(ytr), 1))
    Xte = np.ones((len(yte), 1))
    try:
        res = _fit_family(family, ytr, Xtr, offset_tr)
        pred_tr = _predict(family, res, Xtr, offset_tr)
        pred_te = _predict(family, res, Xte, offset_te)
    except Exception:  # noqa: BLE001
        # fallback: plain mean
        pred_tr = np.full_like(ytr, ytr.mean())
        pred_te = np.full_like(yte, ytr.mean())
    return {
        "description": f"Intercept-only {family} model (no predictors)"
                       + (" with log(population) offset" if is_count else ""),
        "train_metrics": _metrics(ytr, pred_tr, family, 1),
        "test_metrics": _metrics(yte, pred_te, family, 1),
    }


def _overfitting_signal(train_m, test_m, family):
    def gap(key):
        a, b = train_m.get(key), test_m.get(key)
        if a in (None, 0) or b is None:
            return None
        return float((b - a) / abs(a) * 100.0)
    primary = "mean_poisson_deviance" if family in COUNT_FAMILIES else "rmse"
    g = gap(primary)
    return {
        "primary_metric": primary,
        "train_value": train_m.get(primary),
        "test_value": test_m.get(primary),
        "test_minus_train_pct": g,
        "flag": bool(g is not None and g > 25),
        "note": "Large positive gap = validation error much worse than training "
                "error = likely overfitting.",
    }


def _geo_summary(df, y, pred):
    tmp = df[["state"]].copy()
    tmp["observed"] = y
    tmp["predicted"] = pred
    g = tmp.groupby("state").agg(
        observed=("observed", "sum"),
        predicted=("predicted", "sum"),
        n=("observed", "size"),
    ).reset_index()
    g["residual"] = g["observed"] - g["predicted"]
    return g.sort_values("observed", ascending=False).to_dict(orient="records")
