import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit

import pipeline as P
import simulate as S

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import export  # noqa: E402
import server  # noqa: E402


def test_difference_logit_matches_conditional_logit():
    df, _ = S.simulate(n=90, seed=3)
    keep, _ = P.exclude(df)
    D, y = P.differences(keep)
    ours = P.fit(D, y, P.MODEL_WTP)
    X = P.design(keep)[P.MODEL_WTP].reset_index(drop=True)
    cl = ConditionalLogit(keep.chosen.to_numpy(), X, groups=(keep.pid * 100 + keep.set_id).to_numpy())
    # Our estimate is the conditional logit's exact maximum: its score is zero there.
    # (ConditionalLogit.fit itself stops early, ~4e-4 away, with a score of ~0.01.)
    assert np.abs(cl.score(ours.params.to_numpy())).max() < 1e-8
    assert cl.loglike(ours.params.to_numpy()) >= cl.loglike(cl.fit(disp=0).params.to_numpy())


def test_attention_rule_catches_straight_liners_and_passes_careful_people():
    df, _ = S.simulate(n=3, seed=1)
    checks = df.kind == "check"
    df.loc[df.pid == 1, "chosen"] = (df.alt_id == 1).astype(int)        # always the left job
    df.loc[df.pid == 2, "chosen"] = (df.alt_id == 2).astype(int)        # always the right job
    df.loc[(df.pid == 3) & checks, "chosen"] = (df.salary_level == 1.25).astype(int)   # the better job
    assert P.attention_failures(df) == {1: 1, 2: 1}
    keep, failed = P.exclude(df)
    assert set(keep.pid) == {3} and set(keep.kind) == {"design"}


def test_pipeline_recovers_known_preferences():
    df, _ = S.simulate(n=900, seed=7)
    r = P.analyse(df)
    w, lo, hi = P.wtp(r["wtp_model"], "arr_remote")
    assert lo < np.expm1(0.8 / 8.4) < hi and 0.07 < w < 0.13
    assert r["h1"]["p_z"] < 0.001
    assert r["wtp_model"].params["varpay_equity"] < 0


def test_h1_bootstrap_runs():
    df, _ = S.simulate(n=60, seed=5)
    keep, _ = P.exclude(df)
    D, y = P.differences(keep)
    h = P.h1_test(D, y, bootstrap=20, rng=np.random.default_rng(1))
    assert 0 < h["p_boot"] <= 1 and h["n_boot"] >= 15


def _submission(token, plan, anchor, rng):
    """A complete professional's answers, with job choices made by the true model."""
    choices = []
    for s in plan:
        sal = [S.js_round1(s[side]["salary_level"] * anchor) for side in "AB"]
        u = np.array([S.utility(s["A"], sal[0], 1, S.TRUE), S.utility(s["B"], sal[1], 0, S.TRUE)])
        pick = "AB"[int(np.argmax(u + rng.gumbel(size=2)))]
        choices.append({"set_id": s["set_id"], "chose": pick, "rt_ms": 3000, "ctc_A": sal[0], "ctc_B": sal[1]})
    return {
        "token": token, "s1": "pro", "anchor_ctc": anchor, "choices": choices,
        "b1_switch": "3", "b2_switch": "2", "b3a_choice": "absolute", "b3a_order": "absolute_first",
        "b4_ctc": 50, "b4_varpay": 10, "b4_arrangement": 10, "b4_hours": 10, "b4_autonomy": 10, "b4_growth": 10,
        "d1_age": "26-30", "d2_gender": "woman", "d3_stock": "rsu", "d4_channel": "linkedin",
        "j1_exp": "3-5", "j3_paymix": "stock", "j4_arrangement": "remote",
        "j5_hours": 45, "j6_autonomy": "choose", "j7_growth": "track_plus", "j8_satisfaction": 8,
        "total_time_s": 600, "screen_times": {},
    }


def test_app_export_feeds_the_pipeline(tmp_path):
    """The contract between the web app and the analysis: submit through the real
    API, export, and fit every model on what comes out."""
    client = server.create_app(tmp_path / "survey.sqlite3").test_client()
    rng = np.random.default_rng(11)
    for _ in range(90):
        start = client.post("/api/start", json={}).get_json()
        anchor = round(float(np.exp(rng.normal(np.log(12), 0.5))), 1)
        res = client.post("/api/submit", json=_submission(start["token"], start["screens"], anchor, rng))
        assert res.status_code == 200, res.get_json()
    export.write_exports(tmp_path / "survey.sqlite3", tmp_path / "exports")
    df = P.load(tmp_path / "exports" / "choices_long.csv")
    assert list(df.columns) == S.COLUMNS
    assert sorted(df.block.value_counts().to_list()) == [60 * 10, 60 * 10, 60 * 10]   # 30 people per block
    r = P.analyse(df)
    assert r["n_kept"] >= 85
    assert np.isfinite(r["wtp_model"].params).all()
    w, lo, hi = P.wtp(r["wtp_model"], "arr_remote")
    assert lo < np.expm1(0.8 / 8.4) < hi
