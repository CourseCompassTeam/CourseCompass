"""Regex parser for unofficial transcript text. No PDF or LLM required."""

from app.ingestion.transcript_parser import parse_transcript_text

SAMPLE_TEXT = """
Course             Title              Grd R   Att    Cmpt   Gpa    Points   Course Dates
------- -------    ------------------ --- - ------ ------ ------ -------- -----------------
MSSE    600        Object-Oriented So A       3.00   3.00   3.00 12.00000 01/15/24-03/10/24
                   24S8W1    Totals:  3.00   3.00   3.00  12.0000 GPA =  4.0000
                   Cumulative Totals: 3.00   3.00   3.00  12.0000 GPA =  4.0000
MSSE    663        Web Frameworks     A       3.00   3.00   3.00 12.00000 08/26/24-10/20/24
                   24F8W1    Totals:  3.00   3.00   3.00  12.0000 GPA =  4.0000
                   Cumulative Totals: 6.00   6.00   6.00  24.0000 GPA =  4.0000
MSSE    615        Software Engineeri A       3.00   3.00   3.00 12.00000 10/20/25-12/14/25
MSSE    610        Software Req and P A       3.00   3.00   3.00 12.00000 10/20/25-12/14/25
                   25F8W2    Totals:  6.00   6.00   6.00  24.0000 GPA =  4.0000
                   Cumulative Totals: 18.00  18.00  18.00  72.0000 GPA =  4.0000
Student Name: Jane Doe
Student ID: 123456789
"""


def test_parse_extracts_courses_and_drops_pii_lines():
    parsed = parse_transcript_text(SAMPLE_TEXT)

    assert parsed['course_count'] == 4
    codes = [row['code'] for row in parsed['courses']]
    assert codes == ['MSSE 600', 'MSSE 663', 'MSSE 615', 'MSSE 610']
    assert parsed['courses'][0]['grade'] == 'A'
    assert parsed['courses'][0]['hours_completed'] == 3.0
    assert 'Jane Doe' not in str(parsed)
    assert '123456789' not in str(parsed)


def test_parse_keeps_term_and_cumulative_totals():
    parsed = parse_transcript_text(SAMPLE_TEXT)

    assert [row['term'] for row in parsed['term_summaries']] == [
        '24S8W1',
        '24F8W1',
        '25F8W2',
    ]
    assert parsed['cumulative_summary']['hours_completed'] == 18.0
    assert parsed['cumulative_summary']['cumulative_gpa'] == 4.0
