"""Builds a term-by-term course plan. Pure logic: no database, no AI.

The planner is data-driven. It knows nothing about specific courses; every rule
(prerequisites, when a course is offered) comes in as arguments, so it works for
any program. The AI can explain a plan, but the plan itself is computed here so
that prerequisite and offering rules are always exact.
"""

from dataclasses import dataclass, field

DEFAULT_MAX_PER_TERM = 2


@dataclass(frozen=True)
class Term:
    term_id: str
    name: str


@dataclass
class PlannedTerm:
    term: Term
    course_ids: list = field(default_factory=list)


@dataclass
class Unplaced:
    course_id: str
    reason: str


@dataclass
class Plan:
    terms: list  # list[PlannedTerm]; only terms that have at least one course
    unplaced: list  # list[Unplaced]


def build_plan(
    remaining,
    satisfied,
    prerequisites,
    offerings,
    terms,
    max_per_term=DEFAULT_MAX_PER_TERM,
):
    """Places each remaining course in the earliest term where it can be taken.

    remaining:     course ids the student still has to take.
    satisfied:     course ids already done or in progress. Anything that counts
                   as a stand-in for a requirement (for example a legacy course)
                   should be expanded by the caller before it gets here.
    prerequisites: {course_id: [(required_course_id, "prereq" | "coreq"), ...]}
    offerings:     {course_id: set of term_id the course is offered in}
    terms:         ordered list of Term, earliest first (only future terms).
    max_per_term:  most courses placed in one term.

    A "prereq" must be satisfied, or placed in an EARLIER term. A "coreq" may
    also be placed in the same term.
    """
    if max_per_term < 1:
        raise ValueError("max_per_term must be at least 1")

    remaining_set = list(dict.fromkeys(remaining))  # de-duplicate, keep order
    done = set(satisfied)
    todo = [c for c in remaining_set if c not in done]
    todo_set = set(todo)

    depth = _unlock_counts(todo, prerequisites)

    planned = []
    for term in terms:
        if not todo_set:
            break
        in_term = []
        progress = True
        while progress and len(in_term) < max_per_term:
            progress = False
            candidates = [
                c for c in todo
                if c in todo_set
                and term.term_id in offerings.get(c, set())
                and _can_take(c, prerequisites, done, in_term)
            ]
            if candidates:
                # Courses that unlock the most other courses go first, then
                # id order so the result is the same every time.
                candidates.sort(key=lambda c: (-depth[c], str(c)))
                chosen = candidates[0]
                in_term.append(chosen)
                todo_set.discard(chosen)
                progress = True
        if in_term:
            planned.append(PlannedTerm(term=term, course_ids=in_term))
            done.update(in_term)  # counts as done for LATER terms only

    unplaced = [
        Unplaced(c, _reason(c, prerequisites, offerings, done, todo_set))
        for c in todo if c in todo_set
    ]
    return Plan(terms=planned, unplaced=unplaced)


def _can_take(course, prerequisites, done_before, in_term):
    """done_before holds courses finished before this term started."""
    for required, kind in prerequisites.get(course, []):
        if required in done_before:
            continue
        if kind == "coreq" and required in in_term:
            continue
        return False
    return True


def _unlock_counts(todo, prerequisites):
    """For each course, how many other remaining courses depend on it."""
    todo_set = set(todo)
    dependents = {c: set() for c in todo}
    for course in todo:
        for required, _kind in prerequisites.get(course, []):
            if required in todo_set:
                dependents[required].add(course)
    counts = {}

    def count(c, seen):
        total = 0
        for d in dependents[c]:
            if d not in seen:
                seen.add(d)
                total += 1 + count(d, seen)
        return total

    for c in todo:
        counts[c] = count(c, {c})
    return counts


def _reason(course, prerequisites, offerings, done, todo_set):
    if not offerings.get(course):
        return "not offered in any available term"
    missing = [
        r for r, _k in prerequisites.get(course, [])
        if r not in done
    ]
    blocked_by_unplaced = [r for r in missing if r in todo_set]
    if blocked_by_unplaced:
        return "waiting on a prerequisite that could not be placed"
    if missing:
        return "prerequisite is not satisfied and is not in the remaining list"
    return "no available term fits (offered terms are full or already past)"
