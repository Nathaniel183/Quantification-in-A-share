import numpy as np
import pandas as pd
from scipy.optimize import minimize


def mvw(pred: pd.Series, rsk: dict, lam: float) -> pd.Series:
    """
    Mean-Variance utility optimizer (long-only):
        maximize  mu^T w - lam * w^T Sigma w
        s.t.      w >= 0, sum(w) = 1

    Inputs:
        pred: pd.Series (preferred) with MultiIndex (code, date) or (date, code),
              OR a single-column pd.DataFrame with the same MultiIndex.
        rsk:  dict[date] -> pd.DataFrame covariance Sigma, index=code, columns=code
        lam:  risk aversion (risk penalty) coefficient, lam >= 0

    Returns:
        pd.Series with MultiIndex (date, code), name='w'
    """
    if lam < 0:
        raise ValueError("lam must be >= 0")

    # ---- make pred a real 1D Series ----
    if isinstance(pred, pd.DataFrame):
        if pred.shape[1] != 1:
            raise ValueError("pred is a DataFrame; it must have exactly 1 column.")
        pred = pred.iloc[:, 0]
    elif not isinstance(pred, pd.Series):
        raise ValueError("pred must be a pd.Series or a single-column pd.DataFrame.")

    if not isinstance(pred.index, pd.MultiIndex) or pred.index.nlevels != 2:
        raise ValueError("pred must have a 2-level MultiIndex (code,date) or (date,code).")

    # --- Infer which level is date vs code (robust to order) ---
    lv0 = pred.index.get_level_values(0)
    lv1 = pred.index.get_level_values(1)

    def _is_yyyymm_like(x) -> bool:
        s = str(x)
        return len(s) == 6 and s.isdigit()

    # sample to avoid huge loops
    k0 = min(len(lv0), 2000)
    k1 = min(len(lv1), 2000)
    lv0_date_ratio = float(np.mean([_is_yyyymm_like(x) for x in lv0[:k0]]))
    lv1_date_ratio = float(np.mean([_is_yyyymm_like(x) for x in lv1[:k1]]))

    if lv0_date_ratio > lv1_date_ratio:
        date_level, code_level = 0, 1
    else:
        date_level, code_level = 1, 0

    dates_pred = pd.Index(pred.index.get_level_values(date_level).astype(str)).unique()
    dates_rsk = pd.Index([str(d) for d in rsk.keys()]).unique()
    dates = dates_pred.intersection(dates_rsk)

    out_chunks = []

    for d in dates:
        print(f"Date: {d}")
        # --- get mu for this date ---
        mask = pred.index.get_level_values(date_level).astype(str) == str(d)
        pred_d = pred[mask]

        # codes for this date
        codes_d = pred_d.index.get_level_values(code_level).astype(str)

        # IMPORTANT FIX: force to 1D float array
        y = np.asarray(pred_d.to_numpy()).reshape(-1).astype(float)

        mu = pd.Series(y, index=codes_d, dtype=float)
        mu = mu[~mu.index.duplicated(keep="last")]  # keep last if duplicates

        # --- get Sigma for this date ---
        Sigma_df = rsk.get(str(d), None)
        if Sigma_df is None or not isinstance(Sigma_df, pd.DataFrame) or Sigma_df.empty:
            continue

        Sigma_df = Sigma_df.copy()
        Sigma_df.index = Sigma_df.index.astype(str)
        Sigma_df.columns = Sigma_df.columns.astype(str)

        # intersect codes
        codes = mu.index.intersection(Sigma_df.index).intersection(Sigma_df.columns)
        if len(codes) < 2:
            if len(codes) == 1:
                out_chunks.append(
                    pd.Series(
                        [1.0],
                        index=pd.MultiIndex.from_tuples([(str(d), codes[0])], names=["date", "code"]),
                    )
                )
            continue

        mu_vec = mu.loc[codes].to_numpy(dtype=float)  # (n,)
        Sigma = Sigma_df.loc[codes, codes].to_numpy(dtype=float)  # (n,n)

        # clean Sigma: symmetrize + ridge for numerical stability
        Sigma = 0.5 * (Sigma + Sigma.T)
        diag = np.diag(Sigma)
        diag_mean = float(np.mean(diag)) if np.all(np.isfinite(diag)) else 0.0
        ridge = 1e-8 if diag_mean <= 0 or not np.isfinite(diag_mean) else (1e-6 * diag_mean)
        Sigma = Sigma + ridge * np.eye(len(codes))

        n = len(codes)

        # objective: minimize -(mu^T w - lam * w^T Sigma w)
        def obj(w: np.ndarray) -> float:
            return -(mu_vec @ w - lam * (w @ Sigma @ w))

        def grad(w: np.ndarray) -> np.ndarray:
            return (-mu_vec + 2.0 * lam * (Sigma @ w))

        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 1.0) for _ in range(n)]
        w0 = np.full(n, 1.0 / n, dtype=float)

        res = minimize(
            obj,
            w0,
            method="SLSQP",
            jac=grad,
            bounds=bounds,
            constraints=cons,
            options={"maxiter": 200, "ftol": 1e-9, "disp": False},
        )

        if (not res.success) or (not np.all(np.isfinite(res.x))):
            w = np.clip(w0, 0.0, 1.0)
            w = w / w.sum()
        else:
            w = np.clip(res.x, 0.0, 1.0)
            s = w.sum()
            w = w / s if s > 0 else np.full(n, 1.0 / n)

        idx = pd.MultiIndex.from_arrays([[str(d)] * n, list(codes)], names=["date", "code"])
        out_chunks.append(pd.Series(w, index=idx))

    if not out_chunks:
        return pd.Series(dtype=float, name="w")

    out = pd.concat(out_chunks).sort_index()
    out.name = "w"
    return out


def mvw2(pred: pd.Series, rsk: dict, lam: float) -> pd.Series:
    """
    Fast Mean-Variance optimizer via Projected Gradient Descent (PGD):
        minimize f(w) = -mu^T w + lam * w^T Sigma w
        s.t. w in [LOW, UP], sum(w) = 1

    Notes:
        If constraints are infeasible for a given n (e.g., n*LOW>1 or n*UP<1),
        it falls back to simplex constraint: w>=0, sum(w)=1.
    """
    if lam < 0:
        raise ValueError("lam must be >= 0")

    # ---- make pred a real 1D Series ----
    if isinstance(pred, pd.DataFrame):
        if pred.shape[1] != 1:
            raise ValueError("pred is a DataFrame; it must have exactly 1 column.")
        pred = pred.iloc[:, 0]
    elif not isinstance(pred, pd.Series):
        raise ValueError("pred must be a pd.Series or a single-column pd.DataFrame.")

    if not isinstance(pred.index, pd.MultiIndex) or pred.index.nlevels != 2:
        raise ValueError("pred must have a 2-level MultiIndex (code,date) or (date,code).")

    lv0 = pred.index.get_level_values(0)
    lv1 = pred.index.get_level_values(1)

    def _is_yyyymm_like(x) -> bool:
        s = str(x)
        return len(s) == 6 and s.isdigit()

    k0 = min(len(lv0), 2000)
    k1 = min(len(lv1), 2000)
    lv0_date_ratio = float(np.mean([_is_yyyymm_like(x) for x in lv0[:k0]]))
    lv1_date_ratio = float(np.mean([_is_yyyymm_like(x) for x in lv1[:k1]]))
    if lv0_date_ratio > lv1_date_ratio:
        date_level, code_level = 0, 1
    else:
        date_level, code_level = 1, 0

    dates_pred = pd.Index(pred.index.get_level_values(date_level).astype(str)).unique()
    dates_rsk = pd.Index([str(d) for d in rsk.keys()]).unique()
    dates = dates_pred.intersection(dates_rsk)

    # ---- simplex projection: {w>=0, sum(w)=1} ----
    def proj_simplex(v: np.ndarray) -> np.ndarray:
        u = np.sort(v)[::-1]
        cssv = np.cumsum(u) - 1.0
        rho = np.nonzero(u - cssv / (np.arange(len(u)) + 1) > 0)[0]
        if len(rho) == 0:
            w = np.zeros_like(v)
            w[int(np.argmax(v))] = 1.0
            return w
        rho = rho[-1]
        theta = cssv[rho] / (rho + 1.0)
        w = np.maximum(v - theta, 0.0)
        s = w.sum()
        return w / s if s > 0 else np.full_like(w, 1.0 / len(w))

    # ---- bounded simplex projection: {sum(w)=1, LOW<=w<=UP} ----
    def proj_bounded_simplex(v: np.ndarray, low: float, up: float) -> np.ndarray:
        n = v.size
        # Feasibility check
        if n * low > 1.0 + 1e-12 or n * up < 1.0 - 1e-12:
            # infeasible -> fallback
            return proj_simplex(v)

        # Project onto {sum(w)=1, w>=low} first via shifting, then enforce upper bound.
        # Use reduction: w = low + x, where x>=0, sum(x)=1-n*low
        total = 1.0 - n * low
        x = proj_simplex(v - low) * total  # start with a good guess

        # Now enforce upper bounds by iterative "cap and reproject" (waterfilling style)
        # This converges fast in practice.
        w = low + x
        if np.all(w <= up + 1e-12):
            # numerical cleanup
            w = np.clip(w, low, up)
            w /= w.sum()
            return w

        free = np.ones(n, dtype=bool)
        w = np.clip(w, low, up)

        # Iteratively fix those at upper bound and reproject remaining mass
        for _ in range(50):
            over = w > up + 1e-12
            if not np.any(over):
                break
            w[over] = up
            free = ~over

            mass_fixed = float(w[~free].sum())
            mass_left = 1.0 - mass_fixed
            if mass_left <= 0:
                # all mass consumed by caps; distribute minimally among free if any
                if np.any(free):
                    w[free] = low
                    w /= w.sum()
                return w

            # Remaining variables live in [low, up], sum = mass_left
            n_free = int(free.sum())
            # after allocating low to each free var, residual for simplex:
            residual = mass_left - n_free * low
            if residual < 0:
                # can't even allocate lows -> fallback to simplex
                return proj_simplex(v)

            # project (v_free - low) onto simplex of size residual, then add low
            vf = v[free]
            xf = proj_simplex(vf - low) * residual
            w[free] = low + xf
            w = np.clip(w, low, up)

            # check sum
            s = float(w.sum())
            if abs(s - 1.0) < 1e-10:
                break
            # renormalize gently (should be tiny)
            w /= s

        # final safety
        w = np.clip(w, low, up)
        s = float(w.sum())
        w = w / s if s > 0 else np.full(n, 1.0 / n)
        return w

    out_chunks = []

    # --- fixed internal settings (no extra params) ---
    MAX_ITERS = 120
    TOL = 1e-8
    BACKTRACK = True
    INIT_STEP = 1.0

    # --- NEW: weight bounds ---
    LOW = 0.05
    UP = 0.95

    for d in dates:
        print(f"Date: {d}")
        mask = pred.index.get_level_values(date_level).astype(str) == str(d)
        pred_d = pred[mask]
        codes_d = pred_d.index.get_level_values(code_level).astype(str)

        mu_vals = np.asarray(pred_d.to_numpy()).reshape(-1).astype(float)
        mu_s = pd.Series(mu_vals, index=codes_d, dtype=float)
        mu_s = mu_s[~mu_s.index.duplicated(keep="last")]

        Sigma_df = rsk.get(str(d), None)
        if Sigma_df is None or not isinstance(Sigma_df, pd.DataFrame) or Sigma_df.empty:
            continue

        Sigma_df = Sigma_df.copy()
        Sigma_df.index = Sigma_df.index.astype(str)
        Sigma_df.columns = Sigma_df.columns.astype(str)

        codes = mu_s.index.intersection(Sigma_df.index).intersection(Sigma_df.columns)
        if len(codes) < 2:
            if len(codes) == 1:
                out_chunks.append(
                    pd.Series([1.0],
                              index=pd.MultiIndex.from_tuples([(str(d), codes[0])], names=["date", "code"]))
                )
            continue

        mu = mu_s.loc[codes].to_numpy(dtype=float)
        Sigma = Sigma_df.loc[codes, codes].to_numpy(dtype=float)
        Sigma = 0.5 * (Sigma + Sigma.T)

        diag = np.diag(Sigma)
        diag_mean = float(np.mean(diag)) if np.all(np.isfinite(diag)) else 0.0
        ridge = 1e-8 if diag_mean <= 0 or not np.isfinite(diag_mean) else (1e-6 * diag_mean)
        Sigma = Sigma + ridge * np.eye(len(codes))

        n = len(codes)

        # init w: bounded-uniform if feasible else uniform simplex
        if n * LOW <= 1.0 <= n * UP:
            w = np.full(n, 1.0 / n, dtype=float)
            w = np.clip(w, LOW, UP)
            w /= w.sum()
        else:
            w = np.full(n, 1.0 / n, dtype=float)

        def f(wv: np.ndarray) -> float:
            return float(-(mu @ wv) + lam * (wv @ Sigma @ wv))

        def grad(wv: np.ndarray) -> np.ndarray:
            return (-mu + 2.0 * lam * (Sigma @ wv))

        f_prev = f(w)

        for _ in range(MAX_ITERS):
            g = grad(w)

            step = INIT_STEP
            if BACKTRACK:
                for __ in range(12):
                    w_try = w - step * g
                    w_new = proj_bounded_simplex(w_try, LOW, UP)
                    f_new = f(w_new)
                    if f_new <= f_prev - 1e-4 * step * float(g @ (w - w_new)):
                        break
                    step *= 0.5
                else:
                    w_new = proj_bounded_simplex(w - 1e-4 * g, LOW, UP)
                    f_new = f(w_new)
            else:
                w_new = proj_bounded_simplex(w - step * g, LOW, UP)
                f_new = f(w_new)

            if abs(f_prev - f_new) <= TOL * (1.0 + abs(f_prev)):
                w = w_new
                break

            w, f_prev = w_new, f_new

        idx = pd.MultiIndex.from_arrays([[str(d)] * n, list(codes)], names=["date", "code"])
        out_chunks.append(pd.Series(w, index=idx))

    if not out_chunks:
        return pd.Series(dtype=float, name="w")

    out = pd.concat(out_chunks).sort_index()
    out.name = "w"
    return out
