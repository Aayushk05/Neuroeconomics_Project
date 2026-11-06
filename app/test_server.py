import csv
import io
import math
import sqlite3
import zipfile
from datetime import datetime, timezone

import pytest

import server
from export import csv_texts
from schema import CHOICE_COLUMNS, PARTICIPANT_COLUMNS


def js_round1(x):
    """The front end's Math.round(x * 10) / 10."""
    return math.floor(x * 10 + 0.5) / 10


@pytest.fixture
def app(tmp_path):
    return server.create_app(tmp_path / "survey.sqlite3")


@pytest.fixture
def client(app):
    return app.test_client()


def start(client, pilot=False):
    data = client.post("/api/start", json={"pilot": pilot}).get_json()
    return data["token"], data["screens"]


def answers(token, plan, S=12.0, path="pro", **override):
    body = {
        "token": token, "s1": path, "anchor_ctc": S,
        "choices": [{"set_id": s["set_id"], "chose": "A" if s["set_id"] % 3 else "B", "rt_ms": 4200,
                     "ctc_A": js_round1(s["A"]["salary_level"] * S),
                     "ctc_B": js_round1(s["B"]["salary_level"] * S)} for s in plan],
        "b1_switch": "2", "b2_switch": "none", "b3a_choice": "absolute", "b3a_order": "positional_first",
        "b4_ctc": 40, "b4_varpay": 10, "b4_arrangement": 20, "b4_hours": 15, "b4_autonomy": 5, "b4_growth": 10,
        "d1_age": "22-25", "d2_gender": "na", "d3_stock": "no",
        "e1_text": "", "total_time_s": 512.3, "screen_times": {"consent": 30000},
    }
    if path in ("pro", "between"):
        body.update(j1_exp="1-2", j3_paymix="bonus_stock", j4_arrangement="hybrid",
                    j5_hours=48, j6_autonomy="some", j7_growth="track", j8_satisfaction=7)
    else:
        body.update(p2_source="offer", st2_field="cs", st3_year="4")
    body.update(override)
    return body


def exported(app_db):
    conn = sqlite3.connect(app_db)
    try:
        return {name: list(csv.DictReader(io.StringIO(text))) for name, text in csv_texts(conn).items()}
    finally:
        conn.close()


def test_plan_has_fixed_checks_and_the_whole_block(client):
    design = server.load_design()
    for _ in range(20):
        _, plan = start(client)
        assert [s["set_id"] for s in plan] == list(range(1, 11))
        checks = {s["set_id"]: s for s in plan if s["kind"] == "check"}
        assert set(checks) == {4, 9}
        # better job (1.25 x CTC) on the left at screen 4, on the right at screen 9
        assert checks[4]["A"]["salary_level"] == 1.25 and checks[4]["B"]["salary_level"] == 0.8
        assert checks[9]["A"]["salary_level"] == 0.8 and checks[9]["B"]["salary_level"] == 1.25
        shown = [s for s in plan if s["kind"] == "design"]
        assert sorted(s["pair"] for s in shown) == list(range(1, 9))
        # every design screen is one of the frozen pairs, in the recorded orientation
        blocks = [b for b, pairs in design.items()
                  if all(((pairs[s["pair"] - 1][2], pairs[s["pair"] - 1][1]) if s["flipped"]
                          else (pairs[s["pair"] - 1][1], pairs[s["pair"] - 1][2])) == (s["A"], s["B"])
                         for s in shown)]
        assert len(blocks) == 1


def test_block_goes_to_the_least_filled(tmp_path):
    server.create_app(tmp_path / "db.sqlite3")
    conn = sqlite3.connect(tmp_path / "db.sqlite3")
    now = datetime.now(timezone.utc)
    old = "2020-01-01T00:00:00+00:00"
    rows = [("t1", 0, 0, "[]", old, old), ("t2", 1, 0, "[]", old, old),
            ("t3", 2, 0, "[]", old, None),                      # abandoned long ago: doesn't count
            ("t4", 2, 1, "[]", now.isoformat(), None)]          # a pilot start: doesn't count for main data
    conn.executemany("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)", rows)
    blocks = server.load_design()
    assert {server.choose_block(conn, blocks, 0, now) for _ in range(30)} == {2}
    conn.execute("INSERT INTO sessions VALUES ('t5', 2, 0, '[]', ?, NULL)", (now.isoformat(),))
    assert {server.choose_block(conn, blocks, 0, now) for _ in range(60)} == {0, 1, 2}


def test_professional_submission_round_trip(app, client, tmp_path):
    token, plan = start(client)
    res = client.post("/api/submit", json=answers(token, plan, S=13.7))
    assert res.status_code == 200, res.get_json()
    code = res.get_json()["code"]
    assert len(code) == 6

    out = exported(tmp_path / "survey.sqlite3")
    (person,) = out["participants.csv"]
    assert list(person) == PARTICIPANT_COLUMNS
    assert person["code"] == code and person["path"] == "professional"
    assert person["anchor_ctc"] == "13.7" and person["anchor_type"] == "current"
    assert person["d2_self"] == ""
    assert person["st2_field"] == "" and person["j8_satisfaction"] == "7"
    for cut in ("b3b_choice", "st1_degree", "j2_company"):    # items dropped to shorten the survey
        assert cut not in person

    rows = out["choices_long.csv"]
    assert list(rows[0]) == CHOICE_COLUMNS
    assert len(rows) == 20
    assert all(sum(int(r["chosen"]) for r in rows if r["set_id"] == str(s)) == 1 for s in range(1, 11))
    for r in rows:   # stored CTC is the number shown, and matches level x anchor
        assert abs(float(r["salary"]) - float(r["salary_level"]) * 13.7) <= 0.05
    assert {r["kind"] for r in rows if r["set_id"] in ("4", "9")} == {"check"}
    assert out["participants_pilot.csv"] == [] and out["choices_long_pilot.csv"] == []


def test_student_who_prefers_not_to_give_pay_gets_the_default_anchor(client, tmp_path):
    token, plan = start(client)
    body = answers(token, plan, S=12.0, path="student_ug", anchor_na=True)
    del body["anchor_ctc"], body["p2_source"]
    assert client.post("/api/submit", json=body).status_code == 200
    (person,) = exported(tmp_path / "survey.sqlite3")["participants.csv"]
    assert (person["anchor_ctc"], person["anchor_type"], person["path"]) == ("12.0", "default", "student")
    assert person["j1_exp"] == "" and person["st3_year"] == "4"


@pytest.mark.parametrize("override, message", [
    ({"b4_growth": 9}, "100"),
    ({"s1": "nontech"}, "s1"),
    ({"d1_age": "17"}, "d1_age"),
    ({"j5_hours": 5}, "j5_hours"),
    ({"j8_satisfaction": 7.5}, "j8_satisfaction"),
    ({"b4_ctc": True}, "b4_ctc"),
])
def test_bad_answers_are_rejected(client, override, message):
    token, plan = start(client)
    res = client.post("/api/submit", json=answers(token, plan, **override))
    assert res.status_code == 400 and message in res.get_json()["error"]


def test_choices_must_match_the_plan_and_the_anchor(client):
    token, plan = start(client)
    body = answers(token, plan)
    body["choices"] = body["choices"][:9]
    assert client.post("/api/submit", json=body).status_code == 400
    body = answers(token, plan)
    body["choices"][0]["ctc_A"] += 1          # a CTC that was never shown for this anchor
    assert "CTC" in client.post("/api/submit", json=body).get_json()["error"]
    body = answers(token, plan)
    body["choices"][0]["chose"] = "C"
    assert client.post("/api/submit", json=body).status_code == 400
    assert client.post("/api/submit", json=answers("nope", plan)).status_code == 400


def test_retry_after_success_returns_the_same_code_and_stores_once(client, tmp_path):
    token, plan = start(client)
    first = client.post("/api/submit", json=answers(token, plan)).get_json()["code"]
    again = client.post("/api/submit", json=answers(token, plan)).get_json()["code"]
    assert first == again
    assert len(exported(tmp_path / "survey.sqlite3")["choices_long.csv"]) == 20


def test_pilot_responses_export_separately(client, tmp_path):
    token, plan = start(client, pilot=True)
    assert client.post("/api/submit", json=answers(token, plan)).status_code == 200
    out = exported(tmp_path / "survey.sqlite3")
    assert out["participants.csv"] == [] and len(out["choices_long_pilot.csv"]) == 20


def test_export_endpoint_needs_the_token(client, monkeypatch):
    assert client.get("/api/export.zip").status_code == 404
    monkeypatch.setenv("EXPORT_TOKEN", "s3cret")
    assert client.get("/api/export.zip", headers={"Authorization": "Bearer wrong"}).status_code == 404
    res = client.get("/api/export.zip", headers={"Authorization": "Bearer s3cret"})
    assert res.status_code == 200
    assert sorted(zipfile.ZipFile(io.BytesIO(res.data)).namelist()) == [
        "choices_long.csv", "choices_long_pilot.csv", "participants.csv", "participants_pilot.csv"]


def test_index_and_assets_are_served(client):
    assert b"survey.js" in client.get("/").data
    for asset in ("survey.js", "styles.css", "config.js"):
        assert client.get(f"/static/{asset}").status_code == 200
