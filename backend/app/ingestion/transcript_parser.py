"""Parse a Regis-style unofficial transcript without using an LLM.

PDF bytes stay in memory. Only allow-listed course and totals lines are
kept, so name, student ID, and other header PII are dropped.
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any

import pdfplumber

_LOG = logging.getLogger(__name__)

# MSSE 600 Object-Oriented So A 3.00 3.00 3.00 12.00000 01/15/24-03/10/24
_COURSE_LINE = re.compile(
    r'^([A-Z]{2,5})\s+(\d{3,4}[A-Z]?)\s+'
    r'(.+?)\s+'
    r'([A-DF][+-]?|P|NP|W|I|CR|NC|IP)'
    r'(?:\s+R)?\s+'
    r'(\d+\.\d{2})\s+'
    r'(\d+\.\d{2})\s+'
    r'(\d+\.\d{2})\s+'
    r'(\d+\.\d{4,5})\s+'
    r'(\d{2}/\d{2}/\d{2}-\d{2}/\d{2}/\d{2})$'
)

# 24S8W1 Totals: 3.00 3.00 3.00 12.0000 GPA = 4.0000
_TERM_TOTALS = re.compile(
    r'^(\d[A-Z0-9]+)\s+Totals:\s+'
    r'(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+'
    r'(\d+\.\d{4,5})\s+GPA\s*=\s*(\d+\.\d{4})$',
    re.IGNORECASE,
)

# Cumulative Totals: 33.00 33.00 33.00 132.0000 GPA = 4.0000
_CUM_TOTALS = re.compile(
    r'^Cumulative\s+Totals:\s+'
    r'(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+'
    r'(\d+\.\d{4,5})\s+GPA\s*=\s*(\d+\.\d{4})$',
    re.IGNORECASE,
)


def parse_transcript_text(text: str) -> dict[str, Any]:
    """Extracts course rows and totals from transcript body text.

    Args:
        text: Extracted page text, already cropped of header/footer.

    Returns:
        Course list, term summaries, and the last cumulative totals block.
    """
    courses: list[dict[str, Any]] = []
    terms: list[dict[str, Any]] = []
    latest_cumulative: dict[str, Any] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        cum_match = _CUM_TOTALS.match(line)
        if cum_match:
            latest_cumulative = {
                'hours_attempted': float(cum_match.group(1)),
                'hours_completed': float(cum_match.group(2)),
                'hours_gpa': float(cum_match.group(3)),
                'total_points': float(cum_match.group(4)),
                'cumulative_gpa': float(cum_match.group(5)),
            }
            continue

        course_match = _COURSE_LINE.match(line)
        if course_match:
            course = {
                'code': (
                    f'{course_match.group(1)} {course_match.group(2)}'
                ),
                'title': course_match.group(3).strip(),
                'grade': course_match.group(4),
                'hours_attempted': float(course_match.group(5)),
                'hours_completed': float(course_match.group(6)),
                'hours_gpa': float(course_match.group(7)),
                'points': float(course_match.group(8)),
                'dates': course_match.group(9),
            }
            courses.append(course)
            _LOG.info(
                'transcript course %s %s %s',
                course['code'],
                course['grade'],
                course['title'],
            )
            continue

        term_match = _TERM_TOTALS.match(line)
        if term_match:
            terms.append({
                'term': term_match.group(1),
                'hours_attempted': float(term_match.group(2)),
                'hours_completed': float(term_match.group(3)),
                'hours_gpa': float(term_match.group(4)),
                'points': float(term_match.group(5)),
                'term_gpa': float(term_match.group(6)),
            })

    _LOG.info('transcript parsed course_count=%s', len(courses))
    return {
        'course_count': len(courses),
        'courses': courses,
        'term_summaries': terms,
        'cumulative_summary': latest_cumulative,
    }


def process_pdf_bytes(pdf_bytes: bytes) -> dict[str, Any]:
    """Reads a PDF from memory, crops header/footer, and parses courses.

    Args:
        pdf_bytes: Raw uploaded PDF. Never written to disk.

    Returns:
        Parsed course and totals payload.

    Raises:
        ValueError: If the PDF has no extractable text.
    """
    pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            width, height = page.width, page.height
            # Drop the header band (name / student ID) and footer.
            body = page.crop((0, height * 0.18, width, height * 0.93))
            page_text = body.extract_text()
            if page_text:
                pages_text.append(page_text)
    if not pages_text:
        raise ValueError('No extractable text was found in the PDF.')
    return parse_transcript_text('\n'.join(pages_text))
