"""Seed data for local dev and test databases.

DEV/TEST ONLY. Production data is loaded through the admin ingestion API,
never through this script.

Safe to re-run: courses are upserted, and every other row is only inserted if
it is not already there. The whole run is one transaction, so either every row
lands or none do.

Run from the repo root with the venv active:
    python seeds/seed.py
"""

import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()

PROGRAM_NAME = "Master of Science - Software Engineering"
PROGRAM_CREDITS = 36
CREDITS = 3

# Codes, titles, credits and descriptions come from the Regis catalog. Stray
# commas that the catalog text had at line breaks were removed; no words changed.
COURSES = [
    ("MSSE 601", "Software Engineer Fundamentals", "Introduces the Software Engineering Body of Knowledge and the Unified Modeling Language used to communicate the design of object-oriented software systems. Presents an Agile software development process that is enabled with the use of a layered software architecture."),
    ("MSSE 603", "Software Engineering Leadership", "Technical leadership course with a focus on leveling up engineers to mentor and lead multiple projects and engineers within an organization. Team requirements and project delivery are key deliverables."),
    ("MSSE 610", "Software Requirements and Processes", "Examines acquisition, analysis, specification, validation, and management of software requirements. Explores formal software processes, including the definition, implementation, measurement, management, change, and improvement of the software engineering process."),
    ("MSSE 613", "Software Project Management", "Course emulating a real-world developer team implementing a product. This Agile course focuses on project management and delivery where the facilitator is the Product Owner helping the team understand stakeholder requirements and successfully deliver an MVP (Minimum Viable Product)."),
    ("MSSE 615", "Software Engineering and Society", "Professional development course on best practices in small team ethics, communication, and team dynamics within the workplace. Examines the inner workings of different team styles and structures in learning and skills transference across group members and aiding successful developer workplace relations."),
    ("MSSE 635", "Software Architecture and Design", "Study of the concepts, representation techniques, development methods, and tools for architecture-centric software engineering. Topics include domain-specific software architectures, architectural styles, architecture description languages, software connectors, and dynamism in architectures. The course covers the foundations and principles of software architecture as well as some of the more recent literature and research issues."),
    ("MSSE 640", "Software Quality and Test", "Introduces the software quality assurance process and the means to monitor, control, and evaluate software quality. Presents software testing techniques, tools, and processes. Covers both plan-driven and Agile techniques for software quality and test."),
    ("MSSE 642", "Software Assurance", "Provides a detailed explanation of software assurances practices, methods, and tools required throughout the software development life-cycle. Applies life-cycle knowledge in exploring common programming errors and evaluates common software testing tools."),
    ("MSES 602", "Introduction to DevOps Engineering", "Introduces the methodologies, tools, and insights of the DevOps process and what it can do for an organization. The course covers development, deployment and operations including infrastructure as code, continuous deployment, testing automation, validation, monitoring and security."),
    ("MSCC 697", "Information Technology Research Methods", "Through discussions, students become familiar with the foundational concepts of developing a problem statement for further investigation. Presents students with the skills and knowledge to develop their capabilities to identify, categorize, evaluate and synthesize a body of knowledge for a specific purpose."),
    # The full prerequisite rule for 692 cannot be stored in the prerequisites
    # table (see below), so it is kept in the description text.
    ("MSSE 692", "Software Engineering Practicum I", "Begins development of a distributed software system using the principles of Service Oriented Architectures. Encourages use of a cloud provider like Amazon Web Services, Windows Azure, or the Google App Engine. Prerequisite(s): MSSE 610, MSSE 695, and 30 semester hour credits of MSSE coursework, or permission of instructor."),
    ("MSSE 696", "Software Engineering Practicum II", "Completes development of the software system begun in MSSE 692. Concludes with a presentation and paper to mock stakeholders, such as senior management or investors."),
]

# Real prerequisites from the catalog. MSSE 692 also requires MSSE 695, 30
# credits of MSSE coursework, or instructor permission. Only MSSE 610 is
# seeded: 695 is not one of the 12 degree courses (no row to point at), and the
# table has no way to express a credit threshold or an "or permission" option.
PREREQUISITES = [
    ("MSSE 610", "MSSE 601", "prereq"),
    ("MSSE 635", "MSSE 610", "prereq"),
    ("MSSE 640", "MSSE 610", "prereq"),
    ("MSSE 642", "MSSE 610", "prereq"),
    ("MSSE 692", "MSSE 610", "prereq"),
]

# (clerk_user_id, email, full_name, status)
STUDENTS = [
    ("user_3K1pC0YksFOD8HW1dIiz4ITDt90", "nearly.done@example.edu", "Test Student Nearly Done", "active"),
    ("user_3K1pFAxQfqDz2PPIyQtCuhCoMWO", "just.started@example.edu", "Test Student Just Started", "active"),
]

# (course code, term, status). "Nearly done" has 30 credits completed and only
# the two practicums left (6 credits remaining); "just started" has 3 credits.
TRANSCRIPTS = {
    "nearly.done@example.edu": [
        ("MSSE 601", "Fall 2024", "completed"),
        ("MSSE 603", "Fall 2024", "completed"),
        ("MSSE 610", "Spring 2025", "completed"),
        ("MSSE 613", "Spring 2025", "completed"),
        ("MSSE 615", "Summer 2025", "completed"),
        ("MSSE 635", "Summer 2025", "completed"),
        ("MSSE 640", "Fall 2025", "completed"),
        ("MSSE 642", "Fall 2025", "completed"),
        ("MSES 602", "Fall 2025", "completed"),
        ("MSCC 697", "Fall 2025", "completed"),
    ],
    "just.started@example.edu": [
        ("MSSE 601", "Summer 2026", "completed"),
        ("MSSE 603", "Fall 2026", "in_progress"),
    ],
}

# (name, email, contact_type, booking_url). Placeholders, not real contacts.
CONTACTS = [
    ("Test Advisor", "advisor@example.edu", "advisor", "https://example.edu/book-advisor"),
    ("Test Career Services", "careers@example.edu", "career_services", "https://example.edu/careers"),
]

# (credit_min, credit_max, label, next_actions). Brackets from the team's design.
MILESTONES = [
    (0, 12, "Foundations", ["Review your degree plan with your advisor", "Start a portfolio repository on GitHub"]),
    (13, 24, "Internships", ["Add new skills to your resume", "Apply to internships"]),
    (25, None, "Capstone", ["Finalize your portfolio", "Prepare for your practicum"]),
]


def insert_if_missing(cur, exists_sql, insert_sql, params):
    """Runs insert_sql only when exists_sql finds no matching row."""
    cur.execute(exists_sql, params)
    if cur.fetchone() is None:
        cur.execute(insert_sql, params)


def seed(cur):
    """Inserts all seed rows using the given cursor."""
    cur.execute("SELECT program_id FROM programs WHERE name = %s", (PROGRAM_NAME,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO programs (name, total_credits_required) "
            "VALUES (%s, %s) RETURNING program_id",
            (PROGRAM_NAME, PROGRAM_CREDITS),
        )
        row = cur.fetchone()
    program_id = row[0]

    course_ids = {}
    for code, title, description in COURSES:
        cur.execute(
            "INSERT INTO courses (code, title, description, credits, is_active) "
            "VALUES (%s, %s, %s, %s, true) "
            "ON CONFLICT (code) DO UPDATE SET title = EXCLUDED.title, "
            "description = EXCLUDED.description, credits = EXCLUDED.credits "
            "RETURNING course_id",
            (code, title, description, CREDITS),
        )
        course_ids[code] = cur.fetchone()[0]

    for code, course_id in course_ids.items():
        insert_if_missing(
            cur,
            "SELECT 1 FROM requirements WHERE program_id = %(program_id)s "
            "AND course_id = %(course_id)s",
            "INSERT INTO requirements (program_id, course_id, category, credits_required) "
            "VALUES (%(program_id)s, %(course_id)s, 'core', %(credits)s)",
            {"program_id": program_id, "course_id": course_id, "credits": CREDITS},
        )

    for code, required_code, kind in PREREQUISITES:
        insert_if_missing(
            cur,
            "SELECT 1 FROM prerequisites WHERE course_id = %(course_id)s "
            "AND prerequisite_course_id = %(required_id)s",
            "INSERT INTO prerequisites (course_id, prerequisite_course_id, requirement_type) "
            "VALUES (%(course_id)s, %(required_id)s, %(kind)s)",
            {
                "course_id": course_ids[code],
                "required_id": course_ids[required_code],
                "kind": kind,
            },
        )

    student_ids = {}
    for clerk_user_id, email, full_name, status in STUDENTS:
        cur.execute(
            "INSERT INTO students (program_id, clerk_user_id, email, full_name, status) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (program_id, clerk_user_id, email, full_name, status),
        )
        cur.execute("SELECT student_id FROM students WHERE email = %s", (email,))
        student_ids[email] = cur.fetchone()[0]

    for email, entries in TRANSCRIPTS.items():
        for code, term, status in entries:
            insert_if_missing(
                cur,
                "SELECT 1 FROM transcript_entries WHERE student_id = %(student_id)s "
                "AND course_id = %(course_id)s AND term = %(term)s",
                "INSERT INTO transcript_entries (student_id, course_id, term, status) "
                "VALUES (%(student_id)s, %(course_id)s, %(term)s, %(status)s)",
                {
                    "student_id": student_ids[email],
                    "course_id": course_ids[code],
                    "term": term,
                    "status": status,
                },
            )

    for name, email, contact_type, booking_url in CONTACTS:
        insert_if_missing(
            cur,
            "SELECT 1 FROM advisor_contacts WHERE email = %(email)s",
            "INSERT INTO advisor_contacts (name, email, contact_type, booking_url) "
            "VALUES (%(name)s, %(email)s, %(contact_type)s, %(booking_url)s)",
            {"name": name, "email": email, "contact_type": contact_type, "booking_url": booking_url},
        )

    for credit_min, credit_max, label, next_actions in MILESTONES:
        insert_if_missing(
            cur,
            "SELECT 1 FROM milestones WHERE label = %(label)s",
            "INSERT INTO milestones (credit_min, credit_max, label, next_actions) "
            "VALUES (%(credit_min)s, %(credit_max)s, %(label)s, %(next_actions)s)",
            {
                "credit_min": credit_min,
                "credit_max": credit_max,
                "label": label,
                "next_actions": next_actions,
            },
        )


def print_counts(cur):
    """Prints row counts so the run can be checked at a glance."""
    for table in ("programs", "courses", "requirements", "prerequisites", "students",
                  "transcript_entries", "advisor_contacts", "milestones"):
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cur.fetchone()[0]}")


def main():
    if os.getenv("APP_ENV", "local") in ("prod", "production"):
        sys.exit("Refusing to run seed data against a production environment.")
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            seed(cur)
            print("Seed complete. Row counts:")
            print_counts(cur)


if __name__ == "__main__":
    main()
