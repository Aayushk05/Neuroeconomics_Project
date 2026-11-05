"""Simulate the survey export and check the pipeline recovers known preferences.

    python analysis/simulate.py                  # one sample of 120, full report + recovery
    python analysis/simulate.py --reps 200       # Monte Carlo: bias, CI coverage, power
    python analysis/simulate.py --out exports/simulated_choices_long.csv

Uses the frozen design (survey/design_blocks.csv) and the fixed attention checks
(survey/attention_checks.csv) the way the web app shows them: pairs shuffled,
left/right randomised, checks at screens 4 and 9, and salary = level x own CTC
rounded to 0.1 LPA. The output has the columns of the app's choices_long.csv.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import pipeline as P

SURVEY = Path(__file__).resolve().parent.parent / "survey"
DESIGN_SLOTS = [1, 2, 3, 5, 6, 7, 8, 10]
ATTRS = ["salary_level", "varpay", "arrangement", "hours", "autonomy", "growth"]
COLUMNS = ["pid", "block", "set_id", "kind", "pair", "alt_id", "flipped", "chosen",
           "salary_level", "salary", "varpay", "arrangement", "hours", "autonomy", "growth", "rt_ms"]

# True preferences. Salary enters as ln(CTC); 8.4 makes remote worth
# exp(0.8 / 8.4) - 1 = 10% of pay, the middle of H2's predicted 5-15%.
TRUE = {
    "ln_sal": 8.4,
    "varpay_bonus": -0.25, "varpay_equity": -0.55,
    "arr_hybrid": 0.55, "arr_remote": 0.80,
    "hours_50": -0.45, "hours_60": -1.10,
    "auto_some": 0.35, "auto_choose": 0.70,
    "growth_ment": 0.40, "growth_track": 0.60,
    "left": 0.15,
}
SHOCK_SD = {"arr_remote": 0.30, "hours_60": 0.30}   # person-level taste variation
SHARE_RANDOM = 0.10                                  # participants who click at random


def load_design():
    def profile(rows):
        return rows[ATTRS].iloc[0].to_dict()
    d = pd.read_csv(SURVEY / "design_blocks.csv")
    blocks = {b: [(profile(g[g.alt == 1]), profile(g[g.alt == 2])) for _, g in gb.groupby("pair")]
              for b, gb in d.groupby("block")}
    c = pd.read_csv(SURVEY / "attention_checks.csv")
    checks = {s: (profile(g[g.position == "A"]), profile(g[g.position == "B"])) for s, g in c.groupby("screen")}
    return blocks, checks


def js_round1(x):
    """The web app's display rule, Math.round(x * 10) / 10."""
    return float(np.floor(x * 10 + 0.5) / 10)


def utility(profile, salary, left, beta):
    u = beta["ln_sal"] * np.log(salary) + beta["left"] * left
    for name, (attr, level) in P.NONPAY.items():
        if profile[attr] == level:
            u += beta[name]
    return u


def simulate(n=120, seed=0, truth=TRUE):
    """Returns (choices_long dataframe, set of pids who clicked at random)."""
    rng = np.random.default_rng(seed)
    blocks, checks = load_design()
    random_pids = {int(p) + 1 for p in rng.choice(n, size=round(n * SHARE_RANDOM), replace=False)}
    rows = []
    for pid in range(1, n + 1):
        block = (pid - 1) % 3
        anchor = round(float(np.clip(np.exp(rng.normal(np.log(12), 0.5)), 2, 150)), 1)
        beta = dict(truth)
        for k, sd in SHOCK_SD.items():
            beta[k] += rng.normal(0, sd)
        screens = {}
        for set_id, i in zip(DESIGN_SLOTS, rng.permutation(8)):
            a, b = blocks[block][i]
            flipped = int(rng.random() < 0.5)
            screens[set_id] = ("design", i + 1, flipped, *((b, a) if flipped else (a, b)))
        for set_id, (a, b) in checks.items():
            screens[set_id] = ("check", None, 0, a, b)
        for set_id in range(1, 11):
            kind, pair, flipped, A, B = screens[set_id]
            salaries = [js_round1(A["salary_level"] * anchor), js_round1(B["salary_level"] * anchor)]
            if pid in random_pids:
                pick = int(rng.integers(2))
            else:
                u = np.array([utility(A, salaries[0], 1, beta), utility(B, salaries[1], 0, beta)])
                pick = int(np.argmax(u + rng.gumbel(size=2)))      # logit choice
            for alt_id, prof, sal in ((1, A, salaries[0]), (2, B, salaries[1])):
                rows.append(dict(prof, pid=pid, block=block, set_id=set_id, kind=kind, pair=pair,
                                 alt_id=alt_id, flipped=flipped, chosen=int(pick == alt_id - 1),
                                 salary=sal, rt_ms=0))
    return pd.DataFrame(rows)[COLUMNS], random_pids


def recovery(df, truth=TRUE):
    r = P.analyse(df)
    P.report(r)
    m = r["wtp_model"]
    ci = m.conf_int()
    print("\nRECOVERY -- WTP model vs the true weights")
    print(f"{'term':<16}{'est':>8}{'95% CI':>18}{'true':>8}")
    for t in P.MODEL_WTP:
        flag = "" if ci.loc[t, 0] <= truth[t] <= ci.loc[t, 1] else "   <- outside CI"
        print(f"{t:<16}{m.params[t]:>8.2f}   [{ci.loc[t, 0]:>5.2f}, {ci.loc[t, 1]:>5.2f}]{truth[t]:>8.2f}{flag}")
    w, lo, hi = P.wtp(m, "arr_remote")
    print(f"\nRemote WTP: {w:.1%} [{lo:.1%}, {hi:.1%}]; true {np.expm1(truth['arr_remote'] / truth['ln_sal']):.1%}")


def monte_carlo(reps, n, seed, truth=TRUE):
    true_remote = np.expm1(truth["arr_remote"] / truth["ln_sal"])
    recs = []
    for i in range(reps):
        df, random_pids = simulate(n, seed + i, truth)
        keep, failed = P.exclude(df)
        D, y = P.differences(keep)
        m, h = P.fit(D, y, P.MODEL_WTP), P.h1_test(D, y)
        ci = m.conf_int()
        w, lo, hi = P.wtp(m, "arr_remote")
        rec = {"caught": len(set(failed) & random_pids), "attentive_excluded": len(set(failed) - random_pids),
               "kept": keep.pid.nunique(), "remote_wtp": w, "remote_halfwidth": (hi - lo) / 2,
               "remote_covered": lo <= true_remote <= hi, "h1": h["p_z"] < 0.05,
               "equity": m.tvalues["varpay_equity"] < -1.645, "bonus": m.tvalues["varpay_bonus"] < -1.645}
        for t in P.MODEL_WTP:
            rec[f"est:{t}"] = m.params[t]
            rec[f"cov:{t}"] = ci.loc[t, 0] <= truth[t] <= ci.loc[t, 1]
        recs.append(rec)
    r = pd.DataFrame(recs)
    print(f"{reps} simulated samples of {n}")
    print(f"  random clickers caught {r.caught.mean():.1f} of {round(n * SHARE_RANDOM)}; "
          f"attentive people excluded {r.attentive_excluded.mean():.1f}; kept {r.kept.mean():.1f}")
    print(f"  remote WTP: median {r.remote_wtp.median():.1%} (true {true_remote:.1%}), "
          f"median CI half-width {r.remote_halfwidth.median():.1%}, CI coverage {r.remote_covered.mean():.0%}")
    print(f"  power: H1 {r.h1.mean():.0%}, H3 equity < cash {r.equity.mean():.0%}, H3 bonus < cash {r.bonus.mean():.0%}")
    print(f"\n  {'term':<16}{'mean est':>10}{'true':>8}{'95% CI coverage':>18}")
    for t in P.MODEL_WTP:
        print(f"  {t:<16}{r[f'est:{t}'].mean():>10.2f}{truth[t]:>8.2f}{r[f'cov:{t}'].mean():>18.0%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=20261026)
    ap.add_argument("--reps", type=int, default=0, help="Monte Carlo repetitions instead of one sample")
    ap.add_argument("--out", help="also write the simulated choices_long.csv here")
    args = ap.parse_args()
    if args.reps:
        monte_carlo(args.reps, args.n, args.seed)
    else:
        df, _ = simulate(args.n, args.seed)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(args.out, index=False)
        recovery(df)
