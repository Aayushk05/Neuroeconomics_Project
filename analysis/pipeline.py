"""Estimation pipeline for the job-choice experiment (Arm A).

Runs the pre-registered conjoint models on the survey export (app/export.py):

    python analysis/pipeline.py exports/choices_long.csv [--bootstrap 499]

Salary pivots around each participant's own CTC: levels are 0.8 / 1.0 / 1.25 x
their anchor, and `salary` holds the LPA figure that was actually shown.

A binary conditional logit is a logit on the difference between the two jobs
(x_A - x_B) with no constant. Fitting it that way lets us cluster standard errors
by participant; the one constant we do add is the difference in the "shown on the
left" dummy, so it measures position bias. test_pipeline.py checks the estimates
equal statsmodels' ConditionalLogit.
"""
import argparse

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

# Direction people prefer, best last. NOTE: not the order levels are listed in --
# equity is listed third but is the least liked. The attention checks only use the
# UNAMBIGUOUS attributes, because a real person may prefer equity or the office.
BETTER = {
    "salary_level": [0.8, 1.0, 1.25],
    "varpay": ["equity", "bonus", "cash"],
    "arrangement": ["onsite", "hybrid", "remote"],
    "hours": [60, 50, 40],
    "autonomy": ["assigned", "some", "choose"],
    "growth": ["none", "mentorship", "track"],
}
UNAMBIGUOUS = ["salary_level", "hours", "autonomy", "growth"]
RANK = {k: {lvl: i for i, lvl in enumerate(v)} for k, v in BETTER.items()}

# Dummies against the first-listed level of each attribute.
SALARY_DUMMIES = {"sal_100": 1.0, "sal_125": 1.25}           # reference: 0.8 x anchor
NONPAY = {
    "varpay_bonus": ("varpay", "bonus"), "varpay_equity": ("varpay", "equity"),
    "arr_hybrid": ("arrangement", "hybrid"), "arr_remote": ("arrangement", "remote"),
    "hours_50": ("hours", 50), "hours_60": ("hours", 60),
    "auto_some": ("autonomy", "some"), "auto_choose": ("autonomy", "choose"),
    "growth_ment": ("growth", "mentorship"), "growth_track": ("growth", "track"),
}
NP = list(NONPAY)

MODEL_PARTWORTH = [*SALARY_DUMMIES, *NP, "left"]   # part-worths, within-person curvature
MODEL_WTP = ["ln_sal", *NP, "left"]                # H2 / H3: WTP as a share of own CTC
MODEL_H1 = ["ln_sal", "lin_sal", *NP, "left"]      # H1: is ln(CTC) needed beyond linear CTC?


def load(path):
    df = pd.read_csv(path)
    df["hours"] = df["hours"].astype(int)
    df["salary_level"] = df["salary_level"].round(2)
    return df


def dominates(a, b, attrs):
    """True if a is at least as good as b on every attribute in attrs and strictly
    better on at least one, using the preference direction in BETTER."""
    ra = [RANK[k][a[k]] for k in attrs]
    rb = [RANK[k][b[k]] for k in attrs]
    return all(x >= y for x, y in zip(ra, rb)) and any(x > y for x, y in zip(ra, rb))


def attention_failures(df):
    """{pid: number of checks failed}. A check is failed when the job not chosen
    dominates the chosen one on the unambiguous attributes."""
    failed = {}
    for (pid, _), g in df[df.kind == "check"].groupby(["pid", "set_id"]):
        chosen, other = g[g.chosen == 1].iloc[0], g[g.chosen == 0].iloc[0]
        if dominates(other, chosen, UNAMBIGUOUS):
            failed[pid] = failed.get(pid, 0) + 1
    return failed


def exclude(df):
    """Pre-registered rule: fail either check -> excluded. Returns (design rows kept, failures)."""
    failed = attention_failures(df)
    keep = df[~df.pid.isin(failed) & (df.kind == "design")].copy()
    return keep, failed


def design(df):
    """One row per job shown: salary dummies, non-pay dummies, ln and linear CTC, left."""
    X = pd.DataFrame(index=df.index)
    for name, level in SALARY_DUMMIES.items():
        X[name] = (df.salary_level == level).astype(float)
    for name, (attr, level) in NONPAY.items():
        X[name] = (df[attr] == level).astype(float)
    X["ln_sal"] = np.log(df.salary)
    X["lin_sal"] = df.salary
    X["left"] = (df.alt_id == 1).astype(float)
    return X


def differences(df):
    """One row per choice set: x(Job A) - x(Job B), and whether Job A was chosen."""
    X = design(df)
    X.index = pd.MultiIndex.from_frame(df[["pid", "set_id"]])
    is_a = (df.alt_id == 1).to_numpy()
    xa, xb = X[is_a], X[~is_a]
    D = xa - xb.loc[xa.index]
    y = pd.Series(df.chosen.to_numpy()[is_a], index=xa.index)
    return D, y


def fit(D, y, terms, groups=None):
    groups = D.index.get_level_values("pid") if groups is None else groups
    return sm.Logit(y.to_numpy(), D[terms]).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": np.asarray(groups)})


def wtp(res, term, base="ln_sal"):
    """Share of own CTC a person would give up for `term`: exp(b_term / b_ln) - 1,
    with a delta-method 95% CI on the ratio, mapped through exp."""
    b, V = res.params, res.cov_params()
    q = b[term] / b[base]
    var = (V.loc[term, term] / b[base] ** 2 + b[term] ** 2 * V.loc[base, base] / b[base] ** 4
           - 2 * b[term] * V.loc[term, base] / b[base] ** 3)
    half = 1.96 * np.sqrt(var)
    return np.expm1(q), np.expm1(q - half), np.expm1(q + half)


def h1_test(D, y, bootstrap=0, rng=None):
    """H1: ln(CTC) coefficient > 0 in a model that also has linear CTC (one-sided).

    Identified by comparing people at different pay levels. In simulation the
    clustered z-test ran a little liberal (12% false positives at a nominal 5%), so
    a participant-level bootstrap-t p-value is reported alongside when asked for.
    """
    res = fit(D, y, MODEL_H1)
    b, se = res.params["ln_sal"], res.bse["ln_sal"]
    out = {"b_ln": b, "se": se, "z": b / se, "p_z": stats.norm.sf(b / se)}
    if bootstrap:
        rng = rng or np.random.default_rng(0)
        pids = D.index.get_level_values("pid").unique().to_numpy()
        by_pid = {p: D.xs(p, level="pid", drop_level=False) for p in pids}
        y_pid = {p: y.xs(p, level="pid", drop_level=False) for p in pids}
        t_star = []
        for _ in range(bootstrap):
            draw = rng.choice(pids, size=len(pids), replace=True)
            Db = pd.concat([by_pid[p] for p in draw])
            yb = pd.concat([y_pid[p] for p in draw])
            groups = np.repeat(np.arange(len(draw)), [len(by_pid[p]) for p in draw])
            try:
                rb = fit(Db, yb, MODEL_H1, groups=groups)
            except Exception:       # a resample that doesn't converge is skipped
                continue
            t_star.append((rb.params["ln_sal"] - b) / rb.bse["ln_sal"])
        t_star = np.asarray(t_star)
        out["p_boot"] = (1 + np.sum(t_star >= out["z"])) / (len(t_star) + 1)
        out["n_boot"] = len(t_star)
    return out


def within_person_curvature(res):
    """Secondary H1 check from the part-worths: concave iff the slope from 1.0x to
    1.25x is below the slope from 0.8x to 1.0x, i.e. 9*sal_100 - 4*sal_125 > 0.
    Low power: the levels span only 0.8-1.25x of one person's pay."""
    c = pd.Series(0.0, index=res.params.index)
    c["sal_100"], c["sal_125"] = 9, -4
    est = c @ res.params
    se = np.sqrt(c @ res.cov_params() @ c)
    return est, se, stats.norm.sf(est / se)


def analyse(df, bootstrap=0):
    keep, failed = exclude(df)
    D, y = differences(keep)
    return {
        "n_total": df.pid.nunique(), "failed": failed, "n_kept": keep.pid.nunique(), "n_sets": len(y),
        "partworth": fit(D, y, MODEL_PARTWORTH),
        "wtp_model": fit(D, y, MODEL_WTP),
        "h1": h1_test(D, y, bootstrap=bootstrap),
    }


def report(r):
    both = sum(n == 2 for n in r["failed"].values())
    print(f"Participants: {r['n_total']}; failed a check: {len(r['failed'])} ({both} failed both); "
          f"kept: {r['n_kept']} ({r['n_sets']} choice sets)\n")

    pw = r["partworth"]
    print("PART-WORTHS (salary as 0.8 / 1.0 / 1.25 x own CTC; SEs clustered by participant)")
    print(f"{'term':<16}{'est':>8}{'se':>8}{'p':>8}")
    for t in MODEL_PARTWORTH:
        print(f"{t:<16}{pw.params[t]:>8.2f}{pw.bse[t]:>8.2f}{pw.pvalues[t]:>8.3f}")
    est, se, p = within_person_curvature(pw)
    print(f"\nWithin-person curvature (secondary): 9*sal_100 - 4*sal_125 = {est:.2f} (se {se:.2f}), one-sided p = {p:.3f}")

    h = r["h1"]
    line = f"H1: ln(CTC) coefficient with linear CTC also in the model = {h['b_ln']:.2f} (se {h['se']:.2f}), one-sided p = {h['p_z']:.4f}"
    if "p_boot" in h:
        line += f"; bootstrap-t p = {h['p_boot']:.4f} ({h['n_boot']} resamples)"
    print(line)

    m = r["wtp_model"]
    print(f"\nWTP AS A SHARE OF OWN CTC (ln CTC coefficient {m.params['ln_sal']:.2f})")
    print(f"{'term':<16}{'WTP':>8}{'95% CI':>20}")
    for t in NP:
        w, lo, hi = wtp(m, t)
        print(f"{t:<16}{w:>8.1%}   [{lo:>6.1%}, {hi:>6.1%}]")
    print(f"\nPosition (left job) effect: {m.params['left']:.2f} (se {m.bse['left']:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("choices", help="choices_long.csv from app/export.py")
    ap.add_argument("--bootstrap", type=int, default=0, help="participant-level resamples for the H1 p-value")
    args = ap.parse_args()
    report(analyse(load(args.choices), bootstrap=args.bootstrap))
