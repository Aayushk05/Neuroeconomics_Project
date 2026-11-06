"""What a completed submission must contain, and the column order of the exports.

Option codes here must match the `value` attributes in static/survey.js.
"""
import json

# Screen-out answers ("nontech", "none") never reach the server.
ELIGIBLE_S1 = {"student_ug": "student", "student_pg": "student",
               "pro": "professional", "between": "between"}
DEFAULT_ANCHOR = 12.0          # used when P1 = "Prefer not to say"

SWITCH = {"1", "2", "3", "4", "5", "none"}
SIDE = {"positional", "absolute"}
ORDER = {"positional_first", "absolute_first"}

COMMON = {
    "b1_switch": SWITCH, "b2_switch": SWITCH,
    "b3a_choice": SIDE, "b3a_order": ORDER,
    "d1_age": {"18-21", "22-25", "26-30", "31-35", "36-45", "46+"},
    "d2_gender": {"woman", "man", "nonbinary", "self", "na"},
    "d3_stock": {"esop", "rsu", "both", "no", "unsure"},
}
# Item ids keep their survey_copy.md numbers; ST1, J2 and B3b were cut on 2 Nov to shorten the survey.
STUDENT = {
    "st2_field": {"cs", "ece", "other_eng", "other"},
    "st3_year": {"1", "2", "3", "4", "5+"},
}
WORKER = {
    "j1_exp": {"<1", "1-2", "3-5", "6-10", "10+"},
    "j3_paymix": {"cash", "bonus", "stock", "bonus_stock"},
    "j4_arrangement": {"onsite", "hybrid", "remote"},
    "j6_autonomy": {"assigned", "some", "choose"},
    "j7_growth": {"none", "mentor_budget", "track", "track_plus"},
}
# Free text, kept only when the answer it belongs to asks for it.
TEXT = {"d2_self": ("d2_gender", "self"),
        "st2_other": ("st2_field", "other")}
B4 = ["b4_ctc", "b4_varpay", "b4_arrangement", "b4_hours", "b4_autonomy", "b4_growth"]

PARTICIPANT_COLUMNS = [
    "pid", "code", "pilot", "block", "path", "s1", "anchor_ctc", "anchor_type",
    "b1_switch", "b2_switch", "b3a_choice", "b3a_order", *B4,
    "d1_age", "d2_gender", "d2_self", "d3_stock", "d4_channel", "d4_other",
    "st2_field", "st2_other", "st3_year",
    "j1_exp", "j3_paymix", "j4_arrangement", "j5_hours",
    "j6_autonomy", "j7_growth", "j8_satisfaction",
    "e1_text", "total_time_s", "screen_times", "submitted_at",
]
CHOICE_COLUMNS = [
    "pid", "block", "set_id", "kind", "pair", "alt_id", "flipped", "chosen",
    "salary_level", "salary", "varpay", "arrangement", "hours", "autonomy", "growth", "rt_ms",
]
CTC_TOLERANCE = 0.051          # displayed CTC is level x anchor rounded to 0.1 LPA


class Invalid(ValueError):
    """The submission is malformed; the message says which field."""


def _pick(d, key, allowed):
    value = d.get(key)
    if value not in allowed:
        raise Invalid(f"{key}: unexpected value {value!r}")
    return value


def _number(d, key, lo, hi, integer=False):
    value = d.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
        raise Invalid(f"{key}: expected a number from {lo} to {hi}, got {value!r}")
    if integer and int(value) != value:
        raise Invalid(f"{key}: expected a whole number, got {value!r}")
    return int(value) if integer else float(value)


def _text(d, key, limit):
    value = d.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise Invalid(f"{key}: expected text")
    return value.strip()[:limit]


def _choice_rows(choices, plan, anchor):
    if not isinstance(choices, list) or len(choices) != len(plan):
        raise Invalid(f"choices: expected {len(plan)} answers")
    by_set = {c.get("set_id"): c for c in choices if isinstance(c, dict)}
    rows = []
    for screen in plan:
        c = by_set.get(screen["set_id"])
        if c is None:
            raise Invalid(f"choices: no answer for screen {screen['set_id']}")
        chose = _pick(c, "chose", {"A", "B"})
        rt_ms = _number(c, "rt_ms", 0, 3_600_000, integer=True)
        for alt_id, side in ((1, "A"), (2, "B")):
            profile = screen[side]
            shown = _number(c, f"ctc_{side}", 0, 1000)
            if abs(shown - profile["salary_level"] * anchor) > CTC_TOLERANCE:
                raise Invalid(f"choices: screen {screen['set_id']} CTC does not match the anchor")
            rows.append(dict(set_id=screen["set_id"], kind=screen["kind"], pair=screen["pair"],
                             alt_id=alt_id, flipped=screen["flipped"], chosen=int(chose == side),
                             salary_level=profile["salary_level"], salary=shown,
                             varpay=profile["varpay"], arrangement=profile["arrangement"],
                             hours=profile["hours"], autonomy=profile["autonomy"],
                             growth=profile["growth"], rt_ms=rt_ms))
    return rows


def validate(payload, plan):
    """Check a submission against its screen plan.

    Returns (answers, choice_rows): answers holds every participant-level column
    except pid/code/pilot/block/submitted_at; choice_rows holds one dict per job
    shown, without pid/block.
    """
    a = {"s1": _pick(payload, "s1", ELIGIBLE_S1)}
    a["path"] = path = ELIGIBLE_S1[a["s1"]]
    if payload.get("anchor_na") is True:
        a["anchor_ctc"], a["anchor_type"] = DEFAULT_ANCHOR, "default"
    else:
        a["anchor_ctc"] = round(_number(payload, "anchor_ctc", 1, 200), 1)
        a["anchor_type"] = ({"professional": "current", "between": "most_recent"}.get(path)
                            or _pick(payload, "p2_source", {"offer", "estimate"}))
    for key, allowed in COMMON.items():
        a[key] = _pick(payload, key, allowed)
    for key, allowed in (STUDENT if path == "student" else WORKER).items():
        a[key] = _pick(payload, key, allowed)
    if path != "student":
        a["j5_hours"] = _number(payload, "j5_hours", 10, 100)
        a["j8_satisfaction"] = _number(payload, "j8_satisfaction", 0, 10, integer=True)
    points = [_number(payload, key, 0, 100, integer=True) for key in B4]
    if sum(points) != 100:
        raise Invalid(f"b4: points add up to {sum(points)}, not 100")
    a.update(zip(B4, points))
    for key, (parent, trigger) in TEXT.items():
        a[key] = _text(payload, key, 200) if a.get(parent) == trigger else ""
    a["e1_text"] = _text(payload, "e1_text", 2000)
    a["total_time_s"] = _number(payload, "total_time_s", 0, 86_400)
    times = payload.get("screen_times") or {}
    if not isinstance(times, dict) or not all(
            isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)
            for k, v in times.items()):
        raise Invalid("screen_times: expected {screen: milliseconds}")
    a["screen_times"] = json.dumps(times, sort_keys=True)
    return a, _choice_rows(payload.get("choices"), plan, a["anchor_ctc"])
