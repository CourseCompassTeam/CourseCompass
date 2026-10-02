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
    ("MSSE 692", "Software Engineering Practicum I", "Begins development of a distributed software system using the principles of Service Oriented Architectures. Encourages use of a cloud provider like Amazon Web Services, Windows Azure, or the Google App Engine. Prerequisite(s): MSSE 610, MSSE 695, and 30 semester hour credits of MSSE coursework, or permission of instructor."),
    ("MSSE 696", "Software Engineering Practicum II", "Completes development of the software system begun in MSSE 692. Concludes with a presentation and paper to mock stakeholders, such as senior management or investors."),
]

# Real prerequisites from the catalog.
PREREQUISITES = [
    ("MSSE 610", "MSSE 601", "prereq"),
    ("MSSE 635", "MSSE 610", "prereq"),
    ("MSSE 640", "MSSE 610", "prereq"),
    ("MSSE 642", "MSSE 610", "prereq"),
    ("MSSE 692", "MSSE 601", "prereq"),
    ("MSSE 692", "MSSE 610", "prereq"),
    ("MSSE 692", "MSSE 635", "prereq"),
    ("MSSE 692", "MSSE 640", "prereq"),
    ("MSSE 692", "MSSE 642", "prereq"),
    ("MSSE 692", "MSES 602", "prereq"),
    ("MSSE 692", "MSSE 613", "prereq"),
    ("MSSE 692", "MSSE 603", "prereq"),
    ("MSSE 692", "MSSE 615", "prereq"),
    ("MSSE 692", "MSCC 697", "prereq"),
    ("MSSE 696", "MSSE 601", "prereq"),
    ("MSSE 696", "MSSE 610", "prereq"),
    ("MSSE 696", "MSSE 635", "prereq"),
    ("MSSE 696", "MSSE 640", "prereq"),
    ("MSSE 696", "MSSE 642", "prereq"),
    ("MSSE 696", "MSES 602", "prereq"),
    ("MSSE 696", "MSSE 613", "prereq"),
    ("MSSE 696", "MSSE 603", "prereq"),
    ("MSSE 696", "MSSE 615", "prereq"),
    ("MSSE 696", "MSCC 697", "prereq"),
    ("MSSE 696", "MSSE 692", "prereq"),
]

# Term dates from the team's course schedule. term_name uses the short
# format already used in COURSE_OFFERINGS ("2026 FALL 8W1"), not the
# longer form the schedule was first written in.
TERMS = [
    ("2026 FALL 8W1", "2026-08-24", "2026-10-18"),
    ("2026 FALL 8W2", "2026-10-19", "2026-12-13"),
    ("2027 SPR 8W1", "2027-01-11", "2027-03-07"),
    ("2027 SPR 8W2", "2027-03-08", "2027-05-02"),
]

# Real term offerings from the team's rotation schedule. MSES 602 and
# MSCC 697 are not in this list yet.
COURSE_OFFERINGS = {
    "MSSE 610": ["2026 FALL 8W2", "2027 SPR 8W2"],
    "MSSE 613": ["2027 SPR 8W2"],
    "MSSE 642": ["2027 SPR 8W2"],
    "MSSE 696": ["2026 FALL 8W2", "2027 SPR 8W2"],
    "MSSE 601": ["2026 FALL 8W1", "2027 SPR 8W1"],
    "MSSE 603": ["2027 SPR 8W1"],
    "MSSE 635": ["2026 FALL 8W2", "2027 SPR 8W1"],
    "MSSE 640": ["2027 SPR 8W1"],
    "MSSE 692": ["2026 FALL 8W1", "2027 SPR 8W1"],
    "MSSE 615": ["2026 FALL 8W2"],
}

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

# Syllabus chunks staged for embedding. embedding stays NULL until the team
# picks an embedding model; this data is otherwise ready to use as-is.
SYLLABUS_CHUNKS = {
    "MSSE 601": [
        "MSSE-601 Introduction to Software Engineering. This class provides an overview of the software engineering process including planning, engineering process management, requirements gathering, UI design, software architecture, development, software quality, and deployment and maintenance. Format: asynchronous online with weekly Zoom lectures.",
        "Course objectives: describe the knowledge of the field of software engineering and provide examples of the types of activities done in each of these areas. List some of the key capabilities to create or improve a high-performing development team. Describe the software development lifecycle including gathering requirements, architectural design, sustainable development, and software quality assurance. Describe basic analysis and design techniques and explain how they are implemented in software.",
        "Weekly topics: Week 1, introduction to software engineering. Week 2, methodologies and management. Week 3, requirements gathering. Week 4, UI design. Week 5, software architecture. Week 6, software development. Week 7, software quality. Week 8, deployment and maintenance.",
    ],
    "MSSE 603": [
        "MSSE-603 Software Engineering Leadership. This course develops software engineering leadership skills, emphasizing team management, technical strategy, business alignment, and systems thinking. Students will analyze real-world case studies, engage in leadership role rotations, and develop a strategic improvement plan for a selected software organization.",
        "Course objectives: demonstrate principles of effective software engineering leadership and team management. Analyze and apply key capabilities to improve software delivery performance, including technical processes, metrics, and cultural practices. Develop and execute strategies that align technical initiatives with business objectives and organizational goals. Apply systems thinking principles to analyze and improve engineering leadership challenges. Integrate security, tooling, and emerging technologies into software development processes to enhance efficiency and reliability. Communicate and collaborate effectively with cross-functional stakeholders to align technical solutions with business value. Design and present an organizational improvement plan using real-world leadership frameworks and systems thinking methodologies.",
        "Weekly topics: Week 1, introduction to software engineering leadership and systems thinking. Week 2, technical processes and performance measurement. Week 3, team dynamics, culture and management practices. Week 4, business-technology alignment and strategic decision-making. Week 5, leadership challenges, security and risk management. Week 6, applying systems thinking to leadership. Week 7, finalizing leadership strategy and presentation. Week 8, final presentations and course reflection.",
    ],
    "MSSE 610": [
        "MSSE-610 Software Requirements and Processes. This course covers system analysis techniques to acquire, analyze, specify, validate, verify, and manage software requirements using plan driven/waterfall and agile methodologies. Explores how quality requirements lead to quality software. Introduces risk management from a software requirements perspective.",
        "Course objectives: describe the key competencies of a system analyst. Compare and contrast plan-driven/waterfall and agile methodologies. Employ tools and techniques to perform system analysis. Discuss the key differences between user stories and use-cases. Explain the purpose of requirement validation and verification. Describe the process of managing requirements. Describe risk analysis in the context of requirements management.",
        "Weekly topics: Week 1, introduction to waterfall and agile methodologies. Week 2, software requirements and system analysis. Week 3, waterfall projects. Week 4, waterfall projects part 2. Week 5, agile projects. Week 6, agile estimating and planning. Week 7, agile non-functional requirements. Week 8, validating and verifying, managing requirements, managing risk.",
    ],
    "MSSE 613": [
        "MSSE-613 Software Project Management. This course focuses on advanced principles and practices of software engineering project management, emphasizing the creation of real-world project artifacts. Topics include scaled Agile frameworks, advanced planning techniques, quality assurance, resource management, and compliance. Students will work on a capstone project, creating deliverables incrementally each week, culminating in a final presentation.",
        "Course objectives: develop and manage software project artifacts. Apply advanced Agile methodologies to large-scale projects. Utilize tools for planning, tracking, and quality assurance. Address legal, ethical, and compliance issues in software projects. Present and defend a comprehensive project plan and deliverables.",
        "Weekly topics: Week 1, project proposal and stakeholder analysis. Week 2, project plan and risk management plan. Week 3, product backlog and sprint plan. Week 4, tool configuration and quality assurance plan. Week 5, resource allocation plan and budget. Week 6, compliance and ethics report. Week 7, integration of deliverables. Week 8, capstone presentation, peer feedback, individual capstone reflection.",
    ],
    "MSSE 615": [
        "MSSE-615 Software Engineering and Society. This graduate course explores the ethical and societal dimensions of software engineering. Students will analyze professional ethics, societal impacts, and responsible innovation in software development. The course integrates ethical decision-making frameworks with software engineering practices, preparing students to navigate complex ethical challenges in their professional careers. Learners will create a portfolio of assignments that builds from the first week of class to the final week, critically evaluating professional ethics and the societal impacts of software development, with an emphasis on responsible innovation.",
        "Course objectives: analyze ethical dimensions in software engineering. Understand societal impacts of software systems. Apply professional practice principles. Integrate ethical considerations into the software development lifecycle. Evaluate and manage intellectual property in software engineering. Understand global and cultural aspects of software engineering. Apply sustainable and responsible innovation principles. Synthesize ethical decision-making frameworks.",
        "Weekly topics: Week 1, introduction to ethics in software engineering. Week 2, societal impacts of software systems. Week 3, professional practice and legal frameworks. Week 4, ethical software development lifecycle. Week 5, intellectual property in software engineering. Week 6, global and cultural aspects of software engineering. Week 7, sustainable and responsible innovation. Week 8, ethical decision-making and future challenges.",
    ],
    "MSSE 635": [
        "MSSE-635 Software Architecture and Design. This online course explores architectural patterns, design principles, and system design at scale. Students learn to make architectural decisions, understand trade-offs, and design systems that meet quality attributes. Emphasis on microservices, event-driven architecture, and distributed systems concepts in tool-agnostic contexts. Students work collaboratively to design, document, and defend complex software architectures through virtual team interactions.",
        "Course objectives: design software architectures that satisfy functional and quality attribute requirements. Evaluate and select appropriate architectural patterns for given problem domains. Analyze trade-offs between architectural approaches, including monolithic, microservices, and serverless. Document architectural decisions and rationale using industry-standard methods. Apply distributed systems concepts to modern software architecture challenges.",
        "Weekly topics: Week 1, architectural thinking and quality attributes. Week 2, architectural patterns and styles. Week 3, microservices architecture. Week 4, event-driven and message-based architecture. Week 5, distributed systems fundamentals. Week 6, API design and integration patterns. Week 7, architecture documentation and ADRs. Week 8, architecture evaluation and final presentation.",
    ],
    "MSSE 640": [
        "MSSE-640 Software Quality and Test. Reviews the Software Quality Assurance and Verification and Validation processes. Addresses verification of the behavior of a program on a set of test cases selected from the execution domain. This course presents a practical approach to software testing as a sub-discipline of software engineering, introducing quality concepts, standards, measurements, and practices that support the production of quality software. It offers a foundation in testing fundamentals, including test case design, test management, and test measurement strategies. Software quality and testing concepts are presented from managerial, technical, and process-oriented perspectives, for both traditional plan-driven and agile development methodologies.",
        "Course objectives: explain the similarities and differences in software quality practices between plan-driven and agile teams. Integrate software quality assurance practices using Testing Maturity Model levels for software development processes. Develop a comprehensive software quality and test plan. Analyze test cases to support multiple testing goals. Develop a test automation strategy by selecting two or more automated test tools. Evaluate quantitative methods for evaluating the effectiveness of software quality processes. Discuss ethics and social responsibility related to current incidents within the software engineering community.",
        "Weekly topics: Week 1, software quality assurance and testing fundamentals. Week 2, code review and white box testing. Week 3, test-case design. Week 4, unit testing. Week 5, higher-order testing. Week 6, usability testing and debugging. Week 7, test automation tools and techniques in agile environment. Week 8, emerging technology, DevOps testing, and conclusion.",
    ],
    "MSSE 642": [
        "MSSE-642 Software Assurance. Provides a detailed explanation of software assurance practices, methods, and tools required throughout the software development lifecycle. Students apply lifecycle knowledge in exploring common programming errors and evaluate common testing tools. Expands knowledge of the software development lifecycle and software engineering within the context of secure software development, addressing both the IEC/IEEE software development lifecycle and ISC2 CSSLP domains of knowledge. A primary focus is examining common software vulnerabilities and defense, including Identity Access Management and securing web servers with TLS, with project components exploring tools used for identifying flaws in software.",
        "Course objectives: evaluate software design practices for creating secure software. Select appropriate software processes for managing secure software. Demonstrate how software assurance tools are used to manage secure software. Detect and remediate common programming errors affecting security in developed software. Resolve an ethical dilemma through the appraisal of alternatives.",
        "Weekly topics: Week 1, secure coding theory. Week 2, threat modeling and the SDLC. Week 3, common software vulnerabilities and defense part 1. Week 4, common software vulnerabilities and defense part 2. Week 5, identity and access management. Week 6, applied cryptography and TLS. Week 7, penetration testing using Kali and Metasploit. Week 8, DevSecOps research discussion.",
    ],
    "MSSE 692": [
        "MSSE-692 Software Engineering Practicum I. An applied, project-based course where students work in teams to address complex, realistic software engineering challenges. This course serves as the capstone preparation experience, requiring students to self-direct their projects, synthesize and apply knowledge from all previous courses in the program, and demonstrate professional-level software engineering judgment. The Practicum emphasizes the application and integration of software engineering principles across multiple domains including architecture, requirements, quality assurance, project management, and professional practice. Students take full responsibility for project definition, scoping, and execution, engaging in the full software engineering lifecycle from project initiation through delivery of production-quality artifacts.",
        "Course objectives: synthesize knowledge from multiple software engineering domains to solve complex, multi-faceted problems. Engage professionally with clients and stakeholders to elicit requirements, manage expectations, and communicate technical decisions. Collaborate effectively in teams using professional practices, tools, and methodologies. Deliver high-quality, well-documented engineering artifacts that meet professional standards. Present technical work effectively to diverse audiences. Navigate ambiguity and complexity by making sound engineering judgments. Apply ethical reasoning to project decisions considering societal impact, privacy, security, and professional responsibility. Reflect on professional practice and identify areas for continued growth.",
        "Weekly topics: Week 1, project initiation. Week 2, discovery and requirements. Week 3, architecture and design. Week 4, detailed design and planning. Week 5, implementation sprint 1. Week 6, implementation sprint 2. Week 7, quality and refinement. Week 8, delivery and presentation.",
    ],
    # PLACEHOLDER: real syllabus not available. Catalog description only.
    "MSSE 696": [
        "MSSE-696 Software Engineering Practicum II. Completes development of the software system begun in MSSE 692. Concludes with a presentation and paper to mock stakeholders, such as senior management or investors.",
    ],
    "MSES 602": [
        "MSES-602 Introduction to DevOps Engineering. Introduces the methodologies, tools, and insights of the DevOps process and what it can do for an organization. The course covers development, deployment and operations including infrastructure as code, continuous deployment, testing automation, validation, monitoring and security. This course is designed to provide a platform for considering ethical leadership in computer science by examining ethical issues associated with software development and implementation.",
        "Course objectives: explain the need for DevOps and the problems it solves. Assess DevOps concepts and practices, including its relationship to Agile, Lean, and IT Service Management. Analyze the role of workflows, communication, feedback loops, critical success factors, and key performance indicators. Apply DevOps concepts in an enterprise environment by automating processes using tools such as Ansible and scripting languages. Create continuous integration and delivery workflows. Apply CI/CD using tools such as Jenkins and Git. Synthesize the role of monitoring and how it helps IT and business succeed. Evaluate tools used for monitoring, alerting, and reporting such as Splunk, AppDynamics, and Nagios. Identify luminaries in computer science who have used computing for the good of mankind. Analyze the efficacy of a computing solution from various interests, including any trade-offs.",
        "Weekly topics: Week 1, the three ways part 1. Week 2, the three ways part 2. Week 3, starting the transformation. Week 4, the technical practices of flow. Week 5, the technical practices of flow II. Week 6, the technical practices of feedback. Week 7, continual learning and experimentation. Week 8, integrating information security, change management, and compliance.",
    ],
    "MSCC 697": [
        "MSCC-697 Information Technology Research Methods. Through discussions of article reviews, secondary research, and literature reviews, students become familiar with the foundational concepts of developing a problem statement for further investigation. Presents students with the skills and knowledge to identify, categorize, evaluate, and synthesize a body of knowledge for a specific purpose, such as descriptive documentation, training materials, corporate white papers, position papers, convention papers, books, or refereed journal papers. The course establishes a foundation in graduate-level research, study, and communication, introducing graduate research techniques and guidelines for APA 7 written communication style and formatting, and begins construction of an individual annotated bibliography.",
        "Course objectives: critically evaluate the literature surrounding an area of information science or information technology. Develop and articulate a problem based on a review of the literature. Demonstrate an understanding of research ethics. Communicate a critical analysis of a body of research in both written and virtual presentation formats. Demonstrate proficiency in correctly applying APA 7 format and writing style. Demonstrate collaboration and productive teamwork in team assignments and discussions.",
        "Weekly topics: Week 1, defining, reading, and consuming research. Week 2, identifying a research problem. Week 3, telling the research story. Week 4, working with the research problem. Week 5, investigating research approaches. Week 6, design science. Week 7, ethics and presentation strategies. Week 8, presenting research and reflection.",
    ],
}

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

    term_ids = {}
    for term_name, start_date, end_date in TERMS:
        cur.execute(
            "INSERT INTO terms (term_name, start_date, end_date) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT (term_name) DO UPDATE SET start_date = EXCLUDED.start_date, "
            "end_date = EXCLUDED.end_date "
            "RETURNING term_id",
            (term_name, start_date, end_date),
        )
        term_ids[term_name] = cur.fetchone()[0]

    for code, terms in COURSE_OFFERINGS.items():
        for term in terms:
            insert_if_missing(
                cur,
                "SELECT 1 FROM course_offerings WHERE course_id = %(course_id)s "
                "AND term_id = %(term_id)s",
                "INSERT INTO course_offerings (course_id, term_id) "
                "VALUES (%(course_id)s, %(term_id)s)",
                {"course_id": course_ids[code], "term_id": term_ids[term]},
            )

    for code, chunks in SYLLABUS_CHUNKS.items():
        for i, chunk_text in enumerate(chunks):
            insert_if_missing(
                cur,
                "SELECT 1 FROM syllabus_chunks WHERE course_id = %(course_id)s "
                "AND chunk_index = %(chunk_index)s",
                "INSERT INTO syllabus_chunks (course_id, chunk_index, chunk_text, embedding) "
                "VALUES (%(course_id)s, %(chunk_index)s, %(chunk_text)s, NULL)",
                {"course_id": course_ids[code], "chunk_index": i, "chunk_text": chunk_text},
            )

def print_counts(cur):
    """Prints row counts so the run can be checked at a glance."""
    for table in ("programs", "courses", "requirements", "prerequisites", "students",
                  "transcript_entries", "advisor_contacts", "milestones", "course_offerings",
		  "syllabus_chunks", "terms"):
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
