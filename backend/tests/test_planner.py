"""Unit tests for the schedule planner. No database needed.

Run:  python -m pytest backend/tests/test_planner.py -v
"""

import pytest

from app.scheduling.planner import Term, build_plan

T1, T2, T3, T4 = (Term(f"t{i}", f"Term {i}") for i in range(1, 5))
TERMS = [T1, T2, T3, T4]
EVERY_TERM = {"t1", "t2", "t3", "t4"}


def offered_always(*courses):
    return {c: set(EVERY_TERM) for c in courses}


def placed(plan):
    """{term_id: [course ids]}"""
    return {pt.term.term_id: pt.course_ids for pt in plan.terms}


def test_chain_places_one_step_per_term():
    plan = build_plan(
        remaining=["A", "B", "C"],
        satisfied=[],
        prerequisites={"B": [("A", "prereq")], "C": [("B", "prereq")]},
        offerings=offered_always("A", "B", "C"),
        terms=TERMS,
    )
    assert placed(plan) == {"t1": ["A"], "t2": ["B"], "t3": ["C"]}
    assert plan.unplaced == []


def test_prerequisite_is_never_in_the_same_term():
    plan = build_plan(
        remaining=["A", "B"],
        satisfied=[],
        prerequisites={"B": [("A", "prereq")]},
        offerings=offered_always("A", "B"),
        terms=TERMS,
        max_per_term=5,
    )
    assert placed(plan) == {"t1": ["A"], "t2": ["B"]}


def test_corequisite_may_share_a_term():
    plan = build_plan(
        remaining=["A", "B"],
        satisfied=[],
        prerequisites={"B": [("A", "coreq")]},
        offerings=offered_always("A", "B"),
        terms=TERMS,
        max_per_term=2,
    )
    assert placed(plan) == {"t1": ["A", "B"]}


def test_satisfied_prerequisite_allows_an_immediate_start():
    plan = build_plan(
        remaining=["B"],
        satisfied=["A"],
        prerequisites={"B": [("A", "prereq")]},
        offerings=offered_always("B"),
        terms=TERMS,
    )
    assert placed(plan) == {"t1": ["B"]}


def test_courses_already_satisfied_are_not_scheduled_again():
    plan = build_plan(
        remaining=["A", "B"],
        satisfied=["A"],
        prerequisites={},
        offerings=offered_always("A", "B"),
        terms=TERMS,
    )
    assert placed(plan) == {"t1": ["B"]}


def test_course_waits_for_the_term_it_is_offered():
    plan = build_plan(
        remaining=["A", "B"],
        satisfied=[],
        prerequisites={},
        offerings={"A": {"t1", "t2", "t3", "t4"}, "B": {"t3"}},
        terms=TERMS,
    )
    assert placed(plan) == {"t1": ["A"], "t3": ["B"]}


def test_max_per_term_is_respected():
    plan = build_plan(
        remaining=["A", "B", "C", "D", "E"],
        satisfied=[],
        prerequisites={},
        offerings=offered_always("A", "B", "C", "D", "E"),
        terms=TERMS,
        max_per_term=2,
    )
    assert all(len(c) <= 2 for c in placed(plan).values())
    assert sum(len(c) for c in placed(plan).values()) == 5


def test_course_that_unlocks_more_courses_goes_first():
    # With one slot per term, "Z" would win on id order, but "A" unlocks B and C.
    plan = build_plan(
        remaining=["Z", "A", "B", "C"],
        satisfied=[],
        prerequisites={"B": [("A", "prereq")], "C": [("B", "prereq")]},
        offerings=offered_always("Z", "A", "B", "C"),
        terms=TERMS,
        max_per_term=1,
    )
    assert placed(plan)["t1"] == ["A"]


def test_result_is_the_same_every_time():
    args = dict(
        remaining=["D", "C", "B", "A"],
        satisfied=[],
        prerequisites={"C": [("A", "prereq")]},
        offerings=offered_always("A", "B", "C", "D"),
        terms=TERMS,
        max_per_term=2,
    )
    assert placed(build_plan(**args)) == placed(build_plan(**args))


def test_duplicate_remaining_courses_are_placed_once():
    plan = build_plan(
        remaining=["A", "A", "B"],
        satisfied=[],
        prerequisites={},
        offerings=offered_always("A", "B"),
        terms=TERMS,
    )
    assert sorted(c for cs in placed(plan).values() for c in cs) == ["A", "B"]


def test_final_course_goes_last_when_it_requires_everything():
    # Mirrors the practicum rule: the capstone needs every other course first.
    others = ["A", "B", "C", "D"]
    prereqs = {"CAP": [(c, "prereq") for c in others]}
    plan = build_plan(
        remaining=others + ["CAP"],
        satisfied=[],
        prerequisites=prereqs,
        offerings=offered_always(*others, "CAP"),
        terms=TERMS + [Term("t5", "Term 5")],
        max_per_term=2,
    )
    last = plan.terms[-1]
    assert last.course_ids == ["CAP"]
    assert plan.unplaced == []


# ------------------------------------------------------------- unplaced --

def reasons(plan):
    return {u.course_id: u.reason for u in plan.unplaced}


def test_course_with_no_offering_is_reported():
    plan = build_plan(
        remaining=["A", "B"],
        satisfied=[],
        prerequisites={},
        offerings={"A": {"t1"}},
        terms=TERMS,
    )
    assert placed(plan) == {"t1": ["A"]}
    assert reasons(plan) == {"B": "not offered in any available term"}


def test_prerequisite_outside_the_plan_blocks_the_course():
    plan = build_plan(
        remaining=["B"],
        satisfied=[],
        prerequisites={"B": [("MISSING", "prereq")]},
        offerings=offered_always("B"),
        terms=TERMS,
    )
    assert plan.terms == []
    assert "not satisfied" in reasons(plan)["B"]


def test_not_enough_terms_leaves_courses_unplaced():
    plan = build_plan(
        remaining=["A", "B", "C"],
        satisfied=[],
        prerequisites={"B": [("A", "prereq")], "C": [("B", "prereq")]},
        offerings=offered_always("A", "B", "C"),
        terms=TERMS[:2],
    )
    assert placed(plan) == {"t1": ["A"], "t2": ["B"]}
    assert set(reasons(plan)) == {"C"}


def test_prerequisite_cycle_does_not_hang_and_is_reported():
    plan = build_plan(
        remaining=["A", "B"],
        satisfied=[],
        prerequisites={"A": [("B", "prereq")], "B": [("A", "prereq")]},
        offerings=offered_always("A", "B"),
        terms=TERMS,
    )
    assert plan.terms == []
    assert set(reasons(plan)) == {"A", "B"}


def test_nothing_to_schedule_gives_an_empty_plan():
    plan = build_plan([], [], {}, {}, TERMS)
    assert plan.terms == [] and plan.unplaced == []


def test_max_per_term_must_be_positive():
    with pytest.raises(ValueError):
        build_plan(["A"], [], {}, offered_always("A"), TERMS, max_per_term=0)
