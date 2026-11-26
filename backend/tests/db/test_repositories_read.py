"""Read-only checks for the PostgreSQL catalog and audit repositories.

Every test only reads, so it is safe against a shared database. Assertions
check shape and invariants, not exact rows, because real users change data.
Set RUN_DB_TESTS=1 and DATABASE_URL to run them.
"""

import os

import psycopg
import pytest

from app.repositories.connection import Database
from app.repositories.postgres_audit import PostgresAuditRepository
from app.repositories.postgres_catalog import PostgresCatalogRepository

pytestmark = pytest.mark.skipif(
    os.getenv('RUN_DB_TESTS') != '1' or not os.getenv('DATABASE_URL'),
    reason='Set RUN_DB_TESTS=1 (and DATABASE_URL) to run repository read tests.',
)

SEED_EMAIL = 'just.started@example.edu'


@pytest.fixture(scope='module')
def database():
    return Database(os.environ['DATABASE_URL'])


@pytest.fixture(scope='module')
def catalog(database):
    return PostgresCatalogRepository(database)


@pytest.fixture(scope='module')
def audit(database):
    return PostgresAuditRepository(database)


@pytest.fixture(scope='module')
def seed_student(database):
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        row = conn.execute(
            'SELECT student_id, clerk_user_id FROM students WHERE email = %s',
            (SEED_EMAIL,),
        ).fetchone()
    if row is None:
        pytest.skip('Seed student is missing from this database.')
    return {'student_id': str(row[0]), 'clerk_user_id': row[1]}


# ------------------------------------------------------------- catalog reads

def test_get_course_by_code_and_number(catalog):
    course = catalog.get_course('MSSE 635')

    assert course is not None
    assert course['code'] == 'MSSE 635'
    assert catalog.get_course('635')['code'] == 'MSSE 635'


def test_find_courses_handles_blank_and_unknown(catalog):
    assert catalog.find_courses('') == []
    assert catalog.find_courses('NOPE 999') == []
    assert catalog.get_course('NOPE 999') is None


def test_list_programs_for_course_returns_names(catalog):
    course = catalog.get_course('MSSE 635')

    names = catalog.list_programs_for_course(str(course['course_id']))

    assert all(isinstance(name, str) and name for name in names)
    assert catalog.list_programs_for_course('') == []


def test_prerequisites_for_known_and_unknown_course(catalog):
    prereqs = catalog.get_prerequisites('MSSE 692')

    assert prereqs
    assert all('code' in prereq and 'requirement_type' in prereq for prereq in prereqs)
    assert catalog.get_prerequisites('NOPE 999') == []


def test_active_courses_are_all_active(catalog):
    courses = catalog.list_active_courses()

    assert courses
    assert all(course['is_active'] for course in courses)


def test_offerings_have_term_and_dates(catalog):
    offerings = catalog.list_offerings()

    assert offerings
    assert {'code', 'term_name', 'start_date', 'end_date'} <= set(offerings[0])


def test_syllabus_chunks_for_course(catalog):
    chunks = catalog.list_syllabus_chunks('MSSE 601')

    assert chunks
    assert [chunk['chunk_index'] for chunk in chunks] == sorted(
        chunk['chunk_index'] for chunk in chunks)
    assert catalog.list_syllabus_chunks('NOPE 999') == []


def test_all_syllabus_chunks_are_ordered_by_code(catalog):
    rows = catalog.list_all_syllabus_chunks()

    assert rows
    codes = [row['code'] for row in rows]
    assert codes == sorted(codes)


# --------------------------------------------------------------- audit reads

def test_student_lookup_by_clerk_id(audit, seed_student):
    student = audit.get_student(seed_student['clerk_user_id'])

    assert str(student['student_id']) == seed_student['student_id']
    assert audit.get_student('user_does_not_exist') is None


def test_student_course_lists(audit, seed_student):
    student_id = seed_student['student_id']

    assert isinstance(audit.get_completed_courses(student_id), list)
    assert isinstance(audit.get_in_progress_courses(student_id), list)
    assert isinstance(audit.get_substitutions(student_id), list)
    assert audit.get_completed_courses('') == []


def test_program_lookups(audit, seed_student):
    student = audit.get_student(seed_student['clerk_user_id'])
    program = audit.get_program(str(student['program_id']))

    assert program is not None
    assert audit.get_default_program() is not None
    assert audit.get_program_by_name(program['name'])['name'] == program['name']
    assert audit.get_program_by_name('') is None


def test_requirements_for_student_program(audit, seed_student):
    requirements = audit.get_program_requirements(seed_student['student_id'])

    assert requirements
    assert all('course_id' in requirement for requirement in requirements)
    assert audit.get_program_requirements('') == []
